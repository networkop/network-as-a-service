#!/usr/bin/env python3
import os
import copy
import json
import yaml
import logging
import requests
from datetime import datetime
from collections import namedtuple
from jsondiff import diff as jsondiff
from kubernetes import client, config, watch
from kubernetes.client.rest import ApiException

log = logging.getLogger(__name__)

crd_config = namedtuple("NaaS", ["group", "version", "namespace", "scheduler_api"])
DEFAULTS = crd_config(
    "network.as.a.service", "v1", "default", "http://schedule/configure"
)


def normalize_device_name(name):
    return name.lower()


def get_namespaced_crd(name, plural, defaults):
    k8s_api = client.CustomObjectsApi()
    try:
        return k8s_api.get_namespaced_custom_object(
            defaults.group, defaults.version, defaults.namespace, plural, name
        )
    except ApiException as e:
        log.info(f"Caught ApiException when reading {plural}/{name}: {e}")
        return None


def create_namespaced_crd(plural, body, defaults):
    k8s_api = client.CustomObjectsApi()
    return k8s_api.create_namespaced_custom_object(
        defaults.group, defaults.version, defaults.namespace, plural, body
    )


def create_device(body, defaults):
    log.info(f"Creating device {body.get('metadata', {}).get('name')}")
    resp = create_namespaced_crd("devices", body, defaults)
    log.debug(f"Device created. status={resp}")
    return resp


def get_device(name, defaults):
    log.info(f"Reading the {name} device resource")
    return get_namespaced_crd(name, "devices", defaults)


def get_or_create_device(device_name, defaults):
    log.debug(f"Get or Create device resource for {device_name}")
    device = get_device(device_name, defaults)
    if not device:
        blank_device = {
            "apiVersion": "network.as.a.service/v1",
            "kind": "Device",
            "metadata": {
                "name": device_name,
                "namespace": defaults.namespace,
                "labels": {"app": "naas", "type": "model", "device": device_name},
            },
            "spec": {},
        }
        create_device(blank_device, defaults)
    return get_device(device_name, defaults)


def update_device(name, body, defaults):
    log.info(f"Saving resource for device {name}")
    k8s_api = client.CustomObjectsApi()
    resp = k8s_api.replace_namespaced_custom_object(
        defaults.group, defaults.version, defaults.namespace, "devices", name, body
    )
    log.debug(f"Device resources updated. status={resp}")
    return resp


def annotate(owner, namespace):
    return {
        "timestamp": str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        "owner": owner,
        "namespace": namespace,
    }


def add_ports(origin, destination, owner, namespace):
    log.info(f"Adding ports {origin['ports']}")
    ports = origin.pop("ports")
    for port in ports:
        destination[port] = dict()
        destination[port] = origin
        destination[port]["annotations"] = annotate(owner, namespace)
    return destination


def delete_ports(origin, destination, owner):
    log.info(f"Deleting ports {origin['ports']} from {destination}")
    new_destination = copy.deepcopy(destination)
    for port in origin["ports"]:
        if (port in destination) and (
            destination[port].get("annotations", {}).get("owner", "") == owner
        ):
            log.debug(f"Removing port {port} from structured config")
            new_destination.pop(port, None)
    return new_destination


def delete_all_ports(destination, owner):
    log.info(f"Deleting all ports from {destination}")
    new_destination = copy.deepcopy(destination)
    for port, data in destination.items():
        if data.get("annotations", {}).get("owner", "") == owner:
            log.debug(f"Removing port {port} from structured config")
            new_destination.pop(port, None)
    return new_destination


def diff_calculated_between(origin, destination):
    log.info(f"Comparing diff between {origin} and {destination}")
    result = dict()
    new_destination = copy.deepcopy(destination)
    new_origin = copy.deepcopy(origin)

    origin_ports = new_origin.pop("ports", {})
    for port in new_destination.keys():
        new_destination[port].pop("annotations", {})
        if port in origin_ports:
            diff = jsondiff(new_destination[port], new_origin)
            log.debug(f"Diff for port {port} is {diff}")
            if diff:
                result[port] = diff
        else:
            result[port] = new_destination[port]
    log.debug(f"Resulting diff is {result}")
    return result


def process_service(crd_metadata, network_service, action, defaults):
    device_name = normalize_device_name(network_service.pop("devicename"))
    vlan = network_service["vlan"]
    resource_name = crd_metadata["name"]
    resource_namespace = crd_metadata["namespace"]
    resource_generation = crd_metadata["generation"]
    log.info(f"Processing {action} config for Vlans {vlan} on device {device_name}")

    device = get_or_create_device(device_name, defaults)

    device_annotations = device["metadata"].get("annotations")
    log.info(f"Processing request generations")
    if type(device_annotations) == dict:
        generations = yaml.safe_load(device_annotations.get("generations", "{}"))
        log.info(f"Loaded existing generations data {generations}")
    else:
        device_annotations = dict()
        generations = dict()
        device_annotations["generations"] = generations
        log.info(f"Created new generations data")

    device_data = device["spec"]

    if action == "ADDED":
        device_data = add_ports(
            network_service, device_data, resource_name, resource_namespace
        )
        generations[resource_name] = resource_generation

    elif action == "DELETED":
        device_data = delete_ports(network_service, device_data, resource_name)
        generations.pop(resource_name, None)

    elif action == "MODIFIED":
        # To avoid touching newly added resource twice we're comparing generations
        if resource_generation == generations.get(resource_name, ""):
            log.info(f"Request {resource_name} generation hasn't changed, skipping")
            return None, None
        else:
            if not diff_calculated_between(network_service, device_data):
                log.info(
                    f"Nothing has changed for {device_name} and vlan {vlan}, will not update"
                )
                return None, None
            device_data = delete_all_ports(device_data, resource_name)
            device_data = add_ports(
                network_service, device_data, resource_name, resource_namespace
            )

    log.debug(f"Structured {device_name} config: \n {device_data}")

    device_annotations["generations"] = yaml.safe_dump(generations)

    device["metadata"]["annotations"] = device_annotations
    device["spec"] = device_data

    update_device(device_name, device, defaults)

    return device_name, device_data


def update_status(defaults, event_metadata):
    log.info(f"Updating CRD status of {event_metadata['name']}")

    crds = client.CustomObjectsApi()
    resp = crds.patch_namespaced_custom_object_status(
        defaults.group,
        defaults.version,
        event_metadata["namespace"],
        "interfaces",
        event_metadata["name"],
        {"status": {"saved": "OK"}},
    )
    log.info(f"CRD updated. status={resp}")
    return resp


def schedule(device_interface_data, defaults):
    target_devices = [device for device, _ in device_interface_data if device]
    log.info(f"Scheduling configuration update on {target_devices}")
    json_body = {"devices": target_devices}
    headers = {"Content-type": "application/json"}
    try:
        resp = requests.post(
            url=defaults.scheduler_api, data=json.dumps(json_body), headers=headers
        )
        log.info(f"Scheduled response: {resp.text}")
        return resp
    except Exception as e:
        log.info(f"Failed to schedule configuration update. status={e}")
        return None


def process_services(event, defaults):

    event_object = event["object"]
    event_kind = event_object["kind"]
    event_metadata = event_object["metadata"]
    action = event["type"]
    log.info(f"Received {action } event {event_metadata['name']} of {event_kind} kind")
    log.debug(f"Event body: {event_object}")

    # TODO: assuming a single event for now, can this be a list?
    if event_kind != "Interface":
        log.info(f"Skipping event {event_kind} for now...")
        return

    results = list()
    for network_service in event_object["spec"]["services"]:
        results.append(
            process_service(event_metadata, network_service, action, defaults)
        )

    if any([device for device, _ in results]):
        if action != "DELETED":
            update_status(defaults, event_metadata)
        schedule(results, defaults)
    return


def interface_watcher(defaults):
    log.info("Watching Interface CRDs")
    crds = client.CustomObjectsApi()
    w = watch.Watch()
    for event in w.stream(
        crds.list_cluster_custom_object, defaults.group, defaults.version, "interfaces"
    ):
        process_services(event, defaults)


def main():

    try:
        config.load_incluster_config()
    except Exception:
        return 1

    debug = os.getenv("DEBUG", None)
    if debug:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO

    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(module)s - %(funcName)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=log_level,
    )

    interface_watcher(DEFAULTS)


if __name__ == "__main__":
    exit(main())

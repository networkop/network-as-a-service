#!/usr/bin/env python3
import logging
import os
import yaml
from kubernetes import client, config, watch
from kubernetes.client.rest import ApiException
from collections import namedtuple


log = logging.getLogger(__name__)

crd_config = namedtuple("NaaS", ["group", "version", "namespace", "scheduler_api"])
DEFAULTS = crd_config(
    "network.as.a.service", "v1", "default", "http://schedule/configure"
)


def update_configmaps(event):
    event_object = event["object"]
    event_metadata = event_object["metadata"]
    device_name = event_metadata["name"]
    device_data = event_object["spec"]
    log.info(f"Updating ConfigMap for {event_metadata['name']}")
    if not device_data:
        log.info(f"Empty event, skipping...")
        return

    log.info(f"Creating configmap for {device_name}")
    k8s_api = client.CoreV1Api()
    body = {
        "metadata": {
            "name": device_name,
            "annotations": {"order": "99", "template": "interface.j2"},
            "labels": {"device": device_name, "app": "naas", "type": "model"},
        },
        "data": {"structured-config": yaml.safe_dump(device_data)},
    }

    try:
        k8s_api.read_namespaced_config_map(device_name, event_metadata["namespace"])

        resp = k8s_api.replace_namespaced_config_map(
            device_name, event_metadata["namespace"], body
        )
    except ApiException:
        log.info(f"Configmap {device_name} doesn't exist yet. Creating")
        resp = k8s_api.create_namespaced_config_map(event_metadata["namespace"], body)

    log.info(f"Configmap Updated. status={resp}")
    return resp


def device_watcher(defaults):
    log.info("Watching Device CRDs")
    crds = client.CustomObjectsApi()
    w = watch.Watch()
    for event in w.stream(
        crds.list_cluster_custom_object, defaults.group, defaults.version, "devices"
    ):
        update_configmaps(event)


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

    device_watcher(DEFAULTS)


if __name__ == "__main__":
    exit(main())

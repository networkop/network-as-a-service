#!/usr/bin/env python3
from flask import Flask, request, jsonify
import logging
import base64
import jsonpatch
import copy
import yaml
import re
import os
from kubernetes import client, config

logger = logging.getLogger(__name__)

app = Flask(__name__)

DEFAULT_CM = os.getenv("DEFAULT_CM", "mutate-defaults-cm")
DEFAULT_CM_DATA = "defaults"


class MutateException(Exception):
    pass


def get_defaults():
    logger.info(f"Retrieving ConfigMap with CRD Defaults")
    k8s_api = client.CoreV1Api()
    cm_list = k8s_api.list_config_map_for_all_namespaces(
        field_selector=f"metadata.name={DEFAULT_CM}"
    )
    for cm in cm_list.items:
        if cm.metadata.name == DEFAULT_CM:
            logger.info(f"Retrieved CRD Defaults {cm.data.get(DEFAULT_CM_DATA)}")
            return yaml.safe_load(cm.data.get(DEFAULT_CM_DATA, {}))
    return None


def expand_ranges(ports):
    logger.info(f"Expanding interface range {ports}")
    result = list()
    for port in ports:  # (1, '5-10')
        port = str(port)
        if "/" in port:
            logger.info("Modular chassis are not supported yet")
            raise MutateException("Modular chassis are not supported yet")
        elif not "-" in port:
            result.append(str(port))
        else:  # The case for interface range
            start, end = port.split("-")
            for num in range(int(start), int(end) + 1):
                result.append(str(num))  # ('5')
    logger.debug(f"Expanded port range into {result}")
    return result


def normalize_port_ranges(ports):
    check_ports(ports)
    return expand_ranges(ports)


def check_ports(ports):
    if type(ports) != list:
        raise MutateException(f"Ports must be a list, found type: {type(ports)}")


def normalize_ports(spec):
    logger.info(f"Normalizing ports")
    for device in spec["services"]:
        device["ports"] = normalize_port_ranges(device["ports"])


def set_intf_defaults(spec, defaults):
    logger.info(f"Setting interface defaults")
    for device in spec["services"]:
        for k, v in defaults.get("Interface", {}).items():
            if not k in device:
                device[k] = v


# Borrowed from https://github.com/phenixblue/imageswap-webhook/blob/master/app/imageswap-webhook-deploy.py
@app.route("/", methods=["POST"])
def webhook():

    request_info = request.json
    modified_spec = copy.deepcopy(request_info)
    uid = modified_spec["request"]["uid"]
    workload_type = modified_spec["request"]["kind"]["kind"]
    logger.info(f"Processing {workload_type} request with ID: {uid}")
    logger.debug(f"Original request body: {request_info}")

    # Main mutating logic for Interface resources
    try:
        if workload_type == "Interface":
            defaults = get_defaults()
            set_intf_defaults(modified_spec["request"]["object"]["spec"], defaults)
            normalize_ports(modified_spec["request"]["object"]["spec"])
        logger.debug(f"Modified request body: {request_info}")

        patch = jsonpatch.JsonPatch.from_diff(
            request_info["request"]["object"], modified_spec["request"]["object"]
        )
        logger.info(f"Generated JSONPatch: {patch}")

        admission_response = {
            "allowed": True,
            "uid": request_info["request"]["uid"],
            "patch": base64.b64encode(str(patch).encode()).decode(),
            "patchtype": "JSONPatch",
        }
    except MutateException as e:
        logger.info(f"Caught exception: {e}")
        admission_response = {
            "allowed": False,
            "uid": request_info["request"]["uid"],
            "status": {
                "status": "Failure",
                "message": f"Failed to Mutate the request: \n{e}",
            },
        }

    admissionReview = {"response": admission_response}
    return jsonify(admissionReview)


def main():

    try:
        config.load_incluster_config()
    except Exception:
        return 1

    debug = os.getenv("DEBUG", None)
    if debug:
        log_level = logging.DEBUG
    else:
        log_level = logging.DEBUG

    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(module)s - %(funcName)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=log_level,
    )

    app.run(
        host="0.0.0.0",
        port=443,
        debug=True,
        ssl_context=("/certs/tls.crt", "/certs/tls.key"),
    )


if __name__ == "__main__":
    exit(main())

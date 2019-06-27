#!/usr/bin/env python3
import logging
from flask import Flask, request, jsonify
from kubernetes import client, config
from kubernetes.client.rest import ApiException
import os
import yaml
import base64
import random
import string
from jinja2 import Template


INVENTORY_PATH = "/etc/nornir/data"
SCHEDULER_JOB_TEMPLATE = "scheduler-job.j2"

log = logging.getLogger(__name__)
app = Flask(__name__)


class ScheduleException(Exception):
    pass


def get_current_namespace():
    return open("/var/run/secrets/kubernetes.io/serviceaccount/namespace").read()


def get_configmap(name):
    log.info(f"Reading the configmap {name}")
    k8s_api = client.CoreV1Api()
    try:
        return k8s_api.read_namespaced_config_map(name, get_current_namespace())
    except ApiException as e:
        log.info(f"Caught ApiException when reading configmaps/{name}: {e}")
        return None


def generate_random_suffix():
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=6))


def create_job(inventory_slice):
    api = client.BatchV1Api()
    job_name = "-".join(["job", generate_random_suffix()])
    log.info(f"Creating job {job_name}")

    template_cm_name = os.getenv("SCHEDULER_JOB_TEMPLATE", SCHEDULER_JOB_TEMPLATE)
    template_cm = get_configmap(template_cm_name)

    job_template = template_cm.data.get("template")

    t = Template(job_template)
    job_manifest = t.render(
        job={"name": job_name, "inventory": encode(inventory_slice)}
    )

    return api.create_namespaced_job(
        get_current_namespace(), yaml.safe_load(job_manifest), pretty=True
    )


def response(status, message):
    return jsonify({"status": status, "message": message})


def encode(inventory):
    return base64.b64encode(yaml.safe_dump(inventory).encode()).decode()


def get_inventory():
    log.info(f"Reading the inventory file")
    try:
        with open(INVENTORY_PATH, "r") as file:
            return yaml.safe_load(file.read())
    except:
        return None


def inv_slicer(dictionary, step):
    keys = list(dictionary.keys())
    for i in range(0, len(keys), step):
        yield {x: dictionary[x] for x in keys[i : i + step]}


def schedule(sliced_inventory):
    for inventory_slice in sliced_inventory:
        create_job(inventory_slice)


@app.route("/configure", methods=["POST"])
def webhook():
    log.info(f"Got incoming request from {request.remote_addr}")
    payload = request.get_json(force=True)
    log.info(f"Request JSON payload {payload}")

    step = payload.get("step", os.getenv("STEP", "MAX"))

    devices_inventory = get_inventory()
    if not devices_inventory:
        response("Failed", "Could not locate device inventory")

    if step.lower() == "max":
        step = len(devices_inventory)
    else:
        step = int(step)
    log.info(f"Scheduling {step} devices on a single runner")

    devices = payload.get("devices")
    if not devices:
        response("Failed", "Could not find 'device' key in payload")

    if not "all" in devices:
        log.info(f"Filtering device inventory")
        devices_inventory = {k: v for k, v in devices_inventory.items() if k in devices}
        log.info(f"Filtered inventory contains {devices_inventory.keys()}")

    sliced_inventory = [x for x in inv_slicer(devices_inventory, step)]

    schedule(sliced_inventory)

    return response("OK", "Scheduled")


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

    app.run(host="0.0.0.0", port=80, debug=True)

    return 0


if __name__ == "__main__":
    exit(main())

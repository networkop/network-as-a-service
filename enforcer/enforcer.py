#!/usr/bin/env python3
import logging
from kubernetes import client, config
from nornir.plugins.tasks import networking
from nornir.plugins.functions.text import print_result
from nornir.plugins.tasks.text import template_string
from nornir import InitNornir
import os
import yaml

INVENTORY_PATH = "/etc/nornir/hosts.yaml"
log = logging.getLogger(__name__)


class EnforcerException(Exception):
    pass


def get_current_namespace():
    return open("/var/run/secrets/kubernetes.io/serviceaccount/namespace").read()


def get_configmaps(labels=dict()):
    log.info(f"Retrieving the list of ConfigMaps matching labels {labels}")
    label_selector = ",".join([f"{k}={v}" for k, v in labels.items()])
    k8s_api = client.CoreV1Api()
    cm_list = k8s_api.list_namespaced_config_map(
        get_current_namespace(), label_selector=label_selector
    )
    return cm_list.items


def push_config(task, models, templates):
    log.info(f"Pushing config for device '{task.host}' in group '{task.host.groups}'")

    my_models = [
        m
        for m in models
        if m.metadata.labels.get("device") == task.host.name
        or m.metadata.labels.get("group") in task.host.groups
    ]
    log.info(f"Found device-related modes: {[x.metadata.name for x in my_models]}")

    cli_config = str()

    for ordered_model in sorted(
        my_models, key=lambda x: x.metadata.annotations.get("order", "50")
    ):
        model = yaml.safe_load(ordered_model.data.get("structured-config"))
        template_name = ordered_model.metadata.annotations.get("template")
        log.info(
            f"Processing {template_name} template for model {ordered_model.metadata.name}"
        )
        for template in templates:
            if template.metadata.name == template_name:
                log.info(f"Found a {template_name} template")
                r = task.run(
                    name=f"Building {template_name}",
                    task=template_string,
                    template=template.data.get("template"),
                    model=model,
                )
                cli_config += r.result
                cli_config += "\n"

    if not cli_config:
        log.info(f"No config was generated. Push is skipped.")
        return

    log.debug(f"Configuring device {task.host} with \n{cli_config}")
    task.host["config"] = cli_config

    result = task.run(
        task=networking.napalm_configure,
        replace=True,
        configuration=task.host["config"],
    )

    return result


def adapt_host_data(host):
    host.groups.append("global")


def push_configs():

    nr = InitNornir(
        core={"num_workers": 10},
        inventory={
            "plugin": "nornir.plugins.inventory.simple.SimpleInventory",
            "options": {"host_file": INVENTORY_PATH},
            "transform_function": adapt_host_data,
        },
    )

    log.info(f"Downloading Model configmaps")
    models = get_configmaps(labels={"app": "naas", "type": "model"})
    log.info(f"Found models: {[x.metadata.name for x in models]}")

    log.info(f"Downloading Template configmaps")
    templates = get_configmaps(labels={"app": "naas", "type": "template"})
    log.info(f"Found templates: {[x.metadata.name for x in models]}")

    result = nr.run(task=push_config, models=models, templates=templates)

    log.info(f"Result: \n{print_result(result)}")


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

    try:
        push_configs()
    except EnforcerException as e:
        log.info(f"Caught exception: {e}")


if __name__ == "__main__":
    exit(main())

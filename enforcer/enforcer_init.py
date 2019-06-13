#!/usr/bin/env python3
import logging
import os
import yaml
import base64

INVENTORY_PATH = "/etc/nornir/hosts.yaml"
log = logging.getLogger(__name__)
logging.basicConfig(
    format="%(asctime)s %(levelname)s %(module)s - %(funcName)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO,
)


def main():
    encoded_inv = os.getenv("INVENTORY", "")
    if not encoded_inv:
        log.info(f"Could not find env variable 'INVENTORY'")
        return 1

    decoded_inv = base64.b64decode(encoded_inv)
    inv_yaml = yaml.safe_load(decoded_inv.decode())

    log.info(f"Saving inventory file: \n{inv_yaml}")
    with open(INVENTORY_PATH, "w") as f:
        f.write(yaml.dump(inv_yaml, default_flow_style=False))

    return 0


if __name__ == "__main__":
    exit(main())

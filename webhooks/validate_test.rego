package kubernetes.test_admission

import data.kubernetes.admission

existing_devices = [{
    "devicea": 
    {
    "apiVersion": "network.as.a.service/v1",
    "kind": "Device",
    "metadata": {
        "labels": {
            "app": "naas",
            "device": "devicea",
            "type": "model"
        },
        "name": "devicea",
        "namespace": "default",
    },
    "spec": {
        "1": {
            "annotations": {
                "namespace": "tenant-a",
                "owner": "request-001",
            },
            "shutdown": true,
            "stp": "portfast",
            "trunk": true,
            "vlan": 10
        },
        "10": {
            "annotations": {
                "namespace": "tenant-a",
                "owner": "request-001",
            },
            "shutdown": true,
            "stp": "portfast",
            "trunk": true,
            "vlan": 10
        },
        "14": {
            "annotations": {
                "namespace": "tenant-a",
                "owner": "request-001",
            },
            "shutdown": true,
            "stp": "portfast",
            "trunk": true,
            "vlan": 10
        },
        "16": {
            "annotations": {
                "namespace": "tenant-a",
                "owner": "request-001",
            },
            "shutdown": true,
            "stp": "portfast",
            "trunk": true,
            "vlan": 10
        }
    }
}
}]


bad_request = {
  "kind": "AdmissionReview",
  "apiVersion": "admission.k8s.io/v1beta1",
  "request": {
    "kind": {
      "group": "network.as.a.service",
      "version": "v1",
      "kind": "Interface"
    },
    "resource": {
      "group": "network.as.a.service",
      "version": "v1",
      "resource": "interfaces"
    },
    "namespace": "tenant-b",
    "operation": "CREATE",
    "userInfo": {
      "username": "kubernetes-admin",
      "groups": [
        "system:masters",
        "system:authenticated"
      ]
    },
    "object": {
      "apiVersion": "network.as.a.service/v1",
      "kind": "Interface",
      "metadata": {
        "generation": 1,
        "name": "request-002",
        "namespace": "tenant-b",
      },
      "spec": {
        "services": [
          {
            "devicename": "deviceA",
            "ports": [
              "1",
              "12",
              "13",
              "15",
              "16"
            ],
            "shutdown": true,
            "stp": "portfast",
            "trunk": true,
            "vlan": 1010
          },
          {
            "devicename": "deviceB",
            "ports": [
              "1",
              "11",
              "12"
            ],
            "shutdown": 1,
            "stp": "portfast",
            "trunk": false,
            "vlan": 33
          }
        ]
      }
    },
    "oldObject": null,
    "dryRun": false
  }
}


test_validate {
  count(admission.deny) == 2 with input as bad_request with data.kubernetes.devices as existing_devices
}


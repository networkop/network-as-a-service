package kubernetes.admission

import data.kubernetes.namespaces
import data.kubernetes.devices


deny[msg] {
    input.request.kind.kind == "Interface"
    new_tenant := input.request.namespace
    port := input.request.object.spec.services[i].ports[_]
    new_device := input.request.object.spec.services[i].devicename
    existing_device_data := devices[_][lower(new_device)].spec
    other_tenant := existing_device_data[port].annotations.namespace
    other_request = existing_device_data[port].annotations.owner
    trace(sprintf("This tenant: %v",[new_tenant]))
    trace(sprintf("Other tenant: %v",[other_tenant]))
    not new_tenant == other_tenant
    
    msg := sprintf("Port %v@%v is owned by a different tenant: %v (request %v)", [port, new_device, other_tenant, other_request])
}

[![Docker Pulls](https://img.shields.io/docker/pulls/networkop/naas.svg)](https://img.shields.io/docker/pulls/networkop/naas)

# PoC demonstration of Network-as-a-Service concept

This is a complete end-to-end demo of Network-as-a-Service platform and encompasses all the below demos from other branches.

* [Part 1](https://github.com/networkop/network-as-a-service/tree/part-1) - Building the foundation
* [Part 2](https://github.com/networkop/network-as-a-service/tree/part-2) - Designing a Network API
* [Part 3](https://github.com/networkop/network-as-a-service/tree/part-3) - Authentication and Admission control

![](/img/naas-p3.png)


#### 0. Prepare for OIDC authentication

For this demo, I'll only use a single non-admin user. Before you run the rest of the steps, you need to make sure you've followed [dexter][dexter] to setup google credentials and update OAuth client and user IDs in `kind.yaml`, `dexter-auth.sh` and `oidc/manifest.yaml` files.

#### 1. Build the test topology 

This step assumes you have [docker-topo][docker-topo] installed and c(vEOS) image [built][cveos] and available in local docker registry.

```
make topo
```
This test topology can be any Arista EOS device reachable from the localhost. If using a different test topology, be sure to update the [inventory][inventory] file.

#### 2. Build the Kubernetes cluster

The following step will build a docker-based [kind][kind] cluster with a single control plane and a single worker node.

```
make kubernetes
```

#### 3. Check that the cluster is functional

The following step will build a base docker image and push it to dockerhub. It is assumed that the user has done `docker login` and has his username saved in the `DOCKERHUB_USER` environment variable.

```
export KUBECONFIG="$(kind get kubeconfig-path --name="naas")"
make warmup
kubectl get pod test
```

This is a 100MB image, so it may take a few minutes for test pod to transition from `ContainerCreating` to `Running`

#### 4. Build NaaS platform

The next command will install and configure both mutating and validating admission webhooks, the watcher and scheduler services and all of the required CRDs and configmaps.

```
make build
```

#### 5. Authenticate with Google 

Assuming all files from step 0 have been updated correctly, the following command will open a web browser and prompt you to select a google account to authenticate with.

```
make oidc-build
```

From now on, you should be able to switch to your google-authenticated user like this:

```
kubectl config use-context mk
```

And back to the admin user like this:

```
kubectl config use-context kubernetes-admin@naas
```

#### 6. Test 

To demonstrate how everything works, I'm going to issue three API requests. The [first][cr-first] API request will set up a large range of ports on test switches. 

```
kubectl config use-context mk
kubectl apply -f crds/03_cr.yaml                 
```

The [second][cr-second] API request will try to re-assign some of these ports to a different tenant and will get denied by the validation controller.

```
kubectl config use-context kubernetes-admin@naas
kubectl apply -f crds/04_cr.yaml        
Error from server (Port 11@deviceA is owned by a different tenant: tenant-a (request request-001), Port 12@deviceA is owned by a different tenant: tenant-a (request request-001),
```

The [third][cr-third] API request will update some of the ports from the original request within the same tenant.

```
kubectl config use-context mk
kubectl apply -f crds/05_cr.yaml                 
```

The following result can be observed on one of the switches:

```
devicea#sh run int eth2-3
interface Ethernet2
   description request-002
   shutdown
   switchport trunk allowed vlan 100
   switchport mode trunk
   spanning-tree portfast
interface Ethernet3
   description request-001
   shutdown
   switchport trunk allowed vlan 10
   switchport mode trunk
   spanning-tree portfast
```

### Cleanup

```
make clean
```

[docker-topo]: https://github.com/networkop/docker-topo
[cveos]: https://github.com/networkop/docker-topo/tree/master/topo-extra-files/veos
[kind]: https://github.com/kubernetes-sigs/kind
[cr-first]: crds/03_cr.yaml       
[cr-second]: crds/04_cr.yaml
[cr-third]: crds/05_cr.yaml 
[inventory]: topo/inventory.yaml

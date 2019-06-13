NAAS_NAMESPACE ?= 'default'
KIND_IP ?= $(shell docker inspect naas-worker --format '{{.NetworkSettings.IPAddress}}')

.PHONY: scheduler-build
scheduler-build: scheduler-prep scheduler-install

.PHONY: scheduler-prep
scheduler-prep: enforcer-build
	@echo 'Setting up Traefik'
	@kubectl apply -f https://raw.githubusercontent.com/containous/traefik/v1.7/examples/k8s/traefik-rbac.yaml
	@kubectl apply -f https://raw.githubusercontent.com/containous/traefik/v1.7/examples/k8s/traefik-ds.yaml
	@echo 'Updating static DNS mappings'
	@sed -ri 's/(ip host api.naas).*/\1 ${KIND_IP}/' topo/config/2-node_veos-1
	@sed -ri 's/(ip host api.naas).*/\1 ${KIND_IP}/' topo/config/2-node_veos-2
	@sed -ri 's/(ip host api.naas).*/\1 ${KIND_IP}/' templates/generic.j2

.PHONY: scheduler-install
scheduler-install: scheduler-configure
	@echo 'Installing Scheduler deployment'
	echo "${KIND_IP} api.naas" | sudo tee -a /etc/hosts
	@kubectl apply -f scheduler/manifest.yaml

.PHONY: scheduler-configure
scheduler-configure: 
	@echo 'Uploading device inventory'
	@kubectl create secret generic device-inventory -n ${NAAS_NAMESPACE} \
	--from-file=data=topo/inventory.yaml --dry-run -o yaml | kubectl apply -f -
	@echo 'Uploading generic data model'
	@kubectl create cm generic-cm -n ${NAAS_NAMESPACE} \
	--from-file=structured-config=models/generic.yaml --dry-run -o yaml | kubectl apply -f -
	@echo 'Labeling generic data model'
	@kubectl label cm generic-cm app=naas --overwrite
	@kubectl label cm generic-cm type=model --overwrite
	@kubectl label cm generic-cm group=global --overwrite
	@kubectl annotate cm generic-cm order=00 --overwrite
	@kubectl annotate cm generic-cm template=generic.j2 --overwrite
	@echo 'Uploading generic model template'
	@kubectl create cm generic.j2 -n ${NAAS_NAMESPACE} \
	--from-file=template=templates/generic.j2 --dry-run -o yaml | kubectl apply -f -
	@kubectl label cm generic.j2 app=naas --overwrite
	@kubectl label cm generic.j2 type=template --overwrite
	@echo 'Uploading scheduler script'
	@kubectl create cm scheduler-cm -n ${NAAS_NAMESPACE} \
	--from-file=script=scheduler/scheduler.py --dry-run -o yaml | kubectl apply -f -
	@echo 'Uploading scheduler job template'
	@kubectl create cm scheduler-job.j2 -n ${NAAS_NAMESPACE} \
	--from-file=template=scheduler/job.j2 --dry-run -o yaml | kubectl apply -f -
	

.PHONY: scheduler-clean
scheduler-clean: enforcer-clean
	-kubectl delete -f scheduler/manifest.yaml --force --grace-period=0
	-kubectl delete cm -n ${NAAS_NAMESPACE} scheduler-cm
	-kubectl delete cm -n ${NAAS_NAMESPACE} generic.j2
	-kubectl delete cm -n ${NAAS_NAMESPACE} generic-cm
	-kubectl delete cm -n ${NAAS_NAMESPACE} scheduler-job.j2
	-kubectl delete -f https://raw.githubusercontent.com/containous/traefik/v1.7/examples/k8s/traefik-rbac.yaml
	-kubectl delete -f https://raw.githubusercontent.com/containous/traefik/v1.7/examples/k8s/traefik-ds.yaml
	-sudo sed -i '/api.naas/d' /etc/hosts
	-kubectl delete jobs -n ${NAAS_NAMESPACE} --all
	
.PHONY: scheduler-respin
scheduler-respin: scheduler-clean scheduler-build

.PHONY: scheduler-logs
scheduler-logs:
	kubectl logs deploy/scheduler
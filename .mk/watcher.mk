WATCHER_NAMESPACE := "default"

.PHONY: watcher-build
watcher-build: watcher-prepare watcher-install #watcher-test
	
.PHONY: watcher-test
watcher-test:	
	@kubectl apply -f crds/03_cr.yaml

.PHONY: watcher-prepare
watcher-prepare:
	@kubectl apply -f crds/00_namespace.yaml
	@kubectl apply -f crds/01_crd.yaml

.PHONY: watcher-clean
watcher-clean:
	-@kubectl delete -f crds/03_cr.yaml
	-@kubectl delete cm interface.j2 -n ${WATCHER_NAMESPACE}
	-@kubectl delete cm devicea -n ${WATCHER_NAMESPACE}
	-@kubectl delete cm deviceb -n ${WATCHER_NAMESPACE}
	-@kubectl delete cm watcher-cm -n ${WATCHER_NAMESPACE}
	-@kubectl delete --force --grace-period=0 -f watcher/manifest.yaml
	-@kubectl delete interfaces --all --all-namespaces    
	-@kubectl delete devices --all --all-namespaces       
	-@kubectl delete -f crds/00_namespace.yaml
	-@kubectl delete -f crds/01_crd.yaml

 

.PHONY: watcher-install
watcher-install: watcher-configure docker-build
	@kubectl apply -f watcher/manifest.yaml

.PHONY: watcher-configure
watcher-configure: 
	kubectl create cm interface-watcher-cm -n ${WATCHER_NAMESPACE} \
	--from-file=script=./watcher/interface-watcher.py --dry-run -o yaml | kubectl apply -f -
	kubectl create cm device-watcher-cm -n ${WATCHER_NAMESPACE} \
	--from-file=script=./watcher/device-watcher.py --dry-run -o yaml | kubectl apply -f -
	kubectl create cm interface.j2 -n ${WATCHER_NAMESPACE} \
	--from-file=template=./templates/interface.j2 --dry-run -o yaml | kubectl apply -f -
	kubectl label cm interface.j2 app=naas --overwrite
	kubectl label cm interface.j2 type=template --overwrite


.PHONY: watcher-respin
watcher-respin: watcher-clean watcher-build

.PHONY: watcher-logs
watcher-logs:
	@kubectl logs deploy/interface-watcher
	@kubectl logs deploy/device-watcher
	

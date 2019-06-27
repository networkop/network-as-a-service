NAAS_NAMESPACE ?= 'default'

.PHONY: enforcer-build
enforcer-build: enforcer-install

.PHONY: enforcer-configure
enforcer-configure: 
	kubectl create cm enforcer-cm -n ${NAAS_NAMESPACE} \
	--from-file=script=enforcer/enforcer.py --dry-run -o yaml | kubectl apply -f -
	kubectl create cm enforcer-init-cm -n ${NAAS_NAMESPACE} \
	--from-file=script=enforcer/enforcer_init.py --dry-run -o yaml | kubectl apply -f -

.PHONY: enforcer-install
enforcer-install: enforcer-configure docker-build

.PHONY: enforcer-clean
enforcer-clean: 
	-kubectl delete cm enforcer-cm
	-kubectl delete cm enforcer-init-cm

.PHONY: enforcer-logs
enforcer-logs:
	kubectl logs deploy/enforcer

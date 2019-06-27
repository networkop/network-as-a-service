VALIDATING_NAMESPACE := "opa"
MUTATING_NAMESPACE := "mutate"

.PHONY: admission-build
admission-build: admission-prepare validate-build mutate-build

.PHONY: admission-prepare
admission-prepare: ns-build generate-certs

.PHONY: ns-build
ns-build:
	kubectl apply -f webhooks/namespaces.yaml

.PHONY: validate-build
validate-build: opa-install opa-configure

.PHONY: mutate-build
mutate-build: mutate-install  mutate-configure

.PHONY: admission-clean
admission-clean: opa-clean mutate-clean ns-clean

.PHONY: ns-clean
ns-clean:
	-kubectl delete -f webhooks/namespaces.yaml

.PHONY: generate-certs
generate-certs: ca-bundle validate-certs mutate-certs
	
## Thanks to https://github.com/morvencao/kube-mutating-webhook-tutorial/tree/master/deployment
.PHONY: ca-bundle
ca-bundle:
	cat webhooks/template-webhook.yaml | \
    	webhooks/webhook-create-patch-ca-bundle.sh > \
    	webhooks/webhook-ca-bundle.yaml
	kubectl apply -f webhooks/webhook-ca-bundle.yaml

.PHONY: validate-certs
validate-certs: 
	webhooks/webhook-create-self-signed-cert.sh \
		--service validate \
		--namespace ${VALIDATING_NAMESPACE} \
		--secret validate-secret

.PHONY: mutate-certs
mutate-certs: 
	webhooks/webhook-create-self-signed-cert.sh \
		--service mutate \
		--namespace ${MUTATING_NAMESPACE} \
		--secret mutate-secret

.PHONY: opa-install
opa-install: 
	kubectl apply -f webhooks/validate.yaml


.PHONY: mutate-install
mutate-install: mutate-configure
	kubectl apply -f webhooks/mutate.yaml

.PHONY: opa-configure
opa-configure:
	kubectl create cm opa-default-system-main \
	-n ${VALIDATING_NAMESPACE} --from-file=script=./webhooks/main.rego 
	kubectl create cm validate \
	-n ${VALIDATING_NAMESPACE} --from-file=webhooks/validate.rego \
	--dry-run -o yaml | kubectl apply -f -

.PHONY: mutate-configure
mutate-configure:
	kubectl create cm mutate-webhook-cm \
	-n ${MUTATING_NAMESPACE} --from-file=script=./webhooks/mutate.py \
	--dry-run -o yaml | kubectl apply -f -
	kubectl create cm mutate-defaults-cm \
	-n ${MUTATING_NAMESPACE} --from-file=defaults=./webhooks/defaults.yaml \
	--dry-run -o yaml | kubectl apply -f -


.PHONY: mutate-clean
mutate-clean: 
	-kubectl delete -f webhooks/mutate.yaml \
	--force --grace-period=0

.PHONY: opa-clean
opa-clean: 
	-kubectl delete -f webhooks/validate.yaml \
	--force --grace-period=0

.PHONY: validate-logs
validate-logs: 
	kubectl logs -l app=naas --all-containers -n ${VALIDATING_NAMESPACE}

.PHONY: mutate-logs
mutate-logs: 
	kubectl logs deploy/mutate-webhook -n ${MUTATING_NAMESPACE}

.PHONY: admission-respin
admission-respin: admission-clean admission-build
	
VERSION  ?= latest
TOPOLOGY := topo/2-node.yaml

.DEFAULT_GOAL := help

include .mk/kind.mk
include .mk/docker.mk
include .mk/enforcer.mk
include .mk/scheduler.mk

# thanks to https://marmelab.com/blog/2016/02/29/auto-documented-makefile.html
PHONY: help
help: ## Print help
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

.PHONY: build kubernetes kubernetes-stop clean topo warmup

kubernetes: kind-start ## Create local k8s cluster

kubernetes-stop: kind-stop ## Destroy local k8s cluster

warmup: docker-build ## Warmup kubernetes cluster
	kubectl apply -f test.yaml

topo: ## Build test network topology
	docker-topo --create $(TOPOLOGY)

topo-stop: ## Destroy test network topology
	-docker-topo --destroy $(TOPOLOGY)

build: scheduler-build ## Build project
	black ./

clean: scheduler-clean ## Clean project
	-@kubectl delete --force --grace-period=0 -f test.yaml

.PHONY: oidc-build dexter-configure dexter-unconfigure
oidc-build: dexter-configure
	kubectl apply -f oidc/

dexter-configure:
	./dexter-auth.sh
	@echo 'Run "kubectl config use-context mk" to change user'
	
dexter-unconfigure:
	@echo 'Run "kubectl config use-context kubernetes-admin@naas" to change user'
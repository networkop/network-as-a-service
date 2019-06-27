DOCKERHUB_USER ?= "networkop"
RELEASE ?= "latest"

.PHONY: docker-build
docker-build:
	-@docker build -f docker/Dockerfile -t ${DOCKERHUB_USER}/naas:${RELEASE} ./docker/
	-@docker push ${DOCKERHUB_USER}/naas:${RELEASE}
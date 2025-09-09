PROTOC=protoc

.PHONY: gen
gen:
	$(PROTOC) \
		--go_out=. --go_opt=paths=source_relative \
		--go-grpc_out=. --go-grpc_opt=paths=source_relative \
		services/ingestion/v1/ingestion.proto

.PHONY: run-ingester
run-ingester:
	go run -tags ingester_gen ./cmd/ingester -addr :50051
STACK?=dev-indexer
STACK_FILE?=deploy/docker-stack.yml

.PHONY: swarm-init swarm-deploy swarm-ps swarm-rm

swarm-init:
	@docker info --format '{{.Swarm.LocalNodeState}}' | grep -q 'active' \
		|| (echo 'Initializing Docker Swarm...' && docker swarm init)

swarm-deploy:
	@docker stack deploy -c $(STACK_FILE) $(STACK)

swarm-ps:
	@docker stack services $(STACK)

swarm-rm:
	@docker stack rm $(STACK)

# Image build/push helpers
REGISTRY?=ghcr.io/zen-glow
IMAGE?=dev-indexer-app
TAG?=latest

.PHONY: image-build image-push

image-build:
	@docker build --build-arg PYTHON_VERSION=3.12 -t $(REGISTRY)/$(IMAGE):$(TAG) .

image-push:
	@docker push $(REGISTRY)/$(IMAGE):$(TAG)

# --- Proto codegen (Go/Python/TS) ---
.PHONY: proto-go proto-py proto-ts proto-all

PROTO_SRC=protos/canonical.proto services/router/v1/router.proto services/ingestion/v1/ingestion.proto

proto-go:
	@protoc \
		--go_out=. --go_opt=paths=source_relative \
		--go-grpc_out=. --go-grpc_opt=paths=source_relative \
		$(PROTO_SRC)

proto-py:
	@python -m pip show grpcio-tools >/dev/null 2>&1 || python -m pip install grpcio-tools mypy-protobuf
	@python -m grpc_tools.protoc -I. \
		--python_out=. --grpc_python_out=. \
		--mypy_out=. \
		$(PROTO_SRC)

proto-ts:
	@echo "TODO: configure ts-proto or protoc-gen-ts in dashboard/ and run generation"

proto-all: proto-go proto-py proto-ts


# --- Workers ---
.PHONY: cce-worker

cce-worker:
	@python scripts/cce_event_worker.py
# Codegen for local stubs into internal/gen

PROTO_DIR=../../protos
OUT_DIR=internal/gen

all: gen-go

.PHONY: gen-go

gen-go:
	mkdir -p $(OUT_DIR)
	protoc -I $(PROTO_DIR) \
	  --go_out=$(OUT_DIR) --go_opt=paths=source_relative \
	  --go-grpc_out=$(OUT_DIR) --go-grpc_opt=paths=source_relative \
	  $(PROTO_DIR)/services/logging/v1/logging.proto

.PHONY: tools
tools:
	go generate ./...

.PHONY: run
run:
	@mkdir -p bin
	@if [ ! -x bin/logservice ]; then \
		$(MAKE) gen-go; \
		go build -o bin/logservice ./cmd/logservice; \
	fi
	@echo "running logservice on $${ADDR:-:50051}"
	@./bin/logservice -addr "$${ADDR:-:50051}"

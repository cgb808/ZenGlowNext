# Codegen tools and stubs (pinned)

# Install protoc plugins as pinned versions
.PHONY: tools
Tools:
	go generate ./...

# Generate stubs into internal/gen from protos/
PROTO_DIR=../protos
OUT_DIR=internal/gen
# Only generate router service protos to avoid package name conflicts
PROTO_FILES := $(PROTO_DIR)/services/router/v1/router.proto

.PHONY: gen-go
Gen-go:
		mkdir -p $(OUT_DIR)
		protoc -I $(PROTO_DIR) \
			--go_out=$(OUT_DIR) --go_opt=paths=source_relative \
			--go-grpc_out=$(OUT_DIR) --go-grpc_opt=paths=source_relative \
			$(PROTO_FILES)

.PHONY: run
run:
	@mkdir -p bin
	@if [ ! -x bin/router ]; then \
		$(MAKE) Gen-go; \
		go build -o bin/router ./cmd/router; \
	fi
	@echo "running router on $${ADDR:-:50052}"
	@./bin/router -addr "$${ADDR:-:50052}"

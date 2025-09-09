//go:build tools
// +build tools

// Pin protoc plugins for reproducible builds.
// Use:  go generate ./...

package tools

//go:generate go install google.golang.org/protobuf/cmd/protoc-gen-go@v1.34.1
//go:generate go install google.golang.org/grpc/cmd/protoc-gen-go-grpc@v1.4.0

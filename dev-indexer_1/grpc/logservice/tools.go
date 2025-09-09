//go:build tools
// +build tools

// This file pins code generation tool versions in go.mod and enables
// reproducible protoc plugin installs via `go generate`.
//
// Run from this module directory:
//   go generate ./...
//
// Or use the Makefile target:
//   make tools

//go:generate go install google.golang.org/protobuf/cmd/protoc-gen-go@v1.34.1
//go:generate go install google.golang.org/grpc/cmd/protoc-gen-go-grpc@v1.4.0

package tools

import (
    _ "google.golang.org/protobuf/cmd/protoc-gen-go"
    _ "google.golang.org/grpc/cmd/protoc-gen-go-grpc"
)

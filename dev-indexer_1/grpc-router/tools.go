//go:build tools
// +build tools

// Pin protoc plugins for reproducible builds.
// Use:  go generate ./...

package main

import (
	// These imports are used by go mod to ensure the protoc plugins are available
	_ "google.golang.org/grpc/cmd/protoc-gen-go-grpc"
	_ "google.golang.org/protobuf/cmd/protoc-gen-go"
)

//go:generate go install google.golang.org/protobuf/cmd/protoc-gen-go@v1.34.1
//go:generate go install google.golang.org/grpc/cmd/protoc-gen-go-grpc@v1.4.0

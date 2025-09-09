package main

import (
	"context"
	"log/slog"
	"net"
	"os"
	"os/signal"
	"syscall"
	"time"

	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/health"
	"google.golang.org/grpc/health/grpc_health_v1"
	"google.golang.org/grpc/keepalive"
	"google.golang.org/grpc/reflection"
	"google.golang.org/grpc/status"

	loggingv1 "github.com/cgb808/ZenGlowNext/grpc/logservice/internal/gen/services/logging/v1"
	"github.com/cgb808/ZenGlowNext/grpc/logservice/internal/server"
)

func main() {
	// Structured logger
	logger := slog.New(slog.NewJSONHandler(os.Stdout, nil))

	lis, err := net.Listen("tcp", ":50051")
	if err != nil {
		logger.Error("failed to listen", "error", err)
		os.Exit(1)
	}

	// Interceptors and keepalive
	serverOptions := []grpc.ServerOption{
		grpc.ChainUnaryInterceptor(
			LoggingUnaryInterceptor(logger),
			RecoveryUnaryInterceptor(logger),
		),
		grpc.ChainStreamInterceptor(
			LoggingStreamInterceptor(logger),
			RecoveryStreamInterceptor(logger),
		),
		grpc.KeepaliveParams(keepalive.ServerParameters{
			MaxConnectionIdle: 5 * time.Minute,
			Timeout:           10 * time.Second,
			MaxConnectionAge:  1 * time.Hour,
		}),
	}

	grpcServer := grpc.NewServer(serverOptions...)

	// Services
	ls := server.NewLogServer()
	loggingv1.RegisterLogServiceServer(grpcServer, ls)

	// Health + reflection
	healthServer := health.NewServer()
	grpc_health_v1.RegisterHealthServer(grpcServer, healthServer)
	reflection.Register(grpcServer)

	go func() {
		logger.Info("logservice listening", "address", lis.Addr().String())
		// Report SERVING for overall server and service name
		healthServer.SetServingStatus("", grpc_health_v1.HealthCheckResponse_SERVING)
		healthServer.SetServingStatus("logging.v1.LogService", grpc_health_v1.HealthCheckResponse_SERVING)
		if err := grpcServer.Serve(lis); err != nil {
			logger.Error("failed to serve", "error", err)
		}
	}()

	// Graceful shutdown
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit
	logger.Info("shutting down server...")
	healthServer.SetServingStatus("", grpc_health_v1.HealthCheckResponse_NOT_SERVING)
	healthServer.SetServingStatus("logging.v1.LogService", grpc_health_v1.HealthCheckResponse_NOT_SERVING)
	grpcServer.GracefulStop()
	logger.Info("server gracefully stopped")
}

// --- Interceptors ---

func RecoveryUnaryInterceptor(logger *slog.Logger) grpc.UnaryServerInterceptor {
	return func(ctx context.Context, req interface{}, info *grpc.UnaryServerInfo, handler grpc.UnaryHandler) (interface{}, error) {
		defer func() {
			if r := recover(); r != nil {
				logger.Error("panic recovered", "method", info.FullMethod, "panic", r)
			}
		}()
		return handler(ctx, req)
	}
}

func LoggingUnaryInterceptor(logger *slog.Logger) grpc.UnaryServerInterceptor {
	return func(ctx context.Context, req interface{}, info *grpc.UnaryServerInfo, handler grpc.UnaryHandler) (interface{}, error) {
		start := time.Now()
		resp, err := handler(ctx, req)
		dur := time.Since(start)
		st, _ := status.FromError(err)
		code := codes.OK
		if st != nil {
			code = st.Code()
		}
		logger.Info("grpc unary",
			"method", info.FullMethod,
			"duration_ms", dur.Milliseconds(),
			"code", code.String(),
		)
		return resp, err
	}
}

func RecoveryStreamInterceptor(logger *slog.Logger) grpc.StreamServerInterceptor {
	return func(srv interface{}, ss grpc.ServerStream, info *grpc.StreamServerInfo, handler grpc.StreamHandler) error {
		defer func() {
			if r := recover(); r != nil {
				logger.Error("panic recovered", "method", info.FullMethod, "panic", r)
			}
		}()
		return handler(srv, ss)
	}
}

func LoggingStreamInterceptor(logger *slog.Logger) grpc.StreamServerInterceptor {
	return func(srv interface{}, ss grpc.ServerStream, info *grpc.StreamServerInfo, handler grpc.StreamHandler) error {
		start := time.Now()
		err := handler(srv, ss)
		dur := time.Since(start)
		st, _ := status.FromError(err)
		code := codes.OK
		if st != nil {
			code = st.Code()
		}
		logger.Info("grpc stream",
			"method", info.FullMethod,
			"duration_ms", dur.Milliseconds(),
			"code", code.String(),
		)
		return err
	}
}

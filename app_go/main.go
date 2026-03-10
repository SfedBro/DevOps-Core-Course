package main

import (
	"encoding/json"
	"fmt"
	"net"
	"net/http"
	"os"
	"runtime"
	"time"
)

type Service struct {
	Name        string `json:"name"`
	Version     string `json:"version"`
	Description string `json:"description"`
	Framework   string `json:"framework"`
}

type System struct {
	Hostname     string `json:"hostname"`
	Platform     string `json:"platform"`
	Architecture string `json:"architecture"`
	CPUCount     int    `json:"cpu_count"`
	GoVersion    string `json:"go_version"`
}

type RuntimeInfo struct {
	UptimeSeconds int64  `json:"uptime_seconds"`
	UptimeHuman   string `json:"uptime_human"`
	CurrentTime   string `json:"current_time"`
	Timezone      string `json:"timezone"`
}

type RequestInfo struct {
	ClientIP  string `json:"client_ip"`
	UserAgent string `json:"user_agent"`
	Method    string `json:"method"`
	Path      string `json:"path"`
}

type Endpoint struct {
	Path        string `json:"path"`
	Method      string `json:"method"`
	Description string `json:"description"`
}

type ServiceInfo struct {
	Service   Service     `json:"service"`
	System    System      `json:"system"`
	Runtime   RuntimeInfo `json:"runtime"`
	Request   RequestInfo `json:"request"`
	Endpoints []Endpoint  `json:"endpoints"`
}

var startTime = time.Now().UTC()

type responseWriter struct {
	http.ResponseWriter
	statusCode int
}

func (rw *responseWriter) WriteHeader(code int) {
	rw.statusCode = code
	rw.ResponseWriter.WriteHeader(code)
}

func logEvent(level string, message string, fields map[string]interface{}) {
	payload := map[string]interface{}{
		"timestamp": time.Now().UTC().Format(time.RFC3339Nano),
		"level":     level,
		"message":   message,
		"service":   "devops-go",
	}

	for key, value := range fields {
		payload[key] = value
	}

	if err := json.NewEncoder(os.Stdout).Encode(payload); err != nil {
		fmt.Fprintf(os.Stderr, "{\"level\":\"ERROR\",\"message\":\"failed to encode log\",\"error\":%q}\n", err.Error())
	}
}

func mainHandler(w http.ResponseWriter, r *http.Request) {
	uptimeSeconds := int64(time.Since(startTime).Seconds())
	hours := uptimeSeconds / 3600
	minutes := (uptimeSeconds % 3600) / 60

	hostname, err := os.Hostname()
	if err != nil {
		logEvent("ERROR", "failed to resolve hostname", map[string]interface{}{
			"event": "hostname_error",
			"error": err.Error(),
		})
		hostname = "unknown"
	}

	clientIP, _, err := net.SplitHostPort(r.RemoteAddr)
	if err != nil {
		logEvent("ERROR", "failed to parse client ip", map[string]interface{}{
			"event": "client_ip_error",
			"error": err.Error(),
		})
		clientIP = r.RemoteAddr
	}

	resp := ServiceInfo{
		Service: Service{
			Name:        "devops-info-service",
			Version:     "1.0.0",
			Description: "DevOps course info service",
			Framework:   "Go net/http",
		},
		Runtime: RuntimeInfo{
			UptimeSeconds: uptimeSeconds,
			UptimeHuman:   formatUptime(hours, minutes),
			CurrentTime:   time.Now().UTC().Format(time.RFC3339),
			Timezone:      "UTC",
		},
		System: System{
			Hostname:     hostname,
			Platform:     runtime.GOOS,
			Architecture: runtime.GOARCH,
			CPUCount:     runtime.NumCPU(),
			GoVersion:    runtime.Version(),
		},
		Request: RequestInfo{
			ClientIP:  clientIP,
			UserAgent: r.Header.Get("User-Agent"),
			Method:    r.Method,
			Path:      r.URL.Path,
		},
		Endpoints: []Endpoint{
			{Path: "/", Method: "GET", Description: "Service information"},
			{Path: "/health", Method: "GET", Description: "Health check"},
		},
	}

	w.Header().Set("Content-Type", "application/json")
	if err := json.NewEncoder(w).Encode(resp); err != nil {
		logEvent("ERROR", "failed to encode response", map[string]interface{}{
			"event": "response_encode_error",
			"error": err.Error(),
		})
	}
}

func healthHandler(w http.ResponseWriter, r *http.Request) {
	uptimeSeconds := int64(time.Since(startTime).Seconds())

	resp := map[string]interface{}{
		"status":         "healthy",
		"timestamp":      time.Now().UTC().Format(time.RFC3339),
		"uptime_seconds": uptimeSeconds,
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(resp)
}

func formatUptime(hours int64, minutes int64) string {
	return fmt.Sprintf("%d hours, %d minutes", hours, minutes)
}

func loggingMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		started := time.Now()
		writer := &responseWriter{ResponseWriter: w, statusCode: http.StatusOK}
		next.ServeHTTP(writer, r)

		clientIP, _, err := net.SplitHostPort(r.RemoteAddr)
		if err != nil {
			clientIP = r.RemoteAddr
		}

		level := "INFO"
		if writer.statusCode >= http.StatusInternalServerError {
			level = "ERROR"
		} else if writer.statusCode >= http.StatusBadRequest {
			level = "WARN"
		}

		logEvent(level, "request completed", map[string]interface{}{
			"event":       "http_request",
			"method":      r.Method,
			"path":        r.URL.Path,
			"status_code": writer.statusCode,
			"client_ip":   clientIP,
			"duration_ms": time.Since(started).Milliseconds(),
		})
	})
}

func main() {
	host := os.Getenv("HOST")
	if host == "" {
		host = "0.0.0.0"
	}

	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	mux := http.NewServeMux()
	mux.HandleFunc("/", mainHandler)
	mux.HandleFunc("/health", healthHandler)

	addr := host + ":" + port
	logEvent("INFO", "application startup", map[string]interface{}{
		"event": "startup",
		"host":  host,
		"port":  port,
	})
	err := http.ListenAndServe(addr, loggingMiddleware(mux))
	if err != nil {
		logEvent("ERROR", "server failed", map[string]interface{}{
			"event": "server_error",
			"error": err.Error(),
		})
	}
}

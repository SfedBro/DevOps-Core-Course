package main

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"
)

func TestFormatUptime(t *testing.T) {
	cases := []struct {
		hours   int64
		minutes int64
		want    string
	}{
		{0, 0, "0 hours, 0 minutes"},
		{1, 30, "1 hours, 30 minutes"},
		{5, 59, "5 hours, 59 minutes"},
	}

	for _, c := range cases {
		got := formatUptime(c.hours, c.minutes)
		if got != c.want {
			t.Errorf("formatUptime(%d, %d) = %q, want %q", c.hours, c.minutes, got, c.want)
		}
	}
}

func TestMainHandler(t *testing.T) {
	req := httptest.NewRequest("GET", "/", nil)
	req.RemoteAddr = "127.0.0.1:12345"
	req.Header.Set("User-Agent", "GoTestClient")
	w := httptest.NewRecorder()

	mainHandler(w, req)

	resp := w.Result()
	if resp.StatusCode != http.StatusOK {
		t.Errorf("expected status 200, got %d", resp.StatusCode)
	}

	var si ServiceInfo
	if err := json.NewDecoder(resp.Body).Decode(&si); err != nil {
		t.Fatalf("failed to decode JSON: %v", err)
	}

	if si.Service.Name != "devops-info-service" {
		t.Errorf("unexpected service name: %s", si.Service.Name)
	}

	if si.Request.ClientIP != "127.0.0.1" {
		t.Errorf("unexpected client IP: %s", si.Request.ClientIP)
	}

	if si.Request.UserAgent != "GoTestClient" {
		t.Errorf("unexpected UserAgent: %s", si.Request.UserAgent)
	}

	if len(si.Endpoints) != 2 {
		t.Errorf("expected 2 endpoints, got %d", len(si.Endpoints))
	}
}

func TestHealthHandler(t *testing.T) {
	req := httptest.NewRequest("GET", "/health", nil)
	w := httptest.NewRecorder()

	healthHandler(w, req)

	resp := w.Result()
	if resp.StatusCode != http.StatusOK {
		t.Errorf("expected status 200, got %d", resp.StatusCode)
	}

	var body map[string]interface{}
	if err := json.NewDecoder(resp.Body).Decode(&body); err != nil {
		t.Fatalf("failed to decode JSON: %v", err)
	}

	if body["status"] != "healthy" {
		t.Errorf("unexpected status: %v", body["status"])
	}

	if _, ok := body["uptime_seconds"]; !ok {
		t.Errorf("uptime_seconds missing in response")
	}
}

func TestHandlersTiming(t *testing.T) {
	startTime = time.Now().UTC().Add(-time.Hour*2 - time.Minute*15) // симулируем аптайм 2ч 15м

	req := httptest.NewRequest("GET", "/", nil)
	req.RemoteAddr = "127.0.0.1:12345"
	w := httptest.NewRecorder()

	mainHandler(w, req)

	var si ServiceInfo
	if err := json.NewDecoder(w.Body).Decode(&si); err != nil {
		t.Fatalf("failed to decode JSON: %v", err)
	}

	if !strings.HasPrefix(si.Runtime.UptimeHuman, "2 hours") {
		t.Errorf("unexpected uptime human: %s", si.Runtime.UptimeHuman)
	}
}

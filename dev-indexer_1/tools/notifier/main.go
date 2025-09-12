package main

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"io"
	"net/http"
	"os"
	"strings"
	"text/template"
	"time"
)

type ReqTemplate struct {
	Method  string            `json:"method"`
	URL     string            `json:"url"`
	Headers map[string]string `json:"headers"`
	Body    any               `json:"body"`
}

func toJSON(v any) (string, error) {
	b, err := json.Marshal(v)
	if err != nil {
		return "", err
	}
	return string(b), nil
}

func dict(kv ...any) (map[string]any, error) {
	if len(kv)%2 != 0 {
		return nil, errors.New("dict requires even number of args")
	}
	m := make(map[string]any, len(kv)/2)
	for i := 0; i < len(kv); i += 2 {
		k, ok := kv[i].(string)
		if !ok {
			return nil, errors.New("dict keys must be strings")
		}
		m[k] = kv[i+1]
	}
	return m, nil
}

func loadTemplate(path string) (*template.Template, error) {
	b, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	coalesce := func(args ...any) any {
		for _, a := range args {
			if a == nil {
				continue
			}
			switch v := a.(type) {
			case string:
				if v != "" {
					return v
				}
			case int:
				if v != 0 {
					return v
				}
			case int64:
				if v != 0 {
					return v
				}
			case float64:
				if v != 0 {
					return v
				}
			case bool:
				if v {
					return v
				}
			default:
				return v
			}
		}
		return nil
	}
	return template.New("req").Funcs(template.FuncMap{
		"env":      os.Getenv,
		"now":      time.Now,
		"join":     strings.Join,
		"epoch":    func() int64 { return time.Now().Unix() },
		"tojson":   toJSON,
		"dict":     dict,
		"coalesce": coalesce,
	}).Parse(string(b))
}

func renderTemplate(t *template.Template, data map[string]any) (*ReqTemplate, error) {
	var buf bytes.Buffer
	if err := t.Execute(&buf, data); err != nil {
		return nil, err
	}
	var rt ReqTemplate
	if err := json.Unmarshal(buf.Bytes(), &rt); err != nil {
		return nil, fmt.Errorf("template did not render valid JSON: %w", err)
	}
	if rt.Method == "" || rt.URL == "" {
		return nil, errors.New("template must define method and url")
	}
	return &rt, nil
}

func doRequest(ctx context.Context, rt *ReqTemplate, timeout time.Duration) (int, []byte, error) {
	var body io.Reader
	if rt.Body != nil {
		b, err := json.Marshal(rt.Body)
		if err != nil {
			return 0, nil, fmt.Errorf("marshal body: %w", err)
		}
		body = bytes.NewReader(b)
	}
	req, err := http.NewRequestWithContext(ctx, strings.ToUpper(rt.Method), rt.URL, body)
	if err != nil {
		return 0, nil, err
	}
	for k, v := range rt.Headers {
		req.Header.Set(k, v)
	}
	if req.Header.Get("Content-Type") == "" && rt.Body != nil {
		req.Header.Set("Content-Type", "application/json")
	}
	client := &http.Client{Timeout: timeout}
	resp, err := client.Do(req)
	if err != nil {
		return 0, nil, err
	}
	defer resp.Body.Close()
	rb, _ := io.ReadAll(resp.Body)
	return resp.StatusCode, rb, nil
}

func main() {
	var (
		tplPath    = flag.String("template", "", "Path to request template (Go text/template rendering to JSON)")
		dataJSON   = flag.String("data", "{}", "JSON object with template data")
		timeoutS   = flag.Int("timeout", 10, "HTTP timeout seconds")
		require2xx = flag.Bool("require-2xx", true, "Exit non-zero if status is not 2xx")
		verbose    = flag.Bool("v", false, "Verbose logging")
	)
	flag.Parse()
	if *tplPath == "" {
		fmt.Fprintln(os.Stderr, "-template is required")
		os.Exit(2)
	}
	var data map[string]any
	if err := json.Unmarshal([]byte(*dataJSON), &data); err != nil {
		fmt.Fprintf(os.Stderr, "invalid -data JSON: %v\n", err)
		os.Exit(2)
	}
	t, err := loadTemplate(*tplPath)
	if err != nil {
		fmt.Fprintf(os.Stderr, "load template: %v\n", err)
		os.Exit(1)
	}
	rt, err := renderTemplate(t, data)
	if err != nil {
		fmt.Fprintf(os.Stderr, "render: %v\n", err)
		os.Exit(1)
	}
	if *verbose {
		enc, _ := json.Marshal(rt)
		fmt.Fprintf(os.Stderr, "request: %s\n", string(enc))
	}
	ctx, cancel := context.WithTimeout(context.Background(), time.Duration(*timeoutS)*time.Second)
	defer cancel()
	status, body, err := doRequest(ctx, rt, time.Duration(*timeoutS)*time.Second)
	if err != nil {
		fmt.Fprintf(os.Stderr, "http error: %v\n", err)
		os.Exit(1)
	}
	if *verbose {
		fmt.Fprintf(os.Stderr, "status=%d body=%s\n", status, string(body))
	} else {
		fmt.Println(status)
	}
	if *require2xx && (status < 200 || status >= 300) {
		os.Exit(1)
	}
}

package main

import (
	"context"
	"crypto/ecdsa"
	"crypto/elliptic"
	"crypto/rand"
	"crypto/tls"
	"crypto/x509"
	"crypto/x509/pkix"
	"encoding/json"
	"encoding/pem"
	"math/big"
	"net"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"testing"
	"time"
)

type testPKI struct {
	caPEM      []byte
	caCert     *x509.Certificate
	caKey      *ecdsa.PrivateKey
	clientCert string
	clientKey  string
	caFile     string
	serverTLS  tls.Certificate
}

func newTestPKI(t *testing.T) *testPKI {
	t.Helper()
	dir := t.TempDir()
	caKey, _ := ecdsa.GenerateKey(elliptic.P256(), rand.Reader)
	caTpl := &x509.Certificate{
		SerialNumber:          big.NewInt(1),
		Subject:               pkix.Name{CommonName: "test-ca"},
		NotBefore:             time.Now().Add(-time.Hour),
		NotAfter:              time.Now().Add(time.Hour),
		IsCA:                  true,
		KeyUsage:              x509.KeyUsageCertSign | x509.KeyUsageDigitalSignature,
		BasicConstraintsValid: true,
	}
	caDER, _ := x509.CreateCertificate(rand.Reader, caTpl, caTpl, &caKey.PublicKey, caKey)
	caCert, _ := x509.ParseCertificate(caDER)
	caPEM := pem.EncodeToMemory(&pem.Block{Type: "CERTIFICATE", Bytes: caDER})

	issue := func(cn string, ips []net.IP, client bool) ([]byte, []byte) {
		key, _ := ecdsa.GenerateKey(elliptic.P256(), rand.Reader)
		usage := x509.ExtKeyUsageServerAuth
		if client {
			usage = x509.ExtKeyUsageClientAuth
		}
		tpl := &x509.Certificate{
			SerialNumber: big.NewInt(time.Now().UnixNano()),
			Subject:      pkix.Name{CommonName: cn, OrganizationalUnit: []string{"tm-ou"}},
			NotBefore:    time.Now().Add(-time.Hour),
			NotAfter:     time.Now().Add(time.Hour),
			KeyUsage:     x509.KeyUsageDigitalSignature,
			ExtKeyUsage:  []x509.ExtKeyUsage{usage},
			IPAddresses:  ips,
		}
		der, _ := x509.CreateCertificate(rand.Reader, tpl, caCert, &key.PublicKey, caKey)
		keyDER, _ := x509.MarshalECPrivateKey(key)
		return pem.EncodeToMemory(&pem.Block{Type: "CERTIFICATE", Bytes: der}),
			pem.EncodeToMemory(&pem.Block{Type: "EC PRIVATE KEY", Bytes: keyDER})
	}

	clientPEM, clientKeyPEM := issue("tm-client", nil, true)
	serverPEM, serverKeyPEM := issue("127.0.0.1", []net.IP{net.ParseIP("127.0.0.1")}, false)
	serverTLS, _ := tls.X509KeyPair(serverPEM, serverKeyPEM)

	p := &testPKI{caPEM: caPEM, caCert: caCert, caKey: caKey, serverTLS: serverTLS}
	p.clientCert = filepath.Join(dir, "client.crt")
	p.clientKey = filepath.Join(dir, "client.key")
	p.caFile = filepath.Join(dir, "ca.crt")
	os.WriteFile(p.clientCert, clientPEM, 0o644)
	os.WriteFile(p.clientKey, clientKeyPEM, 0o600)
	os.WriteFile(p.caFile, caPEM, 0o644)
	return p
}

func (p *testPKI) mtlsServer(t *testing.T, handler http.Handler) *httptest.Server {
	t.Helper()
	pool := x509.NewCertPool()
	pool.AppendCertsFromPEM(p.caPEM)
	ts := httptest.NewUnstartedServer(handler)
	ts.TLS = &tls.Config{
		Certificates: []tls.Certificate{p.serverTLS},
		ClientCAs:    pool,
		ClientAuth:   tls.RequireAndVerifyClientCert,
	}
	ts.StartTLS()
	t.Cleanup(ts.Close)
	return ts
}

func TestBuildCSClientDefaultWithoutConfig(t *testing.T) {
	if buildCSClient(&Config{}) != http.DefaultClient {
		t.Fatal("unconfigured cert paths must fall back to the default client")
	}
}

func TestBuildCSClientFallbackOnUnreadablePaths(t *testing.T) {
	cfg := &Config{
		CrowdSecClientCert: "/nonexistent/c.crt",
		CrowdSecClientKey:  "/nonexistent/c.key",
		CrowdSecCACert:     "/nonexistent/ca.crt",
	}
	if buildCSClient(cfg) != http.DefaultClient {
		t.Fatal("unreadable cert files must fall back instead of crashing the agent")
	}
}

func TestBuildCSClientLoadsCertAndCA(t *testing.T) {
	p := newTestPKI(t)
	c := buildCSClient(&Config{
		CrowdSecClientCert: p.clientCert,
		CrowdSecClientKey:  p.clientKey,
		CrowdSecCACert:     p.caFile,
	})
	if c == http.DefaultClient {
		t.Fatal("valid cert config must build a dedicated client")
	}
	tcfg := c.Transport.(*http.Transport).TLSClientConfig
	if len(tcfg.Certificates) != 1 {
		t.Fatalf("client certificate not loaded, got %d", len(tcfg.Certificates))
	}
	if tcfg.RootCAs == nil {
		t.Fatal("CA pool not loaded")
	}
}

func TestCSHasMachineViaCertAlone(t *testing.T) {
	a := &App{cfg: &Config{CrowdSecClientCert: "/c.crt", CrowdSecClientKey: "/c.key"}}
	if !a.csHasMachine() {
		t.Fatal("a client cert pair must count as machine-capable")
	}
	a = &App{cfg: &Config{CrowdSecClientCert: "/c.crt"}}
	if a.csHasMachine() {
		t.Fatal("a cert without its key must not count")
	}
}

func TestCSRequestOverMTLS(t *testing.T) {
	p := newTestPKI(t)
	var sawKeyHeader string
	ts := p.mtlsServer(t, http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		sawKeyHeader = r.Header.Get("X-Api-Key")
		w.Write([]byte(`[]`))
	}))
	cfg := &Config{
		CrowdSecLAPIURL:    ts.URL,
		CrowdSecClientCert: p.clientCert,
		CrowdSecClientKey:  p.clientKey,
		CrowdSecCACert:     p.caFile,
	}
	a := &App{cfg: cfg, csClient: buildCSClient(cfg)}
	resp, err := a.csRequest(context.Background(), http.MethodGet, "/v1/decisions", nil, false)
	if err != nil {
		t.Fatalf("cert-only request against an mTLS LAPI failed: %v", err)
	}
	resp.Body.Close()
	if resp.StatusCode != 200 {
		t.Fatalf("expected 200, got %d", resp.StatusCode)
	}
	if sawKeyHeader != "" {
		t.Fatalf("no API key is configured, none must be sent, got %q", sawKeyHeader)
	}

	bare := &App{cfg: &Config{CrowdSecLAPIURL: ts.URL}, csClient: http.DefaultClient}
	if _, err := bare.csRequest(context.Background(), http.MethodGet, "/v1/decisions", nil, false); err == nil {
		t.Fatal("a client without the cert must be rejected by the mTLS server")
	}
}

func TestCSGetJWTCertOnlyOmitsCredentials(t *testing.T) {
	p := newTestPKI(t)
	var loginBody map[string]any
	ts := p.mtlsServer(t, http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		json.NewDecoder(r.Body).Decode(&loginBody)
		json.NewEncoder(w).Encode(map[string]string{
			"token":  "tok",
			"expire": time.Now().Add(time.Hour).Format(time.RFC3339),
		})
	}))
	cfg := &Config{
		CrowdSecLAPIURL:    ts.URL,
		CrowdSecClientCert: p.clientCert,
		CrowdSecClientKey:  p.clientKey,
		CrowdSecCACert:     p.caFile,
	}
	a := &App{cfg: cfg, csClient: buildCSClient(cfg)}
	csJWT, csJWTExpiry = "", time.Time{}
	defer func() { csJWT, csJWTExpiry = "", time.Time{} }()
	tok, err := a.csGetJWT(context.Background())
	if err != nil || tok != "tok" {
		t.Fatalf("cert-only login failed: tok=%q err=%v", tok, err)
	}
	if _, has := loginBody["machine_id"]; has {
		t.Fatal("cert-only login must not send machine_id")
	}
	if _, has := loginBody["password"]; has {
		t.Fatal("cert-only login must not send a password")
	}
}

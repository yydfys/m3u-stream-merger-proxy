import sys
content = open('config/config.go').read()

# 1. Data paths + DNS_SERVER + SSL_SKIP_VERIFY (InsecureSkipVerify) + UA
content = content.replace(
    'var globalConfig = &Config{\n\tDataPath: "/m3u-proxy/data/",\n\tTempPath: "/tmp/m3u-proxy/",\n}',
    'var globalConfig = &Config{\n\tDataPath: "/m3u-proxy/data/",\n\tTempPath: "/tmp/m3u-proxy/",\n}\n'
    'func init() {\n'
    '\tif d := os.Getenv("DATA_DIR"); d != "" {\n'
    '\t\tglobalConfig.DataPath = d\n'
    '\t}\n'
    '\tif t := os.Getenv("TEMP_DIR"); t != "" {\n'
    '\t\tglobalConfig.TempPath = t\n'
    '\t}\n'
    '\tif dns := os.Getenv("DNS_SERVER"); dns != "" {\n'
    '\t\tnet.DefaultResolver = &net.Resolver{\n'
    '\t\t\tPreferGo: true,\n'
    '\t\t\tDial: func(ctx context.Context, network, address string) (net.Conn, error) {\n'
    '\t\t\t\tvar d net.Dialer\n'
    '\t\t\t\treturn d.DialContext(ctx, "udp", dns)\n'
    '\t\t\t},\n'
    '\t\t}\n'
    '\t}\n'
    '\tif os.Getenv("SSL_VERIFY") == "false" {\n'
    '\t\thttp.DefaultTransport.(*http.Transport).TLSClientConfig = &tls.Config{InsecureSkipVerify: true}\n'
    '\t}\n'
    '\tua := os.Getenv("HTTP_USER_AGENT")\n'
    '\tif ua == "" {\n'
    '\t\tua = "okhttp/4.12.0"\n'
    '\t}\n'
    '\thttp.DefaultTransport = &uaTransport{inner: http.DefaultTransport, ua: ua}\n'
    '}\n\n'
    'type uaTransport struct {\n'
    '\tinner http.RoundTripper\n'
    '\tua    string\n'
    '}\n\n'
    'func (t *uaTransport) RoundTrip(req *http.Request) (*http.Response, error) {\n'
    '\tif req.Header.Get("User-Agent") == "" {\n'
    '\t\treq.Header.Set("User-Agent", t.ua)\n'
    '\t}\n'
    '\treturn t.inner.RoundTrip(req)\n'
    '}'
)

# 2. Add imports
content = content.replace(
    '\t"os"\n',
    '\t"os"\n\t"context"\n\t"crypto/tls"\n\t"net"\n\t"net/http"\n'
)

open('config/config.go', 'w').write(content)
print("patch OK")

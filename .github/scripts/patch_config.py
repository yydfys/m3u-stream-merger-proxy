import sys, os

# Get working directory from either GITHUB_WORKSPACE or CWD
repo_root = os.environ.get('GITHUB_WORKSPACE', '.')
os.chdir(repo_root)

# ============================================================
# 1. PATCH config.go - add init() with env var overrides
# ============================================================
content = open('config/config.go').read()

# Replace var globalConfig (NO semicolons after &Config)
old = 'var globalConfig = &Config{\n\tDataPath: "/m3u-proxy/data/",\n\tTempPath: "/tmp/m3u-proxy/",\n}'
new = (
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
    '\tua string\n'
    '}\n\n'
    'func (t *uaTransport) RoundTrip(req *http.Request) (*http.Response, error) {\n'
    '\tif req.Header.Get("User-Agent") == "" {\n'
    '\t\treq.Header.Set("User-Agent", t.ua)\n'
    '\t}\n'
    '\treturn t.inner.RoundTrip(req)\n'
    '}'
)

if old not in content:
    print("ERROR: config.go does not contain expected string!")
    print("Looking for:", repr(old[:80]))
    sys.exit(1)

content = content.replace(old, new)

# Add imports: context, crypto/tls, net, net/http
# Upstream format: "os\n\t"  (tab before "os")
content = content.replace('\t"os"\n', '\t"os"\n\t"context"\n\t"crypto/tls"\n\t"net"\n\t"net/http"\n')

open('config/config.go', 'w').write(content)
print("config.go: patched OK")

# ============================================================
# 2. PATCH parser.go - formatStreamEntry for OUTPUT_DIRECT_URLS
# ============================================================
parser = open('sourceproc/parser.go').read()
old_call = '\tentry.WriteString(GenerateStreamURL(baseURL, stream))\n'
new_call = (
    '\tif os.Getenv("OUTPUT_DIRECT_URLS") == "true" {\n'
    '\t\tvar origUrl string\n'
    '\t\tstream.URLs.Range(func(_ string, innerMap map[string]string) bool {\n'
    '\t\t\tfor _, srcUrl := range innerMap {\n'
    '\t\t\t\tparts := strings.SplitN(srcUrl, ":::", 2)\n'
    '\t\t\t\tif len(parts) == 2 {\n'
    '\t\t\t\t\torigUrl = parts[1]\n'
    '\t\t\t\t\treturn false\n'
    '\t\t\t\t}\n'
    '\t\t\t}\n'
    '\t\t\treturn true\n'
    '\t\t})\n'
    '\t\tif origUrl != "" {\n'
    '\t\t\tentry.WriteString(origUrl)\n'
    '\t\t\tentry.WriteString("\\n")\n'
    '\t\t\treturn entry.String()\n'
    '\t\t}\n'
    '\t}\n'
    '\tentry.WriteString(GenerateStreamURL(baseURL, stream))\n'
)

if old_call not in parser:
    print("ERROR: parser.go does not contain expected call!")
    sys.exit(1)

parser = parser.replace(old_call, new_call)
open('sourceproc/parser.go', 'w').write(parser)
print("parser.go: patched OK")

print("ALL PATCHES APPLIED SUCCESSFULLY")

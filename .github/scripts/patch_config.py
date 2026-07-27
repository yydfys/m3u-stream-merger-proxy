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
# 3. Patch helpers.go - add OUTPUT_DIRECT_URLS support
helpers_path = 'sourceproc/helpers.go'
helpers = open(helpers_path).read()

old_fn = 'func GenerateStreamURL(baseUrl string, stream *StreamInfo) string {'
new_fn = 'func GenerateStreamURL(baseUrl string, stream *StreamInfo) string {'

new_fn += '\n\tif os.Getenv("OUTPUT_DIRECT_URLS") == "true" {'
new_fn += '\n\t\tvar originalUrl string'
new_fn += '\n\t\tif stream.URLs != nil {'
new_fn += '\n\t\t\tstream.URLs.Range(func(_ string, innerMap map[string]string) bool {'
new_fn += '\n\t\t\tfor _, srcUrl := range innerMap {'
new_fn += '\n\t\t\t\tparts := strings.SplitN(srcUrl, ":::", 2)'
new_fn += '\n\t\t\t\tif len(parts) == 2 {'
new_fn += '\n\t\t\t\t\toriginalUrl = parts[1]'
new_fn += '\n\t\t\t\t\treturn false'
new_fn += '\n\t\t\t\t}'
new_fn += '\n\t\t\t}'
new_fn += '\n\t\t\treturn true'
new_fn += '\n\t\t})'
new_fn += '\n\t\tif originalUrl != "" {'
new_fn += '\n\t\t\treturn originalUrl'
new_fn += '\n\t\t}'
new_fn += '\n\t}'

helpers = helpers.replace(old_fn, new_fn)

if '"os"' not in helpers:
    helpers = helpers.replace('import (', 'import (\n\t"os"')

open(helpers_path, 'w').write(helpers)

print("patch OK")

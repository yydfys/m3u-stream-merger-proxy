import sys

# 1. Config.go patches
content = open('config/config.go').read()

content = content.replace(
    'var globalConfig = &Config;{\n\tDataPath: "/m3u-proxy/data/",\n\tTempPath: "/tmp/m3u-proxy/",\n}',
    'var globalConfig = &Config;{\n\tDataPath: "/m3u-proxy/data/",\n\tTempPath: "/tmp/m3u-proxy/",\n}\n'
    'func init() {\n'
    '\tif d := os.Getenv("DATA_DIR"); d != "" {\n'
    '\t\tglobalConfig.DataPath = d\n'
    '\t}\n'
    '\tif t := os.Getenv("TEMP_DIR"); t != "" {\n'
    '\t\tglobalConfig.TempPath = t\n'
    '\t}\n'
    '\tif dns := os.Getenv("DNS_SERVER"); dns != "" {\n'
    '\t\tnet.DefaultResolver = &net.Resolver;{\n'
    '\t\t\tPreferGo: true,\n'
    '\t\t\tDial: func(ctx context.Context, network, address string) (net.Conn, error) {\n'
    '\t\t\t\tvar d net.Dialer\n'
    '\t\t\t\treturn d.DialContext(ctx, "udp", dns)\n'
    '\t\t\t},\n'
    '\t\t}\n'
    '\t}\n'
    '\tif os.Getenv("SSL_VERIFY") == "false" {\n'
    '\t\thttp.DefaultTransport.(*http.Transport).TLSClientConfig = &tls.Config;{InsecureSkipVerify: true}\n'
    '\t}\n'
    '\tua := os.Getenv("HTTP_USER_AGENT")\n'
    '\tif ua == "" {\n'
    '\t\tua = "okhttp/4.12.0"\n'
    '\t}\n'
    '\thttp.DefaultTransport = &uaTransport;{inner: http.DefaultTransport, ua: ua}\n'
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

content = content.replace(
    '\t"os"\n',
    '\t"os"\n\t"context"\n\t"crypto/tls"\n\t"net"\n\t"net/http"\n'
)

open('config/config.go', 'w').write(content)

# 2. Patch parser.go - formatStreamEntry for OUTPUT_DIRECT_URLS
parser_path = 'sourceproc/parser.go'
parser = open(parser_path).read()

# Before calling GenerateStreamURL, check for OUTPUT_DIRECT_URLS
old_call = '\tentry.WriteString(GenerateStreamURL(baseURL, stream))\n'
new_call = (
    '\tif os.Getenv("OUTPUT_DIRECT_URLS") == "true" {'
    '\n\t\tvar origUrl string'
    '\n\t\tstream.URLs.Range(func(_ string, innerMap map[string]string) bool {'
    '\n\t\t\tfor _, srcUrl := range innerMap {'
    '\n\t\t\t\tparts := strings.SplitN(srcUrl, ":::", 2)'
    '\n\t\t\t\tif len(parts) == 2 {'
    '\n\t\t\t\t\torigUrl = parts[1]'
    '\n\t\t\t\t\treturn false'
    '\n\t\t\t\t}'
    '\n\t\t\t}'
    '\n\t\t\treturn true'
    '\n\t\t})'
    '\n\t\tif origUrl != "" {'
    '\n\t\t\tentry.WriteString(origUrl)'
    '\n\t\t\tentry.WriteString("\\n")'
    '\n\t\t\treturn entry.String()'
    '\n\t\t}'
    '\n\t}'
    '\tentry.WriteString(GenerateStreamURL(baseURL, stream))\n'
)

parser = parser.replace(old_call, new_call)
open(parser_path, 'w').write(parser)

# 3. Remove old OUTPUT_DIRECT_URLS patch from helpers.go (keep the file clean)
helpers_path = 'sourceproc/helpers.go'
helpers = open(helpers_path).read()

# Remove the old patch from GenerateStreamURL
old_patch = '\n\tif os.Getenv("OUTPUT_DIRECT_URLS") == "true" {'
old_patch += '\n\t\tvar originalUrl string'
old_patch += '\n\t\tif stream.URLs != nil {'
old_patch += '\n\t\t\tstream.URLs.Range(func(_ string, innerMap map[string]string) bool {'
old_patch += '\n\t\t\t\tfor _, srcUrl := range innerMap {'
old_patch += '\n\t\t\t\t\tparts := strings.SplitN(srcUrl, ":::", 2)'
old_patch += '\n\t\t\t\t\tif len(parts) == 2 {'
old_patch += '\n\t\t\t\t\t\toriginalUrl = parts[1]'
old_patch += '\n\t\t\t\t\t\treturn false'
old_patch += '\n\t\t\t\t\t}'
old_patch += '\n\t\t\t\t}'
old_patch += '\n\t\t\t\treturn true'
old_patch += '\n\t\t\t})'
old_patch += '\n\t\t}'
old_patch += '\n\t\tif originalUrl != "" {'
old_patch += '\n\t\t\treturn originalUrl'
old_patch += '\n\t\t}'
old_patch += '\n\t}'

# Check if the old patch exists
if old_patch in helpers:
    helpers = helpers.replace(old_patch, '')
    print("helpers.go: old patch REMOVED")
else:
    print("helpers.go: old patch NOT FOUND (may already be removed)")

open(helpers_path, 'w').write(helpers)
print("patch OK")

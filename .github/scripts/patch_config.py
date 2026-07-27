import sys, re
content = open('config/config.go').read()

# 1. Add init() with DATA_DIR + DNS_SERVER support
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
    '}'
)

# 2. Add "context" and "net" to imports
content = content.replace(
    '\t"os"\n',
    '\t"os"\n\t"context"\n\t"net"\n'
)

open('config/config.go', 'w').write(content)
print("patch OK")

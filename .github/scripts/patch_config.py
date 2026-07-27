import sys
content = open('config/config.go').read()
content = content.replace(
    'var globalConfig = &Config{\n\tDataPath: "/m3u-proxy/data/",\n\tTempPath: "/tmp/m3u-proxy/",\n}',
    'var globalConfig = &Config{\n\tDataPath: "/m3u-proxy/data/",\n\tTempPath: "/tmp/m3u-proxy/",\n}\nfunc init() {\n\tif d := os.Getenv("DATA_DIR"); d != "" {\n\t\tglobalConfig.DataPath = d\n\t}\n\tif t := os.Getenv("TEMP_DIR"); t != "" {\n\t\tglobalConfig.TempPath = t\n\t}\n}'
)
open('config/config.go', 'w').write(content)
print("patch OK")

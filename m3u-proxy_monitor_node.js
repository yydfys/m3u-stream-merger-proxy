// m3u-proxy 监控更新脚本
// 纯 Node.js 内置模块，零外部依赖
// 运行在 TVBox lab 环境 (Node.js)
// 检查 fork 仓库 release，下载最新 ARM64 二进制，更新私目录

const https = require('https');
const http = require('http');
const fs = require('fs');
const path = require('path');
const zlib = require('zlib');
const { execFileSync } = require('child_process');

// ==================== 配置 ====================
const CONFIG = {
  // GitHub
  GH_OWNER: 'yydfys',
  GH_REPO: 'm3u-stream-merger-proxy',
  // 本地路径
  LAB_DIR: '/storage/emulated/0/VodPlus/m3u-proxy',    // 私目录
  BIN_NAME: 'm3u-proxy-arm64',
  VERSION_FILE: 'version.txt',
  LOG_FILE: 'm3u-proxy_monitor.log',
  // 下载
  DOWNLOAD_TIMEOUT: 60000,
  // 推送
  PUSH_URL: 'http://127.0.0.1:9978/api/qpush',          // lab qpush API
  PUSH_TOKEN: '',
};

// ==================== 日志 ====================
function log(msg) {
  const ts = new Date().toISOString().replace('T', ' ').slice(0, 19);
  const line = `[${ts}] ${msg}`;
  console.log(line);
  try {
    const logPath = path.join(CONFIG.LAB_DIR, CONFIG.LOG_FILE);
    fs.appendFileSync(logPath, line + '\n');
  } catch(e) {}
}

// ==================== HTTP 请求 ====================
function httpsGet(url, timeout) {
  return new Promise((resolve, reject) => {
    const isHttps = url.startsWith('https');
    const mod = isHttps ? https : http;
    const req = mod.get(url, { timeout: timeout || 30000 }, (res) => {
      const chunks = [];
      res.on('data', c => chunks.push(c));
      res.on('end', () => {
        const data = Buffer.concat(chunks);
        resolve({ status: res.statusCode, headers: res.headers, data });
      });
    });
    req.on('error', reject);
    req.on('timeout', () => { req.destroy(); reject(new Error('timeout')); });
  });
}

// ==================== GitHub API ====================
async function getLatestRelease() {
  const url = `https://api.github.com/repos/${CONFIG.GH_OWNER}/${CONFIG.GH_REPO}/releases/latest`;
  const res = await httpsGet(url);
  if (res.status !== 200) {
    const text = res.data.toString();
    // Try listing tags instead
    const tagsUrl = `https://api.github.com/repos/${CONFIG.GH_OWNER}/${CONFIG.GH_REPO}/tags?per_page=5`;
    const tagsRes = await httpsGet(tagsUrl);
    if (tagsRes.status !== 200) {
      throw new Error(`GitHub API error: ${tagsRes.status}`);
    }
    const tags = JSON.parse(tagsRes.data.toString());
    if (!tags || tags.length === 0) {
      throw new Error('No tags found');
    }
    // Return the latest tag info
    return { tag_name: tags[0].name, assets: [] };
  }
  return JSON.parse(res.data.toString());
}

async function getReleaseByTag(tag) {
  const url = `https://api.github.com/repos/${CONFIG.GH_OWNER}/${CONFIG.GH_REPO}/releases/tags/${tag}`;
  const res = await httpsGet(url);
  if (res.status !== 200) return null;
  return JSON.parse(res.data.toString());
}

// ==================== 版本比对 ====================
function getLocalVersion() {
  const vPath = path.join(CONFIG.LAB_DIR, CONFIG.VERSION_FILE);
  try {
    return fs.readFileSync(vPath, 'utf8').trim();
  } catch(e) {
    return '';
  }
}

function saveLocalVersion(ver) {
  const vPath = path.join(CONFIG.LAB_DIR, CONFIG.VERSION_FILE);
  fs.writeFileSync(vPath, ver + '\n');
}

// ==================== 下载二进制 ====================
async function downloadBinary(url, destPath) {
  log(`Downloading: ${url}`);
  const res = await httpsGet(url, CONFIG.DOWNLOAD_TIMEOUT);
  if (res.status !== 200 && res.status !== 302) {
    throw new Error(`Download failed: HTTP ${res.status}`);
  }
  // Ensure parent dir exists
  const dir = path.dirname(destPath);
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
  fs.writeFileSync(destPath, res.data);
  fs.chmodSync(destPath, 0o755);
  const size = fs.statSync(destPath).size;
  log(`Downloaded: ${(size / 1024 / 1024).toFixed(2)} MB`);
  return size;
}

// ==================== 检查并更新 ====================
async function checkAndUpdate() {
  log('=== m3u-proxy 更新检查 ===');

  // 1. 获取最新 release
  let latest;
  try {
    latest = await getLatestRelease();
  } catch(e) {
    log(`获取 release 失败: ${e.message}`);
    return;
  }

  const newTag = latest.tag_name || '';
  if (!newTag) {
    log('没有找到最新版本号');
    return;
  }

  const currentVer = getLocalVersion();
  log(`本地版本: "${currentVer}" → 远程版本: "${newTag}"`);

  if (newTag === currentVer) {
    log('已是最新版本，跳过');
    return;
  }

  // 2. 找二进制 assets
  let downloadUrl = '';
  if (latest.assets && latest.assets.length > 0) {
    const asset = latest.assets.find(a => a.name && a.name.includes('arm64'));
    if (asset) downloadUrl = asset.browser_download_url;
  }

  // 如果 release 没有 asset，从 fork 的 tag source 构建（由 Actions 自动完成）
  // 这里我们等 Actions 构建完成后，从 Actions artifact 获取
  // 简化方案：提示用户手动触发 Actions
  if (!downloadUrl) {
    log(`版本 ${newTag} 还没有 ARM64 二进制，触发 Actions 构建...`);
    // 尝试通过 API 触发 workflow
    const triggerUrl = `https://api.github.com/repos/${CONFIG.GH_OWNER}/${CONFIG.GH_REPO}/actions/workflows/build-arm64.yml/dispatches`;
    // 注意：这里需要 GH_TOKEN 来触发，但手机上没有
    // 所以这里只输出提示，让用户手动在 GitHub 上点 "Run workflow"
    log(`请前往 GitHub Actions 手动触发构建:`);
    log(`  https://github.com/${CONFIG.GH_OWNER}/${CONFIG.GH_REPO}/actions`);
    log(`  点击 "Build ARM64 Binary" → "Run workflow"`);

    // 或者我们可以等一会再检查
    log(`等待 60 秒后重新检查...`);
    await new Promise(r => setTimeout(r, 60000));
    
    // 重新检查 release
    const retryRelease = await getReleaseByTag(newTag);
    if (retryRelease && retryRelease.assets) {
      const asset = retryRelease.assets.find(a => a.name && a.name.includes('arm64'));
      if (asset) downloadUrl = asset.browser_download_url;
    }
  }

  if (!downloadUrl) {
    log('仍无可用二进制，跳过本次更新');
    return;
  }

  // 3. 下载二进制
  const binPath = path.join(CONFIG.LAB_DIR, CONFIG.BIN_NAME);
  try {
    await downloadBinary(downloadUrl, binPath);
  } catch(e) {
    log(`下载失败: ${e.message}`);
    return;
  }

  // 4. 验证
  if (!fs.existsSync(binPath)) {
    log('下载后文件不存在！更新失败');
    return;
  }

  // 5. 保存版本
  saveLocalVersion(newTag);
  log(`✅ 更新完成: ${currentVer || '无'} → ${newTag}`);

  // 6. 推送通知
  await pushNotify(newTag);
}

// ==================== 推送 ====================
async function pushNotify(version) {
  const title = '📡 m3u-proxy 已更新';
  const body = `版本: ${version}\n路径: ${CONFIG.LAB_DIR}/${CONFIG.BIN_NAME}\n请重启服务生效`;

  try {
    const postData = JSON.stringify({
      title: title,
      content: body,
      token: CONFIG.PUSH_TOKEN
    });

    const url = new URL(CONFIG.PUSH_URL);
    const mod = url.protocol === 'https:' ? https : http;
    const options = {
      hostname: url.hostname,
      port: url.port || (url.protocol === 'https:' ? 443 : 80),
      path: url.pathname,
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(postData)
      }
    };

    await new Promise((resolve, reject) => {
      const req = mod.request(options, (res) => {
        resolve();
      });
      req.on('error', reject);
      req.write(postData);
      req.end();
    });
    log('推送通知发送成功');
  } catch(e) {
    log(`推送失败: ${e.message}`);
  }
}

// ==================== 主入口 ====================
async function main() {
  log('m3u-proxy 监控脚本启动');
  try {
    await checkAndUpdate();
  } catch(e) {
    log(`错误: ${e.message}\n${e.stack}`);
  }
  log('=== 检查完成 ===');
}

main();

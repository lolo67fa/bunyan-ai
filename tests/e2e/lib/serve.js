// Minimal static server for the app under test (index.html, style.css, app.js),
// plus /architecture.json for the harness fixture.
// Playwright starts it through `webServer` in playwright.config.js.
// Each test gets a fresh browser context, so localStorage never leaks between tests.

const http = require('http');
const fs = require('fs');
const path = require('path');
const { appDir, architecturePath, isHarnessFixture } = require('./requirements');

const ROOT = appDir();
const PORT = Number(process.env.PORT || 4317);
const TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
};

if (!fs.existsSync(path.join(ROOT, 'index.html'))) {
  console.error(`APP_DIR has no index.html: ${ROOT}`);
  process.exit(1);
}

http
  .createServer((req, res) => {
    const urlPath = decodeURIComponent(new URL(req.url, 'http://x').pathname);
    // The harness fixture renders the architecture given to the suite. A generated app
    // is served exactly as it is.
    const architecture = architecturePath();
    if (urlPath === '/architecture.json' && isHarnessFixture() && architecture && fs.existsSync(architecture)) {
      res.writeHead(200, { 'Content-Type': TYPES['.json'], 'Cache-Control': 'no-store' });
      fs.createReadStream(architecture).pipe(res);
      return;
    }
    const file = path.resolve(ROOT, '.' + (urlPath.endsWith('/') ? urlPath + 'index.html' : urlPath));
    if (!file.startsWith(ROOT + path.sep) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) {
      res.writeHead(404).end('Not found');
      return;
    }
    res.writeHead(200, { 'Content-Type': TYPES[path.extname(file)] || 'application/octet-stream', 'Cache-Control': 'no-store' });
    fs.createReadStream(file).pipe(res);
  })
  .listen(PORT, '127.0.0.1', () => console.log(`Serving ${ROOT} on http://127.0.0.1:${PORT}`));

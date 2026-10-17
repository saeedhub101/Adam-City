const { app, BrowserWindow } = require('electron');
const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');

let server;
let mainWindow;
const distDir = path.resolve(__dirname, '..', 'dist');
const mimeTypes = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.webp': 'image/webp',
  '.svg': 'image/svg+xml',
  '.woff2': 'font/woff2',
  '.glb': 'model/gltf-binary',
  '.gltf': 'model/gltf+json',
  '.bin': 'application/octet-stream'
};

function startAssetServer() {
  server = http.createServer((req, res) => {
    let requestPath;
    try {
      requestPath = decodeURIComponent(new URL(req.url, 'http://127.0.0.1').pathname);
    } catch {
      res.writeHead(400).end('Bad request');
      return;
    }
    if (requestPath === '/') requestPath = '/index.html';
    const resolved = path.resolve(distDir, '.' + requestPath);
    if (!resolved.startsWith(distDir + path.sep) && resolved !== path.join(distDir, 'index.html')) {
      res.writeHead(403).end('Forbidden');
      return;
    }
    fs.readFile(resolved, (error, data) => {
      if (error) {
        res.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' }).end('Not found');
        return;
      }
      res.writeHead(200, {
        'Content-Type': mimeTypes[path.extname(resolved).toLowerCase()] || 'application/octet-stream',
        'Cache-Control': 'no-cache',
        'X-Content-Type-Options': 'nosniff'
      });
      res.end(data);
    });
  });
  return new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(0, '127.0.0.1', () => {
      server.removeListener('error', reject);
      resolve(server.address().port);
    });
  });
}

async function createWindow() {
  const port = await startAssetServer();
  mainWindow = new BrowserWindow({
    width: 1440,
    height: 900,
    minWidth: 980,
    minHeight: 650,
    backgroundColor: '#111820',
    title: 'Saeed Open World',
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: true
    }
  });
  await mainWindow.loadURL('http://127.0.0.1:' + port + '/');
  mainWindow.on('closed', () => { mainWindow = null; });
}

app.whenReady().then(createWindow).catch(error => {
  console.error('Failed to launch Saeed Open World:', error);
  app.quit();
});
app.on('window-all-closed', () => app.quit());
app.on('before-quit', () => {
  if (server) server.close();
});

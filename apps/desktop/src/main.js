const { app, BrowserWindow, shell, Menu, Tray, nativeImage, ipcMain } = require("electron");
const path = require("path");
const { exec, spawn } = require("child_process");
const http = require("http");

// ─── Config ────────────────────────────────────────────────────────────────────

const WEB_URL = "http://localhost:3000";
const BACKEND_URL = "http://localhost:8000";
const isDev = process.argv.includes("--dev");

let mainWindow = null;
let tray = null;
let backendReady = false;

// ─── Check if server is up ────────────────────────────────────────────────────

function waitForServer(url, timeout = 30000) {
  return new Promise((resolve, reject) => {
    const start = Date.now();
    const check = () => {
      http.get(url, (res) => {
        if (res.statusCode < 500) resolve();
        else setTimeout(check, 500);
      }).on("error", () => {
        if (Date.now() - start > timeout) reject(new Error(`Server not ready: ${url}`));
        else setTimeout(check, 500);
      });
    };
    check();
  });
}

// ─── Create window ────────────────────────────────────────────────────────────

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 820,
    minWidth: 800,
    minHeight: 600,
    titleBarStyle: "hiddenInset",   // macOS native traffic lights
    trafficLightPosition: { x: 16, y: 16 },
    backgroundColor: "#ffffff",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
    show: false,
    icon: path.join(__dirname, "..", "build", "icon.png"),
  });

  // Show loading page first
  mainWindow.loadURL("data:text/html," + encodeURIComponent(loadingHTML()));

  // Wait for web server and then load app
  waitForServer(WEB_URL)
    .then(() => {
      mainWindow.loadURL(WEB_URL);
      mainWindow.once("ready-to-show", () => {
        mainWindow.show();
        if (isDev) mainWindow.webContents.openDevTools();
      });
    })
    .catch(() => {
      mainWindow.loadURL("data:text/html," + encodeURIComponent(errorHTML()));
      mainWindow.show();
    });

  // Open external links in browser, not Electron
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: "deny" };
  });

  mainWindow.on("closed", () => { mainWindow = null; });
}

// ─── Tray ─────────────────────────────────────────────────────────────────────

function createTray() {
  // Use a template image (16x16 or 22x22 for macOS)
  const iconPath = path.join(__dirname, "..", "build", "tray-icon.png");
  let trayIcon;
  try {
    trayIcon = nativeImage.createFromPath(iconPath);
  } catch {
    trayIcon = nativeImage.createEmpty();
  }

  tray = new Tray(trayIcon);
  tray.setToolTip("OpenMarvis");
  const menu = Menu.buildFromTemplate([
    { label: "打开 OpenMarvis", click: () => { if (mainWindow) mainWindow.show(); else createWindow(); } },
    { type: "separator" },
    { label: "退出", role: "quit" },
  ]);
  tray.setContextMenu(menu);
  tray.on("click", () => { if (mainWindow) mainWindow.show(); });
}

// ─── App events ───────────────────────────────────────────────────────────────

app.whenReady().then(() => {
  // macOS dock icon
  if (process.platform === "darwin") {
    app.dock.setIcon(path.join(__dirname, "..", "build", "icon.png"));
  }

  createWindow();
  createTray();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
    else if (mainWindow) mainWindow.show();
  });
});

app.on("window-all-closed", () => {
  // Keep running in tray on macOS
  if (process.platform !== "darwin") app.quit();
});

// Prevent multiple instances
const gotLock = app.requestSingleInstanceLock();
if (!gotLock) {
  app.quit();
} else {
  app.on("second-instance", () => {
    if (mainWindow) { mainWindow.show(); mainWindow.focus(); }
  });
}

// ─── HTML templates ───────────────────────────────────────────────────────────

function loadingHTML() {
  return `<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  html, body { height: 100%; background: #fff; font-family: -apple-system, sans-serif; }
  .c { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100vh; gap: 16px; }
  .logo { width: 72px; height: 72px; border-radius: 18px; background: #111; display: flex; align-items: center; justify-content: center; }
  .spinner { width: 20px; height: 20px; border: 2.5px solid #e5e7eb; border-top-color: #111; border-radius: 50%; animation: spin .8s linear infinite; }
  @keyframes spin { to { transform: rotate(360deg); } }
  h1 { font-size: 20px; font-weight: 700; color: #111; }
  p { font-size: 13px; color: #9ca3af; }
</style>
</head>
<body>
<div class="c">
  <div class="logo">
    <svg width="42" height="42" viewBox="0 0 100 100" fill="none">
      <path d="M62,16 C65,10 70,9 72,14 C70,18 66,20 63,22 C67,26 70,32 70,40 C70,50 64,58 56,62 C52,64 48,66 46,70 C44,74 44,80 48,82 C52,84 56,82 58,78 C60,74 60,68 62,64 C68,60 74,52 74,42 C74,32 70,24 64,18 Z" fill="white"/>
      <path d="M36,30 C34,24 36,16 42,14 C48,12 56,14 60,20 C64,26 63,36 58,42 C54,46 48,48 42,46 C36,44 32,38 36,30 Z" fill="white"/>
      <path d="M36,42 C32,44 26,46 24,52 C22,58 26,64 32,64 C36,64 40,62 42,58 C44,54 42,48 38,44 Z" fill="white"/>
      <path d="M58,14 L62,6 L68,12 L64,16 Z" fill="white"/>
      <circle cx="50" cy="26" r="3.5" fill="#111"/>
    </svg>
  </div>
  <h1>OpenMarvis</h1>
  <p>正在启动，请稍候…</p>
  <div class="spinner"></div>
</div>
</body>
</html>`;
}

function errorHTML() {
  return `<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  html, body { height: 100%; background: #fff; font-family: -apple-system, sans-serif; }
  .c { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100vh; gap: 14px; text-align: center; padding: 40px; }
  h1 { font-size: 18px; font-weight: 700; color: #111; }
  p { font-size: 13px; color: #6b7280; line-height: 1.7; max-width: 320px; }
  code { background: #f3f4f6; padding: 2px 6px; border-radius: 4px; font-size: 12px; }
  button { margin-top: 8px; padding: 10px 24px; border-radius: 10px; background: #111; color: #fff; border: none; font-size: 13px; font-weight: 600; cursor: pointer; }
</style>
</head>
<body>
<div class="c">
  <h1>无法连接到 OpenMarvis</h1>
  <p>请先启动后端和 Web 服务，然后点击重试：</p>
  <p>
    后端：<code>cd apps/backend && uvicorn openmarvis.main:app --reload</code><br/>
    Web：<code>cd apps/web && npm run dev</code>
  </p>
  <button onclick="location.reload()">重试</button>
</div>
</body>
</html>`;
}

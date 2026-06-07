const { app, BrowserWindow, shell, Menu, Tray, nativeImage } = require("electron");
const path  = require("path");
const http  = require("http");
const { spawn } = require("child_process");
const fs    = require("fs");

// ─── Paths ────────────────────────────────────────────────────────────────────

// apps/desktop/src/main.js  →  3 levels up = project root
const PROJECT  = path.resolve(__dirname, "..", "..", "..");
const BACKEND  = path.join(PROJECT, "apps", "backend");
const WEB      = path.join(PROJECT, "apps", "web");
const UVICORN  = path.join(BACKEND, ".venv", "bin", "uvicorn");
const LOG_DIR  = path.join(PROJECT, ".logs");

const WEB_URL  = "http://localhost:3000";
const HEALTH   = "http://127.0.0.1:8000/healthz";

let mainWindow   = null;
let tray         = null;
let backendProc  = null;
let frontendProc = null;

// ─── Logging ─────────────────────────────────────────────────────────────────

fs.mkdirSync(LOG_DIR, { recursive: true });
function logStream(name) {
  return fs.createWriteStream(path.join(LOG_DIR, `${name}.log`), { flags: "a" });
}

// ─── Port check ───────────────────────────────────────────────────────────────

function portOpen(url) {
  return new Promise((resolve) => {
    http.get(url, (r) => resolve(r.statusCode < 500))
        .on("error", () => resolve(false));
  });
}

function waitFor(url, timeoutMs = 60000) {
  return new Promise((resolve, reject) => {
    const start = Date.now();
    const tick = () => {
      http.get(url, (r) => {
        if (r.statusCode < 500) { resolve(); return; }
        reschedule();
      }).on("error", reschedule);
    };
    const reschedule = () => {
      if (Date.now() - start > timeoutMs) reject(new Error(`Timeout: ${url}`));
      else setTimeout(tick, 700);
    };
    tick();
  });
}

// ─── Start services ───────────────────────────────────────────────────────────

async function startBackend() {
  if (await portOpen(HEALTH)) {
    console.log("[desktop] backend already running");
    return;
  }
  if (!fs.existsSync(UVICORN)) {
    throw new Error(`uvicorn not found at ${UVICORN}\nRun: cd ${PROJECT} && make install`);
  }
  backendProc = spawn(UVICORN, ["openmarvis.main:app", "--port", "8000"], {
    cwd: BACKEND,
    env: { ...process.env },
  });
  const log = logStream("backend");
  backendProc.stdout.pipe(log);
  backendProc.stderr.pipe(log);
  backendProc.on("exit", (code) => {
    console.log(`[desktop] backend exited (${code})`);
    backendProc = null;
  });
  console.log("[desktop] backend started, waiting for health...");
  await waitFor(HEALTH, 60000);
  console.log("[desktop] backend ready");
}

async function startFrontend() {
  if (await portOpen(WEB_URL)) {
    console.log("[desktop] frontend already running");
    return;
  }

  // Prefer pre-built Next.js (faster); fall back to dev server
  const nextBin  = path.join(WEB, "node_modules", ".bin", "next");
  const hasBuild = fs.existsSync(path.join(WEB, ".next", "BUILD_ID"));

  const args = hasBuild ? ["start"] : ["dev"];
  frontendProc = spawn(nextBin, args, {
    cwd: WEB,
    env: { ...process.env, PORT: "3000" },
  });
  const log = logStream("web");
  frontendProc.stdout.pipe(log);
  frontendProc.stderr.pipe(log);
  frontendProc.on("exit", (code) => {
    console.log(`[desktop] frontend exited (${code})`);
    frontendProc = null;
  });
  console.log("[desktop] frontend started, waiting...");
  await waitFor(WEB_URL, 90000);
  console.log("[desktop] frontend ready");
}

// ─── Cleanup ──────────────────────────────────────────────────────────────────

function killServices() {
  if (backendProc)  { backendProc.kill();  backendProc  = null; }
  if (frontendProc) { frontendProc.kill(); frontendProc = null; }
}

app.on("will-quit", killServices);
process.on("SIGTERM", () => { killServices(); app.quit(); });

// ─── Window ───────────────────────────────────────────────────────────────────

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280, height: 820, minWidth: 800, minHeight: 600,
    titleBarStyle: "hiddenInset",
    trafficLightPosition: { x: 16, y: 16 },
    backgroundColor: "#ffffff",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
    show: false,
  });

  // Set dock icon (macOS)
  if (process.platform === "darwin") {
    try { app.dock.setIcon(path.join(__dirname, "..", "build", "icon.png")); } catch (_) {}
  }

  mainWindow.loadURL("data:text/html," + encodeURIComponent(loadingHTML("Starting services...")));

  startServices()
    .then(() => {
      mainWindow.loadURL(WEB_URL);
      mainWindow.once("ready-to-show", () => mainWindow.show());
    })
    .catch((err) => {
      console.error("[desktop] startup failed:", err.message);
      mainWindow.loadURL("data:text/html," + encodeURIComponent(errorHTML(err.message)));
      mainWindow.show();
    });

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: "deny" };
  });
  mainWindow.on("closed", () => { mainWindow = null; });
}

async function startServices() {
  await startBackend();
  await startFrontend();
}

// ─── Tray ─────────────────────────────────────────────────────────────────────

function createTray() {
  // Use Template image so macOS auto-inverts for dark menu bar
  const iconPath = path.join(__dirname, "..", "build", "tray-iconTemplate.png");
  let icon;
  try {
    icon = nativeImage.createFromPath(iconPath);
    icon.setTemplateImage(true);
  } catch { icon = nativeImage.createEmpty(); }
  tray = new Tray(icon);
  tray.setToolTip("OpenMarvis");
  tray.setContextMenu(Menu.buildFromTemplate([
    { label: "Open OpenMarvis", click: () => mainWindow ? mainWindow.show() : createWindow() },
    { type: "separator" },
    { label: "Quit", role: "quit" },
  ]));
  tray.on("click", () => mainWindow ? mainWindow.show() : createWindow());
}

// ─── App lifecycle ────────────────────────────────────────────────────────────

const gotLock = app.requestSingleInstanceLock();
if (!gotLock) {
  app.quit();
} else {
  app.on("second-instance", () => {
    if (mainWindow) { mainWindow.show(); mainWindow.focus(); }
  });

  app.whenReady().then(() => {
    createWindow();
    createTray();
    app.on("activate", () => {
      if (BrowserWindow.getAllWindows().length === 0) createWindow();
      else if (mainWindow) mainWindow.show();
    });
  });

  app.on("window-all-closed", () => {
    if (process.platform !== "darwin") { killServices(); app.quit(); }
  });
}

// ─── HTML templates ───────────────────────────────────────────────────────────

function loadingHTML(msg) {
  return `<!DOCTYPE html><html><head><meta charset="utf-8">
<style>
*{margin:0;padding:0;box-sizing:border-box}
html,body{height:100%;background:#fff;font-family:-apple-system,sans-serif}
.c{display:flex;flex-direction:column;align-items:center;justify-content:center;height:100vh;gap:16px}
.logo{width:72px;height:72px;border-radius:18px;background:#111;display:flex;align-items:center;justify-content:center}
.spinner{width:20px;height:20px;border:2.5px solid #e5e7eb;border-top-color:#111;border-radius:50%;animation:spin .8s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
h1{font-size:20px;font-weight:700;color:#111}
p{font-size:13px;color:#9ca3af}
</style></head><body>
<div class="c">
  <div class="logo">
    <svg width="42" height="42" viewBox="0 0 100 100" fill="none">
      <path d="M62,16 C65,10 70,9 72,14 C70,18 66,20 63,22 C67,26 70,32 70,40 C70,50 64,58 56,62 C52,64 48,66 46,70 C44,74 44,80 48,82 C52,84 56,82 58,78 C60,74 60,68 62,64 C68,60 74,52 74,42 C74,32 70,24 64,18 Z" fill="white"/>
      <path d="M36,30 C34,24 36,16 42,14 C48,12 56,14 60,20 C64,26 63,36 58,42 C54,46 48,48 42,46 C36,44 32,38 36,30 Z" fill="white"/>
      <path d="M36,42 C32,44 26,46 24,52 C22,58 26,64 32,64 C36,64 40,62 42,58 C44,54 42,48 38,44 Z" fill="white"/>
      <circle cx="50" cy="26" r="3.5" fill="#111"/>
    </svg>
  </div>
  <h1>OpenMarvis</h1>
  <p>${msg}</p>
  <div class="spinner"></div>
</div></body></html>`;
}

function errorHTML(msg) {
  const escaped = msg.replace(/</g, "&lt;").replace(/>/g, "&gt;");
  return `<!DOCTYPE html><html><head><meta charset="utf-8">
<style>
*{margin:0;padding:0;box-sizing:border-box}
html,body{height:100%;background:#fff;font-family:-apple-system,sans-serif}
.c{display:flex;flex-direction:column;align-items:center;justify-content:center;height:100vh;gap:14px;text-align:center;padding:40px}
h1{font-size:18px;font-weight:700;color:#111}
p{font-size:13px;color:#6b7280;line-height:1.7;max-width:360px}
pre{background:#f3f4f6;padding:10px 16px;border-radius:8px;font-size:11px;text-align:left;max-width:480px;overflow:auto;white-space:pre-wrap;word-break:break-all}
button{margin-top:8px;padding:10px 24px;border-radius:10px;background:#111;color:#fff;border:none;font-size:13px;font-weight:600;cursor:pointer}
</style></head><body>
<div class="c">
  <h1>Startup Failed</h1>
  <p>Make sure you have run <b>make install</b> and added your API key to <b>apps/backend/.env</b></p>
  <pre>${escaped}</pre>
  <p>Logs: ${LOG_DIR}</p>
  <button onclick="location.reload()">Retry</button>
</div></body></html>`;
}

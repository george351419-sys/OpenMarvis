# OpenMarvis — Installation Guide

> For anyone who wants to run OpenMarvis on their own machine.

---

## Requirements

| Requirement | Version | Install |
|-------------|---------|---------|
| macOS | 13 Ventura or later | — |
| Python | 3.11 | `brew install python@3.11` |
| Node.js | 20 or later | `brew install node` |
| pnpm | 9 or later | `npm install -g pnpm` |
| Git | any | pre-installed on macOS |

Optional but recommended:

```bash
brew install cliclick   # needed for App automation (clicking UI in 3rd-party apps)
brew install pandoc     # needed for document conversion (Word / PDF)
```

---

## Step 1 — Get the code

```bash
git clone https://github.com/george351419-sys/OpenMarvis.git
cd OpenMarvis
```

---

## Step 2 — Install dependencies

```bash
make install
```

This runs `pnpm install` (frontend) and creates a Python virtual environment with all backend packages.  
Takes about 2–3 minutes on first run.

---

## Step 3 — Set your API key

```bash
cp apps/backend/.env.example apps/backend/.env
```

Open `apps/backend/.env` in any text editor and fill in **one** of:

```env
# Option A — Claude (best quality, recommended)
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxxxxxx

# Option B — DeepSeek (fast, cost-effective)
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Option C — Hunyuan (Tencent, good for Chinese tasks)
HUNYUAN_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxx
OPENMARVIS_LLM__PROVIDER_MODEL=openai/hunyuan-turbos-latest
OPENMARVIS_LLM__API_BASE=https://api.hunyuan.cloud.tencent.com/v1
```

**Where to get an API key:**
- Claude: https://console.anthropic.com
- DeepSeek: https://platform.deepseek.com
- Hunyuan: https://cloud.tencent.com/product/hunyuan

---

## Step 4 — Grant macOS permissions (first time only)

Some features require system permissions. Go to:

**System Settings → Privacy & Security**

- **Accessibility** — required for App automation (controlling other apps)
- **Screen Recording** — required for vision-based App automation

You only need these if you plan to use the App agent to control third-party apps like WeChat or other native macOS applications. Core features (file search, web, documents) work without them.

---

## Step 5 — Launch

### Option A: Desktop app (recommended — double-click to open)

```bash
cd apps/desktop
npm install
npm start
```

The desktop window will auto-start the backend and frontend, then open the interface.  
**No browser needed.**

To create a Desktop shortcut you can double-click next time:

```bash
cat > ~/Desktop/OpenMarvis.command << 'EOF'
#!/bin/zsh
cd /path/to/OpenMarvis/apps/desktop
npm start
EOF
chmod +x ~/Desktop/OpenMarvis.command
```

Replace `/path/to/OpenMarvis` with your actual clone path.

### Option B: Browser (open http://localhost:3000)

```bash
./start.sh
```

This starts both services and opens your browser automatically.  
Press `Ctrl+C` to stop everything.

### Option C: Manual start (advanced)

Run each in a separate terminal tab:

```bash
# Terminal 1 — backend
cd apps/backend
.venv/bin/uvicorn openmarvis.main:app --reload --port 8000

# Terminal 2 — frontend
cd apps/web
npm run dev
```

Then open http://localhost:3000

---

## Troubleshooting

**"make install" fails with Python not found**
```bash
brew install python@3.11
```

**"make install" fails with pnpm not found**
```bash
npm install -g pnpm
```

**Desktop app opens but shows "Startup Failed"**
- Make sure `apps/backend/.env` exists and has a valid API key
- Check logs in `<project>/.logs/backend.log` and `web.log`

**Port 8000 or 3000 already in use**
```bash
lsof -i :8000 -sTCP:LISTEN   # see what's using the port
kill <PID>                     # kill it, then retry
```

**macOS security warning on first launch**
- Right-click `OpenMarvis.command` → Open → Open anyway  
  (macOS warns on unsigned scripts from the internet; this is safe)

---

## Updating

```bash
git pull
make install   # re-run if dependencies changed
```

---

## System-level features & permissions

| Feature | What it needs |
|---------|--------------|
| File search & read/write | No special permissions |
| Web search & browsing | No special permissions |
| Document conversion | `brew install pandoc` |
| Scheduled tasks | No special permissions |
| Control macOS system settings | Accessibility permission |
| Control 3rd-party apps (WeChat etc.) | Accessibility + Screen Recording |
| Click UI in other apps | `brew install cliclick` + Accessibility |

---

## Uninstall

```bash
# Remove the project
rm -rf /path/to/OpenMarvis

# Remove app data (conversations, settings, memories)
rm -rf ~/.openmarvis
```

That's everything — no system-wide packages are installed outside the project folder.

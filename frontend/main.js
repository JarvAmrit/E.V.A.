/**
 * E.V.A. Electron Main Process
 *
 * Creates an always-on-top, frameless HUD window and loads the renderer.
 * The window is semi-transparent with vibrancy for the Iron Man aesthetic.
 */

const { app, BrowserWindow, ipcMain, screen } = require("electron");
const path = require("path");

let mainWindow;

function createWindow() {
  const { width, height } = screen.getPrimaryDisplay().workAreaSize;

  mainWindow = new BrowserWindow({
    width: Math.min(1400, width),
    height: Math.min(900, height),
    x: Math.floor((width - Math.min(1400, width)) / 2),
    y: Math.floor((height - Math.min(900, height)) / 2),
    // Frameless, always-on-top overlay
    frame: false,
    transparent: true,
    alwaysOnTop: false,       // set true in production for HUD mode
    backgroundColor: "#00000000",
    vibrancy: "dark",         // macOS vibrancy
    visualEffectState: "active",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      nodeIntegration: false,
      contextIsolation: true,
      // Allow iframes to load any URL (needed for the web panel)
      webviewTag: true,
    },
    titleBarStyle: "hidden",
    trafficLightPosition: { x: 16, y: 16 },
  });

  mainWindow.loadFile(path.join(__dirname, "renderer", "index.html"));

  // Open DevTools in dev mode
  if (process.argv.includes("--inspect")) {
    mainWindow.webContents.openDevTools({ mode: "detach" });
  }

  mainWindow.on("closed", () => {
    mainWindow = null;
  });
}

app.whenReady().then(() => {
  createWindow();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});

// ── IPC: toggle always-on-top ─────────────────────────────────────────────
ipcMain.handle("toggle-always-on-top", () => {
  const current = mainWindow.isAlwaysOnTop();
  mainWindow.setAlwaysOnTop(!current);
  return !current;
});

// ── IPC: minimise window ──────────────────────────────────────────────────
ipcMain.handle("minimize-window", () => {
  mainWindow.minimize();
});

// ── IPC: close window ─────────────────────────────────────────────────────
ipcMain.handle("close-window", () => {
  mainWindow.close();
});

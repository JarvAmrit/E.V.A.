/**
 * E.V.A. Preload Script
 *
 * Bridges the Electron main process and the renderer via a safe, restricted API.
 * Only the explicitly exposed functions are available to renderer code.
 */

const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("eva", {
  /** Toggle the window always-on-top mode. */
  toggleAlwaysOnTop: () => ipcRenderer.invoke("toggle-always-on-top"),

  /** Minimise the window. */
  minimize: () => ipcRenderer.invoke("minimize-window"),

  /** Close the window. */
  close: () => ipcRenderer.invoke("close-window"),
});

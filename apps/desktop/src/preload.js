const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("electronAPI", {
  platform: process.platform,
  openExternal: (url) => ipcRenderer.invoke("open-external", url),
});

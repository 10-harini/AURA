const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  // File dialogs
  openFileDialog:   () => ipcRenderer.invoke('open-file-dialog'),
  saveFileDialog:   (name) => ipcRenderer.invoke('save-file-dialog', name),
  openFolderDialog: () => ipcRenderer.invoke('open-folder-dialog'),

  // Window controls
  minimize:    () => ipcRenderer.send('win-minimize'),
  maximize:    () => ipcRenderer.send('win-maximize'),
  unmaximize:  () => ipcRenderer.send('win-unmaximize'),
  closeWindow: () => ipcRenderer.send('win-close'),
});
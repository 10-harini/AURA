const { app, BrowserWindow, ipcMain, dialog } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const http = require('http');

let mainWindow;
let pythonProcess;
let backendReady = false;

// ── Show a simple loading window immediately ──────────────────────────────────
function createLoadingWindow() {
  mainWindow = new BrowserWindow({
    width: 1280, height: 820,
    minWidth: 900, minHeight: 600,
    frame: false,
    backgroundColor: '#0d0d14',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });
  mainWindow.loadFile('loading.html');
}

function loadMainApp() {
  mainWindow.loadFile('index.html');
}

// ── Poll /ping until Flask responds ──────────────────────────────────────────
function waitForBackend(retries, delay, onReady, onFail) {
  http.get('http://127.0.0.1:5050/ping', (res) => {
    if (res.statusCode === 200) { onReady(); }
    else { retry(); }
  }).on('error', () => { retry(); });

  function retry() {
    if (retries <= 0) { onFail(); return; }
    setTimeout(() => waitForBackend(retries - 1, delay, onReady, onFail), delay);
  }
}

// ── Try python3 first, fall back to python ───────────────────────────────────
function startPython() {
  const pyScript = path.join(__dirname, 'backend', 'app.py');

  const candidates = process.platform === 'win32'
    ? ['python', 'python3']
    : ['python3', 'python'];

  let idx = 0;

  function tryNext() {
    if (idx >= candidates.length) {
      console.error('Could not find Python 3. Please install from https://python.org');
      if (!backendReady) loadMainApp();
      return;
    }
    const cmd = candidates[idx++];
    console.log('Trying Python binary:', cmd);

    const proc = spawn(cmd, [pyScript], {
      stdio: ['ignore', 'pipe', 'pipe'],
      env: { ...process.env, PYTHONIOENCODING: 'utf-8', PYTHONUTF8: '1' }
    });

    proc.on('error', () => {
      console.log(cmd, 'not found, trying next...');
      tryNext();
    });

    proc.stderr.on('data', d => process.stdout.write('[Flask] ' + d.toString()));
    proc.stdout.on('data', d => process.stdout.write('[Flask] ' + d.toString()));

    proc.on('exit', (code) => {
      if (!backendReady) {
        console.warn(cmd, 'exited early with code', code, '- trying next...');
        tryNext();
      }
    });

    pythonProcess = proc;
  }

  tryNext();
}

// ── App lifecycle ─────────────────────────────────────────────────────────────
app.whenReady().then(() => {
  createLoadingWindow();
  startPython();

  waitForBackend(60, 500,
    () => {
      backendReady = true;
      loadMainApp();
    },
    () => {
      console.error('Backend timed out - loading app anyway');
      loadMainApp();
    }
  );
});

app.on('window-all-closed', () => {
  if (pythonProcess) pythonProcess.kill();
  if (process.platform !== 'darwin') app.quit();
});
app.on('before-quit', () => {
  if (pythonProcess) pythonProcess.kill();
});

// ── IPC: window controls ──────────────────────────────────────────────────────
ipcMain.on('win-minimize',   () => mainWindow.minimize());
ipcMain.on('win-maximize',   () => mainWindow.maximize());
ipcMain.on('win-unmaximize', () => mainWindow.unmaximize());
ipcMain.on('win-close',      () => mainWindow.close());

// ── IPC: native file dialogs ──────────────────────────────────────────────────
ipcMain.handle('open-file-dialog', async () => {
  const r = await dialog.showOpenDialog(mainWindow, { properties: ['openFile'] });
  return r.filePaths[0] || null;
});
ipcMain.handle('save-file-dialog', async (_, defaultName) => {
  const r = await dialog.showSaveDialog(mainWindow, { defaultPath: defaultName || 'new_file.txt' });
  return r.filePath || null;
});
ipcMain.handle('open-folder-dialog', async () => {
  const r = await dialog.showOpenDialog(mainWindow, { properties: ['openDirectory'] });
  return r.filePaths[0] || null;
});
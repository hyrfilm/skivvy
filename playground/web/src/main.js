import { createNanoTerm, defineNanoTermConfig, parseOverlayJson, parseOverlayParam, registry } from 'nanoterm';
import overlayRaw from './generated/fs-overlay.json?raw';

const PROJECT_ROOT = '/home/guest/playground';
const WARMUP_DELAY_MS = 1500;

const CATEGORIES = {
  basics:    { label: 'Basics',    cfg: 'cfg.json',           ops: [{ '-': 'tests_' }, { '-': 'cfg_' }] },
  diffs:     { label: 'Diffs',     cfg: 'cfg_diffs.json',     ops: [{ '-': 'tests_' }, { '+': 'tests_diffs' }, { '-': 'cfg_' }, { '+': 'cfg_diffs' }] },
  matchers:  { label: 'Matchers',  cfg: 'cfg_matchers.json',  ops: [{ '-': 'tests_' }, { '+': 'tests_matchers' }, { '-': 'cfg_' }, { '+': 'cfg_matchers' }] },
  variables: { label: 'Variables', cfg: 'cfg_variables.json', ops: [{ '-': 'tests_' }, { '+': 'tests_variables' }, { '-': 'cfg_' }, { '+': 'cfg_variables' }] },
  oauth:     { label: 'OAuth',     cfg: 'cfg_oauth.json',     ops: [{ '-': 'tests_' }, { '+': 'tests_oauth' }, { '-': 'cfg_' }, { '+': 'cfg_oauth' }] },
  headers:   { label: 'Headers',   cfg: 'cfg_headers.json',   ops: [{ '-': 'tests_' }, { '+': 'tests_headers' }, { '-': 'cfg_' }, { '+': 'cfg_headers' }] },
  graphql:   { label: 'GraphQL',   cfg: 'cfg_graphql.json',   ops: [{ '-': 'tests_' }, { '+': 'tests_graphql' }, { '-': 'cfg_' }, { '+': 'cfg_graphql' }] },
  readme:    { label: 'README',    cfg: 'cfg_readme.json',    ops: [{ '-': 'tests_' }, { '+': 'tests_readme' }, { '-': 'cfg_' }, { '+': 'cfg_readme' }], args: '--set=http_request_level=INFO --set=http_response_level=INFO' },
};

function collectFiles(fs, absolutePath, relativePath = '') {
  const node = fs.stat(absolutePath);
  if (!node) {
    return [];
  }

  if (node.type === 'file') {
    return [{ path: relativePath || node.name, content: node.content }];
  }

  const children = fs.readDir(absolutePath) ?? [];
  children.sort((left, right) => left.name.localeCompare(right.name));
  return children.flatMap((child) => {
    const childAbsolutePath = absolutePath === '/' ? `/${child.name}` : `${absolutePath}/${child.name}`;
    const childRelativePath = relativePath ? `${relativePath}/${child.name}` : child.name;
    return collectFiles(fs, childAbsolutePath, childRelativePath);
  });
}

function shellQuote(value) {
  if (value === '') {
    return "''";
  }
  if (/^[A-Za-z0-9_./:-]+$/.test(value)) {
    return value;
  }
  return `'${value.replace(/'/g, `'"'"'`)}'`;
}

function isWithinProjectRoot(absolutePath) {
  return absolutePath === PROJECT_ROOT || absolutePath.startsWith(`${PROJECT_ROOT}/`);
}

function getRelativeCwd(absolutePath) {
  if (absolutePath === PROJECT_ROOT) {
    return '.';
  }
  return absolutePath.slice(`${PROJECT_ROOT}/`.length);
}

function warmRunner(endpoint) {
  void fetch(endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      command: 'skivvy --version',
      cwd: '.',
      files: [],
    }),
  }).catch(() => {});
}

registry.register({
  name: 'skivvy',
  description: 'Run skivvy against the current playground workspace',
  usage: 'skivvy <cfg-or-test-path> [extra args...]',
  handler: async (ctx) => {
    if (ctx.args.length === 0) {
      ctx.writeStdout('usage: skivvy <cfg-or-test-path> [extra args...]\r\n');
      return { exitCode: 1 };
    }

    const endpoint = ctx.env.get('SKIVVY_RUNNER_URL') || 'http://127.0.0.1:8787/run-skivvy';
    const cwd = ctx.fs.resolvePath('.');
    if (!isWithinProjectRoot(cwd)) {
      ctx.writeStdout('skivvy: current directory must be inside ~/playground\r\n');
      return { exitCode: 1 };
    }

    const files = collectFiles(ctx.fs, PROJECT_ROOT);

    if (files.length === 0) {
      ctx.writeStdout('skivvy: playground workspace is empty\r\n');
      return { exitCode: 1 };
    }

    try {
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          command: ['skivvy', ...ctx.args].map(shellQuote).join(' '),
          cwd: getRelativeCwd(cwd),
          files,
        }),
      });

      if (!response.ok) {
        ctx.writeStdout(`skivvy: runner returned HTTP ${response.status}\r\n`);
        return { exitCode: 1 };
      }

      const payload = await response.json();
      if (typeof payload.output === 'string' && payload.output.length > 0) {
        ctx.writeStdout(payload.output.replace(/\n/g, '\r\n'));
      }

      // Refresh editor file tree — tests may have written files via $write_file
      refreshEditorFileTree();

      return { exitCode: typeof payload.exitCode === 'number' ? payload.exitCode : 1 };
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      ctx.writeStdout(`skivvy: ${message}\r\n`);
      return { exitCode: 1 };
    }
  },
});

const searchParams = new URLSearchParams(window.location.search);
const commandParam = searchParams.get('command');
const overlayParam = searchParams.get('overlay');
const runParam = searchParams.get('run');
const categoryParam = searchParams.get('category') || 'basics';
const category = CATEGORIES[categoryParam] ?? CATEGORIES.basics;
const runnerUrl = import.meta.env.VITE_SKIVVY_RUNNER_URL || 'http://127.0.0.1:8787/run-skivvy';

const baseOverlay = parseOverlayJson(overlayRaw);
if (overlayParam) {
  const urlOverlay = parseOverlayParam(overlayParam);
  if (urlOverlay?._?.ops) {
    baseOverlay._ = { ...(baseOverlay._ ?? {}), ops: urlOverlay._.ops };
  }
} else if (category.ops.length > 0) {
  baseOverlay._ = { ...(baseOverlay._ ?? {}), ops: category.ops };
}

const config = defineNanoTermConfig({
  profile: {
    startupCommands: ['cd ~/playground', 'ls'],
    pendingInput: commandParam ?? `skivvy ${runParam ?? (overlayParam ? 'cfg.json' : (category.args ? `${category.cfg} ${category.args}` : category.cfg))}`,
    env: {
      SKIVVY_RUNNER_URL: runnerUrl,
    },
  },
  fs: {
    backend: 'memory',
    overlay: baseOverlay,
  },
});

const container = document.getElementById('terminal');
if (!container) {
  throw new Error('missing #terminal container');
}

const nano = createNanoTerm(container, config);
window.setTimeout(() => warmRunner(runnerUrl), WARMUP_DELAY_MS);

// ── editor panel ──────────────────────────────────────────────────────────────

const editorPanel    = document.getElementById('editor-panel');
const fileTreeEl     = document.getElementById('file-tree');
const editorTextarea = document.getElementById('editor-textarea');
const editorPathEl   = document.getElementById('editor-path');
const editorBadgeEl  = document.getElementById('editor-badge');
const editorSaveBtn  = document.getElementById('editor-save');
const toggleBtn      = document.getElementById('toggle-editor');

let openPath     = null;
let savedContent = null;

// Files to skip in the tree (not useful to edit in the playground)
const SKIP_NAMES = new Set(['.nashrc', '__pycache__', 'server.py']);
const SKIP_EXT   = new Set(['.pyc', '.pyo']);

function listPlaygroundFiles(absDir) {
  const entries = nano.fs.readDir(absDir) ?? [];
  const result  = [];

  const sorted = [...entries].sort((a, b) => {
    // dirs before files so grouping works naturally
    if (a.type !== b.type) return a.type === 'dir' ? -1 : 1;
    return a.name.localeCompare(b.name);
  });

  for (const entry of sorted) {
    if (entry.name.startsWith('.') || SKIP_NAMES.has(entry.name)) continue;
    const ext = entry.name.slice(entry.name.lastIndexOf('.'));
    if (SKIP_EXT.has(ext)) continue;

    const abs = `${absDir}/${entry.name}`;
    if (entry.type === 'dir') {
      result.push(...listPlaygroundFiles(abs));
    } else {
      result.push(abs.slice(PROJECT_ROOT.length + 1));
    }
  }

  return result;
}

function setBadge(modified) {
  if (!openPath) {
    editorBadgeEl.textContent = '';
    editorBadgeEl.className = 'badge';
    return;
  }
  editorBadgeEl.textContent = modified ? 'modified' : 'saved';
  editorBadgeEl.className   = modified ? 'badge modified' : 'badge saved';
}

function openFile(relPath) {
  const content = nano.fs.readFile(`${PROJECT_ROOT}/${relPath}`);
  if (content === null) return;

  openPath     = relPath;
  savedContent = content;
  editorTextarea.value = content;
  editorPathEl.textContent = relPath;
  setBadge(false);

  document.querySelectorAll('#file-tree .file-entry').forEach((el) => {
    el.classList.toggle('active', el.dataset.path === relPath);
  });
}

function saveFile() {
  if (!openPath) return;
  nano.fs.writeFile(`${PROJECT_ROOT}/${openPath}`, editorTextarea.value);
  savedContent = editorTextarea.value;
  setBadge(false);
}

function toRoute(relPath) {
  // "api/fortunes/1.json" → "/fortunes/1"
  return '/' + relPath.slice('api/'.length).replace(/\.json$/, '');
}

function buildFileTree() {
  const files = listPlaygroundFiles(PROJECT_ROOT);
  fileTreeEl.innerHTML = '';

  const rootFiles  = [];
  const testFiles  = [];
  const apiFiles   = [];
  const otherFiles = new Map(); // dir → [paths]

  for (const f of files) {
    const top = f.indexOf('/') >= 0 ? f.slice(0, f.indexOf('/')) : '';
    if (top === 'tests')      testFiles.push(f);
    else if (top === 'api')   apiFiles.push(f);
    else if (top === '')      rootFiles.push(f);
    else {
      if (!otherFiles.has(top)) otherFiles.set(top, []);
      otherFiles.get(top).push(f);
    }
  }

  const renderFile = (relPath, { isRoute = false } = {}) => {
    const el = document.createElement('div');
    const isActive = relPath === openPath;
    el.className    = 'file-entry' + (isRoute ? ' api-route' : '') + (isActive ? ' active' : '');
    el.dataset.path = relPath;
    el.textContent  = isRoute ? toRoute(relPath) : relPath.split('/').pop();
    el.title        = relPath;
    const depth     = isRoute ? 0 : (relPath.match(/\//g) ?? []).length;
    el.style.paddingLeft = (10 + depth * 14) + 'px';
    el.addEventListener('click', () => openFile(relPath));
    fileTreeEl.appendChild(el);
  };

  const renderDirLabel = (text) => {
    const label = document.createElement('div');
    label.className   = 'dir-label';
    label.textContent = text;
    fileTreeEl.appendChild(label);
  };

  const renderSeparator = () => {
    const hr = document.createElement('hr');
    hr.className = 'tree-separator';
    fileTreeEl.appendChild(hr);
  };

  // Root-level files (cfg.json, README.md, …)
  for (const f of rootFiles) renderFile(f);

  // Test files
  if (testFiles.length > 0) {
    if (rootFiles.length > 0) renderSeparator();
    renderDirLabel('tests/');
    for (const f of testFiles) renderFile(f);
  }

  // Any other non-api dirs (shouldn't normally appear but handle gracefully)
  for (const [dir, dirFiles] of [...otherFiles.entries()].sort()) {
    renderSeparator();
    renderDirLabel(dir + '/');
    for (const f of dirFiles) renderFile(f);
  }

  // API files as routes
  if (apiFiles.length > 0) {
    renderSeparator();
    renderDirLabel('api/');
    for (const f of apiFiles) renderFile(f, { isRoute: true });
  }
}

// Called from the skivvy command handler after a run
function refreshEditorFileTree() {
  buildFileTree();
  // Re-read the open file in case it was modified by the run (e.g. $write_file)
  if (openPath) {
    const fresh = nano.fs.readFile(`${PROJECT_ROOT}/${openPath}`);
    if (fresh !== null && fresh !== savedContent) {
      savedContent = fresh;
      editorTextarea.value = fresh;
      setBadge(false);
    }
  }
}

editorTextarea.addEventListener('input', () => {
  if (openPath) setBadge(editorTextarea.value !== savedContent);
});

editorTextarea.addEventListener('keydown', (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key === 's') {
    e.preventDefault();
    saveFile();
    return;
  }
  // Tab → two spaces (simple code-editor behaviour)
  if (e.key === 'Tab') {
    e.preventDefault();
    const s = editorTextarea.selectionStart;
    const end = editorTextarea.selectionEnd;
    editorTextarea.value = editorTextarea.value.slice(0, s) + '  ' + editorTextarea.value.slice(end);
    editorTextarea.selectionStart = editorTextarea.selectionEnd = s + 2;
    if (openPath) setBadge(editorTextarea.value !== savedContent);
  }
});

editorSaveBtn.addEventListener('click', saveFile);

// Panel toggle
let panelOpen = true;
toggleBtn.addEventListener('click', () => {
  panelOpen = !panelOpen;
  editorPanel.classList.toggle('collapsed', !panelOpen);
  toggleBtn.textContent = panelOpen ? 'hide editor' : 'show editor';
  // Re-fit terminal after CSS transition completes
  window.setTimeout(() => nano.fit(), 160);
});

// Build tree and auto-open first test file once the VFS is populated
window.setTimeout(() => {
  buildFileTree();
  const firstTest = listPlaygroundFiles(`${PROJECT_ROOT}/tests`)[0];
  if (firstTest) openFile(firstTest);
}, 50);

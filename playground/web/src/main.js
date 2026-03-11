import { createNanoTerm, defineNanoTermConfig, parseOverlayJson, registry } from 'nanoterm';
import overlayRaw from './generated/fs-overlay.json?raw';

const PROJECT_ROOT = '/home/guest/playground';
const WARMUP_DELAY_MS = 1500;

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
      return { exitCode: typeof payload.exitCode === 'number' ? payload.exitCode : 1 };
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      ctx.writeStdout(`skivvy: ${message}\r\n`);
      return { exitCode: 1 };
    }
  },
});

const searchParams = new URLSearchParams(window.location.search);
const replayParam = searchParams.get('replay');
const runnerUrl = import.meta.env.VITE_SKIVVY_RUNNER_URL || 'http://127.0.0.1:8787/run-skivvy';

const config = defineNanoTermConfig({
  profile: {
    startupCommands: ['motd', 'cd ~/playground', 'ls', ...(replayParam ? [`replay ${replayParam}`] : [])],
    env: {
      SKIVVY_RUNNER_URL: runnerUrl,
    },
  },
  fs: {
    backend: 'memory',
    overlay: parseOverlayJson(overlayRaw),
  },
});

const container = document.getElementById('terminal');
if (!container) {
  throw new Error('missing #terminal container');
}

createNanoTerm(container, config);
window.setTimeout(() => warmRunner(runnerUrl), WARMUP_DELAY_MS);

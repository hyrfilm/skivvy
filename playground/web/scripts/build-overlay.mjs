#!/usr/bin/env node

import { promises as fs } from 'node:fs';
import path from 'node:path';
import { TextDecoder } from 'node:util';
import { glob } from 'tinyglobby';

const DEFAULT_OUT = 'src/generated/fs-overlay.json';

function printHelp() {
  console.log(`Usage:
  node scripts/build-overlay.mjs --fromDir <directory> [--out <file>] [--exclude <glob> ...]

Options:
  --fromDir   Source directory to serialize into overlay JSON (required)
  --out       Output file path (default: ${DEFAULT_OUT})
  --exclude   Glob pattern to exclude (can be repeated)
  --help      Show this help

Example:
  node scripts/build-overlay.mjs --fromDir ./overlay --out ./src/generated/fs-overlay.json --exclude "**/*.tmp"
`);
}

function parseArgs(argv) {
  const args = {
    fromDir: '',
    out: DEFAULT_OUT,
    exclude: [],
  };

  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    if (token === '--help' || token === '-h') {
      args.help = true;
      continue;
    }
    if (token === '--fromDir') {
      args.fromDir = argv[index + 1] || '';
      index += 1;
      continue;
    }
    if (token === '--out') {
      args.out = argv[index + 1] || DEFAULT_OUT;
      index += 1;
      continue;
    }
    if (token === '--exclude') {
      const value = argv[index + 1];
      if (value) {
        args.exclude.push(value);
        index += 1;
      }
      continue;
    }
    throw new Error(`Unknown argument: ${token}`);
  }

  return args;
}

function setPath(tree, parts, value) {
  let current = tree;
  for (const part of parts.slice(0, -1)) {
    if (!current[part] || typeof current[part] !== 'object' || Array.isArray(current[part])) {
      current[part] = {};
    }
    current = current[part];
  }
  current[parts[parts.length - 1]] = value;
}

function normalizeParts(relativePath) {
  return relativePath.split(path.sep).filter(Boolean);
}

function decodeUtf8(buffer) {
  const decoder = new TextDecoder('utf-8', { fatal: true });
  try {
    const text = decoder.decode(buffer);
    if (text.includes('\u0000')) {
      return null;
    }
    const suspiciousChars = text.match(/[\u0001-\u0008\u000B\u000C\u000E-\u001A]/g)?.length || 0;
    if (suspiciousChars > text.length * 0.1) {
      return null;
    }
    return text;
  } catch {
    return null;
  }
}

async function buildOverlay({ fromDir, exclude }) {
  const sourceDir = path.resolve(fromDir);
  const stat = await fs.stat(sourceDir).catch(() => null);
  if (!stat || !stat.isDirectory()) {
    throw new Error(`--fromDir path is not a directory: ${fromDir}`);
  }

  const files = await glob('**/*', {
    cwd: sourceDir,
    onlyFiles: true,
    dot: true,
    ignore: exclude,
  });

  files.sort((left, right) => left.localeCompare(right));

  const root = {};
  const types = {};
  const stats = {
    json: 0,
    text: 0,
    base64: 0,
  };

  for (const relativePath of files) {
    const absolutePath = path.join(sourceDir, relativePath);
    const parts = normalizeParts(relativePath);
    const content = await fs.readFile(absolutePath);

    if (path.extname(relativePath) === '.json') {
      const maybeText = decodeUtf8(content);
      if (maybeText !== null) {
        try {
          setPath(root, parts, JSON.parse(maybeText));
          setPath(types, parts, 'json');
          stats.json += 1;
          continue;
        } catch {
          // fall through and classify as text/base64
        }
      }
    }

    const maybeText = decodeUtf8(content);
    if (maybeText !== null) {
      setPath(root, parts, maybeText);
      stats.text += 1;
      continue;
    }

    setPath(root, parts, content.toString('base64'));
    setPath(types, parts, 'base64');
    stats.base64 += 1;
  }

  const overlay = {
    '/': root,
  };

  if (Object.keys(types).length > 0) {
    overlay._ = {
      types: {
        '/': types,
      },
    };
  }

  return { overlay, stats, totalFiles: files.length };
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args.help) {
    printHelp();
    return;
  }

  if (!args.fromDir) {
    throw new Error('Missing required argument: --fromDir');
  }

  const { overlay, stats, totalFiles } = await buildOverlay({
    fromDir: args.fromDir,
    exclude: args.exclude,
  });

  const outPath = path.resolve(args.out || DEFAULT_OUT);
  await fs.mkdir(path.dirname(outPath), { recursive: true });
  await fs.writeFile(outPath, `${JSON.stringify(overlay, null, 2)}\n`, 'utf8');

  console.log(`Overlay generated: ${outPath}`);
  console.log(`Files processed: ${totalFiles}`);
  console.log(`JSON: ${stats.json}, text: ${stats.text}, base64: ${stats.base64}`);
}

main().catch((error) => {
  console.error(`overlay build failed: ${error.message}`);
  process.exitCode = 1;
});

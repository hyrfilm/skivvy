#!/usr/bin/env node

import { promises as fs } from 'node:fs';
import path from 'node:path';
import { TextDecoder } from 'node:util';

const ROOT = path.resolve(import.meta.dirname, '..');
const OUTPUT = path.join(ROOT, 'src', 'generated', 'fs-overlay.json');
const SOURCES = [
  {
    fromDir: path.join(ROOT, 'overlay'),
    prefix: [],
  },
];

function setPath(tree, parts, value) {
  let current = tree;
  for (const part of parts.slice(0, -1)) {
    if (!(part in current)) {
      current[part] = {};
    }
    current = current[part];
  }
  current[parts.at(-1)] = value;
}

function decodeUtf8(buffer) {
  const decoder = new TextDecoder('utf-8', { fatal: true });
  try {
    const text = decoder.decode(buffer);
    if (text.includes('\u0000')) {
      return null;
    }
    return text;
  } catch {
    return null;
  }
}

async function addDirectory(overlay, fromDir, prefix) {
  try {
    const stat = await fs.stat(fromDir);
    if (!stat.isDirectory()) {
      return;
    }
  } catch {
    return;
  }

  const files = await listFiles(fromDir);
  files.sort((left, right) => left.localeCompare(right));

  for (const relativePath of files) {
    const absolutePath = path.join(fromDir, relativePath);
    const parts = [...prefix, ...relativePath.split(path.sep).filter(Boolean)];
    const content = await fs.readFile(absolutePath);

    if (path.extname(relativePath) === '.json') {
      const maybeText = decodeUtf8(content);
      if (maybeText !== null) {
        try {
          setPath(overlay.json, parts, JSON.parse(maybeText));
          continue;
        } catch {
        }
      }
    }

    const maybeText = decodeUtf8(content);
    if (maybeText !== null) {
      setPath(overlay.text, parts, maybeText);
      continue;
    }

    setPath(overlay.binary, parts, content.toString('base64'));
  }
}

async function listFiles(rootDir, currentDir = rootDir) {
  const entries = await fs.readdir(currentDir, { withFileTypes: true });
  const files = [];
  for (const entry of entries) {
    const absolutePath = path.join(currentDir, entry.name);
    if (entry.isDirectory()) {
      files.push(...await listFiles(rootDir, absolutePath));
      continue;
    }
    if (entry.isFile()) {
      files.push(path.relative(rootDir, absolutePath));
    }
  }
  return files;
}

async function main() {
  const overlay = {
    json: {},
    text: {},
    binary: {},
  };

  for (const source of SOURCES) {
    await addDirectory(overlay, source.fromDir, source.prefix);
  }

  await fs.mkdir(path.dirname(OUTPUT), { recursive: true });
  await fs.writeFile(OUTPUT, `${JSON.stringify(overlay, null, 2)}\n`, 'utf8');
  console.log(`Overlay generated at ${OUTPUT}`);
}

main().catch((error) => {
  console.error(error.message);
  process.exitCode = 1;
});

#!/usr/bin/env node
import { runOverlayBuild } from 'nanoterm/scripts/build-overlay';

await runOverlayBuild({
  fromDir: './overlay',
  out: './src/generated/fs-overlay.json',
});

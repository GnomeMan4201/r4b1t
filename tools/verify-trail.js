#!/usr/bin/env node
'use strict';

const fs = require('node:fs/promises');
const trail = require('../trail-manifest.js');
const blind = require('../blind-manifest.js');

async function readJson(path) {
  if (path === '-') return JSON.parse(await fs.readFile(0, 'utf8'));
  return JSON.parse(await fs.readFile(path, 'utf8'));
}

async function main() {
  const [, , childPath, parentPath] = process.argv;
  if (!childPath) {
    throw new Error('Usage: npm run trail:verify -- <trail.json> [parent.json]');
  }
  const input = await readJson(childPath);
  if (input && input.manifest && input.manifest.format === blind.FORMAT) {
    const child = await blind.verify(input);
    if (parentPath) {
      const result = await blind.verifyLineage(child, await readJson(parentPath));
      console.log('LINEAGE VERIFIED / V0.2');
      console.log('child:  ' + result.child.trail_id);
      console.log('parent: ' + result.parent.trail_id);
      console.log('fork:   ' + result.fork_at);
      return;
    }
    console.log('TRAIL VERIFIED / V0.2');
    console.log('trail:     ' + child.trail_id);
    console.log('genesis:   ' + child.manifest.genesis_id);
    console.log('committed: ' + child.manifest.steps.length);
    child.statuses.forEach((entry) => console.log('step ' + entry.index + ':    ' + entry.status));
    return;
  }
  const child = await trail.verify(input);
  if (parentPath) {
    const result = await trail.verifyLineage(child, await readJson(parentPath));
    console.log('LINEAGE VERIFIED');
    console.log('child:  ' + result.child.trail_id);
    console.log('parent: ' + result.parent.trail_id);
    console.log('fork:   ' + result.fork_at);
    return;
  }
  console.log('TRAIL VERIFIED');
  console.log('trail:  ' + child.trail_id);
  console.log('routes: ' + child.manifest.routes.length);
  if (child.manifest.parent) {
    console.log('lineage: DECLARED / PARENT ARTIFACT REQUIRED');
  } else {
    console.log('lineage: ORIGIN');
  }
}

main().catch((error) => {
  console.error('REJECTED / ' + error.message);
  process.exitCode = 1;
});

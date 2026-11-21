#!/usr/bin/env node
import { createHash } from 'node:crypto';
import { gzipSync } from 'node:zlib';
import { mkdir, writeFile } from 'node:fs/promises';
import { join, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

const project = resolve(process.argv[2] ?? process.cwd());
const load = (rel) => import(pathToFileURL(join(project, rel)).href);
const [{ Terrain }, { generateCity }, { subdivide, resetLotIds }, { Rng }] = await Promise.all([
  load('src/world/terrain.js'),
  load('src/world/netgen.js'),
  load('src/world/lots.js'),
  load('src/core/rng.js'),
]);

const MAP_VERSION = 1;
const MAP_SEED = 0x5eed1234;
const terrain = new Terrain({ cell: 8, extent: 1792 });
terrain.bake();

const rng = new Rng(MAP_SEED);
const city = generateCity(terrain, rng.fork());
resetLotIds();
const { lots } = subdivide(city.blocks, terrain, rng.fork());

const graph = city.graph;
const payload = {
  schema: 'one-bbm-steel-city-map',
  version: MAP_VERSION,
  seed: MAP_SEED,
  dimensions: { citySize: 3000, tileSize: 128, sectorSize: 512 },
  counts: {
    roadNodes: graph.nodes.length,
    roadEdges: graph.edges.length,
    blocks: city.blocks.length,
    lots: lots.length,
    bridges: city.bridges.length,
    pointsOfInterest: city.pois?.length ?? 0,
  },
  terrain: {
    cell: terrain.cell,
    extent: terrain.extent,
    n: terrain.n,
    origin: terrain.origin,
    min: terrain._min,
    max: terrain._max,
    gridF32: Buffer.from(terrain.grid.buffer, terrain.grid.byteOffset, terrain.grid.byteLength).toString('base64'),
    roadWF32: Buffer.from(terrain.roadW.buffer, terrain.roadW.byteOffset, terrain.roadW.byteLength).toString('base64'),
  },
  city: {
    roads: graph,
    blocks: city.blocks,
    bridges: city.bridges,
    pois: city.pois ?? [],
    lots,
  },
};

const json = Buffer.from(JSON.stringify(payload));
const compressed = gzipSync(json, { level: 9, mtime: 0 });
const sha256 = createHash('sha256').update(compressed).digest('hex');
const outDir = join(project, 'map-package');
await mkdir(outDir, { recursive: true });
await writeFile(join(outDir, 'steel-city-v1.json.gz'), compressed);
await writeFile(join(outDir, 'steel-city-v1.manifest.json'), JSON.stringify({
  schema: payload.schema,
  version: MAP_VERSION,
  seed: MAP_SEED,
  encoding: 'gzip-json',
  bytes: compressed.byteLength,
  sha256,
  counts: payload.counts,
}, null, 2) + '\n');

console.log('[map-export] complete', JSON.stringify({
  ...payload.counts,
  rawBytes: json.byteLength,
  compressedBytes: compressed.byteLength,
  sha256,
}));

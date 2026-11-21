#!/usr/bin/env python3
from pathlib import Path
import sys

root = Path(sys.argv[1])

cache = r'''const MAP_VERSION = 2;
const BASE = 'https://raw.githubusercontent.com/gokerabidine-gif/ONE_BBM/map-assets/maps/steel-city-v2';
const MANIFEST_URL = BASE + '.manifest.json';
const PACKAGE_URL = BASE + '.pack';
const DB_NAME = 'one-bbm-city-map';
const DB_STORE = 'packages';
const DB_KEY = 'steel-city-v2';

function report(state, loaded = 0, total = 0, message = '') {
  if (typeof window === 'undefined') return;
  window.dispatchEvent(new CustomEvent('onebbm:map-status', {
    detail: { state, loaded, total, message },
  }));
}

function openDb() {
  return new Promise((resolve, reject) => {
    if (!globalThis.indexedDB) return reject(new Error('IndexedDB unavailable'));
    const req = indexedDB.open(DB_NAME, 1);
    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains(DB_STORE)) db.createObjectStore(DB_STORE, { keyPath: 'key' });
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error ?? new Error('Could not open map storage'));
  });
}

function requestValue(req) {
  return new Promise((resolve, reject) => {
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error ?? new Error('Map storage request failed'));
  });
}

async function readPackage() {
  const db = await openDb();
  try {
    const tx = db.transaction(DB_STORE, 'readonly');
    return await requestValue(tx.objectStore(DB_STORE).get(DB_KEY));
  } finally {
    db.close();
  }
}

async function writePackage(bytes, manifest) {
  const db = await openDb();
  try {
    const tx = db.transaction(DB_STORE, 'readwrite');
    await requestValue(tx.objectStore(DB_STORE).put({
      key: DB_KEY,
      bytes: bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength),
      manifest,
      savedAt: Date.now(),
    }));
  } finally {
    db.close();
  }
}

async function fetchBytes(url, onProgress) {
  const response = await fetch(url, { cache: 'no-store' });
  if (!response.ok) throw new Error('Map server returned HTTP ' + response.status);
  const total = Number(response.headers.get('content-length')) || 0;
  if (!response.body?.getReader) {
    const bytes = new Uint8Array(await response.arrayBuffer());
    onProgress?.(bytes.byteLength, total || bytes.byteLength);
    return bytes;
  }
  const reader = response.body.getReader();
  const chunks = [];
  let loaded = 0;
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    chunks.push(value);
    loaded += value.byteLength;
    onProgress?.(loaded, total);
    report('downloading', loaded, total);
  }
  const bytes = new Uint8Array(loaded);
  let offset = 0;
  for (const chunk of chunks) {
    bytes.set(chunk, offset);
    offset += chunk.byteLength;
  }
  return bytes;
}

async function sha256(bytes) {
  if (!globalThis.crypto?.subtle) throw new Error('Secure checksum verification unavailable');
  const digest = await crypto.subtle.digest('SHA-256', bytes);
  return Array.from(new Uint8Array(digest), (v) => v.toString(16).padStart(2, '0')).join('');
}

function decodeFloat32(base64, count, label) {
  const binary = atob(base64);
  if (binary.length !== count * 4) throw new Error(label + ' terrain data has an invalid size');
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  return new Float32Array(bytes.buffer);
}

async function unpack(bytes, manifest) {
  if (bytes.byteLength !== manifest.bytes) throw new Error('City map package size mismatch');
  const digest = await sha256(bytes);
  if (digest !== manifest.sha256) throw new Error('City map checksum mismatch');
  if (typeof DecompressionStream !== 'function') throw new Error('Gzip decoding is not supported on this device');
  const stream = new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'));
  const raw = await new Response(stream).arrayBuffer();
  const payload = JSON.parse(new TextDecoder().decode(raw));
  if (payload.schema !== 'one-bbm-steel-city-map' || payload.version !== MAP_VERSION) {
    throw new Error('Unsupported city map version');
  }
  const n = payload.terrain?.n;
  if (!Number.isInteger(n) || n < 2 || n > 2048) throw new Error('Invalid terrain grid');
  payload.terrain.grid = decodeFloat32(payload.terrain.gridF32, n * n, 'Height');
  payload.terrain.roadW = decodeFloat32(payload.terrain.roadWF32, n * n, 'Road');
  delete payload.terrain.gridF32;
  delete payload.terrain.roadWF32;
  const roads = payload.city?.roads;
  if (!Array.isArray(roads?.nodes) || !Array.isArray(roads?.edges) ||
      !Array.isArray(payload.city?.blocks) || !Array.isArray(payload.city?.lots) ||
      roads.nodes.length !== payload.counts.roadNodes ||
      roads.edges.length !== payload.counts.roadEdges ||
      payload.city.blocks.length !== payload.counts.blocks ||
      payload.city.lots.length !== payload.counts.lots) {
    throw new Error('City map package is incomplete');
  }
  if (!payload.rngState || !Array.isArray(payload.landmarks)) {
    throw new Error('City map package is missing deterministic world state');
  }
  return payload;
}

export async function downloadSteelCityMap({ onProgress } = {}) {
  report('checking');
  const manifestResponse = await fetch(MANIFEST_URL, { cache: 'no-store' });
  if (!manifestResponse.ok) throw new Error('City map manifest unavailable (HTTP ' + manifestResponse.status + ')');
  const manifest = await manifestResponse.json();
  if (manifest.schema !== 'one-bbm-steel-city-map' || manifest.version !== MAP_VERSION ||
      manifest.encoding !== 'gzip-json' || !Number.isInteger(manifest.bytes) || !manifest.sha256) {
    throw new Error('City map manifest is invalid');
  }
  const bytes = await fetchBytes(PACKAGE_URL, onProgress);
  const payload = await unpack(bytes, manifest);
  try {
    await writePackage(bytes, manifest);
  } catch (err) {
    console.warn('[map] downloaded but could not persist offline package', err);
  }
  report('ready', bytes.byteLength, manifest.bytes);
  return payload;
}

let loading = null;
export function loadSteelCityMap() {
  if (loading) return loading;
  loading = (async () => {
    try {
      const cached = await readPackage();
      if (cached?.bytes && cached.manifest?.version === MAP_VERSION) {
        const bytes = new Uint8Array(cached.bytes);
        const payload = await unpack(bytes, cached.manifest);
        report('cached', bytes.byteLength, bytes.byteLength);
        return payload;
      }
    } catch (err) {
      console.warn('[map] cached package rejected; attempting fresh download', err);
    }
    try {
      return await downloadSteelCityMap();
    } catch (err) {
      report('error', 0, 0, err?.message ?? String(err));
      console.warn('[map] full city package unavailable; using deterministic generator fallback', err);
      return null;
    }
  })().finally(() => { loading = null; });
  return loading;
}
'''
(root / 'src/world/map-cache.js').write_text(cache)

p = root / 'src/world/index.js'
s = p.read_text()
if "import { RoadGraph } from './roadgraph.js';" not in s:
    anchor = "import { Router } from './route.js';"
    if anchor not in s: raise SystemExit('world RoadGraph import anchor missing')
    s = s.replace(anchor, anchor + "\nimport { RoadGraph } from './roadgraph.js';\nimport { loadSteelCityMap } from './map-cache.js';", 1)

start = s.index('    const t0 = performance.now();\n\n    /* ---- 1. terrain')
end_anchor = '    const tPlan = performance.now();'
end = s.index(end_anchor, start) + len(end_anchor)
new_init = r'''    const t0 = performance.now();

    /* ---- 1. terrain + verified complete city package ----------------- */
    this.terrain = new Terrain({ cell: 8, extent: 1792 });
    const mapPack = await loadSteelCityMap();
    let city;
    let lots;
    let byTile;

    if (mapPack) {
      const saved = mapPack.terrain;
      if (saved.cell !== this.terrain.cell || saved.extent !== this.terrain.extent ||
          saved.grid.length !== this.terrain.grid.length ||
          saved.roadW.length !== this.terrain.roadW.length) {
        throw new Error('[world] downloaded map terrain does not match this build');
      }
      this.terrain.grid.set(saved.grid);
      this.terrain.roadW.set(saved.roadW);
      this.terrain._min = saved.min;
      this.terrain._max = saved.max;
      this.terrain.baked = true;

      for (const savedLandmark of mapPack.landmarks) {
        const landmark = LANDMARKS.find((item) => item.id === savedLandmark.id);
        if (!landmark) continue;
        if (landmark.site && savedLandmark.site) Object.assign(landmark.site, savedLandmark.site);
        if (landmark.uphill && savedLandmark.uphill) Object.assign(landmark.uphill, savedLandmark.uphill);
      }

      const roads = new RoadGraph();
      roads.nodes = mapPack.city.roads.nodes;
      roads.edges = mapPack.city.roads.edges;
      roads.finalise();
      Object.assign(roads, {
        dedup: mapPack.city.roads.dedup,
        landmarkReserve: mapPack.city.roads.landmarkReserve,
        closure: mapPack.city.roads.closure,
        mainComponent: Int32Array.from(mapPack.city.roads.mainComponent),
        mainComponentId: mapPack.city.roads.mainComponentId,
        driveComponent: Int32Array.from(mapPack.city.roads.driveComponent),
        driveMain: mapPack.city.roads.driveMain,
        strandedNodes: mapPack.city.roads.strandedNodes,
      });
      city = {
        graph: roads,
        blocks: mapPack.city.blocks,
        bridges: mapPack.city.bridges,
        pois: mapPack.city.pois,
      };
      lots = mapPack.city.lots;
      byTile = new Map();
      for (const lot of lots) {
        const key = lot.tx + ',' + lot.tz;
        let list = byTile.get(key);
        if (!list) byTile.set(key, (list = []));
        list.push(lot);
      }
      this.rng.s0 = mapPack.rngState.s0;
      this.rng.s1 = mapPack.rngState.s1;
      this.rng.s2 = mapPack.rngState.s2;
      this.rng.s3 = mapPack.rngState.s3;
      console.info('[world] verified offline Steel City map package loaded', mapPack.counts);
    } else {
      this.terrain.bake();
      resetLotIds();
      city = generateCity(this.terrain, this.rng.fork());
      const divided = subdivide(city.blocks, this.terrain, this.rng.fork());
      lots = divided.lots;
      byTile = divided.byTile;
    }
    const tBake = performance.now();

    /* ---- 2. publish the city plan ------------------------------------- */
    this.roads = city.graph;
    this.blocks = city.blocks;
    this.bridgeSpecs = city.bridges;
    this.lots = lots;
    this._lotsByTile = byTile;
    this.pois = city.pois ?? [];
    this._poiById = new Map(this.pois.map((p) => [p.id, p]));
    this._router = new Router(this.roads);
    const tPlan = performance.now();'''
s = s[:start] + new_init + s[end:]
p.write_text(s)

p = root / 'src/ui/boot.js'
s = p.read_text()
if "downloadSteelCityMap" not in s:
    anchor = "import { BOYZ, BOY_BY_ID } from './data.js';"
    if anchor not in s: raise SystemExit('boot map downloader import anchor missing')
    s = s.replace(anchor, anchor + "\nimport { downloadSteelCityMap } from '../world/map-cache.js';", 1)

    anchor = "    this._marks = { boot: true };"
    if anchor not in s: raise SystemExit('boot map listener insertion anchor missing')
    listener = r'''    this._marks = { boot: true };
    this._mapListener = (event) => {
      const detail = event.detail ?? {};
      if (detail.state === 'downloading') {
        const pct = detail.total > 0 ? Math.round(detail.loaded / detail.total * 100) : 0;
        if (this.mapStatus) this.mapStatus.textContent = 'Downloading full city map… ' + pct + '%';
        if (this.stage) this.stage.textContent = 'Downloading complete Steel City map… ' + pct + '%';
      } else if (detail.state === 'cached') {
        if (this.mapStatus) this.mapStatus.textContent = 'FULL CITY MAP INSTALLED · OFFLINE READY';
      } else if (detail.state === 'ready') {
        if (this.mapStatus) this.mapStatus.textContent = 'FULL CITY MAP VERIFIED · SAVED OFFLINE';
      } else if (detail.state === 'error') {
        if (this.mapStatus) this.mapStatus.textContent = 'MAP DOWNLOAD FAILED · ' + (detail.message || 'Tap retry');
      }
    };
    window.addEventListener('onebbm:map-status', this._mapListener);'''
    s = s.replace(anchor, listener, 1)

    anchor = "    el('div', 'ow-boot-hint', w,"
    map_ui = r'''    const mapRow = el('div', 'ow-boot-map-row', w);
    setStyle(mapRow, 'display', 'flex');
    setStyle(mapRow, 'align-items', 'center');
    setStyle(mapRow, 'justify-content', 'space-between');
    setStyle(mapRow, 'gap', '12px');
    setStyle(mapRow, 'width', '100%');
    setStyle(mapRow, 'max-width', '720px');
    setStyle(mapRow, 'margin', '18px auto 6px');
    this.mapStatus = el('div', 'ow-boot-map-status', mapRow, 'Checking full city map…');
    setStyle(this.mapStatus, 'font-size', '12px');
    setStyle(this.mapStatus, 'letter-spacing', '.08em');
    setStyle(this.mapStatus, 'opacity', '.86');
    this.mapButton = el('button', 'ow-btn', mapRow, 'DOWNLOAD / UPDATE MAP');
    this.mapButton.type = 'button';
    this._press(this.mapButton, async () => {
      this.mapButton.disabled = true;
      this.mapButton.textContent = 'DOWNLOADING…';
      this.mapStatus.textContent = 'Downloading and verifying the complete city package…';
      try {
        await downloadSteelCityMap({
          onProgress: (loaded, total) => {
            const pct = total > 0 ? Math.round(loaded / total * 100) : 0;
            this.mapButton.textContent = 'DOWNLOADING ' + pct + '%';
          },
        });
        this.mapStatus.textContent = 'Map verified and saved. Restarting to load it…';
        location.reload();
      } catch (err) {
        this.mapStatus.textContent = 'Download failed: ' + (err?.message ?? String(err));
        this.mapButton.disabled = false;
        this.mapButton.textContent = 'RETRY MAP DOWNLOAD';
      }
    });

    el('div', 'ow-boot-hint', w,
      'Carson is the only selectable character. The full city map is stored for offline play.');'''
    if anchor not in s: raise SystemExit('boot map UI insertion anchor missing')
    map_start = s.index(anchor)
    map_end = s.index(');', map_start) + 2
    s = s[:map_start] + map_ui + s[map_end:]

    anchor = "    this._offWorld?.();"
    if anchor not in s: raise SystemExit('boot map listener cleanup anchor missing')
    s = s.replace(anchor, anchor + "\n    window.removeEventListener('onebbm:map-status', this._mapListener);", 1)
    p.write_text(s)

print('Verified full-city map cache, downloader, world restore, and boot-screen map control applied')

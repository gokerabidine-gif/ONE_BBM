#!/usr/bin/env python3
from pathlib import Path
import sys
root = Path(sys.argv[1])
module = r'''import * as THREE from 'three';

const DB = 'one-bbm-static-geometry-v1';
const STORE = 'building-far-tiles';
const VERSION = 1;
const MAX_TILE_BYTES = 8 * 1024 * 1024;

function openDb() {
  return new Promise((resolve, reject) => {
    if (!globalThis.indexedDB) return reject(new Error('IndexedDB unavailable'));
    const req = indexedDB.open(DB, 1);
    req.onupgradeneeded = () => {
      if (!req.result.objectStoreNames.contains(STORE)) req.result.createObjectStore(STORE, { keyPath: 'key' });
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error ?? new Error('Geometry cache open failed'));
  });
}
function reqValue(req) {
  return new Promise((resolve, reject) => {
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error ?? new Error('Geometry cache request failed'));
  });
}
async function getRecord(key) {
  const db = await openDb();
  try { return await reqValue(db.transaction(STORE, 'readonly').objectStore(STORE).get(key)); }
  finally { db.close(); }
}
async function putRecord(record) {
  const db = await openDb();
  try {
    const tx = db.transaction(STORE, 'readwrite');
    await reqValue(tx.objectStore(STORE).put(record));
  } finally { db.close(); }
}
async function compress(text) {
  if (typeof CompressionStream !== 'function') throw new Error('Geometry compression unavailable');
  const stream = new Blob([text]).stream().pipeThrough(new CompressionStream('gzip'));
  return new Uint8Array(await new Response(stream).arrayBuffer());
}
async function decompress(bytes) {
  if (typeof DecompressionStream !== 'function') throw new Error('Geometry decompression unavailable');
  const stream = new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'));
  return await new Response(stream).text();
}

function encodeNode(object, materialKeys, protoIds) {
  const node = {
    type: object.isLOD ? 'lod' : object.isInstancedMesh ? 'instanced' : object.isMesh ? 'mesh' : 'group',
    name: object.name || '', matrix: object.matrix.toArray(), matrixAutoUpdate: object.matrixAutoUpdate,
    visible: object.visible, renderOrder: object.renderOrder, userData: object.userData ?? {},
    castShadow: object.castShadow, receiveShadow: object.receiveShadow, frustumCulled: object.frustumCulled,
    children: [],
  };
  if (object.isLOD) {
    node.autoUpdate = object.autoUpdate;
    node.levels = object.levels.map((level) => level.distance);
  }
  if (object.isInstancedMesh) {
    const protoId = object.name.startsWith('bi_') ? object.name.slice(3) : protoIds.get(object.geometry.uuid);
    if (!protoId) throw new Error('Unmapped instanced building prototype: ' + object.name);
    node.protoId = protoId;
    node.count = object.count;
    node.matrices = Array.from(object.instanceMatrix.array);
    node.instanceColor = object.instanceColor ? Array.from(object.instanceColor.array) : null;
    node.instanceColorItemSize = object.instanceColor?.itemSize ?? 3;
  } else if (object.isMesh) {
    const mat = Array.isArray(object.material) ? object.material[0] : object.material;
    const materialKey = materialKeys.get(mat?.uuid);
    if (!materialKey) throw new Error('Unmapped building material: ' + object.name);
    node.materialKey = materialKey;
    node.geometry = object.geometry.toJSON();
  }
  node.children = object.children.map((child) => encodeNode(child, materialKeys, protoIds));
  return node;
}

function decodeNode(data, lib, geometryLoader) {
  let object;
  if (data.type === 'lod') {
    object = new THREE.LOD();
    object.autoUpdate = data.autoUpdate !== false;
  } else if (data.type === 'instanced') {
    const proto = lib.protos.get(data.protoId);
    if (!proto) throw new Error('Missing cached prototype ' + data.protoId);
    object = new THREE.InstancedMesh(proto.geo, lib.mat(proto.key), data.count);
    object.name = data.name;
    for (let i = 0; i < data.count; i++) {
      const matrix = new THREE.Matrix4().fromArray(data.matrices, i * 16);
      object.setMatrixAt(i, matrix);
    }
    if (data.instanceColor) {
      object.instanceColor = new THREE.InstancedBufferAttribute(new Float32Array(data.instanceColor), data.instanceColorItemSize || 3);
      object.instanceColor.needsUpdate = true;
    }
    object.instanceMatrix.needsUpdate = true;
    object.computeBoundingSphere();
    object.computeBoundingBox();
  } else if (data.type === 'mesh') {
    const geometry = geometryLoader.parse(data.geometry);
    object = new THREE.Mesh(geometry, lib.mat(data.materialKey));
    object.name = data.name;
  } else {
    object = new THREE.Group();
    object.name = data.name;
  }
  if (data.matrix) object.matrix.fromArray(data.matrix);
  object.matrixAutoUpdate = data.matrixAutoUpdate !== false;
  object.visible = data.visible !== false;
  object.renderOrder = data.renderOrder ?? 0;
  object.userData = data.userData ?? {};
  if ('castShadow' in data) object.castShadow = data.castShadow;
  if ('receiveShadow' in data) object.receiveShadow = data.receiveShadow;
  if ('frustumCulled' in data) object.frustumCulled = data.frustumCulled;
  for (let i = 0; i < data.children.length; i++) {
    const child = decodeNode(data.children[i], lib, geometryLoader);
    if (data.type === 'lod') object.addLevel(child, data.levels?.[i] ?? 0);
    else object.add(child);
  }
  return object;
}

function materialIndex(lib) {
  const keys = new Map();
  for (const [key, material] of lib._mats) keys.set(material.uuid, key);
  return keys;
}
function prototypeIndex(lib) {
  const ids = new Map();
  for (const [id, proto] of lib.protos) ids.set(proto.geo.uuid, id);
  return ids;
}
function cacheKey(tx, tz) { return 'v' + VERSION + ':ultra:' + tx + ',' + tz; }

export async function restoreFarTile(tx, tz, lib) {
  try {
    const record = await getRecord(cacheKey(tx, tz));
    if (!record?.bytes || record.version !== VERSION) return null;
    const json = JSON.parse(await decompress(new Uint8Array(record.bytes)));
    if (json.version !== VERSION || json.tx !== tx || json.tz !== tz) return null;
    const group = decodeNode(json.root, lib, new THREE.BufferGeometryLoader());
    const sphere = json.sphere ? new THREE.Sphere(new THREE.Vector3(...json.sphere.center), json.sphere.radius) : null;
    let lod = null;
    group.traverse((o) => { if (o.isLOD && !lod) lod = o; });
    return { group, handles: [], colMeshes: [], lod, sphere, stats: json.stats ?? {} };
  } catch (err) {
    console.warn('[geometry-cache] cached far tile rejected', tx, tz, err);
    return null;
  }
}

export function scheduleFarTileSave(rec, built, lib) {
  if (!rec || !built?.group || !globalThis.indexedDB) return;
  const save = async () => {
    try {
      const root = encodeNode(built.group, materialIndex(lib), prototypeIndex(lib));
      const sphere = built.sphere ? { center: built.sphere.center.toArray(), radius: built.sphere.radius } : null;
      const bytes = await compress(JSON.stringify({ version: VERSION, tx: rec.tx, tz: rec.tz, root, sphere, stats: built.stats }));
      if (bytes.byteLength > MAX_TILE_BYTES) return;
      await putRecord({ key: cacheKey(rec.tx, rec.tz), version: VERSION, bytes: bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength), savedAt: Date.now() });
    } catch (err) {
      console.warn('[geometry-cache] far tile was not cached', rec.key, err);
    }
  };
  const idle = globalThis.requestIdleCallback;
  if (typeof idle === 'function') idle(() => { void save(); }, { timeout: 2500 });
  else setTimeout(() => { void save(); }, 1200);
}
'''
(root / 'src/buildings/geometry-cache.js').write_text(module)
p = root / 'src/buildings/index.js'
s = p.read_text()
anchor = "import { farFacadeDetailDistance } from './quality.js';"
if 'restoreFarTile' not in s:
    if anchor not in s: raise SystemExit('building import anchor missing')
    s = s.replace(anchor, anchor + "\nimport { restoreFarTile, scheduleFarTileSave } from './geometry-cache.js';", 1)
old = """  _buildFar(rec) {
    if (!this._live(rec)) return;
    this._buildTileInSlices(rec, 1);
  }"""
new = """  async _buildFar(rec) {
    if (!this._live(rec)) return;
    let cached = await restoreFarTile(rec.tx, rec.tz, this.lib);
    if (!this._live(rec)) {
      if (cached) releaseTile(cached, null);
      return;
    }
    if (cached) {
      setVisible(cached, true);
      rec.far = cached;
      rec.group.add(cached.group);
      this.render?.patchMaterials?.(cached.group);
      this._refreshCull(rec, cached);
      this._accum(cached.stats);
      return;
    }
    this._buildTileInSlices(rec, 1);
  }"""
new = """  async _buildFar(rec) {
    if (!this._live(rec)) return;
    let cached = await restoreFarTile(rec.tx, rec.tz, this.lib);
    if (!this._live(rec)) {
      if (cached) releaseTile(cached, null);
      return;
    }
    if (cached) {
      setVisible(cached, true);
      rec.far = cached;
      rec.group.add(cached.group);
      this.render?.patchMaterials?.(cached.group);
      this._refreshCull(rec, cached);
      this._accum(cached.stats);
      return;
    }
    let built = null;
    try {
      const plans = this._plans(rec);"""
if 'async _buildFar(rec)' not in s:
    if old not in s: raise SystemExit('_buildFar insertion anchor missing')
    s = s.replace(old, new, 1)
old2 = """          this._accum(built.stats);
          if (!lod) setVisible(rec.far, false);"""
new2 = """          this._accum(built.stats);
          if (lod) scheduleFarTileSave(rec, built, this.lib);
          if (!lod) setVisible(rec.far, false);"""
if 'if (lod) scheduleFarTileSave(rec, built, this.lib);' not in s:
    if old2 not in s: raise SystemExit('sliced tile publish cache anchor missing')
    s = s.replace(old2, new2, 1)
old3 = "    this.schedule(() => this._buildFar(rec), 1);"
new3 = """    this.schedule(() => {
      const world = this.world;
      if (world) world._sectorJobs++;
      Promise.resolve(this._buildFar(rec))
        .catch((err) => this._buildFailed(rec, 'far-cache', err))
        .finally(() => { if (world) world._sectorJobs = Math.max(0, world._sectorJobs - 1); });
    }, 1);"""
if 'Promise.resolve(this._buildFar(rec))' not in s:
    if old3 not in s: raise SystemExit('far tile scheduling anchor missing')
    s = s.replace(old3, new3, 1)
p.write_text(s)
print('Added versioned IndexedDB cache for far building geometry sectors')

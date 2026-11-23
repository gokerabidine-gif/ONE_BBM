#!/usr/bin/env python3
from pathlib import Path
import sys
import os

arg = Path(sys.argv[1])
root = arg.resolve()
# If the workflow is already inside PROJECT_DIR but passes its relative name,
# that nested directory won't exist. Use the current project directory.
if not root.exists() and not arg.is_absolute():
    root = Path.cwd().resolve()
os.chdir(root)

# Keep the ultra visual preset on Android, without the adaptive scale governor.
p = root / 'src/main.js'
s = p.read_text()
for old, new in [
    ('renderScale: 1.18', 'renderScale: 1.0'),
    ('shadowMapSize: 4096', 'shadowMapSize: 2048'),
    ('cascades: 4', 'cascades: 3'),
    ('shadowDistance: 430', 'shadowDistance: 320'),
    ('drawDistance: 6000', 'drawDistance: 4500'),
    ('streamRadius: 1000', 'streamRadius: 650'),
    ('tileBuildBudgetMs: 8', 'tileBuildBudgetMs: 6'),
    ('particleBudget: 24000', 'particleBudget: 12000'),
    ('decalBudget: 512', 'decalBudget: 256'),
    ('trafficBudget: 76', 'trafficBudget: 38'),
    ('pedBudget: 48', 'pedBudget: 0'),
    ('lodBias: 0.85', 'lodBias: 0.95'),
]:
    s = s.replace(old, new)
needle = 'if (isAndroidMobile) { gov.minScale = 0.62; gov.targetMs = 18.5; gov.slowMs = 21; gov.trimStep = 0.12; gov._warmup = 24; gov.ignoreStreamingBusy = true; }'
if needle in s:
    s = s.replace(needle, 'if (isAndroidMobile) { gov.enabled = false; gov.minScale = 1.0; gov.maxScale = 1.0; gov._warmup = 999999; }', 1)
elif 'gov.enabled = false' not in s:
    raise SystemExit('Android governor line was not found; refusing to patch blindly')
p.write_text(s)

p = root / 'src/props/index.js'
s = p.read_text()
anchor = '    this.nearRadius = q.streamRadius >= 700 ? 195 : q.streamRadius >= 450 ? 175 : 140;'
if anchor in s:
    s = s.replace(anchor, "    this.nearRadius = /Android/i.test(navigator.userAgent) ? 250 : (q.streamRadius >= 700 ? 195 : q.streamRadius >= 450 ? 175 : 140);", 1)
elif 'this.nearRadius = /Android/i.test(navigator.userAgent)' not in s:
    raise SystemExit('Prop near-radius anchor missing')
anchor = '    this.midRadius = Math.min(q.streamRadius ?? 520, this.nearRadius + 230);'
if anchor in s:
    s = s.replace(anchor, "    this.midRadius = /Android/i.test(navigator.userAgent) ? Math.min(q.streamRadius ?? 650, 540) : Math.min(q.streamRadius ?? 520, this.nearRadius + 230);", 1)
elif 'this.midRadius = /Android/i.test(navigator.userAgent)' not in s:
    raise SystemExit('Prop mid-radius anchor missing')
p.write_text(s)

# Android: remove every non-player pedestrian/character. The player avatar is
# managed by src/player and is not part of PedSystem.
p = root / 'src/peds/index.js'
s = p.read_text()
old = '    this.budget = Math.max(4, this.q.pedBudget ?? 40);'
new = '    this._androidNoNpc = /Android/i.test(navigator.userAgent);\n    this.budget = this._androidNoNpc ? 0 : Math.max(4, this.q.pedBudget ?? 40);'
if old not in s: raise SystemExit('PedSystem budget anchor missing')
s = s.replace(old, new, 1)
old = '    this.ambientBodies = Math.max(6, Math.min(38, Math.round(this.budget * 0.36)));'
new = '    this.ambientBodies = this._androidNoNpc ? 0 : Math.max(6, Math.min(38, Math.round(this.budget * 0.36)));'
if old not in s: raise SystemExit('PedSystem ambient-body anchor missing')
s = s.replace(old, new, 1)
old = '    this.maxBodies = this.ambientBodies + CREW_MAX + HOSTILE_BODIES;'
new = '    this.maxBodies = this._androidNoNpc ? 0 : this.ambientBodies + CREW_MAX + HOSTILE_BODIES;'
if old not in s: raise SystemExit('PedSystem max-body anchor missing')
s = s.replace(old, new, 1)
old = '    this.crewAuto = true;          // spawn them as soon as there is a player'
new = '    this.crewAuto = !this._androidNoNpc; // companions disabled on Android'
if old not in s: raise SystemExit('Crew auto anchor missing')
s = s.replace(old, new, 1)
old = '  update(dt, ctx) {\n    const t0 = performance.now();'
new = '  update(dt, ctx) {\n    if (this._androidNoNpc) { this.stats.live = 0; this.stats.target = 0; this.stats.crew = 0; this.stats.ms = 0; return; }\n    const t0 = performance.now();'
if old not in s: raise SystemExit('PedSystem update anchor missing')
s = s.replace(old, new, 1)
old = '  spawnHostile(position, opts) {\n    return this.hostiles.spawn(position, opts);'
new = '  spawnHostile(position, opts) {\n    if (this._androidNoNpc) return null;\n    return this.hostiles.spawn(position, opts);'
if old not in s: raise SystemExit('Hostile spawn API anchor missing')
s = s.replace(old, new, 1)
old = '  spawnCrew(ids = null) {\n    this.crewAuto = ids === null;\n    return this.crew.spawn(ids);'
new = '  spawnCrew(ids = null) {\n    if (this._androidNoNpc) { this.crewAuto = false; this.crew.despawn(); return 0; }\n    this.crewAuto = ids === null;\n    return this.crew.spawn(ids);'
if old not in s: raise SystemExit('Crew spawn API anchor missing')
s = s.replace(old, new, 1)
p.write_text(s)

# Guard direct hostile and crew subsystem spawn paths too.
p = root / 'src/peds/hostile.js'
s = p.read_text()
old = '  spawn(position, opts = DEF) {\n    if (!position || !Number.isFinite(position.x)) return null;'
new = '  spawn(position, opts = DEF) {\n    if (this.sys._androidNoNpc || !position || !Number.isFinite(position.x)) return null;'
if old not in s: raise SystemExit('Hostile class spawn anchor missing')
p.write_text(s.replace(old, new, 1))

p = root / 'src/peds/crew.js'
s = p.read_text()
old = '  spawn(ids = null) {\n    const want = this._resolveIds(ids);'
new = '  spawn(ids = null) {\n    if (this.sys._androidNoNpc) { this.despawn(); return 0; }\n    const want = this._resolveIds(ids);'
if old not in s: raise SystemExit('Crew class spawn anchor missing')
p.write_text(s.replace(old, new, 1))

# Wait for IndexedDB transaction completion to ensure cache writes commit.
for rel in ['src/buildings/geometry-cache.js', 'src/world/sector-cache.js', 'src/props/tile-cache.js']:
    p = root / rel
    if not p.exists():
        raise SystemExit('Expected persistent cache module missing: ' + rel)
    s = p.read_text()
    old = "async function putRecord(record) {\n  const db = await openDb();\n  try {\n    const tx = db.transaction(STORE, 'readwrite');\n    await reqValue(tx.objectStore(STORE).put(record));\n  } finally { db.close(); }\n}"
    new = "async function putRecord(record) {\n  const db = await openDb();\n  try {\n    const tx = db.transaction(STORE, 'readwrite');\n    const done = new Promise((resolve, reject) => { tx.oncomplete = resolve; tx.onerror = () => reject(tx.error); tx.onabort = () => reject(tx.error || new Error('cache transaction aborted')); });\n    tx.objectStore(STORE).put(record);\n    await done;\n  } finally { db.close(); }\n}"
    if old in s: s = s.replace(old, new, 1)
    if 'async function writeRecord(record)' in s:
        old = "async function writeRecord(record) {\n  const db = await openDb();\n  try {\n    const tx = db.transaction(STORE, 'readwrite');\n    await reqValue(tx.objectStore(STORE).put(record));\n  } finally { db.close(); }\n}"
        new = "async function writeRecord(record) {\n  const db = await openDb();\n  try {\n    const tx = db.transaction(STORE, 'readwrite');\n    const done = new Promise((resolve, reject) => { tx.oncomplete = resolve; tx.onerror = () => reject(tx.error); tx.onabort = () => reject(tx.error || new Error('cache transaction aborted')); });\n    tx.objectStore(STORE).put(record);\n    await done;\n  } finally { db.close(); }\n}"
        if old in s: s = s.replace(old, new, 1)
    old = "async function write(v){const db=await openDb();try{const tx=db.transaction(STORE,'readwrite');await req(tx.objectStore(STORE).put(v));}finally{db.close();}}"
    new = "async function write(v){const db=await openDb();try{const tx=db.transaction(STORE,'readwrite');const done=new Promise((resolve,reject)=>{tx.oncomplete=resolve;tx.onerror=()=>reject(tx.error);tx.onabort=()=>reject(tx.error||new Error('cache transaction aborted'));});tx.objectStore(STORE).put(v);await done;}finally{db.close();}}"
    if old in s: s = s.replace(old, new, 1)
    s = s.replace('const VERSION = 1;', 'const VERSION = 2;')
    s = s.replace('VERSION=1,', 'VERSION=2,')
    p.write_text(s)
print('Mobile visual stability and persistent cache transaction fixes applied')

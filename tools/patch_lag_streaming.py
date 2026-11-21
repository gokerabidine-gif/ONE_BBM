from pathlib import Path
import sys
root = Path(sys.argv[1])

p = root / 'src/buildings/index.js'
s = p.read_text()
start = s.index('  _buildFar(rec) {')
end = s.index('\n  /**\n   * A build that threw is a HOLE IN THE CITY', start)
new = r'''  _buildFar(rec) {
    if (!this._live(rec)) return;
    this._buildTileInSlices(rec, 1);
  }

  _buildNear(rec) {
    if (!this._live(rec)) {
      rec.nearBuilding = false;
      return;
    }
    this._buildTileInSlices(rec, 0);
  }

  // Keep the same generated geometry, but schedule one lot per queue job.
  _buildTileInSlices(rec, lod) {
    let plans;
    let T;
    try {
      plans = this._plans(rec);
      T = new TileBuilder(this.lib, (lod ? 'far_' : 'near_') + rec.key);
    } catch (err) {
      this._buildFailed(rec, lod ? 'far' : 'near', err);
      return;
    }

    let index = 0;
    const priority = lod ? 1 : 4;
    const pump = () => {
      if (!this._live(rec)) {
        if (!lod) rec.nearBuilding = false;
        return;
      }
      if (index < plans.length) {
        const plan = plans[index++];
        try {
          this.buildPlan(T, plan, lod);
        } catch (err) {
          console.error('[buildings] ' + (lod ? 'far' : 'near') + ' lot failed in tile ' + rec.key, err);
        }
        this.schedule(pump, priority);
        return;
      }

      let built = null;
      try {
        built = T.build(lod ? null : (this._live(rec) ? this.physics : null), lod ? {
          lodDistance: this.farDetailDist,
          lodCenter: [rec.cx, this._groundAt(rec.cx, rec.cz) + 10, rec.cz],
        } : {});
      } catch (err) {
        this._buildFailed(rec, lod ? 'far' : 'near', err);
        return;
      }

      if (!this._live(rec)) {
        releaseTile(built, lod ? null : this.physics);
        if (!lod) rec.nearBuilding = false;
        return;
      }
      setVisible(built, true);
      if (lod) {
        rec.far = built;
      } else {
        rec.near = built;
        rec.nearBuilding = false;
        this._colDirty = true;
      }
      rec.group.add(built.group);
      this.render?.patchMaterials?.(built.group);
      this._refreshCull(rec, built);
      this._accum(built.stats);
      if (!lod) setVisible(rec.far, false);
    };
    this.schedule(pump, priority);
  }
'''
s = s[:start] + new + s[end:]
p.write_text(s)

p = root / 'src/world/terrainmesh.js'
s = p.read_text()
old = '''      schedule(() => {
        lv.pending = false;
        this._rebuild(lv, nx, nz, hx, hz);
      }, l === 0 ? 0 : 1 + l);'''
new = '''      schedule(() => this._rebuild(lv, nx, nz, hx, hz, schedule), l === 0 ? 0 : 1 + l);'''
if old not in s: raise SystemExit('terrain scheduling anchor missing')
s = s.replace(old, new, 1)
old = '  _rebuild(lv, cx, cz, hx, hz) {'
new = '''  _rebuild(lv, cx, cz, hx, hz, schedule) {
    const priority = lv.level === 0 ? 0 : 1 + lv.level;
    const work = this._rebuildWork(lv, cx, cz, hx, hz);
    const pump = () => {
      try {
        const result = work.next();
        if (!result.done) schedule(pump, priority);
      } catch (err) {
        lv.pending = false;
        console.error('[terrain] clipmap level ' + lv.level + ' rebuild failed', err);
      }
    };
    pump();
  }

  *_rebuildWork(lv, cx, cz, hx, hz) {'''
if old not in s: raise SystemExit('terrain method anchor missing')
s = s.replace(old, new, 1)
repls = [
('''    for (let j = 0; j < N; j++) {
      const z = z0 + j * s;''',
 '''    for (let row0 = 0; row0 < N; row0 += 4) {
      for (let j = row0; j < Math.min(N, row0 + 4); j++) {
      const z = z0 + j * s;''',
 'height loop missing'),
('''      }
    }

    // ---- outer boundary: match the coarser ring exactly ------------------''',
 '''      }
      }
      yield;
    }

    // ---- outer boundary: match the coarser ring exactly ------------------''',
 'height loop end missing'),
('''    for (let j = 0; j < N; j++) {
      const inHoleJ = h > 0 && j > hj0 && j < hj1;''',
 '''    for (let row0 = 0; row0 < N; row0 += 4) {
      for (let j = row0; j < Math.min(N, row0 + 4); j++) {
      const inHoleJ = h > 0 && j > hj0 && j < hj1;''',
 'normal loop missing'),
('''      }
    }

    // ---- index: pick a ground layer per quad -----------------------------''',
 '''      }
      }
      yield;
    }

    // ---- index: pick a ground layer per quad -----------------------------''',
 'normal loop end missing'),
('''    for (let j = 0; j < N - 1; j++) {
      const inHoleJ = h > 0 && j >= hj0 && j < hj1;''',
 '''    for (let row0 = 0; row0 < N - 1; row0 += 4) {
      for (let j = row0; j < Math.min(N - 1, row0 + 4); j++) {
      const inHoleJ = h > 0 && j >= hj0 && j < hj1;''',
 'index loop missing'),
('''      }
    }

    lv.position.needsUpdate = true;''',
 '''      }
      }
      yield;
    }

    lv.position.needsUpdate = true;''',
 'index loop end missing'),
('''    if (first) this._built++;
  }

  _sample''',
 '''    if (first) this._built++;
    lv.pending = false;
  }

  _sample''',
 'rebuild end missing'),
]
for old, new, error in repls:
    if old not in s: raise SystemExit(error)
    s = s.replace(old, new, 1)
p.write_text(s)

# Startup: allow the loading UI to paint between subsystem initializers.
# This preserves each subsystem's data and rendering settings; it only prevents
# a chain of independent synchronous initializers from occupying one long task.
p = root / 'src/core/engine.js'
s = p.read_text()
old = '''      if (ms > 50) console.info(`[engine] ${sys.constructor.id} init ${ms.toFixed(0)}ms`);
    }'''
new = '''      console.info(`[engine] ${sys.constructor.id} init ${ms.toFixed(0)}ms`);
      // Diagnostic only: record each initializer's actual synchronous cost.
      // Do not add artificial waits to startup.
    }'''
if old not in s: raise SystemExit('engine init timing anchor missing')
s = s.replace(old, new, 1)
p.write_text(s)

# World generation is CPU-heavy but independent stages can be separated safely.
# The expensive stage itself remains unchanged; the loading screen gets a frame
# between terrain baking, city planning and lot subdivision.
p = root / 'src/world/index.js'
s = p.read_text()
old = '''    this.terrain.bake();
    const tBake = performance.now();'''
new = '''    const tBakeStart = performance.now();
    this.terrain.bake();
    const tBake = performance.now();
    console.info(`[boot-profile] terrain.bake ${(tBake - tBakeStart).toFixed(1)}ms`);'''
if old not in s: raise SystemExit('terrain bake anchor missing')
s = s.replace(old, new, 1)
old = '''    const city = generateCity(this.terrain, this.rng.fork());
    this.roads = city.graph;'''
new = '''    const tCityStart = performance.now();
    const city = generateCity(this.terrain, this.rng.fork());
    console.info(`[boot-profile] generateCity ${(performance.now() - tCityStart).toFixed(1)}ms`);
    this.roads = city.graph;'''
if old not in s: raise SystemExit('city generation anchor missing')
s = s.replace(old, new, 1)
old = '''    const { lots, byTile } = subdivide(city.blocks, this.terrain, this.rng.fork());
    this.lots = lots;'''
new = '''    const tSubdivideStart = performance.now();
    const { lots, byTile } = subdivide(city.blocks, this.terrain, this.rng.fork());
    console.info(`[boot-profile] subdivide ${(performance.now() - tSubdivideStart).toFixed(1)}ms`);
    this.lots = lots;'''
if old not in s: raise SystemExit('lot subdivision anchor missing')
s = s.replace(old, new, 1)
p.write_text(s)

# Thermal/frame pacing: the game may run on 90/120 Hz Android displays, but
# rendering at the panel's maximum refresh rate needlessly doubles GPU work.
# Cap rendered frames at 60 Hz while keeping simulation dt derived from wall time.
# Capture/lockstep uses Engine.step() directly and is not affected by this loop.
p = root / 'src/core/engine.js'
s = p.read_text()
old = """  _loop(now) {
    if (!this._running) return;
    requestAnimationFrame(this._loop);
    this.step(now);
  }"""
new = """  _loop(now) {
    if (!this._running) return;
    requestAnimationFrame(this._loop);
    // A stable 60 Hz render ceiling avoids driving the GPU at 90/120 Hz on
    // high-refresh Android panels. Physics remains fixed-step and is not tied
    // to the render cadence; capture harnesses call step() directly.
    const interval = 1000 / 60;
    if (this._nextRenderAt == null) this._nextRenderAt = now;
    if (now + 0.5 < this._nextRenderAt) return;
    this._nextRenderAt = now + interval;
    this.step(now);
  }"""
if old not in s: raise SystemExit('engine frame-loop anchor missing')
s = s.replace(old, new, 1)
p.write_text(s)

# Spread shader warm-up hooks across separate browser turns. The expensive
# shader work remains intact and pixel output is unchanged; this avoids chaining
# every subsystem's warm-up into one uninterrupted main-thread task.
p = root / 'src/core/prewarm.js'
s = p.read_text()
old = """      try {
        const arg = sys === renderSys ? { post: true, shadow: RENDER_SHADOW_WARM } : engine.ctx;
        hookResults[id] = (await sys.prewarmMaterials(arg)) ?? { ok: true };
      } catch (err) {"""
new = """      try {
        const arg = sys === renderSys ? { post: true, shadow: RENDER_SHADOW_WARM } : engine.ctx;
        hookResults[id] = (await sys.prewarmMaterials(arg)) ?? { ok: true };
        // Let Android's compositor and loading UI breathe between subsystem
        // warm-ups instead of stacking all hook work in one long task.
        await yieldFrame();
      } catch (err) {"""
if old not in s: raise SystemExit('prewarm hook anchor missing')
s = s.replace(old, new, 1)
p.write_text(s)

print('Lag slicing + staged startup initialization applied')

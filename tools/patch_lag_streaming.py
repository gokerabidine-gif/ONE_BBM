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
print('Lag slicing patch applied')

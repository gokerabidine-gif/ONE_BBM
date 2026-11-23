#!/usr/bin/env python3
"""Register streamed high-detail road sectors with the city hierarchical culler."""
from pathlib import Path
import sys

root = Path(sys.argv[1]).resolve()
p = root / "src/world/index.js"
s = p.read_text()
if "_registerRoadSectorCull(rec)" in s:
    print("Road-sector hierarchical culling already installed.")
    raise SystemExit(0)

old = "  static deps = ['materials', 'physics'];"
new = "  static deps = ['materials', 'physics', 'render'];"
if old not in s: raise SystemExit("WorldSystem dependency anchor missing")
s = s.replace(old, new, 1)

old = "    this.physics = physics;\n    this.materials = materials;"
new = "    this.physics = physics;\n    this.render = ctx.get('render');\n    this.materials = materials;"
if old not in s: raise SystemExit("World render dependency assignment anchor missing")
s = s.replace(old, new, 1)

old = "const rec = { sx, sz, group: null, job: null, pend: null, pendI: 0 };"
new = "const rec = { sx, sz, group: null, job: null, pend: null, pendI: 0, cullOff: null };"
if old not in s: raise SystemExit("road-sector record anchor missing")
s = s.replace(old, new, 1)

# Both the immediate attach path and amortised attach path share this helper.
old = """            this.root.add(out.group);
            const far0 = this._far.get(`${sx},${sz}`);
"""
new = """            this.root.add(out.group);
            this._registerRoadSectorCull(rec);
            const far0 = this._far.get(`${sx},${sz}`);
"""
if old not in s: raise SystemExit("immediate road-sector attach anchor missing")
s = s.replace(old, new, 1)

old = """          this.root.add(out.group);
          this._attachQ.push(rec);
"""
new = """          this.root.add(out.group);
          this._registerRoadSectorCull(rec);
          this._attachQ.push(rec);
"""
if old not in s: raise SystemExit("amortised road-sector attach anchor missing")
s = s.replace(old, new, 1)

method = """  _registerRoadSectorCull(rec) {
    if (!rec?.group || rec.cullOff || !this.render?.registerCullGroup) return;
    const cx = (rec.sx + 0.5) * SECTOR;
    const cz = (rec.sz + 0.5) * SECTOR;
    // Road meshes can span the full sector and cross elevation changes.
    rec.cullOff = this.render.registerCullGroup(rec.group, {
      center: [cx, 18, cz],
      radius: SECTOR * 0.7072 + 72,
      maxDistance: SECTOR_RADIUS_MAX + SECTOR * 0.55,
    });
  }

"""
anchor = "  _dropSector(rec) {"
if anchor not in s: raise SystemExit("road-sector unload method anchor missing")
s = s.replace(anchor, method + anchor, 1)

old = """  _dropSector(rec) {
    if (rec.job) {
"""
new = """  _dropSector(rec) {
    if (rec.cullOff) {
      rec.cullOff();
      rec.cullOff = null;
    } else if (rec.group) {
      this.render?.unregisterCullGroup?.(rec.group);
    }
    if (rec.job) {
"""
if old not in s: raise SystemExit("road-sector cull unregister anchor missing")
s = s.replace(old, new, 1)
p.write_text(s)
print("Registered high-detail road sectors for whole-group camera culling; unload unregisters cleanly.")

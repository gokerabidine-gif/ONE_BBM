#!/usr/bin/env python3
from pathlib import Path
import sys
arg = Path(sys.argv[1])\nroot = arg.resolve()\nif not root.exists() and not arg.is_absolute():\n    root = Path.cwd().resolve()
p = root / "src/peds/index.js"
s = p.read_text()
pairs = [
("    this.budget = Math.max(4, this.q.pedBudget ?? 40);","    this._androidNoNpc = /Android/i.test(navigator.userAgent);\n    this.budget = this._androidNoNpc ? 0 : Math.max(4, this.q.pedBudget ?? 40);"),
("    this.ambientBodies = Math.max(6, Math.min(38, Math.round(this.budget * 0.36)));","    this.ambientBodies = this._androidNoNpc ? 0 : Math.max(6, Math.min(38, Math.round(this.budget * 0.36)));"),
("    this.maxBodies = this.ambientBodies + CREW_MAX + HOSTILE_BODIES;","    this.maxBodies = this._androidNoNpc ? 0 : this.ambientBodies + CREW_MAX + HOSTILE_BODIES;"),
("  update(dt, ctx) {\n    const t0 = performance.now();","  update(dt, ctx) {\n    if (this._androidNoNpc) { this.stats.live = 0; this.stats.target = 0; this.stats.crew = 0; this.stats.ms = 0; return; }\n    const t0 = performance.now();"),
("  spawnHostile(position, opts) {\n    return this.hostiles.spawn(position, opts);","  spawnHostile(position, opts) {\n    if (this._androidNoNpc) return null;\n    return this.hostiles.spawn(position, opts);"),
("  spawnCrew(ids = null) {\n    this.crewAuto = ids === null;\n    return this.crew.spawn(ids);","  spawnCrew(ids = null) {\n    if (this._androidNoNpc) { this.crewAuto = false; this.crew.despawn(); return 0; }\n    this.crewAuto = ids === null;\n    return this.crew.spawn(ids);")
]
for old,new in pairs:
    if old in s: s=s.replace(old,new,1)
elifCheck=False
# Validate each patched anchor is present; catches source drift instead of silently missing.
checks=["this._androidNoNpc = /Android/i.test(navigator.userAgent);","this.ambientBodies = this._androidNoNpc ? 0","this.maxBodies = this._androidNoNpc ? 0","if (this._androidNoNpc) { this.stats.live = 0","spawnHostile(position, opts) {\n    if (this._androidNoNpc) return null;","spawnCrew(ids = null) {\n    if (this._androidNoNpc)"]
for check in checks:
    if check not in s: raise SystemExit("NPC patch validation failed: "+check)
p.write_text(s)
p=root/"src/peds/hostile.js"; s=p.read_text()
old="  spawn(position, opts = DEF) {\n    if (!position || !Number.isFinite(position.x)) return null;"
new="  spawn(position, opts = DEF) {\n    if (this.sys._androidNoNpc || !position || !Number.isFinite(position.x)) return null;"
if old in s:s=s.replace(old,new,1)
elif "this.sys._androidNoNpc || !position" not in s: raise SystemExit("hostile guard missing")
p.write_text(s)
p=root/"src/peds/crew.js"; s=p.read_text()
old="  spawn(ids = null) {\n    const want = this._resolveIds(ids);"
new="  spawn(ids = null) {\n    if (this.sys._androidNoNpc) { this.despawn(); return 0; }\n    const want = this._resolveIds(ids);"
if old in s:s=s.replace(old,new,1)
elif "if (this.sys._androidNoNpc) { this.despawn(); return 0; }" not in s: raise SystemExit("crew guard missing")
p.write_text(s)
print("Android NPC systems disabled; player controller untouched.")

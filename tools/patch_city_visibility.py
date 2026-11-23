#!/usr/bin/env python3
"""Apply stable, camera-driven culling to all registered city tile groups."""
from pathlib import Path
import sys

root = Path(sys.argv[1]).resolve()
p = root / "src/render/cull.js"
s = p.read_text()

entry_old = """        dynamic: false,
        hidden: false,
      };
"""
entry_new = """        dynamic: false,
        hidden: false,
        distanceMargin: 0,
      };
"""
opts_old = """    entry.radius = Math.max(0.5, opts.radius ?? this._autoRadius(object));
    entry.maxDistance = opts.maxDistance ?? 0;
    entry.dynamic = opts.dynamic === true;
"""
opts_new = """    entry.radius = Math.max(0.5, opts.radius ?? this._autoRadius(object));
    entry.maxDistance = opts.maxDistance ?? 0;
    // Larger city groups receive a wider, bounded transition band.
    entry.distanceMargin = Math.max(12, Math.min(64, entry.radius * 0.10));
    entry.dynamic = opts.dynamic === true;
"""
update_old = """      const c = g.center;
      let show = true;
      const far = g.maxDistance > 0 ? g.maxDistance : dd;
      if (this.camPos.distanceTo(c) - g.radius > far) {
        show = false;
        this.stats.groupsCulledDistance++;
      } else if (!this.sphereVisible(c.x, c.y, c.z, g.radius)) {
        show = false;
        this.stats.groupsCulledFrustum++;
      } else {
        this.stats.groupsVisible++;
      }
      if (show === g.hidden) {
        o.visible = show;
        g.hidden = !show;
      }
"""
update_new = """      const c = g.center;
      let show = true;
      const far = g.maxDistance > 0 ? g.maxDistance : dd;
      const margin = g.distanceMargin || 12;
      const surfaceDistance = this.camPos.distanceTo(c) - g.radius;
      // Hysteresis avoids flicker when the camera crosses tile boundaries:
      // hidden groups return early, visible groups cull slightly earlier.
      const distanceLimit = far + (g.hidden ? margin : -margin);
      if (surfaceDistance > distanceLimit) {
        show = false;
        this.stats.groupsCulledDistance++;
      } else {
        const frustumRadius = Math.max(0.5, g.radius + (g.hidden ? margin * 0.35 : -margin * 0.35));
        if (!this.sphereVisible(c.x, c.y, c.z, frustumRadius)) {
          show = false;
          this.stats.groupsCulledFrustum++;
        } else {
          this.stats.groupsVisible++;
        }
      }
      if (show === g.hidden) {
        o.visible = show;
        g.hidden = !show;
      }
"""
if "distanceLimit = far + (g.hidden ? margin : -margin)" in s:
    print("City visibility hysteresis already present; no change.")
else:
    for label, old, new in (("entry", entry_old, entry_new), ("options", opts_old, opts_new), ("update", update_old, update_new)):
        if old not in s:
            raise SystemExit(f"City visibility patch failed: {label} anchor missing")
        s = s.replace(old, new, 1)
    p.write_text(s)
    print("Applied stable frustum + distance hysteresis to every registered city tile root.")

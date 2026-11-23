#!/usr/bin/env python3
"""Prioritize camera-near building geometry over distant city massing."""
from pathlib import Path
import sys

arg = Path(sys.argv[1])
root = arg.resolve()
# Workflow invokes this from PROJECT_DIR but passes PROJECT_DIR again.
if not root.exists() and not arg.is_absolute():
    root = Path.cwd().resolve()
p = root / "src/buildings/index.js"
s = p.read_text()
old_far = "this.schedule(() => this._buildFar(rec), 1);"
new_far = "this.schedule(() => this._buildFar(rec), 8); // distant massing is background work"
old_near = "this.schedule(() => this._buildNear(rec), 4);"
new_near = "this.schedule(() => this._buildNear(rec), 0); // near facade geometry is first priority"
if old_far not in s and new_far not in s:
    raise SystemExit("far-build priority anchor missing")
if old_near not in s and new_near not in s:
    raise SystemExit("near-build priority anchor missing")
s = s.replace(old_far, new_far, 1).replace(old_near, new_near, 1)
p.write_text(s)
print("Near buildings promoted to priority 0; far massing demoted to priority 8")

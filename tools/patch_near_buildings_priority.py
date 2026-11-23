#!/usr/bin/env python3
"""Make camera-near building work outrank far massing, idempotently."""
from pathlib import Path
import sys

arg = Path(sys.argv[1])
root = arg.resolve()
if not root.exists() and not arg.is_absolute():
    root = Path.cwd().resolve()
p = root / "src/buildings/index.js"
s = p.read_text()

# Outer scheduling is already patched by some upstream streaming scripts.
far_variants = [
    "this.schedule(() => this._buildFar(rec), 1);",
    "this.schedule(() => this._buildFar(rec), 8); // distant massing is background work",
]
near_variants = [
    "this.schedule(() => this._buildNear(rec), 4);",
    "this.schedule(() => this._buildNear(rec), 0); // near facade geometry is first priority",
]
if not any(x in s for x in far_variants):
    raise SystemExit("far-build scheduling anchor missing (unrecognized source version)")
if not any(x in s for x in near_variants):
    raise SystemExit("near-build scheduling anchor missing (unrecognized source version)")
s = s.replace(far_variants[0], far_variants[1], 1)
s = s.replace(near_variants[0], near_variants[1], 1)

# Crucial: the sliced geometry queue's per-slice priority is what determines
# whether near facade lots or far massing consume the queue first.
old_slice = "const priority = lod ? 4 : 1;"
new_slice = "const priority = lod ? 8 : 0;"
if old_slice in s:
    s = s.replace(old_slice, new_slice, 1)
elif new_slice not in s:
    raise SystemExit("building-slice priority anchor missing (unrecognized source version)")

p.write_text(s)
print("Building work reprioritized: near slices=0, far slices=8; outer schedule idempotently normalized.")

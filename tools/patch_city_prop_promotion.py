#!/usr/bin/env python3
from pathlib import Path
import sys
arg = Path(sys.argv[1])
root = arg.resolve()
if not root.exists() and not arg.is_absolute():
    root = Path.cwd().resolve()
p = root / "src/props/index.js"
s = p.read_text()
old = "if (this._promoteTimer > 0.45 && this._pending === 0) {"
new = "if (this._promoteTimer > 0.30) {"
if old in s:
    s = s.replace(old, new, 1)
elif new not in s:
    raise SystemExit("prop LOD promotion condition missing; refusing to patch")
p.write_text(s)
print("Near street-prop LOD promotions no longer wait for the entire city queue to drain.")

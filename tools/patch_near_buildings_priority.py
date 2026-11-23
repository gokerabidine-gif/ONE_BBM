#!/usr/bin/env python3
"""Prioritize detailed camera-near city geometry; robust to upstream formatting."""
from pathlib import Path
import re
import sys

arg = Path(sys.argv[1])
root = arg.resolve()
if not root.exists() and not arg.is_absolute():
    root = Path.cwd().resolve()
p = root / "src/buildings/index.js"
s = p.read_text()

def replace_line(pattern, replacement, label):
    global s
    s2, n = re.subn(pattern, replacement, s, count=1, flags=re.MULTILINE)
    if n == 0:
        if replacement.strip() not in s:
            raise SystemExit(label + " anchor missing (unrecognized source version)")
    else:
        s = s2

# Schedule far massing late and near geometry early. Preserve trailing comments.
replace_line(r"^\s*this\.schedule\(\(\) => this\._buildFar\(rec\), \d+\);.*$",
             "    this.schedule(() => this._buildFar(rec), 8); // distant massing is background work",
             "far-build scheduling")
replace_line(r"^\s*this\.schedule\(\(\) => this\._buildNear\(rec\), \d+\);.*$",
             "        this.schedule(() => this._buildNear(rec), 0); // near facade geometry is first priority",
             "near-build scheduling")

# Prioritize the per-slice queue too, otherwise its initial wrapper priority
# does not matter after each slice requeues itself.
replace_line(r"^\s*const priority = lod \? \d+ : \d+;.*$",
             "    const priority = lod ? 8 : 0;",
             "building-slice priority")
p.write_text(s)
print("Building priorities applied: near detail 0; far massing 8.")

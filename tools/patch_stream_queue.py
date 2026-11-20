#!/usr/bin/env python3
from pathlib import Path
import sys

root = Path(sys.argv[1])
p = root / "src/world/streaming.js"
s = p.read_text()
old_init = "    this.pending = 0;\n    this.ran = 0;"
new_init = "    this.heads = new Array(BUCKETS).fill(0);\n    this.pending = 0;\n    this.ran = 0;"
if old_init in s:
    s = s.replace(old_init, new_init, 1)
elif "this.heads = new Array(BUCKETS).fill(0);" not in s:
    raise SystemExit("JobQueue constructor anchor missing")

old = """      const b = this.buckets[p];
      while (b.length) {
        const spent = counted ? ran >= jobBudget : ran > 0 && now() - t0 >= budgetMs;
        if (spent) {
          this.lastMs = now() - t0;
          this.ran = ran;
          this.totalRan += ran;
          return ran;
        }
        const fn = b.shift();
        this.pending--;
        ran++;
        try {
          fn();
        } catch (err) {
          console.error('[world] build job threw:', err);
        }
      }
"""
new = """      const b = this.buckets[p];
      let head = this.heads[p];
      while (head < b.length) {
        const spent = counted ? ran >= jobBudget : ran > 0 && now() - t0 >= budgetMs;
        if (spent) {
          this.heads[p] = head;
          this.lastMs = now() - t0;
          this.ran = ran;
          this.totalRan += ran;
          return ran;
        }
        const fn = b[head++];
        this.pending--;
        ran++;
        try { fn(); } catch (err) { console.error('[world] build job threw:', err); }
      }
      // Reset a drained bucket. Index dequeue avoids repeated array shifts/copies.
      b.length = 0;
      this.heads[p] = 0;
"""
if old in s:
    s = s.replace(old, new, 1)
elif "let head = this.heads[p];" not in s:
    raise SystemExit("JobQueue dequeue anchor missing")
old_clear = "    for (const b of this.buckets) b.length = 0;\n    this.pending = 0;"
new_clear = "    for (const b of this.buckets) b.length = 0;\n    this.heads.fill(0);\n    this.pending = 0;"
if old_clear in s:
    s = s.replace(old_clear, new_clear, 1)
elif "this.heads.fill(0);" not in s:
    raise SystemExit("JobQueue clear anchor missing")
p.write_text(s)

probe = root / "src/world/queueprobe.mjs"
probe.write_text("""import assert from 'node:assert/strict';
import { JobQueue } from './streaming.js';
const q = new JobQueue(); const seen = [];
q.push(() => { seen.push('p2-a'); q.push(() => seen.push('p2-new'), 2); }, 2);
q.push(() => seen.push('p0'), 0); q.push(() => seen.push('p5'), 5);
assert.equal(q.pending, 3); assert.equal(q.run(100, () => 0, 2), 2);
assert.deepEqual(seen, ['p0', 'p2-a']); assert.equal(q.pending, 2);
assert.equal(q.run(100, () => 0, 10), 2);
assert.deepEqual(seen, ['p0','p2-a','p2-new','p5']);
assert.equal(q.pending, 0); assert.equal(q.run(1, () => 0), 0);
for (let i=0;i<5000;i++) q.push(()=>{},i%10);
assert.equal(q.run(100,()=>0,5000),5000); assert.equal(q.pending,0);
q.push(()=>{},1); q.clear(); assert.equal(q.pending,0); assert.equal(q.run(100,()=>0),0);
console.log('[streaming queue] PASS: priority, requeue, budgets, large queue, clear');
""")
pkg = root / "package.json"
text = pkg.read_text()
gate_anchor = "node src/world/routeprobe.mjs && node src/fx/plumeprobe.mjs"
gate_new = "node src/world/routeprobe.mjs && node src/world/queueprobe.mjs && node src/fx/plumeprobe.mjs"
if gate_anchor in text:
    text = text.replace(gate_anchor, gate_new, 1)
elif "node src/world/queueprobe.mjs" not in text:
    raise SystemExit("package gate anchor missing")
pkg.write_text(text)
print("Queue optimization and regression probe applied.")

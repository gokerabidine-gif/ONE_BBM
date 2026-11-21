# Static geometry cache phase

The Android build workflow applies `tools/patch_geometry_cache.py` to add a versioned IndexedDB cache for far building sector geometry. Cache records are local to each device and are rebuilt when the cache version changes.

Build trigger: 2026-11-21 geometry-cache retry.

Retry: corrected patch script.


2026-11-21: added lossless IndexedDB caching for detailed road sectors and complete street-prop tiles (including LOD trees, instancing, material bindings, and static collider meshes). Existing per-frame mesh attach budget remains in place.

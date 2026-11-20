from pathlib import Path
import shutil, sys
project=Path(sys.argv[1]); model=Path(sys.argv[2])
if not model.is_file() or model.stat().st_size < 1_000_000: raise SystemExit('rigged GLB unavailable/invalid')
out=project/'public/models/player-realistic.glb'; out.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(model,out)
p=project/'src/player/character/index.js'; s=p.read_text()
if "GLTFLoader" not in s:
 s=s.replace("import { buildTextures, disposeTextures } from './textures.js';", "import { buildTextures, disposeTextures } from './textures.js';\nimport { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';")
 s=s.replace("    this._parent = null;", "    this._parent = null;\n    this.externalRoot = null; this.externalBones = null; this.externalRest = null; this.proceduralRest = null; this._externalLoadToken = 0;")
 s=s.replace("    if (keep) keep.add(this.root);\n    this.root.visible = this.visible;\n    // Remove original procedural render mesh permanently; keep its bones as animation driver.\n    if (this.mesh) { this.root.remove(this.mesh); this.mesh.visible = false; this.mesh.geometry?.dispose?.(); for (const m of (Array.isArray(this.mesh.material) ? this.mesh.material : [this.mesh.material])) m?.dispose?.(); }\n    this._loadRealisticModel(spec.id);\n    return this.root;", "    if (keep) keep.add(this.root);\n    this.root.visible = this.visible;\n    this._loadRealisticModel(spec.id);\n    return this.root;")
 method='''
  /** Async replacement body; procedural rig remains animation/IK driver. */
  async _loadRealisticModel(id) {
    const token = ++this._externalLoadToken;
    let modelUrl = '';
    try {
      modelUrl = new URL('models/player-realistic.glb', document.baseURI).href;
      window.__ONE_BBM_CHARACTER_MODEL__ = { status: 'loading', url: modelUrl, character: id };
      console.info('[ONE BBM] Loading realistic character model:', modelUrl);
      const gltf = await new GLTFLoader().loadAsync(modelUrl);
      if (token !== this._externalLoadToken || this.spec?.id !== id || !this.root) return;
      const extRoot = gltf.scene; extRoot.name = 'realistic:' + id;
      extRoot.scale.multiplyScalar(this.spec?.build?.scale ?? 1);
      extRoot.traverse(o => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; if (o.material) o.material.roughness = Math.max(0.58, o.material.roughness ?? 0.7); } });
      const src = new Map(); extRoot.traverse(o => { if (o.isBone && o.name) src.set(o.name, o); });
      const pairs = { hips:'Hips', spine:'Spine02', chest:'Spine01', neck:'neck', head:'Head', headEnd:'head_end', clavL:'LeftShoulder', armL:'LeftArm', forearmL:'LeftForeArm', handL:'LeftHand', thighL:'LeftUpLeg', shinL:'LeftLeg', footL:'LeftFoot', toeL:'LeftToeBase', clavR:'RightShoulder', armR:'RightArm', forearmR:'RightForeArm', handR:'RightHand', thighR:'RightUpLeg', shinR:'RightLeg', footR:'RightFoot', toeR:'RightToeBase' };
      this.externalBones = {}; this.proceduralRest = {}; this.externalRest = {};
      for (const [g, n] of Object.entries(pairs)) { const eb=src.get(n), pb=this.bones?.[g]; if (!eb || !pb) continue; this.externalBones[g]=eb; this.proceduralRest[g]=pb.quaternion.clone(); this.externalRest[g]=eb.quaternion.clone(); }
      this.externalRoot=extRoot; this.root.add(extRoot); this.mesh.visible=false; this.syncExternalPose(); this.root.updateMatrixWorld(true);\n      window.__ONE_BBM_CHARACTER_MODEL__ = { status: 'loaded', url: modelUrl, character: id, bones: Object.keys(this.externalBones).length };\n      console.info('[ONE BBM] Realistic character loaded:', id, 'mapped bones:', Object.keys(this.externalBones).length);
    } catch (err) {\n      window.__ONE_BBM_CHARACTER_MODEL__ = { status: 'failed', url: modelUrl, character: id, error: String(err?.message ?? err) };\n      console.error('[ONE BBM] Realistic model load failed:', modelUrl, err);\n    }
  }
  syncExternalPose() {
    if (!this.externalBones || !this.bones) return;
    for (const [name, ext] of Object.entries(this.externalBones)) { const proc=this.bones[name], pr=this.proceduralRest[name], er=this.externalRest[name]; if (!proc||!pr||!er) continue; const delta=pr.clone().invert().multiply(proc.quaternion); ext.quaternion.copy(er).multiply(delta); }
  }
'''
 s=s.replace("  _material(name) {", method+"\n  _material(name) {")
 s=s.replace("    if (this.root?.parent) this.root.parent.remove(this.root);", "    this._externalLoadToken++; if (this.externalRoot?.parent) this.externalRoot.parent.remove(this.externalRoot); this.externalRoot=null; this.externalBones=null;\n    if (this.root?.parent) this.root.parent.remove(this.root);")
 # Explicit call-site patch: the original insertion anchor was incorrect.
 call_anchor = "    this.root.visible = this.visible;\n    return this.root;"
 if call_anchor in s and "this._loadRealisticModel(spec.id);" not in s:
  s = s.replace(call_anchor, "    this.root.visible = this.visible;\n    this._loadRealisticModel(spec.id);\n    return this.root;", 1)
 if "this._loadRealisticModel(spec.id);" not in s:
  raise SystemExit('Failed to add realistic model loader call')
 p.write_text(s)
p=project/'src/player/character/index.js'; s=p.read_text()
call_anchor = "    this.root.visible = this.visible;\n    return this.root;"
if call_anchor in s and "this._loadRealisticModel(spec.id);" not in s:
 s=s.replace(call_anchor, "    this.root.visible = this.visible;\n    this._loadRealisticModel(spec.id);\n    return this.root;", 1)
if "this._loadRealisticModel(spec.id);" not in s:
 raise SystemExit('loader call-site still missing')
p.write_text(s)
p=project/'src/player/anim/animator.js'; s=p.read_text()
if 'rig.syncExternalPose?.();' not in s:
 s=s.replace('    rig.root.updateMatrixWorld(true);\n  }\n\n  /** Interpolate', '    rig.syncExternalPose?.();\n    rig.root.updateMatrixWorld(true);\n  }\n\n  /** Interpolate',1)
 p.write_text(s)
print('realistic replacement patch applied')

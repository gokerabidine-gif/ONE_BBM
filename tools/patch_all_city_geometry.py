#!/usr/bin/env python3
from pathlib import Path
import sys

root = Path(sys.argv[1])

road_module = r'''import * as THREE from 'three';
const DB='one-bbm-road-sector-cache-v1', STORE='sectors', VERSION=1, LIMIT=12*1024*1024;
function openDb(){return new Promise((resolve,reject)=>{const r=indexedDB.open(DB,1);r.onupgradeneeded=()=>{if(!r.result.objectStoreNames.contains(STORE))r.result.createObjectStore(STORE,{keyPath:'key'});};r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(r.error);});}
function req(r){return new Promise((resolve,reject)=>{r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(r.error);});}
async function read(key){const db=await openDb();try{return await req(db.transaction(STORE,'readonly').objectStore(STORE).get(key));}finally{db.close();}}
async function write(v){const db=await openDb();try{const tx=db.transaction(STORE,'readwrite');await req(tx.objectStore(STORE).put(v));}finally{db.close();}}
async function pack(v){const stream=new Blob([JSON.stringify(v)]).stream().pipeThrough(new CompressionStream('gzip'));return new Uint8Array(await new Response(stream).arrayBuffer());}
async function unpack(v){const stream=new Blob([v]).stream().pipeThrough(new DecompressionStream('gzip'));return JSON.parse(await new Response(stream).text());}
const key=(x,z)=>'v'+VERSION+':'+x+','+z;
export async function restoreRoadSector(sx,sz,builder){
 try{
  const rec=await read(key(sx,sz));if(!rec||rec.version!==VERSION)return null;
  const data=await unpack(new Uint8Array(rec.bytes));if(data.sx!==sx||data.sz!==sz||data.version!==VERSION)return null;
  const group=new THREE.Group();group.name='sector_'+sx+'_'+sz;group.matrixAutoUpdate=false;
  const loader=new THREE.BufferGeometryLoader();
  for(const item of data.meshes){
   const mesh=new THREE.Mesh(loader.parse(item.geometry),builder._mat(item.materialKey));
   mesh.name=item.name;mesh.matrix.fromArray(item.matrix);mesh.matrixAutoUpdate=false;
   mesh.receiveShadow=item.receiveShadow;mesh.castShadow=item.castShadow;mesh.visible=item.visible;
   mesh.renderOrder=item.renderOrder;mesh.userData=item.userData??{};group.add(mesh);
  }
  return {group,tris:data.tris??0};
 }catch(e){console.warn('[road-cache] sector restore failed',sx,sz,e);return null;}
}
export function scheduleRoadSectorSave(sx,sz,group,builder,tris){
 if(!group||!globalThis.indexedDB||typeof CompressionStream!=='function')return;
 const save=async()=>{try{
  const mats=new Map();for(const [k,m] of builder._mats??[])mats.set(m.uuid,k);
  const meshes=[];
  for(const m of group.children){if(!m.isMesh)continue;const materialKey=mats.get(m.material?.uuid);if(!materialKey)throw new Error('unmapped road material '+m.name);
   meshes.push({name:m.name,materialKey,geometry:m.geometry.toJSON(),matrix:m.matrix.toArray(),matrixAutoUpdate:m.matrixAutoUpdate,receiveShadow:m.receiveShadow,castShadow:m.castShadow,visible:m.visible,renderOrder:m.renderOrder,userData:m.userData??{}});
  }
  const bytes=await pack({version:VERSION,sx,sz,tris,meshes});if(bytes.byteLength>LIMIT)return;
  await write({key:key(sx,sz),version:VERSION,bytes:bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),savedAt:Date.now()});
 }catch(e){console.warn('[road-cache] sector not cached',sx,sz,e);}};
 const idle=globalThis.requestIdleCallback;if(idle)idle(()=>void save(),{timeout:3000});else setTimeout(()=>void save(),1500);
}
'''

props_module = r'''import * as THREE from 'three';
const DB='one-bbm-prop-tile-cache-v1',STORE='tiles',VERSION=1,LIMIT=10*1024*1024;
const INVISIBLE=new THREE.MeshBasicMaterial({visible:false});
function openDb(){return new Promise((resolve,reject)=>{const r=indexedDB.open(DB,1);r.onupgradeneeded=()=>{if(!r.result.objectStoreNames.contains(STORE))r.result.createObjectStore(STORE,{keyPath:'key'});};r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(r.error);});}
function req(r){return new Promise((resolve,reject)=>{r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(r.error);});}
async function read(key){const db=await openDb();try{return await req(db.transaction(STORE,'readonly').objectStore(STORE).get(key));}finally{db.close();}}
async function write(v){const db=await openDb();try{const tx=db.transaction(STORE,'readwrite');await req(tx.objectStore(STORE).put(v));}finally{db.close();}}
async function pack(v){const stream=new Blob([JSON.stringify(v)]).stream().pipeThrough(new CompressionStream('gzip'));return new Uint8Array(await new Response(stream).arrayBuffer());}
async function unpack(v){const stream=new Blob([v]).stream().pipeThrough(new DecompressionStream('gzip'));return JSON.parse(await new Response(stream).text());}
const key=(x,z,lod)=>'v'+VERSION+':'+lod+':'+x+','+z;
function indexes(lib){
 const mats=new Map();for(const [k,m] of lib._mats??[])mats.set(m.uuid,k);for(const [k,m] of lib._emissive??[])mats.set(m.uuid,k);
 const protos=new Map();for(const [id,p] of lib.protos??[])protos.set(p.geo.uuid,id);
 return {mats,protos};
}
function encode(o,idx){
 const n={type:o.isLOD?'lod':o.isInstancedMesh?'instanced':o.isMesh?'mesh':'group',name:o.name||'',matrix:o.matrix.toArray(),matrixAutoUpdate:o.matrixAutoUpdate,visible:o.visible,renderOrder:o.renderOrder,userData:o.userData??{},castShadow:o.castShadow,receiveShadow:o.receiveShadow,frustumCulled:o.frustumCulled,children:[]};
 if(o.isLOD){n.autoUpdate=o.autoUpdate;n.levels=o.levels.map(x=>x.distance);}
 if(o.isInstancedMesh){n.protoId=idx.protos.get(o.geometry.uuid);if(!n.protoId)throw new Error('unmapped prop prototype '+o.name);n.count=o.count;n.matrices=Array.from(o.instanceMatrix.array);n.instanceColor=o.instanceColor?Array.from(o.instanceColor.array):null;}
 else if(o.isMesh){n.materialKey=idx.mats.get(o.material?.uuid);if(!n.materialKey)throw new Error('unmapped prop material '+o.name);n.geometry=o.geometry.toJSON();}
 n.children=o.children.map(c=>encode(c,idx));return n;
}
function decode(n,lib,loader){
 let o;
 if(n.type==='lod'){o=new THREE.LOD();o.autoUpdate=n.autoUpdate!==false;}
 else if(n.type==='instanced'){
  const p=lib.protos.get(n.protoId);if(!p)throw new Error('missing prop prototype '+n.protoId);
  o=new THREE.InstancedMesh(p.geo,lib.matFor(p.surface),n.count);o.name=n.name;
  for(let i=0;i<n.count;i++)o.setMatrixAt(i,new THREE.Matrix4().fromArray(n.matrices,i*16));
  if(n.instanceColor){o.instanceColor=new THREE.InstancedBufferAttribute(new Float32Array(n.instanceColor),3);o.instanceColor.needsUpdate=true;}
  o.instanceMatrix.needsUpdate=true;o.computeBoundingSphere();o.computeBoundingBox();
 }else if(n.type==='mesh'){o=new THREE.Mesh(loader.parse(n.geometry),lib.matFor(n.materialKey));o.name=n.name;}
 else{o=new THREE.Group();o.name=n.name;}
 if(n.matrix)o.matrix.fromArray(n.matrix);o.matrixAutoUpdate=false;o.visible=n.visible!==false;o.renderOrder=n.renderOrder??0;o.userData=n.userData??{};
 if('castShadow'in n)o.castShadow=n.castShadow;if('receiveShadow'in n)o.receiveShadow=n.receiveShadow;if('frustumCulled'in n)o.frustumCulled=n.frustumCulled;
 for(let i=0;i<n.children.length;i++){const c=decode(n.children[i],lib,loader);if(n.type==='lod')o.addLevel(c,n.levels?.[i]??0);else o.add(c);}
 return o;
}
export async function restorePropTile(tx,tz,lod,lib){
 try{
  const rec=await read(key(tx,tz,lod));if(!rec||rec.version!==VERSION)return null;
  const d=await unpack(new Uint8Array(rec.bytes));if(d.tx!==tx||d.tz!==tz||d.lod!==lod||d.version!==VERSION)return null;
  const group=decode(d.root,lib,new THREE.BufferGeometryLoader()),meshes=[];let lodNode=null;
  group.traverse(o=>{if(o.isMesh)meshes.push(o);if(o.isLOD&&!lodNode)lodNode=o;});
  const colliders=(d.colliders??[]).map(c=>({tag:c.tag,mesh:new THREE.Mesh(new THREE.BufferGeometryLoader().parse(c.geometry),INVISIBLE)}));
  for(const c of colliders){c.mesh.name=c.name??('prop_col:'+c.tag);c.mesh.visible=false;c.mesh.matrixAutoUpdate=false;c.mesh.userData.surface=c.tag;}
  return {group,meshes,colliders,lodNode,lamps:d.lamps??[],stats:d.stats??{}};
 }catch(e){console.warn('[props-cache] tile restore failed',tx,tz,e);return null;}
}
export function schedulePropTileSave(rec,out,group,lib){
 if(!rec||!out||!group||!globalThis.indexedDB||typeof CompressionStream!=='function')return;
 const save=async()=>{try{
  const idx=indexes(lib),root=encode(group,idx);
  const colliders=(out.colliders??[]).map(c=>({tag:c.tag,name:c.mesh.name,geometry:c.mesh.geometry.toJSON()}));
  const bytes=await pack({version:VERSION,tx:rec.tx,tz:rec.tz,lod:rec.lod,root,colliders,lamps:out.lamps??[],stats:out.stats??{}});
  if(bytes.byteLength>LIMIT)return;
  await write({key:key(rec.tx,rec.tz,rec.lod),version:VERSION,bytes:bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),savedAt:Date.now()});
 }catch(e){console.warn('[props-cache] tile not cached',rec.key,e);}};
 const idle=globalThis.requestIdleCallback;if(idle)idle(()=>void save(),{timeout:3500});else setTimeout(()=>void save(),1800);
}
export function disposePropTile(tile){
 for(const m of tile?.meshes??[]){m.geometry?.dispose();if(m.isInstancedMesh)m.dispose();m.parent?.remove(m);}
 for(const c of tile?.colliders??[]){c.mesh.geometry?.dispose();}
 tile?.group?.parent?.remove(tile.group);
}
'''

(root/'src/world/sector-cache.js').write_text(road_module)
(root/'src/props/tile-cache.js').write_text(props_module)

# Integrate persistent road-sector cache while retaining the existing mesh-per-frame attach budget.
p=root/'src/world/index.js';s=p.read_text()
if "restoreRoadSector" not in s:
 anchor="import { RoadMeshBuilder, noGapFix } from './roadmesh.js';"
 if anchor not in s: raise SystemExit('world roadmesh import anchor missing')
 s=s.replace(anchor,anchor+"\nimport { restoreRoadSector, scheduleRoadSectorSave } from './sector-cache.js';",1)
anchor="""        rec.job = this.roadMesh.begin(sx, sz);
        const pri = d2 < SECTOR * SECTOR ? 0 : d2 < SECTOR * SECTOR * 6 ? 2 : 4;
"""
replacement="""        const cacheToken = { cache: true };
        rec.job = cacheToken;
        const pri = d2 < SECTOR * SECTOR ? 0 : d2 < SECTOR * SECTOR * 6 ? 2 : 4;
"""
if "const cacheToken = { cache: true };" not in s:
 if anchor not in s: raise SystemExit('world sector job initialization anchor missing')
 s=s.replace(anchor,replacement,1)
# Cache restore begins only after the normal pump closure exists.
anchor="""        this.queue.push(pump, pri);
      }
      this._stats.sectors = this._sectors.live.size;
"""
replacement="""        const fallback = () => {
          if (rec.job !== cacheToken) return;
          rec.job = this.roadMesh.begin(sx, sz);
          this.queue.push(pump, pri);
        };
        restoreRoadSector(sx, sz, this.roadMesh).then((group) => {
          if (rec.job !== cacheToken) {
            if (group) for (const m of group.children) m.geometry?.dispose();
            return;
          }
          if (!group) { fallback(); return; }
          rec.job = null;
          rec.group = group;
          this._stats.tris += group.children.reduce((n,m)=>n+(m.geometry?.index?.count??0)/3,0);
          rec.pend = group.children.slice();
          rec.pendI = 0;
          group.clear();
          this.root.add(group);
          this._attachQ.push(rec);
        }).catch(fallback);
      }
      this._stats.sectors = this._sectors.live.size;
"""
if "restoreRoadSector(sx, sz, this.roadMesh)" not in s:
 if anchor not in s: raise SystemExit('world sector queue tail anchor missing')
 s=s.replace(anchor,replacement,1)
# Save the fully generated sector before its meshes are attached incrementally.
anchor="""          const out = rec.job.finish();
          rec.job = null;
          rec.group = out.group;
          this._stats.tris += out.tris;
"""
replacement="""          const out = rec.job.finish();
          rec.job = null;
          rec.group = out.group;
          this._stats.tris += out.tris;
          if (out.group) scheduleRoadSectorSave(sx, sz, out.group, this.roadMesh, out.tris);
"""
if "scheduleRoadSectorSave(sx, sz, out.group" not in s:
 if anchor not in s: raise SystemExit('world road sector save anchor missing')
 s=s.replace(anchor,replacement,1)
p.write_text(s)

# Integrate per-tile props caching. Cache hit follows the same culling, physics and static-mesh setup as a fresh build.
p=root/'src/props/index.js';s=p.read_text()
if "restorePropTile" not in s:
 anchor="import { Layout } from './layout.js';"
 if anchor not in s: raise SystemExit('props layout import anchor missing')
 s=s.replace(anchor,anchor+"\nimport { restorePropTile, schedulePropTileSave, disposePropTile } from './tile-cache.js';",1)
anchor="""    if (rec.lod >= 2) return; // beyond the prop horizon; nothing to build
    this._queueBuild(rec);
"""
replacement="""    if (rec.lod >= 2) return; // beyond the prop horizon; nothing to build
    this._pending++;
    this._restoreOrBuild(rec)
      .catch((err) => { console.warn('[props-cache] restore path failed; rebuilding', rec.key, err); if (rec.alive) this._queueBuild(rec); })
      .finally(() => { this._pending = Math.max(0, this._pending - 1); });
"""
if "_restoreOrBuild(rec)" not in s:
 if anchor not in s: raise SystemExit('props tile load anchor missing')
 s=s.replace(anchor,replacement,1)
# Add the async cache restore path immediately before _queueBuild.
anchor="""  _queueBuild(rec) {
"""
replacement="""  async _restoreOrBuild(rec) {
    const cached = await restorePropTile(rec.tx, rec.tz, rec.lod, this.lib);
    if (!rec.alive || this.tiles.get(rec.key) !== rec) {
      if (cached) disposePropTile(cached);
      return;
    }
    if (!cached) { this._queueBuild(rec); return; }
    const group = cached.group;
    this.root.add(group);
    rec.group = group;
    rec.meshes = cached.meshes;
    rec.colliders = cached.colliders;
    rec.lodNode = cached.lodNode;
    rec.lamps = cached.lamps;
    rec.built = true;
    rec.stats = { ...cached.stats };
    this.render?.patchMaterials?.(group);
    const cx = (rec.bx.x0 + rec.bx.x1) * 0.5;
    const cz = (rec.bx.z0 + rec.bx.z1) * 0.5;
    const cy = (this.world.heightAt?.(cx, cz) ?? 0) + 8;
    rec.cullOff = this.render?.registerCullGroup?.(group, {
      center: [cx, cy, cz], radius: 128 * 0.72 + 14,
      maxDistance: rec.lod === 0 ? 0 : this.midRadius + 90,
    }) ?? null;
    for (const m of rec.meshes) m.userData.owStatic = true;
    if (rec.lod === 0 && this.physics?.addStatic) {
      for (const c of rec.colliders) {
        group.add(c.mesh);
        rec.handles.push(this.physics.addStatic(c.mesh, c.tag));
      }
      if (rec.colliders.length) this._colDirty = true;
    }
    this._recount();
  }

  _queueBuild(rec) {
"""
if "_restoreOrBuild(rec) {" not in s:
 if anchor not in s: raise SystemExit('props queueBuild method anchor missing')
 s=s.replace(anchor,replacement,1)
# Save after all tile metadata and physics have been published.
anchor="""    this._recount();
  }

  /* ==================================================================== */
  /* deferred wall pass"""
replacement="""    schedulePropTileSave(rec, out, group, this.lib);
    this._recount();
  }

  /* ==================================================================== */
  /* deferred wall pass"""
if "schedulePropTileSave(rec, out, group, this.lib)" not in s:
 if anchor not in s: raise SystemExit('props finish tile tail anchor missing')
 s=s.replace(anchor,replacement,1)
p.write_text(s)

print('Installed persistent road-sector and street-prop tile caches.')

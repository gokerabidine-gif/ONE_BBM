/**
 * Load and expose a rigged external character for ONE BBM's procedural animator.
 * This is an adapter only: callers must complete bind-pose/axis retarget tests
 * before swapping it into the live CharacterRig.
 */
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { EXTERNAL_BONE_MAP, GAME_ANIMATOR_BONES } from './external-bone-map.js';

const loader = new GLTFLoader();

function byName(root) {
  const found = new Map();
  root.traverse((object) => { if (object.isBone && object.name) found.set(object.name, object); });
  return found;
}

function addHandEnd(hand, side, length = 0.045) {
  const synthetic = new THREE.Bone();
  synthetic.name = `handEnd${side}`;
  // IK-only reference joint; it has no skin weights.
  synthetic.position.set(0, length, 0);
  hand.add(synthetic);
  return synthetic;
}

/** Load an external GLB and expose mapped joints without renaming weighted bones. */
export async function loadExternalCharacterModel(url, opts = {}) {
  const gltf = await loader.loadAsync(url);
  const root = gltf.scene;
  root.name = 'player:external-character';
  root.updateMatrixWorld(true);
  const sourceBones = byName(root);
  const bones = {};
  for (const [source, target] of Object.entries(EXTERNAL_BONE_MAP)) {
    if (!target) continue;
    const bone = sourceBones.get(source);
    if (!bone) throw new Error(`External character is missing joint: ${source}`);
    bones[target] = bone;
  }
  bones.handEndL = sourceBones.get('handEndL') ?? addHandEnd(bones.handL, 'L', opts.handEndLength);
  bones.handEndR = sourceBones.get('handEndR') ?? addHandEnd(bones.handR, 'R', opts.handEndLength);
  const missing = GAME_ANIMATOR_BONES.filter((name) => !bones[name]);
  if (missing.length) throw new Error(`External rig adapter incomplete: ${missing.join(', ')}`);
  if (opts.material) root.traverse((o) => { if (o.isMesh) o.material = opts.material; });
  if (Number.isFinite(opts.scale)) root.scale.multiplyScalar(opts.scale);
  root.updateMatrixWorld(true);
  const boneList = [...new Set(Object.values(bones))];
  const restQuaternions = Object.fromEntries(Object.entries(bones).map(([key, bone]) => [key, bone.quaternion.clone()]));
  const bindPositions = Object.fromEntries(Object.entries(bones).map(([key, bone]) => [key, bone.position.toArray()]));
  const meshes = [];
  root.traverse((o) => { if (o.isSkinnedMesh) meshes.push(o); });
  if (!meshes.length) throw new Error('External model contains no SkinnedMesh');
  return { gltf, root, mesh: meshes[0], meshes, skeleton: meshes[0].skeleton, bones, boneList, bindPositions, restQuaternions, scale: opts.scale ?? 1, animations: gltf.animations };
}

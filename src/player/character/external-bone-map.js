/**
 * Explicit source-joint map for the imported 24-joint GLB.
 * null entries are source helpers/extra joints excluded from the game's named rig.
 * Missing hand-end bones are synthesized by external-character-loader.js.
 */
export const EXTERNAL_BONE_MAP = Object.freeze({
  Hips: 'hips',
  Spine02: 'spine', Spine01: 'chest', Spine: null,
  neck: 'neck', Head: 'head', head_end: 'headEnd', headfront: null,
  LeftShoulder: 'clavL', LeftArm: 'armL', LeftForeArm: 'forearmL', LeftHand: 'handL',
  LeftUpLeg: 'thighL', LeftLeg: 'shinL', LeftFoot: 'footL', LeftToeBase: 'toeL',
  RightShoulder: 'clavR', RightArm: 'armR', RightForeArm: 'forearmR', RightHand: 'handR',
  RightUpLeg: 'thighR', RightLeg: 'shinR', RightFoot: 'footR', RightToeBase: 'toeR',
});

export const GAME_ANIMATOR_BONES = Object.freeze([
  'hips','spine','chest','neck','head','headEnd',
  'clavL','armL','forearmL','handL','handEndL','thighL','shinL','footL','toeL',
  'clavR','armR','forearmR','handR','handEndR','thighR','shinR','footR','toeR',
]);

export const SYNTHESIZED_GAME_BONES = Object.freeze(['handEndL', 'handEndR']);

export function mapExternalBone(name) {
  return Object.hasOwn(EXTERNAL_BONE_MAP, name) ? EXTERNAL_BONE_MAP[name] : undefined;
}

export function validateExternalSkeleton(names, gameBoneNames = GAME_ANIMATOR_BONES) {
  const mapped = names.map((name) => ({ source: name, target: mapExternalBone(name) }));
  const unmapped = mapped.filter(({ target }) => target === undefined);
  const ignored = mapped.filter(({ target }) => target === null).map(({ source }) => source);
  const unknownTargets = mapped.filter(({ target }) => target && !gameBoneNames.includes(target));
  const duplicates = [...new Set(mapped.filter(({ target }) => target).map(({ target }) => target))]
    .filter((target) => mapped.filter((entry) => entry.target === target).length > 1);
  const covered = new Set(mapped.filter(({ target }) => target).map(({ target }) => target));
  const virtualBones = SYNTHESIZED_GAME_BONES.filter((target) => gameBoneNames.includes(target));
  const missingGameBones = gameBoneNames.filter((target) => !covered.has(target) && !virtualBones.includes(target));
  return {
    ok: unmapped.length === 0 && unknownTargets.length === 0 && duplicates.length === 0 && missingGameBones.length === 0,
    mapped, unmapped, ignored, unknownTargets, duplicates, missingGameBones,
    synthesizedGameBones: virtualBones,
    needsRetargeting: ignored.length > 0 || duplicates.length > 0 || virtualBones.length > 0,
    notes: ['GLB joint translations are in centimetres while the game rig is in metres.', 'Bind matrices and forward-axis convention require retarget calibration.', 'handEndL/handEndR are virtual IK reference bones, not skin-weighted joints.', 'Do not attach this skeleton to the live player until retarget tests pass.'],
    manyToOne: duplicates,
  };
}

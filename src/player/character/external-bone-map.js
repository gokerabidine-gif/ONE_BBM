/**
 * Explicit source-joint map for the imported 24-joint GLB.
 * null entries are helper joints that the current procedural player animator
 * does not drive; they must be handled by retargeting, not silently aliased.
 */
export const EXTERNAL_BONE_MAP = Object.freeze({
  Hips: 'hips',
  Spine02: 'spine', Spine01: 'chest', Spine: 'chestAux',
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
  const missingGameBones = gameBoneNames.filter((target) => !covered.has(target));
  return {
    ok: unmapped.length === 0 && unknownTargets.length === 0 && duplicates.length === 0 && missingGameBones.length === 0,
    mapped, unmapped, ignored, unknownTargets, duplicates, missingGameBones,
    needsRetargeting: ignored.length > 0 || duplicates.length > 0 || missingGameBones.length > 0,
    notes: ['GLB joint translations are in centimetres while the game rig is in metres.', 'Bind matrices and forward-axis convention require retarget calibration.', 'Do not attach this skeleton to the live player until the missing joints and aliases are resolved.'],
    manyToOne: duplicates,
  };
}

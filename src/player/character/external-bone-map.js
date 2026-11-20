/**
 * Bone-name adapter for the imported man-base-character rig.
 *
 * This is deliberately only a mapping/validation layer. It does NOT retarget a
 * GLB, replace CharacterRig, or claim compatibility with the live animator.
 * External GLB is authored in a relaxed A-pose and uses a different bind pose;
 * a bind-space retarget step is still required before runtime replacement.
 */
export const EXTERNAL_BONE_MAP = Object.freeze({
  Hips: 'hips', Spine: 'spine', Spine01: 'chest', Spine02: 'chest',
  neck: 'neck', Head: 'head', head_end: 'headEnd', headfront: 'head',
  LeftShoulder: 'clavL', LeftArm: 'armL', LeftForeArm: 'forearmL', LeftHand: 'handL',
  LeftUpLeg: 'thighL', LeftLeg: 'shinL', LeftFoot: 'footL', LeftToeBase: 'toeL',
  RightShoulder: 'clavR', RightArm: 'armR', RightForeArm: 'forearmR', RightHand: 'handR',
  RightUpLeg: 'thighR', RightLeg: 'shinR', RightFoot: 'footR', RightToeBase: 'toeR',
});
export function mapExternalBone(name) { return EXTERNAL_BONE_MAP[name] ?? null; }
export function validateExternalSkeleton(names, gameBoneNames) {
  const mapped = names.map((name) => ({ source: name, target: mapExternalBone(name) }));
  const missing = mapped.filter(({ target }) => !target);
  const unknownTargets = mapped.filter(({ target }) => target && !gameBoneNames.includes(target));
  const duplicateTargets = [...new Set(mapped.filter(({ target }) => target).map(({ target }) => target))]
    .filter((target) => mapped.filter((entry) => entry.target === target).length > 1);
  return { ok: missing.length === 0 && unknownTargets.length === 0, mapped, missing, unknownTargets, duplicateTargets, manyToOne: duplicateTargets };
}

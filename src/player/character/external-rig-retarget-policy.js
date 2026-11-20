/**
 * Retarget preparation helpers for the external GLB.
 * The imported model stores joint translation values in centimetres.
 * These helpers do not load or replace the live player mesh.
 */
export const GLB_TRANSLATION_SCALE = 0.01;
export const VIRTUAL_GAME_BONES = Object.freeze(['handEndL', 'handEndR']);

export function centimetersToMeters(value) {
  if (Array.isArray(value)) return value.map((v) => Number(v) * GLB_TRANSLATION_SCALE);
  if (value && typeof value === 'object') {
    return { x: Number(value.x) * GLB_TRANSLATION_SCALE,
      y: Number(value.y) * GLB_TRANSLATION_SCALE,
      z: Number(value.z) * GLB_TRANSLATION_SCALE };
  }
  return Number(value) * GLB_TRANSLATION_SCALE;
}

/**
 * Create a virtual hand-end point from the forearm-to-hand direction.
 * Input points are expected to already be in game metres and world/local space
 * consistently. A default 8 cm extension is used when the vector is valid.
 */
export function synthesizeHandEnd(forearm, hand, length = 0.08) {
  const dx = hand.x - forearm.x, dy = hand.y - forearm.y, dz = hand.z - forearm.z;
  const magnitude = Math.hypot(dx, dy, dz);
  if (!Number.isFinite(magnitude) || magnitude < 1e-6) return null;
  const scale = length / magnitude;
  return { x: hand.x + dx * scale, y: hand.y + dy * scale, z: hand.z + dz * scale };
}

export function getExternalRigPolicy() {
  return Object.freeze({
    scaleTranslations: GLB_TRANSLATION_SCALE,
    ignoredSourceJoints: ['Spine', 'headfront'],
    virtualGameBones: VIRTUAL_GAME_BONES,
    virtualHandEndLengthMeters: 0.08,
    requiredCalibration: ['bind-pose alignment', 'root/forward axis', 'weapon-hand alignment', 'foot-ground alignment'],
    safeForLiveReplacement: false,
  });
}

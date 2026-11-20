# Imported realistic character rig — compatibility status

## Asset verified
- Rigged GLB: 11,354,468 bytes.
- One skinned mesh, 24 skin joints, two animation clips (`walk`, `run`), 72 channels each.
- FBX companion included in the verified archive.

## Name mapping prototype
`external-bone-map.js` maps external joint names to the existing player rig names. This is a diagnostic/preparation step, not a runtime replacement.

## Required before replacing the three playable brothers
1. Load with Three.js GLTFLoader and inspect mesh/root transforms and bind matrices.
2. Retarget imported bind pose to the game's procedural rig (or derive a compatible skeleton) while preserving scale and forward-axis conventions.
3. Preserve CharacterRig/Animator contracts: named bones, weapon hand, aim IK, crouch, jump, seat poses, camera fade, disposal.
4. Run head/identity, aim, hand, shirt/camera, drive/seat, and gait probes plus visual comparison.
5. Only after tests pass, replace the mesh factory for the three brothers; side NPCs remain untouched.

Imported clips are not yet used: the player is currently driven by a procedural animator, so applying GLB clips directly would conflict with that controller.

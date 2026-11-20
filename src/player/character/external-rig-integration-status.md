# Realistic character replacement — verified integration status

## Asset inspected
The imported GLB has one skinned mesh, 24 source joints, and two clips named `walk` and `run` (72 channels each).

## Source archive recovered and inspected (2026-11-20)
The original project source ZIP and the character-model workflow artifact were recovered locally from GitHub Actions. The GLB was parsed directly.

- GLB Armature node has a uniform scale of `0.01`.
- The mesh POSITION accessor bounds are approximately `[-0.54, 0.54] m` in X, `0..1.8 m` in Y, and `[-0.171, 0.171] m` in Z before node transforms.
- The mesh node is a child of the scaled Armature node. Therefore the displayed mesh scale is a **calibration risk**; confirm the rendered size and skin bind before changing transforms. Do not apply a blanket centimetres-to-metres scale to the already-loaded GLB without checking node transforms.
- Source joint translations are expressed in the Armature's local space; the root scale already participates in their world transforms. The helper's raw `centimetersToMeters()` conversion is for raw data only, not a second scaling pass on GLTFLoader output.

## Adapter preparation now committed
- `Spine02 → spine`, `Spine01 → chest`
- The extra source `Spine` joint is excluded from the game's named-bone map (not incorrectly mapped to a nonexistent `chestAux`).
- `headfront` is excluded as a helper.
- `handEndL` and `handEndR` are declared virtual IK references; the loader creates these when absent.
- A retarget policy helper documents centimetres-to-metres conversion and the required calibration checks.

## Remaining integration gate
- [ ] normalize scale and root orientation to metres / +Y up / -Z forward
- [ ] calibrate bind pose and hierarchy against the live player rig
- [ ] verify synthesized hand-end directions and weapon-hand alignment
- [ ] foot-ground alignment and root motion check
- [ ] test weapon hand, aiming IK, gait, idle, crouch, jump, swim, vehicle poses
- [ ] compare all three brothers; ensure side NPCs remain untouched
- [ ] build and test an APK with the replacement active

The structural bone map is improved, but the live player mesh is **not replaced** and no APK with this replacement has been built yet.

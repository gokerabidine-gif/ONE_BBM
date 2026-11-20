# Realistic character replacement — verified integration status

## Asset inspected
The imported GLB has one skinned mesh, 24 source joints, and two clips named `walk` and `run` (72 channels each).

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

# Realistic character replacement — verified integration status

## Asset inspected
The source artifact contains one skinned mesh, 24 joints and two clips named `walk` and `run` (72 channels each). Joint names and hierarchy were inspected from the GLB JSON.

## Compatibility findings
The current player animator expects 24 named joints including `handEndL` and `handEndR`. The imported GLB does not contain these hand-end joints; it has an additional spine joint and a helper `headfront` joint. Imported joint translations are centimetres, while the game rig is authored in metres. The rest pose and bind matrices also require calibration.

The validator now **fails** if joints are missing, unmapped, duplicated/aliased, or mapped outside the animator's expected names. This model is not directly compatible yet.

## Integration gate
- [ ] normalize scale and root orientation to metres / +Y up / -Z forward
- [ ] calibrate bind pose and hierarchy
- [ ] synthesize missing hand-end joints or adapt IK
- [ ] safely exclude helper head-front joint
- [ ] test weapon hand, aiming IK, gait, idle, crouch, jump, swim, vehicle poses
- [ ] compare three brothers and ensure side NPCs are untouched

No playable brother is replaced until these gates pass.

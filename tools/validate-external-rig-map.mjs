import fs from 'node:fs';
import { validateExternalSkeleton } from '../src/player/character/external-bone-map.js';

const glbPath = process.argv[2];
if (!glbPath) throw new Error('Usage: node tools/validate-external-rig-map.mjs <rigged.glb>');
const b = fs.readFileSync(glbPath);
if (b.toString('ascii', 0, 4) !== 'glTF') throw new Error('Not a GLB');
if (b.readUInt32LE(4) !== 2) throw new Error('Unsupported GLB version');
const totalLength = b.readUInt32LE(8);
if (totalLength !== b.length) throw new Error('GLB length header does not match file length');
const jsonLength = b.readUInt32LE(12);
if (b.toString('ascii', 16, 20) !== 'JSON') throw new Error('First GLB chunk is not JSON');
const json = JSON.parse(b.toString('utf8', 20, 20 + jsonLength));
const skin = json.skins?.[0];
if (!skin) throw new Error('GLB has no skin');
const names = skin.joints.map((i) => json.nodes[i]?.name ?? `joint_${i}`);
const result = validateExternalSkeleton(names);
const animationNames = (json.animations ?? []).map((a) => a.name.toLowerCase());
const animationChecks = {
  walk: animationNames.some((name) => name.includes('walk')),
  run: animationNames.some((name) => name.includes('run')),
};
const report = {
  fileBytes: b.length,
  meshCount: json.meshes?.length ?? 0,
  skinJointCount: names.length,
  animations: (json.animations ?? []).map((a) => ({ name: a.name, channelCount: a.channels?.length ?? 0 })),
  animationChecks,
  validation: result,
  readyForLiveReplacement: false,
  blockers: [
    'Bind-pose and forward-axis calibration have not been verified in-game.',
    'The source walk/run clips are not yet retargeted to the procedural player animator.',
    'Weapon-hand, foot-ground, and all gameplay-state tests remain outstanding.',
  ],
};
console.log(JSON.stringify(report, null, 2));
if (!result.ok || !animationChecks.walk || !animationChecks.run || report.meshCount < 1) process.exitCode = 1;

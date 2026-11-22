import React, {useId} from 'react';
import {useCurrentFrame} from 'remotion';
import {C, LOOK} from '../theme';
import {Pt} from './lib';

export type Pose = 'stand' | 'sit' | 'type' | 'run' | 'walk' | 'slump' | 'cheer';

export type HeroProps = {
  x: number; // ground point under the hips
  y: number; // floor y (raise it to jump)
  scale?: number;
  facing?: 1 | -1;
  pose?: Pose;
  pose2?: Pose; // blend toward this pose...
  mix?: number; // ...by this amount (0..1). Ease it in the scene.
  brow?: number; // -1 angry .. 0 neutral .. 1 sad
  browLift?: number; // px, raises both brows (surprise)
  mouth?: number; // -1 frown .. 1 smile
  mouthOpen?: number; // 0..1
  glasses?: boolean;
  scarf?: boolean; // costume pieces
  cap?: boolean;
  headphones?: boolean;
  fill?: string; // override body colour (background people are darker)
  backFill?: string;
  squash?: number; // 1 normal, <1 squashed, >1 stretched
  headTilt?: number; // degrees
  runPhase?: number; // radians, for the run cycle
  typeSpeed?: number; // typing bob speed
  variant?: 'hero' | 'shadow';
  eyeGlow?: number; // shadow eye intensity
  seed?: number;
};

// ---- body proportions (stick figure) ----
const THIGH = 82;
const SHIN = 98;
const UPPER_ARM = 62;
const FOREARM = 64;
const TORSO = 95;
const HEAD_R = 62;

// Standing height at scale 1, from the floor to the top of the head.
export const HERO_HEIGHT = 172 + TORSO + HEAD_R * 2 - 14;

const add = (a: Pt, b: Pt): Pt => [a[0] + b[0], a[1] + b[1]];
const rot = (v: Pt, deg: number): Pt => {
  const r = (deg * Math.PI) / 180;
  return [v[0] * Math.cos(r) - v[1] * Math.sin(r), v[0] * Math.sin(r) + v[1] * Math.cos(r)];
};

// Two-bone IK: returns [joint, end]. bend -1 puts the joint toward +x when the limb points down.
const ik = (a: Pt, target: Pt, l1: number, l2: number, bend: 1 | -1): [Pt, Pt] => {
  const dx = target[0] - a[0];
  const dy = target[1] - a[1];
  const dist = Math.hypot(dx, dy) || 1;
  const d = Math.min(l1 + l2 - 0.5, Math.max(Math.abs(l1 - l2) + 1, dist));
  const ux = dx / dist;
  const uy = dy / dist;
  const end: Pt = [a[0] + ux * d, a[1] + uy * d];
  const base = Math.atan2(uy, ux);
  const off = Math.acos(Math.min(1, Math.max(-1, (l1 * l1 + d * d - l2 * l2) / (2 * l1 * d))));
  const ang = base + bend * off;
  return [[a[0] + Math.cos(ang) * l1, a[1] + Math.sin(ang) * l1], end];
};

// Smooth noodle through the joint (a quadratic that passes through j at its midpoint).
// Straight bones with a small rounded joint, so knees and elbows read as real joints.
const noodle = (a: Pt, j: Pt, b: Pt) => {
  const p = (u: Pt, v: Pt, k: number): string => `${(u[0] + (v[0] - u[0]) * k).toFixed(1)},${(u[1] + (v[1] - u[1]) * k).toFixed(1)}`;
  return `M${p(a, a, 0)} L${p(a, j, 0.72)} Q${p(j, j, 0)} ${p(j, b, 0.28)} L${p(b, b, 0)}`;
};

type Rig = {
  hip: Pt;
  chest: Pt;
  shoulder: Pt;
  headC: Pt;
  tilt: number;
  legs: [Pt, Pt][]; // [knee, foot]
  arms: [Pt, Pt][]; // [elbow, hand]
};

// Full skeleton for one pose. Motions are kept small and smooth (realistic, not bouncy).
const rig = (pose: Pose, t: number, breath: number, runPhase: number, typeSpeed: number): Rig => {
  let hip: Pt = [0, -172];
  let lean = 0;
  let tilt = 0;
  let feet: [Pt, Pt] = [
    [-16, 0],
    [18, 0],
  ];
  let hands: [Pt, Pt] | null = null; // absolute targets; null = relative to shoulder
  let handRel: [Pt, Pt] = [
    [-40, 104 + breath * 2],
    [46, 102 + breath * 2],
  ];
  let elbowBend: [1 | -1, 1 | -1] = [1, -1];

  if (pose === 'sit' || pose === 'type') {
    hip = [0, -108];
    feet = [
      [74, 0],
      [92, 0],
    ];
    if (pose === 'type') {
      lean = 14;
      // small, quick finger-taps rather than big arm bobs
      const b1 = Math.min(0, Math.sin(t * typeSpeed) * 3);
      const b2 = Math.min(0, Math.sin(t * typeSpeed + 2.1) * 3);
      hands = [
        [122, -158 + b1],
        [142, -160 + b2],
      ];
    } else {
      lean = 2;
      handRel = [
        [46, 100],
        [58, 100],
      ];
      elbowBend = [1, 1];
    }
  } else if (pose === 'slump') {
    // sitting on the floor, back against the wall, legs out, head hanging
    hip = [0, -14];
    lean = -8;
    tilt = 24;
    feet = [
      [150, 0],
      [172, 0],
    ];
  } else if (pose === 'run') {
    const bob = Math.abs(Math.cos(runPhase)) * 7;
    hip = [0, -160 - bob];
    lean = 14;
    // heel kicks up behind first, then the foot reaches forward and lands
    const foot = (p: number): Pt => [Math.sin(p) * 68, -Math.max(0, Math.cos(p + 0.55)) * 60];
    feet = [foot(runPhase + Math.PI), foot(runPhase)];
    // arms swing opposite to the legs, elbows bent and pointing back
    const hand = (p: number): Pt => {
      const s = -Math.sin(p);
      return [s * 62 + 6, 110 - Math.abs(s) * 28];
    };
    handRel = [hand(runPhase), hand(runPhase + Math.PI)];
    elbowBend = [1, 1];
  } else if (pose === 'walk') {
    // calm walk: small steps, gentle arm swing
    const bob = Math.abs(Math.cos(runPhase)) * 3;
    hip = [0, -169 - bob];
    lean = 3;
    const foot = (p: number): Pt => [Math.sin(p) * 38, -Math.max(0, Math.cos(p + 0.6)) * 22];
    feet = [foot(runPhase + Math.PI), foot(runPhase)];
    const hand = (p: number): Pt => [-Math.sin(p) * 26 + 4, 108];
    handRel = [hand(runPhase), hand(runPhase + Math.PI)];
    elbowBend = [1, 1];
  } else if (pose === 'cheer') {
    const w = Math.sin(t * 0.12) * 3;
    handRel = [
      [-112, -62 + w],
      [116, -66 - w],
    ];
    elbowBend = [-1, 1];
    tilt = -6;
  }

  const torsoLen = TORSO * (1 + breath * 0.012);
  const chest = add(hip, rot([0, -torsoLen], lean));
  const shoulder = add(hip, rot([0, -torsoLen + 12], lean));
  let headC = add(chest, rot([0, -HEAD_R + 14 + breath * 1.5], lean * 0.6));
  if (pose === 'slump') headC = add(headC, [16, 6]); // head hangs forward and down
  const legs = feet.map((f) => ik(hip, f, THIGH, SHIN, -1));
  if (pose === 'slump') {
    // arms limp, hands resting on the floor beside the hips
    hands = [
      [-30, -2],
      [44, -2],
    ];
    elbowBend = [1, 1];
  }
  const targets: [Pt, Pt] = hands ?? [add(shoulder, handRel[0]), add(shoulder, handRel[1])];
  const arms = targets.map((h, i) => ik(shoulder, h, UPPER_ARM, FOREARM, elbowBend[i]));
  return {hip, chest, shoulder, headC, tilt, legs, arms};
};

// The channel's main character: a stick figure with a big round head (no neck),
// dot eyes, line brows and mouth, noodle limbs with soft joints, no fingers,
// and a thick black border around everything.
export const Hero: React.FC<HeroProps> = ({
  x,
  y,
  scale = 1,
  facing = 1,
  pose = 'stand',
  pose2,
  mix = 0,
  brow = 0,
  browLift = 0,
  mouth = 0,
  mouthOpen = 0,
  glasses = false,
  scarf = false,
  cap = false,
  headphones = false,
  fill,
  backFill,
  squash = 1,
  headTilt = 0,
  runPhase = 0,
  typeSpeed = 0.9,
  variant = 'hero',
  eyeGlow = 1,
  seed = 0,
}) => {
  const t = useCurrentFrame() + seed * 37;
  const gradId = useId().replace(/:/g, '');
  const shadow = variant === 'shadow';
  const LIMB = LOOK.heroLimb; // limb thickness (set by the current look)
  const line = LOOK.heroLine && !shadow; // line-art figure
  const breath = Math.sin(t / 16);

  // ---- skeleton: computed for each pose, then blended so poses never snap ----
  const A = rig(pose, t, breath, runPhase, typeSpeed);
  const B = pose2 ? rig(pose2, t, breath, runPhase, typeSpeed) : A;
  const m = pose2 ? Math.max(0, Math.min(1, mix)) : 0;
  const lp = (a: Pt, b: Pt): Pt => [a[0] + (b[0] - a[0]) * m, a[1] + (b[1] - a[1]) * m];
  const hip = lp(A.hip, B.hip);
  const chest = lp(A.chest, B.chest);
  const shoulder = lp(A.shoulder, B.shoulder);
  const headC = lp(A.headC, B.headC);
  const tilt = headTilt + A.tilt + (B.tilt - A.tilt) * m;
  const legs = [0, 1].map((i) => [lp(A.legs[i][0], B.legs[i][0]), lp(A.legs[i][1], B.legs[i][1])] as [Pt, Pt]);
  const arms = [0, 1].map((i) => [lp(A.arms[i][0], B.arms[i][0]), lp(A.arms[i][1], B.arms[i][1])] as [Pt, Pt]);

  // ---- face ----
  const blink = t % 113 < 4 ? 0.12 : 1;
  const eyeF: Pt = add(headC, [26, -6]);
  const eyeB: Pt = add(headC, [-4, -6]);
  const browBase = -22 - browLift;
  const browLine = (eye: Pt, innerLeft: boolean) => {
    const inner = eye[1] + browBase - brow * 8;
    const outer = eye[1] + browBase + brow * 3.5;
    const lx = eye[0] - 12;
    const rx = eye[0] + 12;
    return innerLeft ? `M${lx},${inner} L${rx},${outer}` : `M${lx},${outer} L${rx},${inner}`;
  };
  const mY = headC[1] + 30;
  const mx1 = headC[0] + 1;
  const mx2 = headC[0] + 31;

  // ---- colours ----
  const fillFront = shadow ? '#000' : fill ?? C.hero;
  const fillBack = shadow ? '#000' : backFill ?? C.heroDark;
  const border = shadow ? C.accent : LOOK.heroBorderColor;
  const bw = shadow ? 3.2 : line ? 0 : LOOK.heroBorder;

  const torsoPath = `M${hip[0]},${hip[1]} L${chest[0]},${chest[1]}`;
  const legPath = (i: number) => noodle(hip, legs[i][0], legs[i][1]);
  const armPath = (i: number) => noodle(shoulder, arms[i][0], arms[i][1]);

  // Stroke drawn twice: thick border underneath, colour on top.
  const stroke = (d: string, color: string, key: string) => (
    <g key={key}>
      <path d={d} stroke={border} strokeWidth={LIMB + bw * 2} fill="none" strokeLinecap="round" strokeLinejoin="round" />
      <path d={d} stroke={color} strokeWidth={LIMB} fill="none" strokeLinecap="round" strokeLinejoin="round" />
    </g>
  );

  const sx = squash === 1 ? 1 : 1 / Math.sqrt(squash);

  return (
    <g
      transform={`translate(${x},${y}) scale(${facing * scale * sx},${scale * squash})`}
      style={shadow ? {filter: `drop-shadow(0 0 6px ${C.accent}) drop-shadow(0 0 20px ${C.accent}88)`} : undefined}
    >
      {/* limbs first (back ones darker), then the torso on top so the joints
          where limbs meet the body are hidden, then the head */}
      {stroke(armPath(0), fillBack, 'ab')}
      {stroke(legPath(0), fillBack, 'lb')}
      {stroke(legPath(1), fillFront, 'lf')}
      {stroke(armPath(1), fillFront, 'af')}
      <path d={torsoPath} stroke={border} strokeWidth={LIMB + 4 + bw * 2} fill="none" strokeLinecap="round" />
      <path d={torsoPath} stroke={fillFront} strokeWidth={LIMB + 4} fill="none" strokeLinecap="round" />
      {scarf && !shadow ? (
        <g>
          <path d={`M${chest[0] - 20},${chest[1] + 4} Q${chest[0]},${chest[1] + 14} ${chest[0] + 22},${chest[1] + 2}`} stroke="#6E6E74" strokeWidth={16} fill="none" strokeLinecap="round" />
          <path
            d={`M${chest[0] - 12},${chest[1] + 10} q${-10 + Math.sin(t / 14) * 3},34 ${-18 + Math.sin(t / 11) * 4},62`}
            stroke="#5E5E64"
            strokeWidth={13}
            fill="none"
            strokeLinecap="round"
          />
        </g>
      ) : null}
      {LOOK.heroShade && !shadow ? (
        <defs>
          <radialGradient id={gradId} cx="0.38" cy="0.32" r="0.75">
            <stop offset="0" stopColor="#FFFFFF" />
            <stop offset="0.45" stopColor={fillFront} />
            <stop offset="1" stopColor="#5E5E62" />
          </radialGradient>
        </defs>
      ) : null}
      <g transform={`rotate(${tilt} ${headC[0]} ${headC[1] + HEAD_R * 0.6})`}>
        <circle
          cx={headC[0]}
          cy={headC[1]}
          r={HEAD_R}
          fill={line ? LOOK.heroHeadFill : LOOK.heroShade && !shadow ? `url(#${gradId})` : fillFront}
          stroke={line ? fillFront : border}
          strokeWidth={line ? LIMB * 0.75 : bw * 1.2}
        />
        {shadow ? (
          <g opacity={eyeGlow}>
            <ellipse cx={eyeF[0]} cy={eyeF[1]} rx={13} ry={3} fill={C.accent} transform={`rotate(-18 ${eyeF[0]} ${eyeF[1]})`} />
            <ellipse cx={eyeB[0]} cy={eyeB[1]} rx={11} ry={2.8} fill={C.accent} transform={`rotate(18 ${eyeB[0]} ${eyeB[1]})`} />
            <ellipse cx={eyeF[0]} cy={eyeF[1]} rx={7} ry={1.1} fill="#FFD0D5" transform={`rotate(-18 ${eyeF[0]} ${eyeF[1]})`} />
            <ellipse cx={eyeB[0]} cy={eyeB[1]} rx={6} ry={1} fill="#FFD0D5" transform={`rotate(18 ${eyeB[0]} ${eyeB[1]})`} />
          </g>
        ) : (
          <g>
            <ellipse cx={eyeF[0]} cy={eyeF[1]} rx={6.5} ry={6.5 * blink} fill={C.heroFace} />
            <ellipse cx={eyeB[0]} cy={eyeB[1]} rx={6} ry={6 * blink} fill={C.heroFace} />
            <path d={browLine(eyeF, true)} stroke={C.heroFace} strokeWidth={5.5} strokeLinecap="round" />
            <path d={browLine(eyeB, false)} stroke={C.heroFace} strokeWidth={5.5} strokeLinecap="round" />
            {mouthOpen > 0.05 ? (
              <ellipse cx={(mx1 + mx2) / 2} cy={mY + 3} rx={11} ry={9 * mouthOpen} fill={C.heroFace} />
            ) : (
              <path
                d={`M${mx1},${mY} Q${(mx1 + mx2) / 2},${mY + mouth * 12} ${mx2},${mY}`}
                stroke={C.heroFace}
                strokeWidth={4.5}
                fill="none"
                strokeLinecap="round"
              />
            )}
            {glasses ? (
              <g stroke={LOOK.heroShade ? "#18181A" : "#E6E6EA"} strokeWidth={3.2} fill="rgba(255,255,255,0.08)">
                <circle cx={eyeF[0]} cy={eyeF[1]} r={14.5} />
                <circle cx={eyeB[0]} cy={eyeB[1]} r={13.5} />
                <path d={`M${eyeB[0] + 13.5},${eyeB[1] - 2} L${eyeF[0] - 14.5},${eyeF[1] - 2}`} fill="none" />
                <path d={`M${eyeB[0] - 13.5},${eyeB[1] - 3} L${headC[0] - 40},${headC[1] - 12}`} fill="none" />
              </g>
            ) : null}
          </g>
        )}
        {cap ? (
          <g>
            <path d={`M${headC[0] - 60},${headC[1] - 34} Q${headC[0] - 10},${headC[1] - 96} ${headC[0] + 48},${headC[1] - 50} L${headC[0] + 40},${headC[1] - 28} Z`} fill="#2E2E33" />
            <path d={`M${headC[0] + 26},${headC[1] - 30} L${headC[0] + 82},${headC[1] - 22}`} stroke="#1A1A1D" strokeWidth={9} strokeLinecap="round" />
            <circle cx={headC[0] + 4} cy={headC[1] - 50} r={6} fill="#8A8A90" />
          </g>
        ) : null}
        {headphones ? (
          <g fill="none">
            <path d={`M${headC[0] - 50},${headC[1] + 4} Q${headC[0] - 46},${headC[1] - 82} ${headC[0] + 10},${headC[1] - 66}`} stroke="#2A2A2E" strokeWidth={9} strokeLinecap="round" />
            <ellipse cx={headC[0] - 46} cy={headC[1] + 6} rx={14} ry={22} fill="#2A2A2E" />
          </g>
        ) : null}
      </g>
      {LOOK.annotate && !shadow ? (
        <g stroke={C.white} strokeWidth={1.6} fill={C.white} opacity={0.85}>
          {(() => {
            const top = Math.min(headC[1] - HEAD_R, ...arms.map((a) => a[1][1]));
            const ax = -130;
            return (
              <>
                <line x1={ax} x2={ax} y1={0} y2={top} />
                <line x1={ax - 12} x2={ax + 12} y1={0} y2={0} />
                <line x1={ax - 12} x2={ax + 12} y1={top} y2={top} />
                <line x1={ax + 12} x2={headC[0] - HEAD_R} y1={top} y2={top} strokeDasharray="4 6" />
                <text
                  x={ax - 14}
                  y={top / 2}
                  stroke="none"
                  fontFamily={LOOK.mono}
                  fontSize={22}
                  textAnchor="end"
                  transform={`scale(${facing} 1)`}
                  style={{transformBox: 'fill-box', transformOrigin: 'center'}}
                >
                  {`H ${Math.round(-top)}`}
                </text>
                <circle cx={headC[0]} cy={headC[1]} r={3} />
                <text
                  x={headC[0] + HEAD_R + 14}
                  y={headC[1] - HEAD_R + 4}
                  stroke="none"
                  fontFamily={LOOK.mono}
                  fontSize={20}
                  transform={`scale(${facing} 1)`}
                  style={{transformBox: 'fill-box', transformOrigin: 'center'}}
                >
                  R62
                </text>
              </>
            );
          })()}
        </g>
      ) : null}
    </g>
  );
};

// His inner voice: same body, pure black, taller, glowing accent border, slit eyes.
export const Shadow: React.FC<{
  x: number;
  y: number;
  scale: number;
  facing?: 1 | -1;
  opacity?: number;
}> = ({x, y, scale, facing = 1, opacity = 1}) => {
  const t = useCurrentFrame();
  const flicker = 0.85 + 0.15 * Math.sin(t * 0.7) * Math.sin(t * 0.23);
  return (
    <g opacity={opacity}>
      <Hero
        x={x + Math.sin(t / 30) * 4}
        y={y}
        scale={scale}
        facing={facing}
        variant="shadow"
        eyeGlow={flicker}
        squash={1 + Math.sin(t / 22) * 0.012}
        seed={5}
      />
    </g>
  );
};

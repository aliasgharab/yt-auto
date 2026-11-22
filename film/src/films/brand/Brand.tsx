import React from 'react';
import {AbsoluteFill} from 'remotion';
import {applyLook, C, LOOK} from '../../theme';
import {LOOKS} from '../../looks';
import {LookFx} from '../../components/LookFx';
import {Hero} from '../../components/Hero';
import {Glow, Marker} from '../../components/Primitives';

// Channel branding for "Hidden Flaw" plus the per-video thumbnail, all in the documentary look.
// Render stills at frame 30 (markers are fully drawn by then).
export const CHANNEL = {name: 'HIDDEN FLAW', tagline: 'True tech stories, explained in minutes.'};

// Each exported component calls applyLook() first: children (and their LOOK fonts) are created
// by the caller before Frame itself renders.
const Frame: React.FC<{w: number; h: number; children: React.ReactNode}> = ({w, h, children}) => {
  return (
    <LookFx look="documentary">
      <AbsoluteFill style={{background: C.bgDark}}>
        <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} style={{position: 'absolute', inset: 0}}>
          {children}
        </svg>
      </AbsoluteFill>
    </LookFx>
  );
};

// A big shaded head on its own (avatar).
const Head: React.FC<{cx: number; cy: number; r: number; brow?: number}> = ({cx, cy, r, brow = 0.5}) => {
  const k = r / 62;
  const eye = (dx: number) => <circle cx={cx + dx * k} cy={cy - 6 * k} r={6.5 * k} fill={C.heroFace} />;
  const b = (dx: number, inner: 1 | -1) => {
    const x = cx + dx * k;
    const y = cy - 28 * k;
    return <path d={`M${x - 12 * k},${y + (inner < 0 ? -brow * 8 : brow * 3.5) * k} L${x + 12 * k},${y + (inner < 0 ? brow * 3.5 : -brow * 8) * k}`} stroke={C.heroFace} strokeWidth={5.5 * k} strokeLinecap="round" />;
  };
  return (
    <g>
      <defs>
        <radialGradient id="headShade" cx="0.38" cy="0.32" r="0.75">
          <stop offset="0" stopColor="#FFFFFF" />
          <stop offset="0.45" stopColor={C.hero} />
          <stop offset="1" stopColor="#5E5E62" />
        </radialGradient>
      </defs>
      <circle cx={cx} cy={cy} r={r} fill="url(#headShade)" />
      {eye(-14)}
      {eye(16)}
      {b(-14, 1)}
      {b(16, -1)}
      <path d={`M${cx - 12 * k},${cy + 30 * k} Q${cx + 2 * k},${cy + 24 * k} ${cx + 16 * k},${cy + 30 * k}`} stroke={C.heroFace} strokeWidth={5 * k} fill="none" strokeLinecap="round" />
    </g>
  );
};

export const Avatar: React.FC = () => {
  applyLook(LOOKS.documentary);
  return (
  <Frame w={800} h={800}>
    <Glow x={250} y={180} r={700} color={C.lamp} opacity={0.25} />
    <Head cx={400} cy={410} r={220} brow={0.45} />
    <Marker x={420} y={400} rx={300} ry={290} from={0} seed={5} />
  </Frame>
  );
};

export const Banner: React.FC = () => {
  // 2560x1440; everything important sits inside the 1546x423 safe area in the middle (x 507-2053)
  applyLook(LOOKS.documentary);
  return (
    <Frame w={2560} h={1440}>
      <Glow x={760} y={420} r={900} color={C.lamp} opacity={0.35} />
      <line x1={0} x2={2560} y1={930} y2={930} stroke="#2C2C30" strokeWidth={3} />
      <Hero x={700} y={930} scale={0.95} pose="stand" brow={0.4} mouth={-0.1} />
      <text x={1530} y={760} textAnchor="end" fontFamily={LOOK.display} fontSize={210} fill={C.white} letterSpacing={6}>
        HIDDEN
      </text>
      <text x={1830} y={760} textAnchor="middle" fontFamily={LOOK.display} fontSize={210} fill={C.white} letterSpacing={6}>
        FLAW
      </text>
      <Marker x={1830} y={672} rx={250} ry={132} from={0} seed={2} />
      <text x={1480} y={895} textAnchor="middle" fontFamily={LOOK.font} fontWeight={700} fontSize={54} fill="#B8B8BE" letterSpacing={3}>
        {CHANNEL.tagline.toUpperCase()}
      </text>
    </Frame>
  );
};

// Per-video thumbnail: one big word circled in red, one short red line, the Hero looking at it.
export type ThumbProps = {word: string; line?: string; brow?: number};
export const Thumbnail: React.FC<ThumbProps> = ({word, line = '', brow = 0.6}) => {
  applyLook(LOOKS.documentary);
  const w = word.toUpperCase();
  const size = Math.min(230, 640 / Math.max(1, w.length * 0.47));
  const textW = w.length * size * 0.47;
  const cx = 420;
  const cy = 330 - size * 0.38;
  return (
    <Frame w={1280} h={720}>
      <Glow x={1100} y={80} r={800} color={C.lamp} opacity={0.35} />
      <Hero x={1060} y={800} scale={1.5} pose="stand" facing={-1} brow={brow} mouth={-0.3} />
      <text x={cx} y={330} textAnchor="middle" fontFamily={LOOK.display} fontSize={size} fill={C.white} letterSpacing={3}>
        {w}
      </text>
      <Marker x={cx} y={cy} rx={textW * 0.6} ry={size * 0.75} from={0} seed={4} />
      {line ? (
        <text x={cx} y={540} textAnchor="middle" fontFamily={LOOK.font} fontWeight={700} fontSize={64} fill={C.accent} letterSpacing={3}>
          {line.toUpperCase()}
        </text>
      ) : null}
    </Frame>
  );
};

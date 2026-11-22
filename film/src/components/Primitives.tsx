import React, {useId} from 'react';
import {useCurrentFrame} from 'remotion';
import {C, LOOK, propFill} from '../theme';
import {Pt, circlePts, rectPts, wobblyPath} from './lib';

type Base = {
  fill?: string;
  stroke?: string;
  sw?: number;
  seed?: number;
  amp?: number;
  opacity?: number;
};

// Flat prop shape with a thin wobbly outline. The current look decides
// whether it's filled, tinted or line-only, and how thick and wobbly the line is.
export const WPoly: React.FC<Base & {pts: Pt[]; closed?: boolean}> = ({
  pts,
  closed = true,
  fill,
  stroke,
  sw = 2.2,
  seed = 1,
  amp = 1.4,
  opacity = 1,
}) => {
  const t = useCurrentFrame();
  const f = closed ? propFill(fill ?? C.prop) : 'none';
  const s = stroke ?? C.outline;
  return (
    <path
      d={wobblyPath(pts, t, seed, amp * LOOK.wobble, closed)}
      fill={f}
      stroke={s}
      strokeWidth={sw * LOOK.strokeScale}
      strokeLinejoin="round"
      strokeLinecap="round"
      opacity={opacity}
    />
  );
};

export const WRect: React.FC<Base & {x: number; y: number; w: number; h: number}> = ({x, y, w, h, ...rest}) => (
  <WPoly pts={rectPts(x, y, w, h)} {...rest} />
);

export const WCircle: React.FC<Base & {cx: number; cy: number; r: number}> = ({cx, cy, r, ...rest}) => (
  <WPoly pts={circlePts(cx, cy, r)} {...rest} />
);

export const WLine: React.FC<Base & {pts: Pt[]}> = ({pts, ...rest}) => <WPoly pts={pts} closed={false} {...rest} />;

// Big soft light glow. Use for every light source. Blueprint draws it as dashed
// "light radius" rings instead.
export const Glow: React.FC<{
  x: number;
  y: number;
  r: number;
  color: string;
  opacity?: number;
  ry?: number;
}> = ({x, y, r, color, opacity = 1, ry}) => {
  const id = useId().replace(/:/g, '');
  const t = useCurrentFrame();
  if (LOOK.glow === 'hatch') {
    if (r < 60 || opacity < 0.05) return null;
    const k = ry ? ry / r : 1;
    return (
      <g opacity={Math.min(1, opacity) * 0.55} stroke={C.white} fill="none" strokeWidth={1.6}>
        <ellipse cx={x} cy={y} rx={r * 0.22} ry={r * 0.22 * k} strokeDasharray="6 8" strokeDashoffset={-t * 0.6} />
        <ellipse cx={x} cy={y} rx={r * 0.42} ry={r * 0.42 * k} strokeDasharray="2 10" strokeDashoffset={t * 0.4} />
      </g>
    );
  }
  const mult = (LOOK.glow === 'neon' ? 0.8 : LOOK.glow === 'chalk' ? 0.5 : 1) * LOOK.glowStrength;
  return (
    <g style={{mixBlendMode: 'screen'}} opacity={opacity * mult}>
      <defs>
        <radialGradient id={id}>
          <stop offset="0" stopColor={color} stopOpacity={0.85} />
          <stop offset="0.25" stopColor={color} stopOpacity={0.35} />
          <stop offset="0.6" stopColor={color} stopOpacity={0.1} />
          <stop offset="1" stopColor={color} stopOpacity={0} />
        </radialGradient>
      </defs>
      <ellipse cx={x} cy={y} rx={r} ry={ry ?? r} fill={`url(#${id})`} />
    </g>
  );
};

// Light cone (lamp, street light, spotlight), pointing down.
export const Cone: React.FC<{
  x: number;
  y: number;
  topW: number;
  bottomW: number;
  h: number;
  color: string;
  opacity?: number;
}> = ({x, y, topW, bottomW, h, color, opacity = 0.25}) => {
  const id = useId().replace(/:/g, '');
  const pts = `${x - topW / 2},${y} ${x + topW / 2},${y} ${x + bottomW / 2},${y + h} ${x - bottomW / 2},${y + h}`;
  if (LOOK.glow === 'hatch') {
    return <polygon points={pts} fill="none" stroke={C.white} strokeWidth={1.5} strokeDasharray="10 8" opacity={0.5} />;
  }
  return (
    <g style={{mixBlendMode: 'screen'}} opacity={opacity}>
      <defs>
        <linearGradient id={id} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor={color} stopOpacity={0.9} />
          <stop offset="1" stopColor={color} stopOpacity={0} />
        </linearGradient>
      </defs>
      <polygon points={pts} fill={`url(#${id})`} />
    </g>
  );
};

// Full-frame background in the current style (grid paper, chalk smudges...).
export const Backdrop: React.FC<{dark?: boolean}> = ({dark = false}) => {
  const bg = dark ? C.bgDark : C.bg;
  return (
    <g>
      <rect x={0} y={0} width={1920} height={1080} fill={bg} />
      {LOOK.name === 'blueprint'
        ? [
            ...Array.from({length: 49}, (_, i) => (
              <line key={'v' + i} x1={i * 40} x2={i * 40} y1={0} y2={1080} stroke="#FFFFFF" strokeWidth={i % 5 === 0 ? 1.2 : 0.5} opacity={i % 5 === 0 ? 0.22 : 0.1} />
            )),
            ...Array.from({length: 28}, (_, i) => (
              <line key={'h' + i} x1={0} x2={1920} y1={i * 40} y2={i * 40} stroke="#FFFFFF" strokeWidth={i % 5 === 0 ? 1.2 : 0.5} opacity={i % 5 === 0 ? 0.22 : 0.1} />
            )),
          ]
        : null}
      {LOOK.name === 'chalk'
        ? [
            [400, 300, 380, 0.05],
            [1400, 620, 520, 0.06],
            [900, 900, 300, 0.04],
            [1650, 200, 260, 0.05],
          ].map(([x, y, r, o], i) => <ellipse key={i} cx={x} cy={y} rx={r} ry={r * 0.45} fill="#FFFFFF" opacity={o} transform={`rotate(-12 ${x} ${y})`} />)
        : null}
    </g>
  );
};

// Dark room background with the thin floor line.
export const Ground: React.FC<{floor: number}> = ({floor}) => (
  <>
    <Backdrop />
    {LOOK.lineOnly ? null : <rect x={0} y={floor} width={1920} height={1080 - floor} fill={C.bgFloor} />}
    <line x1={0} x2={1920} y1={floor} y2={floor} stroke={C.floorLine} strokeWidth={2 * Math.max(1, LOOK.strokeScale * 0.8)} />
  </>
);

// Red hand-drawn marker loop that draws itself on (documentary-style annotation).
// Only shows in looks with `markers` on.
export const Marker: React.FC<{x: number; y: number; rx: number; ry: number; from: number; to?: number; seed?: number; box?: boolean}> = ({
  x,
  y,
  rx,
  ry,
  from,
  to = Infinity,
  seed = 3,
  box = false,
}) => {
  const t = useCurrentFrame();
  if (!LOOK.markers || t < from || t > to + 8) return null;
  const draw = Math.min(1, (t - from) / 12);
  if (draw < 0.02) return null; // never show a lone round cap
  const fade = t > to ? 1 - (t - to) / 8 : 1;
  // one loop plus a short overshoot (~12 degrees) that stays on the ellipse,
  // with a gentle uneven radius, like a quick pen stroke
  const pts: string[] = [];
  if (box) {
    // hand-drawn rounded box for blocks of text (an ellipse can't enclose a wide block's corners)
    const r = Math.min(rx, ry) * 0.35;
    const w = (i: number) => Math.sin(i * 1.7 + seed) * 3;
    const L = x - rx, R = x + rx, T = y - ry, B = y + ry;
    const d = `M${L + r},${T + w(1)} L${R - r},${T + w(2)} Q${R},${T} ${R + w(3)},${T + r} L${R + w(4)},${B - r} Q${R},${B} ${R - r},${B + w(5)} L${L + r},${B + w(6)} Q${L},${B} ${L + w(7)},${B - r} L${L + w(8)},${T + r} Q${L},${T} ${L + r + 4},${T - 2} L${L + r + 60},${T - 6}`;
    return (
      <path d={d} fill="none" stroke={C.accent} strokeWidth={7} strokeLinecap="round" strokeLinejoin="round" pathLength={1} strokeDasharray={1} strokeDashoffset={1 - draw} opacity={fade} style={{filter: `drop-shadow(0 0 6px ${C.accent}aa)`}} />
    );
  }
  const turns = 1.035;
  for (let i = 0; i <= 64; i++) {
    const u = i / 64;
    const a = -2.2 + u * Math.PI * 2 * turns;
    const k = 1 + 0.04 * Math.sin(u * Math.PI * 2 * 3 + seed) * Math.sin(u * Math.PI);
    pts.push(`${i === 0 ? 'M' : 'L'}${(x + Math.cos(a) * rx * k).toFixed(1)},${(y + Math.sin(a) * ry * k).toFixed(1)}`);
  }
  return (
    <path
      d={pts.join(' ')}
      fill="none"
      stroke={C.accent}
      strokeWidth={7}
      strokeLinecap="round"
      pathLength={1}
      strokeDasharray={1}
      strokeDashoffset={1 - draw}
      opacity={fade}
      style={{filter: `drop-shadow(0 0 6px ${C.accent}aa)`}}
    />
  );
};

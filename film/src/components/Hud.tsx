import React from 'react';
import {AbsoluteFill, Easing, interpolate, random, useCurrentFrame} from 'remotion';
import {BAR, C, LOOK} from '../theme';
import {fadeInOut, pop} from './lib';

// Thin black bars, top and bottom. Always on top.
export const Letterbox: React.FC = () => (
  <AbsoluteFill style={{pointerEvents: 'none'}}>
    <div style={{position: 'absolute', top: 0, left: 0, right: 0, height: BAR, background: '#000'}} />
    <div style={{position: 'absolute', bottom: 0, left: 0, right: 0, height: BAR, background: '#000'}} />
  </AbsoluteFill>
);

// Game-style DAY counter in the top left. `days` = [frame, day] keyframes.
export const DayCounter: React.FC<{days: [number, number][]; hideAt?: number}> = ({days, hideAt}) => {
  const f = useCurrentFrame();
  if (hideAt !== undefined && f >= hideAt) return null;
  let cur = days[0];
  for (const d of days) if (f >= d[0]) cur = d;
  if (cur[1] <= 0) return null; // day 0 = counter hidden
  const since = f - cur[0];
  // gentle swell when the day changes, no bounce
  const s = f > 0 && since < 30 ? 1 + 0.12 * Math.sin((Math.min(since, 20) / 20) * Math.PI) : 1;
  return (
    <div
      style={{
        position: 'absolute',
        left: 44,
        top: BAR + 22,
        fontFamily: LOOK.font,
        fontWeight: 700,
        color: LOOK.caption ? '#111' : C.white,
        fontSize: 30 * LOOK.fontScale,
        letterSpacing: 2,
        padding: '6px 16px',
        border: LOOK.caption ? '4px solid #111' : `2px solid ${C.white}40`,
        borderRadius: LOOK.caption ? 0 : 10,
        background: LOOK.caption ? '#FFE14D' : 'rgba(0,0,0,0.45)',
        boxShadow: LOOK.caption ? '5px 5px 0 #111' : undefined,
        scale: String(s),
        transformOrigin: 'left center',
      }}
    >
      <span style={{color: LOOK.caption ? '#111' : `${C.white}99`, fontSize: 22 * LOOK.fontScale, marginRight: 10}}>DAY</span>
      {cur[1]}
    </div>
  );
};

// Narrator: small, white, top centre, 8 words max, fades in and out.
export const Narrator: React.FC<{lines: [number, number, string][]}> = ({lines}) => {
  const f = useCurrentFrame();
  const line = lines.find(([a, b]) => f >= a && f <= b);
  if (!line) return null;
  const [a, b, text] = line;
  if (text.split(' ').length > 8) throw new Error(`Narrator line over 8 words: ${text}`);
  const o = fadeInOut(f, a, b, 14, 14);
  if (LOOK.caption) {
    // comic-book caption box
    return (
      <div
        style={{
          position: 'absolute',
          top: BAR + 40,
          left: '50%',
          translate: `-50% ${(1 - o) * -10}px`,
          opacity: o,
          fontFamily: LOOK.font,
          fontWeight: 700,
          fontSize: 34 * LOOK.fontScale,
          color: '#111',
          background: '#FFE14D',
          border: '4px solid #111',
          padding: '8px 22px',
          boxShadow: '6px 6px 0 #111',
          textTransform: 'uppercase',
          whiteSpace: 'nowrap',
        }}
      >
        {text}
      </div>
    );
  }
  return (
    <div
      style={{
        position: 'absolute',
        top: BAR + 34,
        left: 0,
        right: 0,
        textAlign: 'center',
        fontFamily: LOOK.font,
        fontWeight: 700,
        fontSize: 40 * LOOK.fontScale,
        color: C.white,
        opacity: o,
        translate: `0px ${(1 - o) * 8}px`,
        textShadow: '0 2px 12px rgba(0,0,0,0.9)',
        textTransform: LOOK.uppercase ? 'uppercase' : undefined,
        letterSpacing: LOOK.uppercase ? 2 : undefined,
      }}
    >
      {text}
    </div>
  );
};

// Rep counts that pop on screen. [frame, text, x, y]
export const RepPops: React.FC<{pops: [number, string, number, number][]}> = ({pops}) => {
  const f = useCurrentFrame();
  return (
    <>
      {pops
        .filter(([a]) => f >= a && f < a + 26)
        .map(([a, text, x, y], i) => {
          const g = f - a;
          const s = interpolate(g, [0, 8], [0.85, 1], {extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic)});
          return (
            <div
              key={i + text}
              style={{
                position: 'absolute',
                left: x,
                top: y - g * 0.8,
                fontFamily: LOOK.display,
                fontWeight: 700,
                fontSize: 48 * LOOK.fontScale,
                color: LOOK.popStyle === 'headline' ? C.accent : C.white,
                WebkitTextStroke: LOOK.popStyle === 'headline' ? undefined : `2px ${C.hero}`,
                scale: String(Math.max(0, s)),
                opacity: interpolate(g, [0, 5, 18, 26], [0, 1, 1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}),
                translate: '-50% -50%',
                whiteSpace: 'nowrap',
                textShadow: LOOK.popStyle === 'headline' ? '0 4px 0 #000, 0 0 30px rgba(0,0,0,0.8)' : `0 0 18px ${C.hero}`,
                textTransform: LOOK.popStyle === 'headline' ? 'uppercase' : undefined,
              }}
            >
              {text}
            </div>
          );
        })}
    </>
  );
};

// White flash for big hits. Frames are local to the parent sequence.
export const Flash: React.FC<{at: number[]; color?: string}> = ({at, color = '#FFFFFF'}) => {
  const f = useCurrentFrame();
  // documentary look: a soft 3-frame flash; other looks: a hard 7-frame one
  const doc = LOOK.name === 'documentary';
  const env = doc ? ([[0, 1, 3], [0.45, 0.25, 0]] as const) : ([[0, 2, 7], [0.95, 0.8, 0]] as const);
  const o = Math.max(0, ...at.map((a) => (f >= a ? interpolate(f - a, [...env[0]], [...env[1]], {extrapolateRight: 'clamp'}) : 0)));
  const burst = LOOK.burst ? <Burst at={at} /> : null;
  if (o <= 0) return burst;
  return (
    <>
      <AbsoluteFill style={{background: color, opacity: o, mixBlendMode: 'screen'}} />
      {burst}
    </>
  );
};

// Comic-book impact burst with a sound-effect word.
const Burst: React.FC<{at: number[]; word?: string}> = ({at, word = 'BOOT!'}) => {
  const f = useCurrentFrame();
  const hit = [...at].reverse().find((a) => f >= a && f < a + 40);
  if (hit === undefined) return null;
  const g = f - hit;
  const s = pop(g, 10);
  const o = interpolate(g, [30, 40], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const spikes = 18;
  const pts = (r1: number, r2: number) =>
    Array.from({length: spikes * 2}, (_, i) => {
      const a = (i / (spikes * 2)) * Math.PI * 2;
      const r = i % 2 === 0 ? r1 * (1 + 0.15 * random(`b${i}`)) : r2;
      return `${960 + Math.cos(a) * r},${520 + Math.sin(a) * r * 0.62}`;
    }).join(' ');
  return (
    <AbsoluteFill style={{opacity: o}}>
      <svg width={1920} height={1080} viewBox="0 0 1920 1080" style={{scale: String(Math.max(0, s)), transformOrigin: '960px 520px', rotate: '-6deg'}}>
        <polygon points={pts(560, 380)} fill="#FF2E4C" stroke="#111" strokeWidth={10} strokeLinejoin="round" />
        <polygon points={pts(440, 300)} fill="#FFE14D" stroke="#111" strokeWidth={8} strokeLinejoin="round" />
        <text x={960} y={575} textAnchor="middle" fontFamily={LOOK.display} fontSize={190} fill="#FF2E4C" stroke="#111" strokeWidth={10} paintOrder="stroke">
          {word}
        </text>
      </svg>
    </AbsoluteFill>
  );
};

// Radial speed lines for big hits.
export const SpeedLines: React.FC<{at: number; dur?: number; cx?: number; cy?: number; color?: string}> = ({
  at,
  dur = 16,
  cx = 960,
  cy = 540,
  color = '#FFFFFF',
}) => {
  const f = useCurrentFrame();
  const g = f - at;
  if (LOOK.name === 'documentary' || g < 0 || g > dur) return null;
  const o = interpolate(g, [0, 3, dur], [0, 1, 0]);
  const lines = Array.from({length: 46}, (_, i) => {
    const a = random(`a${i}-${Math.floor(g / 2)}`) * Math.PI * 2;
    const r1 = 330 + random(`r${i}-${Math.floor(g / 2)}`) * 220;
    const r2 = 1300;
    const w = 2 + random(`w${i}`) * 7;
    return (
      <path
        key={i}
        d={`M${cx + Math.cos(a) * r1},${cy + Math.sin(a) * r1} L${cx + Math.cos(a + 0.012) * r2},${cy + Math.sin(a + 0.012) * r2} L${cx + Math.cos(a - 0.012) * r2},${cy + Math.sin(a - 0.012) * r2} Z`}
        fill={color}
        stroke={color}
        strokeWidth={w}
        strokeLinejoin="round"
      />
    );
  });
  return (
    <AbsoluteFill style={{opacity: o}}>
      <svg width={1920} height={1080} viewBox="0 0 1920 1080">
        {lines}
      </svg>
    </AbsoluteFill>
  );
};

// The Shadow's words: accent colour, beside the Shadow, flickering in.
export const ShadowLine: React.FC<{
  text: string;
  x: number;
  y: number;
  from: number;
  to: number;
  size?: number;
  anchor?: 'start' | 'middle' | 'end';
}> = ({text, x, y, from, to, size = 46, anchor = 'start'}) => {
  const f = useCurrentFrame();
  const base = fadeInOut(f, from, to, 10, 14);
  if (base <= 0) return null;
  const flick = f - from < 10 ? (random(`fl${f}`) > 0.35 ? 1 : 0.3) : 1;
  return (
    <text
      x={x}
      y={y + Math.sin(f / 9) * 3}
      fontFamily={LOOK.font}
      fontWeight={700}
      fontSize={size}
      fill={C.accent}
      textAnchor={anchor}
      opacity={base * flick}
      style={{filter: `drop-shadow(0 0 10px ${C.accent})`}}
    >
      {text}
    </text>
  );
};

// Locked camera with optional slow push-in toward a focus point.
export const Cam: React.FC<{
  children: React.ReactNode;
  push?: [number, number];
  dur: number;
  focus?: [number, number];
}> = ({children, push = [1, 1], dur, focus = [960, 540]}) => {
  const f = useCurrentFrame();
  const s = interpolate(f, [0, dur], push, {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  return (
    <AbsoluteFill style={{scale: String(s), transformOrigin: `${focus[0]}px ${focus[1]}px`}}>
      {children}
    </AbsoluteFill>
  );
};

export const Stage: React.FC<{children: React.ReactNode}> = ({children}) => (
  <svg width={1920} height={1080} viewBox="0 0 1920 1080" style={{position: 'absolute', inset: 0}}>
    {children}
  </svg>
);

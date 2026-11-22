import React from 'react';
import {random, useCurrentFrame} from 'remotion';
import {C} from '../theme';
import {Cone, Glow, WLine, WRect} from './Primitives';

const wrap = (x: number, period: number, pad: number) => ((((x + pad) % period) + period) % period) - pad;

// Night city that scrolls past behind a running character (parallax).
export const CityScroll: React.FC<{floor: number; speed: number; seed?: string; moonX?: number}> = ({
  floor,
  speed,
  seed = 'city',
  moonX = 1480,
}) => {
  const t = useCurrentFrame();
  const dist = t * speed;

  const layer = (n: number, period: number, factor: number, tag: string, fill: string, hMin: number, hMax: number, windows: boolean, outline: string) => {
    const off = dist * factor;
    return Array.from({length: n}, (_, i) => {
      const w = 110 + random(`${seed}${tag}w${i}`) * 140;
      const h = hMin + random(`${seed}${tag}h${i}`) * (hMax - hMin);
      const x = wrap((i / n) * period - off, period, 300);
      const y = floor - h;
      const cols = Math.floor(w / 36);
      const rows = Math.floor(h / 52);
      return (
        <g key={tag + i}>
          <WRect x={x} y={y} w={w} h={h + 4} fill={fill} stroke={outline} sw={1.8} seed={i * 3 + factor * 10} />
          {windows
            ? Array.from({length: cols * rows}, (_, k) => {
                const on = random(`${seed}${tag}win${i}-${k}`) > 0.82;
                if (!on) return null;
                const cx = x + 16 + (k % cols) * 36;
                const cy = y + 22 + Math.floor(k / cols) * 52;
                return (
                  <g key={k}>
                    <rect x={cx} y={cy} width={14} height={20} fill={C.street} opacity={0.75} />
                    <Glow x={cx + 7} y={cy + 10} r={34} color={C.street} opacity={0.35} />
                  </g>
                );
              })
            : null}
        </g>
      );
    });
  };

  const lampPeriod = 640;
  const lampOff = dist;

  return (
    <g>
      <rect x={0} y={0} width={1920} height={1080} fill={C.bgDark} />
      {/* moon: a light source */}
      <Glow x={moonX} y={230} r={420} color={C.moon} opacity={0.45} />
      <circle cx={moonX} cy={230} r={54} fill={C.moon} />
      <circle cx={moonX + 18} cy={218} r={11} fill="#C4CCE6" />
      <circle cx={moonX - 14} cy={246} r={7} fill="#C4CCE6" />
      {layer(14, 2600, 0.15, 'far', '#101017', 240, 520, true, '#2C2C34')}
      {layer(10, 2400, 0.45, 'mid', '#15151C', 140, 330, true, '#55555E')}
      <rect x={0} y={floor} width={1920} height={1080 - floor} fill={C.bgFloor} />
      <line x1={0} x2={1920} y1={floor} y2={floor} stroke={C.floorLine} strokeWidth={2} />
      {/* curb ticks so the ground reads as moving */}
      {Array.from({length: 16}, (_, i) => {
        const x = wrap(i * 140 - dist, 2240, 100);
        return <line key={i} x1={x} x2={x + 40} y1={floor + 26} y2={floor + 26} stroke="#26262D" strokeWidth={3} strokeLinecap="round" />;
      })}
      {/* street lights: light sources with pools on the ground */}
      {Array.from({length: 4}, (_, i) => {
        const x = wrap(i * lampPeriod - lampOff, lampPeriod * 4, 300);
        const flick = 0.92 + 0.08 * Math.sin(t * 0.9 + i);
        return (
          <g key={'l' + i}>
            <Cone x={x + 46} y={floor - 400} topW={40} bottomW={360} h={400} color={C.street} opacity={0.22 * flick} />
            <Glow x={x + 46} y={floor} r={230} ry={40} color={C.street} opacity={0.6 * flick} />
            <WLine pts={[[x, floor], [x, floor - 420], [x + 46, floor - 420]]} stroke={C.outline} sw={6} fill="none" seed={i} />
            <WRect x={x + 26} y={floor - 424} w={42} h={16} fill="#2A2A30" seed={i + 9} />
            <Glow x={x + 46} y={floor - 404} r={130} color={C.street} opacity={0.9 * flick} />
          </g>
        );
      })}
    </g>
  );
};

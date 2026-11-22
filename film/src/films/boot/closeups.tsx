import React from 'react';
import {useCurrentFrame} from 'remotion';
import {C, LOOK} from '../../theme';
import {Backdrop, Glow, WCircle, WLine, WPoly, WRect} from '../../components/Primitives';

// Glasses resting on a stack of manuals, under the lamp.
export const GlassesCU: React.FC = () => {
  const t = useCurrentFrame();
  const glint = ((t * 9) % 900) - 150;
  const books = [
    {y: 700, h: 120, w: 980, c: '#2A2330', label: 'x86 MANUAL  VOL.1'},
    {y: 590, h: 110, w: 920, c: '#1F2A30', label: 'x86 MANUAL  VOL.2'},
    {y: 490, h: 100, w: 950, c: '#30282A', label: 'x86 MANUAL  VOL.3'},
  ];
  return (
    <g>
      <Backdrop dark />
      <Glow x={1250} y={120} r={1000} color={C.lamp} opacity={0.5} />
      <line x1={0} x2={1920} y1={820} y2={820} stroke={C.floorLine} strokeWidth={2} />
      {books.map((b, i) => (
        <g key={i}>
          <WRect x={960 - b.w / 2} y={b.y} w={b.w} h={b.h} fill={b.c} seed={60 + i} sw={2.5} />
          <text x={960 - b.w / 2 + 60} y={b.y + b.h / 2 + 16} fontFamily={LOOK.mono} fontWeight={700} fontSize={44} fill="#8C8C96">
            {b.label}
          </text>
        </g>
      ))}
      {/* glasses */}
      <g transform="translate(960 420)">
        <WCircle cx={-110} cy={0} r={78} fill="rgba(255,255,255,0.06)" stroke="#E6E6EA" sw={9} seed={64} amp={1} />
        <WCircle cx={110} cy={0} r={78} fill="rgba(255,255,255,0.06)" stroke="#E6E6EA" sw={9} seed={65} amp={1} />
        <WLine pts={[[-34, -8], [0, -22], [34, -8]]} stroke="#E6E6EA" sw={9} seed={66} amp={1} />
        <WLine pts={[[-186, -6], [-300, 60]]} stroke="#E6E6EA" sw={8} seed={67} amp={1} />
        <WLine pts={[[186, -6], [300, 60]]} stroke="#E6E6EA" sw={8} seed={68} amp={1} />
        <clipPath id="lensClip">
          <circle cx={-110} cy={0} r={74} />
          <circle cx={110} cy={0} r={74} />
        </clipPath>
        <g clipPath="url(#lensClip)">
          <rect x={glint - 200} y={-100} width={40} height={220} fill="#FFFFFF" opacity={0.35} transform="skewX(-25)" />
        </g>
      </g>
      <Glow x={960} y={500} r={600} ry={200} color={C.lamp} opacity={0.35} />
    </g>
  );
};

export const ClockCU: React.FC<{speed: number}> = ({speed}) => {
  const t = useCurrentFrame();
  const m = t * speed;
  return (
    <g>
      <Backdrop dark />
      <Glow x={960} y={540} r={700} color={C.moon} opacity={0.25} />
      <WCircle cx={960} cy={540} r={330} fill="#15151B" seed={70} sw={3} />
      {Array.from({length: 12}, (_, i) => {
        const a = (i / 12) * Math.PI * 2;
        return <line key={i} x1={960 + Math.cos(a) * 280} y1={540 + Math.sin(a) * 280} x2={960 + Math.cos(a) * 305} y2={540 + Math.sin(a) * 305} stroke={C.outline} strokeWidth={6} strokeLinecap="round" />;
      })}
      <line x1={960} y1={540} x2={960 + Math.sin((m / 12) * (Math.PI / 180)) * 170} y2={540 - Math.cos((m / 12) * (Math.PI / 180)) * 170} stroke={C.white} strokeWidth={14} strokeLinecap="round" />
      <line x1={960} y1={540} x2={960 + Math.sin(m * (Math.PI / 180)) * 250} y2={540 - Math.cos(m * (Math.PI / 180)) * 250} stroke={C.white} strokeWidth={8} strokeLinecap="round" />
      <circle cx={960} cy={540} r={14} fill={C.white} />
    </g>
  );
};

export const ScopeCU: React.FC<{glitch: boolean}> = ({glitch}) => {
  const t = useCurrentFrame();
  const pts: string[] = [];
  for (let x = 0; x <= 1200; x += 6) {
    const ph = ((x + t * 18) % 200) / 200;
    let y = ph < 0.5 ? -120 : 120;
    if (glitch) y += Math.sin(x * 0.21 + t) * 50 * Math.sin(x * 0.013);
    pts.push(`${x === 0 ? 'M' : 'L'}${360 + x},${540 + y}`);
  }
  return (
    <g>
      <Backdrop dark />
      <Glow x={960} y={540} r={900} ry={500} color={C.led} opacity={0.3} />
      <WRect x={300} y={240} w={1320} h={600} fill="#07110B" seed={80} sw={3} />
      {Array.from({length: 11}, (_, i) => (
        <line key={'v' + i} x1={360 + i * 120} x2={360 + i * 120} y1={260} y2={820} stroke="#1A3324" strokeWidth={2} />
      ))}
      {Array.from({length: 5}, (_, i) => (
        <line key={'h' + i} x1={320} x2={1600} y1={300 + i * 120} y2={300 + i * 120} stroke="#1A3324" strokeWidth={2} />
      ))}
      <path d={pts.join(' ')} stroke={glitch ? C.error : C.led} strokeWidth={6} fill="none" style={{filter: `drop-shadow(0 0 10px ${glitch ? C.error : C.led})`}} />
    </g>
  );
};

export const MugCU: React.FC<{count: number}> = ({count}) => {
  const t = useCurrentFrame();
  return (
    <g>
      <Backdrop dark />
      <Glow x={1300} y={160} r={900} color={C.lamp} opacity={0.45} />
      <line x1={0} x2={1920} y1={820} y2={820} stroke={C.floorLine} strokeWidth={2} />
      {Array.from({length: count}, (_, i) => {
        const x = 960 - (count - 1) * 170 + i * 340;
        return (
          <g key={i}>
            <WPoly pts={[[x - 120, 470], [x + 120, 470], [x + 105, 820], [x - 105, 820]]} fill="#2B2B33" seed={90 + i} sw={3} />
            <WCircle cx={x + 150} cy={610} r={60} fill="none" seed={95 + i} sw={14} stroke="#2B2B33" />
            <WCircle cx={x + 150} cy={610} r={60} fill="none" seed={95 + i} sw={2.5} />
            {i === count - 1
              ? [0, 1, 2].map((k) => (
                  <path
                    key={k}
                    d={`M${x - 50 + k * 50},450 q ${Math.sin(t * 0.2 + k) * 30},-60 0,-120 q ${-Math.sin(t * 0.2 + k) * 30},-60 0,-120`}
                    stroke="#9A9AA4"
                    strokeWidth={8}
                    fill="none"
                    strokeLinecap="round"
                    opacity={0.35}
                    transform={`translate(0 ${-((t * 2 + k * 20) % 40)})`}
                  />
                ))
              : null}
          </g>
        );
      })}
    </g>
  );
};

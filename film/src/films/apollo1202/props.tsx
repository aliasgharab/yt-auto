import React from 'react';
import {Easing, interpolate, random, useCurrentFrame} from 'remotion';
import {C, FLOOR, LOOK} from '../../theme';
import {Backdrop, Cone, Glow, Ground, WLine, WPoly, WRect} from '../../components/Primitives';
import {Pt} from '../../components/lib';

const CL = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;
const EASE = {...CL, easing: Easing.inOut(Easing.cubic)} as const;

const PAPER = '#CBCBCE';
const INK = '#1E1E21';

// ---------------------------------------------------------------- space
export const Stars: React.FC<{n?: number; seed?: string; maxY?: number}> = ({n = 140, seed = 's', maxY = 1080}) => {
  const t = useCurrentFrame();
  return (
    <g>
      {Array.from({length: n}, (_, i) => {
        const x = random(`${seed}x${i}`) * 1920;
        const y = random(`${seed}y${i}`) * maxY;
        const r = 0.8 + random(`${seed}r${i}`) * 1.8;
        const tw = 0.55 + 0.45 * Math.sin(t * 0.05 + i * 1.7);
        return <circle key={i} cx={x} cy={y} r={r} fill={C.white} opacity={0.25 + 0.5 * tw * random(`${seed}o${i}`)} />;
      })}
    </g>
  );
};

export const Earth: React.FC<{x: number; y: number; r: number}> = ({x, y, r}) => (
  <g>
    <Glow x={x} y={y} r={r * 3.2} color={C.moon} opacity={0.35} />
    <circle cx={x} cy={y} r={r} fill="#2A2A2E" />
    {/* lit crescent from the right */}
    <path d={`M${x},${y - r} A${r},${r} 0 0 1 ${x},${y + r} A${r * 0.45},${r} 0 0 0 ${x},${y - r} Z`} fill="#D6D6DA" />
    <path d={`M${x + r * 0.2},${y - r * 0.5} q${r * 0.35},${r * 0.2} ${r * 0.5},${r * 0.6}`} stroke="#8E8E94" strokeWidth={r * 0.12} fill="none" strokeLinecap="round" />
  </g>
);

// Lunar surface with craters and rocks. `scroll` moves it left (px).
export const MoonGround: React.FC<{y: number; scroll?: number; seed?: string; rocks?: boolean}> = ({y, scroll = 0, seed = 'm', rocks = true}) => {
  const span = 2400;
  const craters = Array.from({length: 14}, (_, i) => ({
    x: random(`${seed}cx${i}`) * span,
    dy: 20 + random(`${seed}cy${i}`) * (1080 - y - 40),
    r: 40 + random(`${seed}cr${i}`) * 110,
  }));
  return (
    <g>
      <rect x={0} y={y} width={1920} height={1080 - y} fill="#1E1E21" />
      <line x1={0} x2={1920} y1={y} y2={y} stroke="#4A4A50" strokeWidth={2} />
      {craters.map((c, i) => {
        const x = (((c.x - scroll) % span) + span) % span - 240;
        const k = 0.25 + (c.dy / (1080 - y)) * 0.4; // perspective squash
        return (
          <g key={i}>
            <ellipse cx={x} cy={y + c.dy} rx={c.r} ry={c.r * k} fill="#141416" />
            <path d={`M${x - c.r},${y + c.dy} A${c.r},${c.r * k} 0 0 0 ${x + c.r},${y + c.dy}`} stroke="#3A3A40" strokeWidth={3} fill="none" />
          </g>
        );
      })}
      {rocks
        ? Array.from({length: 26}, (_, i) => {
            const x = (((random(`${seed}rx${i}`) * span - scroll * 1.15) % span) + span) % span - 240;
            const yy = y + 10 + random(`${seed}ry${i}`) * (1080 - y - 20);
            const r = 4 + random(`${seed}rr${i}`) * 10 * (yy - y) / (1080 - y);
            return <ellipse key={'r' + i} cx={x} cy={yy} rx={r * 1.5} ry={r} fill="#3A3A40" />;
          })
        : null}
    </g>
  );
};

// ---------------------------------------------------------------- the lunar module, side view
// (x, y) = ground point under the centre. About 400px wide and 450px tall at scale 1.
export const Lander: React.FC<{x: number; y: number; scale?: number; flame?: number; tilt?: number; ascent?: boolean; cutaway?: number; windowLight?: number}> = ({
  x,
  y,
  scale = 1,
  flame = 0,
  tilt = 0,
  ascent = true,
  cutaway = 0,
  windowLight = 0.5,
}) => {
  const t = useCurrentFrame();
  const fl = flame * (0.85 + 0.15 * Math.sin(t * 1.3) * Math.sin(t * 0.7));
  return (
    <g transform={`translate(${x} ${y}) rotate(${tilt}) scale(${scale})`}>
      {fl > 0 ? (
        <g>
          <Cone x={0} y={-78} topW={60} bottomW={260} h={180} color={C.white} opacity={0.35 * fl} />
          <Glow x={0} y={-60} r={160} color={C.white} opacity={0.7 * fl} />
        </g>
      ) : null}
      {/* legs */}
      {[-1, 1].map((k) => (
        <g key={k}>
          <WLine pts={[[k * 118, -150], [k * 200, -12]]} sw={7} stroke="#8E8E94" seed={700 + k} />
          <WLine pts={[[k * 125, -118], [k * 170, -60]]} sw={4} stroke="#6E6E74" seed={702 + k} />
          <ellipse cx={k * 202} cy={-6} rx={30} ry={8} fill="#7A7A80" />
        </g>
      ))}
      <WLine pts={[[0, -150], [0, -20]]} sw={6} stroke="#6E6E74" seed={704} />
      <ellipse cx={0} cy={-14} rx={24} ry={7} fill="#5A5A60" />
      {/* engine bell */}
      <WPoly pts={[[-28, -112], [28, -112], [44, -74], [-44, -74]]} fill="#2A2A2E" seed={705} />
      {/* descent stage (foil) */}
      <WPoly pts={[[-140, -228], [140, -228], [150, -200], [150, -126], [136, -110], [-136, -110], [-150, -126], [-150, -200]]} fill="#6E6E74" seed={706} />
      {[0, 1, 2, 3].map((i) => (
        <path key={i} d={`M${-130 + i * 70},-222 l12,40 l-8,30 l14,40`} stroke="#8A8A90" strokeWidth={2} fill="none" opacity={0.6} />
      ))}
      {ascent ? (
        <g>
          <WPoly pts={[[-118, -228], [-138, -300], [-104, -384], [26, -404], [108, -372], [140, -302], [122, -228]]} fill="#A2A2A8" seed={707} />
          <WPoly pts={[[-60, -404], [-30, -430], [30, -430], [40, -404]]} fill="#8E8E94" seed={708} />
          {/* front window */}
          <polygon points="62,-366 112,-346 74,-318" fill="#121214" />
          {windowLight > 0 ? <Glow x={84} y={-342} r={60} color={C.lamp} opacity={windowLight} /> : null}
          {/* hatch */}
          <rect x={60} y={-306} width={50} height={56} rx={4} fill="#88888E" stroke="#5A5A60" strokeWidth={2} />
          {/* RCS quads */}
          {[-1, 1].map((k) => (
            <g key={'q' + k} stroke="#5A5A60" strokeWidth={6} strokeLinecap="round">
              <line x1={k * 136} y1={-322} x2={k * 166} y2={-322} />
              <line x1={k * 160} y1={-338} x2={k * 160} y2={-306} />
            </g>
          ))}
          {/* antenna dish */}
          <line x1={-70} y1={-404} x2={-112} y2={-468} stroke="#8E8E94" strokeWidth={4} />
          <path d="M-142,-470 Q-112,-440 -82,-470" stroke="#B0B0B6" strokeWidth={5} fill="none" />
          {cutaway > 0 ? (
            <g opacity={cutaway}>
              <rect x={-96} y={-372} width={150} height={120} rx={6} fill="#0E0E10" stroke="#D8D8DC" strokeWidth={3} strokeDasharray="10 6" />
              <rect x={-80} y={-342} width={118} height={56} rx={4} fill="#5A5A60" stroke="#B0B0B6" strokeWidth={2} />
              {[0, 1, 2, 3, 4].map((i) => (
                <line key={i} x1={-72 + i * 22} x2={-72 + i * 22} y1={-338} y2={-292} stroke="#3A3A40" strokeWidth={3} />
              ))}
              <text x={-21} y={-264} textAnchor="middle" fontFamily={LOOK.font} fontWeight={700} fontSize={22} fill={C.white} letterSpacing={2}>
                COMPUTER
              </text>
            </g>
          ) : null}
        </g>
      ) : (
        <WPoly pts={[[-140, -228], [140, -228], [130, -238], [-130, -238]]} fill="#5A5A60" seed={709} />
      )}
    </g>
  );
};

// ---------------------------------------------------------------- the Moon (near side) with the landing site
const MARIA: [number, number, number, number, number][] = [
  // cx, cy (unit disc), rx, ry, rotation
  [-0.36, -0.33, 0.27, 0.22, -10],
  [-0.6, 0.02, 0.22, 0.42, 10],
  [0.17, -0.33, 0.15, 0.14, 0],
  [0.3, -0.04, 0.17, 0.13, 20],
  [0.66, -0.26, 0.1, 0.08, 0],
  [0.54, 0.16, 0.1, 0.15, -15],
  [0.33, 0.27, 0.07, 0.08, 0],
  [-0.16, 0.36, 0.16, 0.11, 0],
  [-0.4, 0.5, 0.1, 0.07, 0],
];
export const SITE: Pt = [0.24, 0.03];
export const MoonMap: React.FC<{cx?: number; cy?: number; r?: number; pin?: number; label?: number; track?: number}> = ({cx = 960, cy = 570, r = 420, pin = 0, label = 0, track = 0}) => {
  const sx = cx + SITE[0] * r;
  const sy = cy + SITE[1] * r;
  return (
    <g>
      <Backdrop dark />
      <Stars n={90} seed="mm" />
      <Glow x={cx} y={cy} r={r * 1.6} color={C.moon} opacity={0.22} />
      <circle cx={cx} cy={cy} r={r} fill="#8C8C92" />
      {MARIA.map(([x, y, rx, ry, rot], i) => (
        <ellipse key={i} cx={cx + x * r} cy={cy + y * r} rx={rx * r} ry={ry * r} fill="#55555B" transform={`rotate(${rot} ${cx + x * r} ${cy + y * r})`} />
      ))}
      {/* Tycho and a few craters */}
      <circle cx={cx - 0.1 * r} cy={cy + 0.68 * r} r={0.05 * r} fill="#B4B4BA" />
      <circle cx={cx - 0.28 * r} cy={cy - 0.05 * r} r={0.035 * r} fill="#A8A8AE" />
      <circle cx={cx} cy={cy} r={r} fill="none" stroke="#B8B8BE" strokeWidth={2} />
      {/* terminator shade */}
      <path d={`M${cx - r * 0.2},${cy - r * 0.98} A${r},${r} 0 0 0 ${cx - r * 0.2},${cy + r * 0.98} A${r * 0.9},${r} 0 0 1 ${cx - r * 0.2},${cy - r * 0.98}`} fill="#000" opacity={0.0} />
      {track > 0 ? (
        <path d={`M${sx - 260},${sy - 120} Q${sx - 120},${sy - 100} ${sx},${sy}`} stroke={C.white} strokeWidth={3} strokeDasharray="10 8" fill="none" pathLength={1} strokeDashoffset={0} opacity={track * 0.8} />
      ) : null}
      {pin > 0.02 ? (
        <g opacity={Math.min(1, pin * 2)} transform={`translate(${sx} ${sy - (1 - pin) * 30})`}>
          <Glow x={0} y={0} r={60} color={C.accent} opacity={0.6} />
          <circle cx={0} cy={0} r={13} fill={C.accent} />
          <circle cx={0} cy={0} r={5} fill="#FFE0E0" />
        </g>
      ) : null}
      {label > 0 ? (
        <g opacity={label} fontFamily={LOOK.font} fontWeight={700} letterSpacing={3} stroke="#0B0B0C" strokeWidth={8} paintOrder="stroke" strokeLinejoin="round">
          <line x1={sx + 16} y1={sy + 10} x2={sx + 120} y2={sy + 110} stroke={C.white} strokeWidth={2.5} />
          <text x={sx + 130} y={sy + 122} fontSize={38} fill={C.white}>
            SEA OF TRANQUILITY
          </text>
          <text x={sx + 130} y={sy + 162} fontSize={28} fill="#D0D0D4">
            LANDING SITE
          </text>
        </g>
      ) : null}
    </g>
  );
};

// ---------------------------------------------------------------- inside the lunar module (side-on)
export const CABIN_PANEL: Pt = [960, FLOOR - 300];
export const Cabin: React.FC<{alarm?: number; lamp?: number}> = ({alarm = 0, lamp = 0}) => {
  const t = useCurrentFrame();
  const [px, py] = CABIN_PANEL;
  return (
    <g>
      <Ground floor={FLOOR} />
      {/* curved cabin walls */}
      <path d={`M0,120 Q960,40 1920,120 L1920,${FLOOR} L0,${FLOOR} Z`} fill="#121214" />
      {Array.from({length: 9}, (_, i) => (
        <line key={i} x1={120 + i * 210} x2={120 + i * 210} y1={110} y2={FLOOR} stroke="#1B1B1E" strokeWidth={4} />
      ))}
      {/* two triangular windows, moonlight */}
      {[
        [470, 1],
        [1450, -1],
      ].map(([wx, k]) => (
        <g key={wx}>
          <polygon points={`${wx - 110 * k},200 ${wx + 110 * k},240 ${wx - 70 * k},420`} fill="#1C1C20" stroke="#3A3A40" strokeWidth={4} />
          <Glow x={wx} y={290} r={330} color={C.moon} opacity={0.32} />
          <Stars n={12} seed={`w${wx}`} maxY={0} />
        </g>
      ))}
      {/* central instrument panel with the DSKY */}
      <WRect x={px - 110} y={py - 90} w={220} h={290} fill="#2E2E33" seed={720} />
      {Array.from({length: 6}, (_, i) => (
        <circle key={i} cx={px - 76 + (i % 3) * 76} cy={py - 56 + Math.floor(i / 3) * 40} r={11} fill="#1A1A1D" stroke="#5A5A60" strokeWidth={2} />
      ))}
      <rect x={px - 80} y={py + 10} width={160} height={70} rx={4} fill="#0E0E10" stroke="#4A4A50" strokeWidth={2} />
      <rect x={px - 72} y={py + 18} width={40} height={20} fill={lamp > 0 ? '#F4F1EA' : '#26262A'} />
      {lamp > 0 ? <Glow x={px - 52} y={py + 28} r={90} color={C.lamp} opacity={lamp * (0.8 + 0.2 * Math.sin(t * 0.4))} /> : null}
      <text x={px + 30} y={py + 66} textAnchor="middle" fontFamily={LOOK.mono} fontWeight={700} fontSize={26} fill={alarm > 0 ? C.accent : '#6A6A70'} opacity={alarm > 0 ? alarm : 1}>
        {alarm > 0 ? '1202' : '0000'}
      </text>
      {Array.from({length: 12}, (_, i) => (
        <rect key={'k' + i} x={px - 80 + (i % 6) * 28} y={py + 104 + Math.floor(i / 6) * 30} width={20} height={20} rx={3} fill="#4A4A50" />
      ))}
      <Glow x={px} y={py + 40} r={220} color={C.screen} opacity={0.18} />
    </g>
  );
};

// A helmet bubble over a standing or seated Hero's head.
export const Helmet: React.FC<{x: number; y: number; scale?: number; sit?: boolean; facing?: 1 | -1}> = ({x, y, scale = 1, sit = false, facing = 1}) => {
  const hx = x + (sit ? 4 : 0) * facing * scale;
  const hy = y - (sit ? 251 : 315) * scale;
  const r = 84 * scale;
  return (
    <g>
      <circle cx={hx} cy={hy} r={r} fill="rgba(255,255,255,0.05)" stroke="#A8A8AE" strokeWidth={5 * scale} />
      <path d={`M${hx - r * 0.55},${hy - r * 0.62} A${r * 0.85},${r * 0.85} 0 0 1 ${hx + r * 0.1},${hy - r * 0.85}`} stroke="#FFFFFF" strokeWidth={6 * scale} fill="none" opacity={0.45} strokeLinecap="round" />
      <rect x={hx - r * 0.75} y={hy + r * 0.78} width={r * 1.5} height={14 * scale} rx={6} fill="#7A7A80" />
    </g>
  );
};

// A short bob of hair drawn behind a Hero head (draw this before the Hero).
export const Hair: React.FC<{x: number; y: number; scale?: number; sit?: boolean; facing?: 1 | -1; color?: string}> = ({x, y, scale = 1, sit = false, facing = 1, color = '#3E3E44'}) => {
  const hx = x + (sit ? 4 : 0) * facing * scale;
  const hy = y - (sit ? 251 : 315) * scale;
  const k = facing;
  const s = scale;
  return (
    <g fill={color}>
      <circle cx={hx - 8 * k * s} cy={hy - 8 * s} r={74 * s} />
      <path d={`M${hx - 78 * k * s},${hy - 10 * s} Q${hx - 90 * k * s},${hy + 50 * s} ${hx - 60 * k * s},${hy + 70 * s} L${hx - 10 * k * s},${hy + 40 * s} L${hx - 10 * k * s},${hy} Z`} />
    </g>
  );
};

// ---------------------------------------------------------------- the DSKY close-up
const STATUS = [
  ['UPLINK ACTY', 'TEMP'],
  ['NO ATT', 'GIMBAL LOCK'],
  ['STBY', 'PROG'],
  ['KEY REL', 'RESTART'],
  ['OPR ERR', 'TRACKER'],
  ['', 'ALT'],
];
export const DSKY_R1: Pt = [1170, 488];
export const DSKY_PROG: Pt = [700, 360];
export const Dsky: React.FC<{lamp?: number; code?: number; restart?: number; verb?: string; noun?: string}> = ({lamp = 0, code = 0, restart = 0, verb = '16', noun = '68'}) => {
  const t = useCurrentFrame();
  const flick = 0.9 + 0.1 * Math.sin(t * 0.5);
  const digit = (txt: string, x: number, y: number, size: number, col = '#D8D8DC') => (
    <text x={x} y={y} textAnchor="middle" fontFamily={LOOK.mono} fontWeight={700} fontSize={size} fill={col} letterSpacing={6}>
      {txt}
    </text>
  );
  return (
    <g>
      <Backdrop dark />
      <Glow x={960} y={440} r={900} ry={600} color={C.screen} opacity={0.18} />
      <WRect x={360} y={110} w={1200} h={870} fill="#3A3A3F" sw={3} seed={730} />
      {/* status lamps */}
      <WRect x={400} y={150} w={400} h={500} fill="#1A1A1D" seed={731} />
      {STATUS.map((row, r) =>
        row.map((lab, c) => {
          const x = 420 + c * 190;
          const y = 170 + r * 78;
          const lit = (lab === 'PROG' && lamp > 0) || (lab === 'RESTART' && restart > 0);
          const o = lab === 'PROG' ? lamp : lab === 'RESTART' ? restart : 0;
          return (
            <g key={lab + r + c}>
              <rect x={x} y={y} width={170} height={60} rx={4} fill={lit ? '#EFEBE0' : '#2A2A2E'} opacity={lit ? 0.4 + 0.6 * o * flick : 1} />
              {lit ? <Glow x={x + 85} y={y + 30} r={190} color={C.lamp} opacity={o * flick} /> : null}
              <text x={x + 85} y={y + 38} textAnchor="middle" fontFamily={LOOK.font} fontWeight={700} fontSize={22} fill={lit ? '#1A1A1A' : '#5E5E64'} letterSpacing={1}>
                {lab}
              </text>
            </g>
          );
        }),
      )}
      {/* numeric display */}
      <WRect x={860} y={150} w={620} h={500} fill="#0C0C0E" seed={732} />
      <rect x={890} y={176} width={150} height={90} rx={4} fill="#26262A" />
      <text x={965} y={230} textAnchor="middle" fontFamily={LOOK.font} fontWeight={700} fontSize={20} fill="#6A6A70">COMP ACTY</text>
      {[['PROG', 1290, 190], ['VERB', 960, 310], ['NOUN', 1290, 310]].map(([lab, x, y]) => (
        <g key={lab as string}>
          <rect x={(x as number) - 60} y={y as number} width={120} height={28} rx={3} fill="#3A3A40" />
          <text x={x as number} y={(y as number) + 22} textAnchor="middle" fontFamily={LOOK.font} fontWeight={700} fontSize={20} fill="#C8C8CC" letterSpacing={2}>
            {lab}
          </text>
        </g>
      ))}
      {digit('63', 1290, 262, 54)}
      {digit(code > 0 ? '05' : verb, 960, 384, 54)}
      {digit(code > 0 ? '09' : noun, 1290, 384, 54)}
      {[440, 530, 620].map((y) => (
        <line key={y} x1={900} x2={1440} y1={y - 44} y2={y - 44} stroke="#2E2E33" strokeWidth={3} />
      ))}
      {code > 0 ? (
        <g opacity={Math.min(1, code)}>
          <Glow x={DSKY_R1[0]} y={DSKY_R1[1] - 18} r={260} ry={90} color={C.accent} opacity={0.35} />
          {digit('+01202', DSKY_R1[0], DSKY_R1[1], 76, C.accent)}
        </g>
      ) : (
        digit('+00487', DSKY_R1[0], DSKY_R1[1], 76)
      )}
      {digit(code > 0 ? '+00000' : '-00156', 1170, 578, 76)}
      {digit(code > 0 ? '+00000' : '+05912', 1170, 640 - 2, 60)}
      {/* keypad */}
      {['VERB', 'NOUN', '+', '-', '0', '7', '8', '9', '4', '5', '6', '1', '2', '3', 'CLR', 'PRO', 'KEY REL', 'ENTR', 'RSET'].map((k, i) => {
        const col = i % 10;
        const row = Math.floor(i / 10);
        const x = 420 + col * 110;
        const y = 700 + row * 130;
        return (
          <g key={k + i}>
            <rect x={x} y={y} width={92} height={100} rx={8} fill="#26262A" stroke="#55555A" strokeWidth={2} />
            <text x={x + 46} y={y + 60} textAnchor="middle" fontFamily={LOOK.font} fontWeight={700} fontSize={k.length > 2 ? 20 : 34} fill="#C8C8CC">
              {k}
            </text>
          </g>
        );
      })}
    </g>
  );
};

// ---------------------------------------------------------------- evidence paper
export const Doc: React.FC<{
  x?: number;
  y?: number;
  w?: number;
  h?: number;
  title?: string;
  lines: string[];
  reveal?: number[]; // local frame at which each line types on
  tilt?: number;
  hand?: boolean; // handwritten
  size?: number;
  gap?: number;
  stamp?: string;
  stampAt?: number;
  stampXY?: Pt;
  backdrop?: boolean;
  children?: React.ReactNode;
}> = ({x = 560, y = 150, w = 800, h = 780, title, lines, reveal, tilt = -2, hand = false, size = 40, gap = 64, stamp, stampAt = 0, stampXY, backdrop = true, children}) => {
  const t = useCurrentFrame();
  const [stx, sty] = stampXY ?? [x + w - 230, y + h - 110];
  return (
    <g>
      {backdrop ? (
        <>
          <Backdrop dark />
          <Glow x={x + w * 0.9} y={y - 40} r={1000} color={C.lamp} opacity={0.3} />
        </>
      ) : null}
      <g transform={`rotate(${tilt} ${x + w / 2} ${y + h / 2})`}>
        <rect x={x + 10} y={y + 14} width={w} height={h} fill="#000" opacity={0.5} />
        <rect x={x} y={y} width={w} height={h} fill={PAPER} stroke="#8A8A90" strokeWidth={2} />
        {title ? (
          <text x={x + 60} y={y + 90} fontFamily={LOOK.font} fontWeight={700} fontSize={44} fill={INK} letterSpacing={3}>
            {title}
          </text>
        ) : null}
        {title ? <line x1={x + 60} x2={x + w - 60} y1={y + 116} y2={y + 116} stroke="#7A7A80" strokeWidth={2} /> : null}
        {lines.map((l, i) => {
          const r0 = reveal ? reveal[i] ?? 0 : i * 10;
          const n = Math.max(0, Math.floor((t - r0) * 1.8));
          return (
            <text
              key={i}
              x={x + 60}
              y={y + (title ? 190 : 110) + i * gap}
              fontFamily={hand ? LOOK.font : LOOK.mono}
              fontWeight={hand ? 400 : 700}
              fontSize={size}
              fill={hand ? '#26263A' : '#2A2A2E'}
              letterSpacing={hand ? 1 : 0}
              style={{whiteSpace: 'pre'}}
            >
              {l.slice(0, n)}
            </text>
          );
        })}
        {stamp ? (
          <g transform={`rotate(-10 ${stx} ${sty})`} opacity={interpolate(t, [stampAt, stampAt + 4], [0, 1], CL)}>
            <rect x={stx - 190} y={sty - 52} width={380} height={96} fill="none" stroke={C.accent} strokeWidth={8} />
            <text x={stx} y={sty + 22} textAnchor="middle" fontFamily={LOOK.display} fontSize={66} fill={C.accent} letterSpacing={5}>
              {stamp}
            </text>
          </g>
        ) : null}
        {children}
      </g>
    </g>
  );
};

// ---------------------------------------------------------------- 600 million viewers, drawn as TV sets
export const TvGrid: React.FC<{fill: number}> = ({fill}) => {
  const cols = 15;
  const rows = 8;
  const n = Math.round(fill * cols * rows);
  return (
    <g>
      <Backdrop dark />
      <Glow x={960} y={480} r={900} ry={500} color={C.screen} opacity={0.14} />
      {Array.from({length: cols * rows}, (_, i) => {
        const c = i % cols;
        const r = Math.floor(i / cols);
        const x = 330 + c * 86;
        const y = 190 + r * 76;
        const on = i < n;
        return (
          <g key={i} opacity={on ? 1 : 0.25}>
            <line x1={x + 20} y1={y - 2} x2={x + 10} y2={y - 16} stroke="#6A6A70" strokeWidth={2} />
            <line x1={x + 30} y1={y - 2} x2={x + 42} y2={y - 16} stroke="#6A6A70" strokeWidth={2} />
            <rect x={x} y={y} width={58} height={44} rx={6} fill="#3A3A40" />
            <rect x={x + 6} y={y + 6} width={38} height={32} rx={4} fill={on ? '#DADADE' : '#1A1A1D'} />
            {on ? <Glow x={x + 25} y={y + 22} r={40} color={C.screen} opacity={0.35} /> : null}
          </g>
        );
      })}
      <text x={960} y={870} textAnchor="middle" fontFamily={LOOK.display} fontSize={110} fill={C.white} letterSpacing={4}>
        {Math.round(fill * 600).toLocaleString('en-US')},000,000
      </text>
      <text x={960} y={930} textAnchor="middle" fontFamily={LOOK.font} fontWeight={700} fontSize={30} fill="#8A8A90" letterSpacing={4}>
        ONE SET = FIVE MILLION PEOPLE WATCHING
      </text>
    </g>
  );
};

// ---------------------------------------------------------------- the descent chart (recurring motif)
const curve = (u: number): Pt => [300 + 1280 * u, 250 + 560 * (1 - Math.pow(1 - u, 1.7))];
export const ALARMS: [number, string][] = [
  [0.42, '1202'],
  [0.47, '1202'],
  [0.72, '1201'],
  [0.75, '1202'],
  [0.79, '1202'],
];
export const chartXY = curve;
export const DescentChart: React.FC<{
  progress: number; // 0..1 Eagle along the curve
  alarmsShown?: number; // how many alarm marks are visible (fractional = drawing)
  fuel?: number | null; // seconds of fuel left, null = hide gauge
  landed?: number;
  small?: boolean; // drawn on a console screen (no backdrop)
  codes?: boolean; // show the alarm code labels
}> = ({progress, alarmsShown = 0, fuel = null, landed = 0, small = false, codes = true}) => {
  const t = useCurrentFrame();
  const pts = Array.from({length: 60}, (_, i) => curve(i / 59));
  const done = Array.from({length: 60}, (_, i) => curve((i / 59) * progress));
  const [ex, ey] = curve(progress);
  return (
    <g>
      {small ? null : (
        <>
          <Backdrop dark />
          <Glow x={960} y={540} r={1000} ry={600} color={C.screen} opacity={0.12} />
        </>
      )}
      {Array.from({length: 13}, (_, i) => (
        <line key={'g' + i} x1={300 + i * (1280 / 12)} x2={300 + i * (1280 / 12)} y1={230} y2={830} stroke="#FFFFFF" opacity={0.06} strokeWidth={1.5} />
      ))}
      {Array.from({length: 7}, (_, i) => (
        <line key={'h' + i} x1={300} x2={1580} y1={230 + i * 100} y2={230 + i * 100} stroke="#FFFFFF" opacity={0.06} strokeWidth={1.5} />
      ))}
      <line x1={300} x2={300} y1={220} y2={830} stroke="#8A8A90" strokeWidth={3} />
      <line x1={300} x2={1600} y1={830} y2={830} stroke="#8A8A90" strokeWidth={3} />
      <g fontFamily={LOOK.font} fontWeight={700} fill="#9A9AA0" letterSpacing={3}>
        <text x={300} y={200} fontSize={30}>ALTITUDE</text>
        <text x={1580} y={930} fontSize={30} textAnchor="end">MINUTES INTO THE LANDING</text>
        {[0, 2, 4, 6, 8, 10, 12].map((m) => (
          <text key={m} x={300 + (m / 12.6) * 1280} y={880} fontSize={26} textAnchor="middle">
            {m}
          </text>
        ))}
        <text x={286} y={262} fontSize={24} textAnchor="end">50,000 FT</text>
        <text x={286} y={826} fontSize={24} textAnchor="end">0</text>
      </g>
      <path d={'M' + pts.map((p) => p.join(',')).join(' L')} stroke="#5A5A60" strokeWidth={4} strokeDasharray="12 10" fill="none" />
      <path d={'M' + done.map((p) => p.join(',')).join(' L')} stroke={C.white} strokeWidth={5} fill="none" />
      {/* landing site */}
      <g>
        <line x1={1580} x2={1580} y1={810} y2={850} stroke={C.white} strokeWidth={3} />
        <text x={1580} y={790} textAnchor="end" fontFamily={LOOK.font} fontWeight={700} fontSize={26} fill="#C8C8CC" letterSpacing={2} opacity={landed > 0 ? 0 : 1}>
          TRANQUILITY
        </text>
      </g>
      {/* alarms */}
      {ALARMS.map(([u, code], i) => {
        const k = Math.max(0, Math.min(1, alarmsShown - i));
        if (k <= 0.02) return null;
        const [ax, ay] = curve(u);
        // labels fan out so the late cluster never overlaps
        const [dx, dy] = ([[0, -70], [0, 80], [-90, -100], [0, -150], [90, -100]] as Pt[])[i];
        const up = dy < 0;
        const lx = ax + dx;
        const ly = ay + dy;
        return (
          <g key={i} opacity={k}>
            <Glow x={ax} y={ay} r={70} color={C.accent} opacity={0.6 * k} />
            <circle cx={ax} cy={ay} r={10 + (1 - k) * 18} fill={C.accent} />
            <line x1={ax} x2={lx} y1={ay + (up ? -14 : 14)} y2={ly + (up ? 8 : -34)} stroke={C.accent} strokeWidth={3} opacity={codes ? 1 : 0} />
            <text x={lx} y={ly} textAnchor="middle" fontFamily={LOOK.mono} fontWeight={700} fontSize={34} fill={C.accent} opacity={codes ? 1 : 0}>
              {code}
            </text>
          </g>
        );
      })}
      {/* Eagle icon */}
      <g transform={`translate(${ex} ${ey})`}>
        <Glow x={0} y={0} r={60} color={C.white} opacity={0.4} />
        <polygon points="-14,-4 14,-4 10,-20 -10,-20" fill={C.white} />
        <rect x={-16} y={-4} width={32} height={12} fill="#C8C8CC" />
        <line x1={-14} y1={8} x2={-22} y2={20} stroke={C.white} strokeWidth={3} />
        <line x1={14} y1={8} x2={22} y2={20} stroke={C.white} strokeWidth={3} />
      </g>
      {/* program alarm tally, fixed slot bottom-left of the chart */}
      {alarmsShown > 0 && !small ? (
        <g>
          <text x={340} y={720} fontFamily={LOOK.font} fontWeight={700} fontSize={30} fill="#C8C8CC" letterSpacing={3}>
            PROGRAM ALARMS
          </text>
          {[0, 1, 2, 3, 4].map((i) => (
            <rect key={i} x={340 + i * 52} y={740} width={40} height={40} rx={4} fill={alarmsShown - i > 0.3 ? C.accent : 'none'} stroke={alarmsShown - i > 0.3 ? C.accent : '#5A5A60'} strokeWidth={3} />
          ))}
        </g>
      ) : null}
      {/* fuel gauge, at the right edge of the chart */}
      {fuel !== null ? (
        <g>
          <text x={1730} y={200} textAnchor="middle" fontFamily={LOOK.font} fontWeight={700} fontSize={30} fill="#C8C8CC" letterSpacing={3}>
            FUEL
          </text>
          <rect x={1680} y={230} width={100} height={600} rx={8} fill="#141416" stroke="#8A8A90" strokeWidth={3} />
          {(() => {
            const h = (Math.max(0, fuel) / 180) * 584;
            const low = fuel < 60;
            const blink = low && landed <= 0 ? 0.75 + 0.25 * Math.sin(t * 0.6) : 1;
            return (
              <g>
                <rect x={1688} y={822 - h} width={84} height={h} rx={4} fill={low ? C.accent : '#C8C8CC'} opacity={blink} />
                <text x={1730} y={880} textAnchor="middle" fontFamily={LOOK.mono} fontWeight={700} fontSize={40} fill={low ? C.accent : C.white}>
                  {`0:${String(Math.max(0, Math.floor(fuel)) % 60).padStart(2, '0')}`.replace('0:', Math.floor(fuel / 60) + ':')}
                </text>
                <line x1={1676} x2={1784} y1={822 - (60 / 180) * 584} y2={822 - (60 / 180) * 584} stroke="#8A8A90" strokeWidth={2} strokeDasharray="6 5" />
                <text x={1668} y={822 - (60 / 180) * 584 + 9} textAnchor="end" fontFamily={LOOK.font} fontWeight={700} fontSize={24} fill="#8A8A90">
                  1 MIN
                </text>
              </g>
            );
          })()}
        </g>
      ) : null}
      {landed > 0 ? (
        <text x={1580} y={780} textAnchor="end" fontFamily={LOOK.display} fontSize={64} fill={C.white} letterSpacing={4} opacity={landed}>
          CONTACT
        </text>
      ) : null}
    </g>
  );
};

// ---------------------------------------------------------------- mission control
// A console desk + CRT for a seated controller at heroX (facing +x).
export const Console: React.FC<{heroX: number; screen?: React.ReactNode; glow?: number}> = ({heroX, screen, glow = 1}) => {
  const t = useCurrentFrame();
  const dx = heroX + 104; // knees and shins stay in front of the console face
  const deskY = FLOOR - 150;
  return (
    <g>
      {/* chair */}
      <WRect x={heroX - 60} y={FLOOR - 104} w={120} h={14} fill="#55555A" seed={740} />
      <WLine pts={[[heroX - 56, FLOOR - 104], [heroX - 64, FLOOR - 280]]} sw={7} seed={741} />
      <WLine pts={[[heroX, FLOOR - 90], [heroX, FLOOR - 20]]} sw={6} seed={742} />
      <WLine pts={[[heroX - 50, FLOOR - 4], [heroX + 50, FLOOR - 4]]} sw={6} seed={743} />
      {/* console */}
      <WPoly pts={[[dx, deskY], [dx + 520, deskY], [dx + 520, FLOOR], [dx + 30, FLOOR]]} fill="#3A3A40" seed={744} />
      <WRect x={dx - 10} y={deskY - 10} w={540} h={16} fill="#55555A" seed={745} />
      {Array.from({length: 8}, (_, i) => (
        <rect key={i} x={dx + 40 + i * 52} y={deskY + 30} width={30} height={14} rx={2} fill="#26262A" />
      ))}
      {/* CRT */}
      <WPoly pts={[[dx + 100, deskY - 10], [dx + 440, deskY - 10], [dx + 460, deskY - 300], [dx + 80, deskY - 300]]} fill="#2E2E33" seed={746} />
      <rect x={dx + 110} y={deskY - 284} width={320} height={252} rx={10} fill={C.screenBg} />
      <Glow x={dx + 270} y={deskY - 160} r={380} color={C.screen} opacity={0.35 * glow * (0.95 + 0.05 * Math.sin(t * 0.3))} />
      <svg x={dx + 110} y={deskY - 284} width={320} height={252} viewBox="0 0 320 252">
        {screen}
      </svg>
      {/* coffee cup, ashtray */}
      <rect x={dx + 470} y={deskY - 48} width={30} height={38} rx={3} fill="#6A6A70" />
    </g>
  );
};

export const ControlRoom: React.FC<{wall?: boolean; children?: React.ReactNode}> = ({wall = true, children}) => {
  const t = useCurrentFrame();
  return (
    <g>
      <Ground floor={FLOOR} />
      {wall ? (
        <g>
          <WRect x={140} y={100} w={1640} h={330} fill="#1C1C20" seed={750} />
          <rect x={170} y={124} width={1580} height={282} fill="#0E0E10" />
          {/* big wall display: lunar orbit plot */}
          <circle cx={960} cy={265} r={70} fill="none" stroke="#6A6A70" strokeWidth={3} />
          <ellipse cx={960} cy={265} rx={260} ry={110} fill="none" stroke="#4A4A50" strokeWidth={2} strokeDasharray="8 8" strokeDashoffset={-t * 0.5} />
          {[0, 1, 2, 3].map((i) => (
            <rect key={i} x={240 + i * 90} y={170 + (i % 2) * 70} width={70} height={40} fill="#26262A" />
          ))}
          {[0, 1, 2, 3].map((i) => (
            <rect key={'r' + i} x={1420 + (i % 2) * 140} y={170 + Math.floor(i / 2) * 90} width={110} height={60} fill="#26262A" />
          ))}
          <Glow x={960} y={265} r={700} ry={200} color={C.screen} opacity={0.15} />
        </g>
      ) : null}
      {children}
    </g>
  );
};

// ---------------------------------------------------------------- the computer itself
export const AgcUnit: React.FC = () => (
  <g>
    <Backdrop dark />
    <Glow x={1300} y={160} r={1000} color={C.lamp} opacity={0.3} />
    <rect x={0} y={760} width={1920} height={320} fill="#141416" />
    <line x1={0} x2={1920} y1={760} y2={760} stroke="#2C2C30" strokeWidth={2} />
    {/* AGC case */}
    <WPoly pts={[[300, 520], [1220, 520], [1260, 770], [260, 770]]} fill="#8A8A90" seed={760} />
    <WPoly pts={[[300, 520], [1220, 520], [1180, 470], [340, 470]]} fill="#A2A2A8" seed={761} />
    {Array.from({length: 18}, (_, i) => (
      <line key={i} x1={340 + i * 48} x2={330 + i * 50} y1={540} y2={750} stroke="#6A6A70" strokeWidth={4} />
    ))}
    {[0, 1, 2].map((i) => (
      <rect key={'c' + i} x={420 + i * 220} y={700} width={140} height={40} rx={6} fill="#4A4A50" />
    ))}
    {/* label plate */}
    <rect x={560} y={566} width={400} height={86} fill="#C8C8CC" stroke="#5A5A60" strokeWidth={2} />
    <text x={760} y={602} textAnchor="middle" fontFamily={LOOK.font} fontWeight={700} fontSize={24} fill={INK} letterSpacing={2}>
      APOLLO GUIDANCE COMPUTER
    </text>
    <text x={760} y={636} textAnchor="middle" fontFamily={LOOK.font} fontWeight={700} fontSize={20} fill="#3A3A40" letterSpacing={2}>
      MIT INSTRUMENTATION LABORATORY
    </text>
    {/* DSKY beside it */}
    <WRect x={1360} y={470} w={300} h={300} fill="#5A5A60" seed={762} />
    <rect x={1380} y={490} width={120} height={150} fill="#2A2A2E" />
    <rect x={1510} y={490} width={130} height={150} fill="#0C0C0E" />
    {[0, 1, 2].map((r) => (
      <text key={r} x={1575} y={530 + r * 40} textAnchor="middle" fontFamily={LOOK.mono} fontWeight={700} fontSize={26} fill="#C8C8CC">
        {['+0000', '+0000', '+0000'][r]}
      </text>
    ))}
    {Array.from({length: 14}, (_, i) => (
      <rect key={'k' + i} x={1384 + (i % 7) * 38} y={660 + Math.floor(i / 7) * 46} width={30} height={36} rx={3} fill="#3A3A40" />
    ))}
    <text x={1510} y={820} textAnchor="middle" fontFamily={LOOK.font} fontWeight={700} fontSize={26} fill="#8A8A90" letterSpacing={3}>
      DISPLAY + KEYBOARD
    </text>
    {/* spec tag on the desk */}
    <g transform="rotate(-3 760 900)">
      <rect x={480} y={840} width={560} height={130} fill={PAPER} />
      <text x={510} y={890} fontFamily={LOOK.mono} fontWeight={700} fontSize={30} fill={INK}>WEIGHT     70 LB</text>
      <text x={510} y={940} fontFamily={LOOK.mono} fontWeight={700} fontSize={30} fill={INK}>CLOCK      1 MHZ</text>
    </g>
  </g>
);

export const MemoryGrid: React.FC<{fill: number}> = ({fill}) => {
  const cols = 64;
  const rows = 32;
  const n = Math.floor(fill * cols * rows);
  const cell = 18;
  const x0 = 960 - (cols * cell) / 2;
  const y0 = 220;
  return (
    <g>
      <Backdrop dark />
      <Glow x={960} y={500} r={900} ry={400} color={C.screen} opacity={0.12} />
      <text x={960} y={190} textAnchor="middle" fontFamily={LOOK.font} fontWeight={700} fontSize={36} fill="#9A9AA0" letterSpacing={4}>
        WORKING MEMORY: EVERY SQUARE IS ONE WORD
      </text>
      {Array.from({length: cols * rows}, (_, i) => {
        const c = i % cols;
        const r = Math.floor(i / cols);
        return <rect key={i} x={x0 + c * cell} y={y0 + r * cell} width={cell - 4} height={cell - 4} fill={i < n ? '#C8C8CC' : '#1E1E22'} />;
      })}
      <text x={960} y={y0 + rows * cell + 120} textAnchor="middle" fontFamily={LOOK.display} fontSize={110} fill={C.white} letterSpacing={4} opacity={interpolate(fill, [0.6, 1], [0, 1], CL)}>
        2,048 WORDS ≈ 4 KB
      </text>
    </g>
  );
};

// Core rope: a wire threads THROUGH a ring for a 1, goes AROUND it for a 0.
const BITS = [1, 0, 1, 1, 0, 1, 0];
export const CoreRope: React.FC<{draw: number}> = ({draw}) => {
  const ringY = 520;
  const xs = BITS.map((_, i) => 420 + i * 180);
  // wire path: dips through the ring centre (1) or arcs over the top (0)
  let d = `M200,${ringY}`;
  xs.forEach((x, i) => {
    d += BITS[i] ? ` L${x - 60},${ringY} L${x + 60},${ringY}` : ` L${x - 90},${ringY} Q${x},${ringY - 250} ${x + 90},${ringY}`;
  });
  d += ` L1720,${ringY}`;
  const [nx, ny] = [200 + draw * 1520, ringY];
  return (
    <g>
      <Backdrop dark />
      <Glow x={1100} y={300} r={1000} color={C.lamp} opacity={0.28} />
      <text x={960} y={190} textAnchor="middle" fontFamily={LOOK.font} fontWeight={700} fontSize={40} fill="#C8C8CC" letterSpacing={4}>
        CORE ROPE MEMORY
      </text>
      <text x={960} y={240} textAnchor="middle" fontFamily={LOOK.font} fontWeight={700} fontSize={30} fill="#8A8A90" letterSpacing={3}>
        THROUGH THE RING = 1    AROUND IT = 0
      </text>
      {xs.map((x, i) => (
        <g key={i}>
          <ellipse cx={x} cy={ringY} rx={50} ry={74} fill="none" stroke="#6A6A70" strokeWidth={26} />
          <ellipse cx={x} cy={ringY} rx={50} ry={74} fill="none" stroke="#8E8E94" strokeWidth={8} />
        </g>
      ))}
      <path d={d} stroke="#E0D8C8" strokeWidth={6} fill="none" pathLength={1} strokeDasharray={1} strokeDashoffset={1 - draw} strokeLinecap="round" />
      {/* the ring's front half drawn over the wire for the 1s */}
      {xs.map((x, i) =>
        BITS[i] ? <path key={'f' + i} d={`M${x - 50},${ringY} A50,74 0 0 0 ${x + 50},${ringY}`} stroke="#8E8E94" strokeWidth={22} fill="none" /> : null,
      )}
      {xs.map((x, i) => {
        const shown = 200 + draw * 1520 > x + 60;
        return (
          <text key={'b' + i} x={x} y={720} textAnchor="middle" fontFamily={LOOK.mono} fontWeight={700} fontSize={80} fill={C.white} opacity={shown ? 1 : 0.12}>
            {BITS[i]}
          </text>
        );
      })}
      {/* needle at the wire's tip */}
      {draw > 0.01 && draw < 0.99 ? <line x1={nx - 10} y1={ny + 6} x2={nx + 90} y2={ny - 30} stroke="#D8D8DC" strokeWidth={5} strokeLinecap="round" /> : null}
      <text x={960} y={880} textAnchor="middle" fontFamily={LOOK.font} fontWeight={700} fontSize={32} fill="#8A8A90" letterSpacing={3}>
        WOVEN BY HAND. ONE WIRE AT A TIME.
      </text>
    </g>
  );
};

// ---------------------------------------------------------------- Margaret Hamilton's desk
export const Office: React.FC<{lamp?: number}> = ({lamp = 1}) => {
  const t = useCurrentFrame();
  const flick = 0.95 + 0.05 * Math.sin(t * 0.37) * Math.sin(t * 0.11);
  const deskY = FLOOR - 150;
  return (
    <g>
      <Ground floor={FLOOR} />
      <WRect x={240} y={240} w={300} h={260} fill="#0B0B0D" seed={770} />
      <Glow x={390} y={370} r={240} color={C.moon} opacity={0.12} />
      <WLine pts={[[390, 240], [390, 500]]} seed={771} />
      {/* chair */}
      <WRect x={760} y={FLOOR - 104} w={120} h={14} fill={C.propLight} seed={772} />
      <WLine pts={[[764, FLOOR - 104], [756, FLOOR - 290]]} sw={7} seed={773} />
      <WLine pts={[[772, FLOOR - 90], [772, FLOOR]]} sw={5} seed={774} />
      <WLine pts={[[868, FLOOR - 90], [868, FLOOR]]} sw={5} seed={775} />
      {/* desk */}
      <WRect x={890} y={deskY} w={560} h={20} fill={C.propLight} seed={776} />
      <WLine pts={[[910, deskY + 20], [910, FLOOR]]} sw={6} seed={777} />
      <WLine pts={[[1430, deskY + 20], [1430, FLOOR]]} sw={6} seed={778} />
      {/* stacks of program listings */}
      {[
        [1000, 9],
        [1110, 14],
        [1220, 6],
      ].map(([x, n]) =>
        Array.from({length: n}, (_, i) => (
          <rect key={`${x}-${i}`} x={x + (i % 2) * 3} y={deskY - 12 - i * 12} width={96} height={11} fill={i % 2 ? '#B4B4B8' : '#A2A2A6'} stroke="#6A6A70" strokeWidth={1} />
        )),
      )}
      <rect x={940} y={deskY - 5} width={70} height={5} fill="#C8C8CC" />
      {/* lamp */}
      <WRect x={1340} y={deskY - 8} w={60} h={8} fill="#2A2A32" seed={779} />
      <WLine pts={[[1370, deskY - 8], [1330, deskY - 150], [1280, deskY - 200]]} sw={5} seed={780} />
      <WPoly pts={[[1240, deskY - 230], [1300, deskY - 214], [1286, deskY - 176], [1226, deskY - 192]]} fill="#2A2A32" seed={781} />
      {lamp > 0 ? (
        <g>
          <Cone x={1250} y={deskY - 186} topW={60} bottomW={380} h={186} color={C.lamp} opacity={0.3 * lamp * flick} />
          <Glow x={1255} y={deskY - 184} r={260} color={C.lamp} opacity={0.85 * lamp * flick} />
          <Glow x={1180} y={deskY} r={320} ry={44} color={C.lamp} opacity={0.5 * lamp} />
        </g>
      ) : null}
    </g>
  );
};

// ---------------------------------------------------------------- radar switch panel + signal wire
export const SWITCH_XY: Pt = [600, 520];
export const RadarPanel: React.FC<{pulses: number; label?: number}> = ({pulses, label = 0}) => {
  const t = useCurrentFrame();
  const [sx, sy] = SWITCH_XY;
  // the wire leaves the bottom edge of the panel, under the switch
  const wire: Pt[] = [
    [sx, 742],
    [sx, 820],
    [1340, 820],
    [1340, 640],
  ];
  const len = 78 + 740 + 180;
  const posAt = (d: number): Pt => {
    if (d < 78) return [sx, 742 + d];
    if (d < 78 + 740) return [sx + (d - 78), 820];
    return [1340, 820 - (d - 818)];
  };
  return (
    <g>
      <Backdrop dark />
      <Glow x={700} y={300} r={900} color={C.lamp} opacity={0.22} />
      {/* panel */}
      <WRect x={300} y={180} w={620} h={560} fill="#3A3A3F" sw={3} seed={790} />
      {[[330, 210], [870, 210], [330, 710], [870, 710]].map(([x, y]) => (
        <circle key={`${x}${y}`} cx={x} cy={y} r={9} fill="#26262A" />
      ))}
      <text x={610} y={270} textAnchor="middle" fontFamily={LOOK.font} fontWeight={700} fontSize={38} fill="#D8D8DC" letterSpacing={4}>
        RENDEZVOUS RADAR
      </text>
      {['LGC', 'AUTO TRACK', 'SLEW'].map((lab, i) => (
        <text key={lab} x={sx + 104} y={sy - 80 + i * 90} fontFamily={LOOK.font} fontWeight={700} fontSize={30} fill={i === 1 ? C.white : '#8A8A90'} letterSpacing={2}>
          {lab}
        </text>
      ))}
      <circle cx={sx} cy={sy} r={46} fill="#26262A" stroke="#6A6A70" strokeWidth={4} />
      {/* lever, set toward AUTO TRACK (position for an abort) */}
      <line x1={sx} y1={sy} x2={sx + 46} y2={sy - 10} stroke="#D8D8DC" strokeWidth={18} strokeLinecap="round" />
      <circle cx={sx + 50} cy={sy - 11} r={14} fill="#E8E8EC" />
      <text x={610} y={690} textAnchor="middle" fontFamily={LOOK.font} fontWeight={700} fontSize={24} fill="#8A8A90" letterSpacing={3}>
        SET FOR A POSSIBLE ABORT
      </text>
      {/* wire to the computer */}
      <path d={'M' + wire.map((p) => p.join(',')).join(' L')} stroke="#5A5A60" strokeWidth={8} fill="none" strokeLinejoin="round" />
      <WRect x={1160} y={430} w={360} h={210} fill="#8A8A90" seed={791} />
      {Array.from({length: 8}, (_, i) => (
        <line key={i} x1={1190 + i * 42} x2={1190 + i * 42} y1={450} y2={600} stroke="#6A6A70" strokeWidth={4} />
      ))}
      <rect x={1230} y={505} width={220} height={60} fill="#C8C8CC" />
      <text x={1340} y={546} textAnchor="middle" fontFamily={LOOK.font} fontWeight={700} fontSize={30} fill={INK} letterSpacing={3}>
        COMPUTER
      </text>
      {pulses > 0
        ? Array.from({length: 16}, (_, i) => {
            const d = ((t * 14 + i * (len / 16)) % len);
            const [px, py] = posAt(d);
            return (
              <g key={'p' + i} opacity={pulses}>
                <circle cx={px} cy={py} r={10} fill={C.accent} />
              </g>
            );
          })
        : null}
      {pulses > 0 ? <Glow x={1340} y={560} r={260} color={C.accent} opacity={0.25 * pulses * (0.8 + 0.2 * Math.sin(t))} /> : null}
      <g opacity={label}>
        <text x={970} y={880} textAnchor="middle" fontFamily={LOOK.font} fontWeight={700} fontSize={34} fill={C.accent} letterSpacing={3}>
          6,400 MEANINGLESS SIGNALS A SECOND
        </text>
      </g>
    </g>
  );
};

// ---------------------------------------------------------------- the computer's time budget
const SEGS: [string, number][] = [
  ['GUIDANCE', 0.34],
  ['THROTTLE', 0.17],
  ['DISPLAY', 0.14],
  ['OTHER JOBS', 0.2],
];
export const BAR_X = 260;
export const BAR_W = 1300;
export const TimeBar: React.FC<{steal: number; over?: number}> = ({steal, over = 0}) => {
  const t = useCurrentFrame();
  const base = SEGS.reduce((a, s) => a + s[1], 0); // 0.88
  let x = BAR_X;
  const y = 470;
  const h = 130;
  const red = steal * 0.15;
  const used = base + red;
  const overW = Math.max(0, used - 1) * BAR_W;
  return (
    <g>
      <Backdrop dark />
      <Glow x={960} y={500} r={900} ry={400} color={C.screen} opacity={0.12} />
      <text x={BAR_X} y={y - 50} fontFamily={LOOK.font} fontWeight={700} fontSize={38} fill="#C8C8CC" letterSpacing={4}>
        THE COMPUTER'S TIME, EVERY SECOND
      </text>
      <rect x={BAR_X} y={y} width={BAR_W} height={h} fill="#141416" />
      {SEGS.map(([lab, w], i) => {
        const x0 = x;
        x += w * BAR_W;
        return (
          <g key={lab}>
            <rect x={x0 + 2} y={y + 2} width={w * BAR_W - 4} height={h - 4} fill={['#8E8E94', '#7A7A80', '#6A6A70', '#5A5A60'][i]} />
            <text x={x0 + (w * BAR_W) / 2} y={y + h / 2 + 12} textAnchor="middle" fontFamily={LOOK.font} fontWeight={700} fontSize={30} fill="#141416" letterSpacing={2}>
              {lab}
            </text>
          </g>
        );
      })}
      {/* stolen slivers */}
      {Array.from({length: 12}, (_, i) => {
        const k = Math.max(0, Math.min(1, steal * 12 - i));
        if (k <= 0.02) return null;
        const sw = (0.15 / 12) * BAR_W;
        return <rect key={'s' + i} x={x + i * sw + 1} y={y + 2} width={(sw - 2) * k} height={h - 4} fill={C.accent} />;
      })}
      <rect x={BAR_X} y={y} width={BAR_W} height={h} fill="none" stroke={over > 0 ? C.white : '#8A8A90'} strokeWidth={4} />
      <text x={BAR_X + BAR_W} y={y - 50} textAnchor="end" fontFamily={LOOK.font} fontWeight={700} fontSize={30} fill="#8A8A90" letterSpacing={3} opacity={1 - over}>
        100%
      </text>
      {steal > 0.3 ? (
        <g opacity={interpolate(steal, [0.3, 0.6], [0, 1], CL)}>
          <path d={`M${x},${y + h + 20} L${x},${y + h + 40} L${x + red * BAR_W},${y + h + 40} L${x + red * BAR_W},${y + h + 20}`} stroke={C.accent} strokeWidth={4} fill="none" />
          <text x={x + (red * BAR_W) / 2} y={y + h + 100} textAnchor="middle" fontFamily={LOOK.display} fontSize={64} fill={C.accent} letterSpacing={3}>
            {`${Math.round(red * 100)}%`}
          </text>
          <text x={x + (red * BAR_W) / 2} y={y + h + 140} textAnchor="middle" fontFamily={LOOK.font} fontWeight={700} fontSize={28} fill="#C8C8CC" letterSpacing={3}>
            RADAR NOISE
          </text>
        </g>
      ) : null}
      {over > 0 ? (
        <g opacity={over}>
          <rect x={BAR_X + BAR_W} y={y + 2 + Math.sin(t * 0.9) * 2} width={overW + 80 * over} height={h - 4} fill={C.accent} opacity={0.85} />
          <text x={BAR_X + BAR_W + 80} y={y - 40} textAnchor="end" fontFamily={LOOK.display} fontSize={54} fill={C.accent} letterSpacing={3}>
            OVER 100%
          </text>
        </g>
      ) : null}
    </g>
  );
};

// ---------------------------------------------------------------- the job list on restart
export const JOBS: [string, boolean][] = [
  ['STEER TO THE LANDING SITE', true],
  ['CONTROL THE ENGINE', true],
  ['HOLD THE ATTITUDE', true],
  ['UPDATE THE DISPLAY', false],
  ['RADAR BOOKKEEPING', false],
  ['LOW-PRIORITY TASKS', false],
];
export const JobList: React.FC<{blank: number; drop: number; keep: number}> = ({blank, drop, keep}) => (
  <g>
    <Backdrop dark />
    <Glow x={960} y={500} r={900} ry={500} color={C.screen} opacity={0.14} />
    <WRect x={520} y={150} w={880} h={800} fill="#1C1C20" seed={800} />
    <text x={580} y={230} fontFamily={LOOK.font} fontWeight={700} fontSize={40} fill="#C8C8CC" letterSpacing={4}>
      COMPUTER JOB LIST
    </text>
    <text x={1340} y={230} textAnchor="end" fontFamily={LOOK.mono} fontWeight={700} fontSize={30} fill={blank > 0.5 ? C.white : '#4A4A50'}>
      {blank > 0.5 ? 'RESTART' : 'PRIORITY'}
    </text>
    {JOBS.map(([lab, kept], i) => {
      const y = 280 + i * 108;
      const gone = kept ? 0 : drop;
      const o = (1 - blank) * (kept ? 1 : 1 - gone * 0.75);
      return (
        <g key={lab} opacity={o} transform={`translate(${gone * 36} 0)`}>
          <rect x={580} y={y} width={760} height={84} rx={6} fill={kept ? '#2E2E33' : '#26262A'} stroke={kept && keep > 0 ? C.white : '#4A4A50'} strokeWidth={kept ? 2 + keep * 3 : 2} />
          <text x={620} y={y + 54} fontFamily={LOOK.mono} fontWeight={700} fontSize={34} fill={kept ? C.white : '#9A9AA0'}>
            {`${i + 1}  ${lab}`}
          </text>
          {!kept && gone > 0.02 ? <line x1={604} y1={y + 42} x2={604 + 712 * Math.min(1, gone * 1.4)} y2={y + 42} stroke={C.accent} strokeWidth={8} strokeLinecap="round" /> : null}
          {kept && keep > 0 ? (
            <text x={1310} y={y + 54} textAnchor="end" fontFamily={LOOK.font} fontWeight={700} fontSize={28} fill={C.white} letterSpacing={3} opacity={keep}>
              KEEP
            </text>
          ) : null}
        </g>
      );
    })}
  </g>
);

// ---------------------------------------------------------------- the window view, boulders ahead
export const BOULDERS: Pt = [1180, 700];
export const WindowView: React.FC<{scroll: number; target: number}> = ({scroll, target}) => {
  const t = useCurrentFrame();
  const bx = BOULDERS[0] - scroll;
  return (
    <g>
      <rect x={0} y={0} width={1920} height={1080} fill="#050507" />
      <Stars n={40} seed="wv" maxY={340} />
      <MoonGround y={360} scroll={scroll * 0.9} seed="wv" />
      {/* crater with a boulder field around it */}
      <ellipse cx={bx} cy={BOULDERS[1]} rx={230} ry={70} fill="#0E0E10" />
      <path d={`M${bx - 230},${BOULDERS[1]} A230,70 0 0 0 ${bx + 230},${BOULDERS[1]}`} stroke="#4A4A50" strokeWidth={4} fill="none" />
      {Array.from({length: 22}, (_, i) => {
        const a = random(`ba${i}`) * Math.PI * 2;
        const rr = 250 + random(`bd${i}`) * 90;
        const x = bx + Math.cos(a) * rr;
        const y = BOULDERS[1] + Math.sin(a) * rr * 0.32;
        const s = 10 + random(`bs${i}`) * 16;
        return <ellipse key={i} cx={x} cy={y} rx={s * 1.4} ry={s} fill="#6A6A70" stroke="#2A2A2E" strokeWidth={2} />;
      })}
      {/* where the computer is taking them: a dashed aim point */}
      <g opacity={target}>
        <ellipse cx={bx + 30} cy={BOULDERS[1] + 10} rx={44} ry={16} fill="none" stroke={C.white} strokeWidth={3} strokeDasharray="8 6" strokeDashoffset={-t} />
        <line x1={bx + 30} x2={bx + 30} y1={BOULDERS[1] - 30} y2={BOULDERS[1] + 50} stroke={C.white} strokeWidth={2} />
      </g>
      {/* window frame (triangular) */}
      <path d="M0,0 L1920,0 L1920,1080 L0,1080 Z M180,180 L1760,230 L1200,1000 L560,1000 Z" fill="#121214" fillRule="evenodd" />
      <path d="M180,180 L1760,230 L1200,1000 L560,1000 Z" fill="none" stroke="#3A3A40" strokeWidth={10} />
      {/* reticle lines on the glass */}
      <g stroke="#9A9AA0" strokeWidth={2} opacity={0.5}>
        {[0, 1, 2, 3, 4, 5].map((i) => (
          <line key={i} x1={700 + i * 60} x2={720 + i * 60} y1={300 + i * 90} y2={300 + i * 90} />
        ))}
      </g>
    </g>
  );
};

// ---------------------------------------------------------------- the hand controller
export const HandStick: React.FC<{grab: number; mode: number}> = ({grab, mode}) => {
  const hx = interpolate(grab, [0, 1], [380, 900]);
  const hy = interpolate(grab, [0, 1], [760, 520]);
  return (
    <g>
      <Backdrop dark />
      <Glow x={1100} y={200} r={1000} color={C.moon} opacity={0.22} />
      <WRect x={0} y={640} w={1920} h={440} fill="#2E2E33" seed={810} />
      {/* controller */}
      <rect x={890} y={600} width={80} height={60} rx={6} fill="#26262A" />
      <WPoly pts={[[914, 600], [946, 600], [942, 470], [918, 470]]} fill="#6A6A70" seed={811} />
      <rect x={880} y={440} width={100} height={40} rx={14} fill="#8A8A90" />
      {/* mode switch plate */}
      <WRect x={1180} y={420} w={420} h={180} fill="#3A3A3F" seed={812} />
      <text x={1220} y={490} fontFamily={LOOK.font} fontWeight={700} fontSize={36} fill={mode < 0.5 ? C.white : '#6A6A70'} letterSpacing={3}>
        AUTO
      </text>
      <text x={1400} y={490} fontFamily={LOOK.font} fontWeight={700} fontSize={36} fill={mode >= 0.5 ? C.white : '#6A6A70'} letterSpacing={3}>
        MANUAL
      </text>
      <line x1={1380} y1={560} x2={1380 + interpolate(mode, [0, 1], [-60, 60])} y2={530} stroke="#D8D8DC" strokeWidth={14} strokeLinecap="round" />
      <circle cx={1380} cy={560} r={20} fill="#26262A" />
      {/* the arm (suit sleeve) and glove */}
      <path d={`M-40,980 Q${(hx - 40) / 2},${hy + 260} ${hx - 40},${hy + 20}`} stroke="#9A9AA0" strokeWidth={70} fill="none" strokeLinecap="round" />
      <path d={`M-40,980 Q${(hx - 40) / 2},${hy + 260} ${hx - 40},${hy + 20}`} stroke="#B4B4BA" strokeWidth={56} fill="none" strokeLinecap="round" />
      <rect x={hx - 80} y={hy - 18} width={64} height={70} rx={10} fill="#5A5A60" />
      <circle cx={hx + 6} cy={hy + 4} r={44} fill="#D0D0D4" stroke="#5A5A60" strokeWidth={3} />
    </g>
  );
};

// ---------------------------------------------------------------- the medal
export const Medal: React.FC<{x: number; y: number; scale?: number}> = ({x, y, scale = 1}) => (
  <g transform={`translate(${x} ${y}) scale(${scale})`}>
    <path d="M-26,-60 L0,-10 L26,-60" stroke="#4A4A50" strokeWidth={14} fill="none" />
    <Glow x={0} y={10} r={60} color={C.white} opacity={0.5} />
    <polygon points="0,-14 8,4 28,6 12,18 18,38 0,26 -18,38 -12,18 -28,6 -8,4" fill="#ECECEF" stroke="#8A8A90" strokeWidth={2} />
    <circle cx={0} cy={14} r={6} fill="#8A8A90" />
  </g>
);

// ---------------------------------------------------------------- the code, public now
const CODE = [
  '# LUMINARY 099  -  LUNAR LANDING GUIDANCE',
  '',
  '# BURN, BABY, BURN -- MASTER IGNITION ROUTINE',
  '',
  'P63LM      TC     PHASCHNG',
  '           OCT    04024',
  '           TC     BANKCALL',
  '           CADR   R02BOTH',
  '',
  '           CAF    ZERO        # TEMPORARY, I HOPE HOPE HOPE',
  '           TS     DIDFLAG',
  '',
  '# OFF TO SEE THE WIZARD ...',
  '           TC     POSTJUMP',
  '           CADR   BURNBABY',
  '',
  '           TC     ALARM',
  '           OCT    01202',
  '# NOLI SE TANGERE',
];
export const CODE_HOPE_LINE = 9;
export const CodeScreen: React.FC<{scroll: number; children?: React.ReactNode}> = ({scroll, children}) => (
  <g>
    <Backdrop dark />
    <WRect x={150} y={100} w={1620} h={880} fill="#26262A" sw={3} seed={820} />
    <rect x={190} y={140} width={1540} height={800} rx={8} fill="#0B0B0D" />
    <Glow x={960} y={540} r={900} ry={460} color={C.screen} opacity={0.16} />
    <svg x={190} y={140} width={1540} height={800} viewBox="0 0 1540 800">
      <g transform={`translate(0 ${-scroll})`}>
        {CODE.map((l, i) => (
          <text key={i} x={50} y={70 + i * 52} fontFamily={LOOK.mono} fontWeight={700} fontSize={34} fill={l.startsWith('#') ? '#8A8A90' : '#D8D8DC'} style={{whiteSpace: 'pre'}}>
            {l}
          </text>
        ))}
        {children}
      </g>
    </svg>
  </g>
);

export {EASE};

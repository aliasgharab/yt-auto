import React from 'react';
import {interpolate, random, useCurrentFrame} from 'remotion';
import {C, FLOOR, LOOK} from '../../theme';
import {Backdrop, Cone, Glow, Ground, WCircle, WLine, WPoly, WRect} from '../../components/Primitives';
import {Pt} from '../../components/lib';

const CL = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;
const INK = '#2A2A2E';
const PAPER = '#CBCAC5';

// ---------------------------------------------------------------- the moth (top-down, head up)
// Wingspan about 300px at s = 1. flap 0..1 folds the wings, flat < 1 squashes it (crushed).
export const Moth: React.FC<{x: number; y: number; s?: number; rot?: number; flap?: number; flat?: number; opacity?: number}> = ({
  x,
  y,
  s = 1,
  rot = 0,
  flap = 0,
  flat = 1,
  opacity = 1,
}) => {
  const k = 1 - 0.78 * flap;
  const wing = (dir: number) => (
    <g transform={`scale(${dir * k} 1)`}>
      <path d="M6,-2 C30,12 92,34 90,64 C80,86 40,72 8,30 Z" fill="#5E5852" stroke="#2E2A27" strokeWidth={2} />
      <path d="M4,-20 C40,-62 120,-72 152,-42 C162,-12 122,8 72,14 C42,16 14,8 4,0 Z" fill="#78726B" stroke="#2E2A27" strokeWidth={2} />
      <path d="M18,-14 C58,-40 108,-48 140,-36" stroke="#4E4943" strokeWidth={3} fill="none" />
      <path d="M22,-4 C60,-10 100,-6 128,-14" stroke="#4E4943" strokeWidth={2} fill="none" />
      <circle cx={98} cy={-22} r={8} fill="#4A4540" />
    </g>
  );
  return (
    <g transform={`translate(${x} ${y}) rotate(${rot}) scale(${s} ${s * flat})`} opacity={opacity}>
      {wing(-1)}
      {wing(1)}
      <ellipse cx={0} cy={16} rx={11} ry={46} fill="#47423D" stroke="#2A2623" strokeWidth={2} />
      {[0, 1, 2, 3].map((i) => (
        <line key={i} x1={-9} x2={9} y1={14 + i * 10} y2={14 + i * 10} stroke="#33302C" strokeWidth={2} />
      ))}
      <circle cx={0} cy={-32} r={12} fill="#3F3A35" />
      <path d="M-4,-40 C-14,-70 -30,-86 -46,-94" stroke="#3F3A35" strokeWidth={3} fill="none" strokeLinecap="round" />
      <path d="M4,-40 C14,-70 30,-86 46,-94" stroke="#3F3A35" strokeWidth={3} fill="none" strokeLinecap="round" />
    </g>
  );
};

// ---------------------------------------------------------------- one relay, macro (side view)
// Armature pivots at P; closed 0..1. With a moth stuck, it can't close fully.
export const RELAY_P: Pt = [860, 470];
export const CONTACT: Pt = [1260, 548]; // the fixed contact's top
export const BigRelay: React.FC<{closed: number; moth?: boolean; mothLift?: number; labels?: number; spark?: number}> = ({
  closed,
  moth = false,
  mothLift = 0,
  labels = 0,
  spark = 0,
}) => {
  const a = -7 * (1 - closed);
  const rad = (a * Math.PI) / 180;
  const onArm = (lx: number, ly: number): Pt => [RELAY_P[0] + lx * Math.cos(rad) - ly * Math.sin(rad), RELAY_P[1] + lx * Math.sin(rad) + ly * Math.cos(rad)];
  const sp = onArm(300, 0);
  const hook: Pt = [1160, 300];
  const zig = Array.from({length: 11}, (_, i) => {
    const u = i / 10;
    const px = hook[0] + (sp[0] - hook[0]) * u + (i % 2 ? 14 : -14) * (i > 0 && i < 10 ? 1 : 0);
    const py = hook[1] + (sp[1] - hook[1]) * u;
    return `${i ? 'L' : 'M'}${px.toFixed(1)},${py.toFixed(1)}`;
  }).join(' ');
  return (
    <g>
      <Backdrop dark />
      <Glow x={900} y={260} r={900} ry={560} color={C.lamp} opacity={0.22} />
      {/* base plate */}
      <WRect x={480} y={760} w={960} h={44} fill="#3A3A3F" seed={1} />
      {/* frame */}
      <WRect x={560} y={440} w={30} h={320} fill="#4A4A50" seed={2} />
      <WRect x={560} y={440} w={310} h={22} fill="#4A4A50" seed={3} />
      {/* coil */}
      <WRect x={610} y={500} w={190} h={260} fill="#55555B" seed={4} />
      {Array.from({length: 24}, (_, i) => (
        <line key={i} x1={614} x2={796} y1={510 + i * 10.5} y2={510 + i * 10.5} stroke="#3C3C41" strokeWidth={3} />
      ))}
      <WRect x={650} y={488} w={110} h={14} fill="#6A6A70" seed={5} />
      {/* fixed contact on its post */}
      <WRect x={1250} y={556} w={20} h={204} fill="#4A4A50" seed={6} />
      <rect x={1232} y={CONTACT[1]} width={56} height={12} rx={4} fill="#A8A8AE" />
      {/* spring */}
      <path d={zig} stroke="#8A8A90" strokeWidth={4} fill="none" strokeLinejoin="round" />
      <WRect x={1140} y={280} w={40} h={20} fill="#3A3A3F" seed={7} />
      {/* armature + moving contact */}
      <g transform={`rotate(${a} ${RELAY_P[0]} ${RELAY_P[1]})`}>
        <rect x={RELAY_P[0]} y={RELAY_P[1]} width={430} height={18} rx={4} fill="#7A7A80" />
        <rect x={RELAY_P[0] + 392} y={RELAY_P[1] + 18} width={16} height={56} fill="#7A7A80" />
        <rect x={RELAY_P[0] + 374} y={RELAY_P[1] + 66} width={52} height={10} rx={4} fill="#B4B4BA" />
      </g>
      <circle cx={RELAY_P[0]} cy={RELAY_P[1] + 9} r={12} fill="#2A2A2E" stroke="#8A8A90" strokeWidth={3} />
      {/* wires */}
      <path d="M640,760 C640,860 520,860 470,900" stroke="#5A5A60" strokeWidth={6} fill="none" />
      <path d="M1260,760 C1260,860 1380,860 1460,900" stroke="#5A5A60" strokeWidth={6} fill="none" />
      {spark > 0 ? <Glow x={CONTACT[0]} y={CONTACT[1]} r={110} color={C.white} opacity={spark} /> : null}
      {moth ? <Moth x={CONTACT[0] + 4} y={CONTACT[1] - 12 - mothLift} s={0.46} rot={-8} flat={mothLift > 0 ? 1 : 0.3} /> : null}
      {labels > 0 ? (
        <g opacity={labels} fontFamily={LOOK.font} fontWeight={700} fontSize={42} fill={C.white} letterSpacing={3}>
          <path d="M600,630 L470,630 L430,600" stroke={C.white} strokeWidth={2.5} fill="none" />
          <circle cx={600} cy={630} r={5} fill={C.white} />
          <text x={430} y={585} textAnchor="middle">
            COIL
          </text>
          <path d="M1300,560 L1420,640 L1470,640" stroke={C.white} strokeWidth={2.5} fill="none" />
          <circle cx={1300} cy={560} r={5} fill={C.white} />
          <text x={1480} y={654}>SWITCH</text>
        </g>
      ) : null}
    </g>
  );
};

// ---------------------------------------------------------------- a bank of small relays (front view)
export const RelayGrid: React.FC<{x0: number; y0: number; cols: number; rows: number; cell?: number; numbers?: boolean; active?: number; seedKey?: string}> = ({
  x0,
  y0,
  cols,
  rows,
  cell = 60,
  numbers = false,
  active = 1,
  seedKey = 'g',
}) => {
  const t = useCurrentFrame();
  return (
    <g>
      {Array.from({length: cols * rows}, (_, k) => {
        const r = Math.floor(k / cols);
        const c = k % cols;
        const x = x0 + c * cell;
        const y = y0 + r * cell;
        const per = 5 + Math.floor(random(`${seedKey}p${k}`) * 9);
        const on = active > 0 && random(`${seedKey}${k}-${Math.floor((t + k * 3) / per)}`) > 0.55;
        const w = cell * 0.78;
        return (
          <g key={k}>
            <rect x={x - w / 2} y={y - w / 2} width={w} height={w} rx={4} fill="#34343A" stroke="#1E1E21" strokeWidth={1.5} />
            <rect x={x - w * 0.3} y={y - w * 0.18} width={w * 0.34} height={w * 0.5} fill="#4C4C52" />
            <line x1={x + w * 0.1} y1={y - w * (on ? 0.2 : 0.3)} x2={x + w * 0.38} y2={y - w * (on ? 0.2 : 0.3)} stroke="#8A8A90" strokeWidth={Math.max(2, cell * 0.05)} strokeLinecap="round" />
            <circle cx={x + w * 0.24} cy={y + w * 0.22} r={Math.max(2, cell * 0.06)} fill={on ? C.white : '#55555A'} opacity={on ? 0.9 * active : 1} />
            {numbers ? (
              <text x={x - w / 2 + 6} y={y + w / 2 - 6} fontFamily={LOOK.mono} fontSize={cell * 0.2} fill="#8A8A90">
                {k + 1}
              </text>
            ) : null}
          </g>
        );
      })}
    </g>
  );
};

// ---------------------------------------------------------------- the Mark II: a row of relay cabinets
export const CAB_W = 210;
export const CAB_STEP = 230;
export const CAB_H = 560;
export const cabDot = (x0: number, i: number, r: number, c: number): Pt => [x0 + i * CAB_STEP + 30 + c * 30, FLOOR - CAB_H + 98 + r * 34];

export const MarkII: React.FC<{x0?: number; letters?: string; night?: number; redDot?: [number, number, number]; plate?: boolean}> = ({
  x0 = 60,
  letters = 'ABCDEFGH',
  night = 0,
  redDot,
  plate = false,
}) => {
  const t = useCurrentFrame();
  const top = FLOOR - CAB_H;
  return (
    <g>
      {letters.split('').map((L, i) => {
        const x = x0 + i * CAB_STEP;
        return (
          <g key={i}>
            <WRect x={x} y={top} w={CAB_W} h={CAB_H} fill="#3A3A3F" seed={10 + i} />
            <WRect x={x + 12} y={top + 72} w={CAB_W - 24} h={430} fill="#232327" seed={20 + i} />
            <rect x={x + 70} y={top + 14} width={70} height={46} rx={4} fill="#18181B" />
            <text x={x + 105} y={top + 51} textAnchor="middle" fontFamily={LOOK.display} fontSize={38} fill="#D8D8DC">
              {L}
            </text>
            {Array.from({length: 12 * 6}, (_, k) => {
              const r = Math.floor(k / 6);
              const c = k % 6;
              const [cx, cy] = cabDot(x0, i, r, c);
              const per = 4 + Math.floor(random(`m${i}-${k}`) * 10);
              const on = random(`m${i}-${k}-${Math.floor((t + k) / per)}`) > 0.6;
              return (
                <g key={k}>
                  <rect x={cx - 11} y={cy - 9} width={22} height={18} rx={3} fill="#3E3E44" />
                  <circle cx={cx + 5} cy={cy + 3} r={3} fill={on && night < 1 ? C.white : '#56565C'} opacity={on ? 1 - 0.7 * night : 1} />
                </g>
              );
            })}
            <rect x={x + 8} y={FLOOR - 40} width={CAB_W - 16} height={40} fill="#26262A" />
            {i < letters.length - 1 ? (
              <path d={`M${x + 160},${top} C${x + 190},${top - 50} ${x + 250},${top - 50} ${x + 280},${top}`} stroke="#4A4A50" strokeWidth={8} fill="none" />
            ) : null}
          </g>
        );
      })}
      {plate ? (
        <g>
          <rect x={x0 + 2 * CAB_STEP + 24} y={top + 230} width={CAB_W * 2} height={120} rx={8} fill="#8E8A80" stroke="#5A5650" strokeWidth={4} />
        </g>
      ) : null}
      {redDot ? (
        (() => {
          const [cx, cy] = cabDot(x0, redDot[0], redDot[1], redDot[2]);
          return (
            <g>
              <Glow x={cx + 5} y={cy + 3} r={40} color={C.accent} opacity={0.8} />
              <circle cx={cx + 5} cy={cy + 3} r={4} fill={C.accent} />
            </g>
          );
        })()
      ) : null}
    </g>
  );
};

export const CeilingLamps: React.FC<{xs: number[]; on?: number}> = ({xs, on = 1}) => {
  const t = useCurrentFrame();
  return (
    <g>
      {xs.map((x, i) => {
        const fl = 0.95 + 0.05 * Math.sin(t * 0.3 + i * 2) * Math.sin(t * 0.07 + i);
        return (
          <g key={i}>
            <line x1={x} x2={x} y1={0} y2={150} stroke="#2E2E33" strokeWidth={4} />
            <WPoly pts={[[x - 50, 190], [x - 18, 150], [x + 18, 150], [x + 50, 190]]} fill="#2A2A30" seed={40 + i} />
            {on > 0 ? (
              <g>
                <Cone x={x} y={190} topW={100} bottomW={560} h={FLOOR - 190} color={C.lamp} opacity={0.12 * on * fl} />
                <Glow x={x} y={192} r={200} color={C.lamp} opacity={0.75 * on * fl} />
              </g>
            ) : null}
          </g>
        );
      })}
    </g>
  );
};

// ---------------------------------------------------------------- the logbook page (close-up)
export type Entry = {time?: string; text: string};
export const LOG_X = 600; // text column
export const logY = (i: number) => 236 + i * 64; // baseline of entry row i
export const CH = 20.4; // mono advance at 34px
export const LOG_9_9: Entry[] = [
  {time: '0800', text: 'Arctan started'},
  {time: '1000', text: 'stopped - arctan  OK'},
  {time: '1100', text: 'Started Cosine Tape (Sine check)'},
  {time: '1525', text: 'Started Multi Adder Test.'},
  {time: '1545', text: 'Relay #70 Panel F'},
  {text: '      (moth) in relay.'},
  {text: ''},
  {text: ''},
  {text: 'First actual case of bug being found.'},
  {time: '1630', text: 'Arctan started.'},
  {time: '1700', text: 'closed down.'},
];
export const MOTH_ON_PAGE: Pt = [760, 660];

export const LogPage: React.FC<{
  day?: string;
  entries?: Entry[];
  typed?: number[]; // characters shown per entry (default: all)
  moth?: number; // 0..1 the moth settles onto the page
  tape?: number; // 0..1 tape strips
  tilt?: number;
  children?: React.ReactNode;
  glass?: boolean;
}> = ({day = '9/9', entries = LOG_9_9, typed, moth = 0, tape = 0, tilt = -1.5, children, glass = false}) => {
  const t = useCurrentFrame();
  return (
    <g>
      <Backdrop dark />
      <Glow x={1250} y={100} r={1100} color={C.lamp} opacity={0.32} />
      <g transform={`rotate(${tilt} 960 540)`}>
        <rect x={470} y={84} width={1000} height={930} fill="#000" opacity={0.35} transform="translate(10 12)" />
        <WRect x={460} y={80} w={1000} h={930} fill={PAPER} stroke="#8A8A90" sw={2} seed={60} />
        {Array.from({length: 13}, (_, i) => (
          <line key={i} x1={470} x2={1450} y1={logY(i) + 10} y2={logY(i) + 10} stroke="#A9A8A3" strokeWidth={1.5} />
        ))}
        <line x1={580} x2={580} y1={90} y2={1000} stroke="#A9A8A3" strokeWidth={2} />
        <text x={500} y={170} fontFamily={LOOK.mono} fontWeight={700} fontSize={44} fill={INK}>
          {day}
        </text>
        {entries.map((e, i) => {
          const n = typed ? typed[i] ?? 0 : 999;
          const full = (e.time ? e.time + '  ' : '') + e.text;
          const shown = full.slice(0, Math.max(0, n));
          const hasTime = !!e.time;
          return (
            <text key={i} x={hasTime ? 492 : LOG_X} y={logY(i)} fontFamily={LOOK.mono} fontWeight={500} fontStyle="italic" fontSize={34} fill={INK}>
              {hasTime ? (
                <>
                  <tspan>{shown.slice(0, 4)}</tspan>
                  <tspan x={LOG_X}>{shown.slice(6)}</tspan>
                </>
              ) : (
                shown
              )}
            </text>
          );
        })}
        {moth > 0 ? (
          <Moth
            x={MOTH_ON_PAGE[0]}
            y={MOTH_ON_PAGE[1] - (1 - moth) * 260}
            s={0.5 + (1 - moth) * 0.12}
            rot={-18}
            flat={0.92}
            opacity={Math.min(1, moth * 3)}
          />
        ) : null}
        {tape > 0
          ? [
              [MOTH_ON_PAGE[0] - 62, MOTH_ON_PAGE[1] - 30, -28],
              [MOTH_ON_PAGE[0] + 58, MOTH_ON_PAGE[1] + 18, -28],
            ].map(([x, y, r], i) => (
              <rect
                key={i}
                x={x - 80}
                y={y - 18}
                width={160}
                height={36}
                fill="#EDEBE4"
                opacity={0.55 * interpolate(tape, [i * 0.5, i * 0.5 + 0.5], [0, 1], CL)}
                transform={`rotate(${r} ${x} ${y})`}
              />
            ))
          : null}
        {children}
      </g>
      {glass ? (
        <g opacity={0.5}>
          <polygon points={`${200 + ((t * 1.2) % 400)},0 ${420 + ((t * 1.2) % 400)},0 ${0 + ((t * 1.2) % 400)},1080 ${-220 + ((t * 1.2) % 400)},1080`} fill="#FFFFFF" opacity={0.05} />
          <polygon points="1500,0 1560,0 1260,1080 1200,1080" fill="#FFFFFF" opacity={0.06} />
        </g>
      ) : null}
    </g>
  );
};

// ---------------------------------------------------------------- glass museum case with the logbook
export const MuseumCase: React.FC<{light?: number}> = ({light = 1}) => {
  const t = useCurrentFrame();
  return (
    <g>
      <Backdrop dark />
      <Cone x={960} y={0} topW={160} bottomW={1100} h={760} color={C.lamp} opacity={0.18 * light} />
      <Glow x={960} y={560} r={620} ry={260} color={C.lamp} opacity={0.4 * light} />
      {/* pedestal */}
      <WRect x={560} y={700} w={800} h={380} fill="#232327" seed={70} />
      <rect x={560} y={700} width={800} height={6} fill="#3A3A40" />
      {/* open logbook, seen at an angle */}
      <WPoly pts={[[620, 690], [950, 670], [960, 560], [660, 580]]} fill="#B9B8B3" seed={71} />
      <WPoly pts={[[970, 670], [1300, 690], [1260, 580], [960, 560]]} fill="#C4C3BE" seed={72} />
      {Array.from({length: 6}, (_, i) => (
        <g key={i}>
          <line x1={680 + i * 4} x2={930 - i * 2} y1={598 + i * 14} y2={584 + i * 14} stroke="#77767A" strokeWidth={2} opacity={0.8} />
          <line x1={990 + i * 2} x2={1250 - i * 4} y1={584 + i * 14} y2={598 + i * 14} stroke="#77767A" strokeWidth={2} opacity={i === 3 ? 0 : 0.8} />
        </g>
      ))}
      <Moth x={1060} y={636} s={0.14} rot={-14} flat={0.5} />
      {/* glass box */}
      <rect x={540} y={330} width={840} height={370} fill="#FFFFFF" opacity={0.035} />
      <rect x={540} y={330} width={840} height={370} fill="none" stroke="#9A9AA0" strokeWidth={2} opacity={0.6} />
      <polygon points={`${600 + Math.sin(t / 60) * 6},330 ${680 + Math.sin(t / 60) * 6},330 ${600 + Math.sin(t / 60) * 6},700 ${540},700`} fill="#FFFFFF" opacity={0.06} />
      <polygon points="1240,330 1270,330 1200,700 1170,700" fill="#FFFFFF" opacity={0.05} />
      {/* placard on the pedestal */}
      <rect x={1100} y={760} width={220} height={110} fill="#C9C8C4" />
      <text x={1116} y={798} fontFamily={LOOK.font} fontWeight={700} fontSize={22} fill={INK} letterSpacing={1}>
        LOGBOOK, MARK II
      </text>
      <text x={1116} y={830} fontFamily={LOOK.font} fontSize={20} fill={INK}>
        Harvard, 1947
      </text>
    </g>
  );
};

// ---------------------------------------------------------------- desk with chair, logbook and a hanging bulb
export const Desk: React.FC<{dx?: number; bulb?: number; book?: boolean; letter?: boolean}> = ({dx = 0, bulb = 1, book = true, letter = false}) => {
  const t = useCurrentFrame();
  const deskY = FLOOR - 150;
  const fl = 0.94 + 0.06 * Math.sin(t * 0.37) * Math.sin(t * 0.11);
  const X = (v: number) => v + dx;
  return (
    <g>
      <WRect x={X(760)} y={FLOOR - 104} w={120} h={14} fill={C.propLight} seed={80} />
      <WLine pts={[[X(764), FLOOR - 104], [X(756), FLOOR - 290]]} sw={7} seed={81} />
      <WLine pts={[[X(772), FLOOR - 90], [X(772), FLOOR]]} sw={5} seed={82} />
      <WLine pts={[[X(868), FLOOR - 90], [X(868), FLOOR]]} sw={5} seed={83} />
      <WRect x={X(890)} y={deskY} w={520} h={20} fill={C.propLight} seed={84} />
      <WLine pts={[[X(910), deskY + 20], [X(910), FLOOR]]} sw={6} seed={85} />
      <WLine pts={[[X(1390), deskY + 20], [X(1390), FLOOR]]} sw={6} seed={86} />
      {book ? (
        <g>
          <WPoly pts={[[X(960), deskY - 8], [X(1100), deskY - 14], [X(1240), deskY - 8], [X(1240), deskY], [X(960), deskY]]} fill="#C4C3BE" seed={87} />
          <line x1={X(1100)} x2={X(1100)} y1={deskY - 14} y2={deskY} stroke="#77767A" strokeWidth={2} />
          <line x1={X(1010)} x2={X(1070)} y1={deskY - 22} y2={deskY - 60} stroke="#1E1E22" strokeWidth={5} strokeLinecap="round" />
        </g>
      ) : null}
      {letter ? <WPoly pts={[[X(1080), deskY - 3], [X(1250), deskY - 5], [X(1252), deskY], [X(1078), deskY]]} fill="#D0CFCA" seed={88} /> : null}
      {bulb > 0 ? (
        <g>
          <line x1={X(1120)} x2={X(1120)} y1={0} y2={FLOOR - 470} stroke="#2E2E33" strokeWidth={3} />
          <rect x={X(1110)} y={FLOOR - 470} width={20} height={20} fill="#3A3A40" />
          <ellipse cx={X(1120)} cy={FLOOR - 430} rx={20} ry={26} fill="#F4F1EA" opacity={0.9} />
          <Glow x={X(1120)} y={FLOOR - 430} r={420} color={C.lamp} opacity={0.75 * bulb * fl} />
          <Glow x={X(1110)} y={deskY} r={360} ry={50} color={C.lamp} opacity={0.4 * bulb} />
        </g>
      ) : null}
    </g>
  );
};

// ---------------------------------------------------------------- a wall clock
export const WallClock: React.FC<{min: number; sec: number; cx?: number; cy?: number; r?: number}> = ({min, sec, cx = 960, cy = 540, r = 330}) => {
  // min = minutes past noon
  const minA = ((min % 60) / 60) * 360;
  const hourA = ((min / 60) / 12) * 360;
  const secA = (sec / 60) * 360;
  const hand = (a: number, len: number, w: number, col: string) => (
    <line x1={cx} y1={cy} x2={cx + Math.sin((a * Math.PI) / 180) * len} y2={cy - Math.cos((a * Math.PI) / 180) * len} stroke={col} strokeWidth={w} strokeLinecap="round" />
  );
  const k = r / 330;
  return (
    <g>
      <Glow x={cx} y={cy} r={r * 2.1} color={C.lamp} opacity={0.18} />
      <WCircle cx={cx} cy={cy} r={r} fill="#1A1A1D" sw={3} seed={90} />
      <circle cx={cx} cy={cy} r={r - 24 * k} fill="#CFCECA" />
      {Array.from({length: 60}, (_, i) => {
        const a = (i / 60) * Math.PI * 2;
        const big = i % 5 === 0;
        return (
          <line
            key={i}
            x1={cx + Math.cos(a) * (r - (big ? 70 : 50) * k)}
            y1={cy + Math.sin(a) * (r - (big ? 70 : 50) * k)}
            x2={cx + Math.cos(a) * (r - 40 * k)}
            y2={cy + Math.sin(a) * (r - 40 * k)}
            stroke={INK}
            strokeWidth={(big ? 9 : 3) * Math.max(0.5, k)}
          />
        );
      })}
      {k > 0.5
        ? [12, 3, 6, 9].map((n, i) => {
            const a = (i / 4) * Math.PI * 2 - Math.PI / 2;
            return (
              <text key={n} x={cx + Math.cos(a) * (r - 120 * k)} y={cy + Math.sin(a) * (r - 120 * k) + 22 * k} textAnchor="middle" fontFamily={LOOK.font} fontWeight={700} fontSize={64 * k} fill={INK}>
                {n}
              </text>
            );
          })
        : null}
      {hand(hourA, r * 0.5, 18 * k + 2, '#1A1A1C')}
      {hand(minA, r * 0.78, 10 * k + 1.5, '#1A1A1C')}
      {hand(secA, r * 0.82, 3 * k + 1, '#6A6A70')}
      <circle cx={cx} cy={cy} r={14 * k + 3} fill="#1A1A1C" />
    </g>
  );
};

// ---------------------------------------------------------------- generic evidence page (book, clipping)
export const Page: React.FC<{x?: number; y?: number; w?: number; h?: number; tilt?: number; children?: React.ReactNode; tone?: string}> = ({
  x = 520,
  y = 110,
  w = 880,
  h = 860,
  tilt = -1.5,
  children,
  tone = PAPER,
}) => (
  <g>
    <Backdrop dark />
    <Glow x={1300} y={120} r={1000} color={C.lamp} opacity={0.32} />
    <g transform={`rotate(${tilt} 960 540)`}>
      <rect x={x + 10} y={y + 12} width={w} height={h} fill="#000" opacity={0.35} />
      <WRect x={x} y={y} w={w} h={h} fill={tone} stroke="#8A8A90" sw={2} seed={95} />
      {children}
    </g>
  </g>
);

// ---------------------------------------------------------------- a modern monitor
export const Monitor: React.FC<{children: React.ReactNode}> = ({children}) => (
  <g>
    <Backdrop dark />
    <Glow x={960} y={520} r={1000} ry={640} color={C.screen} opacity={0.18} />
    <WRect x={200} y={110} w={1520} h={820} fill="#1A1A1D" sw={3} seed={97} />
    <rect x={240} y={150} width={1440} height={740} fill={C.screenBg} />
    <WRect x={880} y={930} w={160} h={60} fill="#232327" seed={98} />
    <WRect x={760} y={990} w={400} h={24} fill="#2A2A2E" seed={99} />
    {children}
  </g>
);

// ---------------------------------------------------------------- a building facade at dusk
export const Facade: React.FC<{kind: 'harvard' | 'museum'}> = ({kind}) => {
  const t = useCurrentFrame();
  const base = FLOOR;
  const win = (x: number, y: number, k: number, w = 40, h = 64) => {
    const on = random(`fw${kind}${k}`) > 0.35;
    return (
      <g key={k}>
        <rect x={x} y={y} width={w} height={h} fill={on ? '#E9E5DA' : '#151517'} opacity={on ? 0.85 : 1} />
        {on ? <Glow x={x + w / 2} y={y + h / 2} r={80} color={C.lamp} opacity={0.3 + 0.05 * Math.sin(t / 9 + k)} /> : null}
      </g>
    );
  };
  if (kind === 'harvard') {
    return (
      <g>
        <Ground floor={FLOOR} />
        <Glow x={1500} y={240} r={700} color={C.lamp} opacity={0.12} />
        <WRect x={420} y={base - 420} w={1080} h={420} fill="#2B2B30" seed={100} />
        <WPoly pts={[[400, base - 420], [960, base - 560], [1520, base - 420]]} fill="#232327" seed={101} />
        <WRect x={900} y={base - 640} w={120} h={160} fill="#26262B" seed={102} />
        <WPoly pts={[[890, base - 640], [960, base - 720], [1030, base - 640]]} fill="#1E1E22" seed={103} />
        {Array.from({length: 9}, (_, i) => win(470 + i * 115, base - 360, i))}
        {Array.from({length: 9}, (_, i) => (i === 4 ? null : win(470 + i * 115, base - 220, 20 + i)))}
        <WRect x={920} y={base - 150} w={80} h={150} fill="#141416" seed={104} />
        <Glow x={960} y={base - 80} r={150} color={C.lamp} opacity={0.45} />
        {/* brick courses */}
        {Array.from({length: 14}, (_, i) => (
          <line key={i} x1={420} x2={1500} y1={base - 400 + i * 28} y2={base - 400 + i * 28} stroke="#222226" strokeWidth={2} />
        ))}
        {[200, 300, 1660, 1780].map((x, i) => (
          <g key={i}>
            <WLine pts={[[x, base], [x, base - 150]]} sw={8} seed={110 + i} />
            <WCircle cx={x} cy={base - 230} r={95 + (i % 2) * 20} fill="#1A1A1D" seed={115 + i} />
          </g>
        ))}
      </g>
    );
  }
  return (
    <g>
      <Ground floor={FLOOR} />
      <Glow x={300} y={200} r={400} color={C.moon} opacity={0.25} />
      <circle cx={300} cy={200} r={38} fill={C.moon} />
      <WRect x={260} y={base - 380} w={1400} h={380} fill="#2C2C31" seed={120} />
      <WRect x={240} y={base - 410} w={1440} h={40} fill="#36363B" seed={121} />
      {Array.from({length: 22}, (_, i) => (
        <line key={i} x1={300 + i * 62} x2={300 + i * 62} y1={base - 360} y2={base - 290} stroke="#3C3C42" strokeWidth={4} />
      ))}
      {Array.from({length: 10}, (_, i) => win(330 + i * 132, base - 250, 40 + i, 60, 130))}
      <text x={960} y={base - 384} textAnchor="middle" fontFamily={LOOK.font} fontWeight={700} fontSize={26} fill="#B8B8BE" letterSpacing={10}>
        NATIONAL MUSEUM OF AMERICAN HISTORY
      </text>
      {[140, 1780].map((x, i) => (
        <g key={i}>
          <WLine pts={[[x, base], [x, base - 300]]} sw={6} seed={130 + i} />
          <circle cx={x} cy={base - 306} r={10} fill={C.street} />
          <Glow x={x} y={base - 306} r={240} color={C.street} opacity={0.6} />
          <Glow x={x} y={base} r={220} ry={30} color={C.street} opacity={0.35} />
        </g>
      ))}
    </g>
  );
};

import React from 'react';
import {AbsoluteFill, Easing, interpolate, random, Sequence, useCurrentFrame} from 'remotion';
import {applyLook, C, FLOOR, LOOK} from '../../theme';
import {LOOKS} from '../../looks';
import {LookFx} from '../../components/LookFx';
import {Hero} from '../../components/Hero';
import {Cam, Letterbox, Narrator, Stage} from '../../components/Hud';
import {Backdrop, Cone, Glow, Ground, Marker, WRect} from '../../components/Primitives';
import {TitleCard} from '../../components/TitleCard';
import voice from '../../../public/voice/moth.json';
import {MothSound} from './Sound';
import {
  BigRelay,
  cabDot,
  CeilingLamps,
  CH,
  CONTACT,
  Desk,
  Facade,
  LOG_X,
  logY,
  LogPage,
  MarkII,
  Monitor,
  Moth,
  MOTH_ON_PAGE,
  MuseumCase,
  Page,
  RelayGrid,
  WallClock,
} from './props';

// ---------------------------------------------------------------- timing (all from the narration)
export const VOICE_AT = 20;
export const lineAt = (n: number) => voice.lines[n - 1].startFrame + VOICE_AT;
export const lineEnd = (n: number) => voice.lines[n - 1].endFrame + VOICE_AT;
export const TITLE_AT = Math.round(voice.duration * 30) + VOICE_AT + 20;
export const MOTH_DURATION = TITLE_AT + 360;

const EASE = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.inOut(Easing.cubic)} as const;
const CL = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;

// cast: Grace Hopper is the light clay figure with a Navy cap; operators are darker, bare-headed
const OPS = {fill: '#8E8E94', backFill: '#6A6A70'};
const NAVY = {fill: '#7A7A80', backFill: '#5C5C62'};
const INK = '#2A2A2E';

type SP = {s: number; d: number};
const at = (n: number, s: number) => lineAt(n) - s;

// ---------------------------------------------------------------- small shared pieces
const NameTag: React.FC<{x: number; y: number; text: string; from?: number; flip?: boolean}> = ({x, y, text, from = 0, flip = false}) => {
  const f = useCurrentFrame();
  const o = interpolate(f, [from, from + 12], [0, 1], CL);
  const k = flip ? -1 : 1;
  return (
    <g opacity={o}>
      <path d={`M${x},${y} L${x + 70 * k},${y - 70} L${x + 110 * k},${y - 70}`} stroke={C.white} strokeWidth={2.5} fill="none" />
      <circle cx={x} cy={y} r={5} fill={C.white} />
      <text x={x + 120 * k} y={y - 60} textAnchor={flip ? 'end' : 'start'} fontFamily={LOOK.font} fontWeight={700} fontSize={40} fill={C.white} letterSpacing={3}>
        {text}
      </text>
    </g>
  );
};

const Chapter: React.FC<{part: string; title: string; d: number}> = ({part, title, d}) => {
  const f = useCurrentFrame();
  const o = interpolate(f, [0, 8, d - 8, d], [0, 1, 1, 0], CL);
  return (
    <AbsoluteFill style={{background: C.bgDark, alignItems: 'center', justifyContent: 'center'}}>
      <div style={{opacity: o, textAlign: 'center', translate: `0px ${(1 - o) * 6}px`}}>
        <div style={{fontFamily: LOOK.font, fontWeight: 700, fontSize: 40, color: C.accent, letterSpacing: 10}}>{part}</div>
        <div style={{fontFamily: LOOK.display, fontSize: 120, color: C.white, letterSpacing: 4, marginTop: 10}}>{title}</div>
      </div>
    </AbsoluteFill>
  );
};
const chapter = (part: string, title: string): React.FC<SP> => {
  const Card: React.FC<SP> = ({d}) => <Chapter part={part} title={title} d={d} />;
  return Card;
};

// a red strike that never shows a lone cap
const Strike: React.FC<{x1: number; y1: number; x2: number; y2: number; p: number; w?: number}> = ({x1, y1, x2, y2, p, w = 10}) =>
  p > 0.02 ? (
    <line x1={x1} y1={y1} x2={x1 + (x2 - x1) * Math.min(1, p)} y2={y1 + (y2 - y1) * Math.min(1, p)} stroke={C.accent} strokeWidth={w} strokeLinecap="round" style={{filter: `drop-shadow(0 0 6px ${C.accent})`}} />
  ) : null;

// ---------------------------------------------------------------- cold open
const Afternoon: React.FC<SP> = ({d}) => {
  const f = useCurrentFrame();
  // the moth drifts in through the window light toward panel F
  const u = interpolate(f, [30, d - 10], [0, 1], EASE);
  const mx = 320 + u * 980 + Math.sin(f * 0.21) * 30;
  const my = 330 + u * 120 + Math.sin(f * 0.33) * 40;
  return (
    <Cam dur={d} push={[1, 1.08]} focus={[1100, 520]}>
      <Stage>
        <Ground floor={FLOOR} />
        {/* afternoon window */}
        <WRect x={150} y={200} w={300} h={380} fill="#1A1A1C" seed={3} />
        <rect x={170} y={220} width={260} height={340} fill="#D9D6CE" opacity={0.75} />
        <line x1={300} x2={300} y1={220} y2={560} stroke="#1A1A1C" strokeWidth={10} />
        <line x1={170} x2={430} y1={390} y2={390} stroke="#1A1A1C" strokeWidth={10} />
        <Glow x={300} y={390} r={520} color={C.lamp} opacity={0.4} />
        <polygon points="170,220 430,220 1000,860 440,860" fill={C.lamp} opacity={0.06} />
        <MarkII x0={560} letters="CDEFG" />
        {f > 30 ? (
          <g>
            <Glow x={mx} y={my} r={120} color={C.lamp} opacity={0.35} />
            <Moth x={mx} y={my} s={0.36} rot={20 + Math.sin(f * 0.4) * 25} flap={0.45 + 0.45 * Math.sin(f * 1.7)} />
          </g>
        ) : null}
      </Stage>
    </Cam>
  );
};

const MothMacro: React.FC<SP> = ({d}) => {
  const f = useCurrentFrame();
  return (
    <Cam dur={d} push={[1, 1.1]} focus={[960, 560]}>
      <Stage>
        <Backdrop dark />
        <Glow x={960} y={480} r={760} color={C.lamp} opacity={0.3} />
        <Moth x={960} y={560} s={1.7} rot={-6} flap={0.06 + 0.04 * Math.sin(f * 0.25)} />
        <Marker x={960} y={540} rx={330} ry={250} from={40} />
      </Stage>
    </Cam>
  );
};

const Museum: React.FC<SP> = ({d}) => (
  <Cam dur={d} push={[1, 1.12]} focus={[960, 600]}>
    <Stage>
      <MuseumCase />
    </Stage>
  </Cam>
);

// "First actual case of bug being found." on row 8
const BUG_LINE_Y = logY(8);
const wordBox = (start: number, len: number) => ({x: LOG_X + (start + len / 2) * CH, rx: (len * CH) / 2 + 12});

const LogOpen: React.FC<SP> = ({s, d}) => {
  const f = useCurrentFrame();
  const fy = interpolate(f, [0, d], [360, 700], EASE);
  return (
    <Cam dur={d} push={[1.25, 1.35]} focus={[960, fy]}>
      <Stage>
        <LogPage moth={1} tape={1}>
          <Marker x={LOG_X + (37 * CH) / 2} y={BUG_LINE_Y - 12} rx={(37 * CH) / 2 + 16} ry={34} from={at(5, s) + 10} box />
        </LogPage>
      </Stage>
    </Cam>
  );
};

const Nameplate: React.FC<SP> = ({d}) => (
  <Cam dur={d} push={[1, 1.08]} focus={[960, 540]}>
    <Stage>
      <Backdrop dark />
      <Glow x={960} y={300} r={900} color={C.lamp} opacity={0.25} />
      <WRect x={140} y={90} w={1640} h={900} fill="#3A3A3F" seed={5} />
      <RelayGrid x0={220} y0={170} cols={24} rows={2} cell={64} />
      <RelayGrid x0={220} y0={770} cols={24} rows={3} cell={64} seedKey="b" />
      <rect x={470} y={330} width={980} height={340} rx={12} fill="#8E8A80" stroke="#5A5650" strokeWidth={6} />
      <rect x={490} y={350} width={940} height={300} rx={8} fill="none" stroke="#6A665E" strokeWidth={3} />
      {[
        [500, 360],
        [1420, 360],
        [500, 640],
        [1420, 640],
      ].map(([x, y], i) => (
        <circle key={i} cx={x} cy={y} r={9} fill="#5A5650" />
      ))}
      <text x={960} y={480} textAnchor="middle" fontFamily={LOOK.display} fontSize={110} fill="#1E1D1A" letterSpacing={6}>
        HARVARD MARK II
      </text>
      <text x={960} y={580} textAnchor="middle" fontFamily={LOOK.font} fontWeight={700} fontSize={46} fill="#2E2C28" letterSpacing={8}>
        AIKEN RELAY CALCULATOR
      </text>
    </Stage>
  </Cam>
);

const COMMITS = ['a1f3c9e  fix bug in login form', '9be2210  fix null pointer bug', '77d01aa  bug: crash on startup', 'e4c8b12  fix bug #4021', '3d9f0b1  revert "fix bug"', 'c02aa7e  fix the bug the fix caused'];
const Terminal: React.FC<SP> = ({s, d}) => {
  const f = useCurrentFrame();
  const l8 = at(8, s);
  const dim = interpolate(f, [l8 - 6, l8 + 6], [0, 1], CL);
  const q = Math.floor(interpolate(f, [l8, l8 + 18], [0, 30], CL));
  const ans = Math.floor(interpolate(f, [l8 + 18, l8 + 34], [0, 34], CL));
  const strike = interpolate(f, [l8 + 42, l8 + 54], [0, 1], EASE);
  const row = (i: number) => 250 + i * 64;
  return (
    <Cam dur={d} push={[1, 1.06]} focus={[960, 500]}>
      <Stage>
        <Monitor>
          <text x={290} y={row(0) - 20} fontFamily={LOOK.mono} fontSize={34} fill="#8A8A90">
            $ git log --oneline
          </text>
          {COMMITS.map((c, i) => {
            const show = f >= 6 + i * 8;
            if (!show) return null;
            const [hash, ...rest] = c.split('  ');
            const msg = rest.join('  ');
            const parts = msg.split(/(bug)/);
            return (
              <text key={i} x={290} y={row(i + 1)} fontFamily={LOOK.mono} fontSize={38} fill={C.term} opacity={1 - 0.6 * dim}>
                <tspan fill="#6A6A70">{hash}  </tspan>
                {parts.map((p, k) => (
                  <tspan key={k} fill={p === 'bug' ? (dim > 0.5 ? C.white : C.accent) : C.term} fontWeight={p === 'bug' ? 700 : 400}>
                    {p}
                  </tspan>
                ))}
              </text>
            );
          })}
          {f >= l8 ? (
            <g fontFamily={LOOK.mono} fontSize={38}>
              <text x={290} y={row(7) + 20} fill={C.white}>
                {'$ origin of "bug"?'.slice(0, q)}
              </text>
              <text x={290} y={row(8) + 20} fill={C.white}>
                {'> 1947. A moth. Invented the word.'.slice(0, ans)}
              </text>
              <Strike x1={300} y1={row(8) + 8} x2={300 + 34 * 22.8} y2={row(8) + 8} p={strike} w={8} />
            </g>
          ) : null}
        </Monitor>
      </Stage>
    </Cam>
  );
};

// ---------------------------------------------------------------- part I: the machine
const Harvard: React.FC<SP> = ({d}) => (
  <Cam dur={d} push={[1, 1.06]} focus={[960, 600]}>
    <Stage>
      <Facade kind="harvard" />
    </Stage>
  </Cam>
);

const MachineRoom: React.FC<SP> = ({d}) => (
  <Cam dur={d} push={[1, 1.05]} focus={[800, 600]}>
    <Stage>
      <Ground floor={FLOOR} />
      <CeilingLamps xs={[360, 960, 1560]} />
      <MarkII x0={40} />
      <Hero x={600} y={FLOOR} pose="stand" cap {...NAVY} brow={-0.1} mouth={0} seed={3} />
      <Hero x={1340} y={FLOOR} pose="stand" {...OPS} facing={-1} brow={0.1} mouth={0.1} seed={4} />
      <NameTag x={660} y={FLOOR - 350} text="U.S. NAVY" from={30} />
    </Stage>
  </Cam>
);

// top-down plan: the cabinets fill the room; one operator for scale
const FloorPlan: React.FC<SP> = ({d}) => {
  const f = useCurrentFrame();
  const z = interpolate(f, [0, d - 6], [2.0, 1], EASE);
  const cabs: [number, number, number, number][] = [
    ...Array.from({length: 8}, (_, i): [number, number, number, number] => [370 + i * 150, 240, 140, 70]),
    ...Array.from({length: 3}, (_, j): [number, number, number, number] => [370, 330 + j * 170, 70, 160]),
    ...Array.from({length: 3}, (_, j): [number, number, number, number] => [1480, 330 + j * 170, 70, 160]),
    ...Array.from({length: 8}, (_, k): [number, number, number, number] => [520 + (k % 4) * 225, 400 + Math.floor(k / 4) * 110, 205, 90]),
  ];
  return (
    <AbsoluteFill style={{scale: String(z), transformOrigin: '960px 725px'}}>
      <Stage>
        <rect x={0} y={0} width={1920} height={1080} fill={C.bgDark} />
        {Array.from({length: 25}, (_, i) => (
          <line key={i} x1={i * 80} x2={i * 80} y1={0} y2={1080} stroke="#FFFFFF" opacity={0.04} />
        ))}
        {Array.from({length: 14}, (_, i) => (
          <line key={i} x1={0} x2={1920} y1={i * 80} y2={i * 80} stroke="#FFFFFF" opacity={0.04} />
        ))}
        <rect x={340} y={220} width={1240} height={640} fill="#141416" stroke="#8A8A90" strokeWidth={6} />
        {cabs.map(([x, y, w, h], i) => (
          <g key={i}>
            <rect x={x} y={y} width={w} height={h} fill="#3A3A3F" stroke="#6A6A70" strokeWidth={2} />
            {Array.from({length: Math.round((w * h) / 900)}, (_, k) => (
              <circle key={k} cx={x + 10 + ((k * 23) % (w - 16))} cy={y + 10 + Math.floor((k * 23) / (w - 16)) * 16} r={3} fill="#5A5A60" />
            ))}
          </g>
        ))}
        {/* the operator, seen from above */}
        <ellipse cx={960} cy={725} rx={24} ry={11} fill="#85858B" />
        <circle cx={960} cy={725} r={12} fill="#BDBDC2" />
        <text x={995} y={790} fontFamily={LOOK.font} fontWeight={700} fontSize={22} fill={C.white} letterSpacing={2}>
          ONE PERSON
        </text>
      </Stage>
    </AbsoluteFill>
  );
};

const NoScreen: React.FC<SP> = ({s, d}) => {
  const f = useCurrentFrame();
  const l = at(12, s);
  const hits = [l + 6, l + 36, l + 66];
  const p = hits.map((h) => interpolate(f, [h, h + 10], [0, 1], EASE));
  const cur = hits.reduce((a, h, i) => (f >= h ? i : a), -1);
  const X = (cx: number, cy: number, i: number) => {
    const col = i === cur ? C.accent : '#55555A';
    const k = p[i];
    if (k <= 0.02) return null;
    const r = 120;
    return (
      <g stroke={col} strokeWidth={14} strokeLinecap="round" style={i === cur ? {filter: `drop-shadow(0 0 8px ${C.accent})`} : undefined}>
        <line x1={cx - r} y1={cy - r} x2={cx - r + 2 * r * Math.min(1, k * 2)} y2={cy - r + 2 * r * Math.min(1, k * 2)} />
        {k > 0.5 ? <line x1={cx + r} y1={cy - r} x2={cx + r - 2 * r * (k - 0.5) * 2} y2={cy - r + 2 * r * (k - 0.5) * 2} /> : null}
      </g>
    );
  };
  return (
    <Cam dur={d} push={[1, 1.04]} focus={[960, 560]}>
      <Stage>
        <Backdrop dark />
        <Glow x={960} y={300} r={1000} ry={500} color={C.lamp} opacity={0.2} />
        <rect x={0} y={720} width={1920} height={360} fill="#141416" />
        <line x1={0} x2={1920} y1={720} y2={720} stroke={C.floorLine} strokeWidth={2} />
        {/* screen */}
        <WRect x={380} y={430} w={220} h={180} fill="#3A3A3F" seed={7} />
        <rect x={400} y={450} width={180} height={140} fill="#1A1A1D" />
        <WRect x={450} y={610} w={80} h={110} fill="#2E2E33" seed={8} />
        {/* keyboard */}
        <WRect x={780} y={650} w={360} h={70} fill="#3A3A3F" seed={9} />
        {Array.from({length: 24}, (_, k) => (
          <rect key={k} x={796 + (k % 12) * 28} y={662 + Math.floor(k / 12) * 26} width={22} height={20} rx={3} fill="#55555A" />
        ))}
        {/* chip */}
        <WRect x={1360} y={590} w={160} h={130} fill="#2A2A2E" seed={10} />
        {Array.from({length: 6}, (_, k) => (
          <g key={k}>
            <rect x={1372 + k * 26} y={576} width={10} height={14} fill="#8A8A90" />
          </g>
        ))}
        {X(490, 560, 0)}
        {X(960, 640, 1)}
        {X(1440, 640, 2)}
      </Stage>
    </Cam>
  );
};

const RelayWall: React.FC<SP> = ({d}) => {
  const f = useCurrentFrame();
  const z = interpolate(f, [0, d - 10], [3.2, 1], EASE);
  return (
    <AbsoluteFill style={{scale: String(z), transformOrigin: '990px 570px'}}>
      <Stage>
        <Backdrop dark />
        <Glow x={960} y={400} r={1100} color={C.lamp} opacity={0.18} />
        <RelayGrid x0={90} y0={110} cols={32} rows={15} cell={57} />
      </Stage>
    </AbsoluteFill>
  );
};

// a relay clicking: closes for 8 frames every 22
const clickAt = (f: number, every = 22, from = 10) => {
  if (f < from) return 0;
  const g = (f - from) % every;
  return interpolate(g, [0, 3, 10, 14], [0, 1, 1, 0], CL);
};

const RelayExplain: React.FC<SP> = ({s, d}) => {
  const f = useCurrentFrame();
  const c = clickAt(f, 22, 10);
  return (
    <Cam dur={d} push={[1.2, 1.28]} focus={[920, 560]}>
      <Stage>
        <BigRelay closed={c} labels={interpolate(f, [at(14, s) + 30, at(14, s) + 44], [0, 1], CL)} spark={c > 0.9 ? 0.5 : 0} />
      </Stage>
    </Cam>
  );
};

const Shift: React.FC<SP> = ({d}) => {
  const f = useCurrentFrame();
  return (
    <Cam dur={d} push={[1.15, 1.25]} focus={[1000, 560]}>
      <Stage>
        <Ground floor={FLOOR} />
        <MarkII x0={1460} letters="AB" />
        <Desk dx={-160} />
        <WallClock min={(14 * 60 + 10 + f * 0.5) % 720} sec={(f * 2) % 60} cx={560} cy={290} r={90} />
        <Hero x={660} y={FLOOR} pose="sit" {...OPS} brow={0.05} mouth={0} headTilt={8} seed={2} />
        <Hero x={1500} y={FLOOR} pose="stand" {...OPS} facing={-1} brow={0.15} mouth={0} seed={6} />
      </Stage>
    </Cam>
  );
};

const ENTRIES_9_8 = [
  {time: '0900', text: 'TEST - run 14   OK'},
  {time: '1030', text: 'FAILURE - Panel C'},
  {time: '1110', text: 'FIX - relay cleaned'},
  {time: '1200', text: 'TEST - run 15   OK'},
];
const LogShift: React.FC<SP> = ({s, d}) => {
  const f = useCurrentFrame();
  const l = at(16, s);
  const typed = [0, 1, 2, 3].map((i) => Math.floor(interpolate(f, [l - 20 + i * 30, l + 10 + i * 30], [0, 30], CL)));
  return (
    <Cam dur={d} push={[1.3, 1.38]} focus={[760, 250]}>
      <Stage>
        <LogPage day="9/8" entries={ENTRIES_9_8} typed={typed} tilt={1} />
      </Stage>
    </Cam>
  );
};

// September 1947: the 1st was a Monday
const CAL_X = 505;
const CAL_Y = 470;
const calXY = (day: number) => {
  const idx = day;
  return [CAL_X + (idx % 7) * 130 + 65, CAL_Y + Math.floor(idx / 7) * 90 + 45] as const;
};
const Calendar: React.FC<SP> = ({s, d}) => {
  const [mx, my] = calXY(9);
  return (
    <Cam dur={d} push={[1, 1.12]} focus={[mx, my]}>
      <Stage>
        <Page x={440} y={215} w={1040} h={780} tilt={0}>
          <text x={960} y={320} textAnchor="middle" fontFamily={LOOK.display} fontSize={80} fill={INK} letterSpacing={6}>
            SEPTEMBER 1947
          </text>
          {'SMTWTFS'.split('').map((ch, i) => (
            <text key={i} x={CAL_X + i * 130 + 65} y={435} textAnchor="middle" fontFamily={LOOK.font} fontWeight={700} fontSize={30} fill="#5A5A60">
              {ch}
            </text>
          ))}
          {Array.from({length: 30}, (_, i) => {
            const [x, y] = calXY(i + 1);
            return (
              <g key={i}>
                <text x={x} y={y + 16} textAnchor="middle" fontFamily={LOOK.font} fontWeight={700} fontSize={46} fill={INK}>
                  {i + 1}
                </text>
              </g>
            );
          })}
          {Array.from({length: 6}, (_, r) => (
            <line key={r} x1={CAL_X} x2={CAL_X + 910} y1={CAL_Y + r * 90} y2={CAL_Y + r * 90} stroke="#9A9A9E" strokeWidth={1.5} />
          ))}
          <Marker x={mx} y={my} rx={54} ry={42} from={at(17, s) + 20} />
        </Page>
      </Stage>
    </Cam>
  );
};

// ---------------------------------------------------------------- part II: the hunt
const TAPE = ['0.86602540', '0.86602540', '0.90371206', '0.00000000', '1.27000000', '0.00000000', '9.03700000', '0.00000000'];
const ErrorLamp: React.FC<SP> = ({d}) => {
  const f = useCurrentFrame();
  const blink = (f % 20) < 14 ? 1 : 0.2;
  const scroll = f * 0.8;
  return (
    <Cam dur={d} push={[1, 1.08]} focus={[1240, 420]}>
      <Stage>
        <Backdrop dark />
        <WRect x={200} y={130} w={1520} h={820} fill="#3A3A3F" seed={11} />
        <RelayGrid x0={280} y0={210} cols={10} rows={4} cell={70} active={0.6} />
        {/* error lamp */}
        <circle cx={1300} cy={330} r={70} fill="#2A1C1D" stroke="#6A6A70" strokeWidth={6} />
        <circle cx={1300} cy={330} r={54} fill={C.accent} opacity={blink} />
        <Glow x={1300} y={330} r={320} color={C.accent} opacity={0.7 * blink} />
        <text x={1300} y={460} textAnchor="middle" fontFamily={LOOK.font} fontWeight={700} fontSize={44} fill={C.white} letterSpacing={6}>
          ERROR
        </text>
        {/* printer tape */}
        <rect x={360} y={540} width={600} height={360} fill="#1A1A1D" />
        <clipPath id="tapeclip">
          <rect x={420} y={540} width={480} height={360} />
        </clipPath>
        <g clipPath="url(#tapeclip)">
          <rect x={440} y={520} width={440} height={420} fill="#C9C8C4" />
          {TAPE.map((n, i) => (
            <text key={i} x={470} y={600 + i * 56 - scroll} fontFamily={LOOK.mono} fontWeight={700} fontSize={40} fill={INK}>
              {n}
            </text>
          ))}
        </g>
        <rect x={360} y={880} width={600} height={30} fill="#2A2A2E" />
      </Stage>
    </Cam>
  );
};

const Search: React.FC<SP> = ({d}) => {
  const f = useCurrentFrame();
  const pan = interpolate(f, [0, d], [0, 520], EASE);
  const walk = interpolate(f, [0, d], [0, 520], EASE);
  const beam = (x: number, k: number) => {
    const sway = Math.sin(f * 0.05 + k) * 40;
    return <polygon points={`${x + 36},${FLOOR - 232} ${x + 360},${FLOOR - 440 + sway} ${x + 380},${FLOOR - 250 + sway}`} fill={C.lamp} opacity={0.14} />;
  };
  return (
    <AbsoluteFill style={{scale: '1.08', transformOrigin: '960px 640px'}}>
      <Stage>
        <Ground floor={FLOOR} />
        <g transform={`translate(${-pan} 0)`}>
          <MarkII x0={60} night={0.6} />
          {[0, 1].map((i) => {
            const x = 520 + i * 260 + walk;
            return (
              <g key={i}>
                {beam(x, i)}
                <Hero x={x} y={FLOOR} pose="walk" runPhase={f * 0.13 + i * 2.2} {...OPS} brow={0.2} seed={i + 1} />
              </g>
            );
          })}
        </g>
        <rect x={0} y={0} width={1920} height={1080} fill="#000" opacity={0.25} />
      </Stage>
    </AbsoluteFill>
  );
};

const Clock: React.FC<SP> = ({d}) => {
  const f = useCurrentFrame();
  const m = interpolate(f, [0, 60], [15 * 60 + 41 - 720, 15 * 60 + 45 - 720], EASE);
  return (
    <Cam dur={d} push={[1, 1.1]} focus={[960, 540]}>
      <Stage>
        <Backdrop dark />
        {Array.from({length: 16}, (_, i) => (
          <line key={i} x1={i * 128 + 40} x2={i * 128 + 40} y1={0} y2={1080} stroke="#141416" strokeWidth={3} />
        ))}
        <WallClock min={m} sec={f >= 60 ? Math.floor((f - 60) / 30) * 6 : f} />
      </Stage>
    </Cam>
  );
};

// Panel F, relays numbered 1..80. Number 70 is row 6, col 9.
const PF = {x0: 470, y0: 260, cell: 100};
const PanelF: React.FC<SP> = ({s, d}) => {
  const f = useCurrentFrame();
  const r70: [number, number] = [PF.x0 + 9 * PF.cell, PF.y0 + 6 * PF.cell];
  const push = interpolate(f, [at(21, s) + 20, d], [1, 1.35], EASE);
  return (
    <AbsoluteFill style={{scale: String(push), transformOrigin: `${r70[0]}px ${r70[1]}px`}}>
      <Stage>
        <Backdrop dark />
        <Glow x={1100} y={500} r={900} color={C.lamp} opacity={0.25} />
        <WRect x={380} y={110} w={1160} h={940} fill="#3A3A3F" seed={12} />
        <rect x={830} y={140} width={260} height={64} rx={6} fill="#18181B" />
        <text x={960} y={190} textAnchor="middle" fontFamily={LOOK.display} fontSize={48} fill="#E2E2E6" letterSpacing={6}>
          PANEL F
        </text>
        <RelayGrid x0={PF.x0} y0={PF.y0} cols={10} rows={8} cell={PF.cell} numbers seedKey="f" active={f < at(21, s) + 20 ? 1 : 0} />
        <Marker x={r70[0]} y={r70[1]} rx={52} ry={52} from={at(21, s) + 34} />
      </Stage>
    </AbsoluteFill>
  );
};

const Found: React.FC<SP> = ({s, d}) => {
  const f = useCurrentFrame();
  // the armature keeps trying, and can't close: the moth is in the way
  const tries = f < 12 ? 0 : interpolate((f - 12) % 40, [0, 6, 14, 22], [0, 0.55, 0.55, 0], CL);
  return (
    <Cam dur={d} push={[1.3, 1.75]} focus={[CONTACT[0], CONTACT[1] - 20]}>
      <Stage>
        <BigRelay closed={tries} moth />
        <Marker x={CONTACT[0] + 4} y={CONTACT[1] - 14} rx={92} ry={48} from={at(22, s) + 14} />
      </Stage>
    </Cam>
  );
};

const Tweezers: React.FC<SP> = ({d}) => {
  const half = Math.floor(d * 0.45);
  return (
    <>
      <Sequence durationInFrames={half} layout="none">
        <TweezerLift d={half} />
      </Sequence>
      <Sequence from={half} durationInFrames={d - half} layout="none">
        <TapeIn d={d - half} />
      </Sequence>
    </>
  );
};
const TweezerLift: React.FC<{d: number}> = ({d}) => {
  const f = useCurrentFrame();
  const grip = interpolate(f, [0, 16], [0, 1], EASE);
  const lift = interpolate(f, [18, d], [0, 160], EASE);
  const tx = CONTACT[0] + 4;
  const ty = CONTACT[1] - 14 - lift - (1 - grip) * 120;
  const open = 14 * (1 - grip) + 3;
  return (
    <Cam dur={d} push={[1.5, 1.6]} focus={[CONTACT[0], CONTACT[1] - 100]}>
      <Stage>
        <BigRelay closed={0} moth mothLift={lift} />
        <g>
          <polygon points={`${tx - open},${ty} ${tx - open - 4},${ty - 10} ${tx + 360},${ty - 520} ${tx + 380},${ty - 506}`} fill="#A0A0A6" stroke="#55555A" strokeWidth={2} />
          <polygon points={`${tx + open},${ty} ${tx + open + 6},${ty - 6} ${tx + 404},${ty - 486} ${tx + 390},${ty - 500}`} fill="#8A8A90" stroke="#55555A" strokeWidth={2} />
        </g>
      </Stage>
    </Cam>
  );
};
const TapeIn: React.FC<{d: number}> = ({d}) => {
  const f = useCurrentFrame();
  const m = interpolate(f, [0, 26], [0, 1], EASE);
  const tape = interpolate(f, [30, 60], [0, 1], EASE);
  return (
    <Cam dur={d} push={[1.8, 1.9]} focus={[MOTH_ON_PAGE[0], MOTH_ON_PAGE[1]]}>
      <Stage>
        <LogPage typed={[99, 99, 99, 99, 99, 99, 0, 0, 0, 0, 0]} moth={m} tape={tape} />
      </Stage>
    </Cam>
  );
};

const LogWrite: React.FC<SP> = ({s, d}) => {
  const f = useCurrentFrame();
  const n = Math.floor(interpolate(f, [8, 8 + 37 * 1.6], [0, 37], CL));
  const bug = wordBox(21, 3);
  const later = Math.floor(interpolate(f, [80, 130], [0, 20], CL));
  return (
    <Cam dur={d} push={[1.3, 1.42]} focus={[900, 700]}>
      <Stage>
        <LogPage moth={1} tape={1} typed={[99, 99, 99, 99, 99, 99, 0, 0, n, later, Math.max(0, later - 6)]}>
          <Marker x={bug.x} y={BUG_LINE_Y - 12} rx={bug.rx} ry={30} from={at(26, s) + 16} seed={5} />
        </LogPage>
      </Stage>
    </Cam>
  );
};

// ---------------------------------------------------------------- part III: the twist
const Handbook: React.FC<SP> = ({d}) => {
  const lines = ['Q. What is a "bug"?', 'A. The term "bug" is used to', 'a limited extent to designate', 'any fault or trouble in the', 'connections or working of', 'electric apparatus.'];
  return (
    <Cam dur={d} push={[1, 1.12]} focus={[900, 560]}>
      <Stage>
        <Page tone="#C2BFB6">
          <text x={960} y={210} textAnchor="middle" fontFamily={LOOK.display} fontSize={56} fill={INK} letterSpacing={4}>
            NEW CATECHISM OF ELECTRICITY
          </text>
          <text x={960} y={260} textAnchor="middle" fontFamily={LOOK.font} fontWeight={700} fontSize={30} fill="#55555A" letterSpacing={6}>
            NEW YORK, 1896
          </text>
          <line x1={600} x2={1320} y1={290} y2={290} stroke="#77767A" strokeWidth={2} />
          {lines.map((l, i) => (
            <text key={i} x={600} y={380 + i * 70} fontFamily={LOOK.font} fontSize={46} fill={INK}>
              {l}
            </text>
          ))}
          <Marker x={885} y={580} rx={305} ry={176} from={50} box />
        </Page>
      </Stage>
    </Cam>
  );
};

const Edison: React.FC<SP> = ({d}) => (
  <Cam dur={d} push={[1.2, 1.3]} focus={[880, 560]}>
    <Stage>
      <Ground floor={FLOOR} />
      {Array.from({length: 16}, (_, i) => (
        <line key={i} x1={i * 128 + 40} x2={i * 128 + 40} y1={60} y2={FLOOR} stroke="#141416" strokeWidth={3} />
      ))}
      <Desk book={false} letter />
      <Hero x={820} y={FLOOR} pose="sit" fill="#9E9EA4" backFill="#74747A" brow={-0.1} mouth={0.2} headTilt={6} seed={9} />
      <NameTag x={770} y={FLOOR - 380} text="THOMAS EDISON" from={14} flip />
    </Stage>
  </Cam>
);

// timeline 1870 -> 1950
const yx = (y: number) => 260 + (y - 1870) * 17.5;
const Timeline: React.FC<SP> = ({d}) => {
  const f = useCurrentFrame();
  const grow = interpolate(f, [10, d - 30], [0, 1], EASE);
  const events: [number, string, number][] = [
    [1878, 'EDISON: "BUGS"', 0],
    [1896, 'HANDBOOK', 0.26],
    [1947, 'THE MOTH', 1],
  ];
  const barEnd = yx(1878) + (yx(1947) - yx(1878)) * grow;
  return (
    <Stage>
      <Backdrop dark />
      <Glow x={960} y={500} r={1000} ry={500} color={C.lamp} opacity={0.15} />
      <line x1={yx(1870)} x2={yx(1950)} y1={640} y2={640} stroke="#8A8A90" strokeWidth={4} />
      {Array.from({length: 9}, (_, i) => (
        <g key={i}>
          <line x1={yx(1870 + i * 10)} x2={yx(1870 + i * 10)} y1={630} y2={650} stroke="#8A8A90" strokeWidth={3} />
          <text x={yx(1870 + i * 10)} y={700} textAnchor="middle" fontFamily={LOOK.font} fontWeight={700} fontSize={32} fill="#8A8A90">
            {1870 + i * 10}
          </text>
        </g>
      ))}
      <rect x={yx(1878)} y={584} width={Math.max(0, barEnd - yx(1878))} height={30} fill={C.white} opacity={0.85} />
      <text x={(yx(1878) + barEnd) / 2} y={570} textAnchor="middle" fontFamily={LOOK.font} fontWeight={700} fontSize={36} fill={C.white} letterSpacing={3} opacity={interpolate(grow, [0.3, 0.5], [0, 1], CL)}>
        {`"BUG" IN USE: ${Math.round(69 * grow)} YEARS`}
      </text>
      {events.map(([y, label, g], i) => {
        const o = interpolate(grow, [g - 0.06, g], [0, 1], CL);
        const red = y === 1947;
        return (
          <g key={i} opacity={o}>
            <line x1={yx(y)} x2={yx(y)} y1={640} y2={790} stroke={red ? C.accent : C.white} strokeWidth={3} />
            <circle cx={yx(y)} cy={640} r={12} fill={red ? C.accent : C.white} />
            <text x={yx(y)} y={840} textAnchor="middle" fontFamily={LOOK.font} fontWeight={700} fontSize={40} fill={red ? C.accent : C.white} letterSpacing={3}>
              {label}
            </text>
            <text x={yx(y)} y={884} textAnchor="middle" fontFamily={LOOK.font} fontSize={30} fill="#8A8A90">
              {y}
            </text>
          </g>
        );
      })}
      {grow > 0.97 ? <Moth x={yx(1947)} y={530} s={0.3} rot={-8} opacity={interpolate(grow, [0.97, 1], [0, 1], CL)} /> : null}
    </Stage>
  );
};

const LogActual: React.FC<SP> = ({s, d}) => {
  const act = wordBox(6, 6);
  return (
    <Cam dur={d} push={[2.1, 2.3]} focus={[920, BUG_LINE_Y - 12]}>
      <Stage>
        <LogPage moth={1} tape={1}>
          <Marker x={act.x} y={BUG_LINE_Y - 12} rx={act.rx} ry={30} from={at(31, s) + 14} seed={7} />
        </LogPage>
      </Stage>
    </Cam>
  );
};

// ---------------------------------------------------------------- part IV: the storyteller
const Hopper: React.FC<SP> = ({d}) => (
  <Cam dur={d} push={[1.25, 1.35]} focus={[860, 560]}>
    <Stage>
      <Ground floor={FLOOR} />
      <CeilingLamps xs={[700]} />
      <MarkII x0={1000} letters="EFGH" />
      <Hero x={760} y={FLOOR} pose="stand" cap brow={-0.15} mouth={0.3} headTilt={-3} />
      <NameTag x={810} y={FLOOR - 400} text="GRACE HOPPER" from={30} />
    </Stage>
  </Cam>
);

const Stagey: React.FC<{children?: React.ReactNode; slide?: boolean}> = ({children, slide = true}) => {
  const STAGE_Y = 780;
  return (
    <g>
      <Backdrop />
      <rect x={0} y={STAGE_Y} width={1920} height={300} fill="#141416" />
      <line x1={0} x2={1920} y1={STAGE_Y} y2={STAGE_Y} stroke={C.floorLine} strokeWidth={2} />
      {slide ? (
        <g>
          <rect x={1200} y={170} width={560} height={340} fill="#D9D7D0" opacity={0.85} />
          <Glow x={1480} y={340} r={500} color={C.lamp} opacity={0.2} />
          <Moth x={1480} y={340} s={0.7} rot={-10} />
        </g>
      ) : null}
      <Cone x={900} y={0} topW={120} bottomW={700} h={STAGE_Y} color={C.lamp} opacity={0.2} />
      <Glow x={900} y={STAGE_Y} r={420} ry={60} color={C.lamp} opacity={0.5} />
      {children}
    </g>
  );
};
const LECT_X = 860;
const Lecture: React.FC<SP> = ({d}) => {
  const f = useCurrentFrame();
  return (
    <Cam dur={d} push={[1, 1.08]} focus={[960, 600]}>
      <Stage>
        <Stagey>
          <Hero x={LECT_X} y={780} pose="stand" cap brow={-0.2} mouth={0.5} mouthOpen={Math.max(0, Math.sin(f * 0.5)) * 0.4} headTilt={Math.sin(f / 30) * 3} />
          <WRect x={960} y={560} w={150} h={220} fill="#2E2E33" seed={13} />
          <WRect x={940} y={548} w={190} h={22} fill="#3A3A40" seed={14} />
        </Stagey>
        {/* audience, foreground silhouettes */}
        {Array.from({length: 9}, (_, i) => {
          const x = 80 + i * 230 + (i % 2) * 40;
          const y = 1000 + (i % 3) * 26;
          return (
            <g key={i}>
              <ellipse cx={x} cy={y + 130} rx={110} ry={90} fill="#050506" />
              <circle cx={x} cy={y} r={62} fill="#050506" />
            </g>
          );
        })}
      </Stage>
    </Cam>
  );
};

const Myths: React.FC<SP> = ({s, d}) => {
  const f = useCurrentFrame();
  const c1 = interpolate(f, [at(34, s) + 30, at(34, s) + 42], [0, 1], CL);
  const c2 = interpolate(f, [at(34, s) + 70, at(34, s) + 82], [0, 1], CL);
  const k1 = interpolate(f, [at(35, s), at(35, s) + 10], [0, 1], EASE);
  const k2 = interpolate(f, [at(35, s) + 14, at(35, s) + 24], [0, 1], EASE);
  return (
    <Cam dur={d} push={[1, 1.08]} focus={[960, 560]}>
      <Stage>
        <Page x={460} y={150} w={1000} h={760} tilt={1.5} tone="#C6C4BD">
          <text x={960} y={250} textAnchor="middle" fontFamily={LOOK.font} fontWeight={700} fontSize={36} fill="#55555A" letterSpacing={8}>
            WHAT MANY STILL BELIEVE
          </text>
          <line x1={540} x2={1380} y1={280} y2={280} stroke="#77767A" strokeWidth={2} />
          <g opacity={c1}>
            <text x={560} y={430} fontFamily={LOOK.display} fontSize={80} fill={INK} letterSpacing={2}>
              1. SHE FOUND THE MOTH.
            </text>
          </g>
          <g opacity={c2}>
            <text x={560} y={590} fontFamily={LOOK.display} fontSize={80} fill={INK} letterSpacing={2}>
              2. SHE INVENTED
            </text>
            <text x={620} y={690} fontFamily={LOOK.display} fontSize={80} fill={INK} letterSpacing={2}>
              THE WORD "BUG".
            </text>
          </g>
          <Strike x1={545} y1={400} x2={1370} y2={400} p={k1} />
          <Strike x1={545} y1={600} x2={1370} y2={660} p={k2} />
        </Page>
      </Stage>
    </Cam>
  );
};

const HopperClose: React.FC<SP> = ({d}) => {
  const f = useCurrentFrame();
  const smile = interpolate(f, [10, 50], [0.2, 0.7], EASE);
  return (
    <Cam dur={d} push={[2.5, 2.75]} focus={[LECT_X + 14, 470]}>
      <Stage>
        <Stagey slide={false}>
          <Hero x={LECT_X} y={780} pose="stand" cap brow={-0.25} browLift={interpolate(f, [10, 50], [0, 5], EASE)} mouth={smile} headTilt={-4} />
        </Stagey>
      </Stage>
    </Cam>
  );
};

// ---------------------------------------------------------------- what happened next
const Smithsonian: React.FC<SP> = ({d}) => (
  <Cam dur={d} push={[1, 1.08]} focus={[960, 600]}>
    <Stage>
      <Facade kind="museum" />
    </Stage>
  </Cam>
);

const MothNow: React.FC<SP> = ({d}) => {
  const f = useCurrentFrame();
  const yr = Math.round(interpolate(f, [20, d - 40], [1947, 2026], EASE));
  return (
    <>
      <Cam dur={d} push={[1.6, 1.85]} focus={[MOTH_ON_PAGE[0] + 60, MOTH_ON_PAGE[1] - 20]}>
        <Stage>
          <LogPage moth={1} tape={1} glass />
        </Stage>
      </Cam>
      {/* museum label, lying on the case floor beside the page */}
      <Stage>
        <g transform="rotate(-2 1500 920)">
          <rect x={1310} y={846} width={420} height={164} fill="#18181B" stroke="#55555A" strokeWidth={2} />
          <text x={1340} y={892} fontFamily={LOOK.font} fontWeight={700} fontSize={30} fill="#B8B8BE" letterSpacing={3}>
            MOTH, PANEL F, RELAY 70
          </text>
          <text x={1340} y={980} fontFamily={LOOK.display} fontSize={74} fill={C.white} letterSpacing={2}>
            {`1947 – ${yr}`}
          </text>
        </g>
      </Stage>
    </>
  );
};

const Montage: React.FC<SP> = ({d}) => {
  const n = 3;
  const len = Math.ceil(d / n);
  return (
    <>
      <Sequence durationInFrames={len} layout="none">
        <Crash />
      </Sequence>
      <Sequence from={len} durationInFrames={len} layout="none">
        <Glitch />
      </Sequence>
      <Sequence from={2 * len} durationInFrames={d - 2 * len} layout="none">
        <Patch />
      </Sequence>
    </>
  );
};
const Crash: React.FC = () => (
  <Stage>
    <Monitor>
      <rect x={620} y={330} width={680} height={340} rx={10} fill="#1C1C20" stroke="#55555A" strokeWidth={3} />
      <circle cx={720} cy={450} r={48} fill="none" stroke={C.accent} strokeWidth={8} />
      <path d="M700,430 L740,470 M740,430 L700,470" stroke={C.accent} strokeWidth={8} strokeLinecap="round" />
      <text x={800} y={440} fontFamily={LOOK.font} fontWeight={700} fontSize={46} fill={C.white}>
        FATAL ERROR
      </text>
      <text x={800} y={490} fontFamily={LOOK.mono} fontSize={26} fill="#9A9AA0">
        The application crashed.
      </text>
      <rect x={1080} y={580} width={180} height={56} rx={6} fill="#3A3A40" />
      <text x={1170} y={618} textAnchor="middle" fontFamily={LOOK.font} fontWeight={700} fontSize={30} fill={C.white}>
        OK
      </text>
    </Monitor>
  </Stage>
);
const Glitch: React.FC = () => {
  const f = useCurrentFrame();
  return (
    <Stage>
      <Monitor>
        {Array.from({length: 11}, (_, i) => {
          const off = (random(`gl${i}-${Math.floor(f / 3)}`) - 0.5) * 120;
          const txt = Array.from({length: 38}, (_, k) => '#@%&*01<>/=;:'[Math.floor(random(`c${i}${k}${Math.floor(f / 4)}`) * 13)]).join('');
          return (
            <text key={i} x={290 + off} y={220 + i * 62} fontFamily={LOOK.mono} fontSize={38} fill={C.term} opacity={0.5 + 0.5 * random(`o${i}${f}`)}>
              {txt}
            </text>
          );
        })}
        <rect x={240} y={420 + (f % 20) * 8} width={1440} height={30} fill={C.white} opacity={0.08} />
      </Monitor>
    </Stage>
  );
};
const Patch: React.FC = () => {
  const f = useCurrentFrame();
  const rows = ['PATCH NOTES  v2.4.1', '', '- Fixed a bug where saves vanished', '- Fixed a bug in the bug fix', '- Known issue: one more bug'];
  return (
    <Stage>
      <Monitor>
        {rows.map((r, i) => {
          const parts = r.split(/(bug)/);
          return (
            <text key={i} x={300} y={300 + i * 80} fontFamily={i === 0 ? LOOK.display : LOOK.mono} fontSize={i === 0 ? 64 : 42} fill={C.white} opacity={interpolate(f, [i * 5, i * 5 + 6], [0, 1], CL)}>
              {parts.map((p, k) => (
                <tspan key={k} fill={p === 'bug' && i === 2 ? C.accent : i === 0 ? C.white : C.term} fontWeight={p === 'bug' ? 700 : 400}>
                  {p}
                </tspan>
              ))}
            </text>
          );
        })}
      </Monitor>
    </Stage>
  );
};

// The end: the machine room after hours. The camera finds one tiny place.
const FINAL_DOT: [number, number, number] = [3, 7, 4];
const Finale: React.FC<SP> = ({s, d}) => {
  const f = useCurrentFrame();
  const x0 = 120;
  const [dx, dy] = cabDot(x0, FINAL_DOT[0], FINAL_DOT[1], FINAL_DOT[2]);
  const z = interpolate(f, [0, at(41, s) + 90], [1, 3.4], EASE);
  const red = interpolate(f, [at(41, s) + 20, at(41, s) + 40], [0, 1], CL);
  return (
    <AbsoluteFill style={{scale: String(z), transformOrigin: `${dx + 5}px ${dy + 3}px`}}>
      <Stage>
        <Ground floor={FLOOR} />
        <CeilingLamps xs={[300, 1300]} on={0.35} />
        <MarkII x0={x0} letters="CDEFGHI" night={0.85} redDot={red > 0 ? FINAL_DOT : undefined} />
        <rect x={0} y={0} width={1920} height={1080} fill="#000" opacity={0.2} />
        <Marker x={dx + 5} y={dy + 3} rx={16} ry={16} from={at(41, s) + 60} />
      </Stage>
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------- shot list: [film frame, scene]
const L = (n: number) => lineAt(n) - 6;
const SHOTS: [number, React.FC<SP>][] = [
  [0, Afternoon],
  [L(2), MothMacro],
  [L(3), Museum],
  [L(4), LogOpen],
  [L(6), Nameplate],
  [L(7), Terminal],
  [lineEnd(8) + 8, chapter('PART I', 'THE MACHINE')],
  [L(9), Harvard],
  [L(10), MachineRoom],
  [L(11), FloorPlan],
  [L(12), NoScreen],
  [L(13), RelayWall],
  [L(14), RelayExplain],
  [L(15), Shift],
  [L(16), LogShift],
  [L(17), Calendar],
  [lineEnd(17) + 8, chapter('PART II', 'THE HUNT')],
  [L(18), ErrorLamp],
  [L(19), Search],
  [L(20), Clock],
  [L(21), PanelF],
  [L(22), Found],
  [L(24), Tweezers],
  [L(25), LogWrite],
  [lineEnd(26) + 8, chapter('PART III', 'THE TWIST')],
  [L(27), Handbook],
  [L(28), Edison],
  [L(29), Timeline],
  [L(30), LogActual],
  [L(32), Hopper],
  [L(33), Lecture],
  [L(34), Myths],
  [L(36), HopperClose],
  [L(37), Smithsonian],
  [L(38), MothNow],
  [L(39), Montage],
  [L(40), Finale],
];
export const SHOT_COUNT = SHOTS.length;

const NARRATOR: [number, number, string][] = [
  [lineAt(1) + 6, lineEnd(1) + 10, 'Harvard, September 1947'],
  [lineAt(3), lineEnd(3) + 10, 'Smithsonian, Washington D.C.'],
  [lineAt(9), lineEnd(9) + 10, 'Cambridge, Massachusetts, 1947'],
  [lineAt(15), lineEnd(15), 'Shifts around the clock'],
  [lineAt(17), lineEnd(17), 'Tuesday, September 9, 1947'],
  [lineAt(20), lineEnd(20), '3:45 PM'],
  [lineAt(28), lineEnd(28), 'Menlo Park, New Jersey, 1878'],
  [lineAt(32), lineEnd(32), 'Harvard Computation Lab, 1947'],
  [lineAt(33), lineEnd(33), '1950s to 1980s'],
  [lineAt(37), lineEnd(37), 'Washington D.C., 1994'],
];

export const MothFilm: React.FC = () => (
  <AbsoluteFill style={{background: C.bg}}>
    {SHOTS.map(([s, Scene], i) => {
      const e = i + 1 < SHOTS.length ? SHOTS[i + 1][0] : TITLE_AT;
      return (
        <Sequence key={i} from={s} durationInFrames={e - s} name={`${i + 1}. ${Scene.name || 'Chapter'}`}>
          <Scene s={s} d={e - s} />
        </Sequence>
      );
    })}
    <Sequence from={TITLE_AT} durationInFrames={360} name="Title card">
      <TitleCard word="BUGGED." line="Every system has a weak spot." accentLine="Sometimes it has wings." />
    </Sequence>
    <Narrator lines={NARRATOR} />
    <Letterbox />
    <MothSound />
  </AbsoluteFill>
);

export const FilmMoth: React.FC = () => {
  applyLook(LOOKS.documentary);
  return (
    <LookFx look="documentary">
      <MothFilm />
    </LookFx>
  );
};

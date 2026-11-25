import React from 'react';
import {AbsoluteFill, Easing, interpolate, useCurrentFrame} from 'remotion';
import {Sequence} from 'remotion';
import {applyLook, C, FLOOR, LOOK} from '../../theme';
import {LOOKS} from '../../looks';
import {LookFx} from '../../components/LookFx';
import {Hero} from '../../components/Hero';
import {Cam, Flash, Letterbox, Narrator, Stage} from '../../components/Hud';
import {Ground, Glow, Marker, WRect} from '../../components/Primitives';
import {TitleCard} from '../../components/TitleCard';
import voice from '../../../public/voice/taumsauk.json';
import {TaumsaukSound} from './Sound';
import {
  Aerial,
  Battery,
  Billion,
  bracketXY,
  BREACH,
  CHART_HIT,
  ControlRoom,
  CrestView,
  Doc,
  gaugeXY,
  HouseInside,
  IdCard,
  LevelChart,
  LOW_X,
  LOW_Y,
  MissouriMap,
  Mountain,
  NightLog,
  PARK_HOUSE,
  ParkMap,
  PumpDiagram,
  READ_BOX,
  Readout,
  SweptHouse,
  TAUM_XY,
  WallSection,
} from './props';

// ---------------------------------------------------------------- timing (all from the narration)
export const VOICE_AT = 20;
export const lineAt = (n: number) => voice.lines[n - 1].startFrame + VOICE_AT;
export const lineEnd = (n: number) => voice.lines[n - 1].endFrame + VOICE_AT;
export const TITLE_AT = Math.round(voice.duration * 30) + VOICE_AT + 20;
export const TAUMSAUK_DURATION = TITLE_AT + 360;

const EASE = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.inOut(Easing.cubic)} as const;
const CL = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;

type SP = {s: number; d: number};
const at = (n: number, s: number) => lineAt(n) - s;

// ---------------------------------------------------------------- small shared pieces
const NameTag: React.FC<{x: number; y: number; text: string; from?: number; flip?: boolean; size?: number}> = ({x, y, text, from = 0, flip = false, size = 40}) => {
  const f = useCurrentFrame();
  const o = interpolate(f, [from, from + 12], [0, 1], CL);
  const k = flip ? -1 : 1;
  return (
    <g opacity={o}>
      <path d={`M${x},${y} L${x + 60 * k},${y - 60} L${x + 100 * k},${y - 60}`} stroke={C.white} strokeWidth={2.5} fill="none" />
      <circle cx={x} cy={y} r={5} fill={C.white} />
      <text x={x + 110 * k} y={y - 50} textAnchor={flip ? 'end' : 'start'} fontFamily={LOOK.font} fontWeight={700} fontSize={size} fill={C.white} letterSpacing={3}>
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

// ---------------------------------------------------------------- cold open
const MountainOpen: React.FC<SP> = ({d}) => {
  const f = useCurrentFrame();
  return (
    <Cam dur={d} push={[1, 1.08]} focus={[900, 500]}>
      <Stage>
        <Mountain flood={interpolate(f, [d - 80, d], [0, 0.3], EASE)} />
      </Stage>
    </Cam>
  );
};

const BillionShot: React.FC<SP> = ({s, d}) => {
  const f = useCurrentFrame();
  return (
    <Cam dur={d} push={[1, 1.04]}>
      <Stage>
        <Billion u={interpolate(f, [at(2, s) + 40, d - 6], [0, 1], EASE)} />
      </Stage>
    </Cam>
  );
};

const Asleep: React.FC<SP> = ({d}) => (
  <Cam dur={d} push={[1.2, 1.34]} focus={[960, 680]}>
    <Stage>
      <HouseInside />
    </Stage>
  </Cam>
);

const MapShot: React.FC<SP> = ({d}) => {
  const f = useCurrentFrame();
  return (
    <Cam dur={d} push={[1, 1.18]} focus={TAUM_XY}>
      <Stage>
        <MissouriMap pin={interpolate(f, [10, 28], [0, 1], EASE)} labels={interpolate(f, [0, 12], [0, 1], CL)} />
      </Stage>
    </Cam>
  );
};

const AerialShot: React.FC<SP> = ({d}) => {
  const f = useCurrentFrame();
  return (
    <Cam dur={d} push={[1.12, 1.0]} focus={[960, 560]}>
      <Stage>
        <Aerial labels={interpolate(f, [24, 40], [0, 1], CL)} />
      </Stage>
    </Cam>
  );
};

const Control: React.FC<SP> = ({d}) => (
  <Cam dur={d} push={[1.02, 1.1]} focus={[1000, 560]}>
    <Stage>
      <ControlRoom />
    </Stage>
  </Cam>
);

const ReadoutWrong: React.FC<SP> = ({s, d}) => (
  <Cam dur={d} push={[1, 1.06]} focus={[960, 520]}>
    <Stage>
      <Readout value="1593.6" clock={2 * 3600 + 11 * 60 + 4} />
      <Marker {...READ_BOX} from={at(7, s) + 12} box />
    </Stage>
  </Cam>
);

// ---------------------------------------------------------------- part I: the battery
const PumpCycle: React.FC<SP> = ({s, d}) => {
  const f = useCurrentFrame();
  const sw = at(10, s);
  const day = interpolate(f, [sw - 14, sw + 10], [0, 1], EASE);
  const level = f < sw ? interpolate(f, [10, sw - 10], [0.1, 1], EASE) : interpolate(f, [sw + 10, d], [1, 0.25], EASE);
  return (
    <Cam dur={d} push={[1, 1.05]} focus={[900, 600]}>
      <Stage>
        <PumpDiagram day={day} level={level} flowDir={f < sw ? -1 : 1} flow={interpolate(f, [sw - 16, sw - 4, sw + 4, sw + 16], [1, 0, 0, 1], CL)} />
      </Stage>
    </Cam>
  );
};

const BatteryShot: React.FC<SP> = ({d}) => {
  const f = useCurrentFrame();
  return (
    <Cam dur={d} push={[1, 1.06]}>
      <Stage>
        <Battery charge={interpolate(f, [0, d - 10], [0.15, 0.9], EASE)} labels={interpolate(f, [30, 44], [0, 1], CL)} />
      </Stage>
    </Cam>
  );
};

const WallIntro: React.FC<SP> = ({d}) => {
  const f = useCurrentFrame();
  return (
    <Cam dur={d} push={[1, 1.05]} focus={[800, 500]}>
      <Stage>
        <WallSection level={330} labels={interpolate(f, [20, 40], [0, 1], CL)} />
      </Stage>
    </Cam>
  );
};

const WallPipe: React.FC<SP> = ({s, d}) => {
  const f = useCurrentFrame();
  const rise = interpolate(f, [at(14, s), at(14, s) + 55], [345, 300], EASE);
  const off = f >= at(14, s) + 58;
  return (
    <Cam dur={d} push={[1.15, 1.3]} focus={[560, 380]}>
      <Stage>
        <WallSection level={rise} pipe={interpolate(f, [6, 24], [0, 1], CL)} stopY={300} stopO={interpolate(f, [at(14, s) - 10, at(14, s) + 6], [0, 1], CL)} pumps={off ? 'OFF' : 'ON'} />
      </Stage>
    </Cam>
  );
};

// ---------------------------------------------------------------- part II: the gauges
const PipeLoose: React.FC<SP> = ({s, d}) => {
  const f = useCurrentFrame();
  const bow = interpolate(f, [16, 60], [0, 1], EASE);
  const slip = interpolate(f, [at(17, s) + 6, at(17, s) + 40], [0, 0.22], EASE);
  const [bx, by] = bracketXY();
  const [gx, gy] = gaugeXY(0.22, 1);
  return (
    <Cam dur={d} push={[1.7, 1.85]} focus={[600, 520]}>
      <Stage>
        <WallSection level={300} pipe={1} bow={bow} gaugeShift={slip} ghost={interpolate(f, [at(17, s) + 6, at(17, s) + 20], [0, 0.8], CL)} />
        <Marker x={bx - 6} y={by - 4} rx={42} ry={36} from={60} to={at(17, s) - 4} />
        <Marker x={gx} y={gy} rx={46} ry={40} from={at(17, s) + 40} seed={5} />
      </Stage>
    </Cam>
  );
};

const TwoFeet: React.FC<SP> = ({s, d}) => {
  const f = useCurrentFrame();
  const real = 258;
  const read = 300;
  const br = interpolate(f, [at(19, s), at(19, s) + 18], [0, 1], EASE);
  return (
    <Cam dur={d} push={[1.35, 1.5]} focus={[420, 290]}>
      <Stage>
        <WallSection level={real} pipe={1} bow={1} gaugeShift={0.22} readY={read} readO={interpolate(f, [10, 26], [0, 1], CL)} />
        {br > 0.02 ? (
          <g opacity={br}>
            <path d={`M660,${real + 4} L680,${real + 4} L680,${read - 4} L660,${read - 4}`} stroke={C.accent} strokeWidth={5} fill="none" style={{filter: `drop-shadow(0 0 6px ${C.accent})`}} />
            <text x={700} y={236} textAnchor="end" fontFamily={LOOK.display} fontSize={46} fill={C.accent} letterSpacing={2}>
              2 FT
            </text>
          </g>
        ) : null}
      </Stage>
    </Cam>
  );
};

const Probes: React.FC<SP> = ({d}) => {
  const f = useCurrentFrame();
  return (
    <Cam dur={d} push={[1.6, 1.8]} focus={[740, 270]}>
      <Stage>
        <WallSection level={320} probes={interpolate(f, [16, 34], [0, 1], CL)} />
        <text x={560} y={190} textAnchor="middle" fontFamily={LOOK.font} fontWeight={700} fontSize={34} fill={C.white} letterSpacing={3} opacity={interpolate(f, [34, 48], [0, 1], CL)}>
          TWO BACKUP PROBES
        </text>
        <line x1={640} y1={200} x2={722} y2={248} stroke={C.white} strokeWidth={2.5} opacity={interpolate(f, [34, 48], [0, 1], CL)} />
      </Stage>
    </Cam>
  );
};

const Crest: React.FC<SP> = ({s, d}) => {
  const f = useCurrentFrame();
  return (
    <Cam dur={d} push={[1, 1.08]} focus={[LOW_X, LOW_Y]}>
      <Stage>
        <CrestView level={640} lines={interpolate(f, [at(21, s) + 10, at(21, s) + 30], [0, 1], CL)} />
        <Marker x={LOW_X} y={LOW_Y - 8} rx={150} ry={46} from={at(22, s) + 20} />
      </Stage>
    </Cam>
  );
};

const Nobody: React.FC<SP> = ({d}) => {
  const f = useCurrentFrame();
  return (
    <Cam dur={d} push={[1, 1.12]} focus={[800, 600]}>
      <Stage>
        <NightLog rows={Math.min(5, 1 + Math.floor(f / 10))} />
      </Stage>
    </Cam>
  );
};

// ---------------------------------------------------------------- part III: the night
const Chart: React.FC<SP> = ({s, d}) => {
  const f = useCurrentFrame();
  return (
    <Cam dur={d} push={[1, 1.05]} focus={[1100, 400]}>
      <Stage>
        <LevelChart
          gauge={interpolate(f, [6, at(26, s) + 10], [0, 1], EASE)}
          room={interpolate(f, [at(26, s) + 30, at(26, s) + 46], [0, 1], CL)}
          real={interpolate(f, [at(27, s) - 4, at(27, s) + 22], [0, 1], EASE)}
        />
        <Marker x={CHART_HIT[0]} y={CHART_HIT[1]} rx={48} ry={48} from={at(27, s) + 24} />
      </Stage>
    </Cam>
  );
};

const Overtop: React.FC<SP> = ({d}) => {
  const f = useCurrentFrame();
  return (
    <Cam dur={d} push={[1.05, 1.2]} focus={[900, 380]}>
      <Stage>
        <WallSection level={248} overflow={interpolate(f, [20, d - 10], [0, 1], EASE)} />
      </Stage>
    </Cam>
  );
};

const Breach: React.FC<SP> = ({s, d}) => {
  const f = useCurrentFrame();
  const go = at(29, s) + 52;
  const b = interpolate(f, [go, go + 50], [0, 1], {...CL, easing: Easing.in(Easing.quad)});
  const level = interpolate(f, [go, d], [LOW_Y - 2, 640], EASE);
  const br = interpolate(f, [go + 30, go + 46], [0, 1], CL);
  return (
    <>
      <Stage>
        <CrestView level={level} spill={interpolate(f, [0, 12, go, go + 10], [0.4, 1, 1, 0], CL)} breach={b} />
        {br > 0.02 ? (
          <g opacity={br}>
            <path d={`M${BREACH[0]},282 L${BREACH[0]},262 L${BREACH[1]},262 L${BREACH[1]},282`} stroke={C.accent} strokeWidth={5} fill="none" style={{filter: `drop-shadow(0 0 6px ${C.accent})`}} />
            <text x={(BREACH[0] + BREACH[1]) / 2} y={244} textAnchor="middle" fontFamily={LOOK.display} fontSize={56} fill={C.accent} letterSpacing={3}>
              ~700 FEET
            </text>
          </g>
        ) : null}
      </Stage>
      <Flash at={[go + 6]} />
    </>
  );
};

const FloodDown: React.FC<SP> = ({d}) => {
  const f = useCurrentFrame();
  return (
    <Cam dur={d} push={[1, 1.06]} focus={[1100, 600]}>
      <Stage>
        <Mountain flood={interpolate(f, [0, d - 20], [0.25, 1], EASE)} drain={interpolate(f, [d - 50, d], [0, 0.6], CL)} dawn={0.15} houseLit={0} />
      </Stage>
    </Cam>
  );
};

const Park: React.FC<SP> = ({d}) => {
  const f = useCurrentFrame();
  return (
    <Cam dur={d} push={[1, 1.12]} focus={PARK_HOUSE}>
      <Stage>
        <ParkMap flood={interpolate(f, [4, d - 24], [0, 0.78], EASE)} labels={interpolate(f, [0, 14], [0, 1], CL)} />
        <Marker x={PARK_HOUSE[0]} y={PARK_HOUSE[1] - 10} rx={44} ry={40} from={d - 30} />
      </Stage>
    </Cam>
  );
};

const Toops: React.FC<SP> = ({d}) => (
  <Cam dur={d} push={[1, 1.1]} focus={[900, 480]}>
    <Stage>
      <IdCard />
    </Stage>
  </Cam>
);

const Swept: React.FC<SP> = ({d}) => {
  const f = useCurrentFrame();
  const wave = interpolate(f, [10, 70], [0, 1], {...CL, easing: Easing.in(Easing.quad)});
  const lift = interpolate(f, [62, d], [0, 1], EASE);
  return (
    <Cam dur={d} push={[1.05, 1.15]} focus={[1200, 620]}>
      <Stage>
        <SweptHouse wave={wave} lift={lift} />
        <g opacity={interpolate(f, [52, 64], [1, 0], CL)}>
          <NameTag x={1180} y={FLOOR - 400} text="THE TOOPS FAMILY HOME" from={0} size={36} />
        </g>
      </Stage>
    </Cam>
  );
};

// All five survived: slow push-in, then a held silence.
const Survived: React.FC<SP> = ({s, d}) => {
  const f = useCurrentFrame();
  const appear = (i: number) => interpolate(f, [10 + i * 8, 30 + i * 8], [0, 1], EASE);
  const fam: {x: number; sc: number; seed: number}[] = [
    {x: 560, sc: 1, seed: 1},
    {x: 760, sc: 0.95, seed: 2},
    {x: 960, sc: 0.66, seed: 3},
    {x: 1110, sc: 0.58, seed: 4},
    {x: 1250, sc: 0.5, seed: 5},
  ];
  return (
    <AbsoluteFill style={{scale: String(interpolate(f, [0, d], [1, 1.14], EASE)), transformOrigin: '900px 620px'}}>
      <Stage>
        <Ground floor={FLOOR} />
        <Glow x={1700} y={FLOOR - 40} r={1300} ry={520} color={C.lamp} opacity={0.3} />
        {/* wreckage */}
        {[
          [150, -14, 12],
          [1460, -10, -8],
          [1620, -24, 18],
          [300, -6, -4],
        ].map(([x, dy, r], i) => (
          <g key={i} transform={`rotate(${r} ${x} ${FLOOR})`}>
            <WRect x={x} y={FLOOR + dy - 14} w={180} h={14} fill="#4A4A50" seed={200 + i} />
          </g>
        ))}
        {fam.map(({x, sc, seed}, i) => (
          <g key={i} opacity={appear(i)}>
            <Hero x={x} y={FLOOR} scale={sc} brow={0.55} mouth={0.05} headTilt={i < 2 ? 3 : -2} seed={seed} />
            {/* a blanket over the shoulders */}
            <path
              d={`M${x - 46 * sc},${FLOOR - 252 * sc} Q${x},${FLOOR - 272 * sc} ${x + 48 * sc},${FLOOR - 252 * sc} L${x + 62 * sc},${FLOOR - 110 * sc} L${x - 58 * sc},${FLOOR - 110 * sc} Z`}
              fill="#6E6E74"
              stroke="#2A2A2E"
              strokeWidth={2}
            />
          </g>
        ))}
        <NameTag x={520} y={FLOOR - 400} text="JERRY" from={30} flip />
        <NameTag x={800} y={FLOOR - 385} text="LISA" from={38} />
        <NameTag x={1270} y={FLOOR - 200} text="THEIR THREE CHILDREN" from={at(35, s)} size={34} />
      </Stage>
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------- aftermath
const Report: React.FC<SP> = ({s, d}) => {
  const f = useCurrentFrame();
  return (
    <Cam dur={d} push={[1, 1.08]} focus={[900, 480]}>
      <Stage>
        <Doc
          title="FEDERAL INVESTIGATION · 2006"
          lines={['ROCK WALL:  HELD UNTIL OVERTOPPED', 'LEVEL GAUGES:  READ ~2 FT LOW', 'BACKUP PROBES:  SET TOO HIGH', 'CAUSE:  THE READINGS']}
          typed={f * 1.4}
          tilt={-1.2}
        >
          <Marker x={850} y={472} rx={340} ry={88} from={at(36, s) + 40} box />
        </Doc>
      </Stage>
    </Cam>
  );
};

const Paid: React.FC<SP> = ({d}) => {
  const f = useCurrentFrame();
  const n = Math.round(interpolate(f, [6, d - 16], [0, 18], EASE));
  return (
    <Cam dur={d} push={[1, 1.05]} focus={[960, 560]}>
      <Stage>
        <rect x={0} y={0} width={1920} height={1080} fill={C.bgDark} />
        <Glow x={800} y={300} r={900} color={C.lamp} opacity={0.2} />
        <line x1={560} x2={1000} y1={920} y2={920} stroke="#6A6A70" strokeWidth={3} />
        {Array.from({length: n}, (_, i) => (
          <g key={i}>
            <WRect x={640} y={880 - i * 38} w={280} h={34} fill={i % 2 ? '#6A6A70' : '#77777D'} seed={210 + i} />
            <text x={780} y={904 - i * 38} textAnchor="middle" fontFamily={LOOK.mono} fontWeight={700} fontSize={20} fill="#2A2A2E">
              $10M
            </text>
          </g>
        ))}
        <text x={1060} y={560} fontFamily={LOOK.display} fontSize={130} fill={C.white} letterSpacing={2}>
          {`$${(n * 10).toString()},000,000`}
        </text>
        <text x={1066} y={630} fontFamily={LOOK.font} fontWeight={700} fontSize={38} fill="#9A9AA0" letterSpacing={5}>
          PAID BY THE OWNER
        </text>
      </Stage>
    </Cam>
  );
};

const Rebuilt: React.FC<SP> = ({d}) => {
  const f = useCurrentFrame();
  return (
    <Cam dur={d} push={[1.1, 1.22]} focus={[880, 560]}>
      <Stage>
        <WallSection level={330} concrete={interpolate(f, [4, 40], [0, 1], EASE)} labels={interpolate(f, [30, 46], [0, 1], CL)} />
      </Stage>
    </Cam>
  );
};

const Final: React.FC<SP> = ({s, d}) => {
  const f = useCurrentFrame();
  return (
    <Cam dur={d} push={[1.08, 1.3]} focus={[960, 540]}>
      <Stage>
        <Readout value="1593.6" clock={5 * 3600 + 9 * 60 + 40} glitch={interpolate(f, [at(39, s) - 6, at(39, s) + 6, at(39, s) + 22], [0, 0.6, 0], CL)} />
        <Marker {...READ_BOX} from={at(39, s) + 30} box />
      </Stage>
    </Cam>
  );
};

// ---------------------------------------------------------------- shot list: [film frame, scene]
const L = (n: number) => lineAt(n) - 6;
const SHOTS: [number, React.FC<SP>][] = [
  [0, MountainOpen],
  [L(2), BillionShot],
  [L(3), Asleep],
  [L(4), MapShot],
  [L(5), AerialShot],
  [L(6), Control],
  [L(7), ReadoutWrong],
  [lineEnd(7) + 8, chapter('PART I', 'A BATTERY OF WATER')],
  [L(9), PumpCycle],
  [L(11), BatteryShot],
  [L(12), WallIntro],
  [L(13), WallPipe],
  [lineEnd(14) + 8, chapter('PART II', 'THE GAUGES')],
  [L(16), PipeLoose],
  [L(18), TwoFeet],
  [L(20), Probes],
  [L(21), Crest],
  [L(23), Nobody],
  [lineEnd(23) + 8, chapter('PART III', 'THE NIGHT')],
  [L(25), Chart],
  [L(28), Overtop],
  [L(29), Breach],
  [L(30), FloodDown],
  [L(31), Park],
  [L(32), Toops],
  [L(33), Swept],
  [L(34), Survived],
  [L(36), Report],
  [L(37), Paid],
  [lineAt(37) + 80, Rebuilt],
  [L(38), Final],
];
export const SHOT_COUNT = SHOTS.length;

const NARRATOR: [number, number, string][] = [
  [lineAt(1) + 6, lineEnd(1) + 10, 'Proffit Mountain, Missouri'],
  [lineAt(3), lineEnd(3) + 10, 'The valley below'],
  [lineAt(6), lineEnd(6) + 10, 'Pumping every night since 1963'],
  [lineAt(24), lineEnd(24) + 20, 'December 14, 2005'],
  [lineAt(28), lineEnd(28), '5:10 AM'],
  [lineAt(29), lineEnd(29), '5:16 AM'],
  [lineAt(31), lineEnd(31), 'Lesterville, Missouri'],
  [lineAt(34), lineEnd(35), 'Dawn, December 14'],
  [lineAt(36), lineEnd(36), 'Federal investigation, 2006'],
  [lineAt(37) + 80, lineEnd(37), 'The new wall, 2010'],
];

export const TaumsaukFilm: React.FC = () => (
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
      <TitleCard word="OVERFLOW." line="A system only knows what its sensors tell it." accentLine="Check the gauges." />
    </Sequence>
    <Narrator lines={NARRATOR} />
    <Letterbox />
    <TaumsaukSound />
  </AbsoluteFill>
);

export const FilmTaumsauk: React.FC = () => {
  applyLook(LOOKS.documentary);
  return (
    <LookFx look="documentary">
      <TaumsaukFilm />
    </LookFx>
  );
};

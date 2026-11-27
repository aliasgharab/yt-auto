import React from 'react';
import {AbsoluteFill, Easing, interpolate, Sequence, useCurrentFrame} from 'remotion';
import {applyLook, C, FLOOR, LOOK} from '../../theme';
import {LOOKS} from '../../looks';
import {LookFx} from '../../components/LookFx';
import {Hero} from '../../components/Hero';
import {Cam, Letterbox, Narrator, Stage} from '../../components/Hud';
import {Backdrop, Glow, Ground, Marker} from '../../components/Primitives';
import {TitleCard} from '../../components/TitleCard';
import voice from '../../../public/voice/apollo1202.json';
import {Apollo1202Sound} from './Sound';
import {
  AgcUnit,
  ALARMS,
  BOULDERS,
  Cabin,
  CODE_HOPE_LINE,
  CodeScreen,
  Console,
  ControlRoom,
  CoreRope,
  DescentChart,
  Doc,
  Dsky,
  DSKY_R1,
  Earth,
  Hair,
  HandStick,
  Helmet,
  JobList,
  Lander,
  Medal,
  MemoryGrid,
  MoonGround,
  MoonMap,
  Office,
  RadarPanel,
  SITE,
  Stars,
  SWITCH_XY,
  TimeBar,
  TvGrid,
  WindowView,
} from './props';

// ---------------------------------------------------------------- timing (all from the narration)
export const VOICE_AT = 20;
export const lineAt = (n: number) => voice.lines[n - 1].startFrame + VOICE_AT;
export const lineEnd = (n: number) => voice.lines[n - 1].endFrame + VOICE_AT;
export const TITLE_AT = Math.round(voice.duration * 30) + VOICE_AT + 20;
export const APOLLO1202_DURATION = TITLE_AT + 360;

const EASE = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.inOut(Easing.cubic)} as const;
const CL = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;

type SP = {s: number; d: number};
const at = (n: number, s: number) => lineAt(n) - s;

// cast: astronauts wear helmets in cold moonlight; Houston wears headsets in screen light
const HOUSTON = {fill: '#B0B0B6', backFill: '#7E7E84'};
const GARMAN = {fill: '#9C9CA2', backFill: '#717177'};

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

const chapter = (part: string, title: string): React.FC<SP> => {
  const Chapter: React.FC<SP> = ({d}) => {
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
  return Chapter;
};

// ---------------------------------------------------------------- cold open
const EagleDescent: React.FC<SP> = ({d}) => {
  const f = useCurrentFrame();
  return (
    <Cam dur={d} push={[1, 1.08]} focus={[880, 420]}>
      <Stage>
        <Backdrop dark />
        <Stars n={160} seed="open" maxY={760} />
        <Earth x={1560} y={230} r={52} />
        <Glow x={1400} y={760} r={900} ry={160} color={C.moon} opacity={0.18} />
        <MoonGround y={770} scroll={f * 3} seed="open" />
        <Lander x={880} y={interpolate(f, [0, d], [600, 640])} scale={0.95} flame={1} tilt={-6} />
      </Stage>
    </Cam>
  );
};

const MoonShot: React.FC<SP> = ({s, d}) => {
  const f = useCurrentFrame();
  const sx = 960 + SITE[0] * 420;
  const sy = 570 + SITE[1] * 420;
  return (
    <Cam dur={d} push={[1, 1.3]} focus={[sx, sy]}>
      <Stage>
        <MoonMap pin={interpolate(f, [at(2, s) + 70, at(2, s) + 84], [0, 1], EASE)} label={interpolate(f, [at(2, s) + 96, at(2, s) + 110], [0, 1], CL)} />
      </Stage>
    </Cam>
  );
};

const AX = 700; // Armstrong
const BX = 1220; // Aldrin
const Crew: React.FC<SP> = ({d}) => (
  <Cam dur={d} push={[1.04, 1.12]} focus={[960, 560]}>
    <Stage>
      <Cabin />
      <Hero x={AX} y={FLOOR} pose="stand" brow={-0.1} mouth={0} seed={1} />
      <Helmet x={AX} y={FLOOR} />
      <Hero x={BX} y={FLOOR} pose="stand" facing={-1} brow={0} mouth={0.1} seed={2} />
      <Helmet x={BX} y={FLOOR} facing={-1} />
      <NameTag x={AX - 60} y={FLOOR - 400} text="NEIL ARMSTRONG" from={30} flip size={36} />
      <NameTag x={BX + 60} y={FLOOR - 400} text="BUZZ ALDRIN" from={62} size={36} />
    </Stage>
  </Cam>
);

const DskyAlarm: React.FC<SP> = ({s, d}) => {
  const f = useCurrentFrame();
  const lamp = interpolate(f, [at(4, s) + 22, at(4, s) + 30], [0, 1], CL);
  const code = interpolate(f, [at(4, s) + 66, at(4, s) + 72], [0, 1], CL);
  return (
    <Cam dur={d} push={[1, 1.14]} focus={[1100, 470]}>
      <Stage>
        <Dsky lamp={lamp} code={code} />
        <Marker x={DSKY_R1[0]} y={DSKY_R1[1] - 25} rx={178} ry={52} from={at(5, s) + 2} box />
      </Stage>
    </Cam>
  );
};

const Transcript: React.FC<SP> = ({d}) => (
  <Cam dur={d} push={[1, 1.08]} focus={[860, 560]}>
    <Stage>
      <Doc
        title="AIR-TO-GROUND TRANSCRIPT"
        lines={['102:38:26  EAGLE', '  PROGRAM ALARM.', '102:38:30  HOUSTON', "  IT'S LOOKING GOOD TO US.", '102:38:32  EAGLE', "  IT'S A 1202."]}
        reveal={[30, 48, 66, 72, 88, 94]}
        size={38}
        tilt={-1.5}
      >
        <Marker x={850} y={617} rx={280} ry={72} from={112} box />
      </Doc>
    </Stage>
  </Cam>
);

const CockpitClose: React.FC<SP> = ({d}) => {
  const f = useCurrentFrame();
  const look = interpolate(f, [10, 40], [0, 1], EASE);
  return (
    <Cam dur={d} push={[1.48, 1.58]} focus={[960, 540]}>
      <Stage>
        <Cabin alarm={1} lamp={1} />
        <Hero x={AX} y={FLOOR} pose="stand" brow={0.4 + 0.3 * look} browLift={4 * look} mouth={-0.3} headTilt={6 * look} seed={1} />
        <Helmet x={AX} y={FLOOR} />
        <Hero x={BX} y={FLOOR} pose="stand" facing={-1} brow={0.6} browLift={6 * look} mouth={-0.4} headTilt={4 * look} seed={2} />
        <Helmet x={BX} y={FLOOR} facing={-1} />
      </Stage>
    </Cam>
  );
};

const Viewers: React.FC<SP> = ({d}) => {
  const f = useCurrentFrame();
  return (
    <Cam dur={d} push={[1, 1.05]}>
      <Stage>
        <TvGrid fill={interpolate(f, [8, 70], [0, 1], EASE)} />
      </Stage>
    </Cam>
  );
};

// the descent chart, drawn small on a console CRT
const ScreenChart: React.FC<{progress: number; alarms: number; ask?: number}> = ({progress, alarms, ask = 0}) => {
  const f = useCurrentFrame();
  const abort = Math.floor(f / 12) % 2 === 0;
  return (
    <>
      <svg x={0} y={0} width={320} height={252} viewBox="200 140 1560 800" preserveAspectRatio="none">
        <DescentChart progress={progress} alarmsShown={alarms} small />
      </svg>
      {ask > 0 ? (
        <g opacity={ask}>
          <rect x={60} y={86} width={200} height={80} fill={C.screenBg} opacity={0.85} />
          <text x={160} y={142} textAnchor="middle" fontFamily={LOOK.mono} fontWeight={700} fontSize={44} fill={abort ? C.accent : C.white}>
            {abort ? 'ABORT?' : 'LAND?'}
          </text>
        </g>
      ) : null}
    </>
  );
};

const BX_H = 760; // Bales at his console
const Bales: React.FC<SP> = ({s, d}) => {
  const f = useCurrentFrame();
  return (
    <Cam dur={d} push={[1.12, 1.24]} focus={[960, 600]}>
      <Stage>
        <ControlRoom>
          <Console heroX={BX_H} screen={<ScreenChart progress={0.43} alarms={1} ask={interpolate(f, [at(9, s) + 70, at(9, s) + 80], [0, 1], CL)} />} />
          <Hero x={BX_H} y={FLOOR} pose="sit" headphones {...HOUSTON} brow={0.5} browLift={2} mouth={-0.25} />
          <NameTag x={BX_H - 50} y={FLOOR - 330} text="STEVE BALES, 26" from={at(9, s) + 30} flip size={38} />
        </ControlRoom>
      </Stage>
    </Cam>
  );
};

// ---------------------------------------------------------------- part I: the computer
const Agc: React.FC<SP> = ({d}) => (
  <Cam dur={d} push={[1, 1.1]} focus={[860, 600]}>
    <Stage>
      <AgcUnit />
    </Stage>
  </Cam>
);

const Memory: React.FC<SP> = ({d}) => {
  const f = useCurrentFrame();
  return (
    <Cam dur={d} push={[1, 1.04]}>
      <Stage>
        <MemoryGrid fill={interpolate(f, [4, 56], [0, 1], EASE)} />
      </Stage>
    </Cam>
  );
};

const Rope: React.FC<SP> = ({d}) => {
  const f = useCurrentFrame();
  return (
    <Cam dur={d} push={[1, 1.06]} focus={[960, 520]}>
      <Stage>
        <CoreRope draw={interpolate(f, [4, d - 8], [0, 1], EASE)} />
      </Stage>
    </Cam>
  );
};

const Cutaway: React.FC<SP> = ({d}) => {
  const f = useCurrentFrame();
  // computer box in the cutaway, in film coords (lander at 960,900, scale 1.5)
  return (
    <Cam dur={d} push={[1, 1.06]} focus={[930, 420]}>
      <Stage>
        <Backdrop dark />
        <Stars n={140} seed="cut" maxY={980} />
        <Earth x={300} y={220} r={46} />
        <MoonGround y={985} scroll={f * 2} seed="cut" rocks={false} />
        <Lander x={960} y={910} scale={1.5} flame={0.8} cutaway={interpolate(f, [8, 22], [0, 1], CL)} windowLight={0.2} />
        <Marker x={928} y={442} rx={128} ry={104} from={30} box />
      </Stage>
    </Cam>
  );
};

const HX = 820; // Hamilton at her desk
const Hamilton: React.FC<SP> = ({d}) => (
  <Cam dur={d} push={[1.15, 1.28]} focus={[900, 600]}>
    <Stage>
      <Office />
      <Hair x={HX} y={FLOOR} sit />
      <Hero x={HX} y={FLOOR} pose="sit" glasses brow={-0.15} mouth={0.15} headTilt={-3} />
      <NameTag x={HX - 40} y={FLOOR - 330} text="MARGARET HAMILTON" from={16} flip size={38} />
    </Stage>
  </Cam>
);

const DesignRules: React.FC<SP> = ({d}) => (
  <Cam dur={d} push={[1, 1.07]} focus={[900, 520]}>
    <Stage>
      <Doc
        title="EXECUTIVE: DESIGN RULES"
        lines={['EVERY JOB HAS A PRIORITY.', '', 'IF THE COMPUTER IS OVERLOADED:', '  1. RESTART', '  2. DROP THE LEAST IMPORTANT', '  3. KEEP FLYING']}
        reveal={[0, 8, 14, 22, 30, 38]}
        size={36}
        tilt={1.5}
      >
        <Marker x={958} y={555} rx={372} ry={124} from={38} box />
      </Doc>
    </Stage>
  </Cam>
);

// ---------------------------------------------------------------- part II: the overload
const Radar: React.FC<SP> = ({s, d}) => {
  const f = useCurrentFrame();
  return (
    <Cam dur={d} push={[1, 1.08]} focus={[860, 560]}>
      <Stage>
        <RadarPanel pulses={interpolate(f, [at(17, s) + 50, at(17, s) + 66], [0, 1], CL)} label={interpolate(f, [at(17, s) + 96, at(17, s) + 110], [0, 1], CL)} />
        <Marker x={SWITCH_XY[0] + 6} y={SWITCH_XY[1] - 4} rx={82} ry={78} from={at(17, s) + 8} />
      </Stage>
    </Cam>
  );
};

const Time: React.FC<SP> = ({s, d}) => {
  const f = useCurrentFrame();
  const steal = interpolate(f, [at(18, s) + 6, at(19, s) + 26], [0, 1], EASE);
  const over = interpolate(f, [at(20, s) + 30, at(20, s) + 44], [0, 1], EASE);
  const push = interpolate(f, [at(20, s), d], [1, 1.12], EASE);
  return (
    <AbsoluteFill style={{scale: String(push), transformOrigin: '1500px 540px'}}>
      <Stage>
        <TimeBar steal={steal} over={over} />
      </Stage>
    </AbsoluteFill>
  );
};

const Jobs: React.FC<SP> = ({s}) => {
  const f = useCurrentFrame();
  const a = at(21, s);
  const blank = interpolate(f, [a + 14, a + 18, a + 28, a + 34], [0, 1, 1, 0], CL);
  return (
    <Stage>
      <JobList blank={blank} drop={interpolate(f, [a + 52, a + 82], [0, 1], EASE)} keep={interpolate(f, [a + 96, a + 112], [0, 1], EASE)} />
    </Stage>
  );
};

const Coping: React.FC<SP> = ({s, d}) => {
  const f = useCurrentFrame();
  const a = at(23, s);
  const hand = (txt: string, y: number, from: number) => (
    <text x={1060} y={y} fontFamily={LOOK.font} fontWeight={700} fontSize={60} fill="#22222E" letterSpacing={2}>
      {txt.slice(0, Math.max(0, Math.floor((f - from) * 1.2)))}
    </text>
  );
  return (
    <Cam dur={d} push={[1, 1.06]} focus={[1300, 560]}>
      <Stage>
        <Backdrop dark />
        <g transform="translate(20 250) scale(0.52)">
          <Dsky lamp={1} code={1} />
        </g>
        <Doc
          x={1000}
          y={160}
          w={820}
          h={760}
          title="PROGRAM ALARM 1202"
          lines={['EXECUTIVE OVERFLOW.', 'TOO MANY JOBS,', 'NOT ENOUGH ROOM.']}
          reveal={[8, 18, 28]}
          size={38}
          tilt={2}
          stamp="NOT A CRASH"
          stampAt={at(22, s) + 26}
          stampXY={[1560, 600]}
          backdrop={false}
        >
          {hand("I'M OVERLOADED,", 760, a + 44)}
          {hand("BUT I'M COPING.", 840, a + 66)}
        </Doc>
      </Stage>
    </Cam>
  );
};

// ---------------------------------------------------------------- part III: the call
const GX = 1320; // Garman in the back room
const BackRoom: React.FC<SP> = ({d}) => {
  const f = useCurrentFrame();
  const BXL = 330;
  return (
    <Cam dur={d} push={[1, 1.05]} focus={[960, 600]}>
      <Stage>
        <ControlRoom wall={false}>
          {/* dividing wall */}
          <rect x={1100} y={60} width={50} height={FLOOR - 60} fill="#1A1A1D" />
          <rect x={1150} y={60} width={770} height={FLOOR - 60} fill="#0F0F11" />
          {[0, 1, 2].map((i) => (
            <rect key={i} x={1500 + i * 120} y={240} width={90} height={150} fill="#26262A" stroke="#3A3A40" strokeWidth={2} />
          ))}
          <g fontFamily={LOOK.font} fontWeight={700} letterSpacing={4} fontSize={34}>
            <rect x={200} y={170} width={420} height={70} fill="#26262A" stroke="#4A4A50" strokeWidth={2} />
            <text x={410} y={218} textAnchor="middle" fill="#C8C8CC">MISSION CONTROL</text>
            <rect x={1220} y={170} width={300} height={70} fill="#26262A" stroke="#4A4A50" strokeWidth={2} />
            <text x={1370} y={218} textAnchor="middle" fill="#C8C8CC">BACK ROOM</text>
          </g>
          <Console heroX={BXL} screen={<ScreenChart progress={0.45} alarms={1} />} />
          <Console heroX={GX - 520 > 0 ? GX : GX} screen={<ScreenChart progress={0.45} alarms={1} />} glow={0.7} />
          <Hero x={BXL} y={FLOOR} pose="sit" headphones {...HOUSTON} brow={0.45} mouth={-0.2} />
          <Hero x={GX} y={FLOOR} pose="sit" headphones {...GARMAN} brow={0} mouth={0} seed={3} />
          {/* the voice loop between them */}
          <path d={`M${BXL - 40},${FLOOR - 290} Q${BXL + 300},250 1125,300 Q${GX - 200},250 ${GX - 40},${FLOOR - 290}`} stroke={C.white} strokeWidth={3} strokeDasharray="12 10" strokeDashoffset={-f * 2} fill="none" opacity={interpolate(f, [20, 40], [0, 0.7], CL)} />
        </ControlRoom>
      </Stage>
    </Cam>
  );
};

const Garman: React.FC<SP> = ({d}) => (
  <Cam dur={d} push={[1.3, 1.42]} focus={[900, 620]}>
    <Stage>
      <ControlRoom wall={false}>
        <rect x={0} y={60} width={1920} height={FLOOR - 60} fill="#0F0F11" />
        {[0, 1, 2, 3].map((i) => (
          <rect key={i} x={200 + i * 120} y={260} width={90} height={150} fill="#26262A" stroke="#3A3A40" strokeWidth={2} />
        ))}
        <Console heroX={820} screen={
          <g fontFamily={LOOK.mono} fontWeight={700} fontSize={30} fill="#C8C8CC">
            {['1106', '1201', '1202', '1210'].map((c, i) => (
              <text key={c} x={40} y={60 + i * 50} fill={c === '1202' ? C.accent : '#C8C8CC'}>{c}</text>
            ))}
          </g>
        } />
        <Hero x={820} y={FLOOR} pose="sit" headphones {...GARMAN} brow={-0.25} mouth={0.1} headTilt={-4} seed={3} />
        <NameTag x={780} y={FLOOR - 330} text="JACK GARMAN, 24" from={20} flip size={36} />
      </ControlRoom>
    </Stage>
  </Cam>
);

const CheatSheet: React.FC<SP> = ({d}) => (
  <Cam dur={d} push={[1, 1.08]} focus={[900, 500]}>
    <Stage>
      <Doc
        title="ALARM CODES  (J. GARMAN)"
        lines={['1106   RESTART. CHECK IT.', '1201   OVERFLOW.', '1202   OVERFLOW.', '            IF NOT CONTINUOUS: GO', '1210   TWO JOBS, ONE DEVICE']}
        reveal={[0, 4, 8, 12, 16]}
        hand
        size={42}
        tilt={-2.5}
      >
        <Marker x={900} y={492} rx={318} ry={70} from={34} box />
      </Doc>
    </Stage>
  </Cam>
);

const GoCall: React.FC<SP> = ({s, d}) => {
  const f = useCurrentFrame();
  const a = at(27, s);
  const resolve = interpolate(f, [a + 20, a + 50], [0, 1], EASE);
  const talk = f > a + 46 && f < a + 92 ? 0.25 + 0.25 * Math.abs(Math.sin(f * 0.5)) : 0;
  const go = interpolate(f, [a + 50, a + 58], [0, 1], CL);
  return (
    <Cam dur={d} push={[1.65, 1.8]} focus={[840, 600]}>
      <Stage>
        <ControlRoom>
          <Console heroX={BX_H} screen={
            <g>
              <ScreenChart progress={0.48} alarms={2} />
              <rect x={70} y={70} width={180} height={110} fill={C.screenBg} opacity={0.9 * go} />
              <text x={160} y={160} textAnchor="middle" fontFamily={LOOK.display} fontSize={96} fill={C.white} opacity={go}>
                GO
              </text>
            </g>
          } />
          <Hero x={BX_H} y={FLOOR} pose="sit" headphones {...HOUSTON} brow={0.5 - 0.75 * resolve} mouth={-0.2 + 0.3 * resolve} mouthOpen={talk} />
        </ControlRoom>
      </Stage>
    </Cam>
  );
};

const AlarmChart: React.FC<SP> = ({d}) => {
  const f = useCurrentFrame();
  const progress = interpolate(f, [0, 20, 60, 95, 132, d], [0.4, 0.475, 0.725, 0.755, 0.795, 0.83], CL);
  const shown = ALARMS.reduce((a, [u]) => a + Math.max(0, Math.min(1, (progress - u) / 0.006 + 0.2)), 0);
  return (
    <Cam dur={d} push={[1, 1.06]} focus={[1100, 600]}>
      <Stage>
        <DescentChart progress={progress} alarmsShown={shown} />
      </Stage>
    </Cam>
  );
};

const Boulders: React.FC<SP> = ({s}) => {
  const f = useCurrentFrame();
  const scroll = f * 1.1;
  return (
    <Stage>
      <WindowView scroll={scroll} target={interpolate(f, [at(29, s) + 50, at(29, s) + 64], [0, 1], CL)} />
      <Marker x={BOULDERS[0] - scroll + 10} y={BOULDERS[1]} rx={330} ry={125} from={at(29, s) + 84} />
    </Stage>
  );
};

const Stick: React.FC<SP> = ({d}) => {
  const f = useCurrentFrame();
  return (
    <Cam dur={d} push={[1, 1.06]} focus={[1000, 520]}>
      <Stage>
        <HandStick grab={interpolate(f, [6, 40], [0, 1], EASE)} mode={interpolate(f, [30, 44], [0, 1], EASE)} />
      </Stage>
    </Cam>
  );
};

const Fuel: React.FC<SP> = ({d}) => {
  const f = useCurrentFrame();
  const end = d - 30;
  return (
    <Cam dur={d} push={[1, 1.1]} focus={[1520, 700]}>
      <Stage>
        <DescentChart progress={interpolate(f, [0, end], [0.83, 1], EASE)} alarmsShown={5} codes={false} fuel={interpolate(f, [0, end], [118, 45], CL)} landed={interpolate(f, [end + 2, end + 14], [0, 1], CL)} />
      </Stage>
    </Cam>
  );
};

const Landed: React.FC<SP> = ({d}) => {
  const f = useCurrentFrame();
  const dust = interpolate(f, [0, 50], [0.6, 0], EASE);
  return (
    <AbsoluteFill style={{scale: String(interpolate(f, [0, d], [1.05, 1.22], EASE)), transformOrigin: '960px 560px'}}>
      <Stage>
        <Backdrop dark />
        <Stars n={160} seed="land" maxY={760} />
        <Earth x={1480} y={250} r={56} />
        <MoonGround y={760} seed="land" />
        <Glow x={960} y={760} r={700} ry={90} color={C.moon} opacity={0.22} />
        <ellipse cx={1040} cy={792} rx={300} ry={20} fill="#000" opacity={0.6} />
        <Lander x={960} y={790} scale={1.05} windowLight={0.6} />
        <Glow x={960} y={790} r={500} ry={70} color={C.white} opacity={dust} />
      </Stage>
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------- what happened next
const MX = 860;
const MedalShot: React.FC<SP> = ({d}) => (
  <Cam dur={d} push={[1.22, 1.34]} focus={[900, 560]}>
    <Stage>
      <Ground floor={FLOOR} />
      <Glow x={960} y={300} r={900} ry={500} color={C.lamp} opacity={0.22} />
      {Array.from({length: 10}, (_, i) => (
        <path key={i} d={`M${120 + i * 180},60 Q${150 + i * 180},460 ${120 + i * 180},${FLOOR}`} stroke="#18181B" strokeWidth={30} fill="none" />
      ))}
      <Hair x={MX} y={FLOOR} color="#5E5E64" />
      <Hero x={MX} y={FLOOR} pose="stand" glasses brow={-0.1} mouth={0.45} headTilt={-3} />
      <Medal x={MX + 2} y={FLOOR - 205} scale={1.0} />
      <Marker x={MX + 2} y={FLOOR - 188} rx={50} ry={52} from={44} />
      <NameTag x={MX + 50} y={FLOOR - 330} text="MARGARET HAMILTON" from={16} size={36} />
    </Stage>
  </Cam>
);

const Code: React.FC<SP> = ({d}) => {
  const f = useCurrentFrame();
  const y = 70 + CODE_HOPE_LINE * 52 - 12;
  return (
    <Cam dur={d} push={[1, 1.06]} focus={[960, 500]}>
      <Stage>
        <CodeScreen scroll={interpolate(f, [0, d], [0, 220], EASE)}>
          <Marker x={958} y={y} rx={318} ry={34} from={56} box />
        </CodeScreen>
      </Stage>
    </Cam>
  );
};

const Final: React.FC<SP> = ({d}) => (
  <Cam dur={d} push={[1, 1.12]} focus={[1100, 640]}>
    <Stage>
      <Backdrop dark />
      <Stars n={200} seed="fin" maxY={720} />
      <Earth x={520} y={260} r={60} />
      <MoonGround y={720} seed="fin" />
      <Glow x={1200} y={720} r={900} ry={120} color={C.moon} opacity={0.18} />
      <ellipse cx={1260} cy={760} rx={240} ry={14} fill="#000" opacity={0.6} />
      <Lander x={1100} y={760} scale={0.75} ascent={false} />
      <line x1={1290} y1={760} x2={1290} y2={640} stroke="#8A8A90" strokeWidth={4} />
      <rect x={1290} y={640} width={70} height={44} fill="#C8C8CC" />
    </Stage>
  </Cam>
);

// ---------------------------------------------------------------- shot list: [film frame, scene]
const L = (n: number) => lineAt(n) - 6;
const SHOTS: [number, React.FC<SP>][] = [
  [0, EagleDescent],
  [L(2), MoonShot],
  [L(3), Crew],
  [L(4), DskyAlarm],
  [L(6), Transcript],
  [L(7), CockpitClose],
  [L(8), Viewers],
  [L(9), Bales],
  [lineEnd(9) + 6, chapter('PART I', 'THE COMPUTER')],
  [lineEnd(9) + 66, Agc],
  [L(11), Memory],
  [L(12), Rope],
  [L(13), Cutaway],
  [L(14), Hamilton],
  [L(15), DesignRules],
  [lineEnd(15) + 6, chapter('PART II', 'THE OVERLOAD')],
  [lineEnd(15) + 66, Radar],
  [L(18), Time],
  [L(21), Jobs],
  [L(22), Coping],
  [lineEnd(23) + 6, chapter('PART III', 'THE CALL')],
  [lineEnd(23) + 66, BackRoom],
  [L(25), Garman],
  [L(26), CheatSheet],
  [L(27), GoCall],
  [L(28), AlarmChart],
  [L(29), Boulders],
  [L(30), Stick],
  [L(31), Fuel],
  [lineEnd(31) + 30, Landed],
  [L(33), MedalShot],
  [L(34), Code],
  [L(35), Final],
];
export const SHOT_COUNT = SHOTS.length;
export const SHOT_STARTS = SHOTS.map((s) => s[0]);

const NARRATOR: [number, number, string][] = [
  [lineAt(1) + 6, lineEnd(1) + 10, 'Apollo 11, lunar descent'],
  [lineAt(2), lineEnd(2) + 6, 'July 20, 1969'],
  [lineAt(3), lineEnd(3), 'Lunar Module Eagle'],
  [lineAt(9), lineEnd(9), 'Mission Control, Houston'],
  [lineEnd(9) + 70, lineEnd(10) + 6, 'MIT, Cambridge, Massachusetts'],
  [lineAt(14), lineEnd(14), 'MIT Instrumentation Laboratory'],
  [lineEnd(15) + 70, lineEnd(16), 'Inside Eagle, 3:10 PM Houston time'],
  [lineEnd(23) + 70, lineEnd(24), 'Houston, seconds later'],
  [lineAt(29), lineEnd(29), 'Below 1,000 feet'],
  [lineAt(32) - 4, lineEnd(32) + 26, 'July 20, 1969, 3:17 PM'],
  [lineAt(33), lineEnd(33), 'Washington, 2016'],
  [lineAt(34), lineEnd(34), 'Published online, 2016'],
];

export const Apollo1202Film: React.FC = () => (
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
      <TitleCard word="OVERLOADED." line="No system is ever perfect." accentLine="Build it to survive." />
    </Sequence>
    <Narrator lines={NARRATOR} />
    <Letterbox />
    <Apollo1202Sound />
  </AbsoluteFill>
);

export const FilmApollo1202: React.FC = () => {
  applyLook(LOOKS.documentary);
  return (
    <LookFx look="documentary">
      <Apollo1202Film />
    </LookFx>
  );
};

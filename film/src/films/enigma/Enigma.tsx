import React from 'react';
import {AbsoluteFill, Easing, interpolate, Sequence, useCurrentFrame} from 'remotion';
import {applyLook, C, FLOOR, LOOK} from '../../theme';
import {LOOKS} from '../../looks';
import {LookFx} from '../../components/LookFx';
import {Hero, Shadow} from '../../components/Hero';
import {Cam, Flash, Letterbox, Narrator, RepPops, ShadowLine, Stage} from '../../components/Hud';
import {Marker} from '../../components/Primitives';
import {TitleCard} from '../../components/TitleCard';
import {AtlanticMap, Bombe, Chalkboard, EnigmaSide, EnigmaTop, Hut, lampXY, Mansion, MidnightClock, MugRadiator, Paper, SubRadio} from './props';
import {Pt} from '../../components/lib';
import {Ground} from '../../components/Primitives';
import voice from '../../../public/voice/enigma.json';
import {EnigmaSound} from './Sound';

// ---------------------------------------------------------------- timing (all from the narration)
export const VOICE_AT = 20; // narration starts at this film frame
const lineAt = (n: number) => voice.lines[n - 1].startFrame + VOICE_AT;
const lineEnd = (n: number) => voice.lines[n - 1].endFrame + VOICE_AT;
export const TITLE_AT = Math.round(voice.duration * 30) + VOICE_AT + 20;
export const ENIGMA_DURATION = TITLE_AT + 360;

const EASE = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.inOut(Easing.cubic)} as const;
const CL = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;

// cast colours: Turing is the hero; everyone else is darker clay
const EXTRA = {fill: '#8E8E94', backFill: '#6A6A70'};
const OFFICER = {fill: '#7A7A80', backFill: '#5C5C62'};
const HX = 820;

type SP = {s: number; d: number}; // scene start (film frame) and duration
const at = (n: number, s: number) => lineAt(n) - s; // a line's start, local to the scene

// ---------------------------------------------------------------- small shared pieces
const NameTag: React.FC<{x: number; y: number; text: string; from?: number}> = ({x, y, text, from = 0}) => {
  const f = useCurrentFrame();
  const o = interpolate(f, [from, from + 12], [0, 1], CL);
  return (
    <g opacity={o}>
      <path d={`M${x},${y} L${x + 70},${y - 70} L${x + 110},${y - 70}`} stroke={C.white} strokeWidth={2.5} fill="none" />
      <circle cx={x} cy={y} r={5} fill={C.white} />
      <text x={x + 120} y={y - 60} fontFamily={LOOK.font} fontWeight={700} fontSize={40} fill={C.white} letterSpacing={3}>
        {text}
      </text>
    </g>
  );
};

const Headline: React.FC<{text: string; sub?: string; size?: number; typed?: number; from?: number}> = ({text, sub, size = 200, typed, from = 0}) => {
  const f = useCurrentFrame();
  const o = interpolate(f, [from, from + 10], [0, 1], CL);
  const shown = typed === undefined ? text : text.slice(0, typed);
  return (
    <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', opacity: o}}>
      <div style={{fontFamily: LOOK.display, fontSize: size, color: C.white, letterSpacing: 4, lineHeight: 1, textShadow: '0 6px 30px rgba(0,0,0,0.8)'}}>{shown}</div>
      {sub ? <div style={{fontFamily: LOOK.font, fontWeight: 700, fontSize: 52, color: C.accent, letterSpacing: 6, marginTop: 30, textTransform: 'uppercase'}}>{sub}</div> : null}
    </AbsoluteFill>
  );
};

// "159" followed by zeros: n digits long, grouped with commas
const bigDigits = (digits: number) => (digits <= 4 ? '3,000' : ('159' + '0'.repeat(digits - 3)).replace(/\B(?=(\d{3})+(?!\d))/g, ','));

const Operator: React.FC<SP> = ({d}) => (
  <Cam dur={d} push={[1, 1.06]} focus={[900, 620]}>
    <Stage>
      <Hut enigma lamp={1} />
      <Hero x={HX} y={FLOOR} pose="type" cap {...EXTRA} brow={-0.3} mouth={-0.1} typeSpeed={0.7} />
    </Stage>
  </Cam>
);

// Three operators typing the same thing at the same time: predictable.
const OperatorsRow: React.FC<SP> = ({d}) => (
  <Cam dur={d} push={[1, 1.06]} focus={[960, 640]}>
    <Stage>
      <Ground floor={FLOOR} />
      {[0, 1, 2].map((i) => {
        const x0 = 200 + i * 600;
        return (
          <g key={i} transform={`translate(${x0} ${FLOOR}) scale(0.8) translate(0 ${-FLOOR})`}>
            <rect x={-60} y={FLOOR - 104} width={120} height={14} fill={C.propLight} />
            <rect x={70} y={FLOOR - 150} width={420} height={20} fill={C.propLight} />
            <rect x={90} y={FLOOR - 130} width={8} height={130} fill={C.propLight} />
            <rect x={470} y={FLOOR - 130} width={8} height={130} fill={C.propLight} />
            <EnigmaSide x={150} y={FLOOR - 150} lamp={0.5} />
            <Hero x={0} y={FLOOR} pose="type" cap {...EXTRA} brow={-0.1} typeSpeed={0.7} />
          </g>
        );
      })}
    </Stage>
  </Cam>
);

// ---------------------------------------------------------------- cold open
const Docs: React.FC<SP> = ({d}) => {
  const third = Math.ceil(d / 3);
  const papers = [
    {title: 'BEFEHL', lines: ['AN ALLE U-BOOTE', 'ANGRIFF 0600', 'QUADRAT AJ 49'], stamp: 'GEHEIM', tilt: -3},
    {title: 'POSITION', lines: ['54 N  22 W', 'KONVOI HX 79', '12 SCHIFFE'], tilt: 2},
    {title: 'ANGRIFFSPLAN', lines: ['WOLFSRUDEL', 'ZIEL: KONVOI', 'BEI NACHT'], stamp: 'GEHEIM', tilt: -1},
  ];
  return (
    <>
      {papers.map((p, i) => (
        <Sequence key={i} from={i * third} durationInFrames={third} layout="none">
          <Cam dur={third} push={[1, 1.07]} focus={[i === 1 ? 700 : 1200, 400]}>
            <Stage>
              <Paper {...p} />
            </Stage>
          </Cam>
        </Sequence>
      ))}
    </>
  );
};

const KeyPress: React.FC<SP> = ({s}) => {
  const f = useCurrentFrame();
  const p1 = at(3, s) + 22;
  const p2 = at(4, s) + 20;
  const down1 = f >= p1 && f < p1 + 14;
  const down2 = f >= p2 && f < p2 + 14;
  const lit = f >= p2 ? (f < p2 + 70 ? 'M' : null) : f >= p1 && f < p1 + 70 ? 'Q' : null;
  const rotors = f >= p2 ? 'ADW' : f >= p1 ? 'ADV' : 'ADU';
  const [mx, my] = lampXY('M');
  return (
    <Stage>
      <EnigmaTop pressed={down1 || down2 ? 'A' : null} lit={lit} rotors={rotors} />
      <Marker x={mx} y={my} rx={54} ry={54} from={p2 + 6} to={p2 + 68} />
    </Stage>
  );
};

const EnigmaName: React.FC<SP> = ({d}) => (
  <>
    <Cam dur={d} push={[1, 1.12]} focus={[960, 400]}>
      <Stage>
        <EnigmaTop rotors="ADW" />
      </Stage>
    </Cam>
    <AbsoluteFill style={{background: 'rgba(0,0,0,0.45)'}} />
    <Headline text="ENIGMA" size={260} from={6} />
  </>
);

const Midnight: React.FC<SP> = ({d}) => {
  const hit = Math.min(d - 20, 56);
  return (
    <>
      <Stage>
        <MidnightClock from={58.6} to={60} dur={hit} />
      </Stage>
      <Flash at={[hit]} />
    </>
  );
};

const BigNum: React.FC<SP> = () => {
  const f = useCurrentFrame();
  const full = bigDigits(21);
  return <Headline text={full} typed={Math.floor(f * 0.9)} size={120} sub="possible settings" />;
};

const Useless: React.FC<SP> = ({s, d}) => {
  const f = useCurrentFrame();
  return (
    <Cam dur={d} push={[1, 1.06]} focus={[900, 420]}>
    <Stage>
      <Paper title="SCHLUESSEL - DIENSTAG" lines={['WALZEN:  II  IV  V', 'RINGE:   02  21  12', 'STECKER: AV BS CG DL', '         FU HZ IN KM']} tilt={1} cross={interpolate(f, [at(8, s) + 30, at(8, s) + 60], [0, 1], CL)} />
    </Stage>
    </Cam>
  );
};

const OfficerShot = (push: [number, number], focus: [number, number]): React.FC<SP> => ({d}) => (
  <Cam dur={d} push={push} focus={focus}>
    <Stage>
      <Hut enigma lamp={1} />
      <Hero x={760} y={FLOOR} pose="stand" cap {...OFFICER} brow={-0.25} mouth={0.45} />
    </Stage>
  </Cam>
);
const Officer = OfficerShot([1, 1.1], [860, 560]);
const OfficerClose = OfficerShot([1.45, 1.6], [790, 560]);

const Almost: React.FC<SP> = ({d}) => {
  const f = useCurrentFrame();
  return (
    <Cam dur={d} push={[1, 1.15]} focus={[1150, 420]}>
      <Stage>
        <EnigmaTop rotors="ADW" crack={interpolate(f, [12, 40], [0, 1], EASE)} />
        <Marker x={1145} y={420} rx={105} ry={290} from={44} seed={2} />
      </Stage>
    </Cam>
  );
};

// ---------------------------------------------------------------- the Atlantic
const SCATTER: Pt[] = [[700, 250], [1100, 820], [600, 860], [1050, 300], [820, 960]];
const PACK: Pt[] = [[800, 600], [850, 560], [880, 620], [760, 640], [830, 660]];
const subsAt = (k: number): Pt[] => SCATTER.map((p, i) => [p[0] + (PACK[i][0] - p[0]) * k, p[1] + (PACK[i][1] - p[1]) * k]);

const Convoy: React.FC<SP> = ({s, d}) => {
  const f = useCurrentFrame();
  const pack = interpolate(f, [at(12, s), at(12, s) + 50], [0, 1], EASE);
  return (
    <Stage>
      <AtlanticMap convoyU={interpolate(f, [0, d], [0.05, 0.33])} subs={subsAt(pack)} labels={interpolate(f, [at(12, s) + 40, at(12, s) + 56], [0, 1], CL)} />
    </Stage>
  );
};

const Sinking: React.FC<SP> = ({d}) => {
  const f = useCurrentFrame();
  return (
    <Stage>
      <AtlanticMap convoyU={interpolate(f, [0, d], [0.33, 0.45])} subs={PACK} sunkAt={[999, 18, 999, 40, 60, 999, 75]} sunkCounter />
    </Stage>
  );
};

const Island: React.FC<SP> = ({d}) => {
  const f = useCurrentFrame();
  return (
    <Cam dur={d} push={[1, 1.9]} focus={[1420, 460]}>
      <Stage>
        <AtlanticMap convoyU={0.45} ships={0} subs={PACK} britainGlow={interpolate(f, [10, 40], [0, 1], EASE)} />
      </Stage>
    </Cam>
  );
};

const Sub: React.FC<SP> = () => (
  <Stage>
    <SubRadio waves={1} />
  </Stage>
);

const Listening: React.FC<SP> = ({d}) => (
  <Cam dur={d} push={[1, 1.06]} focus={[900, 620]}>
    <Stage>
      <Hut radio lamp={0.8} mug={false} />
      <Hero x={HX} y={FLOOR} pose="type" headphones {...EXTRA} brow={0.2} browLift={4} mouth={-0.1} typeSpeed={0.5} />
    </Stage>
  </Cam>
);

const Gibberish: React.FC<SP> = ({d}) => (
  <Cam dur={d} push={[1, 1.08]} focus={[830, 420]}>
    <Stage>
      <Paper title="INTERCEPT 0417" lines={['XQZRT PLMVA OKWNE', 'UTRBC AAXEQ LMPZD', 'HHQRT WNVUA EKSOP', 'JZLMQ RTUVW XKAEB']}>
        <Marker x={826} y={404} rx={232} ry={132} from={40} box />
      </Paper>
    </Stage>
  </Cam>
);

// ---------------------------------------------------------------- Bletchley
const Arrival: React.FC<SP> = () => {
  const f = useCurrentFrame();
  return (
    <Stage>
      <Mansion />
      {[0, 1, 2].map((i) => {
        const x = interpolate(f, [0, 200], [120 + i * 120, 620 + i * 120], CL);
        return <Hero key={i} x={x} y={FLOOR} scale={0.45} pose="walk" runPhase={f * 0.16 + i * 2} {...EXTRA} seed={i} />;
      })}
    </Stage>
  );
};

const TuringIntro: React.FC<SP> = ({d}) => (
  <Cam dur={d} push={[1.1, 1.2]} focus={[860, 560]}>
    <Stage>
      <Hut lamp={1} />
      <Hero x={HX} y={FLOOR} pose="sit" brow={-0.15} mouth={0.1} headTilt={-4} />
      <NameTag x={HX + 70} y={FLOOR - 360} text="ALAN TURING" from={20} />
    </Stage>
  </Cam>
);

const Mug: React.FC<SP> = () => (
  <Stage>
    <MugRadiator />
    <Marker x={930} y={405} rx={185} ry={150} from={40} />
  </Stage>
);

const Pitch: React.FC<SP> = ({d}) => {
  const f = useCurrentFrame();
  const shake = Math.sin(f * 0.18) * 4 * interpolate(f, [20, 40, 80, 100], [0, 1, 1, 0], CL);
  return (
    <Cam dur={d} push={[1.08, 1.16]} focus={[1000, 600]}>
      <Stage>
        <Hut desk={false} chalk lamp={0} />
        <Hero x={620} y={FLOOR} pose="stand" {...EXTRA} brow={-0.5} mouth={-0.4} headTilt={shake} seed={1} />
        <Hero x={820} y={FLOOR} pose="stand" {...EXTRA} brow={-0.4} mouth={-0.3} headTilt={-5} seed={2} />
        <Hero x={1240} y={FLOOR} pose="stand" scarf facing={-1} brow={0.2} mouth={0.2} />
      </Stage>
    </Cam>
  );
};

const ChalkIdea: React.FC<SP> = ({d}) => {
  const f = useCurrentFrame();
  return (
    <Stage>
      <Chalkboard draw={interpolate(f, [0, d - 20], [0, 1], CL)} />
    </Stage>
  );
};

// ---------------------------------------------------------------- the struggle
const BombeProblem: React.FC<SP> = ({d}) => {
  const f = useCurrentFrame();
  return (
    <Cam dur={d} push={[1.12, 1.25]} focus={[1050, 620]}>
      <Stage>
        <Hut desk={false} lamp={0} />
        <Bombe x={1100} spin={f * 0.25} />
        <Hero x={880} y={FLOOR} pose="stand" scarf brow={0.45} mouth={-0.3} />
      </Stage>
    </Cam>
  );
};

const Montage: React.FC<SP> = ({d}) => {
  const n = 3;
  const len = Math.ceil(d / n);
  const shots = [
    <Stage key="b">
      <Hut desk={false} lamp={0} window={false} />
      <Bombe x={660} spin={0} scale={1.0} />
    </Stage>,
    <Stage key="p">
      <Paper title="ERGEBNIS" lines={['RUN 0412   NO MATCH', 'RUN 0413   NO MATCH', 'RUN 0414   NO MATCH', 'RUN 0415   NO MATCH']} tilt={2} stamp="NO MATCH" stampAt={16} />
    </Stage>,
    <Stage key="c">
      <MidnightClock from={40} to={60} dur={len} />
    </Stage>,
  ];
  return (
    <>
      {shots.map((el, i) => (
        <Sequence key={i} from={i * len} durationInFrames={len} layout="none">
          <AbsoluteFill>{i === 0 ? <SpinBombe /> : el}</AbsoluteFill>
        </Sequence>
      ))}
    </>
  );
};
const SpinBombe: React.FC = () => {
  const f = useCurrentFrame();
  return (
    <Stage>
      <Hut desk={false} lamp={0} window={false} />
      <Bombe x={680} spin={f * 0.6} />
    </Stage>
  );
};

const Despair: React.FC<SP> = ({d}) => {
  const f = useCurrentFrame();
  return (
    <Cam dur={d} push={[1, 1.1]} focus={[760, 640]}>
      <Stage>
        <Hut desk={false} lamp={0} />
        <Bombe x={1150} spin={f * 0.15} />
        <Shadow x={460} y={FLOOR} scale={1.75} />
        <Hero x={820} y={FLOOR} pose="slump" scarf brow={1} mouth={-0.7} />
        <ShadowLine text="Give up. Go home." x={760} y={300} from={20} to={d - 6} />
      </Stage>
    </Cam>
  );
};

// ---------------------------------------------------------------- the flaw
const Flaw: React.FC<SP> = ({d}) => {
  const f = useCurrentFrame();
  const k = Math.floor(f / 22);
  const down = f % 22 < 10;
  const [ax, ay] = lampXY('A');
  return (
    <Cam dur={d} push={[1, 1.15]} focus={[ax + 80, ay]}>
      <Stage>
        <EnigmaTop rotors={'QEV'.slice(0, 2) + String.fromCharCode(86 + (k % 4))} pressed={down ? 'A' : null} lit={down ? 'QMTXRBK'[k % 7] : null} />
        <Marker x={ax} y={ay} rx={52} ry={52} from={44} />
      </Stage>
    </Cam>
  );
};

const SelfLetters: React.FC<SP> = ({s}) => {
  const f = useCurrentFrame();
  const second = f >= at(31, s) + 50;
  const L = second ? 'E' : 'A';
  const x = interpolate(f, [second ? at(31, s) + 50 : 20, (second ? at(31, s) + 50 : 20) + 14], [0, 1], EASE);
  return (
    <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', background: C.bgDark}}>
      <div style={{display: 'flex', alignItems: 'center', gap: 80, fontFamily: LOOK.display, fontSize: 300, color: C.white}}>
        <span>{L}</span>
        <span style={{fontSize: 140, color: '#8A8A90'}}>→</span>
        <span style={{position: 'relative'}}>
          {L}
          <svg width={300} height={300} viewBox="0 0 300 300" style={{position: 'absolute', left: -60, top: 20}}>
            <g stroke={C.accent} strokeWidth={22} strokeLinecap="round" opacity={x > 0.02 ? 1 : 0} style={{filter: `drop-shadow(0 0 10px ${C.accent})`}}>
              <line x1={40} y1={40} x2={40 + 220 * Math.min(1, x * 2)} y2={40 + 220 * Math.min(1, x * 2)} />
              {x > 0.5 ? <line x1={260} y1={40} x2={260 - 220 * (x - 0.5) * 2} y2={40 + 220 * (x - 0.5) * 2} /> : null}
            </g>
          </svg>
        </span>
      </div>
    </AbsoluteFill>
  );
};

const Weather: React.FC<SP> = ({d}) => (
  <Cam dur={d} push={[1, 1.1]} focus={[800, 300]}>
    <Stage>
      <Paper title="WETTERBERICHT" lines={['WETTER VORHERSAGE', 'BISKAYA: REGEN', 'WIND: NW 4', 'SICHT: GUT']} tilt={-2}>
        <Marker x={810} y={224} rx={240} ry={46} from={40} />
      </Paper>
    </Stage>
  </Cam>
);

const CIPHER = 'YTLVKENCTEVZTFJL';
const CRIB = 'WETTERBERICHT';
const Crib: React.FC<SP> = ({d}) => {
  const f = useCurrentFrame();
  const step = Math.floor((d - 40) / 4);
  const off = Math.min(3, Math.floor(f / step));
  const slide = interpolate(f % step, [0, 10], [off === 0 ? 0 : off - 1, off], EASE);
  const done = off === 3 && f % step > 12;
  const cell = 92;
  const x0 = 960 - (CIPHER.length * cell) / 2;
  return (
    <Stage>
      <rect x={0} y={0} width={1920} height={1080} fill={C.bgDark} />
      {CIPHER.split('').map((ch, i) => (
        <g key={'c' + i}>
          <rect x={x0 + i * cell + 4} y={380} width={cell - 8} height={110} rx={8} fill="#1C1C20" stroke="#55555A" strokeWidth={2} />
          <text x={x0 + i * cell + cell / 2} y={458} textAnchor="middle" fontFamily={LOOK.mono} fontWeight={700} fontSize={56} fill={C.white}>
            {ch}
          </text>
        </g>
      ))}
      {CRIB.split('').map((ch, i) => {
        const col = Math.round(slide) + i;
        const clash = Math.abs(slide - Math.round(slide)) < 0.05 && CIPHER[col] === ch;
        const x = x0 + (slide + i) * cell;
        return (
          <g key={'k' + i}>
            <rect x={x + 4} y={540} width={cell - 8} height={110} rx={8} fill={clash ? '#3A1012' : '#2A2A2F'} stroke={clash ? C.accent : done ? C.white : '#55555A'} strokeWidth={clash ? 5 : 2} />
            <text x={x + cell / 2} y={618} textAnchor="middle" fontFamily={LOOK.mono} fontWeight={700} fontSize={56} fill={clash ? C.accent : C.white}>
              {ch}
            </text>
            {clash ? <line x1={x + cell / 2} y1={490} x2={x + cell / 2} y2={540} stroke={C.accent} strokeWidth={5} /> : null}
          </g>
        );
      })}
      <text x={960} y={300} textAnchor="middle" fontFamily={LOOK.font} fontWeight={700} fontSize={44} fill="#8A8A90" letterSpacing={4}>
        {done ? 'NO CLASH. THIS POSITION IS POSSIBLE.' : 'SAME LETTER IN THE SAME PLACE = IMPOSSIBLE'}
      </text>
    </Stage>
  );
};

const Shrink: React.FC<SP> = ({d}) => {
  const f = useCurrentFrame();
  const digits = Math.round(interpolate(f, [8, d - 30], [21, 4], EASE));
  return (
    <>
      <Headline text={bigDigits(digits)} size={130} sub={digits <= 4 ? 'possible settings left' : 'possible settings'} />
      <Stage>
        <Marker x={960} y={492} rx={250} ry={86} from={d - 26} />
      </Stage>
    </>
  );
};

// ---------------------------------------------------------------- the breakthrough
const Found: React.FC<SP> = ({s, d}) => {
  const f = useCurrentFrame();
  const stop = at(37, s) - 6;
  // drums slow to a stop: integrate a decaying speed
  const speed = (x: number) => 0.6 * Math.max(0, 1 - x / stop);
  const spin = f < stop ? 0.6 * f - (0.6 * f * f) / (2 * stop) : 0.6 * stop - (0.6 * stop) / 2 + speed(f);
  const lit = interpolate(f, [stop, stop + 6], [0, 1], CL);
  const turn = interpolate(f, [stop + 4, stop + 30], [0, 1], EASE);
  const ss = interpolate(f, [stop, d], [1.4, 0.7], EASE);
  const push = interpolate(f, [stop + 6, d], [1, 1.25], EASE);
  return (
    <>
      <AbsoluteFill style={{scale: String(push), transformOrigin: '1000px 700px'}}>
      <Stage>
        <Hut desk={false} lamp={0} />
        <Bombe x={1100} spin={spin} lit={lit} />
        <text x={1380} y={310} textAnchor="middle" fontFamily={LOOK.display} fontSize={96} letterSpacing={4} fill={C.accent} opacity={interpolate(f, [stop + 2, stop + 14], [0, 1], CL)}>
          KEY FOUND
        </text>
        <Shadow x={520} y={FLOOR} scale={ss} opacity={interpolate(f, [0, 20, stop, stop + 50], [0, 0.6, 0.6, 0], CL)} />
        <Hero x={880} y={FLOOR} pose="stand" scarf brow={0.2 - 0.3 * turn} browLift={12 * turn} mouthOpen={turn > 0.2 && turn < 0.8 ? 0.5 : 0} mouth={turn >= 0.8 ? 0.8 : -0.2} />
      </Stage>
      </AbsoluteFill>
      <Flash at={[stop]} />
    </>
  );
};

const Reroute: React.FC<SP> = ({d}) => {
  const f = useCurrentFrame();
  return (
    <Stage>
      <AtlanticMap convoyU={interpolate(f, [0, d], [0.1, 0.9])} subs={PACK} reroute={interpolate(f, [0, 40], [0, 1], EASE)} />
    </Stage>
  );
};

const TwoYears: React.FC<SP> = () => <Headline text="−2 YEARS" size={240} sub="of war, some historians say" />;

const Alone: React.FC<SP> = ({d}) => (
  <Cam dur={d} push={[1.25, 1.45]} focus={[850, 560]}>
    <Stage>
      <Hut lamp={1} />
      <Hero x={HX} y={FLOOR} pose="sit" scarf brow={-0.2} mouth={0.2} headTilt={-3} />
    </Stage>
  </Cam>
);

// ---------------------------------------------------------------- shot list: [first narration line, scene]
const SHOTS: [number, React.FC<SP>][] = [
  [1, Operator],
  [2, Docs],
  [3, KeyPress],
  [5, EnigmaName],
  [6, Midnight],
  [7, BigNum],
  [8, Useless],
  [9, Officer],
  [10, Almost],
  [11, Convoy],
  [13, Sinking],
  [14, Island],
  [15, Sub],
  [16, Listening],
  [17, Gibberish],
  [18, Arrival],
  [20, TuringIntro],
  [21, Mug],
  [22, Pitch],
  [23, ChalkIdea],
  [25, BombeProblem],
  [27, Montage],
  [28, Despair],
  [29, Flaw],
  [30, SelfLetters],
  [32, OperatorsRow],
  [33, Weather],
  [34, Crib],
  [35, Shrink],
  [36, Found],
  [38, Reroute],
  [39, TwoYears],
  [40, OfficerClose],
  [41, Alone],
];

const shotStart = (i: number) => (i === 0 ? 0 : lineAt(SHOTS[i][0]) - 6);

const NARRATOR: [number, number, string][] = [
  [lineAt(1) + 6, lineEnd(1) + 10, 'Germany, 1939'],
  [lineAt(6), lineEnd(6) + 6, 'Every midnight: new settings'],
  [lineAt(11), lineEnd(11) + 10, 'North Atlantic, 1940'],
  [lineAt(19), lineEnd(19), 'Bletchley Park, England'],
  [lineAt(20), lineEnd(20), 'Autumn, 1939'],
  [lineAt(25), lineEnd(25), 'Spring, 1940'],
  [lineAt(26), lineEnd(26), 'Too slow to beat midnight'],
  [lineAt(27), lineEnd(27) + 20, 'Months pass'],
  [lineAt(30), lineEnd(31), 'A letter never becomes itself'],
  [lineAt(36), lineEnd(36), 'Summer, 1940'],
];

const POPS: [number, string, number, number][] = [
];

export const EnigmaFilm: React.FC = () => (
  <AbsoluteFill style={{background: C.bg}}>
    {SHOTS.map(([, Scene], i) => {
      const s = shotStart(i);
      const e = i + 1 < SHOTS.length ? shotStart(i + 1) : TITLE_AT;
      return (
        <Sequence key={i} from={s} durationInFrames={e - s} name={`${i + 1}. ${Scene.name}`}>
          <Scene s={s} d={e - s} />
        </Sequence>
      );
    })}
    <Sequence from={TITLE_AT} durationInFrames={360} name="Title card">
      <TitleCard word="BROKEN." line="Every system has a flaw." accentLine="Go looking for it." />
    </Sequence>
    <Narrator lines={NARRATOR} />
    <RepPops pops={POPS} />
    <Letterbox />
    <EnigmaSound />
  </AbsoluteFill>
);

export const Enigma: React.FC = () => {
  applyLook(LOOKS.documentary);
  return (
    <LookFx look="documentary">
      <EnigmaFilm />
    </LookFx>
  );
};

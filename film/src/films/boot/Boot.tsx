import React from 'react';
import {AbsoluteFill, Easing, interpolate, random, Sequence, useCurrentFrame} from 'remotion';
import {applyLook, C, FLOOR} from '../../theme';
import {LOOKS} from '../../looks';
import {LookFx} from '../../components/LookFx';
import {Hero, HERO_HEIGHT, Shadow} from '../../components/Hero';
import {Cam, DayCounter, Flash, Letterbox, Narrator, RepPops, ShadowLine, SpeedLines, Stage} from '../../components/Hud';
import {CityScroll} from '../../components/City';
import {TitleCard} from '../../components/TitleCard';
import {clamp01} from '../../components/lib';
import {BoardCU, LaptopCU, Room} from './sets';
import {Marker} from '../../components/Primitives';
import {ClockCU, GlassesCU, MugCU, ScopeCU} from './closeups';
import {BootSound} from './Sound';

export const BOOT_DURATION = 3960; // 2:12 at 30 fps

const HX = 820; // hero's seat position at the desk

// ---------------- timeline data ----------------
const DAYS: [number, number][] = [
  [0, 1],
  [570, 2],
  ...Array.from({length: 18}, (_, i) => [720 + i * 30, 3 + i] as [number, number]),
  [1260, 21],
  [1650, 34],
  [2280, 35],
  [2490, 38],
  [2700, 41],
];

const NARRATOR: [number, number, string][] = [
  [30, 195, 'He wanted to build his own OS.'],
  [390, 555, 'Day one. Nothing worked.'],
  [590, 712, 'So he started reading.'],
  [740, 900, 'Every night. Every error.'],
  [1000, 1180, 'Build. Crash. Read. Repeat.'],
  [1670, 1875, 'Day thirty-four. He almost quit.'],
  [1910, 2060, 'But one LED still blinked.'],
  [2100, 2265, 'He went outside to think.'],
  [2300, 2475, 'Every crash told him something.'],
  [2510, 2685, 'Read the fault. Fix one thing.'],
  [2720, 2925, 'The stack. It was the stack.'],
  [3150, 3340, 'Day forty-one. It booted.'],
  [3390, 3585, 'Then he wrote the next line.'],
];

const POPS: [number, string, number, number][] = [
  [262, 'BUILD #1', 1500, 260],
  ...Array.from({length: 18}, (_, i) => [726 + i * 30, `BUILD #${4 + i * 7}`, 1560, 230] as [number, string, number, number]),
  ...Array.from({length: 8}, (_, i) => [1290 + i * 24, `BUILD #${141 + i}`, 1120 + (i % 2) * 70, 330 - (i % 3) * 30] as [number, string, number, number]),
  [2870, 'BUILD #212', 1500, 760],
  [3160, 'IT BOOTS!', 1060, 380],
];

// ---------------- scenes ----------------

const Intro: React.FC = () => (
  <Cam dur={210} push={[1, 1.08]} focus={[900, 620]}>
    <Stage>
      <Room lamp={0} screen={1} />
      <Hero x={HX} y={FLOOR} pose="type" brow={-0.2} mouth={0.35} />
    </Stage>
  </Cam>
);

const TripleFault: React.FC = () => {
  const f = useCurrentFrame();
  const hit = 100;
  if (f < hit) {
    return (
      <Stage>
        <LaptopCU
          lines={[
            {at: 5, text: '$ nasm boot.asm -o boot.bin', speed: 1.4},
            {at: 45, text: '$ qemu boot.bin', speed: 1.4},
            {at: 72, text: 'Booting...', color: C.white, speed: 1},
          ]}
        />
      </Stage>
    );
  }
  return (
    <>
      <Stage>
        <LaptopCU
          glow={C.error}
          bg="#1A0507"
          tint={0.06 + 0.05 * Math.sin(f)}
          lines={[
            {at: hit, text: 'TRIPLE FAULT', color: C.error, speed: 99, size: 150, center: true, y: 600},
            {at: hit + 14, text: 'cpu reset.', color: C.white, speed: 1.5, size: 54, center: true, y: 720},
          ]}
        />
      </Stage>
      <SpeedLines at={hit} />
      <Flash at={[hit]} />
    </>
  );
};

const FirstShadow: React.FC = () => {
  const f = useCurrentFrame();
  const shadowO = interpolate(f, [30, 75], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const sag = interpolate(f, [0, 30], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  return (
    <Stage>
      <Room lamp={0} screen={0.5} screenColor={C.error} />
      <Shadow x={560} y={FLOOR} scale={1.3} opacity={shadowO} />
      <Hero x={HX} y={FLOOR} pose="sit" brow={0.2 + 0.75 * sag} mouth={-0.6 * sag} headTilt={8 * sag} squash={1 - 0.05 * sag} />
      <ShadowLine text="You're not smart enough." x={650} y={FLOOR - HERO_HEIGHT * 1.3 - 28} from={80} to={205} anchor="middle" />
    </Stage>
  );
};

const Glasses: React.FC = () => (
  <Cam dur={150} push={[1, 1.1]} focus={[960, 470]}>
    <Stage>
      <GlassesCU />
    </Stage>
  </Cam>
);

const ERRS = [
  'error: undefined reference to kmain',
  'error: invalid opcode',
  'page fault at 0xDEADBEEF',
];

const MontageShot: React.FC<{i: number}> = ({i}) => {
  const kind = i % 6;
  const round = Math.floor(i / 6);
  if (kind === 0) {
    return (
      <Stage>
        <LaptopCU glow={C.error} lines={[{at: 0, text: '$ make', speed: 3}, {at: 8, text: ERRS[round], color: C.error, speed: 3}]} />
      </Stage>
    );
  }
  if (kind === 1) {
    return (
      <Stage>
        <BoardCU ledColor={C.error} blinkPeriod={10} />
      </Stage>
    );
  }
  if (kind === 2) {
    return (
      <Cam dur={30} push={[1.05, 1.12]} focus={[900, 600]}>
        <Stage>
          <Room lamp={1} screen={1} />
          <Hero x={HX} y={FLOOR} pose="type" glasses brow={-0.5 + round * 0.3} mouth={-0.2} typeSpeed={1.7} />
        </Stage>
      </Cam>
    );
  }
  if (kind === 3) {
    return (
      <Stage>
        <ClockCU speed={60 + round * 20} />
      </Stage>
    );
  }
  if (kind === 4) {
    return (
      <Stage>
        <ScopeCU glitch={round !== 1} />
      </Stage>
    );
  }
  return (
    <Stage>
      <MugCU count={round + 1} />
    </Stage>
  );
};

const Montage: React.FC = () => (
  <>
    {Array.from({length: 18}, (_, i) => (
      <Sequence key={i} from={i * 30} durationInFrames={30} layout="none">
        <AbsoluteFill>
          <MontageShot i={i} />
        </AbsoluteFill>
      </Sequence>
    ))}
  </>
);

const Grind: React.FC = () => {
  const f = useCurrentFrame();
  const err = Math.floor(f / 24) % 2 === 1;
  return (
    <Stage>
      <Room lamp={1} screen={1} screenColor={err ? C.error : C.screen} />
      <Shadow x={520} y={FLOOR} scale={1.7} />
      <Hero x={HX} y={FLOOR} pose="type" glasses brow={0.5} mouth={-0.35} typeSpeed={1.9} />
      <ShadowLine text="Others ship. You crash." x={520} y={FLOOR - HERO_HEIGHT * 1.7 - 28} from={60} to={225} anchor="middle" />
    </Stage>
  );
};

const KernelPanic: React.FC = () => {
  const f = useCurrentFrame();
  const hit = 45;
  if (f < hit) {
    return (
      <Stage>
        <LaptopCU lines={[{at: 0, text: '$ make run', speed: 2}, {at: 18, text: 'Loading kernel...', color: C.white, speed: 1.5}]} />
      </Stage>
    );
  }
  return (
    <>
      <Stage>
        <LaptopCU
          glow={C.error}
          bg="#220508"
          tint={0.1 + 0.06 * Math.sin(f * 1.3)}
          lines={[
            {at: hit, text: 'KERNEL PANIC', color: C.error, speed: 99, size: 160, center: true, y: 590},
            {at: hit + 10, text: 'not syncing: fatal exception', color: C.white, speed: 2, size: 52, center: true, y: 710},
          ]}
        />
      </Stage>
      <SpeedLines at={hit} dur={22} />
      <Flash at={[hit, hit + 5]} />
    </>
  );
};

const RockBottom: React.FC = () => (
  <Cam dur={240} push={[1, 1.12]} focus={[620, 700]}>
    <Stage>
      <Room lamp={0} screen={0.4} screenColor={C.error} />
      <Shadow x={330} y={FLOOR} scale={2.2} />
      <Hero x={600} y={FLOOR} pose="slump" glasses brow={1} mouth={-0.8} />
      <ShadowLine text="Quit. Nobody is watching." x={590} y={360} from={70} to={232} />
    </Stage>
  </Cam>
);

const LastLed: React.FC = () => (
  <Cam dur={180} push={[1, 1.18]} focus={[1180, 470]}>
    <Stage>
      <BoardCU ledColor={C.led} blinkPeriod={45} />
    </Stage>
  </Cam>
);

const EASE = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.inOut(Easing.cubic)} as const;

const StandUp: React.FC = () => {
  const f = useCurrentFrame();
  // brows go from defeated to determined first, then he slowly gets up
  const brow = interpolate(f, [0, 50], [1, -0.6], EASE);
  const rise = interpolate(f, [50, 105], [0, 1], EASE);
  const shadowScale = interpolate(f, [55, 120], [2.2, 1.7], EASE);
  const flick = f > 60 && f < 90 ? (random(`su${f}`) > 0.4 ? 1 : 0.35) : 1;
  const runStart = 150;
  const runX = interpolate(f, [runStart, 210], [600, -260], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.in(Easing.quad)});
  const runMix = interpolate(f, [runStart, runStart + 10], [0, 1], EASE);
  return (
    <Stage>
      <Room lamp={0} screen={0.4} screenColor={C.error} led={0.5 + 0.5 * Math.sin(f / 7)} />
      <Shadow x={330} y={FLOOR} scale={shadowScale} opacity={flick} />
      {f >= runStart ? (
        <Hero x={runX} y={FLOOR} pose="stand" pose2="run" mix={runMix} facing={-1} runPhase={(f - runStart) * 0.38} glasses brow={-0.7} mouth={-0.1} />
      ) : (
        <Hero
          x={600}
          y={FLOOR}
          pose="slump"
          pose2="stand"
          mix={rise}
          facing={f >= 125 ? -1 : 1}
          glasses
          brow={brow}
          mouth={interpolate(f, [40, 90], [-0.6, -0.15], EASE)}
        />
      )}
    </Stage>
  );
};

const RunA: React.FC = () => {
  const f = useCurrentFrame();
  return (
    <Stage>
      <CityScroll floor={FLOOR} speed={-14} />
      <Hero x={1000} y={FLOOR} pose="run" facing={-1} runPhase={f * 0.36} glasses brow={-0.5} mouth={-0.2} />
    </Stage>
  );
};

const RunB: React.FC = () => {
  const f = useCurrentFrame();
  const sx = interpolate(f, [0, 210], [1380, 2150], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const ss = interpolate(f, [0, 210], [1.7, 1.1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  return (
    <Stage>
      <CityScroll floor={FLOOR} speed={-24} seed="city2" moonX={520} />
      <Shadow x={sx} y={FLOOR} scale={ss} facing={-1} />
      <Hero x={860} y={FLOOR} pose="run" facing={-1} runPhase={f * 0.48} glasses brow={-0.85} mouth={-0.3} />
      <ShadowLine text="You'll crash again." x={sx} y={FLOOR - HERO_HEIGHT * ss - 28} from={30} to={130} anchor="middle" />
    </Stage>
  );
};

const TheFix: React.FC = () => (
  <Stage>
    <LaptopCU
      lines={[
        {at: 10, text: 'kernel/boot.asm', color: C.white, speed: 1.5},
        {at: 50, text: '-   mov esp, 0x7C00', color: C.error, speed: 1.1},
        {at: 95, text: '+   mov esp, 0x90000', color: C.led, speed: 1.1},
        {at: 150, text: '$ make', speed: 2},
        {at: 172, text: 'BUILD OK', color: C.led, speed: 99},
      ]}
    />
  </Stage>
);

const ItBoots: React.FC = () => {
  const f = useCurrentFrame();
  const hit = 112;
  const prog = clamp01((f - 40) / 60);
  return (
    <>
      <Stage>
        <LaptopCU
          glow={f >= hit ? C.led : C.screen}
          tint={f >= hit ? 0.05 : 0}
          lines={[
            {at: 5, text: '$ qemu heroos.img', speed: 1.6},
            {at: 26, text: 'Booting HeroOS...', color: C.white, speed: 1.4},
                        {at: hit, text: 'Hello from HeroOS!', color: C.led, speed: 99, size: 110, center: true, y: 680},
            {at: hit + 30, text: 'hero@heroos:~$', speed: 2, y: 860},
          ]}
        />
        {f >= 40 ? (
          <g>
            <rect x={300} y={470} width={1000} height={40} rx={8} fill="none" stroke={C.outline} strokeWidth={3} />
            <rect x={306} y={476} width={988 * prog} height={28} rx={5} fill={C.term} />
          </g>
        ) : null}
        <Marker x={960} y={650} rx={560} ry={105} from={hit + 8} />
      </Stage>
      <SpeedLines at={hit} dur={20} />
      <Flash at={[hit]} />
    </>
  );
};

const Celebrate: React.FC = () => {
  const f = useCurrentFrame();
  // surprise -> rises out of the chair -> slowly raises both arms. No hopping.
  const standMix = interpolate(f, [26, 66], [0, 1], EASE);
  const cheerMix = interpolate(f, [70, 104], [0, 1], EASE);
  const standing = f >= 68;
  const ss = interpolate(f, [40, 200], [1.2, 0.45], EASE);
  const so = interpolate(f, [120, 210], [1, 0], EASE) * (f > 40 && random(`c${f}`) < 0.2 ? 0.4 : 1);
  return (
    <Stage>
      <Room lamp={1} screen={1} screenColor={C.led} led={1} />
      <Shadow x={420} y={FLOOR} scale={ss} opacity={so} />
      <Hero
        x={HX}
        y={FLOOR}
        pose={standing ? 'stand' : 'sit'}
        pose2={standing ? 'cheer' : 'stand'}
        mix={standing ? cheerMix : standMix}
        glasses
        brow={interpolate(f, [0, 14, 60, 90], [0, 0.25, 0.25, 0.1], EASE)}
        browLift={interpolate(f, [0, 14, 70, 100], [0, 12, 12, 6], EASE)}
        mouthOpen={interpolate(f, [4, 16, 40, 56], [0, 0.7, 0.7, 0], EASE)}
        mouth={interpolate(f, [50, 70], [0, 1], EASE)}
      />
      <Marker x={HX + 10} y={FLOOR - 250} rx={170} ry={250} from={110} seed={7} />
      <ShadowLine text="...?" x={420} y={FLOOR - HERO_HEIGHT * ss - 24} from={60} to={150} anchor="middle" size={36} />
    </Stage>
  );
};

const NextLine: React.FC = () => {
  const f = useCurrentFrame();
  return (
    <Cam dur={240} push={[1, 1.1]} focus={[900, 600]}>
      <Stage>
        <Room lamp={1} screen={1} led={0.6 + 0.4 * Math.sin(f / 10)} />
        <Hero x={HX} y={FLOOR} pose="type" glasses brow={-0.25} mouth={0.45} typeSpeed={0.8} />
      </Stage>
    </Cam>
  );
};

// ---------------- the film ----------------

const SCENES: [number, number, React.FC][] = [
  [0, 210, Intro],
  [210, 150, TripleFault],
  [360, 210, FirstShadow],
  [570, 150, Glasses],
  [720, 540, Montage],
  [1260, 240, Grind],
  [1500, 150, KernelPanic],
  [1650, 240, RockBottom],
  [1890, 180, LastLed],
  [2070, 210, StandUp],
  [2280, 210, RunA],
  [2490, 210, RunB],
  [2700, 240, TheFix],
  [2940, 180, ItBoots],
  [3120, 240, Celebrate],
  [3360, 240, NextLine],
];

// The film itself, drawn in whatever look is active.
export const BootFilm: React.FC = () => (
  <AbsoluteFill style={{background: C.bg}}>
    {SCENES.map(([from, dur, Scene], i) => (
      <Sequence key={i} from={from} durationInFrames={dur} name={Scene.name || `Scene ${i + 1}`}>
        <Scene />
      </Sequence>
    ))}
    <Sequence from={3600} durationInFrames={360} name="Title card">
      <TitleCard word="BOOT." line="Every system starts with one instruction." accentLine="Write yours." />
    </Sequence>
    <Narrator lines={NARRATOR} />
    <RepPops pops={POPS} />
    <DayCounter days={DAYS} hideAt={3600} />
    <Letterbox />
    <BootSound />
  </AbsoluteFill>
);

// The channel version: the dark documentary look.
export const Boot: React.FC = () => {
  applyLook(LOOKS.documentary);
  return (
    <LookFx look="documentary">
      <BootFilm />
    </LookFx>
  );
};

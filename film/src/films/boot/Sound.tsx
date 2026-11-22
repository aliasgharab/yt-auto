import React from 'react';
import {Audio} from '@remotion/media';
import {staticFile} from 'remotion';

// All sound for BOOT. is generated in code by scripts/make_sounds.py.
// Cue = [global frame, file, volume, optional duration in frames]
type Cue = [number, string, number, number?];

const sfx = (name: string) => staticFile(`sfx/${name}.wav`);

const steps = (from: number, to: number, every: number, vol: number): Cue[] =>
  Array.from({length: Math.floor((to - from) / every)}, (_, i) => [Math.round(from + i * every), 'footstep', vol] as Cue);

const CUES: Cue[] = [
  // Intro + first attempt
  [0, 'typing_slow', 0.35, 210],
  [215, 'typing_fast', 0.3, 80],
  [310, 'impact', 0.55],
  [310, 'error_buzz', 0.35],
  [262, 'pop', 0.5],
  // Shadow appears
  [380, 'shadow_swell', 0.55],
  [440, 'glitch', 0.25],
  // Day 2 + glasses
  [570, 'day', 0.5],
  // Montage: one sound per 1-second shot, plus build pops
  ...Array.from({length: 18}, (_, i): Cue[] => {
    const at = 720 + i * 30;
    const kind = i % 6;
    const shot: Cue[] =
      kind === 0
        ? [[at + 8, 'error_buzz', 0.3]]
        : kind === 1
          ? [[at, 'beep', 0.3], [at + 10, 'beep', 0.3], [at + 20, 'beep', 0.3]]
          : kind === 2
            ? [[at, 'typing_fast', 0.4, 30]]
            : kind === 4
              ? [[at, 'glitch', 0.15]]
              : [];
    return [...shot, [at + 6, 'pop', 0.4]];
  }).flat(),
  // Grind: fast typing, error buzz every time the screen flips red
  [1260, 'typing_fast', 0.35, 240],
  [1260, 'day', 0.5],
  ...Array.from({length: 5}, (_, i): Cue => [1284 + i * 48, 'error_buzz', 0.22]),
  ...Array.from({length: 8}, (_, i): Cue => [1290 + i * 24, 'pop', 0.35]),
  [1300, 'shadow_swell', 0.4],
  // Kernel panic
  [1500, 'typing_fast', 0.3, 30],
  [1545, 'impact', 0.6],
  [1545, 'error_buzz', 0.35],
  [1550, 'glitch', 0.4],
  // Rock bottom
  [1650, 'day', 0.4],
  [1700, 'shadow_swell', 0.6],
  // The LED blinks (period 45)
  ...[1890, 1935, 1980, 2025].map((f): Cue => [f, 'beep', 0.22]),
  // Stand up, Shadow flickers, run out
  [2120, 'whoosh', 0.3],
  [2134, 'glitch', 0.3],
  ...steps(2220, 2275, 7.5, 0.5),
  // Run A and B
  [2280, 'day', 0.4],
  ...steps(2280, 2490, 8.7, 0.45),
  [2490, 'day', 0.4],
  ...steps(2490, 2700, 6.5, 0.5),
  [2510, 'shadow_swell', 0.35],
  // The fix
  [2700, 'day', 0.4],
  [2710, 'typing_slow', 0.35, 150],
  [2850, 'typing_fast', 0.3, 25],
  [2870, 'pop', 0.5],
  [2872, 'beep', 0.35],
  // It boots
  [2945, 'typing_fast', 0.3, 25],
  [3052, 'impact', 0.4],
  [3052, 'success', 0.55],
  // Celebrate
  [3160, 'pop', 0.5],
  [3186, 'footstep', 0.4],
  [3190, 'whoosh', 0.25],
  [3250, 'glitch', 0.12],
  // Next line
  [3360, 'typing_slow', 0.3, 240],
  // Title card: one tick per letter of "BOOT.", whoosh on the underline
  ...Array.from({length: 5}, (_, i): Cue => [3620 + i * 9, 'type_tick', 0.6]),
  [3668, 'whoosh', 0.35],
];

export const BootSound: React.FC = () => (
  <>
    <Audio name="Score" src={sfx('boot_score')} volume={0.75} />
    {CUES.map(([from, name, volume, dur], i) => (
      <Audio key={i} name={name} src={sfx(name)} from={from} volume={volume} durationInFrames={dur} />
    ))}
  </>
);

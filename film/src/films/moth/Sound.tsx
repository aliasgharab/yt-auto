import React from 'react';
import {Audio} from '@remotion/media';
import {staticFile} from 'remotion';
import voice from '../../../public/voice/moth.json';

// All audio here is generated in code (scripts/make_sounds.py, scripts/make_voice.py).
const VOICE_AT = 20;
const lineAt = (n: number) => voice.lines[n - 1].startFrame + VOICE_AT;
const lineEnd = (n: number) => voice.lines[n - 1].endFrame + VOICE_AT;
const sfx = (name: string) => staticFile(`sfx/${name}.wav`);

type Cue = [number, string, number, number?];

// Music ducks ~10 dB under the narrator and swells back in the pauses.
const speaking = voice.lines.map((l) => [l.startFrame + VOICE_AT, l.endFrame + VOICE_AT] as const);
const duck = (f: number) => {
  let near = Infinity;
  for (const [a, b] of speaking) {
    if (f >= a && f <= b) return 0.32;
    near = Math.min(near, Math.abs(f - a), Math.abs(f - b));
  }
  return 0.32 + 0.68 * Math.min(1, near / 10);
};

const every = (from: number, to: number, step: number, name: string, vol: number): Cue[] =>
  Array.from({length: Math.max(0, Math.floor((to - from) / step))}, (_, i) => [Math.round(from + i * step), name, vol] as Cue);

const S = (n: number) => lineAt(n) - 6; // shot start
const MARK = 0.3; // marker pen squeak

const CUES: Cue[] = [
  // cold open
  [0, 'relay_bank', 0.18, S(2)],
  [50, 'flutter', 0.3],
  [S(2) + 4, 'flutter', 0.22],
  [S(2) + 40, 'marker', MARK],
  [S(4), 'page', 0.3],
  [lineAt(5) + 10, 'marker', MARK],
  [S(6), 'relay_bank', 0.2, S(7) - S(6)],
  [S(7), 'typing_fast', 0.15, 50],
  [lineAt(8), 'typing_fast', 0.15, 34],
  [lineAt(8) + 42, 'marker', MARK],
  [lineEnd(8) + 8, 'stamp', 0.3],
  // part I: the machine
  [S(10), 'relay_bank', 0.22, S(12) - S(10)],
  [lineAt(12) + 6, 'marker', 0.35],
  [lineAt(12) + 36, 'marker', 0.35],
  [lineAt(12) + 66, 'marker', 0.35],
  [S(13), 'relay_bank', 0.32, S(14) - S(13)],
  ...every(S(14) + 10, S(15), 22, 'relay', 0.4),
  [S(15), 'relay_bank', 0.1, S(16) - S(15)],
  [lineAt(16) - 20, 'pen', 0.35],
  [lineAt(16) + 10, 'pen', 0.35],
  [lineAt(16) + 40, 'pen', 0.35],
  [lineAt(17) + 20, 'marker', MARK],
  [lineEnd(17) + 8, 'stamp', 0.3],
  // part II: the hunt
  ...every(S(18), S(19), 20, 'error_buzz', 0.12),
  ...every(S(19) + 8, S(20), 16, 'footstep', 0.18),
  ...every(S(20) + 60, S(21), 30, 'tick', 0.4),
  [S(20) + 2, 'tick', 0.4],
  [lineAt(21) + 34, 'marker', MARK],
  ...every(S(22) + 12, S(24), 40, 'relay_stuck', 0.35),
  [lineAt(22) + 14, 'marker', MARK],
  [S(24) + 14, 'tweezer', 0.5],
  [S(24) + Math.floor((S(25) - S(24)) * 0.45) + 30, 'tape', 0.45],
  [S(24) + Math.floor((S(25) - S(24)) * 0.45) + 45, 'tape', 0.4],
  [S(25) + 8, 'pen', 0.4],
  [S(25) + 50, 'pen', 0.35],
  [lineAt(26) + 16, 'marker', MARK],
  [lineEnd(26) + 8, 'stamp', 0.3],
  // part III: the twist
  [S(27), 'page', 0.3],
  [S(27) + 50, 'marker', MARK],
  [S(28) + 20, 'pen', 0.3],
  [S(29) + 10, 'whoosh', 0.2],
  [lineAt(31) + 14, 'marker', MARK],
  // part IV: the storyteller
  [lineEnd(33) - 40, 'applause', 0.25],
  [lineAt(35), 'marker', 0.4],
  [lineAt(35) + 14, 'marker', 0.4],
  // what happened next
  ...every(S(38) + 20, S(39) - 40, 8, 'tick', 0.12),
  [S(39), 'error_buzz', 0.2],
  [S(39) + 44, 'glitch', 0.3],
  [S(39) + 88, 'beep', 0.2],
  [S(40), 'relay_bank', 0.12, lineAt(41) + 40 - S(40)],
  [lineAt(41) + 20, 'relay', 0.4],
  [lineAt(41) + 60, 'marker', 0.25],
];

export const MothSound: React.FC = () => (
  <>
    <Audio name="Narration" src={staticFile('voice/moth.wav')} from={VOICE_AT} volume={1} />
    <Audio name="Score" src={sfx('moth_score')} volume={(f) => 0.6 * duck(f)} />
    {CUES.map(([from, name, volume, dur], i) => (
      <Audio key={i} name={name} src={sfx(name)} from={from} volume={volume} durationInFrames={dur} />
    ))}
  </>
);

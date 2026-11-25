import React from 'react';
import {Audio} from '@remotion/media';
import {staticFile} from 'remotion';
import voice from '../../../public/voice/taumsauk.json';

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
  [0, 'night', 0.25, S(2)],
  [S(2) - 50, 'trickle', 0.3, 56],
  [S(2) + 40, 'water_rush', 0.18, S(3) - S(2) - 40],
  ...every(S(2) + 40, S(3) - 4, 8, 'tick', 0.12),
  [S(3), 'night', 0.18, S(4) - S(3)],
  [S(4) + 14, 'beep', 0.15],
  [S(6), 'pump_hum', 0.18, S(8) - S(6) + 40],
  [lineAt(7) + 12, 'marker', MARK],
  [lineEnd(7) + 8, 'stamp', 0.3],
  // part I: the battery
  [S(9), 'pump_hum', 0.25, lineAt(10) - S(9)],
  [lineAt(10) - 10, 'whoosh', 0.2],
  [lineAt(10), 'water_rush', 0.14, S(11) - lineAt(10)],
  [S(11) + 30, 'pen', 0.3],
  [S(12), 'page', 0.25],
  [S(13), 'pump_hum', 0.2, lineAt(14) + 58 - S(13)],
  [lineAt(14) + 58, 'relay', 0.5],
  [lineEnd(14) + 8, 'stamp', 0.3],
  // part II: the gauges
  [S(16) + 16, 'creak', 0.4],
  [S(16) + 60, 'marker', MARK],
  [lineAt(17) + 6, 'creak', 0.3],
  [lineAt(17) + 40, 'marker', MARK],
  [lineAt(19), 'pen', 0.35],
  [S(20) + 16, 'tick', 0.3],
  [S(20) + 22, 'tick', 0.3],
  [lineAt(21) + 10, 'pen', 0.3],
  [lineAt(22) + 20, 'marker', MARK],
  ...every(S(23) + 4, S(23) + 44, 10, 'pen', 0.18),
  [lineEnd(23) + 8, 'stamp', 0.3],
  // part III: the night
  [S(25), 'pump_hum', 0.2, lineAt(27) - S(25)],
  [S(25) + 6, 'pen', 0.2],
  [lineAt(27) - 4, 'glitch', 0.25],
  [lineAt(27) + 24, 'marker', MARK],
  [S(28), 'trickle', 0.4, S(29) - S(28)],
  [S(29), 'trickle', 0.35, 52],
  [lineAt(29) + 46, 'rumble', 0.6],
  [lineAt(29) + 52, 'impact', 0.35],
  [lineAt(29) + 60, 'water_rush', 0.45, S(30) - lineAt(29) - 60],
  [S(30), 'water_rush', 0.5, S(31) - S(30)],
  [S(30), 'rumble', 0.3],
  [S(31), 'water_rush', 0.18, S(32) - S(31)],
  [S(32) - 30, 'marker', MARK],
  [S(32), 'page', 0.3],
  [S(33) + 10, 'water_rush', 0.45, S(34) - S(33) - 10],
  [S(33) + 60, 'creak', 0.45],
  [S(34), 'trickle', 0.12, S(36) - S(34)],
  // aftermath
  [S(36), 'page', 0.3],
  [S(36) + 6, 'typing_slow', 0.15, 50],
  [lineAt(36) + 40, 'marker', MARK],
  ...every(S(37) + 6, lineAt(37) + 64, 4, 'tick', 0.1),
  [lineAt(37) + 80, 'whoosh', 0.18],
  [S(38), 'pump_hum', 0.12, TITLE_FRAMES()],
  [lineAt(39) - 6, 'glitch', 0.25],
  [lineAt(39) + 30, 'marker', MARK],
];

function TITLE_FRAMES() {
  return Math.round(voice.duration * 30) + VOICE_AT + 20 - S(38);
}

export const TaumsaukSound: React.FC = () => (
  <>
    <Audio name="Narration" src={staticFile('voice/taumsauk.wav')} from={VOICE_AT} volume={1} />
    <Audio name="Score" src={sfx('taumsauk_score')} volume={(f) => 0.6 * duck(f)} />
    {CUES.map(([from, name, volume, dur], i) => (
      <Audio key={i} name={name} src={sfx(name)} from={from} volume={volume} durationInFrames={dur} />
    ))}
  </>
);

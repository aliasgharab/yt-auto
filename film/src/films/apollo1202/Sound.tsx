import React from 'react';
import {Audio} from '@remotion/media';
import {staticFile} from 'remotion';
import voice from '../../../public/voice/apollo1202.json';

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
const MARK = 0.28; // marker pen squeak
const CH1 = lineEnd(9) + 6;
const CH2 = lineEnd(15) + 6;
const CH3 = lineEnd(23) + 6;
const CONTACT = lineEnd(31) + 2;

const CUES: Cue[] = [
  // cold open: the engine under everything until the alarm
  [0, 'descent_engine', 0.22, 300],
  [300, 'descent_engine', 0.2, S(4) - 300 + 20],
  [S(2) + 76, 'beep', 0.12],
  [lineAt(4) + 22, 'alarm_tone', 0.3],
  [lineAt(4) + 66, 'beep', 0.12],
  [lineAt(5) + 2, 'marker', MARK],
  // the transcript: radio keyed with Quindar tones
  [S(6) + 26, 'quindar_in', 0.18],
  [S(6) + 30, 'typing_slow', 0.18, 80],
  [S(6) + 84, 'quindar_out', 0.15],
  [S(6) + 112, 'marker', MARK],
  [S(7), 'descent_engine', 0.14, S(8) - S(7)],
  [S(7) + 8, 'alarm_tone', 0.18],
  ...every(S(8) + 8, S(8) + 70, 5, 'tick', 0.08),
  [S(9), 'room_tone', 0.3, 240],
  [S(9) + 78, 'alarm_tone', 0.08],
  // part I
  [CH1, 'whoosh', 0.18],
  [CH1 + 60, 'pump_hum', 0.08, S(11) - CH1 - 60],
  ...every(S(11) + 4, S(11) + 56, 4, 'tick', 0.06),
  [S(12) + 4, 'pen', 0.3, 80],
  [S(13), 'descent_engine', 0.16, S(14) - S(13)],
  [S(13) + 30, 'marker', MARK],
  [S(14) + 10, 'page', 0.3],
  [S(15), 'typing_slow', 0.16, 40],
  [S(15) + 38, 'marker', MARK],
  // part II
  [CH2, 'whoosh', 0.18],
  [lineAt(17) + 8, 'switch_click', 0.4],
  [lineAt(17) + 8, 'marker', MARK],
  [lineAt(17) + 50, 'data_stream', 0.16, S(18) - lineAt(17) - 50],
  [S(18), 'data_stream', 0.1, S(21) - S(18)],
  ...every(lineAt(18) + 6, lineAt(19) + 26, 7, 'tick', 0.1),
  [lineAt(20) + 30, 'error_buzz', 0.22],
  [lineAt(21) + 14, 'glitch', 0.2],
  [lineAt(21) + 52, 'whoosh', 0.15],
  [lineAt(21) + 96, 'beep', 0.1],
  [S(22) + 4, 'alarm_tone', 0.1],
  [lineAt(22) + 26, 'stamp', 0.4],
  [lineAt(23) + 44, 'pen', 0.25, 60],
  // part III
  [CH3, 'whoosh', 0.18],
  [CH3 + 60, 'room_tone', 0.28, S(26) - CH3 - 60],
  [CH3 + 80, 'quindar_in', 0.12],
  [S(26) + 4, 'pen', 0.22, 40],
  [S(26) + 34, 'marker', MARK],
  [S(27), 'room_tone', 0.25, S(28) - S(27)],
  [lineAt(27) + 46, 'quindar_in', 0.15],
  [S(28), 'descent_engine', 0.14, S(29) - S(28)],
  [S(28) + 60, 'alarm_tone', 0.16],
  [S(28) + 95, 'alarm_tone', 0.16],
  [S(28) + 132, 'alarm_tone', 0.16],
  [S(29), 'descent_engine', 0.2, S(31) - S(29)],
  [lineAt(29) + 84, 'marker', MARK],
  [S(30) + 36, 'switch_click', 0.35],
  [S(30) + 50, 'thruster', 0.25],
  [S(30) + 68, 'thruster', 0.2],
  [S(31), 'descent_engine', 0.22, CONTACT - S(31)],
  ...every(S(31) + 50, CONTACT - 4, 14, 'beep', 0.07),
  [CONTACT, 'impact', 0.22],
  // what happened next
  [S(33) + 20, 'applause', 0.1],
  [S(33) + 44, 'marker', MARK],
  [S(34), 'typing_slow', 0.12, 60],
  [S(34) + 56, 'marker', MARK],
];

export const Apollo1202Sound: React.FC = () => (
  <>
    <Audio name="Narration" src={staticFile('voice/apollo1202.wav')} from={VOICE_AT} volume={1} />
    <Audio name="Score" src={sfx('apollo1202_score')} volume={(f) => 0.6 * duck(f)} />
    {CUES.map(([from, name, volume, dur], i) => (
      <Audio key={i} name={name} src={sfx(name)} from={from} volume={volume} durationInFrames={dur} />
    ))}
  </>
);

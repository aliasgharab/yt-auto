import React from 'react';
import {Audio} from '@remotion/media';
import {staticFile} from 'remotion';
import voice from '../../../public/voice/enigma.json';

// All audio here is generated in code (scripts/make_sounds.py, scripts/make_voice.py).
const VOICE_AT = 20;
const lineAt = (n: number) => voice.lines[n - 1].startFrame + VOICE_AT;
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
  // ease back up over ~10 frames after a line ends
  return 0.32 + 0.68 * Math.min(1, near / 10);
};

const ticks = (from: number, to: number, every: number, vol: number): Cue[] =>
  Array.from({length: Math.max(0, Math.floor((to - from) / every))}, (_, i) => [Math.round(from + i * every), 'tick', vol] as Cue);

const CUES: Cue[] = [
  // cold open
  [lineAt(1), 'typing_slow', 0.25, lineAt(2) - lineAt(1)],
  [lineAt(2) - 6, 'stamp', 0.45],
  [lineAt(2) + 20, 'stamp', 0.4],
  [lineAt(2) + 46, 'stamp', 0.4],
  [lineAt(3) + 22, 'type_tick', 0.7],
  [lineAt(3) + 24, 'beep', 0.18],
  [lineAt(4) + 20, 'type_tick', 0.7],
  [lineAt(4) + 22, 'beep', 0.18],
  ...ticks(lineAt(6) - 6, lineAt(6) + 50, 15, 0.45),
  [lineAt(6) + 50, 'impact', 0.35],
  [lineAt(7) - 6, 'typing_fast', 0.2, 40],
  [lineAt(8) + 30, 'whoosh', 0.3],
  [lineAt(10) + 6, 'glitch', 0.2],
  // the Atlantic
  [lineAt(11), 'sonar', 0.4],
  [lineAt(12) + 10, 'sonar', 0.35],
  [lineAt(13) + 18, 'impact', 0.25],
  [lineAt(13) + 40, 'impact', 0.22],
  [lineAt(13) + 60, 'impact', 0.22],
  [lineAt(15) - 6, 'morse', 0.35],
  [lineAt(16), 'morse', 0.18],
  [lineAt(17) + 30, 'stamp', 0.3],
  // Bletchley
  ...Array.from({length: 14}, (_, i): Cue => [lineAt(18) + 8 + i * 15, 'footstep', 0.15]),
  [lineAt(20) + 20, 'day', 0.35],
  [lineAt(21) + 20, 'chain', 0.45],
  [lineAt(21) + 70, 'chain', 0.3],
  [lineAt(22) + 30, 'shadow_swell', 0.35],
  [lineAt(23) - 6, 'chalk', 0.5],
  [lineAt(23) + 50, 'chalk', 0.45],
  [lineAt(24), 'chalk', 0.45],
  // the struggle
  [lineAt(25) - 6, 'bombe', 0.3, lineAt(27) - lineAt(25)],
  [lineAt(26) + 10, 'shadow_swell', 0.3],
  [lineAt(27) - 6, 'bombe', 0.45, 30],
  [lineAt(27) - 2, 'pop', 0.3],
  [lineAt(27) + 24, 'pop', 0.3],
  ...ticks(lineAt(27) + 50, lineAt(28) - 6, 6, 0.35),
  [lineAt(28) - 6, 'bombe', 0.15, lineAt(29) - lineAt(28)],
  [lineAt(28) + 20, 'shadow_swell', 0.45],
  // the flaw
  [lineAt(30) + 20, 'stamp', 0.5],
  [lineAt(31) + 50, 'stamp', 0.5],
  [lineAt(32) - 6, 'typing_slow', 0.2, lineAt(33) - lineAt(32)],
  [lineAt(34), 'whoosh', 0.2],
  // the breakthrough
  [lineAt(36) - 6, 'bombe', 0.4, lineAt(37) - lineAt(36) - 4],
  [lineAt(37) - 6, 'impact', 0.4],
  [lineAt(37) - 6, 'success', 0.5],
  [lineAt(37) - 4, 'pop', 0.4],
  [lineAt(38), 'sonar', 0.25],
  [lineAt(39), 'stamp', 0.4],
];

export const EnigmaSound: React.FC = () => (
  <>
    <Audio name="Narration" src={staticFile('voice/enigma.wav')} from={VOICE_AT} volume={1} />
    <Audio name="Score" src={sfx('enigma_score')} volume={(f) => 0.6 * duck(f)} />
    {CUES.map(([from, name, volume, dur], i) => (
      <Audio key={i} name={name} src={sfx(name)} from={from} volume={volume} durationInFrames={dur} />
    ))}
  </>
);

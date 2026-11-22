import React from 'react';
import {AbsoluteFill, CalculateMetadataFunction, Easing, interpolate, Sequence, staticFile, useCurrentFrame} from 'remotion';
import {Audio, Video} from '@remotion/media';
import {applyLook, C, LOOK} from '../../theme';
import {LOOKS} from '../../looks';
import {LookFx} from '../../components/LookFx';
import {Marker} from '../../components/Primitives';
import {TitleCard} from '../../components/TitleCard';
import {CHANNEL} from '../brand/Brand';

// Re-cuts of finished films (rendered by yt-auto from a film's video.mp4, copied into public/cuts/):
//   ShortCut    — 1080x1920 teaser of a film's cold open, ending on its cliffhanger + "full story" card
//   Compilation — 8-10 min long-form: voiced intro, chapter cards, 3-4 films (their title cards trimmed), outro

const CL = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;
const EASE = {...CL, easing: Easing.inOut(Easing.cubic)} as const;

type CapLine = {text: string; start: number; end: number}; // frames, relative to the cut

// ---------------------------------------------------------------- Short
export type ShortProps = {src: string; from: number; to: number; hook: string; lines: CapLine[]};
export const SHORT_END = 75; // end card frames

export const shortMetadata: CalculateMetadataFunction<ShortProps> = ({props}) => ({
  durationInFrames: props.to - props.from + SHORT_END,
});

const EndCard: React.FC = () => {
  const f = useCurrentFrame();
  const o = interpolate(f, [0, 10], [0, 1], CL);
  return (
    <AbsoluteFill style={{background: C.bgDark, opacity: o, alignItems: 'center', justifyContent: 'center'}}>
      <svg width={1080} height={1920} viewBox="0 0 1080 1920" style={{position: 'absolute', inset: 0}}>
        <text x={540} y={820} textAnchor="middle" fontFamily={LOOK.font} fontWeight={700} fontSize={64} fill="#B8B8BE" letterSpacing={4}>
          FULL STORY ON THE CHANNEL
        </text>
        <text x={540} y={1060} textAnchor="middle" fontFamily={LOOK.display} fontSize={200} fill={C.white} letterSpacing={8}>
          {CHANNEL.name}
        </text>
        <Marker x={540} y={985} rx={370} ry={140} from={8} seed={2} />
      </svg>
    </AbsoluteFill>
  );
};

export const ShortCut: React.FC<ShortProps> = ({src, from, to, hook, lines}) => {
  applyLook(LOOKS.documentary);
  const f = useCurrentFrame();
  const len = to - from;
  const line = lines.find((l) => f >= l.start && f <= l.end + 6);
  const hookIn = interpolate(f, [0, 12], [0, 1], CL);
  // no LookFx here: its overlays are sized for 16:9, and the film footage already carries grain + vignette
  return (
    <>
      <AbsoluteFill style={{background: C.bgDark}}>
        {/* hook headline */}
        <div style={{position: 'absolute', top: 120, height: 470, left: 60, right: 60, display: 'flex', flexDirection: 'column', justifyContent: 'flex-end', alignItems: 'center', opacity: hookIn}}>
          <div style={{textAlign: 'center', fontFamily: LOOK.display, fontSize: 104, lineHeight: 1.05, color: C.white, letterSpacing: 2, textTransform: 'uppercase'}}>{hook}</div>
          <div style={{marginTop: 26, width: 400 * hookIn, height: 8, background: C.accent, boxShadow: `0 0 12px ${C.accent}`}} />
        </div>
        {/* the film, 1.25x, centre-cropped */}
        <div style={{position: 'absolute', top: 620, left: 0, width: 1080, height: 760, overflow: 'hidden'}}>
          <Sequence durationInFrames={len} layout="none">
            <Video
              src={staticFile(src)}
              trimBefore={from}
              trimAfter={to}
              volume={(v) => interpolate(v, [len - 12, len], [1, 0], CL)}
              style={{position: 'absolute', width: 1350, height: 760, left: -135, top: 0}}
            />
          </Sequence>
        </div>
        {/* narration captions */}
        {line ? (
          <div style={{position: 'absolute', top: 1450, left: 70, right: 70, textAlign: 'center', fontFamily: LOOK.font, fontWeight: 700, fontSize: 70, lineHeight: 1.2, color: C.white, textTransform: 'uppercase', letterSpacing: 2}}>
            {line.text}
          </div>
        ) : null}
        <Sequence from={len} durationInFrames={SHORT_END}>
          <EndCard />
          <Audio src={staticFile('sfx/impact.wav')} volume={0.35} />
        </Sequence>
      </AbsoluteFill>
    </>
  );
};

// ---------------------------------------------------------------- Compilation
export type Segment = {src: string; label: string; frames: number};
export type CompProps = {
  title: string; // e.g. "4 Bugs That Cost Billions"
  introVoice: string | null; // public path of the voiced intro, e.g. "voice/comp202612.wav"
  introFrames: number;
  introLines: CapLine[];
  segments: Segment[];
  card: {word: string; line: string; accent: string};
};
export const CHAPTER = 60;
export const OUTRO = 360;

export const compMetadata: CalculateMetadataFunction<CompProps> = ({props}) => ({
  durationInFrames: props.introFrames + props.segments.reduce((a, s) => a + CHAPTER + s.frames, 0) + OUTRO,
});

const ROMAN = ['I', 'II', 'III', 'IV', 'V', 'VI'];

const Intro: React.FC<{title: string; lines: CapLine[]; labels: string[]}> = ({title, lines, labels}) => {
  const f = useCurrentFrame();
  const line = lines.find((l) => f >= l.start && f <= l.end + 6);
  return (
    <AbsoluteFill style={{background: C.bgDark, alignItems: 'center', justifyContent: 'center'}}>
      <div style={{fontFamily: LOOK.display, fontSize: 150, color: C.white, letterSpacing: 4, opacity: interpolate(f, [10, 30], [0, 1], CL), textTransform: 'uppercase'}}>
        {title}
      </div>
      <div style={{display: 'flex', gap: 60, marginTop: 50}}>
        {labels.map((l, i) => (
          <div key={i} style={{fontFamily: LOOK.font, fontWeight: 700, fontSize: 40, letterSpacing: 3, color: i % 2 ? '#B8B8BE' : C.accent, opacity: interpolate(f, [40 + i * 12, 55 + i * 12], [0, 1], CL), textTransform: 'uppercase'}}>
            {ROMAN[i]}. {l}
          </div>
        ))}
      </div>
      {line ? (
        <div style={{position: 'absolute', bottom: 110, left: 200, right: 200, textAlign: 'center', fontFamily: LOOK.font, fontWeight: 700, fontSize: 44, color: '#D8D8DC', letterSpacing: 2, textTransform: 'uppercase'}}>
          {line.text}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};

const Chapter: React.FC<{n: number; label: string}> = ({n, label}) => {
  const f = useCurrentFrame();
  const o = interpolate(f, [0, 10, CHAPTER - 10, CHAPTER], [0, 1, 1, 0], CL);
  const y = interpolate(f, [0, 14], [20, 0], EASE);
  return (
    <AbsoluteFill style={{background: C.bgDark, alignItems: 'center', justifyContent: 'center', opacity: o}}>
      <div style={{fontFamily: LOOK.font, fontWeight: 700, fontSize: 56, color: C.accent, letterSpacing: 8, translate: `0px ${y}px`}}>PART {ROMAN[n]}</div>
      <div style={{fontFamily: LOOK.display, fontSize: 130, color: C.white, letterSpacing: 4, marginTop: 10, textTransform: 'uppercase', translate: `0px ${y}px`}}>{label}</div>
    </AbsoluteFill>
  );
};

export const Compilation: React.FC<CompProps> = ({title, introVoice, introFrames, introLines, segments, card}) => {
  applyLook(LOOKS.documentary);
  let at = introFrames;
  const parts = segments.map((s, i) => {
    const chapterAt = at;
    const videoAt = at + CHAPTER;
    at = videoAt + s.frames;
    return (
      <React.Fragment key={i}>
        <Sequence from={chapterAt} durationInFrames={CHAPTER} name={`Part ${ROMAN[i]}`}>
          <Chapter n={i} label={s.label} />
          <Audio src={staticFile('sfx/whoosh.wav')} volume={0.25} />
        </Sequence>
        <Sequence from={videoAt} durationInFrames={s.frames} name={s.label}>
          <Video src={staticFile(s.src)} trimAfter={s.frames} />
        </Sequence>
      </React.Fragment>
    );
  });
  return (
    <LookFx look="documentary">
      <AbsoluteFill style={{background: C.bgDark}}>
        <Sequence durationInFrames={introFrames} name="Intro">
          <Intro title={title} lines={introLines} labels={segments.map((s) => s.label)} />
          {introVoice ? <Audio src={staticFile(introVoice)} volume={1} /> : null}
          <Audio src={staticFile('sfx/shadow_swell.wav')} volume={0.2} />
        </Sequence>
        {parts}
        <Sequence from={at} durationInFrames={OUTRO} name="Title card">
          <TitleCard word={card.word} line={card.line} accentLine={card.accent} />
        </Sequence>
      </AbsoluteFill>
    </LookFx>
  );
};

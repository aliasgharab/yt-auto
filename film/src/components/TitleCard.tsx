import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import {C, LOOK} from '../theme';

// Last 12 seconds (360 frames): one word types on, wavy accent underline,
// one white line, one short accent line, fade to black.
export const TitleCard: React.FC<{word: string; line: string; accentLine: string}> = ({word, line, accentLine}) => {
  const f = useCurrentFrame();
  const typeStart = 20;
  const perLetter = 9;
  const shown = Math.max(0, Math.min(word.length, Math.floor((f - typeStart) / perLetter) + 1));
  const typedEnd = typeStart + perLetter * word.length;
  const underline = interpolate(f, [typedEnd + 4, typedEnd + 34], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const lineO = interpolate(f, [150, 170], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const accentO = interpolate(f, [205, 225], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const fade = interpolate(f, [300, 350], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const cursorOn = f < typedEnd + 30 && Math.floor(f / 8) % 2 === 0;

  // Wavy underline path that keeps gently moving.
  const wW = 760;
  const pts: string[] = [];
  for (let i = 0; i <= 60; i++) {
    const x = (i / 60) * wW;
    const y = Math.sin(i * 0.55 + f * 0.12) * 9;
    pts.push(`${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`);
  }

  return (
    <AbsoluteFill style={{background: C.bgDark, alignItems: 'center', justifyContent: 'center', fontFamily: LOOK.font}}>
      <div style={{position: 'relative', textAlign: 'center', translate: '0px -40px'}}>
        <div style={{fontFamily: LOOK.display, fontSize: 230, fontWeight: 700, color: C.white, letterSpacing: 6, lineHeight: 1, textTransform: LOOK.uppercase ? 'uppercase' : undefined}}>
          {word.split('').map((ch, i) => {
            const g = f - (typeStart + i * perLetter);
            // the cursor sits right after the last typed letter (hidden letters keep their space)
            const cursorHere = i === Math.min(shown, word.length) - 1 || (shown <= 0 && i === 0);
            const cursor = <span key={'c' + i} style={{display: 'inline-block', width: 14, height: 180, marginLeft: 10, background: C.white, opacity: cursorOn ? 1 : 0, verticalAlign: 'middle'}} />;
            return (
              <React.Fragment key={i}>
              {shown <= 0 && i === 0 ? cursor : null}
              <span
                key={i}
                style={{
                  display: 'inline-block',
                  opacity: i < shown ? 1 : 0,
                  scale: i < shown ? String(interpolate(g, [0, 6], [0.92, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})) : '0',
                }}
              >
                {ch}
              </span>
              {cursorHere && shown > 0 ? cursor : null}
              </React.Fragment>
            );
          })}
        </div>
        <svg width={wW + 20} height={40} viewBox={`-10 -20 ${wW + 20} 40`} style={{display: 'block', margin: '10px auto 0'}}>
          <path
            d={pts.join(' ')}
            stroke={C.accent}
            strokeWidth={9}
            fill="none"
            strokeLinecap="round"
            pathLength={1}
            strokeDasharray={1}
            strokeDashoffset={1 - underline}
            style={{filter: `drop-shadow(0 0 10px ${C.accent})`}}
          />
        </svg>
        <div style={{marginTop: 44, fontSize: 50, fontWeight: 700, color: C.white, opacity: lineO, translate: `0px ${(1 - lineO) * 10}px`}}>
          {line}
        </div>
        <div style={{marginTop: 18, fontSize: 44, fontWeight: 700, color: C.accent, opacity: accentO, translate: `0px ${(1 - accentO) * 10}px`}}>
          {accentLine}
        </div>
      </div>
      <AbsoluteFill style={{background: '#000', opacity: fade}} />
    </AbsoluteFill>
  );
};

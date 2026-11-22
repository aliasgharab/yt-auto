import React from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {BAR, C} from '../theme';
import {LookName} from '../looks';

// Whole-frame post effects for each look (SVG filters + overlays).
export const LookFx: React.FC<{look: LookName; children: React.ReactNode}> = ({look, children}) => {
  const f = useCurrentFrame();
  const id = `fx-${look}`;
  let filter: React.ReactNode = null;

  if (look === 'pixel') {
    const B = 5; // pixel size (Press Start 2P at 40px = 5px per font pixel, so text stays crisp)
    filter = (
      <filter id={id} x="0" y="0" width="1920" height="1080" filterUnits="userSpaceOnUse" primitiveUnits="userSpaceOnUse" colorInterpolationFilters="sRGB">
        <feFlood x={B / 2 - 1} y={B / 2 - 1} width="2" height="2" />
        <feComposite width={B} height={B} />
        <feTile result="grid" />
        <feComposite in="SourceGraphic" in2="grid" operator="in" />
        <feMorphology operator="dilate" radius={B / 2} />
      </filter>
    );
  } else if (look === 'neon') {
    filter = (
      <filter id={id} x="0" y="0" width="100%" height="100%" colorInterpolationFilters="sRGB">
        <feGaussianBlur in="SourceGraphic" stdDeviation="4" result="b1" />
        <feGaussianBlur in="SourceGraphic" stdDeviation="16" result="b2" />
        <feComposite in="SourceGraphic" in2="b1" operator="arithmetic" k1="0" k2="1" k3="0.55" k4="0" result="g1" />
        <feComposite in="g1" in2="b2" operator="arithmetic" k1="0" k2="1" k3="0.9" k4="0" />
      </filter>
    );
  } else if (look === 'chalk') {
    const boil = Math.floor(f / 4); // re-draw texture every 4 frames, like hand-drawn boil
    filter = (
      <filter id={id} x="0" y="0" width="100%" height="100%" colorInterpolationFilters="sRGB">
        <feTurbulence type="fractalNoise" baseFrequency="0.03" numOctaves="2" seed={boil} result="warp" />
        <feDisplacementMap in="SourceGraphic" in2="warp" scale="6" xChannelSelector="R" yChannelSelector="G" result="rough" />
        <feTurbulence type="fractalNoise" baseFrequency="0.75" numOctaves="1" seed={boil + 100} result="grain" />
        <feColorMatrix in="grain" type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  3 0 0 0 -0.75" result="mask" />
        <feComposite in="rough" in2="mask" operator="in" />
      </filter>
    );
  }

  return (
    <AbsoluteFill style={{background: C.bg}}>
      <svg width={0} height={0} style={{position: 'absolute'}}>
        <defs>{filter}</defs>
      </svg>
      <AbsoluteFill style={{filter: filter ? `url(#${id})` : undefined}}>{children}</AbsoluteFill>
      {look === 'comic' ? (
        <>
          {/* halftone dots */}
          <AbsoluteFill
            style={{
              backgroundImage: 'radial-gradient(circle, rgba(0,0,0,0.55) 1.6px, transparent 2.2px)',
              backgroundSize: '10px 10px',
              mixBlendMode: 'multiply',
              opacity: 0.45,
            }}
          />
          {/* panel frame: paper gutter + ink border */}
          <AbsoluteFill style={{top: BAR, bottom: BAR, border: '16px solid #F4EEDC', boxShadow: 'inset 0 0 0 6px #111'}} />
        </>
      ) : null}
      {look === 'documentary' ? (
        <>
          {/* film grain */}
          <AbsoluteFill style={{mixBlendMode: 'overlay', opacity: 0.35}}>
            <svg width={1920} height={1080}>
              <filter id="grain">
                <feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="2" seed={f} />
                <feColorMatrix type="saturate" values="0" />
              </filter>
              <rect width={1920} height={1080} filter="url(#grain)" />
            </svg>
          </AbsoluteFill>
          {/* heavy vignette */}
          <AbsoluteFill style={{background: 'radial-gradient(ellipse at 50% 45%, transparent 45%, rgba(0,0,0,0.75) 100%)'}} />
        </>
      ) : null}
      {look === 'pixel' ? (
        <AbsoluteFill
          style={{
            backgroundImage: 'repeating-linear-gradient(0deg, rgba(0,0,0,0.18) 0px, rgba(0,0,0,0.18) 2px, transparent 2px, transparent 8px)',
          }}
        />
      ) : null}
    </AbsoluteFill>
  );
};


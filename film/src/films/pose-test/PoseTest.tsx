import React from 'react';
import {AbsoluteFill} from 'remotion';
import {applyLook, C, FLOOR} from '../../theme';
import {LOOKS} from '../../looks';
import {LookFx} from '../../components/LookFx';
import {Hero} from '../../components/Hero';
import {Stage} from '../../components/Hud';
import {Ground} from '../../components/Primitives';

// Close-up check of the tricky poses: sit (on a chair at seat height 100), type (desk at 150), slump (floor).
export const PoseTest: React.FC = () => {
  applyLook(LOOKS.documentary);
  const chair = (x: number) => (
    <g>
      <rect x={x - 60} y={FLOOR - 104} width={120} height={14} fill={C.propLight} />
      <rect x={x - 62} y={FLOOR - 290} width={8} height={290} fill={C.propLight} />
      <rect x={x + 50} y={FLOOR - 90} width={6} height={90} fill={C.propLight} />
    </g>
  );
  return (
    <LookFx look="documentary">
      <AbsoluteFill style={{background: C.bg}}>
        <Stage>
          <Ground floor={FLOOR} />
          {chair(260)}
          <Hero x={260} y={FLOOR} pose="sit" />
          {chair(820)}
          <rect x={900} y={FLOOR - 150} width={300} height={20} fill={C.propLight} />
          <Hero x={820} y={FLOOR} pose="type" />
          <rect x={1340} y={FLOOR - 470} width={30} height={470} fill="#2C2C31" />
          <Hero x={1470} y={FLOOR} pose="slump" brow={1} mouth={-0.7} />
        </Stage>
      </AbsoluteFill>
    </LookFx>
  );
};

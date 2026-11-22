import React from 'react';
import {Sequence} from 'remotion';
import {applyLook} from '../../theme';
import {LookFx} from '../../components/LookFx';
import {LOOKS, LookName} from '../../looks';
import {BootFilm} from '../boot/Boot';

// The 10-second payoff of BOOT. (frames 2940-3239): boot screen + celebration.
export const TEST_FROM = 2940;
export const TEST_DURATION = 300;

export const StyleTest: React.FC<{look: LookName}> = ({look}) => {
  applyLook(LOOKS[look]);
  return (
    <LookFx look={look}>
      <Sequence from={-TEST_FROM} layout="none">
        <BootFilm />
      </Sequence>
    </LookFx>
  );
};

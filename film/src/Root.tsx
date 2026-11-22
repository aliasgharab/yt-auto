import {Composition, Folder} from 'remotion';
import {PoseTest} from './films/pose-test/PoseTest';
import {Boot, BOOT_DURATION} from './films/boot/Boot';
import {StyleTest, TEST_DURATION} from './films/style-test/StyleTest';
import {Enigma, ENIGMA_DURATION} from './films/enigma/Enigma';
import {Avatar, Banner, Thumbnail} from './films/brand/Brand';
import {Compilation, compMetadata, ShortCut, shortMetadata} from './films/cuts/Cuts';

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition id="Boot" component={Boot} durationInFrames={BOOT_DURATION} fps={30} width={1920} height={1080} />
      <Composition id="Enigma" component={Enigma} durationInFrames={ENIGMA_DURATION} fps={30} width={1920} height={1080} />
      <Composition id="Pose-test" component={PoseTest} durationInFrames={60} fps={30} width={1920} height={1080} />
      <Folder name="Brand">
        <Composition id="Thumbnail" component={Thumbnail} durationInFrames={31} fps={30} width={1280} height={720} defaultProps={{word: 'Enigma', line: 'The tiny flaw', brow: 0.6}} />
        <Composition id="Avatar" component={Avatar} durationInFrames={31} fps={30} width={800} height={800} />
        <Composition id="Banner" component={Banner} durationInFrames={31} fps={30} width={2560} height={1440} />
      </Folder>
      <Folder name="Cuts">
        <Composition id="ShortCut" component={ShortCut} calculateMetadata={shortMetadata} durationInFrames={1} fps={30} width={1080} height={1920}
          defaultProps={{src: 'cuts/enigma.mp4', from: 0, to: 1053, hook: 'The machine Germany thought was unbreakable', lines: []}} />
        <Composition id="Compilation" component={Compilation} calculateMetadata={compMetadata} durationInFrames={1} fps={30} width={1920} height={1080}
          defaultProps={{title: 'Tech stories', introVoice: null, introFrames: 150, introLines: [], segments: [{src: 'cuts/enigma.mp4', label: 'Enigma', frames: 4524}], card: {word: 'BROKEN.', line: 'Every system has a flaw.', accent: 'Go looking for it.'}}} />
      </Folder>
      {/* FILMS (yt-auto's film builder adds new <Composition> lines above this marker) */}
      <Folder name="Style-tests">
        <Composition id="Style-Pixel" component={StyleTest} durationInFrames={TEST_DURATION} fps={30} width={1920} height={1080} defaultProps={{look: 'pixel' as const}} />
        <Composition id="Style-Neon" component={StyleTest} durationInFrames={TEST_DURATION} fps={30} width={1920} height={1080} defaultProps={{look: 'neon' as const}} />
        <Composition id="Style-Blueprint" component={StyleTest} durationInFrames={TEST_DURATION} fps={30} width={1920} height={1080} defaultProps={{look: 'blueprint' as const}} />
        <Composition id="Style-Chalk" component={StyleTest} durationInFrames={TEST_DURATION} fps={30} width={1920} height={1080} defaultProps={{look: 'chalk' as const}} />
        <Composition id="Style-Documentary" component={StyleTest} durationInFrames={TEST_DURATION} fps={30} width={1920} height={1080} defaultProps={{look: 'documentary' as const}} />
        <Composition id="Style-Comic" component={StyleTest} durationInFrames={TEST_DURATION} fps={30} width={1920} height={1080} defaultProps={{look: 'comic' as const}} />
      </Folder>
    </>
  );
};

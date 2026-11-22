import React from 'react';
import {interpolate, useCurrentFrame} from 'remotion';
import {C, FLOOR, LOOK} from '../../theme';
import {Backdrop, Cone, Glow, Ground, WCircle, WLine, WPoly, WRect} from '../../components/Primitives';

export type RoomLight = {
  lamp?: number; // 0..1
  screen?: number; // 0..1
  screenColor?: string;
  led?: number; // 0..1
  ledColor?: string;
  laptopOpen?: boolean;
};

// The hero's bedroom, side-on. Desk on the right, chair at x~760, window with the moon.
export const Room: React.FC<RoomLight> = ({lamp = 0, screen = 1, screenColor = C.screen, led = 0, ledColor = C.led, laptopOpen = true}) => {
  const t = useCurrentFrame();
  const flick = 0.94 + 0.06 * Math.sin(t * 0.37) * Math.sin(t * 0.11);
  const deskY = FLOOR - 150;
  return (
    <g>
      <Ground floor={FLOOR} />
      {/* window + moon */}
      <WRect x={260} y={250} w={230} h={260} fill="#0B0D16" seed={2} />
      <Glow x={400} y={330} r={260} color={C.moon} opacity={0.22} />
      <circle cx={400} cy={330} r={34} fill={C.moon} opacity={0.9} />
      <WLine pts={[[375, 250], [375, 510]]} seed={3} />
      <WLine pts={[[260, 380], [490, 380]]} seed={4} />
      <WRect x={250} y={506} w={250} h={14} fill={C.propLight} seed={5} />
      {/* moonlight patch on the floor */}
      <Glow x={470} y={FLOOR + 4} r={200} ry={24} color={C.moon} opacity={0.18} />

      {/* poster / shelf */}
      <WRect x={1500} y={330} w={260} h={14} fill={C.propLight} seed={6} />
      <WRect x={1520} y={262} w={34} h={68} fill="#22232B" seed={7} />
      <WRect x={1558} y={272} w={30} h={58} fill="#1D1E26" seed={8} />
      <WRect x={1592} y={256} w={38} h={74} fill="#25262E" seed={9} />

      {/* chair */}
      <WRect x={760} y={FLOOR - 104} w={120} h={14} fill={C.propLight} seed={10} />
      <WLine pts={[[764, FLOOR - 104], [756, FLOOR - 290]]} sw={7} seed={11} />
      <WLine pts={[[772, FLOOR - 90], [772, FLOOR]]} sw={5} seed={12} />
      <WLine pts={[[868, FLOOR - 90], [868, FLOOR]]} sw={5} seed={13} />

      {/* desk */}
      <WRect x={890} y={deskY} w={520} h={20} fill={C.propLight} seed={14} />
      <WLine pts={[[910, deskY + 20], [910, FLOOR]]} sw={6} seed={15} />
      <WLine pts={[[1390, deskY + 20], [1390, FLOOR]]} sw={6} seed={16} />

      {/* manuals stack */}
      <WRect x={1180} y={deskY - 22} w={120} h={22} fill="#2A2330" seed={17} />
      <WRect x={1188} y={deskY - 42} w={110} h={20} fill="#1F2A30" seed={18} />
      <WRect x={1176} y={deskY - 60} w={116} h={18} fill="#30282A" seed={19} />

      {/* dev board with LED */}
      <WRect x={1060} y={deskY - 12} w={90} h={12} fill="#1E4B34" seed={20} />
      <rect x={1128} y={deskY - 20} width={10} height={8} rx={2} fill={led > 0.05 ? ledColor : '#333'} opacity={0.4 + 0.6 * led} />
      <Glow x={1133} y={deskY - 16} r={70} color={ledColor} opacity={led * 0.9} />

      {/* mug */}
      <WPoly pts={[[1320, deskY - 50], [1360, deskY - 50], [1356, deskY], [1324, deskY]]} fill="#2B2B33" seed={21} />
      <WCircle cx={1366} cy={deskY - 28} r={11} fill="none" seed={22} />

      {/* laptop: thin side-on shape, screen faces the hero (left) */}
      <WRect x={940} y={deskY - 8} w={120} h={8} fill="#2A2A32" seed={23} />
      {laptopOpen ? (
        <WPoly pts={[[1050, deskY - 8], [1062, deskY - 10], [1032, deskY - 118], [1020, deskY - 116]]} fill="#2A2A32" seed={24} />
      ) : (
        <WRect x={940} y={deskY - 14} w={120} h={6} fill="#2A2A32" seed={24} />
      )}
      {laptopOpen ? (
        <g opacity={screen}>
          <line x1={1048} y1={deskY - 10} x2={1019} y2={deskY - 114} stroke={screenColor} strokeWidth={5} strokeLinecap="round" />
          <Glow x={1000} y={deskY - 70} r={330} color={screenColor} opacity={0.55 * flick} />
          <Glow x={960} y={deskY - 60} r={120} color={screenColor} opacity={0.4 * flick} />
        </g>
      ) : null}

      {/* desk lamp */}
      <WRect x={1250} y={deskY - 8} w={60} h={8} fill="#2A2A32" seed={25} />
      <WLine pts={[[1280, deskY - 8], [1240, deskY - 150], [1190, deskY - 200]]} sw={5} seed={26} />
      <WPoly pts={[[1150, deskY - 230], [1210, deskY - 214], [1196, deskY - 176], [1136, deskY - 192]]} fill="#2A2A32" seed={27} />
      {lamp > 0 ? (
        <g>
          <Cone x={1160} y={deskY - 186} topW={60} bottomW={360} h={186} color={C.lamp} opacity={0.3 * lamp * flick} />
          <Glow x={1165} y={deskY - 184} r={240} color={C.lamp} opacity={0.85 * lamp * flick} />
          <Glow x={1150} y={deskY} r={260} ry={40} color={C.lamp} opacity={0.5 * lamp} />
        </g>
      ) : null}
    </g>
  );
};

export type TermLine = {at: number; text: string; color?: string; speed?: number; size?: number; center?: boolean; y?: number};

// Hard-cut close-up of the laptop screen. Text types on with a blinking cursor.
export const LaptopCU: React.FC<{
  lines: TermLine[];
  glow?: string;
  bg?: string;
  tint?: number;
  shake?: number;
}> = ({lines, glow = C.screen, bg = C.screenBg, tint = 0}) => {
  const t = useCurrentFrame();
  const flick = 0.95 + 0.05 * Math.sin(t * 0.8);
  let cursor: [number, number] | null = null;
  const rendered = lines.map((l, i) => {
    if (t < l.at) return null;
    const n = Math.min(l.text.length, Math.floor((t - l.at) * (l.speed ?? 1.2)));
    const y = l.y ?? 320 + i * 78;
    const size = (l.size ?? 50) * LOOK.monoScale;
    if (!l.center && (n < l.text.length || i === lines.filter((q) => t >= q.at).length - 1)) cursor = [300 + n * size * 0.52, y];
    return (
      <text key={i} x={l.center ? 960 : 300} y={y} textAnchor={l.center ? 'middle' : 'start'} fontFamily={LOOK.mono} fontWeight={700} fontSize={size} fill={l.color ?? C.term} style={{filter: `drop-shadow(0 0 8px ${l.color ?? C.term}88)`}}>
        {l.text.slice(0, n)}
      </text>
    );
  });
  const cur = cursor as [number, number] | null;
  return (
    <g>
      <Backdrop dark />
      <Glow x={960} y={540} r={1100} ry={700} color={glow} opacity={0.35 * flick} />
      {/* bezel */}
      <WRect x={200} y={170} w={1520} h={840} fill="#16161C" seed={40} sw={3} />
      <WRect x={240} y={210} w={1440} h={760} fill={bg} seed={41} sw={2} />
      {tint > 0 ? <rect x={240} y={210} width={1440} height={760} fill={glow} opacity={tint} /> : null}
      {/* scanlines */}
      {Array.from({length: 26}, (_, i) => (
        <rect key={i} x={240} y={210 + ((i * 30 + t * 2) % 760)} width={1440} height={3} fill="#FFFFFF" opacity={0.025} />
      ))}
      {rendered}
      {cur && Math.floor(t / 8) % 2 === 0 ? <rect x={cur[0] + 4} y={cur[1] - 40} width={26} height={46} fill={C.term} /> : null}
    </g>
  );
};

// Close-up of the dev board with its single LED.
export const BoardCU: React.FC<{ledColor: string; blinkPeriod: number; dim?: number}> = ({ledColor, blinkPeriod, dim = 1}) => {
  const t = useCurrentFrame();
  const phase = (t % blinkPeriod) / blinkPeriod;
  const on = interpolate(phase, [0, 0.08, 0.4, 0.55, 1], [0.15, 1, 1, 0.15, 0.15]);
  return (
    <g>
      <Backdrop dark />
      <Glow x={1180} y={470} r={900} color={ledColor} opacity={on * 0.45 * dim} />
      <WRect x={420} y={420} w={1080} h={420} fill="#163828" seed={50} sw={3} />
      {/* chip */}
      <WRect x={640} y={520} w={260} h={220} fill="#15161B" seed={51} sw={2.5} />
      <text x={666} y={640} fontFamily={LOOK.mono} fontWeight={700} fontSize={36} fill="#55555E">
        MCU
      </text>
      {Array.from({length: 8}, (_, i) => (
        <rect key={'p' + i} x={660 + i * 30} y={500} width={12} height={20} fill="#7A7A84" />
      ))}
      {Array.from({length: 8}, (_, i) => (
        <rect key={'q' + i} x={660 + i * 30} y={740} width={12} height={20} fill="#7A7A84" />
      ))}
      {/* traces */}
      {[0, 1, 2, 3].map((i) => (
        <WLine key={i} pts={[[900, 560 + i * 40], [1040 + i * 20, 560 + i * 40], [1100 + i * 20, 500]]} stroke="#2F6A4C" sw={4} seed={52 + i} />
      ))}
      {/* the LED */}
      <WRect x={1150} y={444} w={60} h={40} fill="#202024" seed={56} />
      <ellipse cx={1180} cy={456} rx={22} ry={16} fill={ledColor} opacity={0.25 + 0.75 * on * dim} />
      <Glow x={1180} y={456} r={260} color={ledColor} opacity={on * dim} />
      <Glow x={1180} y={456} r={70} color="#FFFFFF" opacity={on * 0.6 * dim} />
    </g>
  );
};

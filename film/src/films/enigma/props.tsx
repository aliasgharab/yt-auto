import React from 'react';
import {interpolate, random, useCurrentFrame} from 'remotion';
import {C, FLOOR, LOOK} from '../../theme';
import {Backdrop, Cone, Glow, Ground, WCircle, WLine, WPoly, WRect} from '../../components/Primitives';
import {Pt} from '../../components/lib';

const ROWS = ['QWERTZUIO', 'ASDFGHJK', 'PYXCVBNML'];

// Where a lamp sits on the close-up lampboard (for marker circles).
export const lampXY = (ch: string): Pt => {
  const r = ROWS.findIndex((row) => row.includes(ch));
  const i = ROWS[r].indexOf(ch);
  return [960 - ((ROWS[r].length - 1) * 92) / 2 + i * 92, 340 + r * 70];
};
const CL = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;

// ---------------------------------------------------------------- Enigma, top-down close-up
export const EnigmaTop: React.FC<{lit?: string | null; pressed?: string | null; rotors?: string; glitch?: number; crack?: number}> = ({
  lit = null,
  pressed = null,
  rotors = 'ADU',
  glitch = 0,
  crack = 0,
}) => {
  const t = useCurrentFrame();
  const row = (letters: string, y: number, r: number, kind: 'lamp' | 'key') =>
    letters.split('').map((ch, i) => {
      const x = 960 - ((letters.length - 1) * 92) / 2 + i * 92 + (kind === 'key' && letters.length < 9 ? 0 : 0);
      const isLit = kind === 'lamp' && ch === lit;
      const isDown = kind === 'key' && ch === pressed;
      return (
        <g key={kind + ch}>
          {isLit ? <Glow x={x} y={y} r={150} color={C.lamp} opacity={0.9} /> : null}
          <circle cx={x} cy={y + (isDown ? 4 : 0)} r={r * (isDown ? 0.92 : 1)} fill={isLit ? '#FFF6E0' : kind === 'key' ? (isDown ? '#2A2A2E' : '#3A3A3F') : '#202024'} stroke="#55555A" strokeWidth={2.5} />
          <text
            x={x}
            y={y + 12 + (isDown ? 4 : 0)}
            textAnchor="middle"
            fontFamily={LOOK.mono}
            fontWeight={700}
            fontSize={34}
            fill={isLit ? '#1A1A1A' : kind === 'key' ? '#D6D6DA' : '#5A5A60'}
          >
            {ch}
          </text>
        </g>
      );
    });
  const shown = glitch > 0 ? rotors.split('').map((c, i) => String.fromCharCode(65 + Math.floor(random(`g${t}${i}`) * 26))).join('') : rotors;
  return (
    <g>
      <Backdrop dark />
      <Glow x={960} y={300} r={900} ry={500} color={C.lamp} opacity={0.25} />
      {/* wooden case + metal plate */}
      <WRect x={330} y={110} w={1260} h={880} fill="#2B2B2F" sw={3} seed={300} />
      <WRect x={370} y={150} w={1180} h={800} fill="#1B1B1E" sw={2} seed={301} />
      {/* rotor windows */}
      {shown.split('').map((ch, i) => (
        <g key={'r' + i}>
          <WRect x={800 + i * 120} y={180} w={80} h={70} fill="#0F0F11" seed={310 + i} />
          <text x={840 + i * 120} y={230} textAnchor="middle" fontFamily={LOOK.mono} fontWeight={700} fontSize={44} fill={glitch > 0 ? C.accent : C.white}>
            {ch}
          </text>
          <rect x={790 + i * 120} y={172} width={10} height={86} fill="#3C3C41" />
        </g>
      ))}
      {row(ROWS[0], 340, 30, 'lamp')}
      {row(ROWS[1], 410, 30, 'lamp')}
      {row(ROWS[2], 480, 30, 'lamp')}
      <line x1={420} x2={1500} y1={560} y2={560} stroke="#333338" strokeWidth={3} />
      {row(ROWS[0], 640, 34, 'key')}
      {row(ROWS[1], 730, 34, 'key')}
      {row(ROWS[2], 820, 34, 'key')}
      {crack > 0 ? (
        <path
          d="M1180,150 L1150,260 L1190,330 L1120,450 L1160,560 L1100,690"
          stroke={C.accent}
          strokeWidth={5}
          fill="none"
          pathLength={1}
          strokeDasharray={1}
          strokeDashoffset={1 - crack}
          style={{filter: `drop-shadow(0 0 8px ${C.accent})`}}
        />
      ) : null}
    </g>
  );
};

// ---------------------------------------------------------------- Enigma, side view on a desk
export const EnigmaSide: React.FC<{x: number; y: number; lamp?: number}> = ({x, y, lamp = 0}) => (
  <g>
    <WRect x={x} y={y - 46} w={150} h={46} fill="#34343A" seed={320} />
    <WPoly pts={[[x, y - 46], [x + 150, y - 46], [x + 130, y - 64], [x + 20, y - 64]]} fill="#2A2A2F" seed={321} />
    <WRect x={x + 40} y={y - 74} w={70} h={12} fill="#1E1E22" seed={322} />
    {lamp > 0 ? <Glow x={x + 75} y={y - 60} r={90} color={C.lamp} opacity={lamp} /> : null}
  </g>
);

// ---------------------------------------------------------------- Hut interior (side view)
export const Hut: React.FC<{lamp?: number; desk?: boolean; chalk?: boolean; radio?: boolean; enigma?: boolean; window?: boolean; mug?: boolean}> = ({
  lamp = 1,
  desk = true,
  chalk = false,
  radio = false,
  enigma = false,
  window = true,
  mug = true,
}) => {
  const t = useCurrentFrame();
  const flick = 0.94 + 0.06 * Math.sin(t * 0.37) * Math.sin(t * 0.11);
  const deskY = FLOOR - 150;
  return (
    <g>
      <Ground floor={FLOOR} />
      {/* wall planks */}
      {Array.from({length: 16}, (_, i) => (
        <line key={i} x1={i * 128 + 40} x2={i * 128 + 40} y1={60} y2={FLOOR} stroke="#141416" strokeWidth={3} />
      ))}
      {window ? (
        <g>
          <WRect x={260} y={250} w={230} h={260} fill="#0B0B0D" seed={2} />
          <Glow x={400} y={330} r={260} color={C.moon} opacity={0.18} />
          <circle cx={400} cy={330} r={30} fill={C.moon} opacity={0.85} />
          <WLine pts={[[375, 250], [375, 510]]} seed={3} />
          <WLine pts={[[260, 380], [490, 380]]} seed={4} />
        </g>
      ) : null}
      {chalk ? (
        <g>
          <WRect x={1420} y={260} w={420} h={300} fill="#202322" sw={3} seed={330} />
          {[0, 1, 2].map((i) => (
            <circle key={i} cx={1520 + i * 110} cy={370} r={36} fill="none" stroke="#C8C8CC" strokeWidth={3} opacity={0.7} strokeDasharray="5 4" />
          ))}
          <line x1={1480} x2={1780} y1={460} y2={460} stroke="#C8C8CC" strokeWidth={3} opacity={0.6} />
        </g>
      ) : null}
      {desk ? (
        <g>
          {/* chair */}
          <WRect x={760} y={FLOOR - 104} w={120} h={14} fill={C.propLight} seed={10} />
          <WLine pts={[[764, FLOOR - 104], [756, FLOOR - 290]]} sw={7} seed={11} />
          <WLine pts={[[772, FLOOR - 90], [772, FLOOR]]} sw={5} seed={12} />
          <WLine pts={[[868, FLOOR - 90], [868, FLOOR]]} sw={5} seed={13} />
          {/* desk */}
          <WRect x={890} y={deskY} w={520} h={20} fill={C.propLight} seed={14} />
          <WLine pts={[[910, deskY + 20], [910, FLOOR]]} sw={6} seed={15} />
          <WLine pts={[[1390, deskY + 20], [1390, FLOOR]]} sw={6} seed={16} />
          {/* papers */}
          <WPoly pts={[[960, deskY - 4], [1060, deskY - 6], [1062, deskY], [958, deskY]]} fill="#C9C9CC" seed={17} />
          <WPoly pts={[[1070, deskY - 3], [1150, deskY - 5], [1152, deskY], [1068, deskY]]} fill="#B5B5B9" seed={18} />
          {mug ? <WPoly pts={[[1180, deskY - 44], [1214, deskY - 44], [1211, deskY], [1183, deskY]]} fill="#3A3A40" seed={19} /> : null}
          {enigma ? <EnigmaSide x={960} y={deskY} lamp={0.4 + 0.4 * Math.max(0, Math.sin(t * 0.6))} /> : null}
          {radio ? (
            <g>
              <WRect x={1180} y={deskY - 90} w={150} h={90} fill="#2E2E33" seed={23} />
              <circle cx={1225} cy={deskY - 45} r={22} fill="#1A1A1D" stroke="#66666C" strokeWidth={2} />
              <rect x={1260} y={deskY - 60} width={50} height={14} fill={C.lamp} opacity={0.8} />
              <Glow x={1285} y={deskY - 53} r={70} color={C.lamp} opacity={0.6} />
            </g>
          ) : null}
          {/* lamp */}
          <WRect x={1300} y={deskY - 8} w={60} h={8} fill="#2A2A32" seed={25} />
          <WLine pts={[[1330, deskY - 8], [1290, deskY - 150], [1240, deskY - 200]]} sw={5} seed={26} />
          <WPoly pts={[[1200, deskY - 230], [1260, deskY - 214], [1246, deskY - 176], [1186, deskY - 192]]} fill="#2A2A32" seed={27} />
          {lamp > 0 ? (
            <g>
              <Cone x={1210} y={deskY - 186} topW={60} bottomW={380} h={186} color={C.lamp} opacity={0.3 * lamp * flick} />
              <Glow x={1215} y={deskY - 184} r={260} color={C.lamp} opacity={0.85 * lamp * flick} />
              <Glow x={1180} y={deskY} r={300} ry={44} color={C.lamp} opacity={0.5 * lamp} />
            </g>
          ) : null}
        </g>
      ) : null}
    </g>
  );
};

// ---------------------------------------------------------------- The Bombe
export const Bombe: React.FC<{x: number; spin: number; lit?: number; scale?: number}> = ({x, spin, lit = 0, scale = 1}) => {
  const t = useCurrentFrame();
  const w = 560;
  const h = 470;
  const y = FLOOR - h;
  return (
    <g transform={`translate(${x} ${FLOOR}) scale(${scale}) translate(${-x} ${-FLOOR})`}>
      <WRect x={x} y={y} w={w} h={h} fill="#2C2C31" sw={3} seed={340} />
      <WRect x={x + 20} y={y + 20} w={w - 40} h={h - 70} fill="#1C1C20" seed={341} />
      {Array.from({length: 3 * 6}, (_, k) => {
        const r = Math.floor(k / 6);
        const c = k % 6;
        const cx = x + 70 + c * 84;
        const cy = y + 90 + r * 120;
        const a = (spin * (1 + r * 0.7 + c * 0.13) * 40 + k * 37) % 360;
        return (
          <g key={k}>
            <circle cx={cx} cy={cy} r={34} fill="#3A3A40" stroke="#6A6A70" strokeWidth={2.5} />
            <circle cx={cx} cy={cy} r={20} fill="#26262A" />
            <line x1={cx} y1={cy} x2={cx + Math.cos((a * Math.PI) / 180) * 30} y2={cy + Math.sin((a * Math.PI) / 180) * 30} stroke="#D8D8DC" strokeWidth={4} strokeLinecap="round" />
          </g>
        );
      })}
      {/* indicator lamp on top */}
      <WRect x={x + w / 2 - 30} y={y - 26} w={60} h={26} fill="#222226" seed={342} />
      <circle cx={x + w / 2} cy={y - 34} r={14} fill={lit > 0 ? C.accent : '#3A2224'} />
      {lit > 0 ? <Glow x={x + w / 2} y={y - 34} r={200} color={C.accent} opacity={lit} /> : null}
      {/* cables */}
      <path d={`M${x + 40},${y + h - 40} q60,${30 + Math.sin(t / 20) * 2} 120,0 t120,0 t120,0 t120,0`} stroke="#4A4A50" strokeWidth={5} fill="none" />
    </g>
  );
};

// ---------------------------------------------------------------- Atlantic map
// Simplified but recognisable coastlines (hand-traced, north up).
const NA: Pt[] = [[0, 110], [150, 120], [250, 150], [300, 220], [270, 270], [330, 300], [310, 350], [380, 400], [350, 450], [300, 470], [320, 520], [250, 560], [230, 640], [190, 700], [200, 780], [130, 860], [80, 960], [0, 1000]];
const GREENLAND: Pt[] = [[470, 40], [720, 30], [800, 90], [760, 170], [700, 250], [640, 330], [600, 300], [560, 210], [500, 120]];
const ICELAND: Pt[] = [[960, 210], [1010, 190], [1060, 200], [1110, 220], [1100, 260], [1040, 280], [980, 270], [950, 240]];
const BRITAIN: Pt[] = [
  [1400, 285], [1440, 292], [1432, 330], [1462, 362], [1452, 398], [1478, 432], [1500, 478], [1522, 520], [1534, 556],
  [1556, 578], [1546, 602], [1566, 620], [1522, 634], [1462, 628], [1420, 634], [1380, 652], [1338, 668], [1366, 640],
  [1392, 616], [1410, 600], [1380, 590], [1368, 560], [1392, 540], [1374, 520], [1410, 500], [1400, 468], [1380, 440],
  [1360, 410], [1376, 380], [1350, 350], [1374, 318], [1368, 298],
];
const IRELAND: Pt[] = [[1288, 452], [1330, 432], [1352, 462], [1346, 520], [1322, 560], [1278, 566], [1258, 522], [1274, 482]];
const NORWAY: Pt[] = [[1690, 60], [1650, 150], [1620, 250], [1630, 320], [1680, 345], [1720, 300], [1760, 210], [1810, 120], [1860, 60]];
const EUROPE: Pt[] = [
  [1920, 330], [1800, 380], [1730, 430], [1690, 500], [1640, 560], [1600, 610], [1590, 650], [1540, 680], [1500, 690],
  [1540, 722], [1572, 770], [1560, 840], [1500, 880], [1486, 960], [1510, 1080], [1920, 1080],
];

const bez = (u: number, p0: Pt, p1: Pt, p2: Pt): Pt => [
  (1 - u) * (1 - u) * p0[0] + 2 * (1 - u) * u * p1[0] + u * u * p2[0],
  (1 - u) * (1 - u) * p0[1] + 2 * (1 - u) * u * p1[1] + u * u * p2[1],
];

export type Ship = {u: number; sunk?: number}; // sunk = frames since sinking (undefined = afloat)

export const AtlanticMap: React.FC<{
  convoyU: number; // 0..1 progress along the route
  ships?: number;
  sunkAt?: number[]; // local frames at which ship i sinks
  subs?: Pt[]; // U-boat positions
  reroute?: number; // 0..1: route bends north around the subs
  britainGlow?: number;
  labels?: number; // 0..1: CONVOY / U-BOATS labels
  sunkCounter?: boolean;
}> = ({convoyU, ships = 7, sunkAt = [], subs = [], reroute = 0, britainGlow = 0, labels = 0, sunkCounter = false}) => {
  const t = useCurrentFrame();
  const p0: Pt = [340, 520];
  const p2: Pt = [1350, 560];
  const p1: Pt = [850, 640 - reroute * 420];
  const route = Array.from({length: 40}, (_, i) => bez(i / 39, p0, p1, p2));
  const land = (pts: Pt[], seed: number) => <WPoly pts={pts} fill="#3A3A3F" stroke="#5A5A60" sw={2} seed={seed} />;
  return (
    <g>
      <rect x={0} y={0} width={1920} height={1080} fill="#0D0E11" />
      {Array.from({length: 13}, (_, i) => (
        <line key={'v' + i} x1={i * 160} x2={i * 160} y1={0} y2={1080} stroke="#FFFFFF" strokeWidth={1} opacity={0.05} />
      ))}
      {Array.from({length: 8}, (_, i) => (
        <line key={'h' + i} x1={0} x2={1920} y1={i * 150} y2={i * 150} stroke="#FFFFFF" strokeWidth={1} opacity={0.05} />
      ))}
      {land(NA, 400)}
      {land(GREENLAND, 401)}
      {land(ICELAND, 402)}
      {land(IRELAND, 403)}
      {land(EUROPE, 405)}
      {land(NORWAY, 406)}
      {land(BRITAIN, 404)}
      {britainGlow > 0 ? <Glow x={1420} y={460} r={260} color={C.white} opacity={britainGlow * 0.5} /> : null}
      {reroute > 0 ? (
        <path
          d={`M${p0[0]},${p0[1]} Q850,640 ${p2[0]},${p2[1]}`}
          stroke={C.accent}
          strokeWidth={3}
          strokeDasharray="10 10"
          fill="none"
          opacity={0.6 * reroute}
        />
      ) : null}
      <path d={'M' + route.map((p) => p.join(',')).join(' L')} stroke="#D8D8DC" strokeWidth={2.5} strokeDasharray="12 10" strokeDashoffset={-t} fill="none" opacity={0.6} />
      {Array.from({length: ships}, (_, i) => {
        const u = Math.min(1, Math.max(0, convoyU - i * 0.025));
        const [x, y] = bez(u, p0, p1, p2);
        const off = ((i % 3) - 1) * 16;
        const s = sunkAt[i];
        const g = s === undefined ? -1 : t - s;
        if (g >= 0) {
          const ring = interpolate(g, [0, 24], [0, 1], {...CL, easing: (v) => 1 - (1 - v) * (1 - v)});
          const o = interpolate(g, [0, 6, 60], [1, 1, 0.55], CL);
          return (
            <g key={i}>
              <Glow x={x} y={y + off} r={110} color={C.accent} opacity={interpolate(g, [0, 4, 30], [0, 0.9, 0.25], CL)} />
              <circle cx={x} cy={y + off} r={18 + ring * 50} fill="none" stroke={C.accent} strokeWidth={4} opacity={1 - ring} />
              <path d={`M${x - 16},${y + off - 16} L${x + 16},${y + off + 16} M${x + 16},${y + off - 16} L${x - 16},${y + off + 16}`} stroke={C.accent} strokeWidth={7} strokeLinecap="round" opacity={o} />
            </g>
          );
        }
        return <rect key={i} x={x - 13} y={y + off - 6} width={26} height={12} rx={4} fill="#EDEDF0" />;
      })}
      {subs.map(([x, y], i) => (
        <g key={'s' + i}>
          <Glow x={x} y={y} r={70} color={C.accent} opacity={0.45 + 0.2 * Math.sin(t / 6 + i)} />
          {/* U-boat silhouette: long hull + conning tower, ~52px */}
          <ellipse cx={x} cy={y} rx={26} ry={7} fill={C.accent} />
          <rect x={x - 6} y={y - 14} width={12} height={10} rx={2} fill={C.accent} />
        </g>
      ))}
      {labels > 0 && subs.length ? (
        <g opacity={labels} fontFamily={LOOK.font} fontWeight={700} fontSize={36} letterSpacing={4}>
          <text x={subs.reduce((a, p) => a + p[0], 0) / subs.length} y={Math.max(...subs.map((p) => p[1])) + 70} textAnchor="middle" fill={C.accent}>
            U-BOATS
          </text>
          <text x={bez(Math.max(0, convoyU - 0.07), p0, p1, p2)[0]} y={bez(Math.max(0, convoyU - 0.07), p0, p1, p2)[1] - 50} textAnchor="middle" fill="#D8D8DC">
            CONVOY
          </text>
        </g>
      ) : null}
      {sunkCounter && sunkAt.some((a) => a < 999 && t >= a) ? (
        <text x={850} y={830} textAnchor="middle" fontFamily={LOOK.display} fontSize={64} fill={C.accent} letterSpacing={3}>
          {`SHIPS SUNK: ${[0, 14, 27, 41, 52][sunkAt.filter((a) => a < 999 && t >= a).length]}`}
        </text>
      ) : null}
    </g>
  );
};

// ---------------------------------------------------------------- Submarine on the surface, radioing
export const SubRadio: React.FC<{waves: number}> = ({waves}) => {
  const t = useCurrentFrame();
  const seaY = 650;
  const wave = Array.from({length: 49}, (_, i) => `${i === 0 ? 'M' : 'L'}${i * 40},${seaY + Math.sin(i * 0.7 + t * 0.08) * 6}`).join(' ');
  return (
    <g>
      <Backdrop dark />
      <Glow x={1500} y={220} r={520} color={C.moon} opacity={0.35} />
      <circle cx={1500} cy={220} r={46} fill={C.moon} />
      {/* hull */}
      <WPoly pts={[[520, seaY + 10], [600, seaY - 30], [1300, seaY - 30], [1420, seaY + 4], [1300, seaY + 40], [600, seaY + 40]]} fill="#45454C" stroke="#8A8A90" seed={420} />
      <WPoly pts={[[860, seaY - 30], [880, seaY - 120], [1010, seaY - 120], [1040, seaY - 30]]} fill="#505058" stroke="#8A8A90" seed={421} />
      <WLine pts={[[960, seaY - 120], [960, seaY - 260]]} sw={4} seed={422} />
      <circle cx={960} cy={seaY - 262} r={6} fill={C.accent} />
      {Array.from({length: 4}, (_, i) => {
        const g = ((t * 1.3 + i * 30) % 120) / 120;
        return (
          <circle key={i} cx={960} cy={seaY - 262} r={30 + g * 520} fill="none" stroke={C.white} strokeWidth={3} opacity={(1 - g) * 0.5 * waves} />
        );
      })}
      <path d={wave + ` L1920,1080 L0,1080 Z`} fill="#0F1013" />
      <path d={wave} stroke="#55555B" strokeWidth={3} fill="none" />
    </g>
  );
};

// ---------------------------------------------------------------- Bletchley Park mansion at night
export const Mansion: React.FC = () => {
  const t = useCurrentFrame();
  const base = FLOOR;
  const win = (x: number, y: number, k: number) => {
    const on = random(`w${k}`) > 0.3;
    return (
      <g key={k}>
        <rect x={x} y={y} width={34} height={52} fill={on ? '#E9E2D0' : '#141416'} opacity={on ? 0.9 : 1} />
        {on ? <Glow x={x + 17} y={y + 26} r={70} color={C.lamp} opacity={0.35 + 0.05 * Math.sin(t / 9 + k)} /> : null}
      </g>
    );
  };
  return (
    <g>
      <Ground floor={FLOOR} />
      <Glow x={300} y={200} r={400} color={C.moon} opacity={0.3} />
      <circle cx={300} cy={200} r={40} fill={C.moon} />
      {/* main block, wings, towers */}
      <WRect x={620} y={base - 330} w={680} h={330} fill="#2A2A2F" seed={500} />
      <WPoly pts={[[600, base - 330], [960, base - 470], [1320, base - 330]]} fill="#232327" seed={501} />
      <WRect x={1300} y={base - 250} w={300} h={250} fill="#26262B" seed={502} />
      <WRect x={420} y={base - 250} w={200} h={250} fill="#26262B" seed={503} />
      <WRect x={1190} y={base - 470} w={70} h={150} fill="#232327" seed={504} />
      <WPoly pts={[[1180, base - 470], [1225, base - 540], [1270, base - 470]]} fill="#1E1E22" seed={505} />
      {[0, 1, 2, 3, 4, 5].map((i) => win(660 + i * 105, base - 290, i))}
      {[0, 1, 2, 3, 4, 5].map((i) => win(660 + i * 105, base - 170, 10 + i))}
      {[0, 1, 2].map((i) => win(1330 + i * 90, base - 200, 20 + i))}
      {[0, 1].map((i) => win(450 + i * 90, base - 200, 30 + i))}
      <WRect x={920} y={base - 110} w={80} h={110} fill="#141416" seed={506} />
      <Glow x={960} y={base - 60} r={140} color={C.lamp} opacity={0.5} />
      {/* trees */}
      {[180, 1700, 1820].map((x, i) => (
        <g key={i}>
          <WLine pts={[[x, base], [x, base - 140]]} sw={8} seed={510 + i} />
          <WCircle cx={x} cy={base - 210} r={90} fill="#1A1A1D" seed={515 + i} />
        </g>
      ))}
    </g>
  );
};

// ---------------------------------------------------------------- Close-ups
export const Paper: React.FC<{lines: string[]; stamp?: string; stampAt?: number; cross?: number; tilt?: number; title?: string; children?: React.ReactNode}> = ({lines, stamp, stampAt = 10, cross = 0, tilt = -2, title, children}) => {
  const t = useCurrentFrame();
  return (
    <g>
      <Backdrop dark />
      <Glow x={1300} y={120} r={1000} color={C.lamp} opacity={0.35} />
      <g transform={`rotate(${tilt} 960 540)`}>
        <WRect x={560} y={150} w={800} h={780} fill="#CFCFD2" stroke="#8A8A90" sw={2} seed={600} />
        {title ? (
          <text x={620} y={240} fontFamily={LOOK.font} fontWeight={700} fontSize={46} fill="#1A1A1C" letterSpacing={3}>
            {title}
          </text>
        ) : null}
        {lines.map((l, i) => (
          <text key={i} x={620} y={(title ? 320 : 250) + i * 64} fontFamily={LOOK.mono} fontWeight={700} fontSize={40} fill="#2A2A2E">
            {l.slice(0, Math.max(0, Math.floor(t * 1.6) - i * 12))}
          </text>
        ))}
        {stamp ? (
          <g transform="rotate(-12 1120 820)" opacity={interpolate(t, [stampAt, stampAt + 4], [0, 1], CL)}>
            <rect x={960} y={770} width={330} height={100} fill="none" stroke={C.accent} strokeWidth={8} />
            <text x={1125} y={845} textAnchor="middle" fontFamily={LOOK.display} fontSize={70} fill={C.accent} letterSpacing={6}>
              {stamp}
            </text>
          </g>
        ) : null}
        {cross > 0 ? (
          <g stroke={C.accent} strokeWidth={14} strokeLinecap="round" style={{filter: `drop-shadow(0 0 8px ${C.accent})`}}>
            <line x1={640} y1={300} x2={640 + 640 * Math.min(1, cross * 2)} y2={300 + 560 * Math.min(1, cross * 2)} />
            {cross > 0.5 ? <line x1={1280} y1={300} x2={1280 - 640 * (cross - 0.5) * 2} y2={300 + 560 * (cross - 0.5) * 2} /> : null}
          </g>
        ) : null}
        {children}
      </g>
    </g>
  );
};

export const MidnightClock: React.FC<{from: number; to: number; dur: number}> = ({from, to, dur}) => {
  const t = useCurrentFrame();
  // minutes past 23:00
  const m = interpolate(t, [0, dur], [from, to], {...CL});
  const minA = (m / 60) * 360;
  const hourA = ((11 + m / 60) / 12) * 360;
  const hit = m >= 60;
  return (
    <g>
      <Backdrop dark />
      <Glow x={960} y={540} r={700} color={hit ? C.accent : C.moon} opacity={hit ? 0.35 : 0.2} />
      <WCircle cx={960} cy={540} r={330} fill="#18181B" sw={3} seed={610} />
      {Array.from({length: 12}, (_, i) => {
        const a = (i / 12) * Math.PI * 2;
        return <line key={i} x1={960 + Math.cos(a) * 280} y1={540 + Math.sin(a) * 280} x2={960 + Math.cos(a) * 308} y2={540 + Math.sin(a) * 308} stroke="#9A9AA0" strokeWidth={i % 3 === 0 ? 10 : 5} strokeLinecap="round" />;
      })}
      <line x1={960} y1={540} x2={960 + Math.sin((hourA * Math.PI) / 180) * 170} y2={540 - Math.cos((hourA * Math.PI) / 180) * 170} stroke={C.white} strokeWidth={16} strokeLinecap="round" />
      <line x1={960} y1={540} x2={960 + Math.sin((minA * Math.PI) / 180) * 250} y2={540 - Math.cos((minA * Math.PI) / 180) * 250} stroke={hit ? C.accent : C.white} strokeWidth={9} strokeLinecap="round" />
      <circle cx={960} cy={540} r={14} fill={C.white} />
    </g>
  );
};

export const MugRadiator: React.FC = () => {
  const t = useCurrentFrame();
  return (
    <g>
      <Backdrop dark />
      <Glow x={1300} y={150} r={900} color={C.lamp} opacity={0.4} />
      {/* radiator fins */}
      {Array.from({length: 9}, (_, i) => (
        <WRect key={i} x={460 + i * 112} y={520} w={84} h={420} fill="#3A3A40" seed={620 + i} />
      ))}
      <WRect x={430} y={500} w={1060} h={34} fill="#45454B" seed={630} />
      {/* mug on top */}
      <WPoly pts={[[820, 300], [1000, 300], [990, 500], [830, 500]]} fill="#6A6A70" sw={3} seed={631} />
      <WCircle cx={1030} cy={400} r={48} fill="none" sw={14} stroke="#6A6A70" seed={632} />
      {[0, 1, 2].map((k) => (
        <path
          key={k}
          d={`M${860 + k * 50},290 q ${Math.sin(t * 0.15 + k) * 22},-50 0,-100 q ${-Math.sin(t * 0.15 + k) * 22},-50 0,-100`}
          stroke="#8A8A90"
          strokeWidth={6}
          fill="none"
          opacity={0.3}
          strokeLinecap="round"
        />
      ))}
      {/* chain from mug handle down around the radiator pipe */}
      {Array.from({length: 9}, (_, i) => {
        const x = 1060 + i * 26;
        const y = 420 + i * 20 + Math.sin(i * 0.8 + t * 0.05) * 3;
        return <ellipse key={i} cx={x} cy={y} rx={16} ry={9} fill="none" stroke="#B0B0B6" strokeWidth={5} transform={`rotate(${i % 2 ? 60 : 20} ${x} ${y})`} />;
      })}
      <rect x={1240} y={580} width={60} height={40} rx={8} fill="#8E8E94" />
    </g>
  );
};

export const Chalkboard: React.FC<{draw: number; text?: string}> = ({draw, text = 'BUILD A MACHINE'}) => {
  const d = (k: number) => Math.max(0, Math.min(1, draw * 4 - k));
  const chalk = {stroke: '#DCDCE0', strokeWidth: 6, fill: 'none', strokeLinecap: 'round' as const, pathLength: 1, strokeDasharray: 1};
  return (
    <g>
      <Backdrop dark />
      <Glow x={960} y={200} r={1000} color={C.lamp} opacity={0.2} />
      <WRect x={200} y={140} w={1520} h={800} fill="#1E2120" sw={4} seed={640} />
      {[0, 1, 2].map((i) => (
        <circle key={i} cx={620 + i * 340} cy={420} r={120} {...chalk} strokeDashoffset={1 - d(i * 0.6)} />
      ))}
      {[0, 1, 2].map((i) => (
        <path key={'l' + i} d={`M${620 + i * 340},300 L${620 + i * 340},540`} {...chalk} strokeDashoffset={1 - d(1.6 + i * 0.3)} />
      ))}
      <path d="M440,640 L1480,640" {...chalk} strokeDashoffset={1 - d(2.5)} />
      <path d="M500,640 L500,700 M1420,640 L1420,700" {...chalk} strokeDashoffset={1 - d(2.8)} />
      <text x={960} y={830} textAnchor="middle" fontFamily={LOOK.mono} fontWeight={700} fontSize={84} fill="#F2F2F4" letterSpacing={6}>
        {text.slice(0, Math.floor(Math.max(0, draw * 4 - 3) * text.length))}
      </text>
    </g>
  );
};

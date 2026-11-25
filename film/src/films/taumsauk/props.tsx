import React, {useId} from 'react';
import {interpolate, random, useCurrentFrame} from 'remotion';
import {C, FLOOR, LOOK} from '../../theme';
import {Backdrop, Glow, Ground, WCircle, WLine, WPoly, WRect} from '../../components/Primitives';
import {Pt} from '../../components/lib';
import {Hero} from '../../components/Hero';

const CL = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;
export const INK = '#2A2A2E';
export const PAPER = '#CBCAC5';
// water is grey too: a dark body, a lighter surface line, white foam
export const WATER = '#2B2E33';
export const WATER_D = '#1C1E22';
export const SURF = '#9A9DA3';
export const FOAM = '#D9DBDF';
const ROCK = ['#4A4A50', '#55555B', '#3F3F45', '#5E5E64'];

// ---------------------------------------------------------------- polyline helpers
const segLens = (pts: Pt[]) => pts.slice(1).map((p, i) => Math.hypot(p[0] - pts[i][0], p[1] - pts[i][1]));
export const along = (pts: Pt[], u: number): Pt => {
  const ls = segLens(pts);
  const total = ls.reduce((a, b) => a + b, 0);
  let d = Math.max(0, Math.min(1, u)) * total;
  for (let i = 0; i < ls.length; i++) {
    if (d <= ls[i] || i === ls.length - 1) {
      const k = ls[i] ? Math.min(1, d / ls[i]) : 0;
      return [pts[i][0] + (pts[i + 1][0] - pts[i][0]) * k, pts[i][1] + (pts[i + 1][1] - pts[i][1]) * k];
    }
    d -= ls[i];
  }
  return pts[pts.length - 1];
};
export const partial = (pts: Pt[], u: number): Pt[] => {
  const ls = segLens(pts);
  const total = ls.reduce((a, b) => a + b, 0);
  let d = Math.max(0, Math.min(1, u)) * total;
  const out: Pt[] = [pts[0]];
  for (let i = 0; i < ls.length; i++) {
    if (d >= ls[i]) {
      out.push(pts[i + 1]);
      d -= ls[i];
    } else {
      const k = ls[i] ? d / ls[i] : 0;
      out.push([pts[i][0] + (pts[i + 1][0] - pts[i][0]) * k, pts[i][1] + (pts[i + 1][1] - pts[i][1]) * k]);
      break;
    }
  }
  return out;
};
const d = (pts: Pt[]) => 'M' + pts.map((p) => `${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(' L');

// Stones packed inside a polygon (clip), for piled-rock walls.
const Stones: React.FC<{poly: Pt[]; box: [number, number, number, number]; seed: string; size?: number; opacity?: number}> = ({poly, box, seed, size = 26, opacity = 1}) => {
  const id = useId().replace(/:/g, '');
  const [x0, y0, x1, y1] = box;
  const cells: React.ReactNode[] = [];
  let k = 0;
  for (let y = y0; y < y1 + size; y += size * 0.85) {
    for (let x = x0 + ((Math.round((y - y0) / size) % 2) * size) / 2; x < x1 + size; x += size) {
      const r = size * (0.36 + 0.2 * random(`${seed}r${k}`));
      const jx = (random(`${seed}x${k}`) - 0.5) * size * 0.35;
      const jy = (random(`${seed}y${k}`) - 0.5) * size * 0.35;
      cells.push(<ellipse key={k} cx={x + jx} cy={y + jy} rx={r * 1.15} ry={r * 0.85} fill={ROCK[k % 4]} stroke="#232327" strokeWidth={2} />);
      k++;
    }
  }
  return (
    <g opacity={opacity}>
      <defs>
        <clipPath id={id}>
          <path d={d(poly) + ' Z'} />
        </clipPath>
      </defs>
      <path d={d(poly) + ' Z'} fill="#38383D" />
      <g clipPath={`url(#${id})`}>{cells}</g>
    </g>
  );
};

// A label with a thin leader line, sitting next to what it names.
export const Tag: React.FC<{x: number; y: number; tx: number; ty: number; text: string; o?: number; anchor?: 'start' | 'end' | 'middle'; size?: number; color?: string}> = ({
  x,
  y,
  tx,
  ty,
  text,
  o = 1,
  anchor = 'start',
  size = 34,
  color = C.white,
}) =>
  o > 0.01 ? (
    <g opacity={o}>
      <line x1={x} y1={y} x2={tx} y2={ty + 8} stroke={color} strokeWidth={2.5} opacity={0.8} />
      <circle cx={x} cy={y} r={5} fill={color} />
      <text x={tx} y={ty} textAnchor={anchor} fontFamily={LOOK.font} fontWeight={700} fontSize={size} fill={color} letterSpacing={3}>
        {text}
      </text>
    </g>
  ) : null;

// ---------------------------------------------------------------- night sky
const Sky: React.FC<{dawn?: number; moon?: Pt}> = ({dawn = 0, moon = [1580, 190]}) => {
  const t = useCurrentFrame();
  return (
    <g>
      <rect x={0} y={0} width={1920} height={1080} fill={C.bg} />
      {Array.from({length: 40}, (_, i) => (
        <circle key={i} cx={random(`sx${i}`) * 1920} cy={70 + random(`sy${i}`) * 420} r={1 + random(`sr${i}`) * 1.4} fill={C.white} opacity={(0.25 + 0.3 * Math.sin(t / 20 + i)) * (1 - dawn)} />
      ))}
      <Glow x={moon[0]} y={moon[1]} r={420} color={C.moon} opacity={0.28 * (1 - dawn * 0.5)} />
      <circle cx={moon[0]} cy={moon[1]} r={38} fill={C.moon} opacity={0.9 - dawn * 0.4} />
      {dawn > 0 ? <Glow x={1700} y={900} r={1300} ry={520} color={C.lamp} opacity={0.35 * dawn} /> : null}
    </g>
  );
};

// ---------------------------------------------------------------- the mountain, side-on
export const SLOPE: Pt[] = [
  [720, 330], [820, 382], [950, 482], [1080, 600], [1220, 718], [1360, 812], [1500, 874], [1600, 892], [1920, 896],
];
const surfY = (x: number) =>
  interpolate(
    x,
    SLOPE.map((p) => p[0]),
    SLOPE.map((p) => p[1]),
    CL,
  );
const FLOW: Pt[] = [[690, 306], [730, 330], ...SLOPE.slice(1)];
export const HOUSE_X = 1690;

export const SmallHouse: React.FC<{x: number; y: number; s?: number; lit?: number}> = ({x, y, s = 1, lit = 1}) => (
  <g transform={`translate(${x} ${y}) scale(${s})`}>
    <WRect x={-60} y={-70} w={120} h={70} fill="#3A3A3F" seed={51} />
    <WPoly pts={[[-74, -68], [0, -118], [74, -68]]} fill="#2A2A2E" seed={52} />
    <rect x={-40} y={-50} width={26} height={24} fill={lit > 0 ? '#EDE6D4' : '#151517'} opacity={0.4 + 0.6 * lit} />
    {lit > 0 ? <Glow x={-27} y={-38} r={80} color={C.lamp} opacity={0.6 * lit} /> : null}
    <rect x={14} y={-40} width={22} height={40} fill="#18181B" />
  </g>
);

const Tree: React.FC<{x: number; y: number; h?: number; o?: number}> = ({x, y, h = 46, o = 1}) => (
  <g opacity={o}>
    <line x1={x} y1={y} x2={x} y2={y - h * 0.3} stroke="#232326" strokeWidth={4} />
    <polygon points={`${x - h * 0.32},${y - h * 0.25} ${x},${y - h} ${x + h * 0.32},${y - h * 0.25}`} fill="#26262A" />
  </g>
);

export const Mountain: React.FC<{flood?: number; drain?: number; dawn?: number; houseLit?: number}> = ({flood = 0, drain = 0, dawn = 0, houseLit = 1}) => {
  const t = useCurrentFrame();
  const front = along(FLOW, flood);
  const passed = partial(FLOW, flood);
  const body: Pt[] = [[-20, 1080], [-20, 640], [70, 540], [170, 420], [240, 345], [262, 332], ...SLOPE, [1920, 1080]];
  return (
    <g>
      <Sky dawn={dawn} />
      {/* far ridges */}
      <path d="M0,620 Q300,470 620,560 T1240,520 T1920,560 L1920,1080 L0,1080 Z" fill="#141416" />
      <path d="M0,720 Q420,600 900,690 T1920,660 L1920,1080 L0,1080 Z" fill="#18181B" />
      <WPoly pts={body} fill="#2E2E33" seed={40} />
      {/* trees on the slopes; the flood strips them */}
      {Array.from({length: 30}, (_, i) => {
        const x = 760 + i * 27 + random(`tx${i}`) * 10;
        const gone = flood > 0 && front[0] > x - 10;
        return gone ? null : <Tree key={i} x={x} y={surfY(x) + 4} h={38 + random(`th${i}`) * 18} />;
      })}
      {Array.from({length: 7}, (_, i) => (
        <Tree key={'l' + i} x={60 + i * 26} y={560 - i * 22 + 6} h={40} />
      ))}
      {/* the upper reservoir on the flat top, ringed by a rock wall */}
      <rect x={300} y={302} width={400} height={30} fill={WATER} />
      <line x1={300} x2={700} y1={302} y2={302} stroke={SURF} strokeWidth={2} />
      <Glow x={500} y={304} r={220} ry={20} color={C.moon} opacity={0.25} />
      <WPoly pts={[[262, 334], [292, 294], [322, 294], [344, 334]]} fill="#4A4A50" seed={41} />
      {flood <= 0 ? <WPoly pts={[[676, 334], [698, 294], [728, 294], [748, 334]]} fill="#4A4A50" seed={42} /> : <WPoly pts={[[706, 334], [728, 322], [748, 334]]} fill="#4A4A50" seed={42} />}
      {/* the scar the water leaves: bare stone */}
      {flood > 0.01 ? <path d={d(passed)} stroke="#6E6E74" strokeWidth={54} fill="none" strokeLinecap="round" strokeLinejoin="round" opacity={0.9} /> : null}
      {flood > 0.01 ? (
        <g opacity={1 - drain * 0.85}>
          <path d={d(passed)} stroke={FOAM} strokeWidth={40} fill="none" strokeLinecap="round" strokeLinejoin="round" opacity={0.75} />
          <path d={d(passed)} stroke="#FFFFFF" strokeWidth={6} fill="none" strokeDasharray="30 46" strokeDashoffset={-t * 9} opacity={0.6} />
          <Glow x={front[0]} y={front[1]} r={150} color={C.white} opacity={0.5} />
        </g>
      ) : null}
      <SmallHouse x={HOUSE_X} y={898} lit={houseLit} />
      <Tree x={1810} y={898} h={70} />
      <Tree x={1560} y={894} h={60} />
    </g>
  );
};

// ---------------------------------------------------------------- stopwatch + draining tank
export const Billion: React.FC<{u: number}> = ({u}) => {
  const t = useCurrentFrame();
  const cx = 600;
  const cy = 560;
  const R = 250;
  const min = 12 * u;
  const a = (min / 60) * Math.PI * 2;
  const level = 1 - u;
  const tx = 1080;
  const tw = 460;
  const ty = 230;
  const th = 640;
  const wy = ty + th * (1 - level);
  return (
    <g>
      <Backdrop dark />
      <Glow x={960} y={300} r={1100} ry={600} color={C.lamp} opacity={0.14} />
      {/* stopwatch */}
      <WCircle cx={cx} cy={cy} r={R + 24} fill="#1C1C20" sw={3} seed={60} />
      <WRect x={cx - 34} y={cy - R - 70} w={68} h={42} fill="#2A2A2E" seed={61} />
      {Array.from({length: 60}, (_, i) => {
        const b = (i / 60) * Math.PI * 2;
        const L = i % 5 === 0 ? 30 : 12;
        return <line key={i} x1={cx + Math.sin(b) * (R - L)} y1={cy - Math.cos(b) * (R - L)} x2={cx + Math.sin(b) * R} y2={cy - Math.cos(b) * R} stroke="#8A8A90" strokeWidth={i % 5 === 0 ? 6 : 2.5} />;
      })}
      {/* swept wedge: the twelve minutes */}
      {u > 0.01 ? (
        <path d={`M${cx},${cy} L${cx},${cy - R + 40} A${R - 40},${R - 40} 0 0 1 ${cx + Math.sin(a) * (R - 40)},${cy - Math.cos(a) * (R - 40)} Z`} fill={C.accent} opacity={0.18} />
      ) : null}
      <line x1={cx} y1={cy} x2={cx + Math.sin(a) * (R - 30)} y2={cy - Math.cos(a) * (R - 30)} stroke={C.accent} strokeWidth={9} strokeLinecap="round" />
      <circle cx={cx} cy={cy} r={14} fill={C.white} />
      <text x={cx} y={cy + 120} textAnchor="middle" fontFamily={LOOK.mono} fontWeight={700} fontSize={64} fill={C.white}>
        {`${String(Math.floor(min)).padStart(2, '0')}:${String(Math.floor((min % 1) * 60)).padStart(2, '0')}`}
      </text>
      {/* the tank */}
      <text x={tx + tw / 2} y={ty - 40} textAnchor="middle" fontFamily={LOOK.display} fontSize={66} fill={C.white} letterSpacing={3}>
        1,000,000,000 GALLONS
      </text>
      <rect x={tx} y={wy} width={tw} height={ty + th - wy} fill={WATER} />
      <path
        d={`M${tx},${wy} ${Array.from({length: 24}, (_, i) => `L${tx + ((i + 1) / 24) * tw},${wy + Math.sin(i * 0.9 + t * 0.3) * 4 * (level > 0.02 ? 1 : 0)}`).join(' ')}`}
        stroke={SURF}
        strokeWidth={3}
        fill="none"
      />
      <WRect x={tx} y={ty} w={tw} h={th} fill="none" stroke="#8A8A90" sw={5} seed={62} />
      {[0.25, 0.5, 0.75].map((k) => (
        <line key={k} x1={tx} x2={tx + 30} y1={ty + th * k} y2={ty + th * k} stroke="#8A8A90" strokeWidth={3} />
      ))}
      {/* outflow at the bottom */}
      {u > 0.02 && u < 0.99 ? <path d={`M${tx + tw},${ty + th - 30} q90,0 120,${90}`} stroke={FOAM} strokeWidth={18} fill="none" strokeDasharray="22 14" strokeDashoffset={-t * 6} opacity={0.8} /> : null}
    </g>
  );
};

// ---------------------------------------------------------------- the house in the valley, cut away, family asleep
const Sleeper: React.FC<{x: number; y: number; s: number; seed: number; facing?: 1 | -1}> = ({x, y, s, seed}) => {
  const t = useCurrentFrame();
  const br = Math.sin(t / 26 + seed) * 2;
  return (
    <g>
      <g transform={`translate(${x} ${y}) rotate(-90)`}>
        <Hero x={0} y={0} scale={s} sleep brow={-0.1} mouth={0.1} headTilt={90} seed={seed} />
      </g>
      {/* blanket up to the chest */}
      <rect x={x - 262 * s} y={y - 62 * s - br} width={262 * s + 26} height={62 * s + 12 + br} rx={14} fill="#5C5C62" stroke="#2A2A2E" strokeWidth={2} />
    </g>
  );
};

export const HouseInside: React.FC = () => {
  const t = useCurrentFrame();
  const floor = 860;
  const bed = (x: number, y: number, w: number) => (
    <g>
      <WRect x={x} y={y} w={w} h={28} fill="#4A4A50" seed={x} />
      <WRect x={x - 10} y={y - 60} w={14} h={floor - y + 60} fill="#3A3A40" seed={x + 1} />
      <WRect x={x + w - 4} y={y - 20} w={14} h={floor - y + 20} fill="#3A3A40" seed={x + 2} />
      <WRect x={x + 6} y={y - 22} w={70} h={22} fill="#8A8A90" seed={x + 3} />
    </g>
  );
  return (
    <g>
      <Ground floor={floor} />
      {/* cutaway walls */}
      <rect x={180} y={240} width={1560} height={620} fill="#121214" />
      <WPoly pts={[[150, 250], [960, 90], [1770, 250]]} fill="#1C1C20" seed={70} />
      <rect x={952} y={250} width={16} height={610} fill="#232327" />
      {/* window with moonlight */}
      <WRect x={1500} y={330} w={170} h={190} fill="#0A0A0C" seed={71} />
      <circle cx={1600} cy={390} r={22} fill={C.moon} opacity={0.8} />
      <line x1={1585} x2={1585} y1={330} y2={520} stroke="#232327" strokeWidth={8} />
      <polygon points="1500,330 1670,330 1450,860 1120,860" fill={C.moon} opacity={0.05} />
      <Glow x={1585} y={420} r={300} color={C.moon} opacity={0.22} />
      {/* night-light */}
      <circle cx={260} cy={760} r={9} fill={C.lamp} />
      <Glow x={260} y={760} r={180} color={C.lamp} opacity={0.4} />
      {/* parents */}
      {bed(330, 700, 520)}
      <Sleeper x={800} y={670} s={0.58} seed={2} />
      <Sleeper x={860} y={692} s={0.62} seed={1} />
      {/* children: bunk + small bed */}
      {bed(1040, 560, 380)}
      {bed(1040, 760, 380)}
      <Sleeper x={1420} y={552} s={0.44} seed={3} />
      <Sleeper x={1420} y={752} s={0.44} seed={4} />
      <WRect x={1500} y={790} w={210} h={22} fill="#4A4A50" seed={77} />
      <Sleeper x={1700} y={782} s={0.36} seed={5} />
      {/* a clock on the wall: 5:10 */}
      <circle cx={620} cy={400} r={54} fill="#1A1A1D" stroke="#6A6A70" strokeWidth={4} />
      <line x1={620} y1={400} x2={620 + Math.sin(((5 + 10 / 60) / 12) * Math.PI * 2) * 28} y2={400 - Math.cos(((5 + 10 / 60) / 12) * Math.PI * 2) * 28} stroke={C.white} strokeWidth={6} strokeLinecap="round" />
      <line x1={620} y1={400} x2={620 + Math.sin((10 / 60) * Math.PI * 2 + t * 0.0005) * 42} y2={400 - Math.cos((10 / 60) * Math.PI * 2) * 42} stroke={C.white} strokeWidth={4} strokeLinecap="round" />
    </g>
  );
};

// ---------------------------------------------------------------- Missouri (simplified state outline, lon/lat)
const MO: [number, number][] = [
  [-95.77, 40.58], [-94.0, 40.58], [-91.73, 40.61], [-91.42, 40.38], [-91.1, 39.85], [-90.75, 39.4], [-90.6, 39.1], [-90.2, 38.88],
  [-90.18, 38.63], [-90.35, 38.22], [-90.05, 37.98], [-89.52, 37.3], [-89.17, 37.0], [-89.1, 36.95], [-89.4, 36.75], [-89.53, 36.55],
  [-89.7, 36.0], [-90.37, 36.0], [-90.08, 36.3], [-90.15, 36.5], [-94.62, 36.5], [-94.62, 39.1], [-94.9, 39.4], [-95.1, 39.7],
  [-94.92, 39.88], [-95.3, 40.0], [-95.77, 40.58],
];
export const moXY = (lon: number, lat: number): Pt => [960 + (lon + 92.45) * 140, 540 - (lat - 38.3) * 178];
export const TAUM_XY = moXY(-90.82, 37.54);

export const MissouriMap: React.FC<{pin: number; labels: number}> = ({pin, labels}) => {
  const t = useCurrentFrame();
  const [px, py] = TAUM_XY;
  const stl = moXY(-90.2, 38.63);
  const kc = moXY(-94.58, 39.1);
  return (
    <g>
      <rect x={0} y={0} width={1920} height={1080} fill="#0D0E11" />
      {Array.from({length: 13}, (_, i) => (
        <line key={'v' + i} x1={i * 160} x2={i * 160} y1={0} y2={1080} stroke="#FFFFFF" strokeWidth={1} opacity={0.05} />
      ))}
      {Array.from({length: 8}, (_, i) => (
        <line key={'h' + i} x1={0} x2={1920} y1={i * 150} y2={i * 150} stroke="#FFFFFF" strokeWidth={1} opacity={0.05} />
      ))}
      <WPoly pts={MO.map(([a, b]) => moXY(a, b))} fill="#3A3A3F" stroke="#6A6A70" sw={2.5} seed={80} />
      <text x={960} y={330} textAnchor="middle" fontFamily={LOOK.font} fontWeight={700} fontSize={54} fill="#7A7A80" letterSpacing={18}>
        MISSOURI
      </text>
      {[
        [stl, 'ST. LOUIS', 'start'],
        [kc, 'KANSAS CITY', 'start'],
      ].map(([p, name, a], i) => (
        <g key={i} opacity={labels}>
          <circle cx={(p as Pt)[0]} cy={(p as Pt)[1]} r={8} fill="#B8B8BE" />
          <text x={(p as Pt)[0] + 16} y={(p as Pt)[1] + 10} textAnchor={a as 'start'} fontFamily={LOOK.font} fontWeight={700} fontSize={30} fill="#B8B8BE" letterSpacing={2}>
            {name as string}
          </text>
        </g>
      ))}
      {pin > 0 ? (
        <g opacity={Math.min(1, pin * 2)} transform={`translate(0 ${(1 - pin) * -30})`}>
          <Glow x={px} y={py} r={120} color={C.accent} opacity={0.5 + 0.1 * Math.sin(t / 7)} />
          <circle cx={px} cy={py} r={16} fill={C.accent} />
          <circle cx={px} cy={py} r={30} fill="none" stroke={C.accent} strokeWidth={4} opacity={0.7} />
          <line x1={px + 30} y1={py + 10} x2={px + 90} y2={py + 70} stroke={C.white} strokeWidth={2.5} />
          <text x={px + 100} y={py + 84} fontFamily={LOOK.font} fontWeight={700} fontSize={40} fill={C.white} letterSpacing={3}>
            TAUM SAUK RESERVOIR
          </text>
        </g>
      ) : null}
    </g>
  );
};

// ---------------------------------------------------------------- the reservoir from above
const kidney = (cx: number, cy: number, rx: number, ry: number, k: number): Pt[] =>
  Array.from({length: 72}, (_, i) => {
    const a = (i / 72) * Math.PI * 2;
    // a dent on the north side gives the kidney shape
    const dent = 1 - 0.22 * Math.exp(-((Math.atan2(Math.sin(a + Math.PI / 2), Math.cos(a + Math.PI / 2))) ** 2) / 0.25);
    return [cx + Math.cos(a) * rx * k, cy + Math.sin(a) * ry * k * dent] as Pt;
  });

export const Aerial: React.FC<{labels: number}> = ({labels}) => {
  const t = useCurrentFrame();
  const cx = 960;
  const cy = 560;
  return (
    <g>
      <rect x={0} y={0} width={1920} height={1080} fill="#121214" />
      {/* forest canopy */}
      {Array.from({length: 520}, (_, i) => (
        <circle key={i} cx={random(`fx${i}`) * 1960 - 20} cy={random(`fy${i}`) * 1120 - 20} r={10 + random(`fr${i}`) * 16} fill={random(`fc${i}`) > 0.5 ? '#1B1B1E' : '#202024'} />
      ))}
      <WPoly pts={kidney(cx, cy, 640, 360, 1.08)} fill="#5A5A60" stroke="#77777D" sw={3} seed={90} />
      <WPoly pts={kidney(cx, cy, 640, 360, 1.0)} fill="#8A8A90" seed={91} />
      <WPoly pts={kidney(cx, cy, 640, 360, 0.95)} fill={WATER} seed={92} />
      <Glow x={cx + 160} y={cy - 40} r={420} ry={200} color={C.moon} opacity={0.3} />
      {Array.from({length: 7}, (_, i) => (
        <line key={i} x1={cx - 300 + i * 70 + Math.sin(t / 30 + i) * 10} x2={cx - 220 + i * 70 + Math.sin(t / 30 + i) * 10} y1={cy + 40 + i * 22} y2={cy + 40 + i * 22} stroke={SURF} strokeWidth={2} opacity={0.35} />
      ))}
      <g opacity={labels}>
        <text x={cx} y={cy + 20} textAnchor="middle" fontFamily={LOOK.font} fontWeight={700} fontSize={46} fill={C.white} letterSpacing={6}>
          UPPER RESERVOIR
        </text>
        <text x={cx} y={cy + 72} textAnchor="middle" fontFamily={LOOK.font} fontWeight={700} fontSize={30} fill="#9A9AA0" letterSpacing={4}>
          55 ACRES · MAN-MADE · 1963
        </text>
      </g>
      <Tag x={cx + 560} y={cy + 190} tx={cx + 520} ty={cy + 330} text="ROCK WALL" o={labels} anchor="end" />
    </g>
  );
};

// ---------------------------------------------------------------- control room (side-on)
export const ControlRoom: React.FC<{level?: string; operator?: boolean}> = ({level = '1593.6', operator = true}) => {
  const t = useCurrentFrame();
  const deskY = FLOOR - 150;
  const bars = [0.72, 0.7, 0.71];
  return (
    <g>
      <Ground floor={FLOOR} />
      {/* wall panel with the gauge readouts */}
      <WRect x={1020} y={190} w={600} h={300} fill="#1A1A1D" sw={3} seed={100} />
      <rect x={1044} y={214} width={552} height={252} fill={C.screenBg} />
      <Glow x={1320} y={340} r={520} ry={300} color={C.screen} opacity={0.32 + 0.02 * Math.sin(t / 5)} />
      <text x={1070} y={260} fontFamily={LOOK.mono} fontWeight={700} fontSize={26} fill="#9A9AA0">
        UPPER RESERVOIR · LEVEL
      </text>
      {bars.map((b, i) => (
        <g key={i}>
          <rect x={1080 + i * 120} y={290} width={60} height={140} fill="#202024" stroke="#55555A" strokeWidth={2} />
          <rect x={1080 + i * 120} y={290 + 140 * (1 - b)} width={60} height={140 * b} fill={C.screen} opacity={0.75} />
          <text x={1110 + i * 120} y={455} textAnchor="middle" fontFamily={LOOK.mono} fontSize={20} fill="#8A8A90">
            {`G${i + 1}`}
          </text>
        </g>
      ))}
      <text x={1440} y={350} textAnchor="middle" fontFamily={LOOK.mono} fontWeight={700} fontSize={46} fill={C.white}>
        {level}
      </text>
      <text x={1440} y={392} textAnchor="middle" fontFamily={LOOK.mono} fontSize={22} fill="#8A8A90">
        FT
      </text>
      {/* clock */}
      <circle cx={520} cy={300} r={60} fill="#1A1A1D" stroke="#6A6A70" strokeWidth={4} />
      <line x1={520} y1={300} x2={520 + Math.sin((2.2 / 12) * Math.PI * 2) * 32} y2={300 - Math.cos((2.2 / 12) * Math.PI * 2) * 32} stroke={C.white} strokeWidth={6} strokeLinecap="round" />
      <line x1={520} y1={300} x2={520 + Math.sin(0.2 * Math.PI * 2 + t * 0.002) * 46} y2={300 - Math.cos(0.2 * Math.PI * 2 + t * 0.002) * 46} stroke={C.white} strokeWidth={4} strokeLinecap="round" />
      {/* desk + chair */}
      <WRect x={880} y={deskY} w={640} h={20} fill={C.propLight} seed={101} />
      <WLine pts={[[900, deskY + 20], [900, FLOOR]]} sw={6} seed={102} />
      <WLine pts={[[1500, deskY + 20], [1500, FLOOR]]} sw={6} seed={103} />
      <WRect x={1080} y={deskY - 16} w={220} h={16} fill="#2E2E33" seed={104} />
      <WPoly pts={[[1360, deskY - 44], [1392, deskY - 44], [1389, deskY], [1363, deskY]]} fill="#3A3A40" seed={105} />
      <WRect x={760} y={FLOOR - 104} w={120} h={14} fill={C.propLight} seed={106} />
      <WLine pts={[[764, FLOOR - 104], [756, FLOOR - 290]]} sw={7} seed={107} />
      <WLine pts={[[772, FLOOR - 90], [772, FLOOR]]} sw={5} seed={108} />
      <WLine pts={[[868, FLOOR - 90], [868, FLOOR]]} sw={5} seed={109} />
      {operator ? <Hero x={820} y={FLOOR} pose="sit" glasses brow={0.05} mouth={0} headTilt={-9} /> : null}
    </g>
  );
};

// ---------------------------------------------------------------- gauge readout, close-up
export const Readout: React.FC<{value: string; clock: number; pumps?: string; glitch?: number}> = ({value, clock, pumps = 'ON', glitch = 0}) => {
  const t = useCurrentFrame();
  const sec = Math.floor(clock + t / 30);
  const hh = String(Math.floor(sec / 3600) % 24).padStart(2, '0');
  const mm = String(Math.floor(sec / 60) % 60).padStart(2, '0');
  const ss = String(sec % 60).padStart(2, '0');
  const shown = glitch > 0 ? value.split('').map((c, i) => (c === '.' || random(`gl${Math.floor(t / 2)}${i}`) > glitch ? c : String(Math.floor(random(`gd${t}${i}`) * 10)))).join('') : value;
  return (
    <g>
      <Backdrop dark />
      <Glow x={960} y={540} r={1000} ry={620} color={C.screen} opacity={0.2} />
      <WRect x={250} y={150} w={1420} h={780} fill="#1A1A1D" sw={3} seed={110} />
      <rect x={290} y={190} width={1340} height={700} fill={C.screenBg} />
      {/* scanlines */}
      {Array.from({length: 70}, (_, i) => (
        <line key={i} x1={290} x2={1630} y1={190 + i * 10} y2={190 + i * 10} stroke="#FFFFFF" strokeWidth={1} opacity={0.025} />
      ))}
      <text x={340} y={270} fontFamily={LOOK.mono} fontWeight={700} fontSize={36} fill="#8A8A90">
        TAUM SAUK · UPPER RESERVOIR
      </text>
      <text x={1580} y={270} textAnchor="end" fontFamily={LOOK.mono} fontWeight={700} fontSize={36} fill="#8A8A90">
        {`${hh}:${mm}:${ss}`}
      </text>
      <line x1={340} x2={1580} y1={300} y2={300} stroke="#3A3A40" strokeWidth={2} />
      <text x={340} y={400} fontFamily={LOOK.mono} fontWeight={700} fontSize={40} fill="#B8B8BE">
        WATER LEVEL
      </text>
      <text x={960} y={600} textAnchor="middle" fontFamily={LOOK.mono} fontWeight={700} fontSize={190} fill={C.white}>
        {shown}
      </text>
      <text x={960} y={692} textAnchor="middle" fontFamily={LOOK.mono} fontWeight={700} fontSize={40} fill="#8A8A90">
        FEET ABOVE SEA LEVEL
      </text>
      <line x1={340} x2={1580} y1={740} y2={740} stroke="#3A3A40" strokeWidth={2} />
      <text x={340} y={820} fontFamily={LOOK.mono} fontWeight={700} fontSize={40} fill="#B8B8BE">
        {`PUMPS: ${pumps}`}
      </text>
      <text x={1580} y={820} textAnchor="end" fontFamily={LOOK.mono} fontWeight={700} fontSize={40} fill="#B8B8BE">
        STATUS: NORMAL
      </text>
    </g>
  );
};
// box around the big number on the readout
export const READ_BOX = {x: 960, y: 532, rx: 390, ry: 84};

// ---------------------------------------------------------------- pumped storage, cross-section diagram
export const PumpDiagram: React.FC<{day: number; level: number; flowDir: 1 | -1; flow: number}> = ({day, level, flowDir, flow}) => {
  const t = useCurrentFrame();
  const tunnel: Pt[] = [[610, 392], [650, 520], [1180, 780], [1290, 800], [1420, 840]];
  const ly = 390 - level * 60; // upper water surface
  const lowerY = 830 + level * 25;
  const ph: Pt = [1290, 800];
  const pole: Pt[] = [[1300, 730], [1500, 560], [1730, 640]];
  return (
    <g>
      <Sky dawn={0} moon={[1500, 180]} />
      <g opacity={day}>
        <rect x={0} y={0} width={1920} height={1080} fill="#2A2A2E" />
        <Glow x={1500} y={180} r={600} color={C.lamp} opacity={0.5} />
        <circle cx={1500} cy={180} r={52} fill={C.lamp} />
      </g>
      {/* ground and mountain */}
      <WPoly pts={[[-20, 1080], [-20, 420], [110, 330], [160, 330], [160, 400], [660, 400], [660, 330], [720, 330], [920, 450], [1160, 700], [1300, 820], [1920, 820], [1920, 1080]]} fill="#34343A" seed={120} />
      {/* upper reservoir */}
      <rect x={160} y={ly} width={500} height={400 - ly} fill={WATER} />
      <line x1={160} x2={660} y1={ly} y2={ly} stroke={SURF} strokeWidth={3} />
      {/* lower reservoir */}
      <path d={`M1360,820 L1360,${lowerY} L1640,${lowerY} L1640,820 Z`} fill="#0F0F11" />
      <rect x={1360} y={lowerY} width={280} height={880 - lowerY} fill={WATER} />
      <line x1={1360} x2={1640} y1={lowerY} y2={lowerY} stroke={SURF} strokeWidth={3} />
      <WRect x={1356} y={880} w={288} h={10} fill="#34343A" seed={121} />
      {/* the tunnel through the mountain */}
      <path d={d(tunnel)} stroke="#151517" strokeWidth={34} fill="none" strokeLinejoin="round" />
      <path d={d(tunnel)} stroke={WATER} strokeWidth={22} fill="none" strokeLinejoin="round" />
      {flow > 0 ? (
        <path d={d(tunnel)} stroke={FOAM} strokeWidth={6} fill="none" strokeDasharray="20 30" strokeDashoffset={flowDir * t * 5} opacity={0.8 * flow} strokeLinejoin="round" />
      ) : null}
      {/* powerhouse with pump-turbine */}
      <WRect x={ph[0] - 70} y={ph[1] - 90} w={140} h={90} fill="#4A4A50" seed={122} />
      <circle cx={ph[0]} cy={ph[1] - 40} r={28} fill="#26262A" stroke="#9A9AA0" strokeWidth={3} />
      {[0, 1, 2, 3].map((i) => {
        const a = (i / 4) * Math.PI * 2 + flowDir * t * 0.25 * flow;
        return <line key={i} x1={ph[0]} y1={ph[1] - 40} x2={ph[0] + Math.cos(a) * 24} y2={ph[1] - 40 + Math.sin(a) * 24} stroke={C.white} strokeWidth={4} />;
      })}
      <text x={ph[0]} y={ph[1] + 60} textAnchor="middle" fontFamily={LOOK.font} fontWeight={700} fontSize={36} fill={C.white} letterSpacing={3}>
        {day > 0.5 ? 'TURBINE' : 'PUMP'}
      </text>
      {/* power line to the town */}
      <path d={d(pole)} stroke="#8A8A90" strokeWidth={3} fill="none" />
      <WLine pts={[[1500, 560], [1500, 820]]} sw={6} seed={123} />
      <WLine pts={[[1470, 580], [1530, 580]]} sw={5} seed={124} />
      {Array.from({length: 5}, (_, i) => {
        const u = ((t * 0.012 + i / 5) % 1);
        const p = along(pole, flowDir === 1 ? 1 - u : u);
        return <circle key={i} cx={p[0]} cy={p[1]} r={7} fill={C.white} opacity={0.85 * flow} />;
      })}
      {/* town */}
      {[0, 1, 2, 3].map((i) => (
        <WRect key={i} x={1690 + i * 56} y={820 - 90 - (i % 2) * 50} w={48} h={90 + (i % 2) * 50} fill="#2A2A2E" seed={125 + i} />
      ))}
      {[0, 1, 2, 3].map((i) => (
        <rect key={'w' + i} x={1704 + i * 56} y={760 - (i % 2) * 40} width={16} height={14} fill="#E8E2D2" opacity={0.3 + 0.6 * (day > 0.5 ? 1 : 0.4)} />
      ))}
      <text x={1610} y={500} textAnchor="middle" fontFamily={LOOK.font} fontWeight={700} fontSize={32} fill="#B8B8BE" letterSpacing={3}>
        {day > 0.5 ? 'POWER OUT: SOLD' : 'POWER IN: CHEAP'}
      </text>
      <text x={410} y={300} textAnchor="middle" fontFamily={LOOK.font} fontWeight={700} fontSize={34} fill={C.white} letterSpacing={3}>
        UPPER RESERVOIR
      </text>
      <text x={1500} y={940} textAnchor="middle" fontFamily={LOOK.font} fontWeight={700} fontSize={30} fill="#9A9AA0" letterSpacing={3}>
        LOWER RESERVOIR
      </text>
    </g>
  );
};

// ---------------------------------------------------------------- a battery made of water and rock
export const Battery: React.FC<{charge: number; labels: number}> = ({charge, labels}) => {
  const t = useCurrentFrame();
  const x = 700;
  const y = 250;
  const w = 520;
  const h = 700;
  const wall = 54;
  const iy0 = y + wall;
  const ih = h - wall * 2;
  const wy = iy0 + ih * (1 - charge);
  const outer: Pt[] = [[x, y], [x + w, y], [x + w, y + h], [x, y + h]];
  return (
    <g>
      <Backdrop dark />
      <Glow x={960} y={600} r={800} ry={500} color={C.lamp} opacity={0.14} />
      <WRect x={x + 170} y={y - 50} w={180} h={50} fill="#5A5A60" seed={130} />
      <Stones poly={outer} box={[x, y, x + w, y + h]} seed="bat" size={30} />
      <rect x={x + wall} y={iy0} width={w - wall * 2} height={ih} fill="#0E0E10" />
      <rect x={x + wall} y={wy} width={w - wall * 2} height={iy0 + ih - wy} fill={WATER} />
      <path
        d={`M${x + wall},${wy} ${Array.from({length: 20}, (_, i) => `L${x + wall + ((i + 1) / 20) * (w - wall * 2)},${wy + Math.sin(i * 0.8 + t * 0.25) * 5}`).join(' ')}`}
        stroke={SURF}
        strokeWidth={3}
        fill="none"
      />
      {/* charge ticks */}
      {[0.25, 0.5, 0.75].map((k) => (
        <line key={k} x1={x + wall} x2={x + wall + 30} y1={iy0 + ih * (1 - k)} y2={iy0 + ih * (1 - k)} stroke="#8A8A90" strokeWidth={3} />
      ))}
      <polygon points={`${960 + 20},${560} ${930},${660} ${965},${660} ${940},${760} ${1000},${640} ${965},${640} ${990},${560}`} fill={C.white} opacity={0.15 + 0.75 * charge} />
      <Tag x={x + 20} y={y + 320} tx={x - 60} ty={y + 240} text="ROCK" o={labels} anchor="end" size={44} />
      <Tag x={x + w - 80} y={wy + 60} tx={x + w + 70} ty={wy - 10} text="WATER" o={labels} size={44} />
    </g>
  );
};

// ---------------------------------------------------------------- the wall, in cross-section (the recurring motif)
export const WS = {crest: 380, parTop: 250, parX0: 760, parX1: 800, crestX1: 1000, toeUp: 360, toeDown: 1500, ground: 900};
const faceX = (y: number) => (y <= WS.crest ? WS.parX0 : WS.parX0 - (y - WS.crest) * (400 / 520));
// the gauge pipe hangs down the inner face
const PB: Pt = [744, 392];
const PC: Pt = [488, 724];
const NRM: Pt = [-0.79, -0.61];
const qpt = (u: number, bow: number): Pt => {
  const mx = (PB[0] + PC[0]) / 2 + NRM[0] * bow * 120;
  const my = (PB[1] + PC[1]) / 2 + NRM[1] * bow * 120;
  return [(1 - u) ** 2 * PB[0] + 2 * u * (1 - u) * mx + u * u * PC[0], (1 - u) ** 2 * PB[1] + 2 * u * (1 - u) * my + u * u * PC[1]];
};
export const BRACKET_U = 0.5;
export const bracketXY = (): Pt => qpt(BRACKET_U, 0);
export const gaugeXY = (shift: number, bow = 0): Pt => qpt(0.84 - shift, bow);

export const WallSection: React.FC<{
  level: number; // water surface y
  labels?: number;
  pipe?: number; // 0..1 opacity
  bow?: number; // 0..1 pipe pulled off its brackets
  gaugeShift?: number; // 0..~0.3 gauge slid up the pipe
  ghost?: number; // where the gauge should be
  stopY?: number | null;
  stopO?: number;
  pumps?: 'ON' | 'OFF' | null;
  readY?: number | null; // what the gauges said
  readO?: number;
  probes?: number;
  overflow?: number;
  concrete?: number;
  night?: number;
}> = ({level, labels = 0, pipe = 0, bow = 0, gaugeShift = 0, ghost = 0, stopY = null, stopO = 1, pumps = null, readY = null, readO = 1, probes = 0, overflow = 0, concrete = 0}) => {
  const t = useCurrentFrame();
  const fill: Pt[] = [[WS.toeUp, WS.ground], [WS.parX0, WS.crest], [WS.crestX1, WS.crest], [WS.toeDown, WS.ground]];
  const water: Pt[] = concrete > 0
    ? [[-10, level], [718, level], [700, WS.ground], [-10, WS.ground]]
    : level < WS.crest
      ? [[-10, level], [WS.parX0, level], [WS.parX0, WS.crest], [WS.toeUp, WS.ground], [-10, WS.ground]]
      : [[-10, level], [faceX(level), level], [WS.toeUp, WS.ground], [-10, WS.ground]];
  const pipePts = Array.from({length: 21}, (_, i) => qpt(i / 20, bow));
  const pipeD = `M744,236 L${PB[0]},${PB[1]} ` + pipePts.map((p) => `L${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(' ');
  const g = gaugeXY(gaugeShift, bow);
  const g0 = gaugeXY(0, 0);
  const tan = Math.atan2(PC[1] - PB[1], PC[0] - PB[0]) * (180 / Math.PI);
  const over: Pt[] = [[740, level], [800, WS.parTop - 2], [814, 300], [824, WS.crest - 2], [WS.crestX1, WS.crest + 2], [WS.toeDown, WS.ground + 2], [1720, WS.ground + 2]];
  return (
    <g>
      <rect x={0} y={0} width={1920} height={1080} fill={C.bg} />
      <Glow x={1500} y={160} r={500} color={C.moon} opacity={0.18} />
      <circle cx={1500} cy={160} r={30} fill={C.moon} opacity={0.75} />
      <rect x={0} y={WS.ground} width={1920} height={180} fill={C.bgFloor} />
      <line x1={0} x2={1920} y1={WS.ground} y2={WS.ground} stroke={C.floorLine} strokeWidth={2} />
      {/* the reservoir */}
      <path d={d(water) + ' Z'} fill={WATER} />
      <line x1={0} x2={concrete > 0 ? 718 : faceX(level)} y1={level} y2={level} stroke={SURF} strokeWidth={3} />
      {Array.from({length: 6}, (_, i) => (
        <line key={i} x1={80 + i * 110 + Math.sin(t / 25 + i) * 12} x2={130 + i * 110 + Math.sin(t / 25 + i) * 12} y1={level + 24 + (i % 3) * 26} y2={level + 24 + (i % 3) * 26} stroke={SURF} strokeWidth={2} opacity={0.25} />
      ))}
      {/* the wall: piled rock, or (rebuilt) solid concrete */}
      <Stones poly={fill} box={[WS.toeUp, WS.crest, WS.toeDown, WS.ground]} seed="ws" size={34} opacity={1 - concrete} />
      {concrete > 0 ? (
        <g opacity={concrete}>
          <WPoly pts={[[700, WS.ground], [720, WS.parTop], [WS.crestX1, WS.parTop], [1300, WS.ground]]} fill="#8E8E94" seed={140} />
          {Array.from({length: 26}, (_, i) => {
            const y = WS.parTop + 20 + i * 24;
            const xl = 720 - ((y - WS.parTop) / (WS.ground - WS.parTop)) * 20;
            const xr = WS.crestX1 + ((y - WS.parTop) / (WS.ground - WS.parTop)) * 300;
            return <line key={i} x1={xl + 4} x2={xr - 4} y1={y} y2={y} stroke="#6E6E74" strokeWidth={2} />;
          })}
        </g>
      ) : null}
      {/* concrete parapet on top */}
      <g opacity={1 - concrete}>
        <WRect x={WS.parX0} y={WS.parTop} w={WS.parX1 - WS.parX0} h={WS.crest - WS.parTop} fill="#9A9AA0" seed={141} />
      </g>
      {/* overtopping water */}
      {overflow > 0.01 ? (
        <g>
          <path d={d(partial(over, overflow))} stroke={FOAM} strokeWidth={14} fill="none" strokeLinecap="round" strokeLinejoin="round" opacity={0.85} />
          <path d={d(partial(over, overflow))} stroke="#FFFFFF" strokeWidth={4} fill="none" strokeDasharray="18 22" strokeDashoffset={-t * 7} opacity={0.8} />
        </g>
      ) : null}
      {/* gauge pipe with its brackets */}
      {pipe > 0 ? (
        <g opacity={pipe}>
          {[0.12, BRACKET_U, 0.86].map((u) => {
            const p = qpt(u, 0);
            return (
              <g key={u}>
                <line x1={p[0] - NRM[0] * 14} y1={p[1] - NRM[1] * 14} x2={p[0] + NRM[0] * 12} y2={p[1] + NRM[1] * 12} stroke="#111113" strokeWidth={15} strokeLinecap="round" />
                <line x1={p[0] - NRM[0] * 14} y1={p[1] - NRM[1] * 14} x2={p[0] + NRM[0] * 12} y2={p[1] + NRM[1] * 12} stroke="#77777D" strokeWidth={9} strokeLinecap="round" />
              </g>
            );
          })}
          <path d={pipeD} stroke="#1A1A1D" strokeWidth={22} fill="none" strokeLinejoin="round" />
          <path d={pipeD} stroke="#8A8A90" strokeWidth={15} fill="none" strokeLinejoin="round" opacity={0.75} />
          <line x1={744} y1={236} x2={g[0]} y2={g[1]} stroke="#26262A" strokeWidth={2} opacity={0} />
          {ghost > 0 ? (
            <g opacity={ghost} transform={`rotate(${tan} ${g0[0]} ${g0[1]})`}>
              <rect x={g0[0] - 20} y={g0[1] - 9} width={40} height={18} rx={8} fill="none" stroke={C.white} strokeWidth={2.5} strokeDasharray="5 4" />
            </g>
          ) : null}
          <g transform={`rotate(${tan} ${g[0]} ${g[1]})`}>
            <rect x={g[0] - 20} y={g[1] - 9} width={40} height={18} rx={8} fill={C.white} stroke="#1A1A1D" strokeWidth={2} />
          </g>
        </g>
      ) : null}
      {pumps ? (
        <g>
          <path d={`M744,236 Q760,200 840,200`} stroke="#55555A" strokeWidth={3} fill="none" />
          <WRect x={840} y={168} w={230} h={64} fill="#1A1A1D" seed={142} />
          <text x={955} y={214} textAnchor="middle" fontFamily={LOOK.mono} fontWeight={700} fontSize={34} fill={C.white}>
            {`PUMPS ${pumps}`}
          </text>
          {pumps === 'OFF' ? <Glow x={955} y={200} r={140} ry={60} color={C.white} opacity={0.35} /> : null}
        </g>
      ) : null}
      {probes > 0 ? (
        <g opacity={probes}>
          {[752, 730].map((x, i) => (
            <g key={i}>
              <line x1={x} y1={226 - i * 6} x2={x} y2={258} stroke="#D8D8DC" strokeWidth={5} />
              <line x1={x} y1={226 - i * 6} x2={782} y2={226 - i * 6} stroke="#D8D8DC" strokeWidth={4} />
              <circle cx={x} cy={262} r={7} fill={C.white} />
            </g>
          ))}
        </g>
      ) : null}
      {stopY !== null ? (
        <g opacity={stopO}>
          <line x1={60} x2={720} y1={stopY} y2={stopY} stroke={C.white} strokeWidth={3} strokeDasharray="16 12" />
          <text x={220} y={stopY - 16} fontFamily={LOOK.font} fontWeight={700} fontSize={32} fill={C.white} letterSpacing={3}>
            STOP LINE
          </text>
        </g>
      ) : null}
      {readY !== null ? (
        <g opacity={readO}>
          <line x1={200} x2={720} y1={readY} y2={readY} stroke={C.white} strokeWidth={3} strokeDasharray="16 12" />
          <text x={220} y={readY + 46} fontFamily={LOOK.font} fontWeight={700} fontSize={32} fill="#B8B8BE" letterSpacing={3}>
            WHAT THE GAUGES SAID
          </text>
          <text x={220} y={level - 16} fontFamily={LOOK.font} fontWeight={700} fontSize={32} fill={C.white} letterSpacing={3}>
            THE REAL WATER
          </text>
        </g>
      ) : null}
      {labels > 0 ? (
        <g opacity={labels}>
          <text x={930} y={720} textAnchor="middle" fontFamily={LOOK.font} fontWeight={700} fontSize={44} fill={C.white} letterSpacing={6} style={{paintOrder: 'stroke'}} stroke="#0B0B0C" strokeWidth={8}>
            {concrete > 0.5 ? 'SOLID CONCRETE' : 'PILED ROCK'}
          </text>
          {concrete < 0.5 ? <Tag x={800} y={290} tx={900} ty={250} text="CONCRETE WALL ON TOP" /> : null}
          <text x={300} y={700} textAnchor="middle" fontFamily={LOOK.font} fontWeight={700} fontSize={40} fill="#8A8A90" letterSpacing={6}>
            RESERVOIR
          </text>
        </g>
      ) : null}
    </g>
  );
};

// ---------------------------------------------------------------- the crest, seen along its length from inside
const gau = (x: number, c: number, w: number) => Math.exp(-(((x - c) / w) ** 2));
export const crestY = (x: number) => 300 + 18 * gau(x, 520, 140) + 46 * gau(x, 1060, 170);
export const LOW_X = 1060;
export const LOW_Y = crestY(LOW_X);
export const PROBE_Y = 322;
export const BREACH: [number, number] = [740, 1400];

export const CrestView: React.FC<{level: number; lines?: number; breach?: number; spill?: number}> = ({level, lines = 0, breach = 0, spill = 0}) => {
  const t = useCurrentFrame();
  const xs = Array.from({length: 49}, (_, i) => i * 40);
  const top = xs.map((x) => [x, crestY(x)] as Pt);
  const parBot = 410;
  const chunks = 6;
  const cw = (BREACH[1] - BREACH[0]) / chunks;
  const inGap = (x: number) => breach > 0 && x > BREACH[0] && x < BREACH[1];
  return (
    <g>
      <rect x={0} y={0} width={1920} height={1080} fill={C.bg} />
      <Glow x={300} y={150} r={460} color={C.moon} opacity={0.2} />
      <circle cx={300} cy={150} r={28} fill={C.moon} opacity={0.7} />
      {/* rock face below the parapet */}
      <Stones poly={[[0, parBot - 6], [1920, parBot - 6], [1920, 1080], [0, 1080]]} box={[0, parBot - 6, 1920, 1080]} seed="cv" size={46} />
      {/* parapet band (intact parts) */}
      <path d={`M0,${parBot} L${top.map((p) => p.join(',')).join(' L')} L1920,${parBot} Z`} fill="#9A9AA0" />
      {[200, 600, 1000, 1400, 1800].map((x) => (
        <line key={x} x1={x} x2={x} y1={crestY(x)} y2={parBot} stroke="#77777D" strokeWidth={2} />
      ))}
      {/* the breach: the gap opens, pieces fall away */}
      {breach > 0 ? (
        <g>
          <path d={`M${BREACH[0]},${crestY(BREACH[0]) - 4} L${BREACH[1]},${crestY(BREACH[1]) - 4} L${BREACH[1] - 40 * breach},1080 L${BREACH[0] + 40 * breach},1080 Z`} fill="#060607" opacity={Math.min(1, breach * 3)} />
          {Array.from({length: chunks}, (_, i) => {
            const x0 = BREACH[0] + i * cw;
            const fall = Math.max(0, breach * 1.6 - i * 0.08) ** 2 * (700 + i * 40);
            return (
              <g key={i} transform={`translate(0 ${fall}) rotate(${fall * 0.02 * (i % 2 ? 1 : -1)} ${x0 + cw / 2} ${crestY(x0) + 60})`} opacity={Math.max(0, 1 - fall / 140)}>
                <path d={`M${x0},${crestY(x0)} L${x0 + cw},${crestY(x0 + cw)} L${x0 + cw},${parBot + 60} L${x0},${parBot + 60} Z`} fill="#8A8A90" stroke="#4A4A50" strokeWidth={3} />
              </g>
            );
          })}
          {/* water pours through */}
          {Array.from({length: 14}, (_, i) => {
            const x = BREACH[0] + 40 + i * ((BREACH[1] - BREACH[0] - 80) / 13);
            return <line key={i} x1={x} x2={x + 10 * Math.sin(i)} y1={level} y2={1080} stroke={FOAM} strokeWidth={14} strokeDasharray="60 30" strokeDashoffset={-t * 22 - i * 13} opacity={0.6 * Math.min(1, breach * 2)} />;
          })}
        </g>
      ) : null}
      {/* reservoir water in front of us */}
      <rect x={0} y={level} width={1920} height={1080 - level} fill={WATER} />
      <path d={`M0,${level} ${xs.map((x) => `L${x},${level + Math.sin(x / 60 + t * 0.15) * (inGap(x) ? 10 : 3)}`).join(' ')} L1920,${level}`} stroke={SURF} strokeWidth={3} fill="none" />
      {/* foam where the water rushes into the gap */}
      {breach > 0 ? (
        <g opacity={Math.min(1, breach * 2)}>
          <Glow x={(BREACH[0] + BREACH[1]) / 2} y={level} r={420} ry={70} color={C.white} opacity={0.55} />
          {Array.from({length: 9}, (_, i) => {
            const x = BREACH[0] + 60 + i * ((BREACH[1] - BREACH[0] - 120) / 8);
            return <line key={i} x1={x - 30} x2={x + 30} y1={level + 6 + (i % 3) * 8} y2={level + 6 + (i % 3) * 8} stroke={FOAM} strokeWidth={8} strokeLinecap="round" strokeDasharray="24 18" strokeDashoffset={-t * 4 - i * 9} opacity={0.8} />;
          })}
        </g>
      ) : null}
      {/* spilling over the low spot */}
      {spill > 0 ? (
        <g opacity={spill}>
          {[-60, -20, 20, 60].map((dx, i) => (
            <path key={i} d={`M${LOW_X + dx},${crestY(LOW_X + dx) - 2} l${dx * 0.1},-10`} stroke={FOAM} strokeWidth={10} strokeLinecap="round" opacity={0.6 + 0.4 * Math.sin(t / 3 + i)} />
          ))}
          <Glow x={LOW_X} y={LOW_Y} r={200} ry={60} color={C.white} opacity={0.4} />
        </g>
      ) : null}
      {/* backup probes */}
      {[360, 1600].map((x, i) => (
        <g key={i}>
          <WRect x={x - 18} y={crestY(x) - 30} w={36} h={30} fill="#2A2A2E" seed={150 + i} />
          <line x1={x} y1={crestY(x) - 10} x2={x} y2={PROBE_Y} stroke="#D8D8DC" strokeWidth={6} />
          <circle cx={x} cy={PROBE_Y + 4} r={9} fill={C.white} />
        </g>
      ))}
      {lines > 0 ? (
        <g opacity={lines}>
          <line x1={60} x2={1860} y1={PROBE_Y + 4} y2={PROBE_Y + 4} stroke={C.white} strokeWidth={3} strokeDasharray="14 12" />
          <text x={420} y={PROBE_Y - 66} fontFamily={LOOK.font} fontWeight={700} fontSize={34} fill={C.white} letterSpacing={3}>
            BACKUP PROBES TRIGGER HERE
          </text>
          <line x1={410} x2={370} y1={PROBE_Y - 60} y2={PROBE_Y - 4} stroke={C.white} strokeWidth={2.5} />
          <line x1={LOW_X - 260} x2={LOW_X + 260} y1={LOW_Y} y2={LOW_Y} stroke={C.white} strokeWidth={3} strokeDasharray="6 8" opacity={0.8} />
          <text x={LOW_X} y={LOW_Y + 140} textAnchor="middle" fontFamily={LOOK.font} fontWeight={700} fontSize={34} fill={C.white} letterSpacing={3} style={{paintOrder: 'stroke'}} stroke="#0B0B0C" strokeWidth={8}>
            LOWEST POINT OF THE WALL
          </text>
          <line x1={LOW_X} x2={LOW_X} y1={LOW_Y + 104} y2={LOW_Y + 20} stroke={C.white} strokeWidth={2.5} />
        </g>
      ) : null}
    </g>
  );
};

// ---------------------------------------------------------------- the night, drawn as data
const CX0 = 330;
const CX1 = 1620;
const CY0 = 860;
export const chartX = (h: number) => CX0 + (h / 5.5) * (CX1 - CX0);
export const WALL_Y = 300;
const gaugeY = (h: number) => 780 - 380 * (1 - Math.exp(-h / 1.6)) / (1 - Math.exp(-5 / 1.6));
export const chartGauge = (h: number) => Math.max(400, gaugeY(Math.min(h, 5)));
export const chartReal = (h: number) => Math.max(WALL_Y, chartGauge(h) - 100);
export const HIT_H = 5.16;

export const LevelChart: React.FC<{gauge: number; room: number; real: number}> = ({gauge, room, real}) => {
  const N = 60;
  const pts = (fn: (h: number) => number, u: number): Pt[] => {
    const n = Math.max(2, Math.round(N * u));
    return Array.from({length: n}, (_, i) => {
      const h = (i / (n - 1)) * 5.5 * u;
      return [chartX(h), fn(h)] as Pt;
    });
  };
  const gPts = pts(chartGauge, gauge);
  const rPts = pts(chartReal, real);
  const hit: Pt = [chartX(HIT_H - 0.1), WALL_Y];
  const end = gPts[gPts.length - 1];
  return (
    <g>
      <Backdrop dark />
      <Glow x={960} y={300} r={1100} ry={600} color={C.lamp} opacity={0.1} />
      {/* axes */}
      <line x1={CX0} x2={CX1} y1={CY0} y2={CY0} stroke="#6A6A70" strokeWidth={3} />
      <line x1={CX0} x2={CX0} y1={200} y2={CY0} stroke="#6A6A70" strokeWidth={3} />
      {['MIDNIGHT', '1 AM', '2 AM', '3 AM', '4 AM', '5 AM'].map((s, i) => (
        <g key={s}>
          <line x1={chartX(i)} x2={chartX(i)} y1={CY0} y2={CY0 + 14} stroke="#6A6A70" strokeWidth={3} />
          <text x={chartX(i)} y={CY0 + 56} textAnchor="middle" fontFamily={LOOK.font} fontWeight={700} fontSize={30} fill="#8A8A90" letterSpacing={2}>
            {s}
          </text>
        </g>
      ))}
      <text x={CX0 - 30} y={540} textAnchor="middle" fontFamily={LOOK.font} fontWeight={700} fontSize={30} fill="#8A8A90" letterSpacing={4} transform={`rotate(-90 ${CX0 - 30} 540)`}>
        WATER LEVEL
      </text>
      {/* top of the wall */}
      <line x1={CX0} x2={CX1 + 40} y1={WALL_Y} y2={WALL_Y} stroke={C.white} strokeWidth={4} strokeDasharray="18 12" />
      <text x={CX0 + 20} y={WALL_Y - 20} fontFamily={LOOK.font} fontWeight={700} fontSize={34} fill={C.white} letterSpacing={3}>
        TOP OF THE WALL
      </text>
      {/* what the gauges said */}
      <path d={d(gPts)} stroke={C.white} strokeWidth={7} fill="none" strokeLinecap="round" strokeLinejoin="round" />
      {gauge > 0.3 ? (
        <text x={chartX(2.6)} y={chartGauge(2.6) + 70} fontFamily={LOOK.font} fontWeight={700} fontSize={34} fill="#D8D8DC" letterSpacing={3} opacity={Math.min(1, (gauge - 0.3) * 4)}>
          WHAT THE GAUGES SAID
        </text>
      ) : null}
      <circle cx={end[0]} cy={end[1]} r={9} fill={C.white} />
      {/* "room to spare" */}
      {room > 0 ? (
        <g opacity={room}>
          <path d={`M${chartX(5.4)},${WALL_Y + 8} L${chartX(5.4) + 16},${WALL_Y + 8} L${chartX(5.4) + 16},392 L${chartX(5.4)},392`} stroke="#B8B8BE" strokeWidth={3} fill="none" />
          <text x={chartX(5.4) + 30} y={360} textAnchor="start" fontFamily={LOOK.font} fontWeight={700} fontSize={28} fill="#B8B8BE" letterSpacing={3}>
            ROOM TO SPARE
          </text>
        </g>
      ) : null}
      {/* the real water */}
      {real > 0.01 ? (
        <g>
          <path d={d(rPts)} stroke={C.accent} strokeWidth={7} fill="none" strokeLinecap="round" strokeLinejoin="round" style={{filter: `drop-shadow(0 0 6px ${C.accent})`}} />
          <text x={chartX(1.6)} y={chartReal(1.6) - 30} fontFamily={LOOK.font} fontWeight={700} fontSize={34} fill={C.accent} letterSpacing={3} opacity={Math.min(1, real * 3)}>
            THE REAL WATER
          </text>
          {real > 0.93 ? <circle cx={hit[0]} cy={hit[1]} r={12} fill={C.accent} /> : null}
        </g>
      ) : null}
    </g>
  );
};
export const CHART_HIT: Pt = [chartX(HIT_H - 0.1), WALL_Y];

// ---------------------------------------------------------------- the park, top-down
export const PARK_HOUSE: Pt = [1210, 744];
const RIVER: Pt[] = [[980, 1090], [1040, 960], [1120, 860], [1200, 790], [1300, 720], [1420, 650], [1560, 610], [1720, 560], [1940, 520]];
const FLOODPATH: Pt[] = [[600, 360], [680, 440], [780, 520], [900, 600], [1020, 670], [1120, 720], [1210, 750], [1300, 790], [1400, 850]];
export const ParkMap: React.FC<{flood: number; labels: number}> = ({flood, labels}) => {
  const t = useCurrentFrame();
  const path = partial(FLOODPATH, flood);
  return (
    <g>
      <rect x={0} y={0} width={1920} height={1080} fill="#121214" />
      {/* contour lines of the mountain */}
      {Array.from({length: 7}, (_, i) => (
        <ellipse key={i} cx={520} cy={330} rx={160 + i * 80} ry={110 + i * 58} fill="none" stroke="#3A3A40" strokeWidth={2} opacity={0.7} />
      ))}
      <WPoly pts={kidney(520, 330, 120, 70, 1)} fill="#8A8A90" seed={160} />
      <WPoly pts={kidney(520, 330, 120, 70, 0.9)} fill={WATER} seed={161} />
      <text x={520} y={210} textAnchor="middle" fontFamily={LOOK.font} fontWeight={700} fontSize={30} fill="#9A9AA0" letterSpacing={3}>
        PROFFIT MOUNTAIN
      </text>
      {/* park boundary */}
      <path d="M940,640 Q1100,560 1360,600 L1560,700 Q1600,860 1400,940 L1100,960 Q940,880 940,640 Z" fill="none" stroke="#8A8A90" strokeWidth={3} strokeDasharray="14 10" opacity={labels} />
      <text x={1600} y={1000} textAnchor="end" fontFamily={LOOK.font} fontWeight={700} fontSize={34} fill="#B8B8BE" letterSpacing={3} opacity={labels}>
        {"JOHNSON'S SHUT-INS STATE PARK"}
      </text>
      {/* river */}
      <path d={d(RIVER)} stroke="#4A4E55" strokeWidth={16} fill="none" strokeLinecap="round" />
      <text x={1690} y={520} textAnchor="middle" fontFamily={LOOK.font} fontWeight={700} fontSize={26} fill="#77777D" letterSpacing={3} opacity={labels}>
        BLACK RIVER
      </text>
      {/* the flood path */}
      {flood > 0.01 ? (
        <g>
          <path d={d(path)} stroke={FOAM} strokeWidth={70} fill="none" strokeLinecap="round" strokeLinejoin="round" opacity={0.35} />
          <path d={d(path)} stroke={FOAM} strokeWidth={30} fill="none" strokeLinecap="round" strokeLinejoin="round" opacity={0.75} />
          <path d={d(path)} stroke="#FFFFFF" strokeWidth={5} fill="none" strokeDasharray="20 30" strokeDashoffset={-t * 6} opacity={0.7} />
        </g>
      ) : null}
      {/* the superintendent's home */}
      <g transform={`translate(${PARK_HOUSE[0]} ${PARK_HOUSE[1]})`}>
        <rect x={-18} y={-14} width={36} height={28} fill={C.white} />
        <polygon points="-24,-14 0,-34 24,-14" fill={C.white} />
      </g>
      <Tag x={PARK_HOUSE[0] + 26} y={PARK_HOUSE[1] - 30} tx={PARK_HOUSE[0] + 90} ty={PARK_HOUSE[1] - 110} text="SUPERINTENDENT'S HOME" o={labels} size={32} />
    </g>
  );
};

// ---------------------------------------------------------------- evidence: an ID card
export const IdCard: React.FC = () => {
  const id = useId().replace(/:/g, '');
  return (
    <g>
      <Backdrop dark />
      <Glow x={1300} y={150} r={1000} color={C.lamp} opacity={0.32} />
      <g transform="rotate(-3 960 540)">
        <rect x={500} y={262} width={940} height={580} rx={26} fill="#000" opacity={0.35} />
        <rect x={486} y={246} width={940} height={580} rx={26} fill={PAPER} stroke="#8A8A90" strokeWidth={2} />
        <path d="M486,272 Q486,246 512,246 L1400,246 Q1426,246 1426,272 L1426,340 L486,340 Z" fill="#3A3A40" />
        <text x={540} y={308} fontFamily={LOOK.font} fontWeight={700} fontSize={40} fill="#E6E6EA" letterSpacing={6}>
          MISSOURI STATE PARKS
        </text>
        <rect x={540} y={390} width={260} height={330} fill="#55555A" />
        <defs>
          <clipPath id={id}>
            <rect x={540} y={390} width={260} height={330} />
          </clipPath>
        </defs>
        <g clipPath={`url(#${id})`}>
          <Hero x={650} y={1060} scale={1.55} brow={-0.05} mouth={0.25} />
        </g>
        <text x={850} y={440} fontFamily={LOOK.mono} fontWeight={700} fontSize={26} fill="#5A5A60">
          NAME
        </text>
        <text x={850} y={500} fontFamily={LOOK.display} fontSize={66} fill={INK} letterSpacing={2}>
          JERRY TOOPS
        </text>
        <text x={850} y={570} fontFamily={LOOK.mono} fontWeight={700} fontSize={26} fill="#5A5A60">
          POSITION
        </text>
        <text x={850} y={616} fontFamily={LOOK.mono} fontWeight={700} fontSize={36} fill={INK}>
          PARK SUPERINTENDENT
        </text>
        <text x={850} y={680} fontFamily={LOOK.mono} fontWeight={700} fontSize={26} fill="#5A5A60">
          {"JOHNSON'S SHUT-INS STATE PARK"}
        </text>
        <text x={850} y={720} fontFamily={LOOK.mono} fontWeight={700} fontSize={26} fill="#5A5A60">
          LIVES ON SITE
        </text>
        {Array.from({length: 30}, (_, i) => (
          <rect key={i} x={1200 + i * 6} y={760} width={random(`bc${i}`) > 0.5 ? 3 : 1.5} height={44} fill={INK} />
        ))}
      </g>
    </g>
  );
};

// ---------------------------------------------------------------- the house is swept away
export const SweptHouse: React.FC<{wave: number; lift: number}> = ({wave, lift}) => {
  const t = useCurrentFrame();
  const wx = -300 + wave * 1700; // front of the wave
  const wl = FLOOR - 40 - lift * 170; // water height behind the front
  const hx = 1180 + lift * 340;
  const hy = FLOOR - lift * 150;
  const rot = lift * 9;
  return (
    <g>
      <Ground floor={FLOOR} />
      <Glow x={1800} y={FLOOR} r={1200} ry={500} color={C.lamp} opacity={0.12} />
      {[220, 420, 1650, 1820].map((x, i) => (wave > 0.1 && x < wx ? null : <Tree key={i} x={x} y={FLOOR} h={160 + (i % 2) * 40} />))}
      <g transform={`translate(${hx} ${hy}) rotate(${rot})`}>
        <WRect x={-200} y={-240} w={400} h={240} fill="#3A3A3F" seed={170} />
        <WPoly pts={[[-240, -236], [0, -380], [240, -236]]} fill="#2A2A2E" seed={171} />
        <rect x={-150} y={-180} width={80} height={70} fill="#EDE6D4" opacity={lift > 0.3 ? 0.2 : 0.85} />
        {lift < 0.3 ? <Glow x={-110} y={-145} r={160} color={C.lamp} opacity={0.6} /> : null}
        <rect x={40} y={-140} width={70} height={140} fill="#18181B" />
      </g>
      {/* the wave */}
      {wave > 0 ? (
        <g>
          <path
            d={`M-20,1080 L-20,${wl} ${Array.from({length: 30}, (_, i) => {
              const x = -20 + (i / 29) * (wx + 20);
              return `L${x},${wl + Math.sin(i * 0.9 + t * 0.4) * 10}`;
            }).join(' ')} Q${wx + 120},${wl - 30} ${wx + 160},${FLOOR - 10} L${wx + 200},1080 Z`}
            fill={WATER}
          />
          <path
            d={`M-20,${wl} ${Array.from({length: 30}, (_, i) => `L${-20 + (i / 29) * (wx + 20)},${wl + Math.sin(i * 0.9 + t * 0.4) * 10}`).join(' ')} Q${wx + 120},${wl - 30} ${wx + 160},${FLOOR - 10}`}
            stroke={FOAM}
            strokeWidth={10}
            fill="none"
            opacity={0.85}
          />
          <Glow x={wx + 100} y={wl + 40} r={260} color={C.white} opacity={0.35} />
        </g>
      ) : null}
    </g>
  );
};

// ---------------------------------------------------------------- generic evidence paper
export const Doc: React.FC<{title: string; lines: string[]; tilt?: number; typed?: number; stamp?: string; stampO?: number; children?: React.ReactNode}> = ({title, lines, tilt = -1.5, typed = 999, stamp, stampO = 0, children}) => (
  <g>
    <Backdrop dark />
    <Glow x={1300} y={120} r={1000} color={C.lamp} opacity={0.34} />
    <g transform={`rotate(${tilt} 960 540)`}>
      <rect x={470} y={142} width={980} height={810} fill="#000" opacity={0.35} />
      <WRect x={460} y={130} w={980} h={810} fill={PAPER} stroke="#8A8A90" sw={2} seed={180} />
      <text x={530} y={220} fontFamily={LOOK.font} fontWeight={700} fontSize={46} fill={INK} letterSpacing={3}>
        {title}
      </text>
      <line x1={530} x2={1370} y1={248} y2={248} stroke="#6A6A70" strokeWidth={2} />
      {lines.map((l, i) => (
        <text key={i} x={530} y={330 + i * 92} fontFamily={LOOK.mono} fontWeight={700} fontSize={38} fill={INK}>
          {l.slice(0, Math.max(0, Math.floor(typed) - i * 14))}
        </text>
      ))}
      {stamp && stampO > 0 ? (
        <g transform="rotate(-10 1180 830)" opacity={stampO}>
          <rect x={1000} y={780} width={340} height={96} fill="none" stroke={C.accent} strokeWidth={7} />
          <text x={1170} y={850} textAnchor="middle" fontFamily={LOOK.display} fontSize={62} fill={C.accent} letterSpacing={6}>
            {stamp}
          </text>
        </g>
      ) : null}
      {children}
    </g>
  </g>
);

// ---------------------------------------------------------------- night log on the desk (nobody noticed)
export const NightLog: React.FC<{rows: number}> = ({rows}) => {
  const t = useCurrentFrame();
  const entries = ['00:00   LEVEL OK   PUMPING', '01:00   LEVEL OK   PUMPING', '02:00   LEVEL OK   PUMPING', '03:00   LEVEL OK   PUMPING', '04:00   LEVEL OK   PUMPING'];
  return (
    <g>
      <rect x={0} y={0} width={1920} height={1080} fill="#151517" />
      <Glow x={1200} y={300} r={900} color={C.lamp} opacity={0.4} />
      <Glow x={300} y={120} r={700} color={C.screen} opacity={0.18} />
      <g transform="rotate(-4 900 560)">
        <rect x={360} y={180} width={900} height={800} fill="#000" opacity={0.3} />
        <WRect x={350} y={170} w={900} h={800} fill={PAPER} stroke="#8A8A90" sw={2} seed={190} />
        <text x={410} y={250} fontFamily={LOOK.font} fontWeight={700} fontSize={44} fill={INK} letterSpacing={3}>
          NIGHT LOG · DEC 13-14
        </text>
        <line x1={410} x2={1190} y1={278} y2={278} stroke="#6A6A70" strokeWidth={2} />
        {entries.slice(0, rows).map((e, i) => (
          <text key={i} x={410} y={360 + i * 80} fontFamily={LOOK.mono} fontWeight={700} fontSize={36} fill={INK}>
            {e}
          </text>
        ))}
      </g>
      {/* mug with steam */}
      <WPoly pts={[[1380, 600], [1560, 600], [1550, 820], [1390, 820]]} fill="#5A5A60" sw={3} seed={191} />
      <WCircle cx={1590} cy={700} r={44} fill="none" sw={14} stroke="#5A5A60" seed={192} />
      {[0, 1, 2].map((k) => (
        <path key={k} d={`M${1420 + k * 50},590 q ${Math.sin(t * 0.12 + k) * 20},-50 0,-100 q ${-Math.sin(t * 0.12 + k) * 20},-50 0,-100`} stroke="#8A8A90" strokeWidth={6} fill="none" opacity={0.3} strokeLinecap="round" />
      ))}
    </g>
  );
};

import {loadFont} from '@remotion/google-fonts/ComicNeue';

const {fontFamily} = loadFont('normal', {weights: ['400', '700'], subsets: ['latin']});

export const FONT = fontFamily;

export const W = 1920;
export const H = 1080;
export const FPS = 30;
export const BAR = 54; // letterbox bar height
export const FLOOR = 860; // y of the floor line in wide shots

export const BASE_C = {
  bg: '#0E0E13',
  bgFloor: '#09090C',
  bgDark: '#050507', // close-up backgrounds
  floorLine: '#3A3A42',
  outline: '#8A8A94',
  prop: '#1A1A21',
  propLight: '#24242C',
  hero: '#5FA8A0',
  heroDark: '#4A8A83',
  heroFace: '#101417',
  accent: '#FF3B4E',
  white: '#F4F4F6',
  lamp: '#FFC36B',
  screen: '#7FC4FF',
  screenBg: '#06090D',
  term: '#9FF0C8',
  error: '#FF5A5A',
  led: '#5CFF8A',
  moon: '#DDE6FF',
  street: '#FFB25C',
};

export type Palette = typeof BASE_C;

// A "look" is a complete art style. The channel's own look is DEFAULT_LOOK;
// style tests swap in others (see src/looks.ts) without touching any scene code.
export type Look = {
  name: string;
  palette: Partial<Palette>;
  font: string; // narrator, HUD, shadow lines
  mono: string; // screens and terminals
  display: string; // rep pops, bursts
  fontScale: number;
  monoScale: number;
  lineOnly: boolean; // props drawn as outlines only
  lineFill: string; // prop fill when lineOnly ('none' or a faint colour)
  tint: [string, number] | null; // blend every prop fill toward a colour
  strokeScale: number; // prop outline thickness multiplier
  wobble: number; // hand-drawn wobble multiplier
  glow: 'soft' | 'neon' | 'hatch' | 'chalk';
  glowStrength: number; // light glow multiplier
  heroLimb: number; // limb thickness
  heroBorder: number; // border width each side
  heroBorderColor: string;
  heroLine: boolean; // line-art figure: single strokes, hollow head
  heroHeadFill: string; // head fill when heroLine
  caption: boolean; // narrator in comic caption boxes
  burst: boolean; // comic "POW" burst on big hits
  annotate: boolean; // blueprint dimension lines
  heroShade: boolean; // clay-like shaded head
  markers: boolean; // red hand-drawn marker circles on key moments
  uppercase: boolean; // narrator in caps
  popStyle: 'glow' | 'headline'; // rep pop styling
};

export const DEFAULT_LOOK: Look = {
  name: 'default',
  palette: {},
  font: fontFamily,
  mono: fontFamily,
  display: fontFamily,
  fontScale: 1,
  monoScale: 1,
  lineOnly: false,
  lineFill: 'none',
  tint: null,
  strokeScale: 1,
  wobble: 1,
  glow: 'soft',
  glowStrength: 1,
  heroLimb: 15,
  heroBorder: 4.5,
  heroBorderColor: '#000',
  heroLine: false,
  heroHeadFill: 'none',
  caption: false,
  burst: false,
  annotate: false,
  heroShade: false,
  markers: false,
  uppercase: false,
  popStyle: 'glow',
};

// Live values every component reads. A composition calls applyLook() first,
// before its children render.
export const C: Palette = {...BASE_C};
export const LOOK: Look = {...DEFAULT_LOOK};

export const applyLook = (look: Look) => {
  Object.assign(C, BASE_C, look.palette);
  Object.assign(LOOK, look);
};

const hex = (h: string) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));

// Blend a #rrggbb colour toward another. Anything else passes through.
export const blend = (a: string, b: string, t: number) => {
  if (!/^#[0-9a-fA-F]{6}$/.test(a) || !/^#[0-9a-fA-F]{6}$/.test(b)) return a;
  const x = hex(a);
  const y = hex(b);
  return '#' + x.map((v, i) => Math.round(v + (y[i] - v) * t).toString(16).padStart(2, '0')).join('');
};

// How a prop's fill should look in the current style.
export const propFill = (fill: string) => {
  if (fill === 'none') return 'none';
  if (LOOK.lineOnly) return LOOK.lineFill;
  if (LOOK.tint) return blend(fill, LOOK.tint[0], LOOK.tint[1]);
  return fill;
};

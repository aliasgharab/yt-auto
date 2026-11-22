// Small math helpers shared by every film.
export type Pt = [number, number];

// Smooth pseudo-noise: continuous in t, so wobble moves on every frame.
export const wob = (t: number, seed: number, amp = 1.6) =>
  Math.sin(t * 0.13 + seed * 12.9898) * amp * 0.6 +
  Math.sin(t * 0.071 + seed * 78.233) * amp * 0.4;

// Polygon/polyline with hand-drawn wobble. Edges are subdivided so they bend.
export const wobblyPath = (
  pts: Pt[],
  t: number,
  seed = 0,
  amp = 1.6,
  closed = true,
  step = 26,
) => {
  const out: Pt[] = [];
  const n = pts.length;
  const segs = closed ? n : n - 1;
  let k = 0;
  for (let i = 0; i < segs; i++) {
    const [x1, y1] = pts[i];
    const [x2, y2] = pts[(i + 1) % n];
    const m = Math.max(1, Math.round(Math.hypot(x2 - x1, y2 - y1) / step));
    for (let j = 0; j < m; j++) {
      const u = j / m;
      out.push([
        x1 + (x2 - x1) * u + wob(t, seed + k * 0.37, amp),
        y1 + (y2 - y1) * u + wob(t + 50, seed + k * 0.53, amp),
      ]);
      k++;
    }
  }
  if (!closed) {
    const [x, y] = pts[n - 1];
    out.push([x + wob(t, seed + k * 0.37, amp), y + wob(t + 50, seed + k * 0.53, amp)]);
  }
  return 'M' + out.map((p) => p[0].toFixed(1) + ',' + p[1].toFixed(1)).join(' L') + (closed ? ' Z' : '');
};

export const circlePts = (cx: number, cy: number, r: number, n = 0): Pt[] => {
  const count = n || Math.max(10, Math.round((2 * Math.PI * r) / 22));
  return Array.from({length: count}, (_, i) => {
    const a = (i / count) * Math.PI * 2;
    return [cx + Math.cos(a) * r, cy + Math.sin(a) * r] as Pt;
  });
};

export const rectPts = (x: number, y: number, w: number, h: number): Pt[] => [
  [x, y],
  [x + w, y],
  [x + w, y + h],
  [x, y + h],
];

// Fade in over `fin` frames, out over `fout` frames, between a and b.
export const fadeInOut = (f: number, a: number, b: number, fin = 12, fout = 12) => {
  if (f < a || f > b) return 0;
  return Math.min(1, (f - a) / fin, (b - f) / fout);
};

export const clamp01 = (v: number) => Math.max(0, Math.min(1, v));

// Damped overshoot pop: 0 -> 1 with a bounce. Good for squash/stretch.
export const pop = (f: number, dur = 14) => {
  if (f <= 0) return 0;
  const u = f / dur;
  return 1 - Math.exp(-5 * u) * Math.cos(u * 9);
};

# ENIGMA — director's review (v1)

Reviewed from frames every 2 s plus close-ups of every red element.

## Red elements that are misplaced
| Time | Problem | Fix |
|---|---|---|
| 0:12–0:15 | Marker circles the lit M, then stays after the lamp goes dark (circles nothing). | Fade the marker out with the lamp. |
| 0:26 | The strike line starts off the paper (top-left corner) and runs over the heading. | Keep strikes inside the paper, with 20px padding. |
| 0:36–0:48 | U-boats are tiny red dashes; nothing says what they are. The sinking-ship ✕ marker is about 12px and sits on the convoy line. | Make U-boats bigger, with a "U-BOAT" label once. Make sinkings big: a red flash and a ring. |
| 0:44 | "SHIPS SUNK" floats in empty sea, top right, attached to nothing. | Put the counter in a fixed HUD slot (bottom-left), or next to the convoy. |
| 0:58 | Ellipse spills off the paper's left edge, and its closing tail draws as a separate stroke above the heading. | Fit markers to the target's bbox +12px, clamp them to the parent, and keep the overshoot tail under 15° of arc. |
| 1:14 | Marker circles the end of the chain, not the mug, though the joke is the mug. | Circle the mug *and* chain, or the padlock. |
| 1:18 | The Shadow stands among the colleagues at human scale; it reads as a red person in the room. | When the Shadow appears, it is behind and larger than Hero, never in a lineup. |
| 1:32 | "NO MATCH" floats top-right, far from the Bombe/paper. | Stamp it on the paper or the Bombe. |
| 1:36 | The Shadow's head is cut off by the top bar (breaks the rule). | Cap the Shadow's scale so its head stays ≥ 40px below the bar. |
| 1:40 | The lampboard ellipse slices through the Q and O lamps at its ends, and the tail stroke floats above the row. | Same bbox fit. Circle one lamp, not the whole board. |
| 1:42 | A stray red dot floats above the second "A" before the ✕ draws (the ✕ stroke's start cap). | Don't render a stroke until progress > 0.02. |
| 2:08 | The flash whites out the frame for too long, with speed lines over the whole room. It's the loudest moment in a calm film. | 3 frames max, and no speed lines in the documentary look. |

## Wider problems
1. **Characters are too small.** In most room shots Hero is about 15% of the frame height, with large empty walls. Frame closer: Hero should be ⅓ to ½ of the frame height in emotional shots.
2. **The same desk shot is used six times** (operator and Turing, identical framing). Vary it with a close-up of hands and papers, a high angle, or an over-the-shoulder shot.
3. **Too many text-on-black cards** (ENIGMA, the number twice, A→A, E→E, 3,000, −2 YEARS) take about 25% of the runtime. Each one works, but together they feel like slides. Put text *into* the scene (on the paper, the chalkboard, the map) when possible.
4. **Turing and the German operator are the same figure** apart from a cap. Give each side a clear visual code: the operator wears a cap and a red armband stripe and sits in a cold, flat light, while Turing wears a scarf and sits in a warm lamp glow.
5. **The DAY counter is tiny and gamey.** In a real-story film, use a date stamp ("AUTUMN 1940") in the narrator slot instead.
6. **The chalkboard is empty for 2 seconds**, and "BUILD A MACHINE" is dark grey on grey (barely visible at 1:24). Start drawing on the cut and write in white.
7. **The map is generic.** Britain and Europe are unrecognisable blobs. Use simplified *real* coastlines (public-domain Natural Earth data, drawn as SVG paths).
8. **Known poses still show:** sitting (legs hang off the front of the chair, 2:22), and slumped (reads as squatting, 1:36).
9. **The win is a flash, not a moment.** The emotional peak (KEY FOUND) needs a slow push-in on Turing's face, held silence, then the lamp.
10. **The Shadow in a documentary.** An inner-voice demon suits the motivational shorts (BOOT). In a real-history film it fights the tone. Use it only for one real doubt, or replace it with the doubters themselves ("THEY SAID: IT WILL NEVER WORK" stamped on a memo).

## What works
- Lamp-lit desk at night, the grain, the vignette: the mood is right.
- Cold open structure and voice pacing.
- The WETTERBERICHT sliding crib is the best shot: it *explains* something visually. Do more of that.
- The red clock hand at midnight is a good single-accent beat.

## v2 — fixes applied
- Every red item in the table above is fixed. Markers are refitted, papers use a box marker, and the stray dot and floating labels are gone. U-boats are bigger and labelled, sinkings are bigger, the sunk counter sits on the map, and NO MATCH is stamped on the paper.
- The Shadow appears only in the despair beat (plus a faint fade-out at the win). It was removed from the lineup and the Bombe scene, and its head is under the bar.
- Date stamps replace the DAY counter. Closer framing and pushes are on the emotional shots. A row of three identical operators shows "predictable". The officer close-up is new. The papers get a slow Ken Burns push.
- The A key is pressed repeatedly and the A lamp never lights (circled). The chalkboard draws on the cut with bright words. KEY FOUND is attached to the Bombe lamp, followed by a slow push-in. The flash is 3 frames with no speed lines.
- Hand-traced recognisable coastlines (not yet Natural Earth data). Sitting and slumped poses are reworked.
- Still open: typing pose, chapter cards and the "what happened next" beat (these need new narration), real map data.

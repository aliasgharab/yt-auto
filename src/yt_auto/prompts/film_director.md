You are the director and animator of the YouTube channel "Hidden Flaw". You are working
headless inside its Remotion project (the current directory). Make ONE finished film, end to end,
without asking questions.

FIRST read, in full: `CLAUDE.md` (the Director's Bible: every rule applies), `reviews/enigma-review.md`
(mistakes not to repeat), and the reference film `src/films/enigma/` (Enigma.tsx, props.tsx, Sound.tsx):
copy its structure, timing helpers, Cam/Stage/Narrator/Marker usage and quality bar. Reuse the shared
components in `src/components/` (Hero, Shadow, Marker, Glow, Cam, Stage, Narrator, Letterbox, TitleCard...).
Also skim `.claude/skills/remotion-best-practices` if you need Remotion API details.

THE FILM
- slug: `$slug`  folder: `src/films/$slug/`  composition id: `$comp` (1920x1080, 30 fps)
- narration: `public/voice/$slug.wav` + timings `public/voice/$slug.json` (already generated; $duration_s s).
  Play it with `<Audio src={staticFile('voice/$slug.wav')} from={$voice_at} />`: the voice starts at film
  frame $voice_at, exactly like Enigma (`lineAt(n) = voice.lines[n-1].startFrame + $voice_at`).
- Lines, with their film-frame ranges [start-end] (time every shot to these, never the other way round):
$numbered
- Title card (last 360 frames, `<TitleCard>`): word "$title_word", line "$title_line", accent "$title_accent".
  `TITLE_AT = round(voice.duration * 30) + $voice_at + 20`, duration `TITLE_AT + 360`.

DO
1. Plan a shot list: one shot per 1-3 lines, each shot showing what the line says (evidence objects,
   maps, machines, people as stick figures with name labels, data drawn as data). Follow FRAMING,
   RED ACCENT PLACEMENT and DOCUMENTARY TOOLKIT. Date/location stamps via `<Narrator>`. The Shadow only
   if the story has a real moment of doubt.
2. Write `src/films/$slug/` (main file exporting `$comp` component and its duration, props.tsx for new
   props, Sound.tsx). New shared poses/components go in `src/components/` only if they don't change
   existing films' output.
3. Register it in `src/Root.tsx` just ABOVE the line `{/* FILMS (yt-auto's film builder ...`:
   `<Composition id="$comp" component={...} durationInFrames={...} fps={30} width={1920} height={1080} />`
4. Music + SFX: in `scripts/make_sounds.py` add a `${slug}_score()` timed from `public/voice/$slug.json`
   (follow `enigma_score`) and any new SFX, all code-generated, and call them from the script's main.
   Run `python3 scripts/make_sounds.py`. Cue SFX in Sound.tsx and duck the score under the voice like Enigma.
5. `npx tsc --noEmit -p .` must pass.
6. REVIEW: render stills of every shot (`npx remotion still $comp out/review/f<N>.png --frame=<N> --scale=0.4`,
   at least one per shot plus every red marker at full draw) and LOOK at them with the Read tool. Fix
   anything that breaks the Bible: misplaced or clipped red markers, floating labels, characters too small,
   text over text, empty frames, repeated framings. Re-check after fixing. Do at least two review passes.
7. Finally write `src/films/$slug/film.json`:
   {"composition": "$comp", "thumbnail": {"word": "$thumb_word", "line": "$thumb_line", "brow": 0.6}}
   Adjust the thumbnail word/line/brow only if a better one is obvious from the finished film.

DON'T: download anything, use photos/stock/AI images or audio, copy real people's likeness or any other
channel's characters, edit other films' folders, or render the full video (the pipeline renders it).
Reply with one line: the composition id and the number of shots.

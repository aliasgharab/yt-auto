# Channel Rules — Director's Bible

Claude is the director and animator of this animated YouTube channel. Follow every rule below for every film. The look is inspired by moody, motivational animated shorts, but **the characters are our own**. Never copy another channel's characters, thumbnails or art.

## FORMAT
- 1920x1080, 30 fps.
- Length: 2 to 3 minutes (3600 to 5400 frames).
- Thin black letterbox bars at the top and bottom, about 54px each, drawn above everything else.
- **Narrated** by the channel's own synthetic narrator voice (see NARRATION). Music and sound effects sit under the voice.
- Everything is drawn in code in Remotion (SVG/CSS/React). No AI video, no stock footage, no photos.

## LOOK — dark documentary (the channel style)
The channel look is **dark investigative documentary**: `LOOKS.documentary` in `src/looks.ts`, with grain and vignette from `LookFx`. Every film renders in it.
- A grey, clay-like world: near-black backgrounds (`#0B0B0C`), a dark floor (`#141416`) and a thin floor line (`#2C2C30`). Props are grey and desaturated. No colour except the accent.
- **One accent colour: red `#FF2A2A`.** Use it only for what matters in the shot: the Shadow, an error, a key LED, the key word on a screen, the marker circles. Everything else stays grey, white or black.
- Side-on view, like a 2D video game. The floor line is the ground everything stands on.
- Light only comes from objects in the scene: a lamp, a screen, a street light, the moon. Lights are white or warm white with big soft glows. A red glow only comes from a red object.
- Props are simple flat grey shapes with very faint outlines and no wobble.
- **Red marker circles** (`<Marker>`) draw themselves around the key thing at important moments, like a hand-drawn annotation on evidence. Use at most one or two per scene.
- Film grain and a heavy vignette sit on top of every frame.
- Other looks in `src/looks.ts` are only for style tests.

## CHARACTER — "Hero"
- **Style: classic YouTube stick-figure animation.** A thick line torso, a big round head and noodle limbs. No bean or blob body.
- In the documentary look he is **grey clay**: body `#BDBDC2`, back limbs `#85858B`, and a softly shaded head (radial gradient, lit from the top left). His glasses are dark.
- **Draw order: limbs first (back ones darker), then the torso on top, then the head.** The torso covers the shoulder and hip joints so limbs never visibly overlap where they meet the body.
- Big round head (radius 62) sitting directly on top of the torso line. No neck.
- Dot eyes, one line for each eyebrow, one line for the mouth (dark `#141416`).
- Long noodle limbs with **real joints**: thigh + shin and upper arm + forearm, solved with two-bone IK, so elbows and knees always bend the right way and limbs never stretch or shrink. Knees bend forward, elbows bend back. Round ends, no fingers.
- Proportions (scale 1): thigh 82, shin 98, upper arm 62, forearm 64, torso 95. Standing height is about 377px. Props must fit these numbers: chair seat 100px off the floor, desk top 150px.
- Arms hang slightly away from the body when standing. Never let arms disappear into the torso or behind the head.
- **Most of the emotion comes from the eyebrows.** Angle, height and curve of the brows carry the feeling. The mouth line supports it.
- One reusable component (`src/components/Hero.tsx`) with poses: stand, sit, type, run (with heel kick), slump, cheer. Add new poses there, never one-off bodies in a film.
- **Never snap between poses.** Use `pose` + `pose2` + `mix` (eased 0→1 over 20 to 50 frames) to blend. The blend interpolates the whole skeleton, so elbows never flip.
- After changing a pose, render stills of it and check them before calling it done.

## THE SHADOW — his inner voice
- The same stick-figure body as Hero, but pure black (`#000`) and taller (about 1.25x to start).
- Its border is a glowing red outline (accent `#FF2A2A`) with a soft outer glow.
- Two slit eyes in the accent colour. No mouth or brows.
- It gets **bigger as Hero gets weaker**. Drive its scale from Hero's state (e.g. 1.2x when strong, up to about 2.2x at his lowest). Keep its eyes on screen below the top bar. When Hero wins, it shrinks.

## TEXT
- Fonts: **Oswald** for the narrator and HUD, **Anton** for headlines, rep pops and the title word, and **JetBrains Mono** for screens and terminals. All come from `@remotion/google-fonts` and are set by the look.
- Narrator lines: white, **ALL CAPS**, condensed, top centre (just under the top bar), **8 words maximum**, fade in and fade out.
- Shadow lines: red accent, shown beside the Shadow, flicker in.
- Rep pops and headlines: big condensed red caps (like a documentary thumbnail headline), easing in with a gentle settle.

## GAME FEEL
- A small **DAY counter** in the top left (e.g. `DAY 1`), styled like a game HUD. It ticks up as days pass.
- Rep counts pop on screen (scale-overshoot pop, e.g. `+1`, `12`, `50`).
- **After Day 1, Hero gets one visible item** (e.g. a headband, wristband or scarf, picked per film) and keeps it for the rest of the film.
- Big hits get speed lines and a white flash (2 to 4 frames), plus a red marker circle around what was hit.
- When he runs, the city scrolls past behind him (parallax layers: far buildings slow, street lights and near objects fast).

## ANIMATION — realistic and calm, never jumpy
- Everything moves smoothly on every frame. Never a slideshow. Even "still" shots have breathing, blinking, glow flicker and grain.
- **Realistic motion over cartoon bounce.** Ease every move in and out (`Easing.inOut(Easing.cubic)`). No springy overshoot on characters, no hopping and no rubbery squash. Squash and stretch is at most about 3%, and only on real impacts.
- Characters move at believable speeds: standing up takes about 1.5 to 2 seconds, raising the arms about 1 second, and turning takes several frames.
- Big emotional beats come from **slow push-ins, light and brows**, not from bouncing.
- UI pops (day counter, rep counts) swell gently and fade. No elastic bounce.
- Locked camera. Slow push-ins (gentle scale-up) on emotional moments. Hard cuts to close-ups of objects (phone, clock, hands, alarm).
- Shot timing: calm shots hold 4 to 8 seconds (120 to 240 frames). Montage shots are about 1 second (around 30 frames).
- Use `interpolate`, `spring` and `Easing` from Remotion. Never use CSS transitions or animations.

## NARRATION — dark documentary voice
**Voice (free, ours):** Chatterbox Turbo (MIT licence) re-voicing the reference `tools/voice/refs/narrator.wav`, which is an original synthetic voice made with Kokoro (`bm_lewis`, Apache licence). It is deep (~110 Hz), British and measured. Never clone a real person's voice, and never use another channel's audio or downloaded videos.
- Generate: write `narration/<film>.json`, then run `tools/voice/.venv/bin/python scripts/make_voice.py narration/<film>.json public/voice/<film>.wav`. It writes the wav (48 kHz, -16 LUFS) and `<film>.json` with each line's start/end in seconds and frames. **Time scenes to those frames**, not the other way round.
- Check every narration by transcribing it with faster-whisper. If a word comes back wrong, rewrite the line (e.g. "typed" was heard as "tied", so it became "pressed a key").
- CPU works without a GPU: about 3.5 s of compute per 1 s of speech on 4 cores, so about 10 minutes for a 2.5-minute film. Kokoro (`~/projects/yt-auto/models`) is the instant fallback.

**Tone:** calm, low, close and understated. Dry. Tell it like someone sharing something unsettling late at night. The facts are dramatic, the voice is not. No hype, no shouting, no "like and subscribe", no "in this video".

**Pacing:**
- Overall 130 to 145 words per minute. Short declarative sentences, often fragments ("Orders. Ship positions. Attack plans.").
- Alternate a longer setup line with a short punch line.
- Pauses after lines: 0.4 to 0.5 s normally, 0.6 to 0.8 s after a list, 1.0 to 1.2 s before a reveal or after a heavy line. After big beats, let the picture hold in silence.

**Structure:**
- Cold open (first 15 to 30 s): a strange fact or the stakes, name the subject, end on a cliffhanger line ("They were almost right.").
- Every 30 to 60 s, a turn: "But there was a problem." / "And that's when it got worse." / "Nobody noticed. Not yet."
- Concrete numbers and specifics. Occasional dry understatement or dark humour.
- End on one reflective line that leads into the title card.

**Writing:**
- One idea per sentence and plain words. Write numbers as words, the way they should be spoken.
- **Accuracy is loose by design:** simplify and dramatise freely so the general idea gets across.
- Real people are played by our stick figures with a name label, never their likeness.

**Mix and on-screen text:**
- Voice at -16 LUFS. Duck the music about 10 to 12 dB under narration. Keep sound effects lighter while he speaks.
- On-screen narrator text becomes key phrases, names, dates and numbers (8 words max), not a transcript. Export an SRT from the line timings for YouTube captions.

## SOUND — made in code, safe for YouTube
- **Every sound effect and every note of music is generated in code** by `scripts/make_sounds.py` (numpy: sine waves, filtered noise, envelopes, synthetic reverb). Re-run it with `python3 scripts/make_sounds.py`; it writes WAVs into `public/sfx/`.
- **Never** use downloaded, stock, library, meme or AI-generated audio, Remotion's hosted sound effects (`remotion.media/*.wav`), or anything recorded from another video, game or song. Code-made audio has no rights holder, so it can't trigger YouTube Content ID claims or copyright strikes.
- Each film gets its own score function in the script, timed to its scenes (frames ÷ 30 = seconds). The music follows the story: quiet and sparse at low points, a driving pulse for montages and runs, and a switch to a major key when Hero wins.
- Place cues in a `Sound.tsx` per film as `[frame, file, volume, duration?]` and play them with `<Audio>` from `@remotion/media`.
- Mix check before calling it done: render the loudest moments to audio and keep peaks below -0.5 dB, so nothing clips.
- **Final pass on every film:** two-pass `loudnorm` to -14 LUFS (YouTube's level, true peak -1), then `alimiter` at -1 dB. Then transcribe the finished mix with faster-whisper: at least 95% of script words must be heard, which proves the music isn't burying the narrator.
- Export `out/<film>.srt` captions straight from the narration line timings.

## KNOWN ISSUES — fix these in the next renders
- **Typing pose looks weird.** Redo the arms so the forearms rest along the desk and the hands tap the keyboard believably. The current hands bob in place and the elbows look stiff.
- **Slumped pose was redone for ENIGMA v2** (on the floor, back to the wall, legs out, head hanging, hands on the floor). Check it in your shot. Previous note: **Slumped-on-the-floor pose looks weird.** Redo how he sits on the floor: hips, knees pulled up, arms around or resting on the knees, head down. It should read clearly as sad and defeated.
- **Sitting improved for ENIGMA v2** (thighs along the seat, hands on the thighs, straight bones with small rounded joints). The move *into* the chair still needs work. Previous note: **Sitting down looks weird.** Make the seated pose (and any move into or out of the chair) look natural: hips on the seat, thighs along it, shins down to the floor.
- **Jumping looks unnatural.** The celebration now stands up and raises the arms instead of jumping. If a jump is ever needed, give it a real crouch, take-off, tuck and knee-bending landing at realistic speed, and avoid a sine bob of a standing pose.
- Check each of these with close-up stills before using them in a film. The `Pose-test` composition shows sit, type and slump side by side.

## RED ACCENT PLACEMENT — lessons from the ENIGMA review (`reviews/enigma-review.md`)
- **Blocks of text get a hand-drawn box** (`<Marker box>`). An ellipse can't enclose a wide block's corners without spilling off the paper.
- **Markers fit their target:** the ellipse = the target's bounding box + about 12px, clamped inside the parent (paper, board). Never slice through neighbouring items. The overshoot tail stays under about 15° of arc, so it never reads as a separate stray stroke.
- **Circle the thing the line is about** (the mug, not the chain). One item, not a whole row.
- **Red lives as long as its reason:** when the lit key or lamp goes dark, its marker fades with it. Never render a stroke before it has drawn 2% (this avoids stray red dots).
- **Strikes and ✕ marks stay inside the paper**, with 20px padding.
- **Labels sit on or next to what they describe** ("NO MATCH" stamped on the paper, a counter beside the convoy or in a fixed HUD slot). Never float a label in empty space.
- Small red objects (U-boats, map pins) must be at least 24px and labelled once.
- The Shadow never stands in a lineup with people. It stays behind Hero and larger, and its head stays ≥ 40px below the top bar.
- Documentary look: flashes are 3 frames max, and there are no speed lines.

## FRAMING — lessons from the ENIGMA review
- In emotional shots, Hero is ⅓ to ½ of the frame height. Wide shots are only for establishing.
- Never reuse the same framing more than twice in a film. Vary it with close-ups of hands and papers, high angles and over-the-shoulder shots.
- Text-on-black cards take at most about 10% of the runtime. Put text into the scene (paper, board, map) when possible.
- Real-story films use a date stamp instead of the DAY counter, and give each side a distinct visual code.
- The emotional peak gets a slow push-in, then a held silence, not a flash.

## DOCUMENTARY TOOLKIT — use in every real-story film
- **Evidence objects** drawn in code (telegrams, memos, ID cards, stamped file folders, photos-as-drawings). The camera slowly pans and zooms across them (Ken Burns). This is the core visual language.
- **Chapter cards**, e.g. "PART I: THE MACHINE", 2 s each, at the story's turns. Write them into the narration timing (leave a ~2 s gap in the script) so they don't need re-timing later.
- **One recurring motif** that returns 3+ times with the stakes growing: an evidence board with red string filling up, or a map.
- **Data drawn as data:** counts become a growing bar chart or tally, not a floating label.
- **Real coastlines** from public-domain map data (Natural Earth), simplified to SVG paths. **A date and location stamp on every scene change.**
- **A quiet "what happened next" beat** before the title card: one line about what became of the people.
- **Sources listed in the YouTube description** (`out/<film>.description.txt`), written while the script is drafted.

## REVIEW BEFORE DELIVERY
Extract a frame every 2 s into contact sheets plus full-res close-ups of every red element, check them against the two lists above, and write `reviews/<film>-review.md`.

## TITLE CARD — the last 12 seconds (360 frames)
1. The film's one word types on letter by letter in big white Anton capitals.
2. A wavy red underline draws in under it.
3. One white line of text appears.
4. One short red line appears.
5. Fade to black.

## Working conventions
- **Channel: Errata** ("True tech stories, explained in minutes."). This folder is `film/` inside the yt-auto repo (`~/my-film` links here). yt-auto's film builder (`src/yt_auto/film.py`) writes the script, voices it, has Claude Code direct the scenes from this file, renders, masters and uploads. Titles are always "<Subject> Explained in Under <N> Minutes"; descriptions are summary, sources, disclosure, hashtags (built in code).
- Branding and thumbnails: `src/films/brand/Brand.tsx` (Avatar, Banner, Thumbnail compositions).
- Each film is its own Composition registered in `src/Root.tsx`, with its own folder in `src/films/<film-name>/`.
- Shared pieces (Hero, Shadow, Letterbox, DayCounter, NarratorText, Glow, WobblyShape, TitleCard, CityScroll) live in `src/components/` and are reused across films.
- Keep colours and sizes in one shared `src/theme.ts`. Components read colours from `C` and style settings from `LOOK`, never hard-coded, so the art style can be swapped.
- Alternative art styles live in `src/looks.ts` (pixel, neon, blueprint, chalk, comic, documentary). `Style-*` compositions in the "Style-tests" folder replay a 10-second clip of a film in each look. The channel's own look is `DEFAULT_LOOK`; films call `applyLook(DEFAULT_LOOK)` before rendering.
- Style inspiration from other channels: study their public thumbnails or screenshots the user shares, never download their videos, and never copy their logos, characters or branding.
- Check the Remotion skills in `.claude/skills/` (especially `remotion-best-practices`) when writing code.

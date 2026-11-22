# yt-auto Architecture (format-agnostic)

Saved 2026-11-22. This is the pipeline behind the **Errata** channel (formerly Kernel Kids Shorts; handle @ErrataStories)
(`~/projects/yt-auto`, github.com/aliasgharab/yt-auto). Use this doc to
restart it with a different video style (this Remotion film style, long-form, or a new Shorts style).

**Main point:** only the *build* step (script → finished `video.mp4`) depends on the video style.
Ideas, the Notion board, QA, YouTube upload, scheduling, analytics, self-healing and notifications
all work for any format. To change style, write a new **format builder** and register it. The rest stays the same.

---

## 1. Current state (running as Errata since 2026-11-22)

| Item | State |
|---|---|
| GitHub workflows `yt-auto`, `heartbeat`, `doctor` | Disabled 2026-11-22 for the rebuild, **re-enabled 2026-11-22** with `default_format: film` (1 film a night) |
| `pages-build-deployment` (privacy/terms site) | Still on. Keep it: the OAuth consent screen needs it |
| Notion "Content Pipeline" | Nothing pending. The 4 private Needs Approval videos were deleted from YouTube on 2026-11-22 and their rows set to Rejected |
| Secrets / tokens | `YOUTUBE_TOKEN` renewed 2026-11-22 with `youtube.force-ssl` (caption upload); rest unchanged |

**Restart:**
```bash
R=aliasgharab/yt-auto
gh workflow enable yt-auto.yml -R $R
gh workflow enable doctor.yml  -R $R
gh workflow enable heartbeat.yml -R $R && gh workflow run heartbeat.yml -R $R   # cron is unreliable; heartbeat drives it
```
If more than about 7 days have passed, check the YouTube token first: `uv run yt-auto preflight`.

---

## 2. The big picture

```
            ┌──────────── scheduler (GitHub Actions; heartbeat.yml dispatches on time) ────────────┐
            │ preflight 07:15Z │ nightly 07:30Z │ publish every 30 min │ weekly Sun 15:00Z         │
            └────────┬──────────────────┬──────────────────┬───────────────────┬──────────────────┘
                     │                  │                  │                   │
              logins check       IDEA → BUILD → QA     schedule/flip      research + stats + analyze
                                        │                  │                   │
                                        ▼                  ▼                   ▼
   ┌──────────────────────── Notion "Content Pipeline" DB = the ONLY state ─────────────────────────┐
   │ Idea → Scripted → Rendered → Needs Approval → Scheduled → Live    (Rejected / Failed)          │
   │ + "What Works" page (analyst guidance fed back into the script writer)                         │
   └────────────────────────────────────────────────────────────────────────────────────────────────┘
                                        │
                     YouTube Data API: private upload → publishAt at next free slot → public
                     ntfy.sh: phone push for "done", "failed", alerts
```

The runners are ephemeral, so all state lives in Notion rows. Video files live only in the job dir
until they are uploaded to YouTube as **private**. Approving a row then just sets `publishAt`. Nothing is re-uploaded.

---

## 3. Layers

### 3.1 Control and state: `notion.py`, `pipeline.py`
- `notion.py` is a stdlib-only REST client. A row is a plain dict keyed by Notion property names.
- Columns: Title, Topic, Idea Notes, Status, **Format** (`short` / `long` / add more), Source
  (`auto` / `researcher` / `follow-up` / manual), Job, Hook, Script, QA, QA Notes, Approve, Reject,
  Feedback, Video ID, YouTube URL, Publish slot, Duration, Views 1h…7d, Checkpoints JSON,
  Verdict, Ratio 72h, Series, Alerts (dedupe tags).
- `pipeline.py` commands: `nightly`, `publish`, `stats`, `research`, `analyze`, `requeue`, `ntfy-topic`.
  A file lock stops two runs from overlapping.

### 3.2 Ideas: `agents.py` (researcher), analytics follow-ups
- The researcher pulls HN, Reddit and YouTube search signals. A helper LLM turns them into new **Idea** rows, deduplicated by title.
- Winners (72 h views ≥ 1.5× the median) create up to 3 follow-up Idea rows per series.
- If there are no Idea rows, the nightly creates `Source=auto` rows and the script writer picks the topic.

### 3.3 BUILD: the format-specific part
`produce()` in `pipeline.py` calls `build(cfg, topic, job, guidance=, feedback=, on_script=, past=, recent=)`
and expects a **job dir** back (contract in §4). Today's builders:

| Builder | Style | Steps |
|---|---|---|
| `build_short` → `duo.py` | Hiro asks / Baymax explains over Minecraft parkour, ≤ 29 s, 9:16 | Claude writes dialogue JSON (`prompts/duo_writer.md`), helper LLM edits it (`duo_editor.md`), similarity guard. Voices are Chatterbox zero-shot clones (RVC/Kokoro behind a flag), tempo, max-seconds cap. `cards.py` makes animated emoji pop-up cards. `captions.py` aligns words with faster-whisper. ffmpeg composites over a random gameplay segment |
| `build(cfg, "long")` | Old slide explainer, 16:9, 6–9 min | `script.py` makes scenes, `render.py` (Pillow, Ayu dark) makes keyframes, `tts.py` (Kokoro) narrates, then captions, then `assemble.py` (ffmpeg xfade), plus `thumbnail.py` |
| `tools/story_test.py` | Single-narrator story / "what if" world, 60–150 s | Test only. Not wired into the nightly |

### 3.4 QA: `agents.qa` → `qa.json`
- Python checks first (ffprobe: duration, resolution, audio present, loudness, word count).
- Then Claude vision looks at sampled frames (`prompts/qa_vision.md`).
- Verdict is `pass`, `warn` or `fail`. Only `fail` blocks. With `auto_approve: true`, pass/warn rows are approved automatically.

### 3.5 Publish: `youtube.py`, `pipeline.publish`
- After QA the video is uploaded right away as PRIVATE with title, description, tags, SRT captions and an optional thumbnail.
- `publish` gives approved rows the next free slot (`publish.slots`, Toronto time, `min_lead_hours`)
  with `videos.update publishAt`. Rejected rows stay private. Scheduled rows go to Live once their time has passed.
- Quota is 10k units/day, about 1,650 per video (upload plus schedule), so the hard max is about 5 videos/day.

### 3.6 Feedback loop: `analytics.py`, `agents.analyze`
- `stats --due` runs on the 30-min tick and records checkpoints at 1h, 6h, 24h, 72h and 7d.
  From day 4 to day 28 it adds deeper Analytics API metrics (retention, engaged views).
- At 72 h each video gets a verdict (winner / average / loser) against the rolling median of the last 20 **of the same Format**.
  A hook check runs on day 4. Alerts: view-drop streak, policy issues. Cadence rule (currently off).
- Weekly, the analyst rewrites the **What Works** page. `_guidance()` feeds that page, plus recent
  Reject feedback, into the next script prompt. That is the learning loop.

### 3.7 Self-healing: `heal.py`, `doctor.yml`
- Transient errors (network, 429/5xx, HF download, Claude overload) are retried with backoff.
  If they keep failing the row goes back to **Idea** (`requeue:N`, max 3 nights).
- A bug-type failure marks the row **Failed** and makes the nightly exit 1. `doctor.yml` then runs Claude Code
  on the failed log, which opens a fix PR plus a regression test and sends an ntfy. Merging the PR re-queues that run's rows.
- `preflight` checks all logins before the nightly runs.

### 3.8 LLM policy: `helper.py`
- Only the Claude subscription costs money. There is no API key: everything runs headless `claude -p`.
- A free helper model (opencode `deepseek-v4.1-flash-free`) runs first for editor, story_editor, research
  and analyze. Claude is the fallback. Script *writing* and vision QA always use Claude.

### 3.9 Infra
- GitHub Actions on a public repo (free runners). Big assets (gameplay, voices, models) are in a
  release on the private `yt-auto-assets` repo, fetched by `deploy/ci/fetch_assets.sh`. Heavy setup steps run only for the nightly.
- `heartbeat.yml` is a self-re-dispatching runner that triggers tasks on time, because native cron fires 8–9 h late.
  A `gate` job stops a second nightly on the same day.
- `deploy/systemd/*` has the same schedule as user timers (laptop alternative, not installed).
- Secrets: `CLAUDE_CODE_OAUTH_TOKEN`, `NOTION_JSON`, `YOUTUBE_CLIENT_SECRET`, `YOUTUBE_TOKEN`,
  `NTFY_TOPIC`, `ASSETS_TOKEN`.

---

## 4. The format contract (what a new style must provide)

A builder is a function:

```python
def build_<style>(cfg, topic: str | None, job: Path | None, *, guidance="", feedback=None,
                  on_script=None, past=None, recent=None) -> Path:
    ...
```

It must:
1. **Write a script** as JSON in `job/script.json`, with at least `title`, `description`, `tags`, plus whatever
   the style needs (lines / scenes / beats). Feed `guidance` (What Works) and `feedback` (reject notes)
   into the prompt. Use `past` / `recent` to avoid repeats (`write_unique_script` shows the pattern).
2. Call `on_script(script, job)` as soon as the script exists, so Notion shows *Scripted* with Hook and Script.
3. **Render** `job/video.mp4` to the YouTube upload spec (reuse `assemble.AUDIO_ARGS`, `COLOR_ARGS` and the encoder fallback).
4. Write `job/metadata.json`: `{title, description, tags, format, duration_s}`. Optional: `job/captions.srt`
   and `job/thumbnail.png` (uploaded for non-Shorts).
5. Write `job/job.json`: `{format, style, created}`. If `job` is passed and `script.json` already exists,
   re-render without rewriting the script (resume / `--from`).
6. Raise on failure. The `heal` layer decides between retry, requeue and Failed.

Everything after the job dir (QA, upload, schedule, analytics) needs nothing else.

---

## 5. Switching style: checklist

**Config (`config.yaml`)**
- `formats.<name>`: `size`, `target_words` / `scenes` / `max_seconds` for the new style.
- `channel.niche`, `voice_tone` if the topic changes. Character blocks (`duo.*`) only if the style uses them.
- `publish.slots` and `shorts_per_night`. Rename to `videos_per_night` and lower it for long-form
  (renders are slower, and fewer uploads a day suits long-form).

**Code: the spots where "short" is currently hardcoded (generalise these)**
- `pipeline.produce()`: default `build = build_short`, and `"Format": "short"` in `on_script`, `youtube_url(…, "short")`.
  → Choose the builder from the row's `Format` (or `cfg["default_format"]`) through a registry
  `BUILDERS = {"short": build_short, "long": build_long, "film": build_film}`.
- `pipeline.nightly()` and `research()`: new Idea rows get `"Format": "short"`. Use the configured default instead.
- `build_short` adds `#shorts` to the description. Only the Shorts builder should do that.
- `youtube.THUMBNAIL_FOR_SHORTS` / `format != "short"`. Already works for long-form (thumbnail uploads).
- `analytics`: the baseline already filters by Format. Rename user-facing "Shorts" text, and widen the
  hook-check thresholds for long-form (retention at 30 s, not % viewed).
- `agents.YT_QUERIES` and the research prompt: change the search terms for the new style and length.
- `prompts/`: add `<style>_writer.md` and `<style>_editor.md`. Update `qa_vision.md` for the new look.
- QA python checks: allowed duration range and aspect ratio per format.
- Notify text ("New Short done"): use the format name.

**CI**
- `yt-auto.yml` nightly setup installs Chatterbox, Applio, whisper and gameplay assets. Put each behind
  the formats in use. A Remotion builder needs `actions/setup-node`, `npm ci` and Chrome headless deps instead.
- Rendering time: GitHub runners have a 6 h job limit. A 3-min Remotion film at 1080p30 on 4 vCPU is
  fine, but measure before setting a count above 1.

---

## 6. The film format (built: `src/yt_auto/film.py`, project in `film/`)

The Remotion project lives in the repo at `film/` (`~/my-film` is a symlink to it). Rules: `film/CLAUDE.md`.
`default_format: film` in `config.yaml` makes nightly and research produce films; a Notion row's
`Format` column (`film` / `short`) overrides it per row. `yt-auto make --format film [--topic ...]` builds one locally,
`yt-auto make --from out/<job>` resumes one (every stage skips what already exists).

| Stage | What runs | Output |
|---|---|---|
| Script | `claude -p` + `prompts/film_writer.md` (narration rules pulled live from `film/CLAUDE.md`), similarity guard, **every source URL checked to load** | `job/script.json` |
| Voice | `film/scripts/make_voice.py` (Chatterbox Turbo + Whisper retry), python from `film.voice_python` or `tools/clone/.venv` | `film/public/voice/<slug>.{wav,json}` |
| Scenes | **Claude Code headless** (`prompts/film_director.md`, model `film.director_model`) writes `film/src/films/<slug>/`, registers the composition, adds the score/SFX, reviews its own stills | `film/src/films/<slug>/film.json` |
| Music | `film/scripts/make_sounds.py` | `film/public/sfx/*.wav` |
| Render | `npx remotion render Film<Slug>` | `job/raw.mp4` |
| Master | gain to -14.2 LUFS + limiter, then Whisper must hear ≥ 90% of the script | `job/video.mp4` |
| Extras | SRT from line timings (uploaded as captions), `Thumbnail` still → jpg, metadata | `captions.srt`, `thumbnail.jpg`, `metadata.json` |

**Title and description are built in code** (`make_title`, `make_description`), never free-written:
- Title: `<Subject> Explained in Under <N> Minutes`, N = the real running time rounded up (2:43 → 3).
- Description: 1–2 sentence summary, `Sources:` with each checked URL, a one-line disclosure (code-made
  animation/music, synthetic narration), then 3–5 hashtags.

**Schedule (no approval, `auto_approve: true`):** films on `publish.build_days` (Mon/Wed/Fri/Sun nights)
publish at 17:00; each film's vertical Short (`cuts.make_short`: cold open to the cliffhanger + "full story on
the channel", its own Notion row, Source `film-cut`, Series = film title) publishes the next day at 12:00 and
never before its film. The first build night of a month with 4 unused Live films adds an 8-10 min compilation
(`cuts.build_compilation`: voiced intro, chapter cards, films without title cards, chapters in the description).
On CI every film is persisted: its code is committed back and video/script/thumbnails go to release `film-<slug>`.

**QA gates (strict, since nothing waits for a human):** loudness -14±1 LUFS and peak ≤ -0.5 dB, Whisper ≥ 95%
(warn 90-95, fail below), no black gaps > 2 s, no colour but the red accent, letterbox bars, title pattern,
≥ 2 checked sources, hashtags; a 24-frame visual review against the red-placement/framing rules (a visual fail
goes back to the director once for a repair + re-render); a Claude script check for false or defamatory claims
and policy problems. Any fail = not published.

**Thumbnails:** 3 per film (circle / face / case-file stamp), tested hands-off by `thumbtest.py` (Studio's
Test & Compare has no API): from the publish day the thumbnail rotates A,B,C,A,B,C one Pacific day each
(thumbnails.set), and on day 9 each variant is scored by thumbnail CTR from the YouTube Reporting API reach
report (if that API is enabled for the Cloud project) or else by views/day; the winner (A unless another beats
it by > 5%) is set for good and a push reports the scores. State: Notion column "Thumb Test". Runs inside
every `stats` pass (the 30-min publish cron).

**Hands-off checklist (nothing needs the PC or a human):** GitHub Actions (public repo: free) runs everything,
driven by heartbeat.yml; auto_approve on; Notion is state; film code/renders persist to the repo/releases
(those commits also keep the repo "active", so GitHub never auto-disables the workflows); the OAuth app is
In production (refresh tokens don't expire weekly); CLAUDE_CODE_OAUTH_TOKEN lasts a year (`claude setup-token`);
Idea rows refill from weekly research and auto topics; transient failures requeue themselves; doctor.yml
diagnoses failed runs; ntfy pushes are informational only.

**Free helper model first** (`llm.helper.tasks`): research, analyze, editors, compilation plan (validated, else
Claude). Script, director, repair, visual QA and the script check stay on Claude.

QA (`agents.qa_review`) knows films: 1920×1080, 100–240 s, 16 frames checked against `prompts/qa_film_vision.md`.
Branding: `tools/branding.py` renders the avatar and banner from `film/src/films/brand/Brand.tsx`.

### 6.1 Running it with the PC off (free)

Everything above runs on **GitHub Actions** (the same `heartbeat.yml` → nightly setup yt-auto already uses).
Nothing needs a GPU.

| Need | Free option used |
|---|---|
| Compute | GitHub-hosted `ubuntu-latest` runners (4 vCPU, 16 GB). Unlimited minutes on a **public** repo; a private repo gets 2,000 min/month (about 40 films at ~45 min each) |
| Voice model | Chatterbox Turbo weights from Hugging Face, cached with `actions/cache` (`~/.cache/huggingface`), plus `narrator.wav` in the `yt-auto-assets` release |
| Rendering | Node 20 + `npm ci` in `film/`. Remotion downloads its own headless Chrome. Cache `~/.cache/remotion` and `node_modules` |
| Scripts | `claude -p` with `CLAUDE_CODE_OAUTH_TOKEN` (the Claude subscription, as today) |
| State and approval | Notion + YouTube private upload + ntfy, unchanged |

Estimated job time for one 2.5-minute film on a free runner: setup ~5 min, voice ~10 min, music ~1 min,
Remotion render ~15–30 min (measure the first run), encode and upload ~3 min. That's well under the 6 h limit, so 1 film per nightly is safe.

Backup option if Actions limits ever bite: an **Oracle Cloud Always Free** ARM VM (4 cores, 24 GB RAM, always on)
running the same pipeline with the `deploy/systemd/*` timers. Paid services such as Remotion Lambda or GPU clouds aren't needed.

## 7. File map (yt-auto)

```
src/yt_auto/
  __init__.py   CLI (make / qa / ideas / youtube-*), build() long, build_short(), write_unique_script()
  pipeline.py   nightly / publish / stats / research / analyze / requeue; produce(); slots
  duo.py        Shorts dialogue style: script schema, voices, composite
  cards.py      animated emoji pop-up cards        captions.py  whisper word timing -> ASS/SRT
  script.py     long-form scene script              render.py    Pillow keyframes (long)
  tts.py        Kokoro narration                    assemble.py  ffmpeg final encode (YouTube spec)
  thumbnail.py  1280x720 thumbnail                  youtube.py   upload / schedule / stats / analytics
  notion.py     Notion client                       analytics.py checkpoints, verdicts, alerts, guard
  agents.py     researcher, QA, analyst             helper.py    free LLM first, Claude fallback
  heal.py       retry / transient / preflight       notify.py    ntfy.sh
  prompts/      duo_writer, duo_editor, story_*, qa_vision, research, analyze
tools/          story_test.py, branding.py, make_ref.py, clean_voice.py, rvc/, clone/ (Chatterbox venv)
deploy/         ci/*.sh (assets, fonts, rvc), systemd/*.timer, install.sh
.github/workflows/  yt-auto.yml, heartbeat.yml, doctor.yml
docs/           ci-setup, youtube-setup, analytics, rvc-kaggle, privacy/terms (GitHub Pages)
```

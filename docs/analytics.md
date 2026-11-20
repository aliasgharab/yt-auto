# Live analytics, reaction and self-healing

## Analytics (src/yt_auto/analytics.py)

| When | What | Notion columns |
|---|---|---|
| every 30 min (publish cron, `stats --due`) | only if a checkpoint is due or the last sweep is ≥ 6 h old: `videos.list` (statistics, status, contentDetails), 50 ids / call = 1 quota unit | Views, Likes, Comments, Views 1h/6h/24h/72h/7d, Checkpoints (JSON with age + time of each capture), YT Status |
| day 4 – 28, ≤ once a day | YouTube Analytics v2: averageViewPercentage, averageViewDuration, engagedViews, shares, subscribersGained | Avg View %, Avg View (s), Engaged Views, Shares, Subs Gained, Hook Check |
| at the 72 h checkpoint (once) | ratio = 72 h views / median 72 h views of the previous 20 Shorts | Verdict (winner > 1.5x / loser < 0.3x / average / no baseline), Ratio 72h |
| winner | one follow-up Idea row (Source follow-up, same hook pattern, new subtopic), built first next night; max 3 per series | Series |
| day 4 | avg viewed < 60 % or engaged/views < 0.5 → "weak hook": change the hook, not the topic | Hook Check |
| nightly | 7-day median views < 100 in both of the last two weeks → 1 Short/night (+ ntfy) | Alerts (`cadence`) |

Missed checkpoints are not back-filled with later numbers; the capture age is stored in `Checkpoints`.

**Alerts (ntfy):** any policy/copyright/upload-rejection/region-block/age-restriction/missing-video
status (`policy:*` tag, once per issue); the last 3 classified Shorts all ≤ 0.3× the median (`drop3`).

**What Works page:** the analyst's prose (weekly `analyze`) plus a `## Scoreboard (auto-updated from YouTube
stats)` section rewritten by every full sweep: rolling median, hook-pattern table, winners, losers, hook
problems. The writer and editor read the whole page.

**Policy guard:** each new script is compared with the last 30 titles/scripts (word-level
SequenceMatcher, threshold 0.85); too similar → rewritten with that feedback, 3 strikes → build fails.

**Quota:** uploads ~1,600 units each (2/night = 3,200), sweeps ≤ ~50 units/day, scheduling ~2/video.
The Analytics API has its own quota. Plenty of headroom under 10,000/day.

## Self-healing (src/yt_auto/heal.py, .github/workflows/doctor.yml)

- **Retries:** Notion (5) and YouTube (10) calls already back off; each Short build gets
  `heal.build_tries` (2) attempts on transient errors (network, timeouts, 429/5xx, Hugging Face, Claude
  overload/usage limit), reusing the script once written. Still failing → row back to **Idea**
  (`requeue:N` tag), after 3 nights → Failed.
- **Preflight** 02:15 Toronto (`yt-auto preflight`): loads Chatterbox, checks Notion, YouTube
  (token refresh + channel + Analytics), Claude CLI; ntfy if anything is broken.
- **Exit code:** nightly exits 1 if any build hit a non-transient error, or if nothing got built.
- **Doctor:** a failed `nightly` step triggers `doctor.yml`. Claude Code (Sonnet) reads the failed log,
  writes a fix + regression test, and opens a PR labelled `doctor` (ntfy "fix ready"). No code fix →
  ntfy with the diagnosis. Merging the PR re-queues that run's Failed rows and starts a nightly for them.
  Requires: Settings → Actions → General → "Allow GitHub Actions to create and approve pull requests".

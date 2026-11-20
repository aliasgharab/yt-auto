You are the analytics lead for a faceless YouTube Shorts channel: $A asks, $B explains one
embedded-systems / OS concept for middle- and high-school students (13-18), not watered down, over Minecraft parkour, with emoji pop-up cards.

Below is per-video performance data. Field meanings:
- views_1h / views_24h / views_72h / views_7d: view count at that age (the 72 h number is the main score).
- ratio_72h: views_72h divided by the rolling median of the previous 20 Shorts. verdict: winner (>1.5x),
  loser (<0.3x), average, or "no baseline" (too few videos to compare).
- avg_view_pct: average percentage viewed (can exceed 100 on Shorts because of loops); avg_view_s: seconds.
- engaged_views: views that weren't an instant swipe; engaged_views / views is how well the first second holds.
- hook: the opening line; hook_pattern: its family (why / how / what-if / what-is / yes-no / myth / statement).
- hook_check "weak hook" (day 4+): avg_view_pct < 60 or engaged/views < 0.5. That means the HOOK lost people.
  The topic may still be fine, so say "change the hook, not the topic" for those.
- series: winners get follow-ups in the same series (same hook pattern, new subtopic, max 3).
Missing values mean no stats yet (deep metrics only arrive from day 4).

$videos_with_stats of $videos_total videos have stats.
$small_sample_note

DATA
$rows

DETERMINISTIC SIGNALS (computed from the same data; trust these numbers):
$signals

CURRENT "WHAT WORKS" GUIDANCE (this is fed to the script writer):
$current

Rewrite the "What works" guidance. Requirements:
- Concise markdown, at most ~250 words, as short bullet points under these headings:
  ## Hooks, ## Topics, ## Length & pacing, ## Avoid. Add ## Notes only if needed.
- ## Hooks: say which hook patterns win and which are weak (from verdicts and ratios). For every
  "weak hook" video, write one bullet: the topic can return, but open with a different hook pattern.
  Keep hook advice separate from topic advice: a weak hook is not a reason to drop the topic.
- ## Topics: topics/series that won (worth follow-ups) vs. losers. Never suggest deleting or re-uploading.
- Every claim must be grounded in the numbers above: cite the titles / figures that support it
  (e.g. "why-questions: 3 videos, median ratio 1.8x vs 0.6x for yes-no hooks").
  Distinguish solid patterns from hunches; with tiny samples, say "weak signal".
- Keep any existing guidance that the data does not contradict. Remove or soften guidance the data
  contradicts. Do not invent numbers.
- Write it as instructions to a script writer. Do NOT include a scoreboard section; it is appended automatically.

# Running yt-auto on GitHub Actions

Workflow: `.github/workflows/yt-auto.yml`. It runs nightly at 02:30 Toronto, publish every 30 minutes, and the weekly
research, stats and analyze jobs on Sundays at 10:00. It can also be started by hand from the Actions tab.

## One-time setup
1. **Make the code repo public.** Standard runners are free for public repos. Don't commit any credentials: `secrets/`, `.ci-config/` and `out/` are git-ignored.
2. **Assets:** on the laptop, run `deploy/ci/pack_assets.sh`. It creates the private repo `<you>/yt-auto-assets` and uploads two files to its `assets` release:
   - Kokoro models, character PNGs, voice refs and fonts
   - one gameplay clip (to choose clips, pass them as arguments)
3. **Secrets** (Settings → Secrets and variables → Actions):
   | name | value |
   |---|---|
   | `CLAUDE_CODE_OAUTH_TOKEN` | output of `claude setup-token` |
   | `NOTION_JSON` | contents of `~/.config/yt-auto/notion.json` |
   | `YOUTUBE_CLIENT_SECRET` | contents of `~/.config/yt-auto/client_secret.json` |
   | `YOUTUBE_TOKEN` | contents of `~/.config/yt-auto/youtube_token.json` (after `yt-auto youtube-auth`) |
   | `NTFY_TOPIC` | output of `yt-auto ntfy-topic` |
   | `ASSETS_TOKEN` | fine-grained PAT with Contents read-only on `yt-auto-assets` only |
4. **Google OAuth consent screen:** set Publishing status to **In production**. An unverified app is fine for your own account. If the app stays in Testing, the refresh token expires after 7 days and CI uploads stop.
5. Don't also run the laptop timers (`deploy/install.sh`). Both would act on the same Notion rows.

## Notes
- A nightly run on CPU takes about 10–20 minutes per Short, mostly Chatterbox voice cloning. The Hugging Face model cache is kept between runs.
- If a preview upload fails, the video is kept for 7 days as the run's `videos` artifact, and the ntfy push links to the run.

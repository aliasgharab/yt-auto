# YouTube upload setup (one-time, free)

Everything here is free: a Google Cloud project with the YouTube APIs costs nothing
and needs no billing account.

## 1. Create the Google Cloud project

1. Open <https://console.cloud.google.com/projectcreate>, sign in with the Google
   account that **owns the YouTube channel**.
2. Project name: `yt-auto` → **Create**. Make sure it is selected in the top bar.

## 2. Enable the two APIs

3. <https://console.cloud.google.com/apis/library/youtube.googleapis.com> → **Enable**
   (YouTube Data API v3).
4. <https://console.cloud.google.com/apis/library/youtubeanalytics.googleapis.com> → **Enable**
   (YouTube Analytics API).

## 3. OAuth consent screen

5. <https://console.cloud.google.com/auth/overview> → **Get started**.
   - App name `yt-auto`, user support email = your address → Next.
   - Audience: **External** → Next. Contact email → Next. Agree → **Create**.
6. **Audience** page → *Test users* → **Add users** → your own Google account → Save.
7. Still on **Audience**: click **Publish app** → Confirm (status becomes *In production*).
   Why: while the app is in *Testing*, Google issues refresh tokens that **expire after
   7 days** for these scopes, so you'd have to log in weekly
   ([source](https://developers.google.com/identity/protocols/oauth2#expiration)).
   An unverified production app is fine for personal use: you'll just click through an
   "unverified app" warning once (Advanced → *Go to yt-auto (unsafe)*). Don't submit
   it for Google verification — not needed for your own account.

## 4. OAuth client (Desktop app)

8. <https://console.cloud.google.com/auth/clients> → **Create client** →
   Application type **Desktop app**, name `yt-auto` → **Create**.
9. Click **Download JSON**, then:

   ```bash
   mkdir -p ~/.config/yt-auto
   mv ~/Downloads/client_secret_*.json ~/.config/yt-auto/client_secret.json
   chmod 600 ~/.config/yt-auto/client_secret.json
   ```

## 5. Log in once

10. ```bash
    cd ~/projects/yt-auto && uv run yt-auto youtube-auth
    ```
    A browser opens → pick the channel's account (and the channel/brand account if asked)
    → allow all three permissions (upload, view YouTube account, view Analytics).
    The token is saved to `~/.config/yt-auto/youtube_token.json` (chmod 600) and
    refreshes itself. It then prints your channel title.
11. Later, `uv run yt-auto youtube-check` prints the channel title to confirm it still works.
    If it ever says the token is invalid (e.g. you revoked access or changed your
    password), rerun step 10.

## 6. Channel extras (recommended)

12. Verify the channel by phone at <https://www.youtube.com/verify> — needed for custom
    thumbnails on long videos (without it the uploader just skips the thumbnail) and for
    videos longer than 15 min.

## 7. Private lock and the API audit (optional now)

From July 2020 until **November 2, 2026**, videos uploaded by API projects that hadn't
passed YouTube's compliance audit were locked to private. The
[Data API revision history (Nov 2, 2026)](https://developers.google.com/youtube/v3/revision_history)
reversed this: unverified projects' uploads are **no longer restricted to private**.
The uploader always uploads as `private` (with `publishAt` when scheduling, so YouTube
flips it public at that time). If a video ever does get locked private, nothing breaks —
open YouTube Studio and set it to Public by hand.

The audit is therefore only needed if you outgrow the default quota. Form:
**YouTube API Services – Audit and Quota Extension Form**,
<https://support.google.com/youtube/contact/yt_api_form>
(linked from <https://developers.google.com/youtube/v3/guides/quota_and_compliance_audits>).
Suggested answers:

- *Organization*: individual / personal project (student).
- *API client description*: "Single-user command-line tool that uploads videos I create
  to my own channel and reads view/like/retention stats for my own videos. No other
  users, no public-facing app, no data stored beyond video IDs and aggregate stats."
- *Which APIs*: YouTube Data API v3 (videos.insert, thumbnails.set, videos.list,
  channels.list), YouTube Analytics API (reports.query).
- *Users*: 1 (myself). *Channels*: 1 (my own).
- *Data storage*: video IDs, view/like counts and average view duration in local JSON;
  refreshed daily; deleted on revocation.
- *Screencast/screenshots*: a terminal recording of `yt-auto youtube-auth` and an upload.
- *Quota requested*: only as much as needed (e.g. a few uploads/day fits the default).

## Quota (verified 2026-11-19)

From <https://developers.google.com/youtube/v3/determine_quota_cost> and the
[videos.insert reference](https://developers.google.com/youtube/v3/docs/videos/insert):

| Bucket / method | Default | Cost per call |
|---|---|---|
| `videos.insert` (own "Video Uploads" bucket since June 2026) | 100 calls/day | 1 |
| `search.list` (own bucket) | 100 calls/day | 1 |
| everything else, shared | 10,000 units/day | `thumbnails.set` 50, `videos.list` 1, `channels.list` 1 |

Quotas reset at midnight Pacific Time. A typical day (1–3 uploads + thumbnails + a stats
check) uses ~3 upload calls and ~150 units — far under the limits. The YouTube Analytics API
is a separate API with its own quota (see its Quotas page in the Cloud console).

Note: the channel itself also has a YouTube-side daily upload limit (separate from API
quota) that new/unverified channels hit sooner; phone verification raises it.

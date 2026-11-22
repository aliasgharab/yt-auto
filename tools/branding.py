"""Hidden Flaw channel branding: avatar + banner images, channel description and keywords.

The images are drawn by the film project itself (film/src/films/brand/Brand.tsx: Avatar, Banner), so
they match the videos: near-black, grey clay figure, one red hand-drawn marker circle.

  .venv/bin/python tools/branding.py            # render assets/branding/{avatar,banner}.png
  .venv/bin/python tools/branding.py --apply    # ...and set banner + description + keywords on YouTube
                                                #   (~150 quota units). The profile picture and the channel
                                                #   NAME/handle have no API: change them in YouTube Studio ->
                                                #   Customization -> Branding / Basic info.
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets/branding"
FILM = ROOT / "film"

NAME = "Hidden Flaw"
DESCRIPTION = (
    "True tech stories, explained in minutes.\n\n"
    "Hidden Flaw tells the real stories behind famous machines, bugs, hacks and engineering disasters, "
    "and the one flaw that changed everything. How Enigma was broken. How a single worm took down the "
    "early internet. Why a machine built to heal ended up hurting people.\n\n"
    "Short animated documentaries, about 2 to 3 minutes each, with sources in every description.\n\n"
    "Every system has a flaw. Go looking for it."
)
KEYWORDS = ('"Hidden Flaw" "tech history" "tech documentary" "true tech stories" "computer history" '
            '"engineering disasters" cybersecurity hacking "famous bugs" cryptography "explained in minutes"')


def render():
    OUT.mkdir(parents=True, exist_ok=True)
    for comp, name in (("Avatar", "avatar.png"), ("Banner", "banner.png")):
        subprocess.run(["npx", "remotion", "still", comp, str(OUT / name), "--frame=30", "--log=error"],
                       cwd=FILM, check=True)
    print(f"wrote {OUT}/avatar.png, {OUT}/banner.png")


def apply():
    sys.path.insert(0, str(ROOT / "src"))
    from googleapiclient.http import MediaFileUpload
    from yt_auto.youtube import _youtube

    yt = _youtube(manage=True)
    banner_url = yt.channelBanners().insert(
        media_body=MediaFileUpload(str(OUT / "banner.png"), mimetype="image/png")).execute()["url"]
    ch = yt.channels().list(part="brandingSettings", mine=True).execute()["items"][0]
    bs = ch.get("brandingSettings", {})
    bs.setdefault("channel", {}).update({"description": DESCRIPTION, "keywords": KEYWORDS,
                                          "defaultLanguage": "en", "country": "CA"})
    bs.setdefault("image", {})["bannerExternalUrl"] = banner_url
    yt.channels().update(part="brandingSettings", body={"id": ch["id"], "brandingSettings": bs}).execute()
    print(f"channel {ch['id']}: banner, description and keywords set. Now in YouTube Studio: rename the "
          f"channel to {NAME!r}, pick a handle, and upload assets/branding/avatar.png as the picture.")


if __name__ == "__main__":
    render()
    if "--apply" in sys.argv:
        apply()

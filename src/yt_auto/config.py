import os
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]

# Where fonts may live: the user's font dir (CI installs here too, see deploy/ci/install_fonts.sh)
# and the system font tree.
FONT_SEARCH = [Path("~/.local/share/fonts").expanduser(), Path("/usr/local/share/fonts"), Path("/usr/share/fonts")]


def config_dir() -> Path:
    """Credentials dir (notion.json, ntfy.json, YouTube client/token). Override with YT_AUTO_CONFIG_DIR."""
    return Path(os.environ.get("YT_AUTO_CONFIG_DIR") or Path.home() / ".config" / "yt-auto").expanduser()


def expand(p) -> str:
    return os.path.expanduser(os.path.expandvars(str(p)))


def find_font(name: str, search=None) -> Path | None:
    """First file called `name` under the font search dirs (recursive)."""
    for d in search or FONT_SEARCH:
        if d.is_dir():
            hit = next(iter(sorted(d.rglob(name))), None)
            if hit:
                return hit
    return None


def resolve_fonts(render: dict, search=None) -> dict:
    """Expand ~/$VARS in font paths; when a configured path doesn't exist (e.g. on a CI runner),
    fall back to the same file name anywhere in the font search dirs. Env overrides:
    YT_AUTO_FONT_DIR (dir holding Inter-*.ttf), YT_AUTO_MONO_FONT (a monospace .otf/.ttf)."""
    r = dict(render)
    fd = Path(expand(os.environ.get("YT_AUTO_FONT_DIR") or r.get("font_dir") or "~/.local/share/fonts/Inter"))
    if not (fd / "Inter-Regular.ttf").is_file():
        hit = find_font("Inter-Regular.ttf", search)
        if hit:
            fd = hit.parent
    r["font_dir"] = str(fd)
    mono = Path(expand(os.environ.get("YT_AUTO_MONO_FONT") or r.get("mono_font") or "CascadiaMonoNF-Regular.otf"))
    if not mono.is_file():
        hit = find_font(mono.name, search)
        if hit:
            mono = hit
    r["mono_font"] = str(mono)
    return r


def load_config(path: Path | None = None) -> dict:
    path = path or ROOT / "config.yaml"
    with open(path) as f:
        cfg = yaml.safe_load(f)
    cfg["_root"] = ROOT
    if "render" in cfg:
        cfg["render"] = resolve_fonts(cfg["render"])
    return cfg

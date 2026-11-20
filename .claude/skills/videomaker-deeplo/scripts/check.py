"""Vérifie le socle de Deeplo Video Maker : outils, clés API, skills, banque de sons.

Usage : python .claude/skills/videomaker-deeplo/scripts/check.py [--offline]
--offline : ne teste pas les clés auprès de Fish Audio / Groq.
Code de sortie 0 si tout l'obligatoire est vert.
"""
import importlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SKILLS = Path.home() / ".claude" / "skills"
OFFLINE = "--offline" in sys.argv
AUDIO_EXT = {".mp3", ".wav", ".ogg", ".flac", ".m4a", ".aif", ".aiff"}

failed = 0


def line(ok, name, detail="", required=True):
    global failed
    mark = "ok  " if ok else ("FAIL" if required else "opt ")
    if not ok and required:
        failed += 1
    print(f"  {mark} {name:<22} {detail}")


def run(cmd):
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=120, shell=os.name == "nt")
        return (out.stdout or out.stderr).strip()
    except Exception as e:  # noqa: BLE001
        return f"ERR {e}"


def load_env():
    env = {}
    f = ROOT / ".env"
    if f.exists():
        for raw in f.read_text(encoding="utf-8").splitlines():
            if "=" in raw and not raw.lstrip().startswith("#"):
                k, v = raw.split("=", 1)
                env[k.strip()] = v.strip()
    for k in ("GEMINI_API_KEY", "FISH_API_KEY", "GROQ_API_KEY", "PIXABAY_API_KEY", "PEXELS_API_KEY"):
        env[k] = env.get(k) or os.environ.get(k, "")
    if not env["GROQ_API_KEY"]:
        g = Path.home() / ".config" / "groq" / "api_key"
        if g.exists():
            env["GROQ_API_KEY"] = g.read_text(encoding="utf-8").strip()
    return env


def http_ok(url, key):
    import requests

    try:
        r = requests.get(url, headers={"Authorization": f"Bearer {key}"}, timeout=15)
        return r.status_code == 200, f"HTTP {r.status_code}"
    except Exception as e:  # noqa: BLE001
        return False, str(e)[:60]


print("outils")
for tool in ("ffmpeg", "ffprobe"):
    path = shutil.which(tool)
    line(bool(path), tool, run([tool, "-version"]).splitlines()[0][:50] if path else "absent du PATH")
node = run(["node", "-v"])
m = re.match(r"v(\d+)", node)
line(bool(m) and int(m.group(1)) >= 22, "node >= 22", node)
line(sys.version_info >= (3, 9), "python >= 3.9", sys.version.split()[0])
hf = run(["npx", "--yes", "hyperframes@0.9.71", "--version"])
line(bool(re.search(r"\d+\.\d+\.\d+", hf)), "hyperframes CLI", hf.splitlines()[-1][:50] if hf else "")
line(bool(shutil.which("yt-dlp")), "yt-dlp", "", required=False)

print("python")
for mod in ("requests", "numpy", "scipy", "librosa", "matplotlib"):
    try:
        importlib.import_module(mod)
        line(True, mod)
    except ImportError:
        line(False, mod, f"python -m pip install --user {mod}")

print("skills (~/.claude/skills)")
for s, req in (("hyperframes", True), ("hyperframes-cli", True), ("hyperframes-registry", True),
               ("media-use", True), ("reverse-any-video", False), ("real-sfx", True),
               ("openverse-sfx", True), ("transcribe", False), ("gsap-core", False), ("remotion-to-hyperframes", False),
               ("motion-design", False)):
    line((SKILLS / s / "SKILL.md").exists(), s, required=req)

print("clés API")
env = load_env()
line(bool(env["GEMINI_API_KEY"] or env["FISH_API_KEY"]), "voix off (Gemini ou Fish)",
     "clé présente" if (env["GEMINI_API_KEY"] or env["FISH_API_KEY"]) else "aucune : voix locale de test seulement")
for k, url, req in (("GEMINI_API_KEY", None, False),
                    ("FISH_API_KEY", "https://api.fish.audio/model?page_size=1", False),
                    ("GROQ_API_KEY", "https://api.groq.com/openai/v1/models", False),
                    ("PIXABAY_API_KEY", None, False),
                    ("PEXELS_API_KEY", None, False)):
    if not env[k]:
        line(False, k, "vide (.env)", required=req)
    elif OFFLINE or not url:
        line(True, k, "présente (non testée)")
    else:
        ok, detail = http_ok(url, env[k])
        line(ok, k, detail, required=req)

print("projet")
line((ROOT / "studio" / "index.html").exists(), "studio/ HyperFrames")
for d in ("library", "brands", "jobs", "sounds"):
    line((ROOT / d).is_dir(), f"{d}/")
sounds = [p for p in (ROOT / "sounds").rglob("*") if p.suffix.lower() in AUDIO_EXT]
sfx = [p for p in sounds if "music" not in p.parts]
music = [p for p in sounds if "music" in p.parts]
line(len(sfx) >= 120, "banque de SFX", f"{len(sfx)} sons", required=False)
line(len(music) >= 16, "banque musique", f"{len(music)} pistes", required=False)
cfg = SKILLS / "real-sfx" / "config.json"
if cfg.exists():
    libs = json.loads(cfg.read_text(encoding="utf-8")).get("libraries", [])
    on_root = all(Path(lib["path"]).resolve().is_relative_to((ROOT / "sounds").resolve()) for lib in libs)
    line(on_root, "real-sfx -> sounds/", ", ".join(lib["path"] for lib in libs)[:60])

print()
print("SOCLE OK" if not failed else f"{failed} point(s) obligatoire(s) à corriger")
sys.exit(1 if failed else 0)

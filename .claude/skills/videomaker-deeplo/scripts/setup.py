"""INSTALLATION de Deeplo Video Maker sur une nouvelle machine (Windows, macOS, Linux).

  python setup.py plan        # dit ce qui manque, ne modifie rien (à lancer en premier)
  python setup.py install     # installe ce qui manque : paquets Python, skills HyperFrames, modèle Whisper, .env
  python setup.py test        # vrai test de bout en bout : voix locale -> sous-titres -> rendu de 4 s

L'agent montre `plan` à l'utilisateur et attend son « go » avant `install`. Les outils système (ffmpeg, Node 22+,
yt-dlp) ne sont pas installés d'office : `plan` donne la commande exacte pour la machine.
"""
import importlib.util
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
SKILLS = Path.home() / ".claude" / "skills"
HF = "hyperframes@0.9.71"
NPX = ["cmd", "/c", "npx"] if os.name == "nt" else ["npx"]
PIP = ["requests", "numpy", "scipy", "librosa", "matplotlib", "faster-whisper", "kokoro-onnx", "soundfile", "Pillow", "opencv-python-headless"]
MODULE = {"faster-whisper": "faster_whisper", "kokoro-onnx": "kokoro_onnx", "Pillow": "PIL", "opencv-python-headless": "cv2"}
OS = platform.system()

SYS_HINT = {
    "ffmpeg": {"Windows": "winget install Gyan.FFmpeg", "Darwin": "brew install ffmpeg", "Linux": "sudo apt install ffmpeg"},
    "node": {"Windows": "winget install OpenJS.NodeJS.LTS", "Darwin": "brew install node", "Linux": "nodesource ou apt (Node 22+)"},
    "yt-dlp": {"Windows": "winget install yt-dlp.yt-dlp", "Darwin": "brew install yt-dlp", "Linux": "pipx install yt-dlp"},
}


def run(cmd, **kw):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=kw.pop("timeout", 900), **kw)
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except Exception as e:  # noqa: BLE001
        return 1, str(e)


def state():
    s = {"os": f"{OS} {platform.machine()}", "cpu": os.cpu_count(), "system": {}, "python": {}, "skills": {}, "models": {}, "env": {}}
    for t in ("ffmpeg", "ffprobe", "yt-dlp"):
        s["system"][t] = bool(shutil.which(t))
    code, v = run(["node", "-v"])
    m = re.search(r"v(\d+)", v)
    s["system"]["node22"] = bool(m) and int(m.group(1)) >= 22
    for p in PIP:
        s["python"][p] = importlib.util.find_spec(MODULE.get(p, p)) is not None
    for k in ("hyperframes", "hyperframes-cli", "hyperframes-registry", "media-use", "openverse-sfx"):
        s["skills"][k] = (SKILLS / k / "SKILL.md").exists()
    hub = Path(os.environ.get("HF_HOME", Path.home() / ".cache" / "huggingface")) / "hub"
    s["models"]["whisper-large-v3-turbo"] = any(hub.glob("models--*faster-whisper-large-v3-turbo")) if hub.exists() else False
    env = ROOT / ".env"
    txt = env.read_text(encoding="utf-8") if env.exists() else ""
    s["env"]["fichier .env"] = env.exists()
    s["env"]["GEMINI_API_KEY (voix off)"] = bool(re.search(r"^GEMINI_API_KEY=\S+", txt, re.M))
    s["env"]["FISH_API_KEY (optionnelle)"] = bool(re.search(r"^FISH_API_KEY=\S+", txt, re.M))
    s["env"]["GROQ_API_KEY (optionnelle)"] = bool(re.search(r"^GROQ_API_KEY=\S+", txt, re.M)) or \
        (Path.home() / ".config" / "groq" / "api_key").exists()
    s["env"]["PIXABAY_API_KEY (optionnelle)"] = bool(re.search(r"^PIXABAY_API_KEY=\S+", txt, re.M))
    return s


def plan():
    s = state()
    todo, manual = [], []
    for t, ok in s["system"].items():
        if not ok:
            key = "node" if t == "node22" else ("ffmpeg" if t in ("ffmpeg", "ffprobe") else t)
            hint = SYS_HINT.get(key, {}).get(OS, "")
            if hint and hint not in manual:
                manual.append(hint)
    miss_py = [p for p, ok in s["python"].items() if not ok]
    if miss_py:
        todo.append(f"pip install --user {' '.join(miss_py)}")
    if not all(s["skills"].values()):
        todo.append("skills HyperFrames + openverse-sfx (~/.claude/skills)")
    if not s["models"]["whisper-large-v3-turbo"]:
        todo.append("modèle de transcription Whisper large-v3-turbo (~1,6 Go, une fois)")
    if not s["env"]["fichier .env"]:
        todo.append("fichier .env (clés vides à remplir)")
    print(json.dumps({"etat": s, "a_installer_par_l_agent": todo, "a_installer_par_l_utilisateur_ou_l_agent": manual,
                      "pret": not todo and not manual,
                      "duree_estimee_min": 3 + 8 * (not s["models"]["whisper-large-v3-turbo"]) + 2 * len(miss_py) // 3},
                     ensure_ascii=False, indent=1))


def install():
    s = state()
    steps = []
    miss_py = [p for p, ok in s["python"].items() if not ok]
    if miss_py:
        code, o = run([sys.executable, "-m", "pip", "install", "--user", "-q", *miss_py])
        steps.append({"pip": miss_py, "ok": code == 0, "log": o[-300:] if code else ""})
    if not all(s["skills"][k] for k in ("hyperframes", "hyperframes-cli", "hyperframes-registry", "media-use")):
        tmp = Path(tempfile.mkdtemp())
        code, o = run(NPX + ["--yes", HF, "init", "hf-skills", "--example", "blank", "--non-interactive"], cwd=tmp)
        shutil.rmtree(tmp, ignore_errors=True)
        steps.append({"skills hyperframes": "init (installe les skills)", "ok": code == 0, "log": o[-300:] if code else ""})
    if not s["skills"]["openverse-sfx"]:
        code, o = run(NPX + ["--yes", "@opendirectory.dev/skills", "install", "openverse-sfx", "--target", "claude"])
        steps.append({"openverse-sfx": "npx @opendirectory.dev/skills", "ok": code == 0, "log": o[-300:] if code else ""})
    if not s["models"]["whisper-large-v3-turbo"]:
        code, o = run([sys.executable, "-c", "from faster_whisper import WhisperModel; WhisperModel('large-v3-turbo', device='cpu', compute_type='int8')"],
                      env={**os.environ, "HF_HUB_DISABLE_SYMLINKS_WARNING": "1"}, timeout=3600)
        steps.append({"whisper large-v3-turbo": "téléchargé", "ok": code == 0, "log": o[-300:] if code else ""})
    if not (ROOT / ".env").exists():
        (ROOT / ".env").write_text("# Deeplo Video Maker : clés (ne jamais partager ce fichier)\n"
                                   "# Gemini TTS : voix off gratuite (aistudio.google.com/apikey)\nGEMINI_API_KEY=\n"
                                   "# Fish Audio : facultatif (clonage de voix, payant)\nFISH_API_KEY=\n"
                                   "# Groq : facultatif (transcription rapide en ligne)\nGROQ_API_KEY=\n"
                                   "# Pixabay : facultatif (plans de coupe photo / vidéo)\nPIXABAY_API_KEY=\n", encoding="utf-8")
        steps.append({".env": "créé", "ok": True})
    for d in ("jobs", "brands", "library", "sounds"):
        (ROOT / d).mkdir(exist_ok=True)
    print(json.dumps({"etapes": steps, "suite": "python setup.py test"}, ensure_ascii=False, indent=1))


def test():
    """Vrai test : un job jetable, voix locale de 2 phrases, sous-titres, composition, check et rendu de 4 s."""
    env = {**os.environ, "PYTHONUTF8": "1", "HF_HUB_DISABLE_SYMLINKS_WARNING": "1", "HYPERFRAMES_PYTHON": sys.executable}
    py = lambda *a: run([sys.executable, str(HERE / a[0]), *a[1:]], env=env)
    code, o = py("new_job.py", "Test", "installation")
    if code:
        return print(json.dumps({"ok": False, "etape": "new_job", "log": o[-500:]}, ensure_ascii=False))
    job = Path(json.loads(o.strip().splitlines()[-1])["job"])
    (job / "work" / "t_storyboard.json").write_text(json.dumps({"scenes": [
        {"kind": "hook", "kicker": "Test", "text": "Installation réussie", "voice": "Bonjour, l'installation fonctionne."},
        {"kind": "cta", "text": "Prêt à monter", "sub": "Deeplo Video Maker", "voice": "Tout est prêt."}]}, ensure_ascii=False),
        encoding="utf-8")
    report = {"job": str(job)}
    for step in (["voice.py", str(job), "t", "--engine", "local"], ["build_text.py", str(job), "t"],
                 ["build_scenes.py", str(job), "t", "--no-sfx"]):
        code, o = py(*step)
        report[step[0]] = "ok" if code == 0 else o[-400:]
        if code:
            return print(json.dumps({"ok": False, **report}, ensure_ascii=False, indent=1))
    code, o = run(NPX + ["--yes", HF, "check"], cwd=job)
    report["check"] = "ok" if "Check passed" in o else o[-400:]
    code, o = run(NPX + ["--yes", HF, "render", "-q", "draft", "-w", "4", "--end", "4", "-o", "renders/test.mp4"], cwd=job)
    out = job / "renders" / "test.mp4"
    report["rendu"] = f"ok ({out.stat().st_size // 1024} Ko)" if out.exists() else o[-400:]
    ok = all(v == "ok" or str(v).startswith("ok") for k, v in report.items() if k != "job")
    if ok:
        shutil.rmtree(job, ignore_errors=True)
    print(json.dumps({"ok": ok, **report, "note": "job de test supprimé" if ok else "job de test gardé pour diagnostic"},
                     ensure_ascii=False, indent=1))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "plan"
    {"plan": plan, "install": install, "test": test}.get(cmd, plan)()

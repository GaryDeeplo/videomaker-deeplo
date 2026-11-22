"""MISES À JOUR du skill depuis le dépôt public.

  python update.py check      # version locale vs version publiée (rapide, mémorisé 12 h) + nouveautés
  python update.py install    # installe la mise à jour sans toucher aux fichiers de l'utilisateur

Dossier cloné avec git : `git pull --ff-only`. Dossier téléchargé en ZIP : le ZIP du dépôt est récupéré et copié
par-dessus, SAUF ce qui appartient à l'utilisateur : .env, jobs/, chartes de brands/ (le modèle _exemple est mis à jour),
profil.json, dist/. Rien n'est supprimé (les motions ajoutées à library/ restent). Ensuite : check.py.
L'accueil du skill (onboard.py status) appelle `check` et propose la mise à jour quand il y en a une.
"""
import io
import json
import shutil
import subprocess
import sys
import time
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
REPO = "GaryDeeplo/videomaker-deeplo"
RAW = f"https://raw.githubusercontent.com/{REPO}/main"
CACHE = ROOT / ".update_check.json"
KEEP = (".env", "jobs/", "dist/", "profil.json", ".update_check.json")


def vt(v):
    """« 2026.11.22.2 » -> (2026, 11, 22, 2) : comparaison numérique, pas alphabétique."""
    return tuple(int(x) for x in str(v).split(".") if x.isdigit()) or (0,)


def local_version():
    p = ROOT / "VERSION"
    return p.read_text(encoding="utf-8").strip() if p.exists() else "0"


def fetch(url, timeout=4):
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "videomaker-deeplo"}), timeout=timeout) as r:
        return r.read()


def get_file(name):
    """Fichier du dépôt public : CDN raw (rapide), sinon API GitHub (le CDN met quelques minutes à voir un nouveau fichier)."""
    try:
        return fetch(f"{RAW}/{name}").decode("utf-8")
    except Exception:  # noqa: BLE001
        req = urllib.request.Request(f"https://api.github.com/repos/{REPO}/contents/{name}",
                                     headers={"User-Agent": "videomaker-deeplo", "Accept": "application/vnd.github.raw"})
        with urllib.request.urlopen(req, timeout=6) as r:
            return r.read().decode("utf-8")


def news_since(changelog, version):
    """Lignes du journal plus récentes que la version locale (sections « ## <version> »)."""
    res, on = [], False
    for line in changelog.splitlines():
        if line.startswith("## "):
            on = vt(line[3:].split()[0]) > vt(version)
            continue
        if on and line.strip().startswith("-"):
            res.append(line.strip()[1:].strip())
    return res[:8]


def check(force=False):
    loc = local_version()
    if not force and CACHE.exists():
        c = json.loads(CACHE.read_text(encoding="utf-8"))
        if time.time() - c.get("t", 0) < 12 * 3600 and c.get("locale") == loc:
            return c["res"]
    try:
        pub = get_file("VERSION").strip()
        maj = vt(pub) > vt(loc)
        news = news_since(get_file("CHANGELOG.md"), loc) if maj else []
        res = {"locale": loc, "publiee": pub, "maj": maj, "nouveautes": news}
    except Exception as e:  # noqa: BLE001 — hors ligne : on n'insiste pas
        return {"locale": loc, "publiee": None, "maj": False, "erreur": str(e)[:80]}
    CACHE.write_text(json.dumps({"t": time.time(), "locale": loc, "res": res}, ensure_ascii=False), encoding="utf-8")
    return res


def protected(rel):
    rel = rel.replace("\\", "/")
    if rel.startswith("brands/") and not rel.startswith("brands/_exemple/"):
        return True
    return any(rel == k or rel.startswith(k) for k in KEEP)


def install():
    before = local_version()
    if (ROOT / ".git").exists():
        r = subprocess.run(["git", "pull", "--ff-only"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
        return {"ok": r.returncode == 0, "mode": "git pull", "avant": before, "apres": local_version(), "log": (r.stdout + r.stderr)[-400:]}
    data = fetch(f"https://github.com/{REPO}/archive/refs/heads/main.zip", timeout=120)
    n, skipped = 0, 0
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for info in z.infolist():
            if info.is_dir():
                continue
            rel = info.filename.split("/", 1)[1] if "/" in info.filename else ""
            if not rel:
                continue
            if protected(rel):
                skipped += 1
                continue
            dst = ROOT / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            with z.open(info) as src, open(dst, "wb") as f:
                shutil.copyfileobj(src, f)
            n += 1
    if CACHE.exists():
        CACHE.unlink()
    return {"ok": True, "mode": "zip", "avant": before, "apres": local_version(), "fichiers_mis_a_jour": n, "proteges": skipped,
            "suite": "python .claude/skills/videomaker-deeplo/scripts/check.py"}


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    res = check(force=True) if cmd == "check" else install() if cmd == "install" else {"erreur": "check | install"}
    print(json.dumps(res, ensure_ascii=False, indent=1))

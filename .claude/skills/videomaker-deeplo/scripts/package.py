"""PAQUET de distribution -> dist/deeplo-video-maker-<pour>-<AAAA-MM-JJ>.zip

  python package.py --pour equipe     # Deeplo / associés : tout sauf vidéos clients, clés, rendus
  python package.py --pour client     # un client : sans les chartes ni les aperçus tirés de vidéos d'autres clients

Jamais dans un paquet : jobs/ (vidéos et rushs clients), .env (clés), renders, node_modules, caches, dist/.
« client » retire aussi brands/ (sauf _exemple) et, dans library/, les aperçus (preview.mp4, poster.jpg) des entrées
dont la source est le job d'un client : la scène reste utilisable, ses images d'un autre client ne partent pas.
Le paquet est ensuite vérifié : décompressé dans un dossier temporaire, setup.py plan doit s'y exécuter.
"""
import argparse
import datetime
import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

from common import ROOT, out

NEVER_DIRS = {"jobs", "dist", "node_modules", "__pycache__", ".hyperframes", "renders", ".git", "tts_cache"}
NEVER_FILES = {".env", "PLAN.md", "profil.json"}  # profil : préférences de l'utilisateur de cette machine


def keep(rel, pour):
    parts = rel.parts
    if any(p in NEVER_DIRS for p in parts) or rel.name in NEVER_FILES or rel.suffix in (".pyc", ".part"):
        return False
    if pour == "client":
        if parts[0] == "brands" and (len(parts) < 2 or parts[1] != "_exemple"):
            return False
        if rel.as_posix() == "library/index.html":  # régénérée sans les aperçus retirés
            return False
        if parts[0] == "library" and rel.name in ("preview.mp4", "poster.jpg"):
            meta = ROOT / Path(*parts[:-1]) / "meta.json"
            if meta.exists() and json.loads(meta.read_text(encoding="utf-8")).get("source_job"):
                return False
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pour", choices=["equipe", "client"], required=True)
    a = ap.parse_args()
    dist = ROOT / "dist"
    dist.mkdir(exist_ok=True)
    name = f"deeplo-video-maker-{a.pour}-{datetime.date.today()}"
    zpath = dist / f"{name}.zip"
    n, size = 0, 0
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for p in sorted(ROOT.rglob("*")):
            if not p.is_file():
                continue
            rel = p.relative_to(ROOT)
            if keep(rel, a.pour):
                z.write(p, Path(name) / rel)
                n += 1
                size += p.stat().st_size
        for d in ("jobs", "studio/renders"):
            z.writestr(f"{name}/{d}/.gitkeep", "")
        if a.pour == "client":
            z.writestr(f"{name}/library/LISEZMOI.txt",
                       "Les aperçus tirés de vidéos d'autres clients ont été retirés. Chaque scène reste utilisable ;\n"
                       "les aperçus se recréent avec vos propres vidéos (python .claude/skills/videomaker-deeplo/scripts/library.py save).\n")

    # vérification : le paquet s'exécute hors de ce dossier
    with tempfile.TemporaryDirectory() as tmp:
        with zipfile.ZipFile(zpath) as z:
            z.extractall(tmp)
            leaked = [f for f in z.namelist() if f.endswith(".env") or "/jobs/" in f and not f.endswith(".gitkeep")]
        r = subprocess.run([sys.executable, str(Path(tmp) / name / ".claude/skills/videomaker-deeplo/scripts/setup.py"), "plan"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        runs = r.returncode == 0 and '"etat"' in r.stdout
        if a.pour == "client":
            gal = subprocess.run([sys.executable, str(Path(tmp) / name / ".claude/skills/videomaker-deeplo/scripts/library.py"), "gallery"],
                                 capture_output=True, text=True, encoding="utf-8", errors="replace")
            runs = runs and gal.returncode == 0
            with zipfile.ZipFile(zpath, "a") as z:
                z.write(Path(tmp) / name / "library" / "index.html", f"{name}/library/index.html")
    out(ok=runs and not leaked, paquet=str(zpath), fichiers=n, taille_mo=round(zpath.stat().st_size / 1e6, 1),
        contenu_mo=round(size / 1e6, 1), fuite=leaked, setup_plan_hors_dossier="ok" if runs else r.stderr[-400:])


if __name__ == "__main__":
    main()

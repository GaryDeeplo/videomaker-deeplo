"""BROUILLONS NUMÉROTÉS : chaque aperçu rendu s'appelle renders/v<N>-<ce qui change>.mp4 et laisse une ligne dans
work/journal.md (date, version, ce qui a changé), pour retrouver à quoi correspond chaque retour du client.

  python brouillon.py <job> "<ce qui change>" [--rapide]     # rend l'aperçu (qualité brouillon, 15 i/s avec --rapide)
  python brouillon.py <job> --liste                           # les versions déjà rendues

La composition rendue est celle du job (index.html), telle que le dernier monteur l'a écrite.
"""
import argparse
import datetime
import os
import re
import subprocess
import unicodedata

from common import fail, job_dir, out

NPX = ["cmd", "/c", "npx"] if os.name == "nt" else ["npx"]


def slugify(s):
    s = unicodedata.normalize("NFD", s.lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:40] or "apercu"


def versions(job):
    return sorted((int(m.group(1)), f.name) for f in (job / "renders").glob("v*-*.mp4") if (m := re.match(r"v(\d+)-", f.name)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("job")
    ap.add_argument("change", nargs="?", help="ce qui change dans cette version, en quelques mots")
    ap.add_argument("--rapide", action="store_true", help="15 i/s (≈ -40 %), pour juger le montage, pas la fluidité")
    ap.add_argument("--liste", action="store_true")
    a = ap.parse_args()
    job = job_dir(a.job)
    if a.liste:
        return out(ok=True, versions=[n for _, n in versions(job)])
    if not a.change:
        fail("dis ce qui change dans cette version (ex. « musique plus douce »)")
    if not (job / "index.html").exists():
        fail("pas de composition : lance d'abord le monteur")
    n = (versions(job)[-1][0] + 1) if versions(job) else 1
    name = f"v{n}-{slugify(a.change)}.mp4"
    (job / "renders").mkdir(exist_ok=True)
    cmd = NPX + ["--yes", "hyperframes@0.9.71", "render", "-q", "draft", "-w", "8", *(["-f", "15"] if a.rapide else []),
                 "-o", f"renders/{name}"]
    r = subprocess.run(cmd, cwd=job, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0 or not (job / "renders" / name).exists():
        fail("rendu échoué", log=(r.stdout + r.stderr)[-800:])
    jr = job / "work" / "journal.md"
    jr.parent.mkdir(exist_ok=True)
    if not jr.exists():
        jr.write_text("# Journal des versions\n\n", encoding="utf-8")
    with jr.open("a", encoding="utf-8") as f:
        f.write(f"- {datetime.datetime.now():%Y-%m-%d %H:%M} · v{n} · {a.change} · renders/{name}\n")
    out(ok=True, version=n, fichier=str(job / "renders" / name), journal=str(jr))


if __name__ == "__main__":
    main()

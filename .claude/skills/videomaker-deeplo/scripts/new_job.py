"""Crée un job vidéo : jobs/<AAAA-MM-JJ>-<client>-<sujet>/ (c'est aussi un projet HyperFrames).

  python new_job.py <client> <sujet> [--brand <dossier brands/>] [--rush FICHIER ...]

Arborescence : inbox/ (fichiers du client), work/ (JSON intermédiaires), assets/ (médias de la
composition), renders/ (MP4), job.json.
"""
import argparse
import datetime
import re
import shutil
import unicodedata

from common import ROOT, out, write_json


def slugify(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("client")
    ap.add_argument("sujet")
    ap.add_argument("--brand", default="")
    ap.add_argument("--rush", nargs="*", default=[])
    a = ap.parse_args()

    name = f"{datetime.date.today():%Y-%m-%d}-{slugify(a.client)}-{slugify(a.sujet)}"
    job = ROOT / "jobs" / name
    for d in ("inbox", "work", "assets", "renders"):
        (job / d).mkdir(parents=True, exist_ok=True)
    shutil.copy(ROOT / "studio" / "hyperframes.json", job / "hyperframes.json")
    write_json(job / "job.json", {"name": name, "client": a.client, "sujet": a.sujet,
                                  "brand": a.brand or slugify(a.client), "created": str(datetime.date.today())})
    copied = []
    for r in a.rush:
        dst = job / "inbox" / shutil.os.path.basename(r)
        shutil.copy2(r, dst)
        copied.append(str(dst))
    out(ok=True, job=str(job), rushes=copied)


if __name__ == "__main__":
    main()

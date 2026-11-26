"""Crée un job vidéo : jobs/<AAAA-MM-JJ>-<client>-<sujet>/ (c'est aussi un projet HyperFrames).

  python new_job.py <client> <sujet> [--brand <dossier brands/>] [--rush FICHIER ...]

Arborescence : inbox/ (fichiers du client), work/ (JSON intermédiaires), assets/ (médias de la
composition), renders/ (MP4), job.json.
Réponse : `charte` = « trouvée » | « absente » (brands/<marque>/brand.json). Absente : `marques` (dossiers de brands/)
et `proche` (le plus ressemblant) ; relance avec --brand <dossier> ou crée la charte depuis brands/_exemple/.
"""
import argparse
import datetime
import difflib
import re
import shutil
import unicodedata

from common import ROOT, fail, out, write_json


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

    brand = slugify(a.brand) if a.brand else slugify(a.client)
    known = sorted(b.parent.name for b in (ROOT / "brands").glob("*/brand.json") if not b.parent.name.startswith("_"))
    missing = [r for r in a.rush if not shutil.os.path.isfile(r)]
    if missing:
        fail("rush introuvable", fichiers=missing)
    name = f"{datetime.date.today():%Y-%m-%d}-{slugify(a.client)}-{slugify(a.sujet)}"
    job = ROOT / "jobs" / name
    for d in ("inbox", "work", "assets", "renders"):
        (job / d).mkdir(parents=True, exist_ok=True)
    shutil.copy(ROOT / "studio" / "hyperframes.json", job / "hyperframes.json")
    write_json(job / "job.json", {"name": name, "client": a.client, "sujet": a.sujet,
                                  "brand": brand, "created": str(datetime.date.today())})
    copied = []
    for r in a.rush:
        dst = job / "inbox" / shutil.os.path.basename(r)
        shutil.copy2(r, dst)
        copied.append(str(dst))
    if (ROOT / "brands" / brand / "brand.json").exists():
        out(ok=True, job=str(job), rushes=copied, marque=brand, charte="trouvée")
    else:
        near = difflib.get_close_matches(brand, known, n=1, cutoff=0.4) or [k for k in known if k in brand or brand in k][:1]
        out(ok=True, job=str(job), rushes=copied, marque=brand, charte="absente", marques=known, proche=near[0] if near else None,
            attention=f"pas de brands/{brand}/brand.json : la vidéo sortira sans charte. Corrige \"brand\" dans job.json "
                      f"(une des marques), ou crée brands/{brand}/ depuis brands/_exemple/.")


if __name__ == "__main__":
    main()

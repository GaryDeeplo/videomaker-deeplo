"""ACCUEIL du skill : ce que Claude doit savoir avant de poser ses questions (une ligne JSON)

  python onboard.py status [--marque martin] [--parcours rush|sans-rush|shorts]   # installation, clés, marques, projets
                                                  # récents, préférences connues, fichiers récents de Téléchargements,
                                                  # et avec --marque : les goûts gardés du client (gouts.py prompt)
  python onboard.py profil --marque martin --parcours rush format=9:16 style=boite reseaux=instagram,tiktok musique=upbeat
  python onboard.py brief <job> objectif=vendre public=particuliers duree=30 ton=dynamique cta="Réservez sur le site"                           mentions="-20 % jusqu'au 31/12" eviter="les prix" langues=fr,nl      # -> work/brief.json

Préférences (profil.json à la racine, jamais dans git ni dans les paquets) RANGÉES PAR MARQUE ET PAR PARCOURS : un Reel
dynamique pour une marque ne décide pas du style d'une vidéo sobre pour une autre. Ce sont des valeurs par défaut :
la demande du moment gagne toujours, et on n'enregistre qu'avec l'accord de l'utilisateur.
"""
import argparse
import shutil
import sys
from pathlib import Path

from common import ROOT, env_key, out, read_json, write_json

PROFIL = ROOT / "profil.json"
VIDEO = (".mp4", ".mov", ".m4v", ".webm", ".mkv")
IMAGE = (".jpg", ".jpeg", ".png", ".webp", ".heic")


def job_state(j):
    r = j / "renders"
    if (r / "livraison").exists() and any((r / "livraison").glob("*.mp4")):
        return "livré"
    if (j / "work" / "valide.json").exists():
        return "validé par le client, rendu final à faire"
    if (j / "work" / "review" / "validation.html").exists():
        return "page de validation envoyée (review.py)"
    if r.exists() and any(r.glob("*.mp4")):
        return "aperçu fait"
    if (j / "index.html").exists():
        return "monté, pas encore rendu"
    if any((j / "work").glob("*_plan.json")) or any((j / "work").glob("*_storyboard.json")):
        return "en cours (plan / storyboard)"
    return "créé"


def load():
    p = read_json(PROFIL) if PROFIL.exists() else {}
    return p if "reglages" in p else {"reglages": {}}


def status(a):
    jobs = []
    for j in sorted((ROOT / "jobs").glob("20*"), key=lambda p: p.stat().st_mtime, reverse=True):
        if not (j / "job.json").exists() or "test" in j.name:
            continue
        m = read_json(j / "job.json")
        jobs.append({"job": j.name, "client": m.get("client"), "marque": m.get("brand") or None, "sujet": m.get("sujet"),
                     "etat": job_state(j)})
        if len(jobs) == 5:
            break
    brands = [{"dossier": b.parent.name, "nom": read_json(b).get("name", b.parent.name)}
              for b in sorted((ROOT / "brands").glob("*/brand.json")) if not b.parent.name.startswith("_")]
    dl, recent = Path.home() / "Downloads", []
    if dl.exists():
        cands = [p for p in dl.iterdir() if p.is_file() and p.suffix.lower() in VIDEO + IMAGE]
        for p in sorted(cands, key=lambda p: p.stat().st_mtime, reverse=True)[:5]:
            recent.append({"fichier": str(p), "type": "vidéo" if p.suffix.lower() in VIDEO else "image",
                           "mo": round(p.stat().st_size / 1e6, 1)})
    prof = load()["reglages"]
    key = f"{a.marque or '-'}/{a.parcours or '-'}"
    gouts = None
    if a.marque:  # client connu : ses retours gardés (brands/<client>/gouts.json), à garder en tête tout le projet
        try:
            from gouts import prompt_text
            gouts = prompt_text(a.marque) or None
        except SystemExit:  # nom de marque hors brands/ : pas de goûts
            pass
    out(ok=True, installe=all(shutil.which(t) for t in ("ffmpeg", "ffprobe", "node")),
        cles={"gemini_voix": bool(env_key("GEMINI_API_KEY")), "fish_audio": bool(env_key("FISH_API_KEY")), "pixabay": bool(env_key("PIXABAY_API_KEY")),
              "groq": bool(env_key("GROQ_API_KEY"))},
        marques=brands, projets_recents=jobs, telechargements_recents=recent,
        reglages_connus=prof.get(key) if (a.marque or a.parcours) else prof,
        gouts_client=gouts,
        mise_a_jour=__import__("update").check(),
        note="réglages = valeurs par défaut pour CETTE marque et CE parcours ; la demande du moment gagne toujours")


def profil(a, pairs):
    p = load()
    key = f"{a.marque or '-'}/{a.parcours or '-'}"
    cur = p["reglages"].setdefault(key, {})
    for kv in pairs:
        if "=" in kv:
            k, v = kv.split("=", 1)
            cur[k.strip()] = [x for x in v.split(",") if x] if "," in v else v.strip()
    write_json(PROFIL, p)
    out(ok=True, cle=key, reglages=cur)


def brief(job_name, pairs):
    """Le besoin de CETTE vidéo (objectif, public, durée, ton, appel à l'action, mentions, à éviter, langues)."""
    from common import job_dir
    job = job_dir(job_name)
    dst = job / "work" / "brief.json"
    b = read_json(dst) if dst.exists() else {}
    for kv in pairs:
        if "=" in kv:
            k, v = kv.split("=", 1)
            b[k.strip()] = [x.strip() for x in v.split(",") if x.strip()] if k.strip() == "langues" else v.strip()
    dst.parent.mkdir(exist_ok=True)
    write_json(dst, b)
    out(ok=True, brief=b, fichier=str(dst))


def main():
    if len(sys.argv) > 2 and sys.argv[1] == "brief":
        return brief(sys.argv[2], sys.argv[3:])
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["status", "profil"])
    ap.add_argument("--marque")
    ap.add_argument("--parcours", choices=["rush", "sans-rush", "shorts"])
    a, rest = ap.parse_known_args()
    profil(a, rest) if a.cmd == "profil" else status(a)


if __name__ == "__main__":
    main()

"""ACCUEIL du skill : ce que Claude doit savoir avant de poser ses questions (une ligne JSON)

  python onboard.py status [--marque martin] [--parcours <parcours>]   # installation, clés, marques (+ 2 récentes),
                                                  # projets récents, préférences connues, fichiers récents de
                                                  # Téléchargements, et avec --marque : les goûts gardés du client
  python onboard.py profil --marque martin --parcours rush format=9:16 style=boite reseaux=instagram,tiktok musique=upbeat
  python onboard.py brief <job> objectif=vendre public=particuliers duree=30 ton=dynamique cta="Réservez sur le site"
                    mentions="-20 % jusqu'au 31/12" eviter="les prix" langues=fr,nl accroche=titre   # -> work/brief.json

Parcours : rush, sans-rush, shorts, montage, plusieurs-rushs, explainer, punch, infographie, collage, ecran-partage,
mots, immobilier, traduction, lot, calendrier, guide, vitrine.
Clés de profil (liste fermée ; une clé inconnue est ignorée avec un avertissement et la clé la plus proche) : voir
PROFIL_KEYS. Seules `reseaux` et `langues` sont des listes (découpées par virgule) ; les autres valeurs restent
entières (un cta « Réservez, c'est simple » garde sa virgule).

Préférences (profil.json à la racine, jamais dans git ni dans les paquets) RANGÉES PAR MARQUE ET PAR PARCOURS : un Reel
dynamique pour une marque ne décide pas du style d'une vidéo sobre pour une autre. Ce sont des valeurs par défaut :
la demande du moment gagne toujours, et on n'enregistre qu'avec l'accord de l'utilisateur.
"""
import argparse
import difflib
import shutil
import sys
from pathlib import Path

from common import ROOT, env_key, out, read_json, write_json

PROFIL = ROOT / "profil.json"
VIDEO = (".mp4", ".mov", ".m4v", ".webm", ".mkv")
IMAGE = (".jpg", ".jpeg", ".png", ".webp", ".heic")

PARCOURS = ["rush", "sans-rush", "shorts", "montage", "plusieurs-rushs", "explainer", "punch", "infographie", "collage",
            "ecran-partage", "mots", "immobilier", "traduction", "lot", "calendrier", "guide", "vitrine"]
LISTES = {"reseaux", "langues"}  # seules valeurs découpées par virgule
PROFIL_KEYS = {
    "format": "9:16 | 1:1 | 16:9 | tous",
    "style": "style de sous-titres (pop, karaoke, minimal, boite, impact, duo, mono, bulle, souligne, geant, editorial)",
    "reseaux": "instagram,tiktok,facebook,linkedin,youtube",
    "musique": "ambiance (upbeat, chill, inspiring, energetic, acoustic, cinematic, funky, ambient) ou aucune",
    "broll": "oui | non", "sous_titres": "oui | non (en plus des mots dynamiques)", "emoji": "oui | non",
    "zooms": "oui | non", "accroche": "non | titre | dessin", "accroche_style": "papier, plan, pate, neon, …",
    "layout": "full | split | cards", "pack": "ecran-partage | explainer | punch | infographie | montage | classique",
    "habillage": "propositions retenues d'habitude (texte libre)",
    "ton": "dynamique | chaleureux | haut de gamme | sobre", "public": "particuliers | professionnels | candidats | clients",
    "objectif": "vendre | faire connaître | recruter | informer | fidéliser", "cta": "appel à l'action habituel",
    "duree": "15 | 30 | 60 | libre", "langues": "fr,nl,en", "voix": "gemini-<ton> | fish | enregistrement | aucune",
    "look": "tuto-cartes | luxe | ecran-partage | classique", "ouverture": "dessin | derriere | titre | sans",
    "polices": "charte | editorial | chaleureux | premium | moderne | creatif | punch | ludique | net",
}
BRIEF_KEYS = {"objectif", "public", "duree", "ton", "cta", "mentions", "eviter", "langues", "accroche", "accroche_style",
              "habillage", "sous_titres", "format", "reseaux", "look", "ouverture", "polices"}


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


def parse_pairs(pairs, allowed):
    """k=v -> (valeurs gardées, avertissements). Clé hors liste : ignorée, avec la clé la plus proche."""
    vals, warns = {}, []
    for kv in pairs:
        if "=" not in kv:
            warns.append(f"« {kv} » ignoré : attendu cle=valeur")
            continue
        k, v = kv.split("=", 1)
        k = k.strip()
        norm = k.lower().replace("-", "_").replace("é", "e").replace("è", "e")
        if norm in allowed:
            if norm != k:
                warns.append(f"clé « {k} » lue comme « {norm} »")
            k = norm
        else:
            near = difflib.get_close_matches(norm, list(allowed), n=1, cutoff=0.6)
            warns.append(f"clé inconnue « {k} » ignorée" + (f" : vouliez-vous « {near[0]}= » ?" if near else "")
                         + f" (clés : {', '.join(sorted(allowed))})")
            continue
        vals[k] = [x.strip() for x in v.split(",") if x.strip()] if k in LISTES else v.strip()
    return vals, warns


def recent_brands(limit=2):
    """Marques des projets les plus récents (pour l'accueil : 2 marques récentes + « autre »)."""
    seen = []
    for j in sorted((ROOT / "jobs").glob("20*"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            b = read_json(j / "job.json").get("brand")
        except (OSError, ValueError):
            continue
        if b and b not in seen and (ROOT / "brands" / b / "brand.json").exists():
            seen.append(b)
        if len(seen) == limit:
            break
    return seen


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
        marques=brands, marques_recentes=recent_brands(), projets_recents=jobs, telechargements_recents=recent,
        reglages_connus=prof.get(key) if (a.marque or a.parcours) else prof,
        gouts_client=gouts,
        mise_a_jour=__import__("update").check(),
        note="réglages = valeurs par défaut pour CETTE marque et CE parcours ; la demande du moment gagne toujours")


def profil(a, pairs):
    p = load()
    key = f"{a.marque or '-'}/{a.parcours or '-'}"
    vals, warns = parse_pairs(pairs, PROFIL_KEYS)
    cur = p["reglages"].setdefault(key, {})
    cur.update(vals)
    if not cur:
        del p["reglages"][key]
    if vals:
        write_json(PROFIL, p)
    out(ok=bool(vals) or not pairs, cle=key, reglages=cur, enregistre=sorted(vals), avertissements=warns or None)


def brief(job_name, pairs):
    """Le besoin de CETTE vidéo (objectif, public, durée, ton, appel à l'action, mentions, à éviter, langues)."""
    from common import job_dir
    job = job_dir(job_name)
    dst = job / "work" / "brief.json"
    b = read_json(dst) if dst.exists() else {}
    vals, warns = parse_pairs(pairs, BRIEF_KEYS)
    b.update(vals)
    dst.parent.mkdir(exist_ok=True)
    write_json(dst, b)
    out(ok=True, brief=b, fichier=str(dst), avertissements=warns or None)


def main():
    if len(sys.argv) > 2 and sys.argv[1] == "brief":
        return brief(sys.argv[2], sys.argv[3:])
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["status", "profil"])
    ap.add_argument("--marque")
    ap.add_argument("--parcours", choices=PARCOURS)
    a, rest = ap.parse_known_args()
    unknown = [r for r in rest if r.startswith("--")]
    if unknown:
        ap.error(f"option inconnue : {' '.join(unknown)}")
    profil(a, rest) if a.cmd == "profil" else status(a)


if __name__ == "__main__":
    main()

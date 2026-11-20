"""SUGGESTION DE MOTIONS à partir de ce qui est DIT -> work/<slug>_motions_suggested.json

  python suggest_motions.py <job> <slug> [--per-min 5] [--gap 4] [--apply]

Lit les mots horodatés de la vidéo (rush dérushé ou voix off d'un storyboard) et propose des blocs de la bibliothèque :
  montant en euros -> compteur · pourcentage -> jauge · note « 4,9 sur 5 » -> note-etoiles · « plus que 3 jours » ->
  compte-rebours · « nouveau », « offert », « -20 % » -> sticker · « réservez », « commandez »… -> bouton-cta ·
  « abonnez-vous », « suivez-nous » -> suivre · mots-clés -> emoji animé (bravo 👏, idée 💡, merci 🙌, succès 🏆…).
Toutes les valeurs viennent des mots prononcés (jamais inventées). Espacement minimal (--gap), plafond par minute,
rien sous l'accroche d'un short. Claude relit, garde / retire / ajuste, puis copie dans work/<slug>_motions.json
(rush) ou dans le champ "motions" des scènes (storyboard). --apply écrit directement (à relire quand même).
"""
import argparse
import re

from build_text import remap
from common import _norm_word, config, fail, job_dir, out, read_json, write_json

NUMW = {"un": 1, "une": 1, "deux": 2, "trois": 3, "quatre": 4, "cinq": 5, "six": 6, "sept": 7, "huit": 8, "neuf": 9,
        "dix": 10, "quinze": 15, "vingt": 20, "trente": 30, "cent": 100, "mille": 1000}
CTA = {"reservez": "Réserver", "reserver": "Réserver", "commandez": "Commander", "commander": "Commander",
       "inscrivezvous": "S'inscrire", "inscrivez": "S'inscrire", "contacteznous": "Nous contacter", "contactez": "Nous contacter",
       "appelez": "Appeler", "appeleznous": "Nous appeler", "ecriveznous": "Nous écrire", "decouvrez": "Découvrir",
       "profitez": "En profiter", "testez": "Essayer", "essayez": "Essayer", "rejoignez": "Nous rejoindre"}
FOLLOW = {"abonnezvous", "abonnez", "suiveznous", "suivez", "abonne", "abonnes"}
STICKER = {"nouveau": "NOUVEAU", "nouvelle": "NOUVEAU", "nouveaute": "NOUVEAUTÉ", "gratuit": "GRATUIT",
           "gratuite": "GRATUIT", "offert": "OFFERT", "offerte": "OFFERT", "exclusif": "EXCLUSIF", "inedit": "INÉDIT"}
EMOJI = {"bravo": "applaudir", "felicitations": "applaudir", "merci": "bravo", "idee": "idee", "astuce": "idee",
         "conseil": "idee", "succes": "trophee", "reussite": "trophee", "gagne": "trophee", "gagner": "trophee", "gagnez": "trophee",
         "champion": "trophee", "rapide": "fusee", "rapidement": "fusee", "lancement": "fusee", "decoller": "fusee",
         "cadeau": "cadeau", "adore": "adore", "aime": "coeur", "aimez": "coeur", "passion": "coeur", "amour": "coeur",
         "parfait": "valide", "valide": "valide", "garanti": "valide", "incroyable": "waouh", "genial": "waouh",
         "magnifique": "waouh", "top": "waouh", "attention": "alarme", "urgent": "alarme", "important": "cloche",
         "regardez": "regard", "voyez": "regard", "objectif": "cible", "objectifs": "cible", "force": "force",
         "fort": "force", "puissant": "force", "fete": "fete", "anniversaire": "fete", "celebrer": "fete",
         "pourquoi": "reflexion", "question": "reflexion", "drole": "rire", "ici": "doigt", "lien": "doigt",
         "brillant": "eclat", "eclatant": "eclat", "chaud": "feu", "explose": "feu", "star": "etoile", "ok": "pouce"}


def keys(w):
    return {_norm_word(w)} | {_norm_word(x) for x in re.split(r"[’'\-]", w)}


def number_at(ws, i):
    """Nombre dit à partir du mot i (chiffres, « 1 200 », « 4,9 », ou un mot-nombre simple). -> (valeur, nb de mots)"""
    t = ws[i]["w"].replace(" ", "").replace("\xa0", "")
    m = re.fullmatch(r"(\d+)(?:[.,](\d+))?\D*", t)
    if m:
        val, used = float(m.group(1) + ("." + m.group(2) if m.group(2) else "")), 1
        while i + used < len(ws) and re.fullmatch(r"\d{3}\D*", ws[i + used]["w"]) and not m.group(2):
            val = val * 1000 + float(re.match(r"\d{3}", ws[i + used]["w"]).group(0))
            used += 1
        return val, used
    n = _norm_word(t)
    return (float(NUMW[n]), 1) if n in NUMW else (None, 0)


def json_val(s):
    v = s.get("vars", {})
    return str(v.get("to", v.get("value", v.get("rating", v.get("label", s.get("name", ""))))))


def suggest(ws, lo, hi, hook_end, per_min, gap, H, W):
    dur = max(1.0, hi - lo)
    cap = max(1, round(dur / 60 * per_min))
    occ = {}
    raw = []
    for i, w in enumerate(ws):  # occurrences comptées comme motion_nodes : à partir du début de la fenêtre (scène)
        if w["start"] >= lo:
            for k in keys(w["w"]):
                occ[k] = occ.get(k, 0) + 1
        w["_occ"] = dict(occ)
    top = 22 if H > W else 18
    for i, w in enumerate(ws):
        if not (lo <= w["start"] <= hi):
            continue
        k = _norm_word(w["w"])
        nxt = " ".join(_norm_word(x["w"]) for x in ws[i + 1:i + 4])
        prev = " ".join(_norm_word(x["w"]) for x in ws[max(0, i - 3):i])
        val, used = number_at(ws, i)
        base = {"word": w["w"], "occurrence": w["_occ"].get(k, 1), "t": round(w["start"], 2)}
        if val is not None and used:
            after = " ".join(_norm_word(x["w"]) for x in ws[i + used:i + used + 3])
            num_txt = ws[i]["w"]
            if re.match(r"^(pour ?cent|%)", after) or "%" in num_txt:
                if 0 < val <= 100:
                    raw.append({**base, "block": "jauge", "score": 5, "vars": {"value": val, "label": "", "top": top},
                                "why": f"pourcentage dit : {val:g} %"})
                continue
            if re.match(r"^sur (5|cinq)", after) and 0 < val <= 5:
                raw.append({**base, "block": "note-etoiles", "score": 6, "vars": {"rating": val, "count": "", "top": top},
                            "why": f"note dite : {val:g}/5 (préciser le nombre d'avis RÉEL)"})
                continue
            if ("plus que" in prev or "encore" in prev) and re.match(r"^(jours?|heures?|semaines?)", after) and val <= 30:
                unit = after.split()[0]
                raw.append({**base, "block": "compte-rebours", "score": 5,
                            "vars": {"from": int(val) + 2, "to": int(val), "prefix": "J-" if unit.startswith("jour") else "",
                                     "label": f"{'jours' if unit.startswith('jour') else unit} restants", "top": top},
                            "why": f"échéance dite : {val:g} {unit}"})
                continue
            unit = ""
            if re.match(r"^(euros?|eur|€)", after) or "€" in num_txt:
                unit = " €"
            elif re.match(r"^ans?\b|^annees?", after):
                unit = " ans"
            if val >= 10 or unit:
                lbl = re.sub(r"^(euros?|ans?|annees?)\s*", "", after).strip()
                raw.append({**base, "block": "compteur", "score": 4 + (1 if unit else 0) + (1 if val >= 100 else 0),
                            "vars": {"from": 0, "to": val, "prefix": "", "suffix": unit, "decimals": 0 if val == int(val) else 1,
                                     "label": "", "top": top},
                            "why": f"chiffre dit : {num_txt}{unit} (légende à écrire avec les mots de la phrase)"})
            continue
        if k in STICKER:
            raw.append({**base, "block": "sticker", "score": 5, "vars": {"label": STICKER[k], "top": top, "left": 72},
                        "why": f"« {w['w']} »"})
        elif k in CTA or any(x in CTA for x in keys(w["w"])):
            label = CTA.get(k) or next(CTA[x] for x in keys(w["w"]) if x in CTA)
            raw.append({**base, "block": "bouton-cta", "score": 5, "vars": {"label": label, "sub": "", "top": 40},
                        "why": f"appel à l'action dit : « {w['w']} » (sous-texte réel : lien en bio, site…)"})
        elif k in FOLLOW or nxt.startswith("nous") and k in ("suivez", "abonnez"):
            raw.append({**base, "block": "suivre", "score": 5, "vars": {"name": "", "handle": "", "top": 40},
                        "why": "invitation à s'abonner (nom et @compte RÉELS à remplir)"})
        elif k in EMOJI:
            raw.append({**base, "block": "lottie", "name": EMOJI[k], "score": 2, "dur": 1.6,
                        "vars": {"x": 74, "y": 26, "size": 26}, "why": f"« {w['w']} » -> emoji {EMOJI[k]}"})
    # phrase complète autour du mot (pour écrire la légende avec les mots réellement dits)
    for s in raw:
        i = next(j for j, w in enumerate(ws) if round(w["start"], 2) == s["t"])
        a_, b_ = i, i
        while a_ > 0 and not re.search(r"[.!?…]$", ws[a_ - 1]["w"]) and i - a_ < 14:
            a_ -= 1
        while b_ < len(ws) - 1 and not re.search(r"[.!?…]$", ws[b_]["w"]) and b_ - i < 14:
            b_ += 1
        s["phrase"] = " ".join(w["w"] for w in ws[a_:b_ + 1])
    # sélection : score, variété (un même type de bloc perd des points à chaque reprise, une même valeur une seule
    # fois), espacement minimal, plafond par minute, rien sous l'accroche
    picked, seen_vals = [], set()
    pool = [s for s in raw if s["t"] >= hook_end]
    while pool and len(picked) < cap:
        used = {}
        for p in picked:
            used[p["block"]] = used.get(p["block"], 0) + 1
        best = max(pool, key=lambda s: (s["score"] - 2.5 * used.get(s["block"], 0), -s["t"]))
        pool.remove(best)
        val = (best["block"], json_val(best))
        if val in seen_vals or any(abs(best["t"] - p["t"]) < gap for p in picked):
            continue
        seen_vals.add(val)
        picked.append(best)
    picked.sort(key=lambda s: s["t"])
    for j, s in enumerate(picked):
        if s["block"] == "lottie":
            s["vars"]["x"] = 26 if j % 2 else 74  # alterne gauche / droite
        s.setdefault("dur", 3.0 if s["block"] in ("compteur", "jauge", "note-etoiles", "compte-rebours", "suivre") else 2.6)
    return picked, len(raw)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("job")
    ap.add_argument("slug")
    ap.add_argument("--per-min", type=float, default=5)
    ap.add_argument("--gap", type=float, default=4.0)
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    job = job_dir(a.job)
    c = config(job)
    W, H = c["visual"]["width"], c["visual"]["height"]
    work = job / "work"
    words = read_json(work / f"{a.slug}_words.json")["words"]
    sb_path = work / f"{a.slug}_storyboard.json"
    hook_end = 3.7 if (work / f"{a.slug}_hook.json").exists() else 0.0
    if sb_path.exists():  # sans rush : par scène (les mots sont déjà dans le temps de la vidéo)
        sb, tm = read_json(sb_path), read_json(work / f"{a.slug}_timing.json")["scenes"]
        total, found, per_scene = 0, 0, []
        for i, (sc, t) in enumerate(zip(sb["scenes"], tm)):
            if sc.get("kind") == "block":
                per_scene.append([])
                continue
            picks, n = suggest(words, t["start"], t["end"], hook_end, a.per_min * 3, a.gap, H, W)
            picks = picks[:1]  # une surimpression par scène au plus
            per_scene.append(picks)
            total += len(picks)
            found += n
        res = {"mode": "storyboard", "scenes": [{"scene": i, "motions": p} for i, p in enumerate(per_scene) if p]}
        if a.apply:
            for i, p in enumerate(per_scene):
                if p:
                    sb["scenes"][i]["motions"] = [{k: v for k, v in m.items() if k not in ("score", "why", "t")} for m in p]
            write_json(sb_path, sb)
    else:  # rush : temps du dérush
        ws = remap(words, read_json(work / f"{a.slug}_map.json")["segments"])
        dur = float(read_json(work / f"{a.slug}_map.json")["out_duration"])
        picks, found = suggest(ws, 0, dur, hook_end, a.per_min, a.gap, H, W)
        total = len(picks)
        res = {"mode": "rush", "motions": picks}
        if a.apply:
            write_json(work / f"{a.slug}_motions.json",
                       [{k: v for k, v in m.items() if k not in ("score", "why", "t")} for m in picks])
    write_json(work / f"{a.slug}_motions_suggested.json", res)
    out(ok=True, mode=res["mode"], candidats=found, proposes=total, applique=a.apply,
        fichier=str(work / f"{a.slug}_motions_suggested.json"),
        a_completer="légendes, nombre d'avis, @compte : uniquement des infos réelles ; retire ce qui n'apporte rien")


if __name__ == "__main__":
    main()

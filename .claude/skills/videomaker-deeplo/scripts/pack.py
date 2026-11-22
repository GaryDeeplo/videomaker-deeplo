"""CHOIX DU PACK et PREMIER JET des temps forts, à partir de la demande, du brief et de ce qui est dit.

  python pack.py choose <job> [--slug s] [--demande "texte de la demande"]
      -> pack conseillé (ecran-partage | explainer | punch | classique) + pourquoi + commandes à lancer
  python pack.py draft <job> <slug> [--pack auto|ecran-partage|explainer|punch]
      -> work/<slug>_panels.json (écran partagé, explainer) ou work/<slug>_punch.json (punch), posés sur les mots dits.
         Si le fichier existe déjà : work/<slug>_panels_draft.json / <slug>_punch_draft.json (rien n'est écrasé).

Le premier jet lit les phrases de text.json (donc après voice.py / build_text.py) : chiffre -> stat (ou prix),
énumération -> check / steps avec pictos, « pas de / ni » -> picto interdit, d'abord / puis / enfin -> étapes,
appel à l'action -> titre + picto, nom concret connu -> image ("query" anglais), sinon titre avec *mot fort*.
Médias du client (inbox/) placés avant toute banque. C'est un brouillon : relis chaque temps fort (textes courts,
vrais chiffres, chapitres, requêtes), puis fetch / pick pour les images et build.
"""
import argparse
import re
import sys
import unicodedata
from pathlib import Path

from build_text import HARD, WEAK
from common import fail, job_dir, out, probe, read_json, write_json

VIDEO = {".mp4", ".mov", ".m4v", ".webm", ".mkv"}
PHOTO = {".jpg", ".jpeg", ".png", ".webp"}

# mot (sans accents, début de mot) -> picto Lucide
ICONS = [
    ("heure", "clock"), ("minute", "clock"), ("rendez", "calendar"), ("reserv", "calendar-check"), ("agenda", "calendar"),
    ("lundi", "calendar-days"), ("mardi", "calendar-days"), ("mercredi", "calendar-days"), ("jeudi", "calendar-days"),
    ("vendredi", "calendar-days"), ("samedi", "calendar-days"), ("dimanche", "calendar-days"), ("semaine", "calendar-days"),
    ("mois", "calendar-days"), ("prix", "tag"), ("euro", "tag"), ("tarif", "tag"), ("promo", "percent"), ("offert", "gift"),
    ("cadeau", "gift"), ("gratuit", "badge-check"), ("nouveau", "sparkles"), ("nouvelle", "sparkles"), ("lien", "link"),
    ("bio", "link"), ("site", "globe"), ("telephone", "phone"), ("appel", "phone"), ("message", "message-circle"),
    ("ecri", "message-circle"), ("mail", "mail"), ("livr", "truck"), ("colis", "package"), ("commande", "shopping-bag"),
    ("achet", "shopping-bag"), ("client", "users"), ("equipe", "users"), ("famille", "users"), ("enfant", "baby"),
    ("eau", "droplet"), ("oeil", "eye"), ("yeux", "eye"), ("regard", "eye"), ("cils", "eye"), ("coeur", "heart"),
    ("soin", "sparkles"), ("beaute", "sparkles"), ("maison", "house"), ("voiture", "car"), ("payer", "credit-card"),
    ("paiement", "credit-card"), ("secur", "shield-check"), ("garanti", "shield-check"), ("rapide", "zap"), ("vite", "zap"),
    ("avis", "star"), ("etoile", "star"), ("idee", "lightbulb"), ("photo", "camera"), ("video", "video"), ("ordinateur", "monitor"),
    ("adresse", "map-pin"), ("boutique", "store"), ("magasin", "store"), ("argent", "coins"), ("gagn", "coins"),
    ("travail", "briefcase"), ("emploi", "briefcase"), ("recrut", "user-plus"), ("outil", "wrench"), ("cafe", "coffee"),
    ("repas", "utensils"), ("restaurant", "utensils"), ("pain", "croissant"), ("boulang", "croissant"), ("fleur", "flower"),
    ("musique", "music"), ("sport", "dumbbell"), ("livre", "book-open"), ("formation", "graduation-cap"), ("sante", "heart-pulse"),
    ("planete", "leaf"), ("nature", "leaf"), ("attention", "triangle-alert"), ("question", "circle-help"), ("valid", "circle-check"),
    ("detente", "armchair"), ("calme", "armchair"), ("dormir", "moon"), ("nuit", "moon"), ("soleil", "sun"), ("ete", "sun"),
]
# nom concret -> requête de banque d'images (anglais, filmable)
QUERIES = {
    "cils": "eyelashes", "cafe": "coffee", "pain": "bread", "croissant": "croissant", "gateau": "cake", "livraison": "delivery",
    "colis": "parcel", "voiture": "car", "maison": "house", "appartement": "apartment", "cuisine": "kitchen",
    "equipe": "team meeting", "bureau": "office", "ordinateur": "laptop", "telephone": "smartphone", "fleurs": "flowers",
    "fleur": "flower", "jardin": "garden", "plage": "beach", "montagne": "mountain", "ville": "city street",
    "restaurant": "restaurant", "repas": "meal", "vin": "wine", "biere": "beer", "chocolat": "chocolate", "coiffure": "hairdresser",
    "cheveux": "hair", "maquillage": "makeup", "massage": "massage", "spa": "spa", "sport": "workout", "velo": "bicycle",
    "chien": "dog", "chat": "cat", "enfants": "children", "bebe": "baby", "mariage": "wedding", "fete": "party",
    "cadeau": "gift box", "boutique": "shop", "magasin": "store", "vetements": "clothes", "chaussures": "shoes",
    "bijoux": "jewelry", "meuble": "furniture", "canape": "sofa", "peinture": "painting", "chantier": "construction site",
    "outils": "tools", "camion": "truck", "argent": "money", "carte": "credit card", "agenda": "calendar", "soin": "skincare",
    "yeux": "eyes", "regard": "eyes", "mains": "hands", "eau": "water", "nature": "nature", "foret": "forest",
}
CTA = {"reservez": "calendar-check", "reserver": "calendar-check", "appelez": "phone", "commandez": "shopping-bag",
       "ecrivez": "message-circle", "suivez": "user-plus", "abonnez": "user-plus", "contactez": "message-circle",
       "inscrivez": "user-plus", "postulez": "briefcase", "venez": "map-pin", "decouvrez": "sparkles", "profitez": "gift"}
STEP = {"d'abord": 1, "dabord": 1, "premierement": 1, "puis": 2, "ensuite": 2, "apres": 2, "enfin": 3, "finalement": 3}
NUMW = {"un": 1, "une": 1, "deux": 2, "trois": 3, "quatre": 4, "cinq": 5, "six": 6, "sept": 7, "huit": 8, "neuf": 9, "dix": 10,
        "onze": 11, "douze": 12, "treize": 13, "quatorze": 14, "quinze": 15, "seize": 16, "vingt": 20, "trente": 30,
        "quarante": 40, "cinquante": 50, "soixante": 60, "cent": 100, "mille": 1000}
UNIT = {"euros": " €", "euro": " €", "€": " €", "%": " %", "pourcent": " %", "heures": " h", "heure": " h", "h": " h",
        "minutes": " min", "min": " min", "ans": " ans", "jours": " jours", "km": " km", "clients": "", "clientes": ""}


def deac(s):
    s = unicodedata.normalize("NFD", s.lower().replace("œ", "oe"))
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def key(w):
    return deac(re.sub(r"[.,;:!?…«»\"()]", "", w))


def sentences(words):
    """Phrases (liste de mots horodatés) d'après la ponctuation forte."""
    res, cur = [], []
    for w in words:
        cur.append(w)
        if re.search(r"[.!?…]$", w["w"]):
            res.append(cur)
            cur = []
    return res + ([cur] if cur else [])


def punctuate(words, src):
    """Les sous-titres n'ont plus de ponctuation : on la reprend de la transcription (mêmes mots, même ordre)."""
    if not src.exists():
        return
    import difflib
    ref = read_json(src).get("words", [])
    a_, b_ = [key(w["w"]) for w in words], [key(w["w"]) for w in ref]
    for blk in difflib.SequenceMatcher(None, a_, b_, autojunk=False).get_matching_blocks():
        for k in range(blk.size):
            m = re.search(r"[.,;:!?…]+$", ref[blk.b + k]["w"])
            if m and not re.search(r"[.,;:!?…]$", words[blk.a + k]["w"]):
                words[blk.a + k]["w"] += m.group()


def anchor(words, w):
    """(mot, occurrence) pour poser un temps fort sur ce mot."""
    k = key(w["w"])
    n = sum(1 for x in words if x["start"] <= w["start"] and key(x["w"]) == k)
    return w["w"].strip(".,;:!?…«»\"()"), n


def text_of(ws):
    return " ".join(w["w"] for w in ws).strip()


def strong(ws):
    """Le mot fort : chiffre, sinon le mot plein le plus long."""
    cands = [i for i, w in enumerate(ws) if key(w["w"]) not in WEAK and len(key(w["w"])) > 2]
    for i in cands:
        if re.search(r"\d", ws[i]["w"]) or key(ws[i]["w"]) in NUMW and key(ws[i]["w"]) not in ("un", "une"):
            return i
    return max(cands, key=lambda i: len(key(ws[i]["w"]))) if cands else 0


LEAD = {"et", "mais", "donc", "alors", "puis", "euh", "bon", "bref"}


def lead_strip(ws):
    while len(ws) > 1 and key(ws[0]["w"]) in LEAD:
        ws = ws[1:]
    return ws


def accent(ws, max_words=7):
    ws = short(lead_strip(ws), max_words)
    j = strong(ws)
    t = [w["w"].strip(".…") for w in ws]
    t[-1] = t[-1].rstrip(",;:")
    t[0] = t[0][:1].upper() + t[0][1:]
    t[j] = f"*{t[j].strip(',;:!?')}*" + re.sub(r"^.*?([,;:!?]*)$", r"\1", t[j])
    return " ".join(t)


def icon_for(ws):
    for w in ws:
        k = key(w["w"])
        for root, ic in ICONS:
            if k.startswith(root):
                return ic
    return None


def query_for(ws):
    for w in ws:
        q = QUERIES.get(key(w["w"]).split("'")[-1])
        if q:
            return q
    return None


def number(ws):
    """Premier nombre dit : (valeur, suffixe, index du jeton, index du dernier jeton) ou None.
    « vingt-quatre », « 1 800 », « 60 € », et les jetons de plusieurs mots (« une heure, soixante euros »)."""
    flat = [(key(sw), ti) for ti, w in enumerate(ws) for sw in w["w"].split()]
    for i, (k, ti) in enumerate(flat):
        val = None
        if re.fullmatch(r"\d+([.,]\d+)?", k):
            val = float(k.replace(",", "."))
            if i + 1 < len(flat) and re.fullmatch(r"\d{3}", flat[i + 1][0]):
                val, i = val * 1000 + int(flat[i + 1][0]), i + 1
        elif k in ("un", "une") and i + 1 < len(flat) and UNIT.get(flat[i + 1][0], "").strip():
            val = 1
        elif k in NUMW and k not in ("un", "une") or "-" in k and all(p in NUMW or p == "et" for p in k.split("-")):
            val = sum(NUMW.get(p, 0) for p in k.split("-"))
        if val is None:
            continue
        nxt = flat[i + 1][0] if i + 1 < len(flat) else ""
        suf = UNIT.get(nxt, "")
        if not suf and nxt not in UNIT and len(flat) > 3 and val < 3:
            continue  # « deux fois », « 1 seul » : pas un chiffre à mettre en avant
        last = flat[i + 1][1] if suf and i + 1 < len(flat) else flat[i][1]
        return (int(val) if val == int(val) else val), suf, ti, last
    return None


def items_of(ws):
    """Énumération « A, B et C » (3 items courts) ou « pas de A ni de B » -> liste d'items, sinon None."""
    t = text_of(ws).rstrip(".!?…")
    parts = [p.strip() for p in re.split(r",\s*|\s+(?:et|ni|ou)\s+(?=\S)", t) if p.strip()]
    parts = [re.sub(r"(?i)^(et|ou|puis|mais)\s+", "", p_) for p_ in parts]
    neg = re.search(r"\b(pas de|pas d'|ni|sans)\b", t, re.I)
    if len(parts) >= 3 and all(len(p.split()) <= 4 for p in parts):
        return parts
    if neg and len(parts) >= 2 and all(len(p.split()) <= 5 for p in parts):
        return parts
    return None


def step_split(ws):
    """« D'abord A, puis B, et enfin C » dans une seule phrase -> [A, B, C] (au moins 2 marqueurs), sinon None."""
    idx = [i for i, w in enumerate(ws) if key(w["w"]).split("'")[0] in STEP or key(w["w"]) in STEP]
    if len(idx) < 2:
        return None
    res = []
    for a, b in zip(idx, idx[1:] + [len(ws)]):
        part = lead_strip([w for w in ws[a + 1:b]]) if b > a + 1 else []
        while part and key(part[-1]["w"]) in LEAD:
            part = part[:-1]
        if key(ws[a]["w"]).startswith("d'abord") and not part:
            continue
        if part:
            res.append(part)
    return res if len(res) >= 2 else None


def neg_item(it):
    """« ni de maquillage » / « de maquillage » -> « Pas de maquillage »."""
    it = re.sub(r"(?i)^ni\s+", "", it.strip())
    if re.match(r"(?i)(de\s|d')", it):
        it = "pas " + it
    return it[:1].upper() + it[1:]


def short(ws, n=6):
    """Texte court pour l'écran : jusqu'à la première virgule (si assez long), au plus n mots, sans petit mot final."""
    cut = next((i + 1 for i, w in enumerate(ws) if re.search(r"[,;:]$", w["w"]) and i >= 1), len(ws))
    ws = ws[:min(cut, n)]
    while len(ws) > 1 and key(ws[-1]["w"]) in WEAK:
        ws = ws[:-1]
    return ws


def split_long(ws, max_dur=5.5):
    """Une phrase trop longue (voix transcrite sans ponctuation) se coupe à sa plus longue pause."""
    if len(ws) < 6 or ws[-1]["end"] - ws[0]["start"] <= max_dur:
        return [ws]
    gaps = [(ws[i]["start"] - ws[i - 1]["end"], i) for i in range(2, len(ws) - 1)]
    g, i = max(gaps)
    if g < 0.45:
        return [ws]
    return split_long(ws[:i], max_dur) + split_long(ws[i:], max_dur)


CHAP = {"avant": "AVANT", "d'abord": "PENDANT", "pendant": "PENDANT", "apres": "APRÈS", "ensuite": "APRÈS",
        "enfin": "ENFIN", "pourquoi": "POURQUOI", "comment": "COMMENT", "resultat": "RÉSULTAT"}


def media_files(job):
    res = []
    for p in sorted((job / "inbox").glob("*")):
        if p.suffix.lower() in VIDEO | PHOTO:
            res.append(p)
    return res


def is_rush(p):
    """Vidéo avec du son de plus de 8 s : sans doute une prise de parole filmée."""
    try:
        info = probe(p)
    except SystemExit:
        return False
    return info["duration"] > 8 and info["has_audio"]


def choose(job_name, slug=None, demande=""):
    job = job_dir(job_name)
    brief = read_json(job / "work" / "brief.json") if (job / "work" / "brief.json").exists() else {}
    files = media_files(job)
    story = bool(slug) and (job / "work" / f"{slug}_storyboard.json").exists()  # voix off écrite : pas de rush
    rushes = [] if story else [p for p in files if p.suffix.lower() in VIDEO and is_rush(p)]
    said = ""
    if slug:
        for f in (f"{slug}_storyboard.json", f"{slug}_text.json"):
            p = job / "work" / f
            if p.exists():
                said += " " + Path(p).read_text(encoding="utf-8")
    txt = deac(" ".join([demande, " ".join(str(v) for v in brief.values()), said]))
    obj, ton = deac(str(brief.get("objectif", ""))), deac(str(brief.get("ton", "")))
    dur = re.search(r"\d+", str(brief.get("duree", "")))
    dur = int(dur.group()) if dur else None
    explain = len(re.findall(r"\b(comment|etape|d'abord|ensuite|enfin|conseil|astuce|pourquoi|deroule|tuto|guide|expliqu)", txt))
    announce = len(re.findall(r"\b(ouvert|nouveau|nouvelle|promo|offre|lancement|annonce|reduction|soldes|evenement|"
                              r"date|inscription|reserv|disponible|€|euros)", txt))
    if rushes:
        if "sobre" in ton or "haut de gamme" in ton:
            pack, why = "classique", "rush filmé et ton sobre / haut de gamme : sous-titres minimal, peu d'habillage"
        else:
            pack, why = "ecran-partage", (f"rush face caméra ({rushes[0].name}) : animation en haut, visage en bas, "
                                          "sous-titres sur la jointure")
    elif explain >= 2 or "inform" in obj or "conseil" in obj:
        pack, why = "explainer", "pas de rush et contenu qui explique (étapes, conseils) : fiche papier animée par chapitres"
    elif announce >= 2 or any(x in obj for x in ("vend", "remplir", "promo", "annonc")) or (dur and dur <= 20):
        pack, why = "punch", "pas de rush, annonce ou offre courte : images plein cadre coupées vite, gros titres, objets"
    else:
        pack, why = "classique", "pas de rush, message simple : scènes de marque (build_scenes.py)"
    if pack == "punch" and ("haut de gamme" in ton or "calme" in ton or "sobre" in ton):
        why += " ; ton calme : punch avec moins d'éclairs (coupe toutes les 2,5 à 3 s) ou explainer"
    cmds = {
        "ecran-partage": ["layout split (visual.layout ou --layout split)", "pack.py draft <job> <slug>", "panel.py fetch / pick",
                          "build_composition.py <job> <slug> --layout split"],
        "explainer": ["pack.py draft <job> <slug>", "panel.py fetch / pick", "build_explainer.py <job> <slug>"],
        "punch": ["pack.py draft <job> <slug>", "build_punch.py fetch / pick", "build_punch.py <job> <slug>"],
        "classique": ["parcours rush → reel ou sans rush (build_scenes.py)"],
    }[pack]
    out(ok=True, pack=pack, pourquoi=why, rushs=[p.name for p in rushes], medias=len(files), ensuite=cmds,
        autres=[p for p in ("ecran-partage", "explainer", "punch", "classique") if p != pack])


def _assign_media(beats, files, rush_names):
    """Médias du client d'abord : un par temps fort visuel, dans l'ordre, sans répéter."""
    pool = [p for p in files if p.name not in rush_names]
    for b in beats:
        if not pool:
            break
        if b.get("type") == "image" or "media" in b or b.get("_visual"):
            b.pop("query", None)
            b["image" if "type" in b else "media"] = pool.pop(0).name
    return beats


def draft_panels(sents, words, chapters):
    beats = []

    def add(b, ws):
        b["_k0"], b["_t"] = key(ws[0]["w"]), ws[0]["start"]
        beats.append(b)

    def clean(ws):
        t = text_of(short(lead_strip(ws), 5)).rstrip(".,;:!?…")
        return t[:1].upper() + t[1:]

    def plain(ws):
        w, n = anchor(words, ws[0])
        q = query_for(ws)
        k0 = key(ws[0]["w"])
        if k0 in CTA:
            add({"type": "title", "word": w, "occurrence": n, "text": accent(ws, 5), "icon": CTA[k0], "flash": True}, ws)
        elif q and not (beats and beats[-1]["type"] == "image"):
            add({"type": "image", "word": w, "occurrence": n, "query": q, "caption": clean(ws)}, ws)
        else:
            b = {"type": "title", "word": w, "occurrence": n, "text": accent(ws)}
            ic = icon_for(ws)
            if ic and len(beats) % 2 == 0:
                b["icon"] = ic
            if text_of(ws).endswith("?"):
                b["flash"] = True
            add(b, ws)

    run = []  # phrases qui commencent par d'abord / puis / enfin

    def flush():
        if len(run) >= 2:
            w, n = anchor(words, run[0][0])
            items = [lead_strip([x for x in s_ if key(x["w"]) not in STEP]) for s_ in run]
            add({"type": "steps", "word": w, "occurrence": n,
                 "items": [{"text": clean(it).capitalize(), "icon": icon_for(it) or "circle-check"} for it in items[:5]]}, run[0])
        else:
            for s_ in run:
                plain(s_)
        run.clear()

    for ws in sents:
        if len(ws) < 2:
            continue
        k0 = key(ws[0]["w"])
        steps = step_split(ws)
        rich = bool(steps or number(ws) or items_of(ws) or k0 in CTA or k0 in STEP or k0.startswith("d'abord"))
        if not rich and beats and not run and ws[0]["start"] - beats[-1]["_t"] < 1.8:
            continue  # un temps fort toutes les 1,8 s au plus
        if not rich and len(short(lead_strip(ws), 6)) < 3:
            continue  # « il permet » : rien à montrer
        if not steps and (k0 in STEP or k0.startswith("d'abord")):
            run.append(ws)
            continue
        flush()
        w, n = anchor(words, ws[0])
        num = number(ws)
        items = None if steps else items_of(ws)
        if steps:
            add({"type": "steps", "word": w, "occurrence": n,
                 "items": [{"text": clean(it).capitalize(), "icon": icon_for(it) or "circle-check"} for it in steps[:5]]}, ws)
        elif num:
            val, suf, i, last = num
            before = lead_strip(ws[:i]) if i else []
            label = clean(before) if len(before) >= 2 else text_of(short(ws[last + 1:], 5)).rstrip(".,;:!?…")
            b = {"type": "stat", "word": w, "occurrence": n, "value": val, "label": label}
            if suf.strip():
                b["suffix"] = suf
            add(b, ws)
        elif items:
            neg = bool(re.search(r"\b(pas|ni|sans)\b", text_of(ws), re.I))
            head = []
            if neg and not re.match(r"(?i)(pas|ni|sans)\b", items[0]):  # « Avant de venir, pas de A ni de B »
                head, items = [items[0]], items[1:]
            add({"type": "check", "word": w, "occurrence": n, "title": head[0] if head else "",
                 "items": [{"text": neg_item(it) if neg else it[:1].upper() + it[1:],
                            "icon": "ban" if neg and re.match(r"(?i)(pas|ni|sans|de\s|d')", it) else (icon_for([{"w": x} for x in it.split()]) or "circle-check")}
                           for it in items[:4]]}, ws)
        else:
            plain(ws)
    flush()
    if chapters and beats:
        cur = None
        for b in beats:
            cue = CHAP.get(b["_k0"]) or CHAP.get(b["_k0"].split("'")[0] + "'abord" if b["_k0"].startswith("d'") else "")
            if b["_k0"] in CTA:
                cue = "À VOUS"
            if cue:
                cur = cue
            b["chapter"] = cur or ""
        if not any(b["chapter"] for b in beats):  # aucun repère : 3 parties à renommer
            size = -(-len(beats) // 3)
            for g, b in enumerate(beats):
                b["chapter"] = f"PARTIE {g // size + 1}"
        first = next((b["chapter"] for b in beats if b["chapter"]), "")
        for b in beats:
            if not b["chapter"]:
                b["chapter"] = "INTRO" if first else ""
            if b["chapter"] == "INTRO" and b is beats[0]:
                b.pop("chapter")  # l'accroche n'a pas de chapitre
    for b in beats:
        b.pop("_k0", None)
        b.pop("_t", None)
    return beats


def punch_lines(ws):
    """Titre punch : 1 à 3 lignes de 1 à 3 mots, coupées comme les sous-titres, sans connecteur en tête."""
    from build_text import _split_clause
    core = short(lead_strip(ws), 8)
    groups = _split_clause(core, 2) if len(core) > 2 else [core]
    while len(groups) > 3 or (len(groups) > 1 and key(groups[-1][-1]["w"]) in WEAK):
        groups = groups[:-1]
    j = strong([x for g in groups for x in g])
    hi = [x for g in groups for x in g][j]["w"]
    return [" ".join((f"*{x['w'].strip('.,;:!?…').upper()}*" if x["w"] == hi else x["w"].strip(".,;:!?…").upper())
                     for x in g) for g in groups]


def draft_punch(sents, words):
    beats = []
    for s_ in sents:
        # une coupe toutes les 1,5 à 3 s : une phrase longue se coupe à la virgule
        parts, cur = [], []
        for w in s_:
            cur.append(w)
            if re.search(r"[,;:]$", w["w"]) and cur[-1]["end"] - cur[0]["start"] > 0.9:
                parts.append(cur)
                cur = []
        if cur:
            parts.append(cur) if not parts or cur[-1]["end"] - cur[0]["start"] > 0.9 else parts[-1].extend(cur)
        for ws in parts:
            w, n = anchor(words, ws[0])
            b = {"word": w, "occurrence": n, "_visual": True, "query": query_for(ws) or "TODO", "title": punch_lines(ws)}
            num, k0 = number(ws), key(ws[0]["w"])
            if num:
                val, suf, i, last = num
                ww, nn = anchor(words, ws[i])
                b["prop"] = ({"type": "price", "word": ww, "occurrence": nn, "value": f"{val}{suf}", "sub": ""} if "€" in suf
                             else {"type": "stat", "word": ww, "occurrence": nn, "value": str(val), "unit": suf.strip(), "label": ""})
            elif k0 in CTA:
                b["prop"] = {"type": "icon", "icon": CTA[k0],
                             "label": "LIEN EN BIO" if re.search(r"\bbio\b", deac(text_of(ws))) else "TODO : où / comment"}
            elif re.search(r"\b(lundi|mardi|mercredi|jeudi|vendredi|samedi|dimanche)\b", deac(text_of(ws))):
                b["prop"] = {"type": "tag", "text": "TODO : jours / horaires réels"}
            beats.append(b)
    return beats


def draft(job_name, slug, pack="auto"):
    job = job_dir(job_name)
    tj = job / "work" / f"{slug}_text.json"
    if not tj.exists():
        fail(f"{tj.name} manquant : voice.py (ou build_cut.py) puis build_text.py d'abord")
    t = read_json(tj)
    words = [dict(w) for c in t.get("captions", []) for w in c.get("words", [])]
    if not words:
        fail("aucun mot dans text.json")
    punctuate(words, job / "work" / f"{slug}_words.json")
    if pack == "auto":
        import io
        import contextlib
        import json
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            choose(job_name, slug)
        pack = json.loads(buf.getvalue())["pack"]
        if pack == "classique":
            fail("pack conseillé : classique (pas de temps forts à écrire) ; force --pack si tu veux quand même un pack")
    sents = [p for s_ in sentences(words) for p in split_long(s_)]
    files = media_files(job)
    story = (job / "work" / f"{slug}_storyboard.json").exists()
    rush_names = set() if story else {p.name for p in files if p.suffix.lower() in VIDEO and is_rush(p)}
    if pack == "punch":
        beats = _assign_media(draft_punch(sents, words), files, rush_names)
        for b in beats:
            b.pop("_visual", None)
        name = f"{slug}_punch"
    else:
        beats = _assign_media(draft_panels(sents, words, chapters=(pack == "explainer")), files, rush_names)
        name = f"{slug}_panels"
    dst = job / "work" / f"{name}.json"
    if dst.exists():
        dst = job / "work" / f"{name}_draft.json"
    write_json(dst, beats)
    todo = sum(1 for b in beats if "TODO" in str(b))
    kinds = {}
    for b in beats:
        kinds[b.get("type", "plan")] = kinds.get(b.get("type", "plan"), 0) + 1
    out(ok=True, pack=pack, fichier=str(dst), temps_forts=len(beats), types=kinds, a_completer=todo,
        suite="relis chaque temps fort (textes courts, vrais chiffres, chapitres, requêtes anglaises), remplace les TODO, "
              "puis fetch / pick et build")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["choose", "draft"])
    ap.add_argument("job")
    ap.add_argument("slug", nargs="?")
    ap.add_argument("--slug", dest="slug_opt")
    ap.add_argument("--demande", default="")
    ap.add_argument("--pack", default="auto", choices=["auto", "ecran-partage", "explainer", "punch"])
    a = ap.parse_args()
    slug = a.slug or a.slug_opt
    if a.cmd == "choose":
        choose(a.job, slug, a.demande)
    else:
        if not slug:
            fail("draft : donne le slug")
        draft(a.job, slug, a.pack)


if __name__ == "__main__":
    main()

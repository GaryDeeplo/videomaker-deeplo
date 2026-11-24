"""CHOIX DU PACK et PREMIER JET des temps forts, à partir de la demande, du brief et de ce qui est dit.

  python pack.py choose <job> [--slug s] [--demande "texte de la demande"]
      -> pack conseillé (ecran-partage | explainer | punch | infographie | montage | classique) + pourquoi + commandes à lancer
  python pack.py draft <job> <slug> [--pack auto|ecran-partage|explainer|punch|infographie]
      -> work/<slug>_panels.json (écran partagé, explainer) ou work/<slug>_punch.json (punch), posés sur les mots dits.
         Si le fichier existe déjà : work/<slug>_panels_draft.json / <slug>_punch_draft.json (rien n'est écrasé).

Le premier jet lit les phrases de text.json (donc après voice.py / build_text.py) : chiffre -> stat (ou prix),
énumération -> check / steps avec pictos, « pas de / ni » -> picto interdit, d'abord / puis / enfin -> étapes,
appel à l'action -> titre + picto, nom concret connu -> image ("query" anglais), sinon titre avec *mot fort*.
Maquettes quand la phrase en parle : réserver / commander / devis -> formulaire, Google -> recherche, classement ->
classement, messages -> chat, analyse / audit -> progression, site -> navigateur, parcours / clients perdus -> entonnoir,
« en direct » / commandes qui arrivent -> flux, identité visuelle / logo -> nuancier, GitHub / dépôt -> carte de dépôt,
code -> code avant / après, « le plus simple » -> lignes emmêlées ; un outil nommé (Claude, Notion…) -> son vrai logo, liste de 4 outils et plus -> étoile
d'icônes ; « numéro 3 », « le deuxième conseil » -> en-tête de liste « 3 SUR 5 ». Infographie : work/<slug>_data.json
(plusieurs % -> pourcentages, « passe de X à Y » -> courbe, plusieurs nombres -> barres, grand nombre -> compteur,
« N fois » -> ×N, « N jours d'essai » -> cases, lien final -> carte de fin).
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


TOOLS = {"claude": "claude", "anthropic": "anthropic", "chatgpt": "openai", "openai": "openai", "gemini": "googlegemini",
         "notion": "notion", "slack": "slack", "gmail": "gmail", "github": "github", "figma": "figma", "canva": "canva",
         "instagram": "instagram", "tiktok": "tiktok", "youtube": "youtube", "whatsapp": "whatsapp", "linkedin": "linkedin",
         "google": "google", "shopify": "shopify", "wordpress": "wordpress", "stripe": "stripe", "zapier": "zapier", "make": "make",
         "perplexity": "perplexity", "vercel": "vercel", "airtable": "airtable", "hubspot": "hubspot", "trello": "trello",
         "asana": "asana", "discord": "discord", "telegram": "telegram", "pixabay": "pixabay", "firecrawl": "", "posthog": "posthog",
         "playwright": "", "supabase": "supabase", "cursor": "cursor", "n8n": "n8n", "calendly": "calendly", "mailchimp": "mailchimp"}


def icon_for(ws):
    for w in ws:  # un outil nommé -> son vrai logo
        t = TOOLS.get(key(w["w"]).split("'")[-1])
        if t:
            return f"logo:{t}"
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


def _numword(k):
    """« soixante-quatre » -> 64, « quatre-vingt-dix » -> 90, « cents » -> 100 ; None si ce n'est pas un nombre en lettres."""
    k = k.replace("quatre-vingts", "quatre-vingt").replace("quatre-vingt", "octante")
    parts = [x for x in k.split("-") if x != "et"]
    if not parts or not all(x.rstrip("s") in NUMW or x == "octante" for x in parts):
        return None
    return sum(80 if x == "octante" else NUMW[x.rstrip("s")] for x in parts)


def number(ws):
    """Premier nombre dit : (valeur, suffixe, index du jeton, index du dernier jeton) ou None.
    Chiffres (« 1 800 », « 60 € »), lettres (« mille huit cents », « soixante-quatre pour cent »), jetons de plusieurs
    mots (« une heure, soixante euros »)."""
    flat = [(key(sw), ti) for ti, w in enumerate(ws) for sw in w["w"].split()]
    stops = {j for j, (_, ti) in enumerate(flat) if ws[ti]["w"].rstrip()[-1:] in ",.;:!?…" and flat[min(j + 1, len(flat) - 1)][1] != ti}
    i = 0
    while i < len(flat):
        k, ti = flat[i]
        val, j = None, i
        if re.fullmatch(r"\d+([.,]\d+)?", k):
            val = float(k.replace(",", "."))
            while j + 1 < len(flat) and re.fullmatch(r"\d{3}", flat[j + 1][0]):
                val, j = val * 1000 + int(flat[j + 1][0]), j + 1
        elif k in ("un", "une"):
            if i + 1 < len(flat) and UNIT.get(flat[i + 1][0], "").strip():
                val = 1
        elif _numword(k) is not None:
            total, cur = 0, 0
            while j < len(flat):
                kk = flat[j][0]
                if kk == "et" and j + 1 < len(flat) and _numword(flat[j + 1][0]) is not None:
                    j += 1
                    continue
                v = _numword(kk)
                if v is None:
                    break
                if j in stops:  # « Numéro deux, un dépôt » : la virgule arrête le nombre
                    j += 1
                    if v == 100:
                        cur = (cur or 1) * 100
                    elif v == 1000:
                        total, cur = total + (cur or 1) * 1000, 0
                    else:
                        cur += v
                    break
                if v == 100:
                    cur = (cur or 1) * 100
                elif v == 1000:
                    total, cur = total + (cur or 1) * 1000, 0
                else:
                    cur += v
                j += 1
            j -= 1
            val = total + cur
        if val is None:
            i += 1
            continue
        nxt = flat[j + 1][0] if j + 1 < len(flat) else ""
        nxt2 = flat[j + 2][0] if j + 2 < len(flat) else ""
        if nxt == "pour" and nxt2 in ("cent", "cents"):
            suf, last = " %", flat[j + 2][1]
        else:
            suf = UNIT.get(nxt, "")
            last = flat[j + 1][1] if suf and j + 1 < len(flat) else flat[j][1]
        if not suf and nxt not in UNIT and len(flat) > 3 and val < 3:
            i = j + 1
            continue  # « deux fois », « 1 seul » : pas un chiffre à mettre en avant
        return (int(val) if val == int(val) else val), suf, ti, last
    return None


def items_of(ws):
    """Énumération « A, B et C » (3 items courts) ou « pas de A ni de B » -> liste d'items, sinon None."""
    t = text_of(ws).rstrip(".!?…")
    parts = [p.strip() for p in re.split(r",\s*|\s+(?:et|ni|ou)\s+(?=\S)", t) if p.strip()]
    parts = [re.sub(r"(?i)^(et|ou|puis|mais)\s+", "", p_) for p_ in parts]
    neg = re.search(r"\b(pas de|pas d'|ni|sans)\b", t, re.I)
    if len(parts) >= 4 and len(parts[0].split()) > 4 and all(len(p.split()) <= 4 for p in parts[1:]):
        parts[0] = parts[0].split()[-1]  # « On le connecte à Notion, Gmail, Slack et Figma » -> Notion, Gmail, Slack, Figma
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


# idée dite -> maquette d'interface (une de chaque au plus par vidéo)
UI_WORDS = [
    ("rank", r"\b(classement|premiere? place|en tete des|devant (vos|tes|les) concurrents|premiers? sur google)"),
    ("search", r"\b(google|moteur de recherche|recherchent|cherchent|tapent)\b"),
    ("form", r"\b(reserv\w*|command\w*|devis|inscri\w*|formulaire|prendre rendez-vous|prenez rendez-vous)\b"),
    ("chat", r"\b(messages?|whatsapp|ecrivez|ecris|repond\w*|messenger)\b"),
    ("progress", r"\b(analyse\w*|audit\w*|scanne\w*|passe en revue)\b"),
    ("browser", r"\b(votre site|ton site|site web|site internet|page d'accueil)\b"),
    ("funnel", r"\b(parcours|abandonn\w*|perd\w* (des|vos|tes) clients|partent avant)"),
    ("feed", r"\b(en direct|commandes? qui (arrive|tombe)\w*|notifications?)\b"),
    ("palette", r"\b(identite visuelle|charte graphique|vos couleurs|ton logo|votre logo)\b"),
    ("repo", r"\b(github|depot|repo|open source|etoiles)\b"),
    ("code", r"\b(lignes de code|ton code|votre code|refactor\w*|du code)\b"),
    ("paths", r"\b(le plus simple|la plus simple|plus simple que)\b"),
    ("settings", r"\b(reglages|parametres|instructions personnalisees|prompt systeme|colle\w* (cette|la) (ligne|phrase|consigne))\b"),
    ("post", r"\b(tweet\w*|a poste|a publie|sur x|sur linkedin)\b"),
    ("loupe", r"\b(petites lignes|en tout petit|personne ne lit|cache\w* dans)\b"),
]
FORM = [("reserv", "Réservation", "Créneau", "Réserver", "Réservé"), ("command", "Commande", "Produit", "Commander", "Commandé"),
        ("devis", "Demande de devis", "Projet", "Envoyer", "Envoyé"), ("inscri", "Inscription", "E-mail", "S'inscrire", "Inscrit"),
        ("", "Prise de rendez-vous", "Créneau", "Envoyer", "Envoyé")]
ORD = {"premier": 1, "premiere": 1, "deuxieme": 2, "second": 2, "seconde": 2, "troisieme": 3, "quatrieme": 4, "cinquieme": 5,
       "sixieme": 6, "septieme": 7, "huitieme": 8, "neuvieme": 9, "dixieme": 10}
LIST_NOUNS = {"conseil", "astuce", "erreur", "outil", "etape", "raison", "secret", "regle", "point", "idee", "piege", "signe",
              "question", "avantage", "bonus", "methode", "habitude", "connecteur", "plugin", "skill", "application", "appli"}


def ordinal(ws):
    """« Numéro 3, PostHog », « Le deuxième conseil : … », « Erreur numéro 2 » (en tête de phrase) -> (n, nom) ou None."""
    ks = [key(w["w"]) for w in ws[:6]]
    for i, k in enumerate(ks):
        n = None
        if k in ("numero", "n°", "no") and i + 1 < len(ks):
            nk = ks[i + 1]
            n = int(nk) if nk.isdigit() else (NUMW.get(nk) or ORD.get(nk))
            rest = ws[i + 2:]
        elif k in ORD and i + 1 < len(ks) and ks[i + 1].rstrip("s") in LIST_NOUNS:
            n, rest = ORD[k], ws[i + 2:]
        if n:
            name = phrase(rest, 4) if rest else ""
            noun = next((x for x in ks[:i + 2] if x.rstrip("s") in LIST_NOUNS), "")
            return n, (name[:1].upper() + name[1:]) if name else f"{noun.capitalize()} {n}".strip()
        if i >= 3:
            break
    return None


def numbers(ws):
    """Tous les nombres dits : [(valeur, suffixe, index du jeton, dernier jeton)]."""
    res, pos = [], 0
    while pos < len(ws):
        n = number(ws[pos:])
        if not n:
            break
        v, suf, i, last = n
        res.append((v, suf, pos + i, pos + last))
        pos += last + 1
    for j in range(len(res) - 2, -1, -1):  # « 1 800 et 3 150 euros » : l'unité vaut pour les deux
        between = [key(w["w"]) for w in ws[res[j][3] + 1:res[j + 1][2]]]
        if not res[j][1] and res[j + 1][1] and all(x in ("et", "a", "ou", "-") for x in between):
            res[j] = (res[j][0], res[j + 1][1], res[j][2], res[j][3])
    return res


def phrase(ws, n=4):
    """Libellé court : jusqu'à la première ponctuation, au plus n mots, sans petit mot ni connecteur aux bords."""
    out_ = []
    for w in lead_strip(ws) if ws else []:
        out_.append(w)
        if re.search(r"[,.;:!?…]$", w["w"]) or len(out_) >= n:
            break
    while len(out_) > 1 and key(out_[-1]["w"]) in WEAK:
        out_ = out_[:-1]
    return text_of(out_).strip(" ,.:;!?…")


def fmt_num(v):
    return f"{v:,}".replace(",", "\u202f") if isinstance(v, int) else str(v).replace(".", ",")


def media_files(job):
    res = []
    for p in sorted((job / "inbox").glob("*")):
        if p.suffix.lower() in VIDEO | PHOTO:
            res.append(p)
    return res


def is_rush(p):
    """Prise de parole filmée : plus de 8 s et quelqu'un parle (détecteur de voix ; le bruit d'un chantier ne compte pas)."""
    try:
        info = probe(p)
    except SystemExit:
        return False
    if info["duration"] <= 8 or not info["has_audio"]:
        return False
    from footage import speech_ratio
    r = speech_ratio(p, info["duration"])
    return True if r is None else r > 0.25


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
    silent = [] if (story or rushes) else [p for p in files if p.suffix.lower() in VIDEO]
    if len(silent) >= 2:
        pack, why = "montage", (f"{len(silent)} vidéos sans paroles (chantier, ambiance, plats, événement) : meilleurs passages "
                                "mesurés, accélérés, étiquettes, avant / après, musique ou voix off")
    elif rushes:
        if "sobre" in ton or "haut de gamme" in ton:
            pack, why = "classique", "rush filmé et ton sobre / haut de gamme : sous-titres minimal, peu d'habillage"
        else:
            pack, why = "ecran-partage", (f"rush face caméra ({rushes[0].name}) : animation en haut, visage en bas, "
                                          "sous-titres sur la jointure")
    elif len(re.findall(r"\b\d[\d\s.,]*\s*(?:%|€|euros|vues|clients|ventes|jours|ans)|\bpour ?cent\b", txt)) >= 3:
        pack, why = "infographie", "pas de rush et un propos porté par des chiffres : graphiques façon journal de données"
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
        "montage": ["footage.py scan <job>", "footage.py plan <job> <slug>", "build_footage.py <job> <slug>"],
        "infographie": ["work/<slug>_data.json (un graphique par chiffre dit, voir build_data.py)", "build_data.py <job> <slug>"],
        "punch": ["pack.py draft <job> <slug>", "build_punch.py fetch / pick", "build_punch.py <job> <slug>"],
        "classique": ["parcours rush → reel ou sans rush (build_scenes.py)"],
    }[pack]
    out(ok=True, pack=pack, pourquoi=why, rushs=[p.name for p in rushes], medias=len(files), ensuite=cmds,
        autres=[p for p in ("ecran-partage", "explainer", "punch", "infographie", "montage", "classique") if p != pack])


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


def draft_panels(sents, words, chapters, brand=None):
    beats = []
    brand = brand or {}
    bname = brand.get("name") or "Vous"
    site = (brand.get("contact") or {}).get("site") or "TODO-site.be"
    used = set()
    ords = {}  # index de phrase -> (n, nom)

    def ui(ws):
        """Une maquette d'interface si la phrase en parle (une de chaque au plus), sinon None."""
        t = deac(text_of(ws))
        if ws[-1]["end"] - ws[0]["start"] < 1.6:
            return None
        w, n = anchor(words, ws[0])
        if ordinal(ws):  # « Erreur numéro trois, vous ne répondez pas » : le propos est après la virgule
            cut = next((i + 1 for i, x in enumerate(ws) if re.search(r"[,:]$", x["w"])), 0)
            ws = ws[cut:] or ws
        for typ, rx in UI_WORDS:
            if typ in used or not re.search(rx, t):
                continue
            used.add(typ)
            if typ == "form":
                k, title, f2, btn, done = next(f for f in FORM if f[0] in t)
                return {"type": "form", "word": w, "occurrence": n, "url": site, "title": title,
                        "fields": [{"label": "Prénom", "value": "Camille"}, {"label": f2, "value": "TODO"}], "button": btn, "done": done}
            if typ == "search":
                return {"type": "search", "word": w, "occurrence": n, "query": "TODO : ce que tape le client",
                        "results": ["Concurrent A", "Concurrent B", bname], "highlight": 2}
            if typ == "rank":
                return {"type": "rank", "word": w, "occurrence": n, "title": "Google · TODO",
                        "items": [{"text": "Concurrent A"}, {"text": "Concurrent B"}, {"text": bname}], "highlight": 2, "to": 0}
            if typ == "chat":
                return {"type": "chat", "word": w, "occurrence": n, "title": "Messages",
                        "messages": [{"from": "them", "text": "TODO : question du client"}, {"from": "me", "text": clean(ws)}]}
            if typ == "progress":
                return {"type": "progress", "word": w, "occurrence": n, "label": "TODO : ce qui est analysé", "to": 100, "unit": "%",
                        "done": clean(short(ws, 4)) or "Terminé"}
            if typ == "funnel":
                return {"type": "funnel", "word": w, "occurrence": n, "title": "Parcours client",
                        "steps": [{"label": "Accueil", "value": 100}, {"label": "Offre", "value": 70}, {"label": "Formulaire", "value": 25},
                                  {"label": "Paiement", "value": 12}], "leak": 2, "note": "TODO : où ils partent (chiffres réels ou dits comme exemple)"}
            if typ == "feed":
                return {"type": "feed", "word": w, "occurrence": n, "title": "TODO", "badge": "EN DIRECT",
                        "items": [{"text": "TODO", "sub": "il y a 1 min", "icon": icon_for(ws) or "bell"}]}
            if typ == "palette":
                return {"type": "palette", "word": w, "occurrence": n, "title": "La marque"}
            if typ == "repo":
                return {"type": "repo", "word": w, "occurrence": n, "name": "TODO : owner/repo", "badge": "Gratuit"}
            if typ == "code":
                return {"type": "code", "word": w, "occurrence": n, "file": "TODO", "before": ["TODO"], "after": ["TODO"]}
            if typ == "paths":
                return {"type": "paths", "word": w, "occurrence": n, "count": 6, "label": "Le plus simple", "start": "TODO"}
            if typ == "settings":
                return {"type": "settings", "word": w, "occurrence": n, "app": "TODO", "title": "Instructions personnalisées",
                        "text": "TODO : la consigne exacte", "action": "save"}
            if typ == "post":
                return {"type": "post", "word": w, "occurrence": n, "platform": "x", "name": "TODO", "handle": "TODO",
                        "text": "TODO : texte exact de la publication (source réelle)", "date": "TODO"}
            if typ == "loupe":
                return {"type": "loupe", "word": w, "occurrence": n, "title": "TODO", "find": clean(short(ws, 4)) or "TODO", "label": "TODO"}
            return {"type": "browser", "word": w, "occurrence": n, "url": site,
                    "site": {"title": brand.get("tagline") or bname, "sub": "", "button": "TODO", "tiles": []}, "notes": []}
        return None

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
        m = ui(ws)
        if m:
            add(m, ws)
        elif k0 in CTA:
            add({"type": "title", "word": w, "occurrence": n, "text": accent(ws, 5), "icon": CTA[k0], "flash": True}, ws)
        elif q and not (beats and beats[-1]["type"] == "image"):
            add({"type": "image", "word": w, "occurrence": n, "query": q, "caption": clean(ws)}, ws)
        else:
            b = {"type": "title", "word": w, "occurrence": n, "text": accent(ws)}
            ic = icon_for(ws)
            if ic and (len(beats) % 2 == 0 or ic.startswith("logo:")):  # un outil cité garde toujours son logo
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
        o = ordinal(ws)
        if o:
            ords[ws[0]["start"]] = o
        steps = step_split(ws)
        rich = bool(o or steps or number(ws) or items_of(ws) or k0 in CTA or k0 in STEP or k0.startswith("d'abord"))
        if not rich and beats and not run and ws[0]["start"] - beats[-1]["_t"] < 1.8:
            continue  # un temps fort toutes les 1,8 s au plus
        if not rich and len(short(lead_strip(ws), 6)) < 3:
            continue  # « il permet » : rien à montrer
        if not steps and (k0 in STEP or k0.startswith("d'abord")):
            run.append(ws)
            continue
        flush()
        w, n = anchor(words, ws[0])
        body = ws
        if o:
            cut = next((i + 1 for i, x in enumerate(ws) if re.search(r"[,:]$", x["w"])), 0)
            body = ws[cut:] or ws
            m = ui(ws)
            if m:  # l'élément de la liste montre ce dont il parle (dépôt, code, site…)
                add(m, ws)
                continue
        num = number(body)
        items = None if steps or o else items_of(body)
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
        elif items and len(items) >= 4 and not re.search(r"\b(pas|ni|sans)\b", text_of(ws), re.I) and "hub" not in used:
            used.add("hub")
            inames = {key(x) for it in items for x in it.split()}
            c = ({"image": brand["_logo"]} if brand.get("_logo")
                 else {"icon": icon_for([x for x in ws if key(x["w"]) not in inames]) or "sparkles"})  # pas un des outils autour
            add({"type": "hub", "word": w, "occurrence": n, "center": c,
                 "items": [{"icon": icon_for([{"w": x} for x in it.split()]) or "circle-check",
                            "label": " ".join(it.split()[-2:])[:1].upper() + " ".join(it.split()[-2:])[1:]} for it in items[:8]]}, ws)
        elif items:
            neg = bool(re.search(r"\b(pas|ni|sans)\b", text_of(ws), re.I))
            head = []
            if neg and not re.match(r"(?i)(pas|ni|sans)\b", items[0]):  # « Avant de venir, pas de A ni de B »
                head, items = [items[0]], items[1:]
            add({"type": "check", "word": w, "occurrence": n, "title": head[0] if head else "",
                 "items": [{"text": neg_item(it) if neg else it[:1].upper() + it[1:],
                            "icon": "ban" if neg and re.match(r"(?i)(pas|ni|sans|de\s|d')", it) else (icon_for([{"w": x} for x in it.split()]) or "circle-check")}
                           for it in items[:4]]}, ws)
        elif o:  # « Numéro 1, Perplexity, pour chercher… » : le titre vient du propos, posé sur « Numéro »
            add({"type": "title", "word": w, "occurrence": n, "text": accent(body), **({"icon": icon_for(body)} if icon_for(body) else {})}, ws)
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
    if len(ords) >= 2:  # format liste : en-tête « 2 SUR 5 » du n-ième élément jusqu'au suivant (pas sur l'appel final)
        total = max(n for n, _ in ords.values())
        cur = None
        for b in beats:
            hit = next((v for t, v in ords.items() if abs(t - b["_t"]) < 0.05), None)
            if hit:
                cur = {"n": hit[0], "of": total, "name": hit[1], "icon": icon_for([{"w": x} for x in hit[1].split()]) or "sparkles"}
            if b["_k0"] in CTA or b.get("type") == "form" and b is beats[-1]:
                cur = None
            if cur:
                b["list"] = dict(cur)
    for b in beats:
        b.pop("_k0", None)
        b.pop("_t", None)
    return beats


def draft_data(sents, words, brand=None):
    """Premier jet de l'infographie : un graphique par chiffre dit (barres, pourcentages, courbe, compteur, ×N, jours)."""
    brand = brand or {}
    beats, days = [], 0
    last_t = -9.0
    for ws in sents:
        if len(ws) < 2:
            continue
        t = deac(text_of(ws))
        w, n = anchor(words, ws[0])
        nums = numbers(ws)
        k0 = key(lead_strip(ws)[0]["w"])
        day = None
        for rx in (r"\b(\w+) jour\b", r"\bjour (\d+)\b", r"\bau bout de (\S+) jours\b"):
            for g in re.findall(rx, t):
                day = int(g) if g.isdigit() else (ORD.get(g) or _numword(g))
                if day:
                    break
            if day:
                days = max(days, day)
                break
        head = text_of(short(lead_strip(ws), 4)).strip(" ,.:;!?…").upper()

        def label(a, b_):
            return phrase(ws[a:b_], 4) or "TODO"
        b = None
        if nums:  # on compare des nombres de même unité (pas « 1 800 vues » et « 12 jours »)
            nums = [x for x in nums if x[1] == nums[0][1]]
        pct = [x for x in nums if "%" in x[1]]
        if len(pct) >= 2:
            b = {"type": "pct", "items": [{"label": label((pct[j - 1][3] + 1) if j else 0, x[2]), "value": x[0]} for j, x in enumerate(pct[:5])],
                 "highlight": max(range(len(pct[:5])), key=lambda j: pct[j][0])}
        elif len(nums) >= 2 and re.search(r"\b(passe|passent|monte|montent|grimpe|augmente|progresse|double|triple|de \S+ a)\b", t):
            a_, z = nums[0], nums[-1]
            b = {"type": "line", "steps": True, "points": [a_[0], z[0]], "label": f"{fmt_num(z[0])}{z[1]}".strip()}
        elif len(nums) >= 2:
            b = {"type": "bars", "unit": nums[0][1].strip(),
                 "items": [{"label": label(x[3] + 1, (nums[j + 1][2] if j + 1 < len(nums) else len(ws))), "value": x[0]} for j, x in enumerate(nums[:5])],
                 "highlight": max(range(len(nums[:5])), key=lambda j: nums[j][0])}
        elif nums:
            v, suf, i, last = nums[0]
            rest = phrase(ws[last + 1:], 4)
            if "%" in suf:
                b = {"type": "pct", "items": [{"label": label(0, i), "value": v}], "highlight": 0}
            elif re.search(r"\b(fois|x)\b", t) and isinstance(v, int) and v <= 15:
                b = {"type": "grid", "value": f"×{v}", "sub": rest[:20], "count": v, "icon": icon_for(ws) or "sparkles"}
            elif "jour" in suf and isinstance(v, int) and v <= 7 and re.search(r"\b(gratuit|essa[iy]|offert)", t):
                b = {"type": "days", "count": v, "stamp": f"{v} jours " + ("d'essai gratuit" if re.search(r"essa[iy]", t) else "offerts")}
            elif isinstance(v, (int, float)) and v >= 100:
                b = {"type": "flip", "to": int(v), "label": (suf.strip() + " " + rest).strip()}
            else:
                b = {"type": "title", "text": accent(ws)}
        elif k0 in CTA or re.search(r"\b(lien|bio|site)\b", t) and ws is sents[-1]:
            b = {"type": "end", "name": brand.get("name") or "TODO", "sub": "Le lien :", "url": (brand.get("contact") or {}).get("site") or "TODO",
                 "logo": bool(brand.get("_logo"))}
        elif ws[0]["start"] - last_t >= 2.2 and len(short(lead_strip(ws), 6)) >= 3:
            b = {"type": "title", "text": accent(ws)}
        if not b:
            continue
        b = {"word": w, "occurrence": n, **({"head": head} if b["type"] not in ("title", "end") else {}),
             **({"day": day} if day else {}), **b}
        beats.append(b)
        last_t = ws[0]["start"]
    if beats and "head" not in beats[0]:
        beats[0]["head"] = text_of(short(lead_strip(sents[0]), 4)).strip(" ,.:;!?…").upper()
    data = {"beats": beats}
    if days >= 2:
        data["days"] = {"count": days, "label": "TODO : ce que comptent les jours", "word": "Jour"}
    return data


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
        if pack in ("classique", "montage"):
            fail(f"pack conseillé : {pack} (pas de brouillon automatique : écris les temps forts toi-même) ; force --pack si tu veux quand même un pack")
    sents = [p for s_ in sentences(words) for p in split_long(s_)]
    files = media_files(job)
    story = (job / "work" / f"{slug}_storyboard.json").exists()
    rush_names = set() if story else {p.name for p in files if p.suffix.lower() in VIDEO and is_rush(p)}
    from common import brand_info, config
    brand = dict(brand_info(job))
    logo = config(job)["visual"].get("logo")
    if logo:
        brand["_logo"] = logo
    if pack == "infographie":
        data = draft_data(sents, words, brand)
        dst = job / "work" / f"{slug}_data.json"
        if dst.exists():
            dst = job / "work" / f"{slug}_data_draft.json"
        write_json(dst, data)
        kinds = {}
        for b in data["beats"]:
            kinds[b["type"]] = kinds.get(b["type"], 0) + 1
        return out(ok=True, pack=pack, fichier=str(dst), temps_forts=len(data["beats"]), types=kinds,
                   a_completer=sum(1 for b in data["beats"] if "TODO" in str(b)) + ("TODO" in str(data.get("days", ""))),
                   suite="relis : vrais chiffres seulement, libellés courts, rubriques (head), jours ; puis build_data.py")
    if pack == "punch":
        beats = _assign_media(draft_punch(sents, words), files, rush_names)
        for b in beats:
            b.pop("_visual", None)
        name = f"{slug}_punch"
    else:
        beats = _assign_media(draft_panels(sents, words, chapters=(pack == "explainer"), brand=brand), files, rush_names)
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
    ap.add_argument("--pack", default="auto", choices=["auto", "ecran-partage", "explainer", "punch", "infographie"])
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

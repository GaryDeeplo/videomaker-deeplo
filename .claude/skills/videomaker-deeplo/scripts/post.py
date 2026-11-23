"""TEXTE DU POST + DATE DE PUBLICATION, à partir de ce qui est DIT dans la vidéo, du brief et de la marque.

  python post.py draft <job> <slug>        # matière + premier jet -> work/<slug>_post_draft.json (Claude réécrit -> _post.json)
  python post.py check <job> <slug>        # relit work/<slug>_post.json : longueur, hashtags, mentions, « à éviter », chiffres
  python post.py date <job> <slug> [--reseau instagram] [--apres 2026-11-25]
                                           # propose le prochain créneau libre de la marque -> "date" dans _post.json
                                           #   + renders/publication.ics (rappel à importer dans l'agenda)

draft rassemble : l'accroche, les phrases fortes (punchs, chiffres), l'appel à l'action du brief, les mentions
obligatoires, le ton de la marque, des hashtags (marque, ville, métier, sujets dits) ; il assemble un premier jet que
TU réécris dans le ton de la marque (2-3 phrases, première ligne qui donne envie de lire la suite, ≤ 125 caractères,
rien d'inventé). check refuse un chiffre absent de la vidéo, du brief et de la charte (« à vérifier »).
date : jours et heure de la marque (brand.json "publication": {"jours": ["mar", "jeu"], "heure": "18:30"}), sinon
repères génériques par réseau ; saute les jours déjà pris par une autre vidéo de la même marque. Rien n'est publié.
"""
import argparse
import datetime as dt
import re
from collections import Counter
from pathlib import Path

from common import ROOT, fail, job_dir, out, read_json, write_json

NETS = {"instagram": "18:30", "tiktok": "19:00", "facebook": "12:30", "linkedin": "08:30", "youtube": "17:00"}
DEFAULT_DAYS = {"instagram": ["mar", "jeu", "sam"], "tiktok": ["mar", "jeu", "ven"], "facebook": ["mer", "ven"],
                "linkedin": ["mar", "mer", "jeu"], "youtube": ["jeu", "sam"]}
DAYS = {"lun": 0, "mar": 1, "mer": 2, "jeu": 3, "ven": 4, "sam": 5, "dim": 6}
JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
STOP = set("""alors aussi autre avant avec avoir bien cette comme dans depuis donc elle elles encore entre faire fait
leur leurs mais même notre nous notamment parce pour plus quand quelque sans sont tout tous toute toutes très vous votre
voilà vraiment celle celui ceux chose choses permet permettent mettre utiliser différents plusieurs nouveau
nouvelle nouveaux""".split())
NUM = re.compile(r"\d+(?:[.,]\d+)?")
NUMW = {"1": ["un", "une"], "2": ["deux"], "3": ["trois"], "4": ["quatre"], "5": ["cinq"], "6": ["six"], "7": ["sept"],
        "8": ["huit"], "9": ["neuf"], "10": ["dix"], "12": ["douze"], "15": ["quinze"], "20": ["vingt"], "30": ["trente"]}


def brand_of(job):
    jj = job / "job.json"
    b = read_json(jj).get("brand") if jj.exists() else None
    bp = ROOT / "brands" / str(b) / "brand.json" if b else None
    return b, (read_json(bp) if bp and bp.exists() else {})


def tag(s):
    s = re.sub(r"[^\w\s'-]", "", s).replace("'", " ").replace("-", " ")
    return "#" + "".join(w[:1].upper() + w[1:] for w in s.split())


def sentences(t):
    """Phrases dites (sous-titres regroupés jusqu'à la ponctuation)."""
    words = [w for g in t.get("captions", []) for w in g["words"]]
    res, cur = [], []
    for i, w in enumerate(words):
        cur.append(w["w"])
        gap = words[i + 1]["start"] - w["end"] if i + 1 < len(words) else 9
        # fin de phrase : ponctuation, sinon pause de plus de 0,45 s (transcription sans ponctuation), ou 22 mots
        if w["w"].rstrip().endswith((".", "!", "?", "…")) or gap > 0.45 or len(cur) >= 22:
            res.append(" ".join(cur))
            cur = []
    if cur:
        res.append(" ".join(cur))
    return [s.strip() for s in res if len(s.split()) >= 3]


def material(job, slug):
    work = job / "work"
    t = read_json(work / f"{slug}_text.json") if (work / f"{slug}_text.json").exists() else {}
    said = sentences(t)
    full = " ".join(said)
    punch = [" ".join(w["w"] for w in o.get("words", [])) for o in t.get("overlays", []) if o.get("punch")]
    hook = ""
    for f, k in ((f"{slug}_hook.json", "text"), (f"{slug}_footage.json", "title")):
        if (work / f).exists():
            hook = read_json(work / f).get(k) or hook
    if not full and (work / f"{slug}_storyboard.json").exists():  # vidéo sans voix : textes à l'écran du storyboard
        sb = read_json(work / f"{slug}_storyboard.json")
        said = [s.get("voice") or s.get("text") or s.get("title") or "" for s in sb.get("scenes", [])]
        said = [s for s in said if s]
        full = " ".join(said)
    brief = read_json(work / "brief.json") if (work / "brief.json").exists() else {}
    return said, full, punch, hook, brief


def draft(job, slug):
    said, full, punch, hook, brief = material(job, slug)
    if not full and not hook:
        fail("rien à lire : ni texte dit (build_text.py), ni storyboard, ni titre")
    b, br = brand_of(job)
    strong = sorted(said, key=lambda s: -(2 * len(NUM.findall(s)) + sum(p.lower() in s.lower() for p in punch) + 0.02 * len(s)))[:2]
    city = ""
    addr = (br.get("contact") or {}).get("address", "")
    if "," in addr:
        city = addr.split(",")[-1].strip()
        city = re.sub(r"^\d{4,5}\s*", "", city)
    words = [w.strip(".,!?…:;«»\"'").lower() for w in full.split()]
    topics = [w for w, _ in Counter(w for w in words if len(w) >= 6 and w not in STOP and not NUM.search(w)).most_common(4)]
    social = br.get("social") or {}
    tags = list(social.get("hashtags", []))
    if br.get("name") and not br["name"].startswith("Nom de"):
        tags.append(tag(br["name"]))
    if city and city != "ville":
        tags.append(tag(city))
    if br.get("metier"):
        tags.append(tag(br["metier"]))
    tags += [tag(w) for w in topics]
    seen, hashtags = set(), []
    for h in tags:
        if h.lower() not in seen and len(h) > 2:
            seen.add(h.lower())
            hashtags.append(h)
    cta = brief.get("cta") or ((f"Plus d'infos : {(br.get('contact') or {}).get('site')}") if (br.get("contact") or {}).get("site") else "")
    first = hook or (punch[0] if punch else (strong[0] if strong else ""))
    body = " ".join(s for s in strong if s != first)
    data = {"statut": "brouillon : Claude réécrit dans le ton de la marque, puis enregistre work/<slug>_post.json",
            "caption": (first.rstrip(".") + ".\n" + body).strip(), "cta": cta, "hashtags": hashtags[:8],
            "first_comment": brief.get("mentions", "") or "",
            "matiere": {"accroche": hook, "punchs": punch[:4], "phrases_fortes": strong, "ton_marque": br.get("tone", ""),
                        "objectif": brief.get("objectif", ""), "public": brief.get("public", ""), "ton": brief.get("ton", ""),
                        "mentions": brief.get("mentions", ""), "eviter": brief.get("eviter", ""), "langues": brief.get("langues", "fr")}}
    dst = job / "work" / f"{slug}_post_draft.json"
    write_json(dst, data)
    out(ok=True, fichier=str(dst), hashtags=data["hashtags"], accroche=first[:120],
        suite="réécris caption / cta / first_comment dans le ton de la marque -> work/<slug>_post.json, puis post.py check")


def check(job, slug):
    pj = job / "work" / f"{slug}_post.json"
    if not pj.exists():
        fail("work/<slug>_post.json absent (post.py draft, puis réécriture)")
    p = read_json(pj)
    said, full, punch, hook, brief = material(job, slug)
    _, br = brand_of(job)
    cap, cta, fc = p.get("caption", ""), p.get("cta", ""), p.get("first_comment", "")
    allt = f"{cap}\n{cta}\n{fc}"
    pts = []
    first_line = cap.split("\n")[0]
    if len(first_line) > 125:
        pts.append(f"première ligne de {len(first_line)} caractères : coupée par « … plus » sur Instagram (≤ 125)")
    if len(allt) + sum(len(h) + 1 for h in p.get("hashtags", [])) > 2200:
        pts.append("texte trop long (> 2 200 caractères)")
    hs = p.get("hashtags", [])
    if not 3 <= len(hs) <= 8:
        pts.append(f"{len(hs)} hashtags (3 à 8 conseillés)")
    bad = [h for h in hs if not re.fullmatch(r"#[\wÀ-ÿ]+", h)]
    if bad:
        pts.append(f"hashtags mal formés : {', '.join(bad)}")
    low = allt.lower()
    for m in [x.strip() for x in re.split(r"[;,]", str(brief.get("mentions", ""))) if x.strip()]:
        nums = NUM.findall(m)
        ws = [w for w in re.findall(r"[\wÀ-ÿ]{3,}", m.lower()) if not NUM.fullmatch(w) and w not in STOP]
        ok_n = all(n in allt or any(re.search(rf"\b{w_}\b", low) for w_ in NUMW.get(n, [])) for n in nums)  # « 1 h » = « une heure »
        ok_w = not ws or sum(w in low for w in ws) >= max(1, len(ws) / 2)
        if not (ok_n and ok_w):  # chiffres de la mention présents ET au moins la moitié de ses mots
            pts.append(f"mention obligatoire absente : « {m} »")
    for e in [x.strip() for x in re.split(r"[;,]", str(brief.get("eviter", ""))) if x.strip() and x.strip().lower() not in ("rien", "non")]:
        if e.lower() in allt.lower():
            pts.append(f"à éviter, mais présent : « {e} »")
    known = " ".join([full, hook, " ".join(str(v) for v in brief.values()), str(br.get("contact", "")), str(br.get("tagline", ""))])
    known_nums = {n.replace(",", ".") for n in NUM.findall(known)}
    for n in NUM.findall(allt):
        if n.replace(",", ".") not in known_nums:
            pts.append(f"chiffre « {n} » absent de la vidéo, du brief et de la charte : à vérifier (rien d'inventé)")
    ton = str(brief.get("ton", "")).lower()
    emojis = re.findall(r"[\U0001F300-\U0001FAFF\u2600-\u27BF]", allt)
    if ton in ("sobre", "haut de gamme") and len(emojis) > 1:
        pts.append(f"{len(emojis)} emojis pour un ton {ton} (0 ou 1)")
    out(ok=True, verdict="OK" if not pts else "à revoir", points=pts, premiere_ligne=first_line)


def date(job, slug, reseau, apres):
    b, br = brand_of(job)
    pref = br.get("publication") or {}
    days = [DAYS[d[:3].lower()] for d in pref.get("jours", DEFAULT_DAYS.get(reseau, ["mar", "jeu"])) if d[:3].lower() in DAYS]
    heure = pref.get("heure") or NETS.get(reseau, "18:30")
    taken = set()
    for jj in (ROOT / "jobs").glob("*/job.json"):
        try:
            if read_json(jj).get("brand") != b or jj.parent == job:
                continue
        except Exception:  # noqa: BLE001
            continue
        for pj in (jj.parent / "work").glob("*_post*.json"):
            d_ = read_json(pj).get("date")
            if d_:
                taken.add(str(d_)[:10])
    day = dt.date.fromisoformat(apres) if apres else dt.date.today() + dt.timedelta(days=1)
    for _ in range(60):
        if day.weekday() in days and day.isoformat() not in taken:
            break
        day += dt.timedelta(days=1)
    when = f"{day.isoformat()}T{heure}"
    pj = job / "work" / f"{slug}_post.json"
    p = read_json(pj) if pj.exists() else {}
    p.update({"date": when, "reseau": reseau})
    write_json(pj, p)
    # rappel d'agenda (rien n'est publié)
    hh, mm = heure.split(":")
    stamp = dt.datetime.now().strftime("%Y%m%dT%H%M%S")
    st = f"{day.strftime('%Y%m%d')}T{hh}{mm}00"
    desc = (p.get("caption", "") + "\n" + p.get("cta", "") + "\n" + " ".join(p.get("hashtags", []))).strip()
    esc_ = lambda s: str(s).replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")
    ics = "\r\n".join(["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//VideoMakerDeeplo//FR", "BEGIN:VEVENT",
                       f"UID:{slug}-{st}@videomaker-deeplo", f"DTSTAMP:{stamp}", f"DTSTART:{st}", "DURATION:PT15M",
                       f"SUMMARY:{esc_('Publier : ' + slug + ' (' + reseau + ')')}", f"DESCRIPTION:{esc_(desc or 'texte du post : work/' + slug + '_post.json')}",
                       "BEGIN:VALARM", "TRIGGER:-PT30M", "ACTION:DISPLAY", "DESCRIPTION:Publication dans 30 min", "END:VALARM",
                       "END:VEVENT", "END:VCALENDAR"]) + "\r\n"
    (job / "renders").mkdir(exist_ok=True)
    (job / "renders" / "publication.ics").write_text(ics, encoding="utf-8")
    out(ok=True, date=f"{JOURS[day.weekday()]} {day.strftime('%d/%m/%Y')} à {heure}", reseau=reseau,
        jours_pris=sorted(taken)[-5:], rappel=str(job / "renders" / "publication.ics"),
        note="horaire repère : à ajuster avec les statistiques du compte ; rien n'est publié")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["draft", "check", "date"])
    ap.add_argument("job")
    ap.add_argument("slug")
    ap.add_argument("--reseau", default="instagram", choices=list(NETS))
    ap.add_argument("--apres", help="premier jour possible (AAAA-MM-JJ)")
    a = ap.parse_args()
    job = job_dir(a.job)
    {"draft": lambda: draft(job, a.slug), "check": lambda: check(job, a.slug),
     "date": lambda: date(job, a.slug, a.reseau, a.apres)}[a.cmd]()


if __name__ == "__main__":
    main()

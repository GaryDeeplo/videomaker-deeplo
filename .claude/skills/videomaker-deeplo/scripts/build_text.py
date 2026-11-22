"""TEXTE À L'ÉCRAN -> work/<slug>_text.json

Recale les mots sur le dérush (les mots des prises jetées disparaissent), puis prépare :
- "captions" : sous-titres complets mot à mot, en paquets de 1 à captionMaxWords mots (mode PME par défaut :
  la plupart regardent sans le son) ;
- "overlays" : phrases verbatim candidates, scorées, pré-cochées à ~5 par minute (doctrine reel-cut :
  la rareté fait la valeur), avec 2 punchs caméra par minute proposés.
Le script ne décide rien d'important : Claude corrige keep / punch / reason dans overlays, et peut
corriger l'orthographe d'un mot de captions (jamais ses temps).

  python build_text.py <job> <slug>
"""
import argparse
import re
import unicodedata

from common import config, fail, job_dir, out, read_json, write_json

STRONG = re.compile(r"[.!?…]+$")
SOFT = re.compile(r"[,;:]$")
STRIP_END = re.compile(r"[.,;:!?…]+$")
NUM = re.compile(r"\d")
FILLER = {"alors", "donc", "voila", "en", "fait", "du", "coup", "genre", "bah", "ben", "euh", "hein",
          "quoi", "et", "mais", "enfin", "tu", "vois", "je", "veux", "dire"}
STRONG_WORDS = {"jamais", "personne", "rien", "aucun", "gratuit", "gratuitement", "secret", "impossible",
                "nouveau", "nouvelle", "offert", "offerte", "promo", "seulement", "exclusif"}


def deac(s):
    return "".join(c for c in unicodedata.normalize("NFD", s.lower()) if unicodedata.category(c) != "Mn")


def remap(words, segments):
    res = []
    for w in words:
        for s in segments:
            if w["start"] >= s["src_start"] - 1e-3 and w["end"] <= s["src_end"] + 1e-3:
                d = s["out_start"] - s["src_start"]
                res.append({"w": w["w"], "start": round(w["start"] + d, 3), "end": round(w["end"] + d, 3)})
                break
    return res


def score(ph, text):
    n, s = len(ph), 0.0
    if NUM.search(text):
        s += 3.0
    s += 2.0 if 3 <= n <= 8 else (0.5 if n <= 2 else -(n - 8) * 0.4)
    toks = [deac(STRIP_END.sub("", w["w"])) for w in ph]
    s -= sum(t in FILLER for t in toks) / max(n, 1) * 4.0
    if any(t in STRONG_WORDS for t in toks):
        s += 1.5
    if any(w["w"][:1].isupper() and not w["w"].isupper() for w in ph[1:]) and n <= 6:
        s += 0.8
    return round(s, 2)


# mots qui ne finissent jamais un groupe (ils appellent le mot suivant) : articles, prépositions, liaisons, pronoms
WEAK = set("""le la les l un une des du de d à a au aux en et ou mais que qu qui ce cet cette ces se s sa son ses mon ma mes ton
ta tes notre nos votre vos leur leurs sur pour par dans avec sans chez sous vers ne n y on il ils elle elles je j tu nous vous
me m te t lui très plus moins tout tous toute toutes chaque dont où si comme puis aussi c ça ni est sont c'est n'est qu'il
qu'elle qu'on s'il j'ai the a an of to in on at for and or with is are de het een en van op te voor met is""".split())
HARD = set("""le la les l un une des du de d à au aux en sur pour par dans avec sans chez sous vers ma ta sa mon ton son mes tes ses
notre nos votre vos leur leurs ce cet cette ces se ne n me m te t y ça on je j tu il ils elle elles the a an of to in on at for
with het een van op voor met""".split())  # interdits en fin (articles, prépositions, pronoms avant le verbe)
NUMW = set("un une deux trois quatre cinq six sept huit neuf dix onze douze quinze vingt trente quarante cinquante soixante cent mille".split())
QSTART = set("comment pourquoi quand combien quel quelle quels quelles".split())  # ouvrent un groupe
UNITS = set("€ euros euro % cent ans an heures heure h min minutes jours jour semaines mois km kg m² ml g".split())


def _split_clause(cl, max_words):
    """Groupes équilibrés dans un morceau de phrase : jamais de fin sur un petit mot, jamais un mot seul,
    jamais un nombre séparé de son unité (programmation dynamique sur les points de coupe)."""
    n = len(cl)
    # « 1 800 » compte pour un mot : un bloc de 3 chiffres après un nombre prolonge ce nombre
    wt = [0 if t and re.fullmatch(r"\d{3}\D*", cl[t]["w"]) and NUM.search(cl[t - 1]["w"]) else 1 for t in range(n)]
    eff = sum(wt)
    if eff <= max_words:
        return [cl]
    k = -(-eff // max_words)
    target = eff / k
    INF = 1e9
    best, prev = [0.0] + [INF] * n, [0] * (n + 1)

    def numeric(t):
        return 0 <= t < n and (NUM.search(cl[t]["w"]) or deac(STRIP_END.sub("", cl[t]["w"]).lower()) in NUMW)

    for i in range(1, n + 1):
        for j in range(i - 1, -1, -1):
            L = sum(wt[j:i])
            if L > max_words + 1:
                break
            cost = 0.5 * (L - target) ** 2 + (3 if L > max_words else 0)  # un 4e mot plutôt qu'une mauvaise coupe
            if L == 1:
                cost += 12
            last = cl[i - 1]
            if i < n:
                kl = deac(STRIP_END.sub("", last["w"]).lower())
                kl_core = re.split(r"[’']", kl)[0] if re.search(r"[’']$", kl) else kl
                if kl_core in HARD or re.search(r"[’']$", kl):
                    cost += 20
                elif kl_core in WEAK:
                    cost += 8
                elif kl_core in QSTART:
                    cost += 10
                nxt = deac(STRIP_END.sub("", cl[i]["w"]).lower())
                is_num = bool(NUM.search(last["w"])) or kl in NUMW
                if is_num and re.fullmatch(r"\d{3}\D*", cl[i]["w"]) and not re.search(r"[.,;:]$", last["w"]):
                    cost += 30  # « 3 150 » : milliers jamais séparés
                elif is_num and (nxt in UNITS or nxt.startswith("€")):
                    cost += 15
                elif is_num and not re.search(r"[.,;:!?]$", last["w"]):
                    cost += 9  # un nombre reste avec ce qui le suit (« deux livraisons », « de 4 à 7 »)
                after = deac(STRIP_END.sub("", cl[i + 1]["w"]).lower()) if i + 1 < n else ""
                if nxt == "pour" and after == "cent" and is_num:
                    cost += 15  # « 20 pour cent »
                if is_num and nxt in ("a", "et", "ou") and numeric(i + 1):
                    cost += 20
                if kl in ("a", "et", "ou") and numeric(i - 2) and numeric(i):
                    cost += 20  # fourchette « 4 à 7 », « 1 800 et 3 150 »
                if re.fullmatch(r"[?!:;»…]+", cl[i]["w"]):
                    cost += 30
            if best[j] + cost < best[i]:
                best[i], prev[i] = best[j] + cost, j
    out_, i = [], n
    while i > 0:
        out_.append(cl[prev[i]:i])
        i = prev[i]
    return out_[::-1]


def chunks(ws, max_words, gap):
    """Groupes de sous-titres : on coupe d'abord aux fins de phrase, aux virgules et aux pauses, puis chaque morceau
    est réparti en groupes équilibrés (le moins de coupures en plein milieu d'une idée)."""
    clauses, cur = [], []
    for w in ws:
        if cur and w["start"] - cur[-1]["end"] > gap:
            clauses.append(cur)
            cur = []
        cur.append(w)
        if STRONG.search(w["w"]) or (SOFT.search(w["w"]) and len(cur) >= 2):
            clauses.append(cur)
            cur = []
    if cur:
        clauses.append(cur)
    # un morceau d'un seul mot rejoint son voisin s'il reste de la place (« Ensuite, » + « rien à faire »)
    merged = []
    for cl in clauses:
        if merged and (len(cl) == 1 or len(merged[-1]) == 1) and len(merged[-1]) + len(cl) <= max_words                 and not STRONG.search(merged[-1][-1]["w"]) and cl[0]["start"] - merged[-1][-1]["end"] <= gap:
            merged[-1] = merged[-1] + cl
        else:
            merged.append(cl)
    res = []
    for cl in merged:
        res += _split_clause(cl, max_words)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("job")
    ap.add_argument("slug")
    a = ap.parse_args()
    job = job_dir(a.job)
    c = config(job)["text"]
    wj, mj = job / "work" / f"{a.slug}_words.json", job / "work" / f"{a.slug}_map.json"
    for p in (wj, mj):
        if not p.exists():
            fail(f"{p} absent")
    words = read_json(wj)["words"]
    m = read_json(mj)
    from common import HESITATIONS, _norm_word
    ws = [w for w in remap(words, m["segments"]) if _norm_word(w["w"]) not in HESITATIONS]  # « euh » gardé : pas écrit
    if not ws:
        fail("aucun mot après recalage")
    dur = float(m["out_duration"])

    caps = []
    for ch in chunks(ws, c["captionMaxWords"], 0.35):
        caps.append({"id": len(caps), "start": ch[0]["start"], "end": ch[-1]["end"],
                     "words": [{"w": STRIP_END.sub("", x["w"]) or x["w"], "start": x["start"], "end": x["end"]}
                               for x in ch]})

    cands = []
    for ph in chunks(ws, 8, 0.45):
        text = re.sub(r"\s{2,}", " ", " ".join(STRIP_END.sub("", x["w"]) for x in ph)).strip()
        if text:
            cands.append({"id": len(cands), "text": text, "start": ph[0]["start"], "end": ph[-1]["end"],
                          "score": score(ph, text),
                          "words": [{"w": STRIP_END.sub("", x["w"]), "start": x["start"]} for x in ph],
                          "keep": False, "punch": False, "reason": ""})
    target = max(1, round(dur / 60 * c["overlaysPerMinute"]))
    best = sorted(cands, key=lambda x: -x["score"])
    for o in best[:target]:
        o["keep"] = True
    for o in best[:max(1, round(dur / 60 * config(job)["camera"]["punchesPerMinute"]))]:
        o["punch"] = True

    dst = job / "work" / f"{a.slug}_text.json"
    write_json(dst, {"slug": a.slug, "out_duration": dur, "mode": c["mode"], "captions": caps,
                     "overlays": cands})
    out(ok=True, mode=c["mode"], captions=len(caps), overlay_candidats=len(cands), overlays_precoches=target,
        punchs_proposes=sum(o["punch"] for o in cands), mots_perdus_dans_les_coupes=len(words) - len(ws),
        out=str(dst), suite="vérifie keep/punch/reason (et l'orthographe), puis build_composition.py")


if __name__ == "__main__":
    main()

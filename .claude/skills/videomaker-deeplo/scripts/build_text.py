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


def chunks(ws, max_words, gap):
    res, cur = [], []
    for w in ws:
        if cur and (w["start"] - cur[-1]["end"] > gap or len(cur) >= max_words
                    or (SOFT.search(cur[-1]["w"]) and len(cur) >= 2)):
            res.append(cur)
            cur = []
        cur.append(w)
        if STRONG.search(w["w"]):
            res.append(cur)
            cur = []
    if cur:
        res.append(cur)
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

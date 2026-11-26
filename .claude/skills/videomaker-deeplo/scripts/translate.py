"""SOUS-TITRES TRADUITS (FR -> NL / EN / …) sur la même vidéo, voix d'origine conservée.

  python translate.py export <job> <slug> --to nl     # -> work/<slug>_tr_nl.json (phrases + temps, champ "nl" vide)
  #   Claude remplit chaque "nl" (et "hook_nl", "post_nl" s'ils existent) : traduction naturelle, même sens,
  #   longueur proche ; noms propres et marques inchangés. Jamais de temps modifiés.
  python translate.py apply <job> <slug> --to nl      # -> work/<slug>_text_nl.json (+ _hook_nl, _post_nl)
  python build_composition.py <job> <slug> --lang nl  (rush)   |   python build_scenes.py <job> <slug> --lang nl
  python deliver.py <job> <slug> --lang nl

Les temps restent ceux des phrases réellement dites ; à l'intérieur d'une phrase, les mots traduits sont répartis
au prorata de leur longueur (la langue d'arrivée n'a pas les mêmes mots aux mêmes instants).
"""
import argparse
import re

from build_text import chunks, clean_word, group_size, remap
from common import config, fail, job_dir, out, read_json, write_json

STRONG = re.compile(r"[.!?…]$")
STRIP_END = re.compile(r"[.,;:!?…]+$")


def sentences(ws):
    res, cur = [], []
    for i, w in enumerate(ws):
        cur.append(w)
        nxt = ws[i + 1] if i + 1 < len(ws) else None
        if STRONG.search(w["w"]) or nxt is None or nxt["start"] - w["end"] > 0.9:
            res.append(cur)
            cur = []
    return res


def export(job, slug, lang):
    work = job / "work"
    words = read_json(work / f"{slug}_words.json")["words"]
    ws = remap(words, read_json(work / f"{slug}_map.json")["segments"])
    ss = [{"id": k, "start": s[0]["start"], "end": s[-1]["end"], "fr": " ".join(w["w"] for w in s), lang: ""}
          for k, s in enumerate(sentences(ws))]
    data = {"lang": lang, "sentences": ss}
    if (work / f"{slug}_hook.json").exists():
        data["hook_fr"], data[f"hook_{lang}"] = read_json(work / f"{slug}_hook.json")["text"], ""
    if (work / f"{slug}_post.json").exists():
        data["post_fr"], data[f"post_{lang}"] = read_json(work / f"{slug}_post.json"), {}
    lt = (config(job).get("branding") or {}).get("lowerThird") or {}
    if lt.get("role"):  # le nom ne se traduit pas, la fonction oui
        data["role_fr"], data[f"role_{lang}"] = lt["role"], ""
    dst = work / f"{slug}_tr_{lang}.json"
    if dst.exists():  # ré-export : on garde les traductions déjà faites (même texte source)
        old = read_json(dst)
        done = {x["fr"]: x.get(lang, "") for x in old.get("sentences", [])}
        for x in data["sentences"]:
            x[lang] = done.get(x["fr"], "")
        for k in (f"hook_{lang}", f"post_{lang}", f"role_{lang}"):
            if k in data and old.get(k):
                data[k] = old[k]
    write_json(dst, data)
    out(ok=True, phrases=len(ss), fichier=str(dst), suite=f"remplis les champs « {lang} », puis translate.py apply")


def apply(job, slug, lang):
    work = job / "work"
    tr = read_json(work / f"{slug}_tr_{lang}.json")
    missing = [s["id"] for s in tr["sentences"] if not s.get(lang, "").strip()]
    if missing:
        fail(f"traductions manquantes ({lang}) pour les phrases {missing[:12]}")
    c = config(job)
    maxw, maxc = group_size(job, c["text"].get("captionStyle", "pop"), c)  # mêmes groupes que la version d'origine
    caps = []
    for s in tr["sentences"]:
        toks = s[lang].split()
        dur = max(0.2, s["end"] - s["start"])
        weights = [len(STRIP_END.sub("", t)) + 2 for t in toks]
        tot, acc, timed = sum(weights), 0.0, []
        for t, wgt in zip(toks, weights):
            st = s["start"] + dur * acc / tot
            acc += wgt
            timed.append({"w": t, "start": round(st, 3), "end": round(s["start"] + dur * acc / tot, 3)})
        for g in chunks(timed, maxw, 0.35, maxc):  # coupes aux virgules et aux idées (ponctuation lue ici), plafond du style
            g = [{**x, "w": clean_word(x["w"], lang)} for x in g]  # puis mots affichés : ? et ! gardés, . , ; : retirés
            caps.append({"id": len(caps), "start": g[0]["start"], "end": g[-1]["end"], "words": g})
    base = read_json(work / f"{slug}_text.json") if (work / f"{slug}_text.json").exists() else {"overlays": []}
    overlays = [{**o, "keep": False} for o in base.get("overlays", [])]  # textes verbatim : pas en traduction ; punchs gardés
    write_json(work / f"{slug}_text_{lang}.json", {"slug": slug, "lang": lang, "mode": "captions", "captions": caps,
                                                    "overlays": overlays, "out_duration": base.get("out_duration")})
    extra = []
    if tr.get(f"hook_{lang}"):
        write_json(work / f"{slug}_hook_{lang}.json", {"text": tr[f"hook_{lang}"]})
        extra.append("accroche")
    if tr.get(f"post_{lang}"):
        write_json(work / f"{slug}_post_{lang}.json", tr[f"post_{lang}"])
        extra.append("post")
    if tr.get(f"role_{lang}"):
        write_json(work / f"{slug}_role_{lang}.json", {"role": tr[f"role_{lang}"]})
        extra.append("fonction du bandeau")
    out(ok=True, lang=lang, sous_titres=len(caps), aussi=extra,
        suite=f"build_composition.py / build_scenes.py --lang {lang}, puis check + snapshot, deliver.py --lang {lang}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["export", "apply"])
    ap.add_argument("job")
    ap.add_argument("slug")
    ap.add_argument("--to", required=True, help="code langue : nl, en, de…")
    a = ap.parse_args()
    job = job_dir(a.job)
    (export if a.cmd == "export" else apply)(job, a.slug, a.to)


if __name__ == "__main__":
    main()

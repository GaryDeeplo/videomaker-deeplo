"""PLAN DE COUPE déterministe -> work/<slug>_plan.json   (repris de reel-cut, adapté)

Claude ne donne JAMAIS un timestamp. Le OÙ couper vient d'ici (ffmpeg silencedetect + mots
horodatés) ; chaque bord d'îlot tombe au milieu d'un silence mesuré. Le QUOI garder vient de Claude,
qui n'écrit que "keep" et "reason" dans le plan.

  python cut_plan.py <job> <slug> [--min-silence 0.45] [--noise -32] [--pad 0.3]

Dans chaque îlot gardé, l'outil repère aussi (champ "fillers" du plan) :
  hesitation  « euh », « hum », « bah »                    -> remove: true
  repetition  « je je », « le le » (mot répété collé)      -> remove: true (on garde la 2e occurrence)
  pause       blanc de 0,6 s et plus au milieu d'une phrase -> remove: true (on garde 0,12 s de chaque côté)
  tic         « du coup », « en fait », « voilà », « genre » -> remove: false : Claude décide selon la phrase
  reformulation  même suite de 3 mots ou plus redite juste après -> remove: false : retirer si la 2e version
                 n'ajoute rien (« qu'on réalise toutes les semaines, qu'on prend toutes les semaines »)
  restart     (transcription --islands seulement) phrase recommencée : un îlot de parole (VAD) repris au début de
              l'îlot suivant -> on garde la dernière prise, la précédente part (du 1er mot de la fausse prise au mot
              d'avant la reprise). Sûre (remove: true) quand la fausse prise est redite mot pour mot ou abandonnée
              un mot après le passage commun (3 mots ou plus) ; possible (remove: false, Claude tranche) pour un début commun
              de 2 mots, ou de 3 et plus suivi d'une suite différente. Aussi sûre : les 1 à 3 derniers mots d'un îlot
              redits au début du suivant (« une personne qui… | qui m'a aidée »). Un îlot du plan entièrement fait de fausse
              prise passe à keep: false (« reprise (auto) »). Résumé dans "restarts" du plan.
Claude peut basculer "remove" (jamais les temps). Prudence : on ne retire jamais un mot qui porte le sens.

--pad : marge maximale gardée avant / après la parole (bruit de fond, pièce qui résonne : le silence mesuré peut
commencer loin de la voix ; la coupe se rapproche alors des mots, jamais à moins de --pad).
"""
import argparse
import re
import subprocess
from pathlib import Path

from common import HESITATIONS, NO_REPEAT, TICS, _norm_word, config, fail, job_dir, out, read_json, write_json

PAUSE_MIN, PAUSE_KEEP, EDGE = 0.6, 0.12, 0.03
RESTART_GAP = 4.0  # au-delà de 4 s de blanc entre deux îlots, ce n'est plus une reprise mais une nouvelle phrase


def fillers(islands, isl_words):
    """Repérage dans chaque îlot : bornes = fin du mot d'avant / début du mot d'après (jamais un temps écrit à la main)."""
    res = []
    for isl, ws in zip(islands, isl_words):
        n = [_norm_word(w["w"]) for w in ws]

        def span(i, j, kind, text, remove, reason):  # retire les mots i..j inclus
            a = ws[i - 1]["end"] + EDGE if i > 0 else isl["cut_start"]
            b = ws[j + 1]["start"] - EDGE if j + 1 < len(ws) else isl["cut_end"]
            if b - a >= 0.1 and not (i == 0 and j == len(ws) - 1):  # jamais tout l'îlot (c'est le rôle de keep)
                res.append({"id": len(res), "island": isl["id"], "kind": kind, "text": text,
                            "cut_start": round(a, 3), "cut_end": round(b, 3), "remove": remove, "reason": reason})

        k = 0
        while k < len(ws):
            if n[k] in HESITATIONS:
                j = k
                while j + 1 < len(ws) and n[j + 1] in HESITATIONS:
                    j += 1
                span(k, j, "hesitation", " ".join(w["w"] for w in ws[k:j + 1]), True, "hésitation")
                k = j + 1
                continue
            if k + 1 < len(ws) and n[k] and n[k] == n[k + 1] and n[k] not in NO_REPEAT and not n[k].isdigit():
                span(k, k, "repetition", f"{ws[k]['w']} {ws[k + 1]['w']}", True, "mot répété (bégaiement)")
                k += 1
                continue
            for t in TICS:
                if tuple(n[k:k + len(t)]) == t:
                    span(k, k + len(t) - 1, "tic", " ".join(w["w"] for w in ws[k:k + len(t)]), False,
                         "tic de langage : à retirer seulement s'il n'apporte rien à la phrase")
                    k += len(t) - 1
                    break
            k += 1
        # reformulation : une même suite de 3 mots ou plus redite juste après (« qu'on réalise toutes les semaines,
        # qu'on prend toutes les semaines ») -> on propose de retirer de la fin de la 1re à la fin de la 2e ; remove: false,
        # car une répétition peut être voulue ou porter une idée nouvelle (« des vidéos …, et des photos … ») : Claude tranche
        k, seen_r = 0, set()
        while k < len(ws):
            best = None
            for L in range(6, 2, -1):
                key = tuple(n[k:k + L])
                if len(key) < L or not all(key):
                    continue
                for m in range(k + L, min(len(ws) - L + 1, k + L + 9)):
                    if tuple(n[m:m + L]) == key:
                        best = (L, m)
                        break
                if best:
                    break
            if best and (k, best[1]) not in seen_r:
                L, m = best
                seen_r.add((k, m))
                span(k + L, m + L - 1, "reformulation", " ".join(w["w"] for w in ws[k + L:m + L]), False,
                     "reformulation : la même idée redite ; à retirer si la 2e version n'ajoute rien")
                k += L
                continue
            k += 1
        for k in range(len(ws) - 1):  # blancs au milieu d'une phrase (« euh » muet, recherche du mot)
            gap = ws[k + 1]["start"] - ws[k]["end"]
            if gap >= PAUSE_MIN:
                res.append({"id": len(res), "island": isl["id"], "kind": "pause", "text": f"{ws[k]['w']} … {ws[k + 1]['w']}",
                            "cut_start": round(ws[k]["end"] + PAUSE_KEEP, 3), "cut_end": round(ws[k + 1]["start"] - PAUSE_KEEP, 3),
                            "remove": True, "reason": f"blanc de {gap:.1f} s dans la phrase"})
    return res


def _common(e, l):
    """Nombre de mots d'ouverture communs ; le dernier mot de la fausse prise peut être coupé (« dir » / « directrice »)."""
    k = 0
    while k < len(e) and k < len(l) and (e[k] == l[k] or (k == len(e) - 1 and len(e[k]) >= 2 and l[k].startswith(e[k]))):
        k += 1
    return k


def restarts(words):
    """Reprises entre îlots de parole transcrits séparément (transcribe.py --islands) ; d'après ghost-editor
    (subcheck.py, MIT) : une ouverture répétée trahit une fausse prise que Whisper fusionne sur le fichier entier.
    Rend [(i0, i1, j, k, sure)] : mots i0..i1 (indices de words) à couper, reprise au mot j, k mots en commun."""
    groups = {}
    for n, w in enumerate(words):
        if "island" in w:
            groups.setdefault(w["island"], []).append(n)
    ids = sorted(groups)
    toks = {i: [(t, n) for n in groups[i] for t in [_norm_word(words[n]["w"])] if t and t not in HESITATIONS]
            for i in ids}
    res = []
    for x, i in enumerate(ids):
        e = [t for t, _ in toks[i]]
        if not e:
            continue
        found = False
        for y in (x + 1, x + 2):  # îlot suivant, ou celui d'après (un fragment de 3 mots au plus entre les deux)
            if y >= len(ids):
                break
            j = ids[y]
            if words[groups[j][0]]["start"] - words[groups[ids[y - 1]][-1]]["end"] > RESTART_GAP:
                break
            if y == x + 2 and (len(toks[ids[x + 1]]) > 3 or len(e) < 2):  # entre les deux, un vrai bout de phrase
                break
            stream = [t for z in ids[y:y + 4] for t, _ in toks[z]][:len(e) + 3]  # la reprise peut déborder sur l'îlot suivant
            k = _common(e, stream)
            if k == len(e) or (k >= 3 and len(e) - k <= 1):  # redite mot pour mot, ou lâchée un mot plus loin
                sure = True
            elif k >= 3 or (k == 2 and y == x + 1):
                sure = False
            else:
                continue
            res.append((groups[i][0], groups[j][0] - 1, groups[j][0], k, sure))
            found = True
            break
        # bégaiement par-dessus la pause : « une personne qui… | qui m'a aidée » -> on coupe la fin de la 1re
        if not found and x + 1 < len(ids) and toks[ids[x + 1]]:
            j = ids[x + 1]
            l = [t for t, _ in toks[j]]
            if words[groups[j][0]]["start"] - words[groups[i][-1]]["end"] <= RESTART_GAP:
                for m in (3, 2, 1):
                    if len(e) > m and e[-m:] == l[:m] and (m > 1 or (e[-1] not in NO_REPEAT and not e[-1].isdigit())):
                        res.append((toks[i][-m][1], groups[j][0] - 1, groups[j][0], m, True))
                        break
    return res


def apply_restarts(rs, words, plan, isl_words, fl0):
    """Reporte les reprises sur le plan : îlot du plan entièrement dans la fausse prise -> keep (sûre) ou reason ;
    sinon un filler « restart » borné par les mots voisins (jamais un temps écrit à la main)."""
    pos = {id(w): (p, li) for p, ws in enumerate(isl_words) for li, w in enumerate(ws)}
    fl, summary = [], []
    reps = [(f["cut_start"], f["cut_end"]) for f in fl0 if f["kind"] == "repetition"]
    for r, (i0, i1, j, k, sure) in enumerate(rs):
        take = " ".join(w["w"] for w in words[i0:i1 + 1])
        retake = " ".join(w["w"] for w in words[j:j + 8])
        why = (f"reprise : « {take} » recommencé juste après ({k} mot{'s' * (k > 1)} en commun) ; on garde la dernière prise"
               if sure else f"reprise possible : même début ({k} mots) ; à couper si la 2e version redit la même idée")
        touched = {}
        for w in words[i0:i1 + 1]:
            p, li = pos[id(w)]
            touched.setdefault(p, []).append(li)
        for p, lis in touched.items():
            isl, ws = plan[p], isl_words[p]
            a, b = min(lis), max(lis)
            if a == 0 and b == len(ws) - 1:  # tout l'îlot du plan est fausse prise
                if sure and isl["keep"]:
                    isl["keep"], isl["reason"] = False, "reprise (auto)"
                elif not sure and not isl["reason"]:
                    isl["reason"] = "reprise possible (voir restarts)"
                continue
            cs = ws[a - 1]["end"] + EDGE if a > 0 else isl["cut_start"]
            ce = ws[b + 1]["start"] - EDGE if b + 1 < len(ws) else isl["cut_end"]
            if ce - cs >= 0.1 and not any(cs < re_ and ce > rs_ for rs_, re_ in reps):  # déjà vu en « repetition »
                fl.append({"id": len(fl0) + len(fl), "island": isl["id"], "kind": "restart",
                           "text": " ".join(w["w"] for w in ws[a:b + 1]), "cut_start": round(cs, 3),
                           "cut_end": round(ce, 3), "remove": sure, "reason": why})
        summary.append({"id": r, "take": take, "retake": retake, "common_words": k, "sure": sure,
                        "speech_start": words[i0]["start"], "retake_start": words[j]["start"],
                        "plan_islands": sorted(plan[p]["id"] for p in touched), "reason": why})
    return fl, summary


def silences(src, noise, mind, t0, t1):
    cmd = ["ffmpeg", "-hide_banner", "-nostats"]
    if t0:
        cmd += ["-ss", str(t0)]
    if t1:
        cmd += ["-to", str(t1)]
    log = subprocess.run(cmd + ["-i", str(src), "-vn", "-af", f"silencedetect=noise={noise}dB:d={mind}",
                                "-f", "null", "-"], capture_output=True, text=True,
                         encoding="utf-8", errors="replace").stderr
    off = t0 or 0.0
    st = [float(x) + off for x in re.findall(r"silence_start:\s*(-?[\d.]+)", log)]
    en = [float(x) + off for x in re.findall(r"silence_end:\s*([\d.]+)", log)]
    return [(max(off, s), en[i] if i < len(en) else None) for i, s in enumerate(st)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("job")
    ap.add_argument("slug")
    ap.add_argument("--min-silence", type=float)
    ap.add_argument("--noise", type=float)
    ap.add_argument("--pad", type=float)
    a = ap.parse_args()
    job = job_dir(a.job)
    c = config(job)["derush"]
    mind = a.min_silence if a.min_silence is not None else c["minSilence"]
    noise = a.noise if a.noise is not None else c["noiseDb"]
    pad = a.pad if a.pad is not None else c.get("maxPad", 0.3)

    wj = job / "work" / f"{a.slug}_words.json"
    if not wj.exists():
        fail(f"{wj} absent, lance transcribe.py")
    d = read_json(wj)
    words, src = d["words"], Path(d["source"])
    t0, t1 = (d.get("range") or [None, None])
    lo, hi = (t0 or 0.0), (t1 or float(d["duration"]))

    cuts = []
    for s, e in silences(src, noise, mind, t0, t1):
        e = hi if e is None else e
        if e - s >= mind:
            cuts.append({"start": s, "end": e, "mid": (s + e) / 2})

    islands, cur = [], []
    for w in words:
        if cur:
            gap = w["start"] - cur[-1]["end"]
            crosses = any(x["start"] <= cur[-1]["end"] + 1e-3 and x["end"] >= w["start"] - 1e-3 for x in cuts)
            if gap >= mind or crosses:
                islands.append(cur)
                cur = []
        cur.append(w)
    if cur:
        islands.append(cur)

    def before(t):
        p = [x for x in cuts if x["end"] <= t + 1e-3]
        return round(p[-1]["mid"], 3) if p else round(lo, 3)

    def after(t):
        n = [x for x in cuts if x["start"] >= t - 1e-3]
        return round(n[0]["mid"], 3) if n else round(hi, 3)

    plan = [{"id": i, "text": " ".join(w["w"] for w in isl).strip(),
             "speech_start": round(isl[0]["start"], 3), "speech_end": round(isl[-1]["end"], 3),
             "cut_start": max(before(isl[0]["start"]), round(isl[0]["start"] - pad, 3)),
             "cut_end": min(after(isl[-1]["end"]), round(isl[-1]["end"] + pad, 3)),
             "n_words": len(isl), "keep": True, "reason": ""}
            for i, isl in enumerate(islands)]
    for i in range(len(plan) - 1):
        if plan[i]["cut_end"] > plan[i + 1]["cut_start"]:
            m = round((plan[i]["speech_end"] + plan[i + 1]["speech_start"]) / 2, 3)
            plan[i]["cut_end"] = plan[i + 1]["cut_start"] = m

    for isl, ws in zip(plan, islands):  # îlot fait seulement de « euh » : écarté d'office (Claude peut le remettre)
        if all(_norm_word(w["w"]) in HESITATIONS for w in ws):
            isl["keep"], isl["reason"] = False, "hésitation seule (auto)"
    fl = fillers(plan, islands)
    extra, isl_mode = {}, d.get("mode") == "islands"
    if isl_mode:  # transcription îlot par îlot : les fausses prises sont restées écrites, on les repère
        rf, rsum = apply_restarts(restarts(words), words, plan, islands, fl)
        fl += rf
        extra = {"restarts": rsum}
    dst = job / "work" / f"{a.slug}_plan.json"
    write_json(dst, {"slug": a.slug, "source": str(src), "duration": round(hi - lo, 3), "range": [lo, hi],
                     "min_silence": mind, "noise_db": noise, "n_islands": len(plan),
                     "n_silences": len(cuts), "islands": plan, "fillers": fl, **extra})
    kinds = {k: sum(1 for f in fl if f["kind"] == k) for k in ("hesitation", "repetition", "pause", "tic")}
    kinds["ilots_hesitation"] = sum(1 for i in plan if i["reason"] == "hésitation seule (auto)")
    if isl_mode:
        kinds["reprises_sures"] = sum(1 for r in extra["restarts"] if r["sure"])
        kinds["reprises_possibles"] = sum(1 for r in extra["restarts"] if not r["sure"])
        kinds["ilots_reprise"] = sum(1 for i in plan if i["reason"] == "reprise (auto)")
    out(ok=True, islands=len(plan), silences=len(cuts), duration=round(hi - lo, 1), fillers=kinds,
        gain_fillers_s=round(sum(f["cut_end"] - f["cut_start"] for f in fl if f["remove"]), 1), out=str(dst),
        suite="édite keep/reason des îlots et remove des fillers (tics : au cas par cas), puis build_cut.py")


if __name__ == "__main__":
    main()

"""ZOOMS SUR LES MOTS FORTS d'un rush face caméra (style CapCut / Hormozi) : l'image se resserre d'un coup ou glisse
vers le visage sur les mots appuyés, puis revient à la fin de la phrase.

  python zooms.py <job> <slug> [--par-minute 8]      # liste les mots retenus (pour vérifier avant le montage)
  build_composition.py <job> <slug> --zooms           # les pose (ou "camera": {"zooms": true} dans la config)

Les mots viennent des MESURES, jamais d'un timecode écrit : volume de la voix sur chaque mot comparé aux 4 s autour
(le mot qu'on appuie ressort), mot étiré (dit plus lentement que sa longueur), et poids du mot lui-même (chiffre,
nom long, mot de contraste « jamais », « gratuit », « vraiment »…) ; les petits mots (le, de, et…) ne comptent pas.
Espacement d'au moins 3,5 s, rien dans la première seconde, alternance « coup sec » / « glissé ».
"""
import argparse
import re
import subprocess
from pathlib import Path

import numpy as np

from common import job_dir, out, read_json

SMALL = set("""le la les l un une des de du d au aux à a et ou mais donc or ni car que qu qui quoi dont où ce cet cette ces
c ça cela il elle ils elles on je j tu nous vous me m te t se s lui leur leurs y en ne n pas plus mon ma mes ton ta tes
son sa ses notre nos votre vos est sont été être avoir ai as avons avez ont fait faire sur sous dans par pour avec sans
chez vers comme si alors bon ben euh hein voilà là ici aussi très tout tous toute toutes bien peu
permet permettent permettre mettre met mettent utiliser créer crée créé dire dit aller va vont voir peut peux peuvent
notamment différents différentes plusieurs chose choses truc trucs genre juste ailleurs également ensuite déjà
ajouté ajoutés ajoutée ajoutées parallèle côté pareil niveau donc vais vas allons allez""".split())
STRONG = set("""jamais toujours rien tout gratuit gratuite offert offerte vraiment énorme incroyable seul seule seulement
premier première dernier dernière nouveau nouvelle meilleur meilleure pire secret secrets stop attention erreur
erreurs problème solution résultat résultats moitié double triple zéro aucun aucune fois maintenant aujourd'hui
vite rapide facile simple clé important essentiel automatique automatisé""".split())
NUM = re.compile(r"\d")
NUMW = set("""deux trois quatre cinq six sept huit neuf dix onze douze quinze vingt trente quarante cinquante soixante
cent cents mille million millions milliard pourcent""".split())


def norm(w):
    return re.sub(r"[^\wà-ÿ'’-]", "", w.lower()).replace("’", "'").split("'")[-1]


def word_db(audio, sr, words):
    """Volume (dB) de chaque mot dans la voix montée."""
    res = []
    for w in words:
        a, b = int(w["start"] * sr), int(max(w["end"], w["start"] + 0.05) * sr)
        seg = audio[a:b]
        res.append(20 * np.log10(np.sqrt(np.mean(seg ** 2)) + 1e-6) if len(seg) else -80.0)
    return np.array(res)


def strong_words(job, slug, per_min=8.0, gap=3.5):
    """-> [{"t", "fin", "mot", "kind", "score"}] en temps du montage (après coupe)."""
    work = job / "work"
    m, t = read_json(work / f"{slug}_map.json"), read_json(work / f"{slug}_text.json")
    dur = float(m["out_duration"])
    groups = t.get("captions", [])
    words = [dict(w, g=gi) for gi, g in enumerate(groups) for w in g["words"]]
    if len(words) < 4:
        return []
    src = Path(m["cut"])
    src = src if src.is_absolute() else job / "assets" / src.name
    sr = 16000
    p = subprocess.run(["ffmpeg", "-v", "error", "-i", str(src), "-vn", "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"], capture_output=True)
    audio = np.frombuffer(p.stdout, dtype=np.float32)
    db = word_db(audio, sr, words)
    st = np.array([w["start"] for w in words])
    base = np.array([np.median(db[np.abs(st - s) <= 4.0]) for s in st])
    loud = np.clip((db - base) / 5.0, -1, 1.2)  # +5 dB au-dessus de ce qui l'entoure : mot appuyé
    sc = []
    for i, w in enumerate(words):
        n = norm(w["w"])
        if not n or n in SMALL or len(n) < 3 and not NUM.search(n):
            sc.append(-9.0)
            continue
        txt = 0.0
        if NUM.search(w["w"]) or n in NUMW:
            txt += 1.2
        if n in STRONG or n.rstrip("s") in STRONG or n.rstrip("es") in STRONG:
            txt += 1.0
        if len(n) >= 7:
            txt += 0.3
        if w["w"].rstrip().endswith(("!", "?")):
            txt += 0.4
        stretch = (w["end"] - w["start"]) / (0.055 * len(n) + 0.09)
        sc.append(0.9 * loud[i] + txt + 0.35 * np.clip(stretch - 1, 0, 1.5))
    order = np.argsort(sc)[::-1]
    n_max = max(1, int(round(dur / 60 * per_min)))
    picked = []
    for i in order:
        if sc[i] < 0.6 or len(picked) >= n_max:
            break
        s = words[i]["start"]
        if s < 1.0 or s > dur - 1.0 or any(abs(s - q["t"]) < gap for q in picked):
            continue
        g = groups[words[i]["g"]]
        fin = min(dur - 0.2, max(words[i]["end"] + 0.5, min(g["end"] + 0.25, s + 1.8)))  # jusqu'à la fin du groupe dit
        picked.append({"t": round(max(0.0, s - 0.04), 3), "fin": round(fin, 3), "mot": w_clean(words[i]["w"]), "score": round(float(sc[i]), 2)})
    picked.sort(key=lambda q: q["t"])
    for k, q in enumerate(picked):
        q["kind"] = "sec" if k % 2 == 0 else "glisse"
    return picked


def w_clean(w):
    return w.strip(" ,.;:!?…")


def zoom_js(events, sel="#zm", amount=0.12):
    """Lignes GSAP : « sec » = saut immédiat et retour sec ; « glissé » = resserrement rapide puis retour doux."""
    js = []
    for e in events:
        t, f = e["t"], e["fin"]
        if e["kind"] == "sec":
            js.append(f'  tl.set("{sel}", {{ scale: {1 + amount} }}, {t});')
            js.append(f'  tl.set("{sel}", {{ scale: 1 }}, {f});')
        else:
            js.append(f'  tl.fromTo("{sel}", {{ scale: 1 }}, {{ scale: {round(1 + amount * 0.75, 3)}, duration: 0.32, ease: "power3.out", immediateRender: false }}, {t});')
            js.append(f'  tl.to("{sel}", {{ scale: 1, duration: 0.35, ease: "power2.inOut" }}, {round(max(t + 0.35, f - 0.35), 3)});')
    return js


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("job")
    ap.add_argument("slug")
    ap.add_argument("--par-minute", type=float, default=8.0)
    a = ap.parse_args()
    ev = strong_words(job_dir(a.job), a.slug, a.par_minute)
    out(ok=True, zooms=len(ev), mots=[f'{e["t"]} s « {e["mot"]} » ({e["kind"]}, {e["score"]})' for e in ev],
        suite="build_composition.py <job> <slug> --zooms")


if __name__ == "__main__":
    main()

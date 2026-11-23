"""ANALYSE D'UN REEL QUI MARCHE -> son rythme mesuré, puis appliqué à un montage.

  python reference.py analyse <lien Instagram / TikTok / YouTube | fichier vidéo> [--nom ref1]
        -> jobs/_references/<nom>/ : video.mp4, profil.json, planche.jpg (1 image par seconde, à REGARDER)
  python reference.py synthese          # toutes les références : accroches, dispositifs, fins, ce qui manque au skill
  python reference.py apply <job> <slug> --ref <nom>
        -> le rythme de la référence dans jobs/<job>/config.json ("pacing") et le plan de montage (durées des plans)

Mesures (outils, jamais à l'œil) : durée, format, plans (changements d'image confirmés par couleur ET structure,
comme qa.py), durée médiane / plus courte / plus longue d'un plan, coupes par minute, instant de la 1re coupe (fin de
l'accroche), parole (local, faster-whisper : 1er mot, mots par seconde, part de parole, langue), musique (tempo, part
des coupes posées sur un temps), volume (LUFS), mouvement dans l'image.
Ce que l'outil ne mesure pas (texte à l'écran, style des sous-titres, accroche visuelle, ton) : Claude le lit sur
planche.jpg et le note dans profil.json ("lecture") avant d'appliquer. On s'inspire du RYTHME, jamais du contenu :
pas d'images, de musique, de textes ni de marque copiés de la référence (droits d'auteur). La vidéo téléchargée sert
seulement à l'analyse et reste dans jobs/_references/ (jamais livrée ni publiée).
"""
import argparse
import json
import re
import subprocess
from pathlib import Path

import numpy as np

from common import ROOT, fail, job_dir, out, read_json, write_json

REFS = ROOT / "jobs" / "_references"


def fetch(src, d):
    v = d / "video.mp4"
    if v.exists():
        return v
    p = Path(src)
    if p.exists():
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(p), "-c", "copy", str(v)], check=True)
        return v
    r = subprocess.run(["yt-dlp", "-q", "--no-playlist", "-f", "bv*[height<=1920]+ba/b", "--merge-output-format", "mp4",
                        "-o", str(v), src], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0 or not v.exists():
        fail("téléchargement impossible (lien privé, supprimé, ou connexion demandée) : télécharge la vidéo et donne le fichier",
             detail=(r.stderr or "")[-400:])
    return v


def vinfo(v):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height,r_frame_rate:format=duration",
                        "-of", "json", str(v)], capture_output=True, text=True)
    d = json.loads(r.stdout)
    vs = next(s for s in d["streams"] if s["codec_type"] == "video")
    n, k = vs["r_frame_rate"].split("/")
    return {"duree": round(float(d["format"]["duration"]), 2), "largeur": vs["width"], "hauteur": vs["height"],
            "ips": round(float(n) / float(k), 2), "son": any(s["codec_type"] == "audio" for s in d["streams"])}


def cuts(v, dur):
    """Changements de plan confirmés (palette ET structure), les éclairs de coupe fusionnés."""
    from qa import ff, is_cut
    log = ff(["-i", str(v), "-an", "-vf", "scdet=threshold=10"])
    cand = [float(x) for x in re.findall(r"lavfi\.scd\.time:\s*([\d.]+)", log)]
    ts = []
    for t in cand:
        if ts and t - ts[-1] < 0.15:
            continue
        if 0.1 < t < dur - 0.1 and is_cut(v, t):
            ts.append(round(t, 2))
    return ts


def speech(v):
    """Mots horodatés (langue détectée), sur le CPU."""
    import os
    from faster_whisper import WhisperModel
    p = subprocess.run(["ffmpeg", "-v", "error", "-i", str(v), "-vn", "-ac", "1", "-ar", "16000", "-f", "f32le", "-"], capture_output=True)
    a = np.frombuffer(p.stdout, dtype=np.float32)
    if not len(a):
        return [], None
    m = WhisperModel("large-v3-turbo", device="cpu", compute_type="int8", cpu_threads=os.cpu_count() or 4)
    segs, info = m.transcribe(a, word_timestamps=True, condition_on_previous_text=False, vad_filter=True)
    words = [{"w": w.word.strip(), "start": round(float(w.start), 2), "end": round(float(w.end), 2)}
             for s in segs for w in (s.words or []) if w.word.strip()]
    return words, info.language


def music(v, cut_ts):
    try:
        import librosa
        sr = 22050  # décodé par ffmpeg (librosa ne lit pas toujours le son d'un mp4)
        pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", str(v), "-vn", "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"], capture_output=True).stdout
        y = np.frombuffer(pcm, dtype=np.float32).copy()
        tempo, frames = librosa.beat.beat_track(y=y, sr=sr)
        beats = librosa.frames_to_time(frames, sr=sr)
    except Exception:  # noqa: BLE001
        return None, None
    tempo = float(np.atleast_1d(tempo)[0])
    if not len(beats) or not cut_ts:
        return round(tempo), None
    on = sum(1 for c in cut_ts if np.min(np.abs(beats - c)) < 0.12)
    return round(tempo), round(on / len(cut_ts), 2)


def loudness(v):
    from qa import loudness as ld
    return ld(v)[0]


def planche(v, d, dur):
    n = max(1, int(dur))
    cols = 8
    rows = (n + cols - 1) // cols
    dst = d / "planche.jpg"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(v), "-vf",
                    f"fps=1,scale=180:-2,drawtext=fontfile='C\\:/Windows/Fonts/arialbd.ttf':text='%{{eif\\:t\\:d}} s':x=6:y=6:fontsize=18:fontcolor=white:box=1:boxcolor=black@0.6,"
                    f"tile={cols}x{rows}", "-frames:v", "1", "-q:v", "3", str(dst)], check=True)
    return dst


def analyse(src, nom):
    nom = nom or re.sub(r"\W+", "-", Path(src).stem if Path(src).exists() else src.rstrip("/").split("/")[-1] or "ref")[:30]
    d = REFS / nom
    d.mkdir(parents=True, exist_ok=True)
    v = fetch(src, d)
    info = vinfo(v)
    dur = info["duree"]
    ct = cuts(v, dur)
    bounds = [0.0] + ct + [dur]
    shots = np.diff(bounds)
    from footage import motion_profile
    mot = motion_profile(v, 0, dur, fps=5)
    words, lang = speech(v) if info["son"] else ([], None)
    talk = sum(w["end"] - w["start"] for w in words)
    tempo, on_beat = music(v, ct) if info["son"] else (None, None)
    prof = {
        "source": src, "video": info,
        "plans": {"nombre": len(shots), "coupes_par_minute": round(len(ct) / dur * 60, 1),
                  "duree_mediane": round(float(np.median(shots)), 2), "plus_court": round(float(shots.min()), 2),
                  "plus_long": round(float(shots.max()), 2), "premiere_coupe": ct[0] if ct else None, "coupes": ct},
        "parole": {"langue": lang, "premier_mot": words[0]["start"] if words else None,
                   "mots_par_seconde": round(len(words) / talk, 2) if talk else None,
                   "part_de_parole": round(talk / dur, 2), "debut": " ".join(w["w"] for w in words if w["start"] < 3.5)[:200]},
        "musique": {"tempo_bpm": tempo, "coupes_sur_le_temps": on_beat},
        "volume_lufs": loudness(v),
        "mouvement_moyen": round(float(mot.mean()), 2) if len(mot) else None,
        "grammaire": {"_a_remplir_par_claude": "le MÉCANISME, pas l'anecdote : accroche {type, mecanisme, duree_s}, structure, "
                      "dispositifs [liste réutilisable], rythme {changement_visuel_s, cale_sur}, texte, fin {type, mecanisme}, a_retenir [leçons]"},
        "lecture": {"_a_remplir_par_claude": "regarde planche.jpg : texte à l'écran (où, combien, style des sous-titres), "
                    "accroche visuelle des 2 premières secondes, effets (zooms, emojis, transitions), ton"},
    }
    write_json(d / "profil.json", prof)
    sheet = planche(v, d, dur)
    out(ok=True, dossier=str(d), planche=str(sheet), duree=dur, plans=prof["plans"]["nombre"],
        coupes_par_minute=prof["plans"]["coupes_par_minute"], plan_median=prof["plans"]["duree_mediane"],
        premiere_coupe=prof["plans"]["premiere_coupe"], premier_mot=prof["parole"]["premier_mot"],
        mots_par_seconde=prof["parole"]["mots_par_seconde"], tempo=tempo, coupes_sur_le_temps=on_beat,
        suite="regarde planche.jpg, complète \"lecture\" dans profil.json, puis reference.py apply <job> <slug> --ref " + nom)


def apply(job_name, slug, nom):
    pj = REFS / nom / "profil.json"
    if not pj.exists():
        fail(f"référence inconnue : lance d'abord reference.py analyse … --nom {nom}")
    pr = read_json(pj)
    job = job_dir(job_name)
    cpm = pr["plans"]["coupes_par_minute"]
    med = pr["plans"]["duree_mediane"]
    shot = round(min(4.0, max(1.2, med)), 2)  # jamais sous 1,2 s (règle des plans trop courts)
    cfg_p = job / "config.json"
    cfg = read_json(cfg_p) if cfg_p.exists() else {}
    # rush face caméra : les coupes de la référence deviennent des changements visuels (zooms, plans de coupe, blocs)
    zpm = round(min(14, max(4, cpm * 0.5)), 1)
    cfg.setdefault("camera", {})
    cfg["camera"].update({"zooms": cpm >= 12, "zoomsPerMinute": zpm})
    cfg["pacing"] = {"reference": nom, "plan_s": shot, "changements_par_minute": cpm, "premiere_coupe": pr["plans"]["premiere_coupe"],
                     "tempo_bpm": pr["musique"]["tempo_bpm"], "lecture": pr.get("lecture", {})}
    lec = pr.get("lecture") or {}
    done = [f"zooms : {'oui' if cpm >= 12 else 'non'} ({zpm}/min)"]
    # ce que Claude a lu sur la planche (clés structurées de "lecture") : mise en page, sous-titres, mots par groupe
    if lec.get("mise_en_page") in ("full", "split", "cards"):
        cfg.setdefault("visual", {})["layout"] = lec["mise_en_page"]
        done.append(f"mise en page : {lec['mise_en_page']}")
    if lec.get("sous_titres"):
        cfg.setdefault("text", {})["captionStyle"] = lec["sous_titres"]
        done.append(f"sous-titres : style {lec['sous_titres']}")
    if lec.get("mots_par_groupe"):
        cfg.setdefault("text", {})["captionMaxWords"] = int(lec["mots_par_groupe"])
        done.append(f"sous-titres : {int(lec['mots_par_groupe'])} mots au plus par groupe")
    write_json(cfg_p, cfg)
    for kind in ("footage", "punch"):
        fp = job / "work" / f"{slug}_{kind}.json"
        if not fp.exists():
            continue
        plan = read_json(fp)
        items = plan.get("items") if kind == "footage" else plan.get("beats", plan if isinstance(plan, list) else [])
        n = 0
        for it in items or []:
            if isinstance(it, dict) and not it.get("timelapse") and "dur" in it or kind == "footage":
                if isinstance(it, dict) and not it.get("timelapse"):
                    it["dur"] = shot
                    n += 1
        write_json(fp, plan)
        done.append(f"{kind} : {n} plans à {shot} s")
    tempo = pr["musique"]["tempo_bpm"]
    mood = None
    if tempo:
        mood = "energetic" if tempo >= 125 else "upbeat" if tempo >= 105 else "inspiring" if tempo >= 85 else "chill"
        done.append(f"musique conseillée : --mood {mood} (référence à {tempo} bpm)")
    first = pr["plans"]["premiere_coupe"]
    if first:
        done.append(f"accroche : 1re coupe à {first} s dans la référence -> accroche de {round(min(3.0, max(1.2, first)), 1)} s")
    out(ok=True, reference=nom, applique=done, config=str(cfg_p),
        suite="reconstruis (build_*.py), puis check + snapshot ; le contenu reste le tien, seul le rythme est repris")


# dispositifs repérés dans les références -> ce que le skill sait déjà faire (mots-clés -> capacité)
CAPACITES = [
    (("série numérotée", "liste numérotée", "épisode"), "liste « 1 sur 5 » / série (panel list, footage series)"),
    (("alternance",), None),
    (("écran partagé", "split"), "écran partagé (layout split)"),
    (("illustration", "plan d'ambiance", "b-roll", "banque d'images"), "plans de coupe (broll.py)"),
    (("piles de cartes", "cartes"), "piles de cartes d'outils (tools_stack)"),
    (("commentaire", "commente"), "fin « Commente : MOT » (bloc commente-mot)"),
    (("sans parole",), None),
    (("bulles de texte", "bulle"), None),
    (("maquette",), "maquettes d'interface (panel ui)"),
    (("avant / après", "avant-après"), "avant / après (compare)"),
    (("zoom",), "zooms sur les mots forts"),
    (("titre derrière",), "titre derrière la personne (cutout)"),
]


def synthese():
    """Vue d'ensemble de toutes les références analysées : accroches, dispositifs, fins, rythme, et ce qui manque au
    skill. C'est ce recul (plusieurs reels qui marchent) qui décide des prochains développements, pas un cas isolé."""
    profs = [(p.parent.name, read_json(p)) for p in sorted(REFS.glob("*/profil.json"))]
    gs = [(n, p.get("grammaire")) for n, p in profs if p.get("grammaire")]
    if not gs:
        fail("aucune référence avec \"grammaire\" remplie (analyse, puis Claude remplit grammaire dans profil.json)")
    from collections import Counter
    disp = Counter(d for _, g in gs for d in g.get("dispositifs", []))
    rows = []
    for d, n in disp.most_common():
        cap = next((c for keys, c in CAPACITES if any(k in d.lower() for k in keys)), "?")
        rows.append({"dispositif": d, "references": n, "skill": cap or "MANQUE"})
    res = {
        "references": len(gs),
        "accroches": Counter(g["accroche"]["type"] for _, g in gs if g.get("accroche")).most_common(),
        "duree_accroche_s": round(sum(g["accroche"].get("duree_s", 0) for _, g in gs) / len(gs), 1),
        "fins": Counter(g["fin"]["type"] for _, g in gs if g.get("fin")).most_common(),
        "rythme_s": [g.get("rythme", {}).get("changement_visuel_s") for _, g in gs],
        "dispositifs": rows,
        "manques": [r["dispositif"] for r in rows if r["skill"] in ("MANQUE", "?")],
        "lecons": [l for _, g in gs for l in g.get("a_retenir", [])],
    }
    write_json(REFS / "synthese.json", res)
    out(ok=True, **res, fichier=str(REFS / "synthese.json"))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a1 = sub.add_parser("analyse")
    a1.add_argument("src")
    a1.add_argument("--nom")
    sub.add_parser("synthese")
    a2 = sub.add_parser("apply")
    a2.add_argument("job")
    a2.add_argument("slug")
    a2.add_argument("--ref", required=True)
    a = ap.parse_args()
    if a.cmd == "analyse":
        analyse(a.src, a.nom)
    elif a.cmd == "synthese":
        synthese()
    else:
        apply(a.job, a.slug, a.ref)


if __name__ == "__main__":
    main()

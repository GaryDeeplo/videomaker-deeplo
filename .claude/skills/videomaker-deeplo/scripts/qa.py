"""CONTRÔLE QUALITÉ d'un rendu, avant de le montrer : ce qu'un œil attentif repère, mesuré.

  python qa.py <job> <slug> [--video renders/x.mp4]     # défaut : le rendu le plus récent du job

Vérifie (mesures ffmpeg + sous-titres du slug) :
  - plans trop courts (< 0,8 s entre deux changements d'image ; les éclairs de coupe sont ignorés) ;
  - images noires (> 0,15 s) et images figées longues (> 3 s, souvent une vidéo trop courte pour son plan) ;
  - volume : -14 LUFS ± 1,5 attendu après finalize / livraison, pic < -1 dB ; trous de son (> 1,2 s de silence
    dans une vidéo parlée) ;
  - sous-titres : groupes affichés moins de 0,5 s ou lus trop vite (> 22 caractères par seconde) ;
  - durée par rapport au brief (work/brief.json), si elle y est.
Sortie : verdict « OK » ou « à revoir » + la liste des points avec leurs instants. À lancer sur l'aperçu, avant de le
montrer (les points « info » n'empêchent rien, les « à revoir » se corrigent d'abord).
"""
import argparse
import re
import subprocess
from pathlib import Path

from common import job_dir, out, read_json


def ff(args):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", *args, "-f", "null", "-"], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return r.stderr


def duration(v):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(v)],
                       capture_output=True, text=True)
    return float(r.stdout.strip() or 0)


def frame_hist(v, t):
    import cv2
    import numpy as np
    r = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{max(0, t):.3f}", "-i", str(v), "-frames:v", "1", "-vf", "scale=96:-2",
                        "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True)
    img = cv2.imdecode(np.frombuffer(r.stdout, np.uint8), cv2.IMREAD_COLOR) if r.stdout else None
    if img is None:
        return None
    h = cv2.calcHist([cv2.cvtColor(img, cv2.COLOR_BGR2HSV)], [0, 1], None, [24, 16], [0, 180, 0, 256])
    small = cv2.resize(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), (16, 28), interpolation=cv2.INTER_AREA).astype("float32").flatten()
    return cv2.normalize(h, h).flatten(), small


def is_cut(v, t):
    """Vraie coupe : les couleurs de toute l'image changent (un titre ou un objet qui arrive n'en change qu'une partie).
    On compare avant l'instant et après l'éventuel éclair blanc."""
    import cv2
    import numpy as np
    a_, b_ = frame_hist(v, t - 0.1), frame_hist(v, t + 0.2)
    if a_ is None or b_ is None:
        return True
    colors = cv2.compareHist(a_[0], b_[0], cv2.HISTCMP_CORREL)
    shape = float(np.corrcoef(a_[1], b_[1])[0, 1]) if a_[1].std() and b_[1].std() else 0.0
    return colors < 0.9 and shape < 0.75  # palette ET structure changent : c'est une coupe


def shots(v, dur):
    log = ff(["-i", str(v), "-an", "-vf", "scdet=threshold=10"])
    cand = [float(x) for x in re.findall(r"lavfi\.scd\.time:\s*([\d.]+)", log)]
    ts = []
    for t in cand:
        if ts and t - ts[-1] < 0.15:  # l'éclair de coupe donne deux détections collées
            continue
        if is_cut(v, t):
            ts.append(t)
    cuts = [0.0] + ts + [dur]
    segs = [(a, b - a) for a, b in zip(cuts, cuts[1:])]
    # un éclair de coupe (< 0,12 s) n'est pas un plan : on le rattache au plan suivant
    merged = []
    for a, d in segs:
        if merged and d < 0.12:
            continue
        merged.append((a, d))
    return len(ts), [(round(a, 2), round(d, 2)) for a, d in merged[1:-1] if d < 0.8]


def blacks(v):
    log = ff(["-i", str(v), "-an", "-vf", "blackdetect=d=0.15:pix_th=0.08"])
    return [(round(float(a), 2), round(float(d), 2)) for a, d in re.findall(r"black_start:([\d.]+).*?black_duration:([\d.]+)", log)]


def freezes(v):
    log = ff(["-i", str(v), "-an", "-vf", "freezedetect=n=-55dB:d=3"])
    return [(round(float(a), 2), round(float(d), 2)) for a, d in
            re.findall(r"freeze_start:\s*([\d.]+)[\s\S]*?freeze_duration:\s*([\d.]+)", log)]


def loudness(v):
    log = ff(["-i", str(v), "-vn", "-af", "ebur128=peak=true"])
    i = re.findall(r"I:\s*(-?[\d.]+) LUFS", log)
    p = re.findall(r"Peak:\s*(-?[\d.]+) dBFS", log)
    return (float(i[-1]) if i else None), (float(p[-1]) if p else None)


def silences(v):
    log = ff(["-i", str(v), "-vn", "-af", "silencedetect=noise=-45dB:d=1.2"])
    return [(round(float(a), 2), round(float(d), 2)) for a, d in re.findall(r"silence_start:\s*([\d.]+)[\s\S]*?silence_duration:\s*([\d.]+)", log)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("job")
    ap.add_argument("slug")
    ap.add_argument("--video")
    a = ap.parse_args()
    job = job_dir(a.job)
    if a.video:
        v = Path(a.video) if Path(a.video).is_absolute() else job / a.video
    else:
        cands = sorted((job / "renders").rglob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not cands:
            out(ok=False, erreur="aucun rendu : lance d'abord un aperçu (render -q draft)")
            return
        v = cands[0]
    dur = duration(v)
    pts = []  # (niveau, quoi, détail)
    n_cuts, short = shots(v, dur)
    for t, d in short:
        pts.append(("à revoir", "plan trop court", f"{d} s à {t} s"))
    for t, d in blacks(v):
        if t > 0.2 and t + d < dur - 0.3:  # fondu au noir d'ouverture ou de fin : normal
            pts.append(("à revoir", "image noire", f"{d} s à {t} s"))
    for t, d in freezes(v):
        pts.append(("info", "image figée", f"{d} s à {t} s (vidéo trop courte pour son plan ? ou plan fixe voulu)"))
    work = job / "work"
    spoken = (work / f"{a.slug}_text.json").exists()
    lufs, peak = loudness(v)
    is_final = "livraison" in v.parts or v.stem.endswith("_final")
    if lufs is not None and is_final and abs(lufs + 14) > 1.5:
        pts.append(("à revoir", "volume", f"{lufs} LUFS (attendu -14 ± 1,5)"))
    elif lufs is not None and lufs < -30:
        pts.append(("à revoir", "volume", f"{lufs} LUFS : presque muet"))
    if peak is not None and peak > -0.5:
        pts.append(("à revoir", "saturation", f"pic à {peak} dBFS"))
    if spoken:
        for t, d in silences(v):
            if t > 0.5 and t + d < dur - 0.8:
                pts.append(("info", "trou de son", f"{d} s de silence à {t} s"))
        tx = read_json(work / f"{a.slug}_text.json")
        caps = tx.get("captions", [])
        for gi, g in enumerate(caps):
            ws = g.get("words", [])
            if not ws:
                continue
            nxt = caps[gi + 1]["start"] if gi + 1 < len(caps) else dur
            gd = max(0.01, min(nxt, g["end"] + 0.6) - g["start"])  # temps où le groupe reste affiché
            chars = len(" ".join(w["w"] for w in ws))
            if gd < 0.5 and len(ws) > 1:
                pts.append(("info", "sous-titre éclair", f"« {' '.join(w['w'] for w in ws)} » {gd:.2f} s à {g['start']:.1f} s"))
            elif chars / gd > 22:
                pts.append(("à revoir", "sous-titre trop rapide", f"« {' '.join(w['w'] for w in ws)} » {chars / gd:.0f} car/s à {g['start']:.1f} s"))
    bj = work / "brief.json"
    if bj.exists():
        m = re.search(r"\d+", str(read_json(bj).get("duree", "")))
        if m and abs(dur - int(m.group())) > max(5, int(m.group()) * 0.35):
            pts.append(("info", "durée", f"{dur:.1f} s pour un brief de {m.group()} s"))
    bad = [p for p in pts if p[0] == "à revoir"]
    out(ok=True, video=str(v.relative_to(job)), duree=round(dur, 2), plans=n_cuts + 1, lufs=lufs, pic=peak,
        verdict="OK" if not bad else "à revoir", a_revoir=[f"{q} : {d}" for _, q, d in bad][:20],
        infos=[f"{q} : {d}" for lvl, q, d in pts if lvl == "info"][:20])


if __name__ == "__main__":
    main()

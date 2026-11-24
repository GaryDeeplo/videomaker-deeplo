"""CONTRÔLE QUALITÉ d'un rendu, avant de le montrer : ce qu'un œil attentif repère, mesuré.

  python qa.py <job> <slug> [--video renders/x.mp4]     # défaut : le rendu le plus récent du job

Vérifie (mesures ffmpeg + sous-titres du slug) :
  - plans trop courts (< 0,8 s entre deux changements d'image ; les éclairs de coupe sont ignorés) ;
  - images noires (> 0,15 s) et images figées longues (> 3 s, souvent une vidéo trop courte pour son plan) ;
  - volume : -14 LUFS ± 1,5 attendu après finalize / livraison, pic < -1 dB ; trous de son (> 1,2 s de silence
    dans une vidéo parlée) ;
  - sous-titres : groupes affichés moins de 0,5 s ou lus trop vite (> 32 caractères par seconde : les sous-titres
    sont calés mot à mot, on les lit au rythme de la voix ; 25 à 32 = info) ;
  - durée par rapport au brief (work/brief.json), si elle y est ;
  - contenu (d'après ffmpeg-skill, MIT) : micro-coupures du son (silence numérique de 20 ms à 1 s entre deux sons
    francs = à revoir ; s'il est amené en douceur = info, blanc voulu ?), image isolée qui saute (info : nos éclairs de
    transition sont voulus), première image unie (info : le fil d'actualité la montre) ;
  - conformité du fichier livré (--format, ou d'après le nom dans renders/livraison) : h264 yuv420p, taille exacte,
    cadence fixe attendue (--fps, 30), AAC 48 kHz stéréo, son et image de même longueur, BT.709, poids.
Sortie : verdict « OK » ou « à revoir » + la liste des points avec leurs instants. À lancer sur l'aperçu, avant de le
montrer (les points « info » n'empêchent rien, les « à revoir » se corrigent d'abord).
"""
import argparse
import re
import subprocess
from pathlib import Path

from common import FORMATS, job_dir, out, probe, read_json


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


def dropouts(v, dur):
    """Micro-coupures : silence numérique (< -80 dB) de 20 ms à 1 s à l'intérieur du son (un blanc de parole garde le
    souffle de la pièce, bien au-dessus). Son prolongé de 2 s de zéros : une fin muette n'est jamais comptée. D'après
    ffmpeg-skill (MIT), scripts/_common/probe.py _detect_dropouts. Renvoie [(début, fin, brutale)] : brutale = du son
    franc des deux côtés (coupure nette, pas un fondu ni une pause voulue)."""
    log = ff(["-i", str(v), "-map", "0:a:0", "-af", "apad=pad_dur=2,silencedetect=noise=-80dB:d=0.02"])
    gaps, start = [], None
    for kind, val in re.findall(r"silence_(start|end):\s*(-?[\d.]+)", log):
        if kind == "start":
            start = float(val)
        elif start is not None:
            s, e, start = start, float(val), None
            if s > 0.05 and e < dur - 0.05 and 0.02 <= e - s <= 1.0:
                gaps.append((s, e))
    if not gaps:
        return []
    import numpy as np
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(v), "-map", "0:a:0", "-ac", "1", "-ar", "8000", "-f", "s16le", "-"],
                       capture_output=True)
    x = np.frombuffer(r.stdout, np.int16).astype(np.float32) / 32768

    def rms_db(a, b):  # niveau (dBFS) entre a et b secondes
        seg = x[max(0, int(a * 8000)):max(0, int(b * 8000))]
        return 20 * np.log10(float(np.sqrt(np.mean(seg ** 2))) + 1e-9) if len(seg) else -120.0
    return [(round(s, 2), round(e, 2), bool(rms_db(s - 0.03, s - 0.005) > -45 and rms_db(e + 0.005, e + 0.03) > -45))
            for s, e in gaps]


FLASH_JUMP, FLASH_RETURN, FLAT_STD = 12.0, 0.25, 4.0  # seuils de ffmpeg-skill (luma 0-255 sur 64 × 36)


def flashes(v):
    """Images isolées : l'image n diffère de n-1 et de n+1 (≥ 12 de luma moyenne) alors que n-1 et n+1 se ressemblent.
    Une passe ffmpeg réduit chaque image à 3 nombres de 16 bits. D'après ffmpeg-skill (MIT), scripts/_common/probe.py
    detect_flashes. Renvoie les numéros d'image, ou None si la passe échoue."""
    graph = ("[0:v:0]scale=64:36:flags=area,format=gray16le,split=3[a][b][c];"
             "[a]tblend=all_mode=difference,scale=1:1:flags=area[d];"
             "[b]tmix=frames=3:weights='-1 0 1':scale=1,scale=1:1:flags=area[p];"
             "[c]tmix=frames=3:weights='1 0 -1':scale=1,scale=1:1:flags=area[q];"
             "[d][p][q]hstack=inputs=3")
    r = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(v), "-filter_complex", graph,
                        "-fps_mode", "passthrough", "-f", "rawvideo", "-"], capture_output=True)
    if r.returncode != 0 or len(r.stdout) < 6:
        return None
    data = bytes(6) + r.stdout  # tblend ne sort rien pour l'image 0 : l'enregistrement i est l'image i
    n = len(data) // 6

    def rec(i):  # (|f[i] - f[i-1]|, |f[i] - f[i-2]|)
        d, p, q = (int.from_bytes(data[i * 6 + k:i * 6 + k + 2], "little") / 256.0 for k in (0, 2, 4))
        return d, p + q
    found, into = [], (rec(1)[0] if n > 1 else 0.0)
    for i in range(1, n - 1):
        out_, back = rec(i + 1)
        if into >= FLASH_JUMP and out_ >= FLASH_JUMP and back <= FLASH_RETURN * min(into, out_):
            found.append(i)
        into = out_
    return found


def first_frame(v):
    """(moyenne, écart type) de la luma de la première image (64 × 36), None si elle ne se décode pas. D'après
    ffmpeg-skill (MIT), first_frame_stats."""
    import statistics
    r = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(v), "-map", "0:v:0", "-frames:v", "1",
                        "-vf", "scale=64:36:flags=area,format=gray", "-f", "rawvideo", "-"], capture_output=True)
    px = list(r.stdout[:64 * 36])
    if r.returncode != 0 or len(px) < 64 * 36:
        return None
    return statistics.fmean(px), statistics.pstdev(px)


def conformite(video, fmt, fps=None):
    """Fichier livré conforme aux plateformes (Reels, TikTok, Shorts, LinkedIn) : H.264 yuv420p, taille exacte du
    format, cadence fixe attendue, AAC 48 kHz stéréo, son et image de même longueur, couleurs BT.709, poids.
    D'après ffmpeg-skill (MIT), scripts/check.py et _platforms.py. Renvoie [(niveau, quoi, détail)] comme main()."""
    pts, p = [], probe(video)
    want_fps = float(fps or 30)
    if p.get("codec") != "h264":
        pts.append(("à revoir", "codec vidéo", f"{p.get('codec')} (attendu h264 : lu partout)"))
    if p.get("pix_fmt") != "yuv420p":
        pts.append(("à revoir", "format de pixels", f"{p.get('pix_fmt')} (attendu yuv420p : iOS et QuickTime refusent le reste)"))
    if fmt in FORMATS and (p["width"], p["height"]) != FORMATS[fmt]:
        pts.append(("à revoir", "taille", f"{p['width']}×{p['height']} (attendu {FORMATS[fmt][0]}×{FORMATS[fmt][1]} pour {fmt})"))
    if p.get("rotation"):
        pts.append(("à revoir", "rotation", f"{p['rotation']}° dans les métadonnées (certains lecteurs l'ignorent)"))
    if p.get("vfr"):
        pts.append(("à revoir", "cadence", f"variable ({p.get('fps_nominal')} nominale, {p.get('fps')} moyenne)"))
    elif not p.get("fps") or abs(p["fps"] - want_fps) > 0.01:
        pts.append(("à revoir", "cadence", f"{p.get('fps')} i/s (attendu {want_fps:g})"))
    au = p.get("audio")
    if not au:
        pts.append(("à revoir", "son", "aucune piste audio"))
    else:
        if au.get("codec") != "aac" or au.get("sample_rate") != 48000 or au.get("channels") != 2:
            pts.append(("à revoir", "son", f"{au.get('codec')} {au.get('sample_rate')} Hz {au.get('channels')} canal(aux) "
                                           "(attendu AAC 48 kHz stéréo)"))
        vd, ad = p.get("video_duration"), au.get("duration")
        if vd and ad and round(abs(ad - vd), 3) >= 0.1:
            pts.append(("à revoir", "durées son / image", f"son {ad:.2f} s, image {vd:.2f} s (écart ≥ 0,1 s)"))
    col = p.get("color") or {}
    tags = [col.get(k) for k in ("primaries", "transfer", "space")]
    if p.get("hdr"):
        pts.append(("à revoir", "couleurs", f"{p.get('hdr_format')} : délavé sur les plateformes, livrer en SDR BT.709"))
    elif all(t == "bt709" for t in tags):
        pass
    elif all(t in (None, "unknown") for t in tags):
        pts.append(("info", "couleurs", "non balisées (les lecteurs supposent BT.709)"))
    else:
        pts.append(("à revoir", "couleurs", f"balises {'/'.join(str(t) for t in tags)} (attendu bt709)"))
    size = Path(video).stat().st_size
    if size > 4 * 1024 ** 3:
        pts.append(("à revoir", "poids", f"{size / 1e9:.1f} Go (> 4 Go, limite Reels / TikTok)"))
    elif size > 250e6:
        pts.append(("info", "poids", f"{size / 1e6:.0f} Mo : lourd à envoyer par messagerie"))
    return pts


def verdict_of(pts):
    """Même résumé que le contrôle principal : verdict, points à revoir, infos."""
    bad = [f"{q} : {d}" for lvl, q, d in pts if lvl == "à revoir"]
    return {"verdict": "OK" if not bad else "à revoir", "a_revoir": bad[:20],
            "infos": [f"{q} : {d}" for lvl, q, d in pts if lvl == "info"][:20]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("job")
    ap.add_argument("slug")
    ap.add_argument("--video")
    ap.add_argument("--format", help="contrôle de conformité du fichier livré (9:16, 1:1…) ; défaut : d'après le nom "
                                     "(<slug>_9x16.mp4) pour un fichier de renders/livraison")
    ap.add_argument("--fps", type=float, help="cadence attendue pour la conformité (défaut 30)")
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
    info = probe(v)
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
        cqf = work / f"{a.slug}_calques.json"  # composition sans sous-titres (mots dynamiques…) : rien à juger
        if cqf.exists() and not any(c_.get("type") == "sous-titre" for c_ in read_json(cqf).get("calques", [])):
            caps = []
        for gi, g in enumerate(caps):
            ws = g.get("words", [])
            if not ws:
                continue
            nxt = caps[gi + 1]["start"] if gi + 1 < len(caps) else dur
            gd = max(0.01, min(nxt, g["end"] + 0.6) - g["start"])  # temps où le groupe reste affiché
            chars = len(" ".join(w["w"] for w in ws))
            if gd < 0.5 and len(ws) > 1:
                pts.append(("info", "sous-titre éclair", f"« {' '.join(w['w'] for w in ws)} » {gd:.2f} s à {g['start']:.1f} s"))
            elif chars / gd > 32:  # sous-titres calés mot à mot : on lit au rythme de la voix ; au-delà de 32 car/s, illisible
                pts.append(("à revoir", "sous-titre trop rapide", f"« {' '.join(w['w'] for w in ws)} » {chars / gd:.0f} car/s à {g['start']:.1f} s"))
            elif chars / gd > 25:
                pts.append(("info", "sous-titre rapide", f"« {' '.join(w['w'] for w in ws)} » {chars / gd:.0f} car/s à {g['start']:.1f} s (débit de la voix)"))
    if info["has_audio"]:
        dro = dropouts(v, dur)
        for s, e, brutal in dro:
            if brutal:  # son franc juste avant et juste après : un trou, pas une pause
                pts.append(("à revoir", "micro-coupure du son", f"{round(e - s, 2)} s de silence absolu à {s} s"))
        calm = [f"{s} s" for s, e, brutal in dro if not brutal]
        if calm:
            pts.append(("info", "silence absolu", f"{len(calm)} fois ({', '.join(calm[:5])}{' …' if len(calm) > 5 else ''}) : "
                                                 "blanc voulu ? un vrai blanc garde un peu de fond"))
    fl = flashes(v)
    if fl:
        rate = info.get("fps") or 30
        at = ", ".join(f"{i / rate:.2f} s" for i in fl[:5]) + (" …" if len(fl) > 5 else "")
        pts.append(("info", "image isolée", f"{len(fl)} ({at}) : éclair de transition voulu, ou image restée à une coupe ?"))
    ff0 = first_frame(v)
    if ff0 and ff0[1] < FLAT_STD:
        pts.append(("info", "première image unie", f"luma {ff0[0]:.0f} : le fil d'actualité la montre avant la lecture "
                                                   "(commencer sur une image, ou soigner la couverture)"))
    fmt = a.format
    m = re.search(r"_(\d+)x(\d+)(?:_|$)", v.stem)
    if not fmt and m and "livraison" in str(v.parent.name):
        fmt = f"{m.group(1)}:{m.group(2)}"
    conf = None
    if fmt in FORMATS:
        conf_pts = conformite(v, fmt, a.fps)
        pts += conf_pts
        conf = verdict_of(conf_pts)["verdict"]
    bj = work / "brief.json"
    if bj.exists():
        m = re.search(r"\d+", str(read_json(bj).get("duree", "")))
        if m and abs(dur - int(m.group())) > max(5, int(m.group()) * 0.35):
            pts.append(("info", "durée", f"{dur:.1f} s pour un brief de {m.group()} s"))
    try:  # visage couvert par un calque (face.py, positions écrites par build_composition)
        from face import couverture
        pts += couverture(job, a.slug)
    except Exception as e:  # noqa: BLE001
        pts.append(("info", "visage couvert", f"contrôle impossible : {e}"))
    bad = [p for p in pts if p[0] == "à revoir"]
    out(ok=True, video=str(v.relative_to(job)) if v.is_relative_to(job) else str(v), duree=round(dur, 2), plans=n_cuts + 1,
        lufs=lufs, pic=peak, conformite=conf,
        verdict="OK" if not bad else "à revoir", a_revoir=[f"{q} : {d}" for _, q, d in bad][:20],
        infos=[f"{q} : {d}" for lvl, q, d in pts if lvl == "info"][:20])


if __name__ == "__main__":
    main()

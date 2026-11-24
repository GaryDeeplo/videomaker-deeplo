"""IMAGES SANS PAROLES (chantier, ambiance, plats, événement, produit, voyage) : repérer le meilleur de chaque clip.

  python footage.py scan <job> [--seg 3]          # mesure chaque vidéo de inbox/ -> work/footage.json + work/footage/planche.jpg
  python footage.py plan <job> <slug> [--duree 30] [--max 12]
                                                  # premier jet -> work/<slug>_footage.json (ordre chronologique, accélérés)

Mesures (outil, jamais deviné) : netteté, mouvement dans l'image, tremblement de la caméra, luminosité, part de voix
(détecteur de voix local), date de tournage. Pour chaque clip : les 3 meilleurs passages (nets, stables, un peu de
mouvement), et un accéléré possible si le clip est long et la caméra posée (time-lapse).
Dans le plan, Claude ne choisit que : garder ou non, l'ordre, le passage (n° mesuré), l'accéléré, l'étiquette (« JOUR 12 »,
« La cuisine ») et la durée à l'écran. Jamais un timecode. Ensuite : build_footage.py.
Un clip où l'on parle (« jour 12, on casse le mur ») passe plutôt par transcribe.py : ses mots servent de repères.
"""
import argparse
import datetime
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

from common import ROOT, fail, job_dir, out, read_json, rotation_of, write_json

VIDEO = {".mp4", ".mov", ".m4v", ".webm", ".mkv", ".avi"}
FPS = 4


def meta(src):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "stream=codec_type,width,height,r_frame_rate:stream_tags=rotate:stream_side_data_list:format=duration:format_tags=creation_time",
                        "-of", "json", str(src)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    d = json.loads(r.stdout or "{}")
    v = next((s for s in d.get("streams", []) if s.get("codec_type") == "video"), {})
    w, h = v.get("width") or 0, v.get("height") or 0
    if rotation_of(v) in (90, 270):  # tag « rotate » ou matrice d'affichage (téléphone en portrait, ffmpeg 6+)
        w, h = h, w
    ct = (d.get("format", {}).get("tags") or {}).get("creation_time")
    when = None
    if ct:
        try:
            when = datetime.datetime.fromisoformat(ct.replace("Z", "+00:00")).astimezone().replace(tzinfo=None)
        except ValueError:
            when = None
    if when is None or when.year < 2005:  # date absente ou fausse : date du fichier
        when = datetime.datetime.fromtimestamp(Path(src).stat().st_mtime)
    return {"duration": float(d.get("format", {}).get("duration") or 0), "width": w, "height": h,
            "has_audio": any(s.get("codec_type") == "audio" for s in d.get("streams", [])), "date": when.isoformat(timespec="minutes")}


def frames(src, width=192):
    """Images en niveaux de gris à FPS i/s (petites) pour les mesures."""
    p = subprocess.run(["ffmpeg", "-v", "error", "-i", str(src), "-vf", f"fps={FPS},scale={width}:-2,format=gray", "-f", "rawvideo", "-"],
                       capture_output=True)
    m = meta(src)
    h = round(m["height"] * width / max(1, m["width"]) / 2) * 2 or width
    n = len(p.stdout) // (width * h)
    return np.frombuffer(p.stdout[:n * width * h], dtype=np.uint8).reshape(n, h, width) if n else np.zeros((0, h, width), np.uint8)


def speech_ratio(src, dur):
    """Part du clip où quelqu'un parle (détecteur de voix Silero de faster-whisper ; bruit de machine ignoré)."""
    try:
        from faster_whisper.vad import VadOptions, get_speech_timestamps
    except Exception:  # noqa: BLE001
        return None
    p = subprocess.run(["ffmpeg", "-v", "error", "-i", str(src), "-ac", "1", "-ar", "16000", "-f", "f32le", "-"], capture_output=True)
    a = np.frombuffer(p.stdout, dtype=np.float32)
    if not len(a):
        return 0.0
    ts = get_speech_timestamps(a, VadOptions(min_silence_duration_ms=400))
    return round(sum(t["end"] - t["start"] for t in ts) / 16000 / max(0.1, dur), 3)


def measure(src):
    import cv2
    f = frames(src)
    if len(f) < 2:
        return None
    def sharpness(x):  # la zone la plus nette (3 × 3) : un fond flou voulu ne pénalise pas le sujet net
        h, w = x.shape
        lap = cv2.Laplacian(x, cv2.CV_64F)
        return max(lap[i * h // 3:(i + 1) * h // 3, j * w // 3:(j + 1) * w // 3].var() for i in range(3) for j in range(3))
    sharp = np.array([sharpness(x) for x in f])
    bright = f.reshape(len(f), -1).mean(axis=1)
    motion = np.concatenate([[0], np.abs(np.diff(f.astype(np.int16), axis=0)).reshape(len(f) - 1, -1).mean(axis=1)])
    shake = [0.0]
    win = cv2.createHanningWindow(f[0].shape[::-1], cv2.CV_32F)
    for a, b in zip(f[:-1], f[1:]):
        (dx, dy), _ = cv2.phaseCorrelate(a.astype(np.float32), b.astype(np.float32), win)
        shake.append(float(np.hypot(dx, dy)))
    return {"sharp": sharp, "bright": bright, "motion": motion, "shake": np.array(shake)}


def camera_jitter(src, start=0.0, length=None, fps=15):
    """Tremblement de la CAMÉRA (pas du sujet) : mouvement de l'arrière-plan suivi point par point (RANSAC écarte ce qui
    bouge dans l'image), puis écart entre ce trajet et sa version lissée ; un panoramique voulu est lisse et ne compte pas.
    En pixels sur une image de 320 px de large ; > JITTER_MIN : la main tremble."""
    import cv2
    cap = cv2.VideoCapture(str(src))
    sfps = cap.get(cv2.CAP_PROP_FPS) or 30
    sw, sh = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    if not sw:
        return 0.0
    size = (320, max(2, int(sh * 320 / sw)))
    cap.set(cv2.CAP_PROP_POS_MSEC, start * 1000)
    step = max(1, round(sfps / fps))
    n_max = int((length if length else 1e9) * sfps)
    path, prev, f = [(0.0, 0.0)], None, 0
    while f < n_max:
        ok = cap.grab()
        if not ok:
            break
        f += 1
        if (f - 1) % step:
            continue
        ok, img = cap.retrieve()
        if not ok:
            break
        g = cv2.cvtColor(cv2.resize(img, size), cv2.COLOR_BGR2GRAY)
        if prev is not None:
            dx = dy = 0.0
            pts = cv2.goodFeaturesToTrack(prev, 200, 0.01, 8)
            if pts is not None and len(pts) >= 8:
                nxt, st, _ = cv2.calcOpticalFlowPyrLK(prev, g, pts, None)
                good = st.flatten() == 1
                if good.sum() >= 8:
                    m, inl = cv2.estimateAffinePartial2D(pts[good], nxt[good], method=cv2.RANSAC, ransacReprojThreshold=2)
                    if m is not None and inl is not None and inl.sum() >= 8:
                        q = pts[good][inl.flatten() == 1].reshape(-1, 2)
                        spread = np.ptp(q, axis=0) / np.array(size)
                        if spread[0] >= 0.4 and spread[1] >= 0.4:  # points sur tout le décor, pas sur un objet qui passe
                            dx, dy = float(m[0, 2]), float(m[1, 2])
            path.append((path[-1][0] + dx, path[-1][1] + dy))
        prev = g
    cap.release()
    p = np.array(path)
    if len(p) < 6:
        return 0.0
    k = 7
    pad = np.pad(p, ((k // 2, k // 2), (0, 0)), mode="edge")
    smooth = np.stack([np.convolve(pad[:, i], np.ones(k) / k, mode="valid") for i in range(2)], axis=1)
    return round(float(np.mean(np.hypot(*(p - smooth).T))), 2)


def motion_profile(src, start, length, fps=10):
    """Quantité de mouvement dans l'image, image par image (écart moyen entre deux images, niveaux de gris 160 px),
    sur [start, start + length] : le pic = le geste fort (coup de marteau, pâte qui s'étire, verre qu'on remplit)."""
    p = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{max(0.0, start):.3f}", "-t", f"{length:.3f}", "-i", str(src),
                        "-vf", f"fps={fps},scale=160:-2,format=gray", "-f", "rawvideo", "-"], capture_output=True)
    m = meta(src)
    h = round(m["height"] * 160 / max(1, m["width"]) / 2) * 2 or 160
    n = len(p.stdout) // (160 * h)
    if n < 3:
        return np.zeros(0)
    f = np.frombuffer(p.stdout[:n * 160 * h], np.uint8).reshape(n, h, 160).astype(np.int16)
    d = np.abs(np.diff(f, axis=0)).reshape(n - 1, -1).mean(axis=1)
    return np.concatenate([[d[0]], d])


def subject_x(src, start, length, frac=0.32, n=8):
    """Où est le sujet, de gauche (0) à droite (1), sur [start, start + length] : centre des visages (YuNet) s'il y en a,
    sinon centre de ce qui bouge et de ce qui est net (la main qui perce, le chef qui pétrit), plutôt que le milieu.
    frac : largeur gardée par le recadrage, en part de la largeur source (9:16 tiré du 16:9 = 0,32)."""
    import cv2
    try:
        cv2.utils.logging.setLogLevel(cv2.utils.logging.LOG_LEVEL_ERROR)  # avertissement sans conséquence du moteur dnn
    except Exception:  # noqa: BLE001
        pass
    cap = cv2.VideoCapture(str(src))
    sw, sh = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    if not sw or not sh:
        return 0.5
    k = 320 / sw
    size = (320, max(2, int(sh * k)))
    model = ROOT / ".claude" / "skills" / "videomaker-deeplo" / "vendor" / "yunet" / "face_detection_yunet_2023mar.onnx"
    det = cv2.FaceDetectorYN.create(str(model), "", size, 0.7, 0.3, 20) if model.exists() else None
    faces, imgs = [], []
    for t in np.linspace(start + 0.1, start + max(0.2, length - 0.1), n):
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ok, img = cap.read()
        if not ok:
            continue
        img = cv2.resize(img, size)
        imgs.append(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32))
        if det is not None:
            _, fc = det.detect(img)
            if fc is not None and len(fc):
                big = max(fc, key=lambda f: f[2] * f[3])
                if big[2] * big[3] > 0.004 * size[0] * size[1]:
                    faces.append((big[0] + big[2] / 2) / size[0])
    cap.release()
    if len(faces) >= max(2, len(imgs) // 3):
        return round(float(np.median(faces)), 3)
    if len(imgs) < 2:
        return 0.5
    energy = np.zeros_like(imgs[0])
    for a, b in zip(imgs[:-1], imgs[1:]):
        energy += np.abs(b - a)  # ce qui bouge
    energy /= max(1e-6, energy.max())
    lap = np.abs(cv2.Laplacian(np.mean(imgs, axis=0), cv2.CV_32F))
    lap = cv2.GaussianBlur(lap, (0, 0), 6)
    lap /= max(1e-6, lap.max())
    prof = (np.sqrt(energy * lap) + 0.15 * lap).mean(axis=0)  # ce qui bouge ET est net (un premier plan flou qui passe ne compte pas)
    prof = np.convolve(prof, np.ones(15) / 15, mode="same")
    if prof.max() - prof.mean() < 0.02:  # rien qui ressorte : on reste au milieu
        return 0.5
    # fenêtre (largeur frac) qui garde le plus de sujet, avec une préférence pour le milieu à couverture presque égale
    n_ = len(prof)
    cw = max(2, int(round(frac * n_)))
    if cw >= n_:
        return 0.5
    cs = np.concatenate([[0], np.cumsum(prof - prof.min())])
    cover = (cs[cw:] - cs[:-cw]) / max(1e-6, cs[-1])
    xs = (np.arange(len(cover)) + cw / 2) / n_
    best = int(np.argmax(cover - 0.25 * np.abs(xs - 0.5)))
    mid = int(np.argmin(np.abs(xs - 0.5)))
    if cover[best] - cover[mid] < 0.1:  # le décentrage ne gagne pas grand-chose (plan large, sujet au milieu) : milieu
        return 0.5
    # sans visage, la mesure est moins sûre : on ne va qu'aux 2/3 du chemin (le sujet reste cadré, le centre aussi)
    return round(0.5 + 0.65 * (float(xs[best]) - 0.5), 3)


def best_windows(m, seg, ref_sharp, k=3):
    """Passages de seg s les mieux notés, sans chevauchement : nets, ni trop sombres ni brûlés, caméra stable, un peu de vie."""
    n = len(m["sharp"])
    L = max(2, int(seg * FPS))
    if n <= L:
        L = n
    sh = np.clip(m["sharp"] / max(1e-6, ref_sharp), 0, 1.2)
    br = 1 - np.clip(np.abs(m["bright"] - 125) / 125, 0, 1) ** 2
    mo = np.clip(m["motion"] / 6, 0, 1)
    life = 0.55 + 0.45 * np.minimum(mo, 1)  # un peu de mouvement dans l'image, c'est mieux
    stab = 1 / (1 + (m["shake"] / 2.5) ** 2)  # la caméra qui bouge beaucoup est pénalisée
    s = sh * br * life * stab
    cand = []
    for i in range(0, n - L + 1):
        cand.append((float(s[i:i + L].mean()), i))
    cand.sort(reverse=True)
    res = []
    for sc, i in cand:
        if all(abs(i - j) >= L for _, j in res):
            res.append((sc, i))
        if len(res) >= k:
            break
    return [{"from": round(i / FPS, 2), "to": round((i + L) / FPS, 2), "score": round(sc, 3),
             "shake": round(float(m["shake"][i:i + L].mean()), 2), "motion": round(float(m["motion"][i:i + L].mean()), 2)}
            for sc, i in sorted(res, key=lambda x: -x[0])]


def scan(job_name, seg=3.0):
    job = job_dir(job_name)
    vids = sorted(p for p in (job / "inbox").glob("*") if p.suffix.lower() in VIDEO)
    if not vids:
        fail("aucune vidéo dans inbox/")
    rows, ms = [], {}
    for v in vids:
        md = meta(v)
        m = measure(v)
        if m is None:
            continue
        ms[v.name] = m
        rows.append({"clip": v.name, **md, "speech": speech_ratio(v, md["duration"]) if md["has_audio"] else 0.0})
    ref = float(np.percentile(np.concatenate([m["sharp"] for m in ms.values()]), 90)) or 1.0
    for r in rows:
        m = ms[r["clip"]]
        r["segments"] = best_windows(m, seg, ref)
        r["shake_median"] = round(float(np.median(m["shake"])), 2)
        r["timelapse"] = bool(r["duration"] >= 20 and r["shake_median"] < 0.6)  # long et caméra posée : accéléré possible
        r["parole"] = bool(r["speech"] and r["speech"] > 0.25)
    rows.sort(key=lambda r: (r["date"], r["clip"]))
    write_json(job / "work" / "footage.json", {"seg": seg, "clips": rows})
    sheet = planche(job, rows)
    out(ok=True, clips=len(rows), fichier=str(job / "work" / "footage.json"), planche=sheet,
        parole=[r["clip"] for r in rows if r["parole"]], accelere_possible=[r["clip"] for r in rows if r["timelapse"]],
        suite="regarde la planche, puis footage.py plan <job> <slug> (ou transcribe.py pour les clips où l'on parle)")


def planche(job, rows):
    """Une vignette par clip (milieu du meilleur passage) avec n°, date, durée, note."""
    d = job / "work" / "footage"
    d.mkdir(parents=True, exist_ok=True)
    tiles = []
    for k, r in enumerate(rows):
        if not r["segments"]:
            continue
        sg = r["segments"][0]
        t = (sg["from"] + sg["to"]) / 2
        img = d / f"t{k:02d}.jpg"
        lab = f"{k + 1}  {r['date'][5:10]}  {r['duration']:.0f}s  {sg['score']:.2f}" + ("  TL" if r["timelapse"] else "") + ("  PAROLE" if r["parole"] else "")
        lab = lab.replace(":", "\\:")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(t), "-i", str(job / "inbox" / r["clip"]), "-frames:v", "1",
                        "-vf", f"scale=300:300:force_original_aspect_ratio=decrease,pad=300:340:(ow-iw)/2:0:color=0x111111,"
                               f"drawtext=text='{lab}':x=8:y=h-30:fontsize=18:fontcolor=white", str(img)], capture_output=True)
        if img.exists():
            tiles.append(img)
    if not tiles:
        return None
    cols = min(6, len(tiles))
    rows_n = -(-len(tiles) // cols)
    args = sum([["-i", str(t)] for t in tiles], [])
    layout = "|".join(f"{(i % cols) * 300}_{(i // cols) * 340}" for i in range(len(tiles)))
    dst = d / "planche.jpg"
    flt = (f"{''.join(f'[{i}:v]' for i in range(len(tiles)))}xstack=inputs={len(tiles)}:layout={layout}:fill=0x111111"
           if len(tiles) > 1 else "null")
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args, "-filter_complex", flt, "-frames:v", "1", str(dst)], capture_output=True)
    return str(dst) if dst.exists() else None


def plan(job_name, slug, duree=30.0, maxn=12):
    job = job_dir(job_name)
    fj = job / "work" / "footage.json"
    if not fj.exists():
        fail("lance d'abord footage.py scan <job>")
    clips = [c for c in read_json(fj)["clips"] if c["segments"]]
    if not clips:
        fail("aucun passage utilisable")
    # les meilleurs clips, gardés dans l'ordre chronologique
    best = sorted(clips, key=lambda c: -c["segments"][0]["score"])[:maxn]
    keep = [c for c in clips if c in best]
    days = sorted({c["date"][:10] for c in keep})
    d0 = datetime.date.fromisoformat(days[0])
    per = max(1.6, min(4.0, duree / max(1, len(keep))))
    items, n_tl = [], 0
    for c in keep:
        it = {"clip": c["clip"], "seg": 0, "keep": True, "dur": round(per, 1)}
        if c["timelapse"] and n_tl < max(1, len(keep) // 3):
            it.update({"timelapse": True, "speed": round(min(16, max(4, c["duration"] / per)), 1)})
            n_tl += 1
        if len(days) >= 2:
            it["label"] = f"JOUR {(datetime.date.fromisoformat(c['date'][:10]) - d0).days + 1}"
        if c.get("parole"):
            it["note"] = "on parle dans ce clip : transcribe.py pour s'en servir comme repère ou garder le son"
        items.append(it)
    data = {"title": "", "series": None, "sound": "music", "items": items, "compare": []}
    dst = job / "work" / f"{slug}_footage.json"
    if dst.exists():
        dst = job / "work" / f"{slug}_footage_draft.json"
    write_json(dst, data)
    out(ok=True, fichier=str(dst), clips=len(items), jours=len(days), accelere=n_tl, duree_estimee=round(sum(i["dur"] for i in items), 1),
        suite="relis (garder, ordre, passage seg 0-2, accéléré, étiquettes, titre, série, avant / après), puis build_footage.py")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["scan", "plan"])
    ap.add_argument("job")
    ap.add_argument("slug", nargs="?")
    ap.add_argument("--seg", type=float, default=3.0)
    ap.add_argument("--duree", type=float, default=30.0)
    ap.add_argument("--max", type=int, default=12)
    a = ap.parse_args()
    if a.cmd == "scan":
        scan(a.job, a.seg)
    else:
        if not a.slug:
            fail("plan : donne le slug")
        plan(a.job, a.slug, a.duree, a.max)


if __name__ == "__main__":
    main()

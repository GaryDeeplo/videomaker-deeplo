"""CLIGNEMENTS AUX COUPES : aucune coupe ne tombe sur des yeux fermés (appelé par build_cut.py).

  python blink.py <job> <slug>        # contrôle seul sur le plan actuel (work/<slug>_plan.json), sans rien écrire

À chaque point de coupe (dernière image avant, première image après), le score « œil fermé » de MediaPipe Face
Landmarker (blendshapes eyeBlinkLeft / eyeBlinkRight, modèle Apache 2.0 dans vendor/mediapipe) est mesuré image par
image. Yeux fermés (score ≥ 0,4 sur les deux yeux) -> la coupe glisse de quelques images (0,25 s au plus) vers une
image aux yeux ouverts, SANS entrer dans un mot : elle reste entre la fin du dernier mot gardé et le début du mot
suivant (mots horodatés de work/<slug>_words.json). Rien de possible -> la coupe reste et le rapport le dit.
Facultatif : sans MediaPipe (pip install --no-deps mediapipe absl-py), le dérush se fait comme avant.
"""
import argparse
import json
import subprocess
from pathlib import Path

import numpy as np

from common import ROOT, job_dir, out, read_json

MODEL = ROOT / ".claude" / "skills" / "videomaker-deeplo" / "vendor" / "mediapipe" / "face_landmarker.task"
CLOSED = 0.4   # score des deux yeux au-delà duquel l'image montre des yeux fermés (ou mi-clos)
MAX_SHIFT = 0.25
MARGIN = 0.03  # écart gardé avec un mot


def available():
    try:
        import mediapipe  # noqa: F401
    except Exception:  # noqa: BLE001
        return False
    return MODEL.exists()


class Eyes:
    """Score « yeux fermés » (min des deux yeux, 0 à 1 ; None sans visage) aux images d'une fenêtre de la source."""

    def __init__(self, src):
        import mediapipe as mp
        from mediapipe.tasks.python import BaseOptions, vision
        self.mp, self.src = mp, str(src)
        p = json.loads(subprocess.check_output(
            ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,r_frame_rate",
             "-of", "json", self.src]))["streams"][0]
        n, d = map(int, p["r_frame_rate"].split("/"))
        self.fps = n / d if d else 30.0
        # ffmpeg applique la rotation du téléphone : seul le grand côté est imposé (960 px)
        k = 960 / max(p["width"], p["height"])
        self.w, self.h = int(p["width"] * k) // 2 * 2, int(p["height"] * k) // 2 * 2
        self.det = vision.FaceLandmarker.create_from_options(vision.FaceLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=str(MODEL)), running_mode=vision.RunningMode.IMAGE,
            output_face_blendshapes=True, num_faces=1))

    def window(self, t0, t1):
        t0 = max(0.0, t0)
        cmd = ["ffmpeg", "-v", "error", "-ss", f"{t0:.3f}", "-i", self.src, "-t", f"{t1 - t0:.3f}",
               "-vf", f"scale='if(gt(iw,ih),{max(self.w, self.h)},-2)':'if(gt(iw,ih),-2,{max(self.w, self.h)})'",
               "-f", "image2pipe", "-vcodec", "bmp", "-"]
        raw = subprocess.run(cmd, capture_output=True).stdout
        res, i, pos = [], 0, 0
        while pos + 54 <= len(raw) and raw[pos:pos + 2] == b"BM":
            size = int.from_bytes(raw[pos + 2:pos + 6], "little")
            bmp = raw[pos:pos + size]
            pos += size
            w, h = int.from_bytes(bmp[18:22], "little", signed=True), int.from_bytes(bmp[22:26], "little", signed=True)
            off = int.from_bytes(bmp[10:14], "little")
            stride = (w * 3 + 3) & ~3
            px = np.frombuffer(bmp[off:off + stride * abs(h)], np.uint8).reshape(abs(h), stride)[:, :w * 3]
            px = px.reshape(abs(h), w, 3)[::-1 if h > 0 else 1, :, ::-1]  # BMP : de bas en haut, BGR
            img = self.mp.Image(image_format=self.mp.ImageFormat.SRGB, data=np.ascontiguousarray(px))
            r = self.det.detect(img)
            sc = None
            if r.face_blendshapes:
                bs = {c.category_name: c.score for c in r.face_blendshapes[0]}
                sc = min(bs.get("eyeBlinkLeft", 0), bs.get("eyeBlinkRight", 0))
            res.append((t0 + i / self.fps, sc))
            i += 1
        return res


def _closed(sc):
    return sc is not None and sc >= CLOSED


def adjust(src, segs, words):
    """segs [(début, fin)] dans la source -> (segs décalés, rapport). Ne touche jamais un mot."""
    eyes = Eyes(src)
    fr = 1.0 / eyes.fps
    segs = [list(s) for s in segs]
    starts = sorted(float(w["start"]) for w in words)
    ends = sorted(float(w["end"]) for w in words)
    moved, left, checked = [], [], 0
    for n, (s, e) in enumerate(segs):
        prev_e = segs[n - 1][1] if n else -1e9
        next_s = segs[n + 1][0] if n + 1 < len(segs) else 1e9
        for edge in ("start", "end"):
            t = s if edge == "start" else e
            # bornes : entre la fin du mot d'avant et le début du mot d'après, sans toucher l'autre segment
            lo = max([x for x in ends if x <= t + 1e-3] or [t - MAX_SHIFT]) + MARGIN
            hi = min([x for x in starts if x >= t - 1e-3] or [t + MAX_SHIFT]) - MARGIN
            lo, hi = max(lo, t - MAX_SHIFT), min(hi, t + MAX_SHIFT)
            if edge == "start":
                lo, hi = max(lo, prev_e + fr), min(hi, e - 0.3)
            else:
                lo, hi = max(lo, s + 0.3), min(hi, next_s - fr)
            sc = eyes.window(t - MAX_SHIFT - fr, t + MAX_SHIFT + fr)
            if not sc:
                continue
            checked += 1

            def shown(x):  # image montrée à la coupe : la première après un début, la dernière avant une fin
                ref = x if edge == "start" else x - fr
                return min(sc, key=lambda q: abs(q[0] - ref))[1]
            if not _closed(shown(t)):
                continue
            cands = sorted((abs(c - t), c) for c in np.arange(lo, hi + 1e-6, fr / 2) if not _closed(shown(c)))
            tag = f"{'début' if edge == 'start' else 'fin'} du segment {n + 1} ({t:.2f} s)"
            if not cands or lo > hi:
                left.append(f"{tag} : yeux fermés, impossible de décaler sans couper un mot")
                continue
            c = round(float(cands[0][1]), 3)
            if edge == "start":
                segs[n][0] = s = c
            else:
                segs[n][1] = e = c
            moved.append(f"{tag} -> {c:.2f} s ({(c - t) * 1000:+.0f} ms)")
    eyes.det.close()
    return [tuple(x) for x in segs], {"coupes_verifiees": checked, "decalees": moved or None, "restantes": left or None}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("job")
    ap.add_argument("slug")
    a = ap.parse_args()
    job = job_dir(a.job)
    if not available():
        return out(ok=False, erreur="MediaPipe absent : pip install --no-deps mediapipe absl-py (modèle dans vendor/mediapipe)")
    plan = read_json(job / "work" / f"{a.slug}_plan.json")
    words = read_json(job / "work" / f"{a.slug}_words.json")["words"]
    segs = [(float(i["cut_start"]), float(i["cut_end"])) for i in plan["islands"] if i.get("keep")]
    _, rep = adjust(Path(plan["source"]), segs, words)
    out(ok=True, **rep)


if __name__ == "__main__":
    main()

"""DÉTOURAGE DU SUJET : la personne découpée en vidéo transparente (WebM avec couche alpha), pour poser un titre géant
DERRIÈRE elle (la personne passe devant le texte, comme dans les reels tendance). Tout en local : rembg + modèle
u2net_human_seg (ou birefnet-portrait, plus fin et plus lent) déjà présents dans ~/.u2net, aucun service en ligne.

  python cutout.py <job> <video> --from S --dur D [--model u2net_human_seg] [--h 960]   # test : assets/cutout/<…>.webm
  build_composition.py <job> <slug> --derriere "MONTAGE AUTO" [--derriere-mot <mot dit>]   # usage normal

Masque lissé d'une image à l'autre (pas de scintillement) et adouci sur les bords ; 2 à 3 s de vidéo = 20 à 60 s de
calcul selon le modèle. Le fichier est mis en cache (même extrait, même modèle : pas recalculé).
"""
import argparse
import hashlib
import subprocess
from pathlib import Path

import numpy as np

from common import job_dir, out

FPS = 30


def vsize(src):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=p=0",
                        str(src)], capture_output=True, text=True)
    w, h = r.stdout.strip().split(",")[:2]
    return int(w), int(h)


def person_matte(job, src, start, dur, height=960, model="u2net_human_seg"):
    """-> chemin relatif assets/cutout/<…>.webm : le sujet seul (fond transparent), à la taille de la source réduite."""
    import cv2
    from rembg import new_session, remove
    key = hashlib.md5(f"{src}|{start:.3f}|{dur:.3f}|{height}|{model}".encode()).hexdigest()[:10]
    d = job / "assets" / "cutout"
    d.mkdir(parents=True, exist_ok=True)
    dst = d / f"{Path(src).stem[:20]}-{key}.webm"
    if dst.exists():
        return f"assets/cutout/{dst.name}"
    sw, sh = vsize(src)
    H = height - height % 2
    W = round(sw * H / sh / 2) * 2
    p = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{start:.3f}", "-t", f"{dur:.3f}", "-i", str(src), "-vf", f"fps={FPS},scale={W}:{H}",
                        "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True)
    n = len(p.stdout) // (W * H * 3)
    frames = np.frombuffer(p.stdout[:n * W * H * 3], np.uint8).reshape(n, H, W, 3)
    sess = new_session(model)
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                            "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-auto-alt-ref", "0", "-b:v", "0", "-crf", "30", "-deadline", "good",
                            "-cpu-used", "4", str(dst)], stdin=subprocess.PIPE)
    prev = None
    small = (max(2, W // 2), max(2, H // 2))
    for f in frames:
        m = remove(cv2.resize(f, small), session=sess, only_mask=True)  # masque 0-255 à demi-taille (plus rapide)
        m = cv2.resize(np.asarray(m), (W, H), interpolation=cv2.INTER_LINEAR).astype(np.float32) / 255
        m = cv2.GaussianBlur(m, (0, 0), 1.2)
        prev = m if prev is None else 0.6 * m + 0.4 * prev  # lissage dans le temps : pas de bords qui tremblent
        a = np.clip((prev - 0.15) / 0.7, 0, 1)  # bord net mais doux
        rgba = np.dstack([f, (a * 255).astype(np.uint8)])
        enc.stdin.write(rgba.tobytes())
    enc.stdin.close()
    enc.wait()
    if enc.returncode != 0 or not dst.exists():
        raise RuntimeError("encodage du détourage échoué")
    return f"assets/cutout/{dst.name}"


def head_top(job, rel):
    """Haut de la tête (part de la hauteur, 0 = haut) : première ligne où le sujet occupe le centre, médiane sur l'extrait."""
    tops = []
    p = subprocess.run(["ffmpeg", "-v", "error", "-c:v", "libvpx-vp9", "-i", str(job / rel), "-vf", "fps=4,alphaextract,scale=-2:240",
                        "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True)
    w, h = vsize(job / rel)
    hh = 240
    ww = round(w * hh / h / 2) * 2
    n = len(p.stdout) // (ww * hh)
    for k in range(n):
        a = np.frombuffer(p.stdout[k * ww * hh:(k + 1) * ww * hh], np.uint8).reshape(hh, ww)
        mid = a[:, ww // 4: 3 * ww // 4]
        rows = np.where((mid > 128).mean(axis=1) > 0.08)[0]
        if len(rows):
            tops.append(rows[0] / hh)
    return float(np.median(tops)) if tops else 0.3


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("job")
    ap.add_argument("video")
    ap.add_argument("--from", dest="start", type=float, default=0.0)
    ap.add_argument("--dur", type=float, default=2.5)
    ap.add_argument("--model", default="u2net_human_seg")
    ap.add_argument("--h", type=int, default=960)
    a = ap.parse_args()
    job = job_dir(a.job)
    src = Path(a.video) if Path(a.video).is_absolute() else job / a.video
    rel = person_matte(job, src, a.start, a.dur, a.h, a.model)
    out(ok=True, fichier=rel)


if __name__ == "__main__":
    main()

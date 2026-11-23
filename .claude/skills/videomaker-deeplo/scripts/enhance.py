"""NETTETÉ + STABILISATION D'UN RUSH PARLÉ (après build_cut.py) : les passages filmés en marchant sont stabilisés, les
passages plus flous que le reste du rush reçoivent un léger renfort de netteté. Le son et les temps ne bougent pas
(map.json, mots, sous-titres restent justes).

  python enhance.py <job> <slug> [--force-stab] [--sans-nettete]    # appelé par build_cut.py (sauf --no-enhance)

Par morceau monté (map.json) :
- tremblement de la CAMÉRA mesuré sur le décor (footage.camera_jitter) ; >= 1,0 : chaque morceau (plan continu, jamais de coupe dedans) passe en
  vidstab en deux passes ; la version stabilisée n'est gardée que si elle tremble nettement moins (-40 %) ;
- netteté comparée aux meilleurs passages du MÊME rush (un décor uni n'est pas un flou) ; sous 40 % : léger débruitage
  des blocs de compression + renfort de netteté (dosé, sans halo). Un visage net n'est jamais retouché.
Le flou de bougé ne se rattrape pas vraiment : il s'atténue. Mieux vaut le dire au client (guide de tournage).
"""
import argparse
import shutil
import subprocess
import tempfile
from pathlib import Path

import numpy as np

from common import job_dir, out, read_json

JITTER_MIN = 1.0
SOFT_REL = 0.4
SHARPEN = "hqdn3d=1.2:1.2:4:4,unsharp=5:5:0.7:5:5:0.0"


def sharpness(v, t0, t1, n=4):
    import cv2
    vals = []
    for t in np.linspace(t0 + 0.05, max(t0 + 0.1, t1 - 0.05), n):
        r = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", str(v), "-frames:v", "1", "-vf", "scale=540:-2,format=gray",
                            "-f", "rawvideo", "-"], capture_output=True)
        a = np.frombuffer(r.stdout, np.uint8)
        if len(a) < 540 * 10:
            continue
        h = len(a) // 540
        vals.append(cv2.Laplacian(a[:h * 540].reshape(h, 540), cv2.CV_64F).var())
    return float(np.median(vals)) if vals else 0.0


def enhance(job, slug, force_stab=False, sharpen=True):
    from footage import camera_jitter
    m = read_json(job / "work" / f"{slug}_map.json")
    cut = Path(m["cut"])
    cut = cut if cut.is_absolute() else job / "assets" / cut.name
    segs = [(s["out_start"], s["out_end"]) for s in m["segments"]]
    if not segs:
        return {"retouche": 0}
    # un morceau = un plan continu (jamais de coupe à l'intérieur : vidstab et la mesure se trompent sur une coupe)
    blocks = segs
    info = []
    for a, b in blocks:
        j = camera_jitter(cut, a, b - a)
        info.append({"a": a, "b": b, "jitter": j, "sharp": sharpness(cut, a, b)})
    ref = np.percentile([x["sharp"] for x in info], 85) or 1.0
    for x in info:
        x["stab"] = force_stab or x["jitter"] >= JITTER_MIN
        x["soft"] = sharpen and x["sharp"] / ref < SOFT_REL
    if not any(x["stab"] or x["soft"] for x in info):
        return {"retouche": 0, "blocs": len(info)}
    runs = [{"a": x["a"], "b": x["b"], "key": (x["stab"], x["soft"])} for x in info]
    fps = float(eval(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=r_frame_rate",
                                     "-of", "csv=p=0", str(cut)], capture_output=True, text=True).stdout.strip() or "25"))
    tmp = Path(tempfile.mkdtemp(prefix="vm-enh-"))
    parts, rep = [], []
    try:
        for k, r in enumerate(runs):
            stab, soft = r["key"]
            raw = tmp / f"p{k}.mp4"
            f0, f1 = round(r["a"] * fps), round(r["b"] * fps)  # à l'image près : la somme des morceaux = la vidéo, le son reste calé
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(cut), "-an", "-vf", f"select='between(n,{f0},{f1 - 1})',setpts=N/FRAME_RATE/TB",
                            "-r", f"{fps:g}", "-c:v", "libx264", "-crf", "14", "-preset", "veryfast", str(raw)], check=True)
            cur_p, done = raw, []
            if stab:
                trf, sta = f"p{k}.trf", tmp / f"p{k}_s.mp4"
                subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", raw.name, "-vf", f"vidstabdetect=shakiness=6:accuracy=10:result={trf}",
                                "-f", "null", "-"], check=True, cwd=tmp)
                subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", raw.name, "-vf",
                                f"vidstabtransform=input={trf}:smoothing=20:optzoom=1:interpol=bicubic", "-c:v", "libx264", "-crf", "14",
                                "-preset", "veryfast", sta.name], check=True, cwd=tmp)
                before, after = camera_jitter(raw), camera_jitter(sta)
                if after < 0.6 * before:
                    cur_p = sta
                    done.append(f"stabilisé ({before} -> {after})")
            if soft:
                sh_ = tmp / f"p{k}_n.mp4"
                subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(cur_p), "-vf", SHARPEN, "-c:v", "libx264", "-crf", "14",
                                "-preset", "veryfast", str(sh_)], check=True)
                cur_p = sh_
                done.append("netteté")
            parts.append(cur_p)
            if done:
                rep.append({"de": round(r["a"], 2), "a": round(r["b"], 2), "fait": ", ".join(done)})
        if not rep:
            return {"retouche": 0, "blocs": len(info)}
        lst = tmp / "l.txt"
        lst.write_text("".join(f"file '{p.as_posix()}'\n" for p in parts), encoding="utf-8")
        new = tmp / "cut.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-i", str(cut),
                        "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-pix_fmt", "yuv420p",
                        "-c:a", "copy", "-shortest", "-movflags", "+faststart", str(new)], check=True)
        orig = cut.with_name(cut.stem + "_avant_retouche.mp4")
        shutil.copy2(cut, orig)
        shutil.move(str(new), str(cut))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return {"retouche": len(rep), "passages": rep, "original": orig.name}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("job")
    ap.add_argument("slug")
    ap.add_argument("--force-stab", action="store_true")
    ap.add_argument("--sans-nettete", action="store_true")
    a = ap.parse_args()
    r = enhance(job_dir(a.job), a.slug, a.force_stab, not a.sans_nettete)
    out(ok=True, **r, suite="build_text / build_composition comme d'habitude (temps inchangés)")


if __name__ == "__main__":
    main()

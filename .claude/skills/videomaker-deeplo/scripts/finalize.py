"""MASTER FINAL -> renders/<nom>_final.mp4  (vidéo copiée, audio masterisé)

Deux passes loudnorm vers -14 LUFS intégrés (norme Reels / TikTok / YouTube), true peak -2 dBTP avant AAC
(l'encodage AAC ajoute ~0,5 dB). Mesure ensuite le MP4 livré, jamais le WAV intermédiaire.

  python finalize.py <job> <render.mp4> [--lufs -14] [--tp -2]
"""
import argparse
import json
import re
import subprocess
from pathlib import Path

from common import fail, job_dir, out, sh


def ebur(path):
    log = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af", "ebur128=peak=true",
                          "-f", "null", "-"], capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
    i = re.findall(r"I:\s+(-?[\d.]+) LUFS", log)
    p = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", log)
    return (float(i[-1]) if i else None), (float(p[-1]) if p else None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("job")
    ap.add_argument("render")
    ap.add_argument("--lufs", type=float, default=-14.0)
    ap.add_argument("--tp", type=float, default=-2.0)
    a = ap.parse_args()
    job = job_dir(a.job)
    src = Path(a.render)
    if not src.is_absolute():
        src = job / "renders" / src if (job / "renders" / src).exists() else src.resolve()
    if not src.exists():
        fail(f"introuvable : {src}")

    target = f"I={a.lufs}:TP={a.tp}:LRA=11"
    log = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(src), "-vn", "-af",
                          f"loudnorm={target}:print_format=json", "-f", "null", "-"],
                         capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
    try:
        mj = json.loads(log[log.rindex("{"):log.rindex("}") + 1])
    except ValueError:
        fail("mesure loudnorm impossible", stderr=log[-600:])
    second = (f"loudnorm={target}:measured_I={mj['input_i']}:measured_TP={mj['input_tp']}:"
              f"measured_LRA={mj['input_lra']}:measured_thresh={mj['input_thresh']}:offset={mj['target_offset']}:"
              f"linear=true,aresample=48000")
    dst = src.with_name(src.stem.replace("_draft", "") + "_final.mp4")
    sh(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-map", "0:v", "-c:v", "copy", "-map", "0:a",
        "-af", second, "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(dst)], "ffmpeg (master)")
    lufs, peak = ebur(dst)
    ok = lufs is not None and abs(lufs - a.lufs) <= 1.0 and peak is not None and peak <= -1.0
    out(ok=ok, final=str(dst), lufs=lufs, true_peak=peak, cible=f"{a.lufs} LUFS, crête ≤ -1 dBTP",
        verdict="OK" if ok else "À CORRIGER")


if __name__ == "__main__":
    main()

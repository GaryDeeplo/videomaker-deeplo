"""MASTER FINAL -> renders/<nom>_final.mp4  (vidéo copiée, audio masterisé)

Deux passes loudnorm vers -14 LUFS intégrés (norme Reels / TikTok / YouTube), true peak -2 dBTP avant AAC
(l'encodage AAC ajoute ~0,5 dB). Mesure ensuite le MP4 livré, jamais le WAV intermédiaire.
Garde-fous (d'après ffmpeg-skill, MIT) :
  - loudnorm ne reste en mode linéaire que si la plage (LRA) et la crête le permettent, sinon il bascule seul en mode
    dynamique (compresse, peut rater la cible). Plage trop large : la cible LRA est élargie pour rester linéaire.
    Crête trop haute : le mode dynamique est annoncé (« mode ») et ses horodatages réalignés ; s'il rate la cible
    de plus de 1 LU, repli sur un gain fixe + limiteur (alimiter).
  - crête > -1 dBTP dans le MP4 (dépassement de l'AAC) : ré-encodage en 256k, puis 320k, puis plafond abaissé.
  - son coupé à la longueur de l'image (loudnorm rend son dernier bloc entier : +0,1 s sinon) ; AAC 48 kHz stéréo.

  python finalize.py <job> <render.mp4> [--lufs -14] [--tp -2]
"""
import argparse
import json
import math
import re
import subprocess
from pathlib import Path

from common import fail, job_dir, out, probe, sh

LIMIT = -1.0  # crête maximale admise dans le MP4 livré (dBTP)


def ebur(path):
    log = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-vn", "-af", "ebur128=peak=true",
                          "-f", "null", "-"], capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
    i = re.findall(r"I:\s+(-?[\d.]+) LUFS", log)
    p = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", log)
    return (float(i[-1]) if i else None), (float(p[-1]) if p else None)


def loudnorm_mode(mj, lufs, tp, lra):
    """Mode dans lequel loudnorm fera la 2e passe, selon sa propre règle (af_loudnorm.c) : linéaire seulement si les
    mesures sont utilisables, que le gain garde la crête sous le plafond et la plage sous la cible LRA ; sinon
    dynamique. D'après ffmpeg-skill (MIT), scripts/loudness.py loudnorm_mode."""
    try:
        mi, mtp, mlra, mth = (float(mj[k]) for k in ("input_i", "input_tp", "input_lra", "input_thresh"))
    except (KeyError, TypeError, ValueError):
        return "dynamic"
    if mtp == 99 or mth == -70 or mlra == 0 or mi == 0:
        return "dynamic"
    return "linear" if mtp + (lufs - mi) <= tp and mlra <= lra else "dynamic"


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

    log = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(src), "-vn", "-af",
                          f"loudnorm=I={a.lufs}:TP={a.tp}:LRA=11:print_format=json", "-f", "null", "-"],
                         capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
    try:
        mj = json.loads(log[log.rindex("{"):log.rindex("}") + 1])
    except ValueError:
        fail("mesure loudnorm impossible", stderr=log[-600:])
    notes = []
    lra = 11.0
    try:
        if float(mj["input_lra"]) > lra:  # plage plus large que 11 LU : on l'admet plutôt que de laisser loudnorm compresser
            lra = min(50.0, math.ceil(float(mj["input_lra"])) + 1.0)
            notes.append(f"plage {mj['input_lra']} LU > 11 : cible LRA portée à {lra:g} pour rester en mode linéaire")
    except (KeyError, ValueError):
        pass
    info = probe(src)
    keep = min(x for x in ((info.get("audio") or {}).get("duration"), info.get("video_duration"), info["duration"]) if x)

    dst = src.with_name(src.stem.replace("_draft", "") + "_final.mp4")
    ceiling, bitrate, steps, rounds = a.tp, "192k", ["256k", "320k"], 0

    def encode(gain=None):
        """gain (dB) : gain fixe + limiteur au lieu de loudnorm (repli quand le mode dynamique rate la cible)."""
        if gain is not None:
            mode = "limiteur"
            af = f"volume={gain:.2f}dB,alimiter=limit={10 ** ((ceiling - 1) / 20):.4f}:level=false:latency=true"
        else:
            mode = loudnorm_mode(mj, a.lufs, ceiling, lra)
            af = (f"loudnorm=I={a.lufs}:TP={ceiling:.2f}:LRA={lra:g}:measured_I={mj['input_i']}:measured_TP={mj['input_tp']}:"
                  f"measured_LRA={mj['input_lra']}:measured_thresh={mj['input_thresh']}:offset={mj['target_offset']}:linear=true")
            if mode == "dynamic":  # en dynamique, loudnorm horodate lui-même ses blocs (saut de ~0,1 s après un silence)
                af += ",asetpts=N/SR/TB"
        af += f",atrim=duration={keep:.6f},aresample=48000"  # atrim juste après loudnorm (ffmpeg 5.1)
        sh(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-map", "0:v", "-c:v", "copy", "-map", "0:a",
            "-af", af, "-c:a", "aac", "-b:a", bitrate, "-ar", "48000", "-ac", "2", "-movflags", "+faststart", str(dst)],
           "ffmpeg (master)")
        return mode

    def master(gain=None):
        """Encode puis, tant que la crête du MP4 dépasse -1 dBTP (dépassement de l'AAC) : 256k, 320k, puis plafond
        abaissé du dépassement (d'après ffmpeg-skill, MIT, scripts/loudness.py)."""
        nonlocal ceiling, bitrate, steps, rounds
        ceiling, bitrate, steps = a.tp, "192k", ["256k", "320k"]
        mode = encode(gain)
        lufs, peak = ebur(dst)
        while peak is not None and peak > LIMIT and rounds < 5:
            rounds += 1
            if steps:
                bitrate = steps.pop(0)
                notes.append(f"crête {peak} dBTP après AAC : ré-encodage en {bitrate}")
            else:
                ceiling -= (peak - LIMIT) + 0.2
                notes.append(f"crête {peak} dBTP après AAC : plafond abaissé à {ceiling:.2f} dBTP")
            mode = encode(gain)
            lufs, peak = ebur(dst)
        return mode, lufs, peak

    mode, lufs, peak = master()
    if mode == "dynamic":
        notes.append("loudnorm en mode dynamique (crête trop haute pour un simple gain, ou mesure inutilisable) : niveau compressé")
        if lufs is not None and abs(lufs - a.lufs) > 1.0:  # cible ratée : gain fixe + limiteur, corrigé une fois
            notes.append(f"mode dynamique à {lufs} LUFS : repli gain fixe + limiteur")
            gain = a.lufs - float(mj["input_i"])
            mode, lufs, peak = master(gain)
            if lufs is not None and abs(lufs - a.lufs) > 0.5:
                mode, lufs, peak = master(gain + a.lufs - lufs)
    ok = lufs is not None and abs(lufs - a.lufs) <= 1.0 and peak is not None and peak <= LIMIT
    out(ok=ok, final=str(dst), lufs=lufs, true_peak=peak, cible=f"{a.lufs} LUFS, crête ≤ {LIMIT:g} dBTP",
        verdict="OK" if ok else "À CORRIGER", mode={"linear": "linéaire", "dynamic": "dynamique"}.get(mode, mode),
        lra_cible=lra, debit=bitrate, plafond=round(ceiling, 2), reprises=rounds, notes=notes or None)


if __name__ == "__main__":
    main()

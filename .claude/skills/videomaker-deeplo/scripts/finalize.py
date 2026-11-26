"""MASTER FINAL -> renders/<nom>_final.mp4  (vidéo copiée, audio masterisé)

Vers -14 LUFS intégrés (norme Reels / TikTok / YouTube), true peak -2 dBTP avant AAC (l'encodage AAC ajoute ~0,5 dB).
Chaîne : gain de départ mesuré (le mix arrive près de la cible), compresseur de « glue » léger (seuil -16 dB, 1,5:1,
attaque 30 ms, ~1 à 2 dB de réduction), limiteur sur-échantillonné (192 kHz, 0,5 dB sous le plafond : il tient
aussi les crêtes entre les échantillons), gain ajusté jusqu'à ±0,2 LU de la cible, PUIS loudnorm en deux passes sur
ce signal (mesure, puis correction linéaire de quelques dixièmes). Plage (LRA) plafonnée à 9 LU : au-delà, loudnorm la resserre (mode dynamique, annoncé).
Mesure ensuite le MP4 livré, jamais le WAV intermédiaire.
Garde-fous (d'après ffmpeg-skill, MIT) :
  - mode dynamique qui rate la cible de plus de 1 LU : repli sur un gain fixe + limiteur.
  - crête > -1 dBTP dans le MP4 (dépassement de l'AAC) : ré-encodage en 256k, puis 320k, puis plafond abaissé.
  - son coupé à la longueur de l'image (loudnorm rend son dernier bloc entier : +0,1 s sinon) ; AAC 48 kHz stéréo.

  python finalize.py <job> <render.mp4> [--lufs -14] [--tp -2]
"""
import argparse
import json
import re
import subprocess
from pathlib import Path

from common import fail, job_dir, out, probe, sh

LIMIT = -1.0  # crête maximale admise dans le MP4 livré (dBTP)
LRA = 9.0  # plage maximale livrée (LU)


def ebur(path, af=None):
    """(LUFS intégrés, crête vraie dBTP) du fichier, après la chaîne af si donnée."""
    log = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-vn", "-af",
                          (af + "," if af else "") + "ebur128=peak=true", "-f", "null", "-"],
                         capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
    i = re.findall(r"I:\s+(-?[\d.]+) LUFS", log)
    p = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", log)
    return (float(i[-1]) if i else None), (float(p[-1]) if p else None)


def pre_chain(gain, ceiling):
    """Gain de départ, compresseur de « glue » léger, limiteur sur-échantillonné 0,5 dB sous le plafond."""
    return (f"volume={gain:.2f}dB,acompressor=threshold=-16dB:ratio=1.5:attack=30:release=250:knee=4,"
            f"aresample=192000,alimiter=limit={10 ** ((ceiling - 0.5) / 20):.4f}:attack=2:release=60:level=false:latency=true,"
            "aresample=48000")


def measure(src, pre, lufs, tp):
    """Première passe loudnorm (mesures JSON) sur le signal déjà préparé."""
    log = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(src), "-vn", "-af",
                          f"{pre},loudnorm=I={lufs}:TP={tp}:LRA={LRA:g}:print_format=json", "-f", "null", "-"],
                         capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
    try:
        return json.loads(log[log.rindex("{"):log.rindex("}") + 1])
    except ValueError:
        fail("mesure loudnorm impossible", stderr=log[-600:])


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

    # gain de départ : le mix brut, puis corrigé (glue + limiteur retirent un peu de niveau) jusqu'à ±0,2 LU de la cible
    i0, _ = ebur(src)
    if i0 is None or i0 < -70:
        fail("son muet ou illisible", fichier=str(src))
    gain = a.lufs - i0
    for _ in range(4):
        i1, _ = ebur(src, pre_chain(gain, a.tp))
        if i1 is None or i1 < -70 or abs(a.lufs - i1) <= 0.2:
            break
        gain += a.lufs - i1
    notes = []
    info = probe(src)
    keep = min(x for x in ((info.get("audio") or {}).get("duration"), info.get("video_duration"), info["duration"]) if x)

    dst = src.with_name(src.stem.replace("_draft", "") + "_final.mp4")
    ceiling, bitrate, steps, rounds = a.tp, "192k", ["256k", "320k"], 0
    mj, mj_for = None, None

    def encode(fixed=None):
        """fixed (dB) : gain fixe + limiteur au lieu de loudnorm (repli quand le mode dynamique rate la cible)."""
        nonlocal mj, mj_for
        pre = pre_chain(gain, ceiling)
        if mj_for != pre:  # mesure refaite quand le plafond change
            mj, mj_for = measure(src, pre, a.lufs, ceiling), pre
        if fixed is not None:
            mode = "limiteur"
            af = (f"{pre},volume={fixed:.2f}dB,aresample=192000,alimiter=limit={10 ** ((ceiling - 0.5) / 20):.4f}:"
                  "level=false:latency=true,aresample=48000")
        else:
            mode = loudnorm_mode(mj, a.lufs, ceiling, LRA)
            af = (f"{pre},loudnorm=I={a.lufs}:TP={ceiling:.2f}:LRA={LRA:g}:measured_I={mj['input_i']}:measured_TP={mj['input_tp']}:"
                  f"measured_LRA={mj['input_lra']}:measured_thresh={mj['input_thresh']}:offset={mj['target_offset']}:linear=true")
            if mode == "dynamic":  # en dynamique, loudnorm horodate lui-même ses blocs (saut de ~0,1 s après un silence)
                af += ",asetpts=N/SR/TB"
        af += f",atrim=duration={keep:.6f},aresample=48000"  # atrim juste après loudnorm (ffmpeg 5.1)
        sh(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-map", "0:v", "-c:v", "copy", "-map", "0:a",
            "-af", af, "-c:a", "aac", "-b:a", bitrate, "-ar", "48000", "-ac", "2", "-movflags", "+faststart", str(dst)],
           "ffmpeg (master)")
        return mode

    def master(fixed=None):
        """Encode puis, tant que la crête du MP4 dépasse -1 dBTP (dépassement de l'AAC) : 256k, 320k, puis plafond
        abaissé du dépassement (d'après ffmpeg-skill, MIT, scripts/loudness.py)."""
        nonlocal ceiling, bitrate, steps, rounds
        ceiling, bitrate, steps = a.tp, "192k", ["256k", "320k"]
        mode = encode(fixed)
        lufs, peak = ebur(dst)
        while peak is not None and peak > LIMIT and rounds < 5:
            rounds += 1
            if steps:
                bitrate = steps.pop(0)
                notes.append(f"crête {peak} dBTP après AAC : ré-encodage en {bitrate}")
            else:
                ceiling -= (peak - LIMIT) + 0.2
                notes.append(f"crête {peak} dBTP après AAC : plafond abaissé à {ceiling:.2f} dBTP")
            mode = encode(fixed)
            lufs, peak = ebur(dst)
        return mode, lufs, peak

    mode, lufs, peak = master()
    if mode == "dynamic":
        notes.append(f"plage {mj.get('input_lra')} LU > {LRA:g} (ou crête trop haute) : loudnorm en mode dynamique, plage resserrée")
        if lufs is not None and abs(lufs - a.lufs) > 1.0:  # cible ratée : gain fixe + limiteur, corrigé une fois
            notes.append(f"mode dynamique à {lufs} LUFS : repli gain fixe + limiteur")
            fixed = a.lufs - float(mj["input_i"])
            mode, lufs, peak = master(fixed)
            if lufs is not None and abs(lufs - a.lufs) > 0.5:
                mode, lufs, peak = master(fixed + a.lufs - lufs)
    ok = lufs is not None and abs(lufs - a.lufs) <= 1.0 and peak is not None and peak <= LIMIT
    out(ok=ok, final=str(dst), lufs=lufs, true_peak=peak, cible=f"{a.lufs} LUFS, crête ≤ {LIMIT:g} dBTP, plage ≤ {LRA:g} LU",
        verdict="OK" if ok else "À CORRIGER", mode={"linear": "linéaire", "dynamic": "dynamique"}.get(mode, mode),
        gain_depart=round(gain, 2), plage_mesuree=float(mj["input_lra"]) if mj else None, debit=bitrate,
        plafond=round(ceiling, 2), reprises=rounds, notes=notes or None)


if __name__ == "__main__":
    main()

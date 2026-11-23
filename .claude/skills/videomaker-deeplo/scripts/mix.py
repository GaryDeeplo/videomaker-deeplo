"""BAISSE AUTOMATIQUE DE LA MUSIQUE (ducking) : la musique descend quand quelqu'un parle et un peu sous chaque
bruitage, puis remonte dans les silences, avec des rampes douces (pas de « pompage »). Lu dans la composition :
voix (clip "voice" ou rush "a-roll"), bruitages (sound_design, sfx des monteurs) et musique (clip "music").

  python mix.py <job> [--voix -10] [--bruitages -4] [--off]

- Parole détectée sur l'énergie de la voix montée (trames de 20 ms), trous de moins de 0,45 s comblés ; la musique
  commence à descendre 0,12 s avant le premier mot et remonte en 0,5 s après le dernier.
- Sous un bruitage : -4 dB pendant ~0,4 s, pour qu'il se détache sans monter le son.
- La piste d'origine n'est jamais modifiée : assets/<slug>_music_mix.wav est écrit et la composition pointe dessus.
  Si add_music.py a déjà baissé la musique sous la voix (ancien lit sans <slug>_music_bed.wav), seule la partie
  bruitages s'applique (pas de double baisse).
Appelé par les monteurs après le sound design ("music": {"duck": false} dans la config pour s'en passer).
"""
import argparse
import re
import subprocess
from pathlib import Path

import numpy as np

from common import config, job_dir, out

SR = 48000
FR = 100  # résolution de la courbe (pas de 10 ms)


def decode(path, sr=SR, ch=2):
    p = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-vn", "-ac", str(ch), "-ar", str(sr), "-f", "f32le", "-"], capture_output=True)
    a = np.frombuffer(p.stdout, dtype=np.float32)
    return a.reshape(-1, ch) if ch > 1 else a


def attr(tag, name, default=None):
    m = re.search(rf'\b{name}="([^"]*)"', tag)
    return m.group(1) if m else default


def speech_intervals(voice_file, gap=0.45, min_len=0.12):
    """Intervalles de parole (s, dans le fichier) d'après l'énergie de la voix."""
    a = decode(voice_file, 16000, 1)
    if not len(a):
        return []
    hop = 320  # 20 ms
    n = len(a) // hop
    rms = np.sqrt(np.mean(a[:n * hop].reshape(n, hop) ** 2, axis=1) + 1e-12)
    db = 20 * np.log10(rms)
    loud = np.percentile(db, 90)
    on = db > max(-50.0, loud - 24)  # 24 dB sous les passages forts de la voix
    res, s = [], None
    for i, v in enumerate(on):
        t = i * 0.02
        if v and s is None:
            s = t
        elif not v and s is not None:
            res.append([s, t])
            s = None
    if s is not None:
        res.append([s, n * 0.02])
    merged = []
    for iv in res:
        if merged and iv[0] - merged[-1][1] < gap:
            merged[-1][1] = iv[1]
        else:
            merged.append(iv)
    return [iv for iv in merged if iv[1] - iv[0] >= min_len]


def envelope(n, speech, sfx, voice_db, sfx_db, attack=0.12, release=0.5):
    """Gain (linéaire) à FR Hz : bas sous la parole, petit creux sous les bruitages, rampes douces."""
    tgt = np.zeros(n)  # en dB
    for s, e in speech:
        a, b = max(0, int((s - attack) * FR)), min(n, int(e * FR))
        tgt[a:b] = np.minimum(tgt[a:b], voice_db)
    for t in sfx:
        a, b = max(0, int((t - 0.05) * FR)), min(n, int((t + 0.4) * FR))
        tgt[a:b] = np.minimum(tgt[a:b], sfx_db)
    # lissage asymétrique : descente en ~attack, remontée en ~release
    g = np.zeros(n)
    ka, kr = 1 - np.exp(-1 / (attack * FR / 2.5)), 1 - np.exp(-1 / (release * FR / 2.5))
    cur = 0.0
    for i in range(n):
        k = ka if tgt[i] < cur else kr
        cur += (tgt[i] - cur) * k
        g[i] = cur
    return 10 ** (g / 20)


def apply(job, html_text, voice_db=-10.0, sfx_db=-4.0):
    """-> (html modifié, rapport). Écrit assets/<slug>_music_mix.wav."""
    mt = re.search(r'<audio\b[^>]*\bid="music"[^>]*>', html_text)
    if not mt:
        return html_text, {"musique": False}
    mtag = mt.group(0)
    msrc = attr(mtag, "src")
    mstart = float(attr(mtag, "data-start", "0") or 0)
    src = job / msrc
    stem = re.sub(r"_music(_mix)?$", "", Path(msrc).stem)
    bed = job / "assets" / f"{stem}_music_bed.wav"
    orig = job / "assets" / f"{stem}_music.wav"
    base = bed if bed.exists() else (orig if orig.exists() else src)
    already_ducked = not bed.exists()  # ancien lit : déjà baissé sous la voix par add_music
    music = decode(base)
    if not len(music):
        return html_text, {"musique": False}
    n = int(len(music) / SR * FR) + 1
    # voix
    speech = []
    vt = re.search(r'<audio\b[^>]*\bid="voice"[^>]*>', html_text) or re.search(r'<video\b[^>]*\bid="a-roll"[^>]*>', html_text, re.S)
    if vt and not already_ducked:
        vsrc, vst = attr(vt.group(0), "src"), float(attr(vt.group(0), "data-start", "0") or 0)
        if vsrc and (job / vsrc).exists():
            speech = [[s + vst - mstart, e + vst - mstart] for s, e in speech_intervals(job / vsrc)]
    # bruitages (tout audio qui n'est ni la voix ni la musique)
    sfx = []
    for m in re.finditer(r"<audio\b[^>]*>", html_text):
        tag = m.group(0)
        if re.search(r'\bid="(voice|music)"', tag):
            continue
        st = attr(tag, "data-start")
        if st:
            sfx.append(float(st) - mstart + (0.12 if "whoosh" in tag or "swoosh" in tag else 0.0))
    g = envelope(n, speech, sfx, voice_db, sfx_db)
    gs = np.interp(np.arange(len(music)) / SR, np.arange(n) / FR, g).astype(np.float32)
    mixd = music * gs[:, None]
    dst = job / "assets" / f"{stem}_music_mix.wav"
    pcm = (np.clip(mixd, -1, 1) * 32767).astype("<i2").tobytes()
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "s16le", "-ar", str(SR), "-ac", "2", "-i", "-", str(dst)], input=pcm, check=True)
    new_tag = mtag.replace(f'src="{msrc}"', f'src="assets/{dst.name}"')
    html_text = html_text.replace(mtag, new_tag, 1)
    talk = sum(e - s for s, e in speech)
    return html_text, {"musique": True, "parole_s": round(talk, 1), "bruitages": len(sfx), "deja_baissee": already_ducked,
                       "fichier": f"assets/{dst.name}"}


def auto(job, html_text):
    c = config(job)
    mu = c.get("music", {})
    if mu.get("duck") is False:
        return html_text, None
    try:
        return apply(job, html_text, float(mu.get("duckDb", -10)), float(mu.get("sfxDuckDb", -4)))
    except Exception as e:  # noqa: BLE001  (le mixage ne doit jamais bloquer un montage)
        return html_text, {"erreur": str(e)[:200]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("job")
    ap.add_argument("--voix", type=float, default=-10.0, help="baisse sous la parole (dB)")
    ap.add_argument("--bruitages", type=float, default=-4.0, help="baisse sous un bruitage (dB)")
    ap.add_argument("--off", action="store_true", help="revenir à la musique sans baisse ajoutée")
    a = ap.parse_args()
    job = job_dir(a.job)
    p = job / "index.html"
    h = p.read_text(encoding="utf-8")
    if a.off:
        h2 = re.sub(r'(<audio\b[^>]*\bid="music"[^>]*\bsrc="assets/[^"]*?)_music_mix\.wav"', r'\1_music.wav"', h)
        p.write_text(h2, encoding="utf-8")
        out(ok=True, musique="d'origine")
        return
    h2, rep = apply(job, h, a.voix, a.bruitages)
    p.write_text(h2, encoding="utf-8")
    out(ok=True, **rep, suite="aperçu à écouter : la voix doit passer devant sans que la musique disparaisse")


if __name__ == "__main__":
    main()

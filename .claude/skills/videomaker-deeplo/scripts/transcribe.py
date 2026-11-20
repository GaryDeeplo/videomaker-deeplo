"""Transcription MOT À MOT -> work/<slug>_words.json

  python transcribe.py <job> <fichier> [--engine local|groq] [--lang fr] [--slug nom] [--from S --to S]

- local (défaut) : faster-whisper large-v3-turbo sur le CPU, rien ne quitte la machine (~3x temps réel).
- groq : whisper-large-v3-turbo chez Groq, plus rapide ; l'audio part chez Groq (accord du client requis).
Parakeet (npx hyperframes transcribe) a été écarté : il bascule en anglais au milieu du français.

Sortie : {"language","source","duration","text","words":[{"w","start","end"}]} en secondes absolues du fichier.
"""
import argparse
import os
import tempfile
import time
from pathlib import Path

from common import config, fail, job_dir, out, probe, sh, write_json


def extract(src, wav, t0=None, t1=None):
    cmd = ["ffmpeg", "-y", "-loglevel", "error"]
    if t0 is not None:
        cmd += ["-ss", str(t0)]
    if t1 is not None:
        cmd += ["-to", str(t1)]
    sh(cmd + ["-i", str(src), "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(wav)], "ffmpeg (audio)")


# Whisper « nettoie » les hésitations ; un amorçage qui en contient lui fait écrire les « euh » et les répétitions,
# ce qui permet au dérush de les retirer (cut_plan.py).
VERBATIM = {"fr": "Euh, alors, hum, je, je pense que, ben, euh, du coup voilà, hein.",
            "nl": "Eh, dus, uhm, ik, ik denk dat, eh, nou ja.",
            "en": "Um, so, uh, I, I think that, like, you know, uh."}


def prompt_for(lang, vocab):
    """Amorçage : hésitations (mot pour mot) + noms propres de la marque (orthographe : « Claude », pas « Cloud »)."""
    return (VERBATIM.get(lang, "") + (" " + ", ".join(vocab) + "." if vocab else "")).strip() or None


def local(wav, lang, model, prompt=None):
    import numpy as np
    from scipy.io import wavfile
    from faster_whisper import WhisperModel

    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
    _, a = wavfile.read(wav)
    a = a.astype(np.float32) / 32768.0  # tableau en mémoire : évite le décodeur PyAV (incompatible ici)
    m = WhisperModel(model, device="cpu", compute_type="int8", cpu_threads=os.cpu_count() or 4)
    segs, _ = m.transcribe(a, language=lang, word_timestamps=True, condition_on_previous_text=False,
                           initial_prompt=prompt)
    return [{"w": w.word.strip(), "start": float(w.start), "end": float(w.end)}
            for s in segs for w in (s.words or []) if w.word.strip()]


def groq(wav, lang, prompt=None):
    import requests

    key = os.environ.get("GROQ_API_KEY", "")
    kf = Path.home() / ".config" / "groq" / "api_key"
    if not key and kf.exists():
        key = kf.read_text(encoding="utf-8").strip()
    if not key:
        fail("GROQ_API_KEY absente")
    flac = Path(wav).with_suffix(".flac")
    sh(["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav), "-c:a", "flac", str(flac)])
    if flac.stat().st_size > 24 * 1024 * 1024:
        fail("audio > 24 Mo : découpe avec --from/--to ou utilise --engine local")
    with open(flac, "rb") as f:
        r = requests.post("https://api.groq.com/openai/v1/audio/transcriptions",
                          headers={"Authorization": f"Bearer {key}"},
                          files={"file": (flac.name, f, "audio/flac")},
                          data={"model": "whisper-large-v3-turbo", "language": lang,
                                "response_format": "verbose_json", "prompt": prompt or "",
                                "timestamp_granularities[]": ["word", "segment"]}, timeout=600)
    if r.status_code != 200:
        fail(f"Groq HTTP {r.status_code}", body=r.text[:500])
    d = r.json()
    words = [{"w": w["word"].strip(), "start": float(w["start"]), "end": float(w["end"])}
             for w in d.get("words", []) if w["word"].strip()]
    return punctuate(words, d.get("segments", []))


def punctuate(words, segments):
    """Groq rend les mots sans ponctuation : on la reprend du texte des segments, mot par mot."""
    toks = [t for s in segments for t in s.get("text", "").split()]
    norm = lambda s: "".join(c for c in s.lower() if c.isalnum())
    i = 0
    for w in words:
        for j in range(i, min(i + 4, len(toks))):
            if norm(toks[j]) == norm(w["w"]):
                w["w"], i = toks[j], j + 1
                break
    return words


def glue(words):
    """Whisper découpe « qu'elle » en « qu » + « 'elle » et « vendeur-commerçant » en deux : on recolle."""
    res = []
    for w in words:
        if res and len(w["w"]) > 1 and (w["w"][:1] in "'’-" or (w["w"][0] in ",." and w["w"][1].isdigit()
                                                                  and res[-1]["w"][-1:].isdigit())):  # « 3 ,5 » -> « 3,5 »
            res[-1]["w"] += w["w"]
            res[-1]["end"] = w["end"]
        else:
            res.append(dict(w))
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("job")
    ap.add_argument("source")
    ap.add_argument("--engine", choices=["local", "groq"])
    ap.add_argument("--lang")
    ap.add_argument("--slug")
    ap.add_argument("--from", dest="t0", type=float)
    ap.add_argument("--to", dest="t1", type=float)
    a = ap.parse_args()
    job = job_dir(a.job)
    c = config(job)
    src = Path(a.source)
    if not src.is_absolute():
        src = (job / "inbox" / src) if (job / "inbox" / src).exists() else src.resolve()
    if not src.exists():
        fail(f"introuvable : {src}")
    slug = a.slug or src.stem
    lang = a.lang or c["language"]
    engine = a.engine or c["transcribe"]["engine"]

    t = time.time()
    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / "a.wav"
        extract(src, wav, a.t0, a.t1)
        pr = prompt_for(lang, c["transcribe"].get("vocabulary", []))
        words = local(wav, lang, c["transcribe"]["model"], pr) if engine == "local" else groq(wav, lang, pr)
    if not words:
        fail("aucun mot transcrit (pas de voix, ou mauvaise langue ?)")
    words = glue(words)
    off = a.t0 or 0.0
    for w in words:
        w["start"], w["end"] = round(w["start"] + off, 3), round(max(w["end"], w["start"] + 0.05) + off, 3)

    info = probe(src)
    dst = job / "work" / f"{slug}_words.json"
    write_json(dst, {"language": lang, "engine": engine, "source": str(src), "duration": round(info["duration"], 3),
                     "range": [a.t0, a.t1], "text": " ".join(w["w"] for w in words), "words": words})
    el = time.time() - t
    span = (a.t1 or info["duration"]) - off
    out(ok=True, slug=slug, engine=engine, words=len(words), duration=round(span, 1), elapsed=round(el, 1),
        vitesse=f"x{round(span / max(el, .01), 1)} temps réel", out=str(dst))


if __name__ == "__main__":
    main()

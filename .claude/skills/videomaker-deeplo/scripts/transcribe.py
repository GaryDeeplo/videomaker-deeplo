"""Transcription MOT À MOT -> work/<slug>_words.json

  python transcribe.py <job> <fichier> [--engine local|groq] [--lang fr] [--slug nom] [--from S --to S] [--islands]

- local (défaut) : faster-whisper large-v3-turbo sur le CPU, rien ne quitte la machine (~3x temps réel).
- groq : whisper-large-v3-turbo chez Groq, plus rapide ; l'audio part chez Groq (accord du client requis).
Parakeet (npx hyperframes transcribe) a été écarté : il bascule en anglais au milieu du français.

--islands (local) : l'audio est d'abord découpé en îlots de parole (VAD Silero de faster-whisper, pauses >= 0,3 s),
chaque îlot est transcrit seul. Sur un fichier entier, Whisper « lisse » les reprises (la phrase recommencée
disparaît ou se fond dans la bonne) ; îlot par îlot, la fausse prise reste écrite et cut_plan.py la repère (restart).
Plus lent (un passage d'encodeur par îlot). Défaut : transcribe.islands de la config (sinon non) ; --no-islands force.

Sortie : {"language","source","duration","text","words":[{"w","start","end"}]} en secondes absolues du fichier.
Avec --islands, en plus : "islands":[{"id","start","end","text"}] (bornes du VAD) et "island" sur chaque mot.
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


def _load(wav, model):
    import numpy as np
    from scipy.io import wavfile
    from faster_whisper import WhisperModel

    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
    _, a = wavfile.read(wav)
    a = a.astype(np.float32) / 32768.0  # tableau en mémoire : évite le décodeur PyAV (incompatible ici)
    return a, WhisperModel(model, device="cpu", compute_type="int8", cpu_threads=os.cpu_count() or 4)


def local(wav, lang, model, prompt=None):
    a, m = _load(wav, model)
    segs, _ = m.transcribe(a, language=lang, word_timestamps=True, condition_on_previous_text=False,
                           initial_prompt=prompt)
    return [{"w": w.word.strip(), "start": float(w.start), "end": float(w.end)}
            for s in segs for w in (s.words or []) if w.word.strip()]


SR = 16000
ISL_PAUSE, ISL_PAD, ISL_MIN = 0.3, 0.15, 0.15  # pause qui sépare deux îlots, marge de décodage, îlot minimal (s)


def speech_islands(a):
    """Îlots de parole mesurés par le VAD Silero livré avec faster-whisper (aucune dépendance en plus).
    Pause de 0,3 s : la valeur testée par ghost-editor (MIT) ; à 0,7 s une reprise rapide partage l'îlot d'avant."""
    from faster_whisper.vad import VadOptions, get_speech_timestamps

    import numpy as np

    opts = VadOptions(min_silence_duration_ms=int(ISL_PAUSE * 1000), speech_pad_ms=60,
                      min_speech_duration_ms=int(ISL_MIN * 1000))
    vad = [(t["start"] / SR, t["end"] / SR) for t in get_speech_timestamps(a, opts)]
    # musique ou ambiance sous la voix : Silero peut rendre un îlot de 50 s. On le recoupe aux creux d'énergie
    # de 0,3 s et plus (enveloppe RMS 10 ms, seuil = 8e centile + 14 dB, d'après ghost-editor subcheck.py, MIT).
    hop = SR // 100
    rms = np.sqrt(np.convolve(a.astype(np.float64) ** 2, np.ones(2 * hop) / (2 * hop), "same")[::hop])
    db = 20 * np.log10(rms + 1e-9)
    loud = db > np.percentile(db, 8) + 14
    res = []
    for s, e in vad:
        f0, f1 = int(s * 100), min(len(loud), int(e * 100) + 1)
        cur, k = s, f0
        while k < f1:
            if loud[k]:
                k += 1
                continue
            q = k
            while q < f1 and not loud[q]:
                q += 1
            if q - k >= ISL_PAUSE * 100 and k > f0 and q < f1:  # creux intérieur : fin d'un îlot, début du suivant
                if k / 100 - cur >= ISL_MIN:
                    res.append((cur, k / 100))
                cur = q / 100
            k = q
        if e - cur >= ISL_MIN:
            res.append((cur, e))
    return res


def local_islands(wav, lang, model, prompt=None):
    """Chaque îlot transcrit seul, sans le contexte du précédent (d'après ghost-editor, islands_tx.py, MIT) :
    une phrase recommencée reste écrite deux fois au lieu d'être fusionnée. Mots en secondes du wav."""
    a, m = _load(wav, model)
    isl = speech_islands(a)
    dur = len(a) / SR
    words, islands = [], []
    for k, (s, e) in enumerate(isl):
        # marge de 0,15 s pour ne pas rogner la 1re syllabe, sans déborder à mi-chemin des îlots voisins
        a0 = max(0.0, s - ISL_PAD, (isl[k - 1][1] + s) / 2 if k else 0.0)
        b0 = min(dur, e + ISL_PAD, (e + isl[k + 1][0]) / 2 if k + 1 < len(isl) else dur)
        # amorçage fixe (hésitations + vocabulaire), jamais le texte de l'îlot d'avant : testé, il fait sauter la
        # reprise (« … et vous avez… | Vous avez peut-être » devenait « … | peut-être »)
        segs, _ = m.transcribe(a[int(a0 * SR):int(b0 * SR)], language=lang, word_timestamps=True,
                               condition_on_previous_text=False, temperature=(0.0, 0.2), initial_prompt=prompt)
        ws = []
        for sg in segs:
            if sg.no_speech_prob > 0.8:  # souffle, clic : Whisper inventerait une phrase
                continue
            ws += [{"w": w.word.strip(), "start": round(min(b0, a0 + w.start), 3),
                    "end": round(min(b0, a0 + w.end), 3), "island": len(islands)}
                   for w in (sg.words or []) if w.word.strip()]
        if ws:
            islands.append({"id": len(islands), "start": round(s, 3), "end": round(e, 3),
                            "text": " ".join(w["w"] for w in ws)})
            words += ws
    return words, islands


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
        same = res and res[-1].get("island") == w.get("island")  # jamais d'un îlot à l'autre (--islands)
        if same and len(w["w"]) > 1 and (w["w"][:1] in "'’-" or (w["w"][0] in ",." and w["w"][1].isdigit()
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
    ap.add_argument("--islands", action=argparse.BooleanOptionalAction, default=None,
                    help="transcrire îlot par îlot (reprises gardées, cut_plan les repère) ; local seulement")
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
    isl_mode = a.islands if a.islands is not None else bool(c["transcribe"].get("islands", False))
    if isl_mode and engine != "local":
        if a.islands:
            fail("--islands : transcription locale seulement (--engine local)")
        isl_mode = False  # défaut de la config : ignoré pour Groq

    t = time.time()
    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / "a.wav"
        extract(src, wav, a.t0, a.t1)
        pr = prompt_for(lang, c["transcribe"].get("vocabulary", []))
        islands = None
        if engine == "groq":
            words = groq(wav, lang, pr)
        elif isl_mode:
            words, islands = local_islands(wav, lang, c["transcribe"]["model"], pr)
        else:
            words = local(wav, lang, c["transcribe"]["model"], pr)
    if not words:
        fail("aucun mot transcrit (pas de voix, ou mauvaise langue ?)")
    words = glue(words)
    off = a.t0 or 0.0
    for w in words:
        w["start"], w["end"] = round(w["start"] + off, 3), round(max(w["end"], w["start"] + 0.05) + off, 3)
    extra = {}
    if islands is not None:
        for i in islands:
            i["start"], i["end"] = round(i["start"] + off, 3), round(i["end"] + off, 3)
            i["text"] = " ".join(w["w"] for w in words if w["island"] == i["id"])
        extra = {"mode": "islands", "islands": islands}

    info = probe(src)
    dst = job / "work" / f"{slug}_words.json"
    write_json(dst, {"language": lang, "engine": engine, "source": str(src), "duration": round(info["duration"], 3),
                     "range": [a.t0, a.t1], "text": " ".join(w["w"] for w in words), "words": words, **extra})
    el = time.time() - t
    span = (a.t1 or info["duration"]) - off
    out(ok=True, slug=slug, engine=engine, mode="islands" if islands is not None else "fichier entier",
        **({"islands": len(islands)} if islands is not None else {}), words=len(words), duration=round(span, 1), elapsed=round(el, 1),
        vitesse=f"x{round(span / max(el, .01), 1)} temps réel", out=str(dst))


if __name__ == "__main__":
    main()

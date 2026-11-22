"""VOIX OFF d'un storyboard -> assets/<slug>_voice.wav + work/<slug>_{words,map,timing}.json

  python voice.py <job> <slug> [--engine gemini|fish|local] [--voice NOM] [--style "d'une voix calme"] [--speed 1.0]
  python voice.py <job> <slug> --file <audio ou vidéo> [--denoise]    # voix off ENREGISTRÉE (mémo, micro, vidéo)

--file : la voix vient d'un enregistrement (audio, ou le son d'une vidéo). Elle est transcrite (local), chaque champ
"voice" du storyboard est retrouvé dans l'enregistrement et les scènes se calent dessus ; l'orthographe vient du
storyboard. Pas encore de storyboard, ou des scènes sans "voice" : l'outil écrit work/<slug>_voice_phrases.txt (ce
qui est dit, phrase par phrase) pour que Claude écrive le storyboard avec les MÊMES mots, puis on relance.
Une scène sans voix n'est possible qu'au début (intro) ou à la fin (outro) : on ne coupe pas dans l'enregistrement.

Lit work/<slug>_storyboard.json (écrit par Claude, voir references/storyboard.md). Chaque scène qui a un
champ "voice" devient une phrase de voix off :
- gemini (défaut si GEMINI_API_KEY) : Gemini TTS (Google AI Studio, quota gratuit), voix = voice.geminiVoice
  (Kore, Sulafat, Vindemiatrix, Charon…), ton dit en français par voice.geminiStyle ou --style ; attention : en
  gratuit, Google peut utiliser les textes envoyés pour améliorer ses modèles (pas de données confidentielles) ;
- fish (si FISH_API_KEY) : Fish Audio /v1/tts, voix = config voice.fishVoice (reference_id) ou --voice (clonage) ;
- local : Kokoro dans HyperFrames (voix française ff_siwis), gratuit, pour tester ou dépanner.
Chaque phrase est mise en cache (work/tts_cache/) : on ne paie jamais deux fois la même phrase, et on peut
refaire une seule phrase en changeant son texte.

Les temps des scènes viennent de la durée réelle des phrases (déterministe) ; les mots sont horodatés en
retranscrivant la voix (faster-whisper local), puis remplacés par le texte du script quand le compte est bon,
pour une orthographe exacte. Sorties compatibles avec build_text.py et add_music.py (map.json identité).
"""
import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path

from common import config, env_key, fail, job_dir, out, probe, read_json, sh, write_json

LEAD, TAIL = 0.35, 0.6  # silence avant la première phrase et après la dernière


def fish(text, dst, voice, speed, model):
    import requests

    key = env_key("FISH_API_KEY")
    if not key:
        fail("FISH_API_KEY vide dans .env (ou utilise --engine local)")
    body = {"text": text, "format": "wav", "latency": "normal", "prosody": {"speed": speed, "volume": 0}}
    if voice:
        body["reference_id"] = voice
    r = requests.post("https://api.fish.audio/v1/tts", json=body, timeout=180,
                      headers={"Authorization": f"Bearer {key}", "model": model})
    if r.status_code != 200 or len(r.content) < 1000:
        fail(f"Fish Audio HTTP {r.status_code}", body=r.text[:400])
    Path(dst).write_bytes(r.content)


def gemini(text, dst, voice, style, model):
    """Gemini TTS : PCM 16 bits 24 kHz mono renvoyé en base64 -> wav. Relance si le quota par minute est atteint."""
    import base64
    import time
    import wave

    import requests

    key = env_key("GEMINI_API_KEY")
    if not key:
        fail("GEMINI_API_KEY vide dans .env (clé gratuite : aistudio.google.com/apikey)")
    prompt = f"{style.strip().rstrip(':')} : {text}" if style else text
    body = {"contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseModalities": ["AUDIO"],
                                 "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice or "Kore"}}}}}
    base = "https://generativelanguage.googleapis.com/v1beta/models/"
    for attempt in range(6):
        r = requests.post(f"{base}{model}:generateContent", json=body, timeout=180, headers={"x-goog-api-key": key})
        if r.status_code == 404 and attempt == 0:  # modèle renommé : on prend le TTS « flash » disponible
            names = [m["name"].split("/")[-1] for m in requests.get(base.rstrip("/"), headers={"x-goog-api-key": key},
                                                                     timeout=30).json().get("models", [])]
            tts = [n for n in names if "tts" in n and "flash" in n] or [n for n in names if "tts" in n]
            if not tts:
                fail("aucun modèle Gemini TTS disponible pour cette clé")
            model = tts[0]
            continue
        if r.status_code in (429, 500, 503):
            time.sleep(8 + 8 * attempt)
            continue
        break
    if r.status_code != 200:
        fail(f"Gemini TTS HTTP {r.status_code}", body=r.text[:400])
    try:
        part = r.json()["candidates"][0]["content"]["parts"][0]["inlineData"]
    except (KeyError, IndexError):
        fail("Gemini TTS : pas d'audio dans la réponse", body=r.text[:400])
    pcm = base64.b64decode(part["data"])
    rate = int(next((x.split("=")[1] for x in part.get("mimeType", "").split(";") if x.strip().startswith("rate=")), 24000))
    with wave.open(str(dst), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm)


def kokoro(text, dst, voice, speed):
    os.environ.setdefault("HYPERFRAMES_PYTHON", sys.executable)
    res = sh(["npx", "--yes", "hyperframes@0.9.71", "tts", text, "-v", voice or "ff_siwis", "-s", str(speed),
              "-o", str(dst), "--json"] if os.name != "nt" else
             ["cmd", "/c", "npx", "--yes", "hyperframes@0.9.71", "tts", text, "-v", voice or "ff_siwis",
              "-s", str(speed), "-o", str(dst), "--json"], "hyperframes tts")
    if '"ok":true' not in res.replace(" ", ""):
        fail("tts local a échoué", out=res[-400:])


def merge_split(ws, toks):
    """Recolle deux mots transcrits quand ensemble ils font un mot du script (« Insta » + « gram » -> « Instagram »)."""
    n = lambda t: "".join(ch for ch in t.lower() if ch.isalnum())
    keys, out_ = {n(t) for t in toks}, []
    i = 0
    while i < len(ws):
        if i + 1 < len(ws) and n(ws[i]["w"]) not in keys and n(ws[i]["w"]) + n(ws[i + 1]["w"]) in keys:
            out_.append({**ws[i], "w": ws[i]["w"] + ws[i + 1]["w"], "end": ws[i + 1]["end"]})
            i += 2
            continue
        out_.append(ws[i])
        i += 1
    return out_


def from_file(a, job, c, sb_path):
    """Voix off enregistrée -> mêmes sorties que la voix de synthèse (voice.wav, words, map, timing)."""
    import difflib

    from transcribe import glue, local, prompt_for

    src = Path(a.file)
    if not src.is_absolute():
        src = (job / "inbox" / src) if (job / "inbox" / src).exists() else src.resolve()
    if not src.exists():
        fail(f"fichier introuvable : {a.file}")
    if not probe(src).get("has_audio"):
        fail("ce fichier n'a pas de son")
    with tempfile.TemporaryDirectory() as tmp:
        w16 = Path(tmp) / "a.wav"
        sh(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(w16)])
        ws = glue(local(w16, c["language"], c["transcribe"]["model"],
                        prompt_for(c["language"], c["transcribe"].get("vocabulary", []))))
    if not ws:
        fail("aucune parole reconnue dans l'enregistrement")
    sb = read_json(sb_path) if sb_path.exists() else {"scenes": []}
    voiced = [i for i, sc in enumerate(sb["scenes"]) if (sc.get("voice") or "").strip()]
    if not voiced:  # Claude doit d'abord écrire le storyboard avec les phrases dites
        phrases, cur = [], []
        for w in ws:
            cur.append(w["w"])
            if re.search(r"[.!?…]$", w["w"]):
                phrases.append(" ".join(cur))
                cur = []
        if cur:
            phrases.append(" ".join(cur))
        txt = job / "work" / f"{a.slug}_voice_phrases.txt"
        txt.write_text("\n".join(f"{k + 1}. {p}" for k, p in enumerate(phrases)), encoding="utf-8")
        return out(ok=True, a_faire="écris le storyboard : un champ voice par scène = la ou les phrases dites, mots identiques",
                   phrases=phrases, fichier=str(txt))
    if any(i not in voiced for i in range(voiced[0], voiced[-1] + 1)):
        fail("une scène sans voix au milieu : impossible avec une voix enregistrée (déplace-la au début ou à la fin, "
             "ou donne-lui une phrase de l'enregistrement)")
    n = lambda t: "".join(ch for ch in t.lower() if ch.isalnum())
    script, owner = [], []
    for i in voiced:
        for t in tokens(sb["scenes"][i]["voice"]):
            script.append(t)
            owner.append(i)
    ws = merge_split(ws, script)
    sm = difflib.SequenceMatcher(a=[n(x["w"]) for x in ws], b=[n(t) for t in script], autojunk=False)
    first, last = {}, {}
    for bl in sm.get_matching_blocks():
        for k in range(bl.size):
            sc_i, wi = owner[bl.b + k], bl.a + k
            first.setdefault(sc_i, wi)
            last[sc_i] = wi
    missing = [i for i in voiced if i not in first]
    if missing:
        fail("phrases du storyboard introuvables dans l'enregistrement", scenes=missing,
             conseil="copie les phrases dites telles quelles (voice_phrases.txt), sans les reformuler")
    respell(ws, script)
    lead_holds = sum(float(sb["scenes"][i].get("hold", 2.0)) for i in range(voiced[0]))
    O = round(lead_holds + LEAD - ws[first[voiced[0]]]["start"], 3)  # décalage de l'enregistrement dans la vidéo
    trim = max(0.0, -O)
    timing = []
    for i, sc in enumerate(sb["scenes"]):
        if i < voiced[0]:
            st = sum(float(sb["scenes"][k].get("hold", 2.0)) for k in range(i))
            timing.append({"scene": i, "start": round(st, 3), "voice_start": None})
        elif i in first:
            vs = ws[first[i]]["start"] + O
            timing.append({"scene": i, "start": round(lead_holds if i == voiced[0] else max(0.0, vs - 0.15), 3),
                           "voice_start": round(vs, 3)})
        else:  # scènes de fin (outro) : après la dernière phrase, chacune pendant son "hold"
            st = (ws[last[voiced[-1]]]["end"] + O + TAIL if i == voiced[-1] + 1
                  else timing[-1]["start"] + float(sb["scenes"][i - 1].get("hold", 2.0)))
            timing.append({"scene": i, "start": round(st, 3), "voice_start": None})
    total = round(timing[-1]["start"] + float(sb["scenes"][-1].get("hold", 2.0)) if timing[-1]["voice_start"] is None
                  else ws[last[voiced[-1]]]["end"] + O + TAIL, 3)
    for i, tm in enumerate(timing):
        tm["end"] = timing[i + 1]["start"] if i + 1 < len(timing) else total
    dst = job / "assets" / f"{a.slug}_voice.wav"
    pre = ",afftdn=nf=-25" if a.denoise else ""
    af = (f"atrim=start={trim},asetpts=PTS-STARTPTS," if trim else "") + \
         f"adelay={int(max(0.0, O) * 1000)}{pre},apad=whole_dur={total},atrim=end={total}," + \
         f"loudnorm=I={c['derush']['voiceLufs']}:TP=-1.5:LRA=11,aresample=48000"
    sh(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-vn", "-ac", "1", "-af", af, "-c:a", "pcm_s16le", str(dst)],
       "ffmpeg (voix enregistrée)")
    words = [{"w": w["w"], "start": round(w["start"] + O, 3), "end": round(w["end"] + O, 3)} for w in ws
             if w["start"] + O >= 0 and w["end"] + O <= total]
    dur = probe(dst)["duration"]
    write_json(job / "work" / f"{a.slug}_words.json",
               {"language": c["language"], "engine": "enregistrement", "source": str(dst), "duration": dur,
                "range": [None, None], "text": " ".join(w["w"] for w in words), "words": words})
    write_json(job / "work" / f"{a.slug}_map.json",
               {"slug": a.slug, "cut": str(dst), "out_duration": round(dur, 3),
                "segments": [{"src_start": 0.0, "src_end": round(dur, 3), "out_start": 0.0, "out_end": round(dur, 3)}]})
    write_json(job / "work" / f"{a.slug}_timing.json", {"engine": "enregistrement", "voice": src.name, "duration": dur,
                                                        "scenes": timing})
    hors = [w["w"] for w in ws if w["end"] < ws[first[voiced[0]]]["start"] or w["start"] > ws[last[voiced[-1]]]["end"]]
    out(ok=True, engine="enregistrement", source=src.name, duree=round(dur, 1), mots=len(words), scenes_calees=len(first),
        hors_storyboard=" ".join(hors)[:200] or None, voix=str(dst), suite="build_text.py, add_music.py, puis build_scenes.py")


def pronounce(text, lex):
    """Lexique de prononciation de la marque (video.voice.pronunciation) : seule la voix de synthèse lit la forme
    phonétique ; sous-titres et orthographe gardent le texte du storyboard."""
    for word, say in (lex or {}).items():
        text = re.sub(rf"(?<!\w){re.escape(word)}(?!\w)", say, text, flags=re.I)
    return text


def tokens(text):
    return [t for t in re.split(r"\s+", text.strip()) if re.search(r"\w", t)]


def respell(ws, toks):
    """Reprend l'orthographe du script sur les mots transcrits (alignement difflib, blocs de même longueur).
    Renvoie True si toute la phrase a été alignée."""
    import difflib

    n = lambda t: "".join(ch for ch in t.lower() if ch.isalnum())
    sm = difflib.SequenceMatcher(a=[n(x["w"]) for x in ws], b=[n(t) for t in toks], autojunk=False)
    full = True
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal" or (op == "replace" and i2 - i1 == j2 - j1):
            for x, tk in zip(ws[i1:i2], toks[j1:j2]):
                x["w"] = tk
        elif op == "replace" and i2 - i1 == 1:  # « 1h60 » transcrit pour « une heure, soixante euros » : le texte du script
            ws[i1]["w"] = " ".join(toks[j1:j2])
        else:
            full = False
    return full


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("job")
    ap.add_argument("slug")
    ap.add_argument("--engine", choices=["gemini", "fish", "local"])
    ap.add_argument("--file", help="voix off enregistrée : fichier audio ou vidéo (son gardé)")
    ap.add_argument("--denoise", action="store_true", help="réduit le souffle d'un enregistrement au téléphone")
    ap.add_argument("--style", help="ton de la voix, en français (Gemini) : « d'une voix calme et douce »")
    ap.add_argument("--voice")
    ap.add_argument("--speed", type=float)
    a = ap.parse_args()
    job = job_dir(a.job)
    c = config(job)
    vc = c.get("voice", {})
    sb_path = job / "work" / f"{a.slug}_storyboard.json"
    if a.file:
        return from_file(a, job, c, sb_path)
    if not sb_path.exists():
        fail(f"{sb_path} absent : écris d'abord le storyboard")
    sb = read_json(sb_path)
    engine = a.engine or ("gemini" if env_key("GEMINI_API_KEY") else "fish" if env_key("FISH_API_KEY") else "local")
    voice = a.voice or {"gemini": vc.get("geminiVoice", "Kore"), "fish": vc.get("fishVoice")}.get(engine, vc.get("localVoice", "ff_siwis"))
    style = a.style if a.style is not None else vc.get("geminiStyle", "")
    speed = a.speed or vc.get("speed", 1.0)
    pause = vc.get("pause", 0.3)
    cache = job / "work" / "tts_cache"
    cache.mkdir(parents=True, exist_ok=True)

    # 1. une phrase par scène (cache par contenu)
    lines, made = [], 0
    for i, sc in enumerate(sb["scenes"]):
        text = (sc.get("voice") or "").strip()
        if not text:
            lines.append(None)
            continue
        spoken = pronounce(text, vc.get("pronunciation"))
        h = hashlib.sha1(json.dumps([engine, voice, speed, spoken] + ([style] if engine == "gemini" else []),
                                    ensure_ascii=False).encode()).hexdigest()[:12]
        wav = cache / f"{h}.wav"
        if not wav.exists():
            if engine == "gemini":
                gemini(spoken, wav, voice, style, vc.get("geminiModel", "gemini-2.5-flash-preview-tts"))
            elif engine == "fish":
                fish(spoken, wav, voice, speed, vc.get("fishModel", "s2-pro"))
            else:
                kokoro(spoken, wav, voice, speed)
            made += 1
        lines.append({"text": text, "wav": wav, "dur": probe(wav)["duration"]})

    # 2. assemblage : temps déterministes à partir des durées réelles
    t, timing, parts = LEAD, [], []
    for i, (sc, ln) in enumerate(zip(sb["scenes"], lines)):
        start = t
        if ln:
            ln["start"] = t
            t += ln["dur"]
            parts.append(ln)
        hold = float(sc.get("hold", 0 if ln else 2.0))
        t += hold + (pause if ln else 0)
        timing.append({"scene": i, "start": round(start if i else 0.0, 3), "voice_start": round(ln["start"], 3) if ln else None})
    total = round(t - pause + TAIL if parts else t, 3)
    for i, tm in enumerate(timing):
        tm["end"] = timing[i + 1]["start"] if i + 1 < len(timing) else total
    if not parts:
        fail("aucune scène n'a de champ voice")

    dst = job / "assets" / f"{a.slug}_voice.wav"
    inputs, fc = [], []
    for k, ln in enumerate(parts):
        inputs += ["-i", str(ln["wav"])]
        fc.append(f"[{k}:a]aresample=48000,aformat=channel_layouts=mono,adelay={int(ln['start'] * 1000)}[d{k}]")
    fc.append("".join(f"[d{k}]" for k in range(len(parts))) +
              f"amix=inputs={len(parts)}:normalize=0,apad=whole_dur={total},atrim=end={total},"
              f"loudnorm=I={c['derush']['voiceLufs']}:TP=-1.5:LRA=11,aresample=48000[v]")
    fd, script = tempfile.mkstemp(suffix=".txt")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(";".join(fc))
    try:
        sh(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex_script", script, "-map", "[v]",
            "-c:a", "pcm_s16le", str(dst)], "ffmpeg (voix)")
    finally:
        Path(script).unlink(missing_ok=True)

    # 3. mots horodatés : whisper sur chaque phrase, texte du script quand le compte de mots concorde
    import numpy as np
    from faster_whisper import WhisperModel
    from scipy.io import wavfile

    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
    model = WhisperModel(c["transcribe"]["model"], device="cpu", compute_type="int8", cpu_threads=os.cpu_count() or 4)
    words, exact = [], 0
    with tempfile.TemporaryDirectory() as tmp:
        for ln in parts:
            w16 = Path(tmp) / "l.wav"
            sh(["ffmpeg", "-y", "-loglevel", "error", "-i", str(ln["wav"]), "-ac", "1", "-ar", "16000", str(w16)])
            _, au = wavfile.read(w16)
            segs, _ = model.transcribe(au.astype(np.float32) / 32768.0, language=c["language"], word_timestamps=True)
            ws = [{"w": x.word.strip(), "start": round(ln["start"] + x.start, 3), "end": round(ln["start"] + x.end, 3)}
                  for s in segs for x in (s.words or []) if x.word.strip()]
            from transcribe import glue
            ws = merge_split(glue(ws), tokens(ln["text"]))
            if respell(ws, tokens(ln["text"])):
                exact += 1
            words += ws

    dur = probe(dst)["duration"]
    write_json(job / "work" / f"{a.slug}_words.json",
               {"language": c["language"], "engine": f"tts:{engine}", "source": str(dst), "duration": dur,
                "range": [None, None], "text": " ".join(w["w"] for w in words), "words": words})
    write_json(job / "work" / f"{a.slug}_map.json",
               {"slug": a.slug, "cut": str(dst), "out_duration": round(dur, 3),
                "segments": [{"src_start": 0.0, "src_end": round(dur, 3), "out_start": 0.0, "out_end": round(dur, 3)}]})
    write_json(job / "work" / f"{a.slug}_timing.json", {"engine": engine, "voice": voice, "duration": dur, "scenes": timing})
    out(ok=True, engine=engine, voice=voice, phrases=len(parts), generees=made, en_cache=len(parts) - made,
        duree=round(dur, 1), mots=len(words), orthographe_du_script=f"{exact}/{len(parts)} phrases",
        voix=str(dst), suite="build_text.py, add_music.py, puis build_scenes.py")


if __name__ == "__main__":
    main()

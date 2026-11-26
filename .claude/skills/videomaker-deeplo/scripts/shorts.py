"""UNE LONGUE VIDÉO -> PLUSIEURS SHORTS (interview, webinaire, live, podcast filmé)

  python shorts.py sentences <job> <slug>     # phrases numérotées -> work/<slug>_sentences.txt (à lire en entier)
  #   Claude choisit les passages : work/<slug>_shorts.json (numéros de phrases, JAMAIS de timecodes)
  python shorts.py make <job> <slug> [--mode captions|overlays|both|none] [--style <style>] [--mood upbeat] [--size 9:16]
  #   --style : tous les styles de sous-titres de build_composition.py (STYLES : pop, karaoke, minimal, boite, impact,
  #   duo, mono, bulle, souligne, geant, editorial…)

work/<slug>_shorts.json :
  {"shorts": [{"name": "devenir-manager", "from": 12, "to": 18, "skip": [15],
               "hook": "Comment devenir manager ?", "why": "promesse claire, chiffre concret, se suffit à lui-même",
               "post": {"caption": "…", "hashtags": ["…"], "cta": "…"}}]}
Chaque short devient un job enfant jobs/<job>-<name>/ (même charte) : plan de coupe aux bords des phrases
(milieu du blanc entre deux mots, jamais dans un mot), dérush, sous-titres, accroche en titre les 3 premières
secondes, musique facultative, composition. Ensuite : check + snapshot, puis deliver.py sur chaque job enfant.
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
import os
from pathlib import Path

from common import ROOT, fail, job_dir, out, read_json, write_json

HERE = Path(__file__).resolve().parent
STRONG = re.compile(r"[.!?…]$")
PAD = 0.3  # marge maximale avant / après une phrase


def sentences(words):
    res, cur = [], []
    for i, w in enumerate(words):
        cur.append(i)
        nxt = words[i + 1] if i + 1 < len(words) else None
        if STRONG.search(w["w"]) or nxt is None or nxt["start"] - w["end"] > 1.2:
            res.append(cur)
            cur = []
    return [{"id": k, "w0": s[0], "w1": s[-1], "start": words[s[0]]["start"], "end": words[s[-1]]["end"],
             "text": " ".join(words[j]["w"] for j in s)} for k, s in enumerate(res)]


def fmt(t):
    return f"{int(t // 60):02d}:{t % 60:04.1f}"


def cmd_sentences(a):
    job = job_dir(a.job)
    wj = job / "work" / f"{a.slug}_words.json"
    if not wj.exists():
        fail(f"{wj} absent : lance transcribe.py sur la vidéo complète")
    d = read_json(wj)
    ss = sentences(d["words"])
    write_json(job / "work" / f"{a.slug}_sentences.json", ss)
    lines = [f"{s['id']:>3} [{fmt(s['start'])}–{fmt(s['end'])}] {s['text']}" for s in ss]
    txt = job / "work" / f"{a.slug}_sentences.txt"
    txt.write_text("\n".join(lines) + "\n", encoding="utf-8")
    out(ok=True, phrases=len(ss), duree=round(d["duration"], 1), liste=str(txt),
        suite="lis la liste, choisis 3 à 5 passages de 20 à 60 s qui se suffisent à eux-mêmes, écris work/<slug>_shorts.json")


def run_py(script, *args):
    r = subprocess.run([sys.executable, str(HERE / script), *args], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env={**os.environ, "PYTHONUTF8": "1"})
    last = (r.stdout.strip().splitlines() or ["{}"])[-1]
    try:
        res = json.loads(last)
    except json.JSONDecodeError:
        res = {}
    if r.returncode != 0 or not res.get("ok", True):
        fail(f"{script} {' '.join(args[-2:])} a échoué", out=(r.stdout + r.stderr)[-600:])
    return res


def cmd_make(a):
    job = job_dir(a.job)
    work = job / "work"
    words_d = read_json(work / f"{a.slug}_words.json")
    words = words_d["words"]
    ss = read_json(work / f"{a.slug}_sentences.json")
    picks = read_json(work / f"{a.slug}_shorts.json")["shorts"]
    meta = read_json(job / "job.json")
    made = []
    for p in picks:
        name = re.sub(r"[^a-z0-9-]+", "-", p["name"].lower()).strip("-")
        ids = [i for i in range(int(p["from"]), int(p["to"]) + 1) if i not in set(p.get("skip", []))]
        if not ids or ids[0] < 0 or ids[-1] >= len(ss):
            fail(f"short {name} : numéros de phrases hors liste (0 à {len(ss) - 1})")
        child = ROOT / "jobs" / f"{job.name}-{name}"
        for d in ("inbox", "work", "assets", "renders"):
            (child / d).mkdir(parents=True, exist_ok=True)
        shutil.copy2(job / "hyperframes.json", child / "hyperframes.json")
        for cfg in ("config.json",):
            if (job / cfg).exists():
                shutil.copy2(job / cfg, child / cfg)
        ccfg = read_json(child / "config.json") if (child / "config.json").exists() else {}
        txt = ccfg.setdefault("text", {})
        if a.mode:
            txt["mode"] = a.mode
        if a.style:
            txt["captionStyle"] = a.style
        write_json(child / "config.json", ccfg)  # deliver.py reconstruit avec ces choix
        write_json(child / "job.json", {**meta, "name": child.name, "sujet": f"{meta.get('sujet', '')} · {p.get('hook') or name}",
                                        "parent": job.name, "short": name})
        sl = "short"
        write_json(child / "work" / f"{sl}_words.json", words_d)
        # îlots = phrases choisies ; bords au milieu du blanc avec le mot voisin (jamais dans un mot)
        islands = []
        for k in ids:
            s = ss[k]
            prev_end = words[s["w0"] - 1]["end"] if s["w0"] > 0 else max(0.0, s["start"] - PAD)
            next_start = words[s["w1"] + 1]["start"] if s["w1"] + 1 < len(words) else s["end"] + PAD
            cs = round(max(prev_end, s["start"] - PAD, (prev_end + s["start"]) / 2), 3)
            ce = round(min(next_start, s["end"] + PAD, (s["end"] + next_start) / 2), 3)
            if islands and abs(cs - islands[-1]["cut_end"]) < 0.02:
                cs = islands[-1]["cut_end"]
            islands.append({"id": k, "text": s["text"], "speech_start": s["start"], "speech_end": s["end"],
                            "cut_start": cs, "cut_end": ce, "keep": True, "reason": p.get("why", "")})
        span = islands[-1]["cut_end"] - islands[0]["cut_start"]
        from cut_plan import fillers  # « euh », mots doublés, blancs dans la phrase, tics et reformulations, comme un rush
        fl = fillers(islands, [words[ss[k]["w0"]:ss[k]["w1"] + 1] for k in ids])
        write_json(child / "work" / f"{sl}_plan.json", {"slug": sl, "source": words_d["source"], "duration": round(span, 3),
                                                       "range": [islands[0]["cut_start"], islands[-1]["cut_end"]],
                                                       "islands": islands, "fillers": fl, "from_long": job.name})
        if p.get("hook"):
            write_json(child / "work" / f"{sl}_hook.json", {"text": p["hook"]})
        if p.get("post"):
            write_json(child / "work" / f"{sl}_post.json", p["post"])
        cut = run_py("build_cut.py", str(child), sl)
        run_py("build_text.py", str(child), sl)
        run_py("reframe.py", str(child), sl, "--size", a.size)  # source plus large : la fenêtre suit le visage
        if a.mood:
            run_py("add_music.py", str(child), sl, "--mood", a.mood)
        comp = ["build_composition.py", str(child), sl, "--size", a.size]
        if a.mode:
            comp += ["--mode", a.mode]
        if a.style:
            comp += ["--style", a.style]
        run_py(*comp)
        made.append({"short": name, "job": child.name, "phrases": f"{ids[0]}–{ids[-1]}", "duree": cut["apres"],
                     "hook": p.get("hook", "")})
    out(ok=True, shorts=made, suite="check + snapshot sur chaque job, puis deliver.py <job> short")


def caption_styles():
    """Styles de sous-titres : la liste de build_composition.py (source unique), lue sans l'exécuter si l'import échoue."""
    try:
        from build_composition import STYLES
        return list(STYLES)
    except Exception:  # noqa: BLE001 — import cassé : on relit la ligne STYLES = [...] du fichier
        import ast
        src = (HERE / "build_composition.py").read_text(encoding="utf-8")
        m = re.search(r"^STYLES\s*=\s*(\[[^\]]*\])", src, re.M)
        return ast.literal_eval(m.group(1)) if m else ["pop", "karaoke", "minimal", "boite", "impact", "duo"]


def main():
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    s = sp.add_parser("sentences")
    s.add_argument("job")
    s.add_argument("slug")
    m = sp.add_parser("make")
    m.add_argument("job")
    m.add_argument("slug")
    m.add_argument("--mode", choices=["captions", "overlays", "both", "none"])
    m.add_argument("--style", choices=caption_styles())
    m.add_argument("--mood")
    m.add_argument("--size", default="9:16")
    a = ap.parse_args()
    (cmd_sentences if a.cmd == "sentences" else cmd_make)(a)


if __name__ == "__main__":
    main()

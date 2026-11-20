"""PLUSIEURS RUSHS -> UNE VIDÉO (clips filmés au téléphone, dans le désordre, avec des reprises)

  python multi.py list <job>                                   # transcrit chaque clip de inbox/ (une fois) + résumé
  python multi.py assemble <job> <slug> --order c2.mp4,c1.mp4,c4.mp4 [--gap 0.6]

1. list : chaque vidéo de inbox/ est transcrite (local, mise en cache dans work/clip-<nom>_words.json) ; la sortie
   donne pour chaque clip sa durée et son texte. Claude lit tout et décide l'ORDRE DU PROPOS (accroche, explication,
   preuve, appel à l'action) et les clips à laisser de côté (doublons, essais ratés, hors sujet).
2. assemble : les clips retenus sont mis bout à bout dans cet ordre, au format du premier (même taille, 30 i/s, son
   48 kHz ; un clip d'un autre sens est centré sur fond flouté), séparés par un court silence pour que le dérush coupe
   toujours entre deux clips. Les mots horodatés sont recalés sans retranscrire (work/<slug>_words.json).
Ensuite, le parcours rush habituel : cut_plan.py -> keep/reason (meilleure prise de chaque phrase, tous clips
confondus) -> build_cut.py -> build_text.py -> build_composition.py.
"""
import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from common import config, fail, job_dir, out, probe, read_json, sh, write_json

HERE = Path(__file__).resolve().parent
VIDEO = (".mp4", ".mov", ".m4v", ".webm", ".mkv", ".avi")


def clips(job):
    return sorted(p for p in (job / "inbox").iterdir() if p.suffix.lower() in VIDEO and not p.stem.endswith("_assemble"))


def cmd_list(a):
    job = job_dir(a.job)
    rows = []
    for p in clips(job):
        slug = "clip-" + "".join(ch if ch.isalnum() else "-" for ch in p.stem.lower())[:40]
        wj = job / "work" / f"{slug}_words.json"
        if not wj.exists():
            r = subprocess.run([sys.executable, str(HERE / "transcribe.py"), str(job), p.name, "--slug", slug],
                               capture_output=True, text=True, encoding="utf-8", errors="replace",
                               env={**os.environ, "PYTHONUTF8": "1"})
            if not wj.exists():
                rows.append({"clip": p.name, "erreur": (r.stdout + r.stderr)[-200:]})
                continue
        d = read_json(wj)
        info = probe(p)
        rows.append({"clip": p.name, "duree": round(info["duration"], 1), "format": f"{info['width']}x{info['height']}",
                     "mots": len(d["words"]), "texte": d["text"]})
    write_json(job / "work" / "clips.json", rows)
    out(ok=True, clips=rows, suite="choisis l'ordre du propos et les clips à garder, puis : multi.py assemble <job> <slug> --order a,b,c")


def cmd_assemble(a):
    job = job_dir(a.job)
    names = [n.strip() for n in a.order.split(",") if n.strip()]
    paths = []
    for n in names:
        p = job / "inbox" / n
        if not p.exists():
            fail(f"clip introuvable dans inbox/ : {n}")
        paths.append(p)
    first = probe(paths[0])
    W, H = first["width"], first["height"]
    if max(W, H) > 1920:  # un 4K n'apporte rien au montage final : on travaille en 1080p
        k = 1920 / max(W, H)
        W, H = int(W * k) // 2 * 2, int(H * k) // 2 * 2
    parts, offsets, cur, words = [], [], 0.0, []
    for i, p in enumerate(paths):
        info = probe(p)
        same = (info["width"] >= info["height"]) == (W >= H)
        if same:  # même sens : recadré pour remplir
            vf = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}"
        else:  # autre sens : image entière sur fond flouté
            vf = (f"split[a][b];[a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=30:5,eq=brightness=-0.15[bg];"
                  f"[b]scale={W}:{H}:force_original_aspect_ratio=decrease[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2")
        parts.append((i, vf, info["has_audio"]))
        cj = job / "work" / f"clip-{''.join(ch if ch.isalnum() else '-' for ch in p.stem.lower())[:40]}_words.json"
        if cj.exists():
            for w in read_json(cj)["words"]:
                words.append({"w": w["w"], "start": round(w["start"] + cur, 3), "end": round(w["end"] + cur, 3)})
        else:
            fail(f"{p.name} pas encore transcrit : lance d'abord multi.py list")
        offsets.append({"clip": p.name, "debut": round(cur, 3), "duree": round(info["duration"], 3)})
        cur += info["duration"] + a.gap
    fc = []
    for i, vf, has_a in parts:
        fc.append(f"[{i}:v]{vf},fps=30,setsar=1,format=yuv420p,tpad=stop_mode=clone:stop_duration={a.gap}[v{i}]")
        if has_a:
            fc.append(f"[{i}:a]aresample=48000,aformat=channel_layouts=stereo,apad=pad_dur={a.gap}[a{i}]")
        else:
            d = offsets[i]["duree"] + a.gap
            fc.append(f"anullsrc=r=48000:cl=stereo,atrim=duration={d}[a{i}]")
    fc.append("".join(f"[v{i}][a{i}]" for i, _, _ in parts) + f"concat=n={len(parts)}:v=1:a=1[v][a]")
    dst = job / "inbox" / f"{a.slug}_assemble.mp4"
    fd, script = tempfile.mkstemp(suffix=".txt")
    with os.fdopen(fd, "w", encoding="utf-8") as t:
        t.write(";".join(fc))
    try:
        cmd = ["ffmpeg", "-y", "-loglevel", "error"]
        for p in paths:
            cmd += ["-i", str(p)]
        sh(cmd + ["-filter_complex_script", script, "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-crf", "17",
                  "-preset", "medium", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(dst)], "ffmpeg (assemblage)")
    finally:
        Path(script).unlink(missing_ok=True)
    total = probe(dst)["duration"]
    write_json(job / "work" / f"{a.slug}_words.json", {
        "language": config(job)["language"], "engine": "assemblage", "source": str(dst), "duration": round(total, 3), "range": [None, None],
        "text": " ".join(w["w"] for w in words), "words": words, "clips": offsets})
    out(ok=True, assemble=str(dst), clips=offsets, duree=round(total, 1), format=f"{W}x{H}",
        suite=f"cut_plan.py <job> {a.slug} -> keep/reason (meilleure prise de chaque phrase) -> build_cut.py …")


def main():
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("list")
    p.add_argument("job")
    p = sp.add_parser("assemble")
    p.add_argument("job")
    p.add_argument("slug")
    p.add_argument("--order", required=True, help="clips de inbox/ dans l'ordre du propos, séparés par des virgules")
    p.add_argument("--gap", type=float, default=0.6, help="silence entre deux clips (s)")
    a = ap.parse_args()
    {"list": cmd_list, "assemble": cmd_assemble}[a.cmd](a)


if __name__ == "__main__":
    main()

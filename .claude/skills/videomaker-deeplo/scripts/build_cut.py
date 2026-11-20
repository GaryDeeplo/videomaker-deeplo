"""DÉRUSH -> assets/<slug>_cut.mp4 + work/<slug>_map.json   (repris de reel-cut, adapté)

Seul endroit où l'on ré-encode la vidéo. Tout l'habillage suit dans HyperFrames.
Ajouts : réduction à la taille utile du format de sortie (un rush 4K n'est pas traîné jusqu'au rendu),
voix normalisée (loudnorm, derush.voiceLufs), débruitage optionnel.

  python build_cut.py <job> <slug> [--crf 18] [--denoise]
"""
import argparse
import os
import tempfile
from pathlib import Path

from common import config, fail, job_dir, out, probe, read_json, sh, write_json


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("job")
    ap.add_argument("slug")
    ap.add_argument("--crf", type=int, default=18)
    ap.add_argument("--preset", default="medium")
    ap.add_argument("--denoise", action="store_true", help="afftdn : rushs au téléphone, souffle")
    a = ap.parse_args()
    job = job_dir(a.job)
    c = config(job)
    f, lufs = c["derush"]["fade"], c["derush"]["voiceLufs"]
    W, H = c["visual"]["width"], c["visual"]["height"]

    pj = job / "work" / f"{a.slug}_plan.json"
    if not pj.exists():
        fail(f"{pj} absent")
    plan = read_json(pj)
    src = Path(plan["source"])
    keep = [i for i in plan["islands"] if i.get("keep")]
    if not keep:
        fail("aucun îlot gardé")

    holes = sorted((float(x["cut_start"]), float(x["cut_end"])) for x in plan.get("fillers", []) if x.get("remove"))
    segs = []
    for i in keep:
        pieces = [[float(i["cut_start"]), float(i["cut_end"])]]
        for hs, he in holes:  # hésitations, répétitions, blancs : l'îlot est coupé en morceaux
            nxt = []
            for s, e in pieces:
                if he <= s or hs >= e:
                    nxt.append([s, e])
                else:
                    nxt += [p for p in ([s, hs], [he, e]) if p[1] - p[0] > 0.05]
            pieces = nxt
        for s, e in pieces:
            if segs and abs(s - segs[-1][1]) < 1e-3:
                segs[-1][1] = e
            else:
                segs.append([s, e])
    segs = [(s, e) for s, e in segs if e - s > 0.05]
    n_fill = sum(1 for x in plan.get("fillers", []) if x.get("remove"))

    info = probe(src)
    k = max(W / info["width"], H / info["height"])  # échelle « cover » du format de sortie
    scale = f",scale=-2:{int(round(info['height'] * k / 2) * 2)}" if k < 1 else ""

    parts = []
    for n, (s, e) in enumerate(segs):
        d = e - s
        af = f"atrim=start={s}:end={e},asetpts=PTS-STARTPTS"
        if d > 2 * f + 0.05:
            af += f",afade=t=in:st=0:d={f},afade=t=out:st={d - f:.3f}:d={f}"
        parts.append(f"[0:v]trim=start={s}:end={e},setpts=PTS-STARTPTS{scale}[v{n}];[0:a]{af}[a{n}]")
    post = (",afftdn=nf=-25" if a.denoise else "") + f",loudnorm=I={lufs}:TP=-1.5:LRA=11,aresample=48000"
    fc = ";".join(parts) + ";" + "".join(f"[v{n}][a{n}]" for n in range(len(segs))) \
        + f"concat=n={len(segs)}:v=1:a=1[v][ac];[ac]anull{post}[a]"

    dst = job / "assets" / f"{a.slug}_cut.mp4"
    fd, script = tempfile.mkstemp(suffix=".txt")
    with os.fdopen(fd, "w", encoding="utf-8") as t:
        t.write(fc)
    try:
        sh(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-filter_complex_script", script,
            "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-crf", str(a.crf), "-preset", a.preset,
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(dst)],
           "ffmpeg (dérush)")
    finally:
        Path(script).unlink(missing_ok=True)

    mapping, cur = [], 0.0
    for s, e in segs:
        mapping.append({"src_start": round(s, 3), "src_end": round(e, 3),
                        "out_start": round(cur, 3), "out_end": round(cur + (e - s), 3)})
        cur += e - s
    write_json(job / "work" / f"{a.slug}_map.json",
               {"slug": a.slug, "cut": str(dst), "segments": mapping, "out_duration": round(cur, 3)})
    out(ok=True, segments=len(segs), avant=round(plan["duration"], 1), apres=round(cur, 1),
        gain_pct=round(100 * (1 - cur / plan["duration"])), jetes=len(plan["islands"]) - len(keep),
        fillers_retires=n_fill, cut=str(dst))


if __name__ == "__main__":
    main()

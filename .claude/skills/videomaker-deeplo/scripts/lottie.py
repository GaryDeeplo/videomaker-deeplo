"""ANIMATIONS LOTTIE (LottieFiles, emojis animés Noto) -> library/lottie/<nom>/<nom>.webm (vidéo transparente)

  python lottie.py get emoji 🔥 [--name feu]                     # emoji animé Google Noto (CC BY 4.0, crédit auto)
  python lottie.py get url <lien .json/.lottie> --name <nom> --license "Lottie Simple License" --author "<auteur>"
  python lottie.py render <nom> [--size 600]                       # rendu une fois : WebM transparent + aperçu
  python lottie.py list

Une animation rendue se pose dans n'importe quelle vidéo comme un bloc de motion :
  "motions": [{"block": "lottie", "name": "feu", "word": "<mot dit>", "dur": 2, "vars": {"x": 50, "y": 30, "size": 34}}]
(x, y : centre en % du cadre ; size : largeur en vmin). Le crédit part dans renders/credits.txt du job.
Licences admises : Lottie Simple License (LottieFiles, gratuit en commercial, sans attribution), CC BY 4.0 (Noto,
crédit obligatoire), MIT (Fluent). Toujours noter la source : on ne pose jamais une animation sans licence connue.
"""
import argparse
import json
import os
import shutil
import subprocess
import tempfile
import urllib.request
from pathlib import Path

from common import ROOT, fail, out, read_json, sh, write_json

LIB = ROOT / "library" / "lottie"
VENDOR = Path(__file__).resolve().parent.parent / "vendor" / "dotlottie-web"
NPX = ["cmd", "/c", "npx"] if os.name == "nt" else ["npx"]
UA = {"User-Agent": "deeplo-video-maker/1.0"}


def get(a):
    if a.what == "emoji":
        cps = [f"{ord(ch):x}" for ch in a.value if ord(ch) not in (0xFE0F, 0x200D)]
        if not cps:
            fail("emoji vide")
        code = "_".join(cps)
        url = f"https://fonts.gstatic.com/s/e/notoemoji/latest/{code}/lottie.json"
        name = a.name or f"emoji-{code}"
        lic, author, src = "CC BY 4.0", "Google (Noto Animated Emoji)", "https://googlefonts.github.io/noto-emoji-animation/"
    else:
        url, name = a.value, a.name
        if not name:
            fail("--name obligatoire pour une URL")
        lic, author, src = a.license or "", a.author or "", a.source or a.value
        if not lic:
            fail("--license obligatoire (ex. « Lottie Simple License » pour une animation gratuite LottieFiles)")
    d = LIB / name
    d.mkdir(parents=True, exist_ok=True)
    ext = ".lottie" if url.split("?")[0].endswith(".lottie") else ".json"
    dst = d / f"{name}{ext}"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
            dst.write_bytes(r.read())
    except Exception as e:  # noqa: BLE001
        fail(f"téléchargement impossible : {e}", url=url)
    info = {}
    if ext == ".json":
        j = json.loads(dst.read_text(encoding="utf-8"))
        fr = float(j.get("fr", 30))
        info = {"fps": fr, "duration": round((float(j.get("op", 60)) - float(j.get("ip", 0))) / fr, 3),
                "w": j.get("w"), "h": j.get("h")}
    credit = f"Animation « {name} » : {author}, {lic} ({src})"
    write_json(d / "lottie.json", {"name": name, "file": dst.name, "url": url, "license": lic, "author": author,
                                   "source": src, "credit": credit, **info})
    out(ok=True, name=name, fichier=str(dst), licence=lic, **info, suite=f"lottie.py render {name}")


def render(a):
    d = LIB / a.name
    meta = read_json(d / "lottie.json") if (d / "lottie.json").exists() else fail(f"inconnue : {a.name} (lottie.py get)")
    if not (VENDOR / "index.js").exists():
        fail("lecteur dotLottie absent (vendor/dotlottie-web)")
    dur = float(a.dur or meta.get("duration") or 2.0)
    size = int(a.size)
    t = Path(tempfile.mkdtemp())  # nettoyage tolérant : Chrome garde parfois le dossier ouvert sous Windows
    try:
        (t / "lib").mkdir()
        shutil.copytree(VENDOR, t / "lib" / "dotlottie-web")
        (t / "assets").mkdir()
        shutil.copy2(d / meta["file"], t / "assets" / meta["file"])
        shutil.copy2(ROOT / "studio" / "hyperframes.json", t / "hyperframes.json")
        (t / "index.html").write_text(f"""<!doctype html>
<html lang="fr"><head><meta charset="UTF-8" /><meta name="viewport" content="width={size}, height={size}" />
<style>html, body {{ margin: 0; width: {size}px; height: {size}px; background: transparent; overflow: hidden; }}
#anim {{ position: absolute; inset: 0; width: {size}px; height: {size}px; }}</style></head>
<body><div id="root" data-composition-id="lottie" data-start="0" data-duration="{dur}" data-width="{size}" data-height="{size}">
<canvas id="anim" width="{size}" height="{size}"></canvas></div>
<script type="module">
  import {{ DotLottie }} from "./lib/dotlottie-web/index.js";
  DotLottie.setWasmUrl(new URL("./lib/dotlottie-web/dotlottie-player.wasm", import.meta.url).href);
  const player = new DotLottie({{ canvas: document.getElementById("anim"), src: "assets/{meta['file']}", autoplay: false,
    loop: false, renderConfig: {{ autoResize: false, freezeOnOffscreen: false }} }});
  window.__hfLottie = window.__hfLottie || [];
  window.__hfLottie.push(player);
</script></body></html>
""", encoding="utf-8")
        webm = d / f"{a.name}.webm"
        r = subprocess.run(NPX + ["--yes", "hyperframes@0.9.71", "render", "--format", "webm", "-q", "delivery", "-w", "4",
                                  "-o", str(webm)], cwd=t, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode != 0 or not webm.exists():
            fail("rendu Lottie échoué", out=(r.stdout + r.stderr)[-800:])
    finally:
        shutil.rmtree(t, ignore_errors=True)
    # aperçu de bibliothèque : l'animation sur un damier gris (pour voir la transparence)
    sh(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"color=c=0x3a3a3a:s=360x360:d={dur}",
        "-c:v", "libvpx-vp9", "-i", str(webm), "-filter_complex", "[1:v]scale=360:360[l];[0:v][l]overlay=0:0:shortest=1",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "26", "-an", str(d / "preview.mp4")], "ffmpeg (aperçu)")
    sh(["ffmpeg", "-y", "-loglevel", "error", "-ss", str(dur * 0.6), "-i", str(d / "preview.mp4"), "-frames:v", "1",
        str(d / "poster.jpg")], "ffmpeg (vignette)")
    meta.update({"webm": webm.name, "rendered_size": size, "rendered_duration": dur})
    write_json(d / "lottie.json", meta)
    # entrée de galerie (library.py) pour que l'animation soit trouvable et visible
    write_json(d / "meta.json", {"name": a.name, "type": "lottie", "title": f"Lottie : {a.name}",
                                 "description": f"Animation Lottie rendue en vidéo transparente ({dur} s). {meta['credit']}",
                                 "when_to_use": "Réaction, emoji, illustration animée par-dessus une scène ou un rush.",
                                 "tags": ["lottie", "animation", meta.get("license", "")], "files": [webm.name],
                                 "usage": json.dumps({"block": "lottie", "name": a.name, "word": "<mot dit>", "dur": dur,
                                                      "vars": {"x": 50, "y": 30, "size": 34}}, ensure_ascii=False),
                                 "source_job": None, "preview": "preview.mp4", "created": meta.get("created", ""), "uses": 0})
    out(ok=True, name=a.name, webm=str(webm), duree=dur, taille=size, credit=meta["credit"])


def main():
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    g = sp.add_parser("get")
    g.add_argument("what", choices=["emoji", "url"])
    g.add_argument("value")
    g.add_argument("--name")
    g.add_argument("--license")
    g.add_argument("--author")
    g.add_argument("--source")
    rd = sp.add_parser("render")
    rd.add_argument("name")
    rd.add_argument("--size", default=600)
    rd.add_argument("--dur", type=float)
    sp.add_parser("list")
    a = ap.parse_args()
    if a.cmd == "get":
        get(a)
    elif a.cmd == "render":
        render(a)
    else:
        out(ok=True, animations=[{"name": p.parent.name, **{k: v for k, v in read_json(p).items() if k in ("license", "duration", "webm")}}
                                 for p in sorted(LIB.glob("*/lottie.json"))])


if __name__ == "__main__":
    main()

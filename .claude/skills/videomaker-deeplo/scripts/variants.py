"""VARIANTES D'ACCROCHE A/B : 2 ou 3 versions des 3 premières secondes (style d'accroche, titre, sous-titre) sur le
même montage, pour voir laquelle retient le mieux sur Instagram / TikTok. Marche avec tous les rendus.

  python variants.py propose <job> <slug>                  # premier jet work/<slug>_variantes.json (3 styles, titres à réécrire)
  python variants.py make <job> <slug> [--video renders/x.mp4] [--quality draft|delivery]
                                                           # -> renders/variantes/<slug>_<nom>.mp4 + variantes.html

work/<slug>_variantes.json :
  {"dur": 3.0, "variantes": [
     {"nom": "A", "style": "neon",   "texte": "J'ai automatisé mes montages", "sous_titre": ""},
     {"nom": "B", "style": "papier", "texte": "Un reel monté en 2 minutes ?"},
     {"nom": "C", "style": "relief", "texte": "Stop au montage à la main", "accent": "#ff5a36"}]}
Chaque variante = une promesse différente (bénéfice, question, contraste), pas trois fois la même phrase ; titres
courts (≤ 6 mots), vrais (rien que la vidéo ne tienne). Styles : papier, plan, pate, neon, aquarelle, pixel,
isometrique, mosaique, encre, relief.

Fonctionnement : la vidéo de base (le rendu le plus récent du job, SANS accroche) est rendue une seule fois ; pour
chaque variante, seules les premières secondes sont rendues (accroche par-dessus le début de la vidéo, qui démarre
sous le volet de sortie), puis recollées au reste de la base avec son son d'origine (+ impact et souffle de l'accroche).
Ensuite : publier les variantes en « Reels d'essai » (Instagram : montrés d'abord à des non-abonnés) ou à des jours
comparables, et garder celle dont la rétention à 3 s est la meilleure. variantes.html sert de fiche de suivi.
"""
import argparse
import html
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

from common import ROOT, block_file, config, fail, job_dir, mount, out, read_json, write_json

NPX = ["cmd", "/c", "npx"] if os.name == "nt" else ["npx"]
STYLES = ["papier", "plan", "pate", "neon", "aquarelle", "pixel", "isometrique", "mosaique", "encre", "relief"]
esc = lambda s: html.escape(str(s), quote=True)


def vinfo(v):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,r_frame_rate:format=duration",
                        "-of", "json", str(v)], capture_output=True, text=True)
    d = json.loads(r.stdout)
    s = d["streams"][0]
    n, k = s["r_frame_rate"].split("/")
    return int(s["width"]), int(s["height"]), float(n) / float(k), float(d["format"]["duration"])


def base_video(job, arg):
    if arg:
        v = Path(arg) if Path(arg).is_absolute() else job / arg
        if not v.exists():
            fail(f"{v} introuvable")
        return v
    cands = [p for p in (job / "renders").rglob("*.mp4") if "variantes" not in p.parts and "covers" not in p.parts]
    if not cands:
        fail("aucun rendu : rends d'abord la vidéo SANS accroche (render -q draft ou delivery)")
    return max(cands, key=lambda p: p.stat().st_mtime)


def propose(job, slug):
    work = job / "work"
    title = ""
    for f in (f"{slug}_hook.json", f"{slug}_footage.json"):
        if (work / f).exists():
            d = read_json(work / f)
            title = d.get("text") or d.get("title") or (d.get("hook") or {}).get("text", "") or title
    if not title and (work / f"{slug}_text.json").exists():
        caps = read_json(work / f"{slug}_text.json").get("captions", [])
        title = " ".join(w["w"] for g in caps[:2] for w in g["words"])
    c = config(job)
    first = (c.get("hook") or {}).get("style") or "neon"
    others = [s for s in ("papier", "relief", "encre", "pate") if s != first][:2]
    data = {"dur": 3.0, "variantes": [{"nom": n, "style": s, "texte": title, "sous_titre": ""}
                                      for n, s in zip("ABC", [first] + others)],
            "_a_faire": "réécris chaque texte : A = bénéfice, B = question, C = contraste ou chiffre ; ≤ 6 mots, rien d'inventé"}
    dst = work / f"{slug}_variantes.json"
    if dst.exists():
        dst = work / f"{slug}_variantes_draft.json"
    write_json(dst, data)
    out(ok=True, fichier=str(dst), variantes=[f'{v["nom"]} · {v["style"]}' for v in data["variantes"]],
        suite="réécris les titres (3 promesses différentes), puis variants.py make <job> <slug>")


def faces(job):
    """@font-face de la composition du job (même police que la vidéo)."""
    h = (job / "index.html").read_text(encoding="utf-8") if (job / "index.html").exists() else ""
    return "\n".join(re.findall(r"@font-face\s*\{[^}]*\}", h))


def head_comp(job, vdir, v, W, H, hdur, vals, style):
    """Composition des premières secondes : début de la base + accroche par-dessus."""
    (vdir / "assets").mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "studio" / "hyperframes.json", vdir / "hyperframes.json")
    if (job / "assets" / "fonts").exists():
        shutil.copytree(job / "assets" / "fonts", vdir / "assets" / "fonts", dirs_exist_ok=True)
    head = vdir / "assets" / "head_src.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(v), "-t", f"{hdur + 0.2:.2f}", "-an", "-c:v", "libx264", "-preset", "veryfast",
                    "-crf", "14", str(head)], check=True)
    name = f"accroche-{style}"
    block_file(vdir, name)
    host = mount(name, "hook-anim", 0, hdur, W, H, 20, vals, z=200)
    doc = f"""<!doctype html>
<html lang="fr">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width={W}, height={H}" />
<title>variante</title>
<script src="https://cdn.jsdelivr.net/npm/gsap@3.15.0/dist/gsap.min.js"></script>
<style>
  {faces(job)}
  html, body {{ margin: 0; width: {W}px; height: {H}px; overflow: hidden; background: #000; }}
  #root {{ position: relative; width: {W}px; height: {H}px; overflow: hidden; }}
  #base {{ position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }}
</style>
</head>
<body>
  <div id="root" data-composition-id="variante" data-start="0" data-width="{W}" data-height="{H}" data-duration="{hdur}">
    <video id="base" class="clip" src="assets/head_src.mp4" data-start="0" data-duration="{hdur}" data-track-index="1" muted playsinline></video>
{host}
  </div>
<script>
  window.__timelines = window.__timelines || {{}};
  const tl = gsap.timeline({{ paused: true }});
  tl.set("#base", {{ opacity: 1 }}, 0);
  window.__timelines["variante"] = tl;
</script>
</body>
</html>
"""
    (vdir / "index.html").write_text(doc, encoding="utf-8")


def make(job, slug, video, quality):
    work = job / "work"
    vj = work / f"{slug}_variantes.json"
    if not vj.exists():
        fail("lance d'abord variants.py propose <job> <slug> et réécris les titres")
    spec = read_json(vj)
    vs = spec.get("variantes", [])
    if len(vs) < 2:
        fail("au moins 2 variantes")
    for x in vs:
        if x.get("style") not in STYLES:
            fail(f"style inconnu pour {x.get('nom')} : {x.get('style')} ({', '.join(STYLES)})")
    v = base_video(job, video)
    W, H, fps, dur = vinfo(v)
    hdur = float(spec.get("dur", 3.0))
    warn = []
    if "accroche-" in (job / "index.html").read_text(encoding="utf-8"):
        warn.append("la composition du job a déjà une accroche : la base doit être rendue sans (sinon deux accroches se suivent)")
    c = config(job)
    vis = c["visual"]
    sd = __import__("sound_design")
    hit = sd.files("hit")
    wsh = sd.files("whoosh")
    dst = job / "renders" / "variantes"
    dst.mkdir(parents=True, exist_ok=True)
    made = []
    for k, x in enumerate(vs):
        nom = re.sub(r"[^\w-]", "", str(x.get("nom", "ABC"[k % 3]))) or f"v{k}"
        vdir = work / "variantes" / nom
        shutil.rmtree(vdir, ignore_errors=True)
        vdir.mkdir(parents=True)
        vals = {"text": x.get("texte", ""), "sub": x.get("sous_titre", ""), "accent": x.get("accent") or vis.get("accentColor", "#ffcc00"),
                "font": vis.get("fontFamily", "Inter")}
        vals.update({kk: x[kk] for kk in ("bg", "ink") if x.get(kk)})
        if x.get("art") and (job / x["art"]).exists():
            vals["art"] = (job / x["art"]).read_text(encoding="utf-8")
        head_comp(job, vdir, v, W, H, hdur, vals, x["style"])
        hv = vdir / "head.mp4"
        r = subprocess.run(NPX + ["--yes", "hyperframes@0.9.71", "render", "-q", quality, "-w", "8", "-o", str(hv)], cwd=vdir,
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode != 0 or not hv.exists():
            fail(f"rendu de la variante {nom} échoué", detail=(r.stdout + r.stderr)[-600:])
        # tête de la variante + reste de la base (le volet de sortie couvre le raccord), son de la base + impact / souffle
        final = dst / f"{slug}_{nom}.mp4"
        cut = hdur - 0.02
        inputs = ["-i", str(hv), "-i", str(v)]
        fc = (f"[0:v]fps={fps:.3f},scale={W}:{H},setsar=1,trim=0:{cut:.3f},setpts=PTS-STARTPTS[h];"
              f"[1:v]fps={fps:.3f},scale={W}:{H},setsar=1,trim=start={cut:.3f},setpts=PTS-STARTPTS[t];[h][t]concat=n=2:v=1:a=0,format=yuv420p[v];")
        amix = ["[1:a]anull[a0]"]
        n_in = 2
        for f_, t_, vol in ((hit[k % len(hit)][0] if hit else None, 0.15, 0.45), (wsh[k % len(wsh)][0] if wsh else None, hdur - 0.57, 0.4)):
            if f_ is None:
                continue
            inputs += ["-i", str(f_)]
            ms = int(max(0, t_) * 1000)
            amix.append(f"[{n_in}:a]volume={vol},adelay={ms}|{ms},apad[a{n_in - 1}]")
            n_in += 1
        has_audio = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of", "csv=p=0", str(v)],
                                   capture_output=True, text=True).stdout.strip()
        if has_audio:
            fc += ";".join(amix) + ";" + "".join(f"[a{i}]" for i in range(n_in - 1)) + f"amix=inputs={n_in - 1}:duration=first:normalize=0[a]"
            maps = ["-map", "[v]", "-map", "[a]", "-c:a", "aac", "-b:a", "192k"]
        else:
            fc = fc.rstrip(";")
            maps = ["-map", "[v]"]
        subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", fc, *maps, "-c:v", "libx264", "-preset", "medium",
                        "-crf", "18", "-movflags", "+faststart", str(final)], check=True)
        cover = dst / f"{slug}_{nom}_cover.jpg"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "1.2", "-i", str(final), "-frames:v", "1", "-q:v", "3", str(cover)], check=True)
        made.append({"nom": nom, "style": x["style"], "texte": x.get("texte", ""), "video": final.name, "cover": cover.name})
    page(dst, slug, made, v.name)
    out(ok=True, base=str(v.relative_to(job)), variantes=[f'{m["nom"]} · {m["style"]} · « {m["texte"]} »' for m in made],
        dossier=str(dst), page=str(dst / "variantes.html"), avertissements=warn,
        suite="ouvre variantes.html ; publie en Reels d'essai, garde la meilleure rétention à 3 s")


def page(dst, slug, made, base):
    cards = "".join(
        f'<figure><video src="{esc(m["video"])}" poster="{esc(m["cover"])}" controls playsinline preload="none"></video>'
        f'<figcaption><b>{esc(m["nom"])}</b> · {esc(m["style"])}<br><span>« {esc(m["texte"])} »</span>'
        f'<a href="{esc(m["video"])}" download>Télécharger</a></figcaption></figure>' for m in made)
    rows = "".join(f'<tr><td>{esc(m["nom"])}</td><td></td><td></td><td></td><td></td></tr>' for m in made)
    doc = f"""<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Variantes · {esc(slug)}</title>
<style>
 body {{ margin: 0; padding: 24px 16px 48px; font: 16px/1.5 system-ui, sans-serif; background: #f5f4f0; color: #171717; }}
 h1 {{ font-size: 24px; margin: 0 0 4px; }} p {{ margin: 4px 0 16px; color: #555; max-width: 70ch; }}
 .g {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 16px; }}
 figure {{ margin: 0; background: #fff; border-radius: 12px; padding: 10px; box-shadow: 0 2px 10px rgba(0,0,0,.06); }}
 video {{ width: 100%; border-radius: 8px; background: #000; aspect-ratio: 9/16; }}
 figcaption {{ padding: 8px 2px 2px; }} figcaption span {{ color: #444; }} figcaption a {{ display: inline-block; margin-top: 6px; color: #0b57d0; }}
 table {{ border-collapse: collapse; margin-top: 24px; width: 100%; max-width: 720px; background: #fff; }}
 th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; font-size: 14px; }} th {{ background: #eee; }}
</style></head><body>
<h1>Variantes d'accroche · {esc(slug)}</h1>
<p>Même vidéo ({esc(base)}), seules les 3 premières secondes changent. Publiez-les en « Reels d'essai » (Instagram les montre
d'abord à des non-abonnés) ou à des jours et heures comparables, puis gardez celle qui retient le mieux à 3 secondes.</p>
<div class="g">{cards}</div>
<table><tr><th>Variante</th><th>Vues</th><th>Rétention à 3 s</th><th>Durée moyenne</th><th>Partages / enregistrements</th></tr>{rows}</table>
</body></html>"""
    (dst / "variantes.html").write_text(doc, encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["propose", "make"])
    ap.add_argument("job")
    ap.add_argument("slug")
    ap.add_argument("--video")
    ap.add_argument("--quality", default="draft", choices=["draft", "standard", "delivery"])
    a = ap.parse_args()
    job = job_dir(a.job)
    if a.cmd == "propose":
        propose(job, a.slug)
    else:
        make(job, a.slug, a.video, a.quality)


if __name__ == "__main__":
    main()

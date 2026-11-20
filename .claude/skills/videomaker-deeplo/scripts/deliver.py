"""LIVRAISON -> renders/livraison/ : un MP4 masterisé par format, une couverture par format, le texte du post,
les crédits et une page récap (livraison.html) à ouvrir ou envoyer au client.

  python deliver.py <job> <slug> [--formats 9:16,1:1,16:9] [--quality delivery|draft] [--cover-at S]

Détecte seul le type de vidéo : storyboard présent -> build_scenes.py, sinon build_composition.py (rush).
Pour chaque format : composition à la bonne taille, rendu HyperFrames, master -14 LUFS (finalize.py),
couverture extraite du MP4. La composition du format principal est reconstruite à la fin (Studio inchangé).
Texte du post : work/<slug>_post.json écrit par Claude AVANT la livraison :
  {"caption": "…", "hashtags": ["#lyon", "…"], "cta": "…", "first_comment": "…"}
"""
import argparse
import datetime
import html
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from common import FORMATS, config, fail, job_dir, out, read_json, sh, size_of

HERE = Path(__file__).resolve().parent
NPX = ["cmd", "/c", "npx"] if os.name == "nt" else ["npx"]


def run_py(script, *args):
    r = subprocess.run([sys.executable, str(HERE / script), *args], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env={**os.environ, "PYTHONUTF8": "1"})
    last = (r.stdout.strip().splitlines() or ["{}"])[-1]
    try:
        res = json.loads(last)
    except json.JSONDecodeError:
        res = {}
    if r.returncode != 0 or not res.get("ok", True):
        fail(f"{script} a échoué", out=(r.stdout + r.stderr)[-800:])
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("job")
    ap.add_argument("slug")
    ap.add_argument("--formats", default="9:16,1:1,16:9")
    ap.add_argument("--quality", default="delivery", choices=["delivery", "draft", "looks"])
    ap.add_argument("--cover-at", type=float, help="instant de la couverture (s) ; défaut : fin de l'accroche")
    ap.add_argument("--lang", help="version sous-titrée traduite (translate.py) : nl, en…")
    ap.add_argument("--fps", type=int, help="images par seconde (défaut : celles de la composition, 30)")
    ap.add_argument("--apercu", action="store_true",
                    help="aperçu rapide pour validation : 15 i/s, qualité brouillon (~40 %% plus rapide), pas pour publier")
    a = ap.parse_args()
    job = job_dir(a.job)
    c = config(job)
    meta = read_json(job / "job.json")
    work = job / "work"
    scenes = (work / f"{a.slug}_storyboard.json").exists()
    builder = "build_scenes.py" if scenes else "build_composition.py"
    fmts = [f.strip() for f in a.formats.split(",") if f.strip()]
    for f in fmts:
        if f not in FORMATS:
            fail(f"format inconnu : {f}", connus=list(FORMATS))

    cover_t = a.cover_at
    if cover_t is None:
        if scenes:
            tm = read_json(work / f"{a.slug}_timing.json")["scenes"]
            first = next((x for x in tm if x.get("voice_start") is not None), tm[0])  # l'accroche, pas le logo d'intro
            cover_t = round(min(first["end"] - 0.3, (first.get("voice_start") or first["start"]) + 2.2), 2)
        else:
            br = c.get("branding", {})
            cover_t = 1.5 + (float(br.get("introDuration", 1.6)) - 0.45 if br.get("intro") else 0)

    if a.apercu:
        a.fps, a.quality = a.fps or 15, "draft"
    lg = ["--lang", a.lang] if a.lang else []
    sfx = f"_{a.lang}" if a.lang else ""
    dst = job / "renders" / (("apercu" if a.apercu else "livraison") + sfx)
    dst.mkdir(parents=True, exist_ok=True)
    made = []
    base = f"{c['visual']['width']}x{c['visual']['height']}"
    for f in fmts:
        tag = f.replace(":", "x") + sfx
        run_py(builder, str(job), a.slug, "--size", f, *lg)
        raw = job / "renders" / f"{a.slug}_{tag}.mp4"
        fps = ["-f", str(a.fps)] if a.fps else []
        r = subprocess.run(NPX + ["--yes", "hyperframes@0.9.71", "render", "-q", a.quality, "-w", "8", *fps, "-o", str(raw)],
                           cwd=job, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode != 0 or not raw.exists():
            fail(f"rendu {f} échoué", out=(r.stdout + r.stderr)[-800:])
        fin = run_py("finalize.py", str(job), str(raw))
        final = dst / f"{a.slug}_{tag}.mp4"
        shutil.move(fin["final"], final)
        raw.unlink(missing_ok=True)
        cover = dst / f"{a.slug}_{tag}_cover.jpg"
        cj = job / "work" / f"{a.slug}_cover.json"
        chosen = read_json(cj).get("choice") if cj.exists() else None
        if chosen and not a.lang:  # couverture avec titre choisie (covers.py pick) pour ce format
            Wc, Hc = size_of(f, config(job)["visual"])
            hit = list((job / "renders" / "covers").glob(f"{a.slug}_{chosen}-*_{Wc}x{Hc}.jpg"))
            if hit:
                shutil.copy2(hit[0], cover)
                made.append({"format": f, "video": final.name, "cover": cover.name, "lufs": fin["lufs"], "tp": fin["true_peak"],
                             "verdict": fin["verdict"], "mo": round(final.stat().st_size / 1e6, 1)})
                continue
        run_py(builder, str(job), a.slug, "--size", f, "--no-captions", *lg)  # couverture sans sous-titres
        snap = job / "work" / "cover_snap"
        shutil.rmtree(snap, ignore_errors=True)
        subprocess.run(NPX + ["--yes", "hyperframes@0.9.71", "snapshot", "--at", str(cover_t), "--no-end", "-o", str(snap)],
                       cwd=job, capture_output=True, text=True, encoding="utf-8", errors="replace")
        pngs = sorted(snap.glob("*.png")) if snap.exists() else []
        src = ["-i", str(pngs[0])] if pngs else ["-ss", str(cover_t), "-i", str(final)]
        sh(["ffmpeg", "-y", "-loglevel", "error", *src, "-frames:v", "1", "-q:v", "2", str(cover)], "ffmpeg (couverture)")
        made.append({"format": f, "video": final.name, "cover": cover.name, "lufs": fin["lufs"], "tp": fin["true_peak"],
                     "verdict": fin["verdict"], "mo": round(final.stat().st_size / 1e6, 1)})
    run_py(builder, str(job), a.slug, "--size", base)  # le Studio retrouve le format principal

    credits = (job / "renders" / "credits.txt").read_text(encoding="utf-8") if (job / "renders" / "credits.txt").exists() else ""
    pj = work / f"{a.slug}_post{sfx}.json"
    post = read_json(pj) if pj.exists() else {}
    text = post.get("caption", "")
    if post.get("cta"):
        text += "\n\n" + post["cta"]
    if post.get("hashtags"):
        text += "\n\n" + " ".join(post["hashtags"])
    if credits.strip():
        text += "\n\n" + credits.strip()
    (dst / "post.txt").write_text(text.strip() + "\n", encoding="utf-8")
    if credits:
        (dst / "credits.txt").write_text(credits, encoding="utf-8")

    vis = c["visual"]
    bg, ink, acc = vis.get("bgColor", "#f6f4f0"), vis.get("inkColor", "#1a1a1a"), vis["accentColor"]
    cards = "\n".join(
        f'''<figure><video src="{m["video"]}" poster="{m["cover"]}" controls playsinline preload="metadata"></video>
<figcaption><b>{m["format"]}</b> · {m["mo"]} Mo · {m["lufs"]} LUFS
<a href="{m["video"]}" download>Télécharger</a> <a href="{m["cover"]}" download>Couverture</a></figcaption></figure>'''
        for m in made)
    esc = html.escape
    page = f"""<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(meta.get("client", ""))} · {esc(meta.get("sujet", ""))}</title>
<style>
:root {{ --bg: {bg}; --ink: {ink}; --acc: {acc}; }}
* {{ box-sizing: border-box; }}
body {{ margin: 0; background: var(--bg); color: var(--ink); font: 16px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; }}
main {{ max-width: 1100px; margin: 0 auto; padding: 40px 16px 64px; }}
h1 {{ margin: 0 0 4px; font-size: 28px; }} .sub {{ opacity: .7; margin: 0 0 28px; }}
.grid {{ display: flex; flex-wrap: wrap; gap: 20px; align-items: flex-start; }}
figure {{ margin: 0; flex: 1 1 260px; max-width: 420px; }}
video {{ width: 100%; border-radius: 10px; background: #000; display: block; }}
figcaption {{ font-size: 14px; margin-top: 8px; }} figcaption a {{ color: var(--acc); margin-left: 10px; }}
h2 {{ font-size: 18px; margin: 36px 0 10px; border-top: 2px solid var(--acc); padding-top: 14px; }}
pre {{ white-space: pre-wrap; background: rgba(0,0,0,.05); padding: 16px; border-radius: 10px; font: 15px/1.5 inherit; }}
button {{ background: var(--acc); color: #fff; border: 0; padding: 10px 16px; border-radius: 8px; font-weight: 600; cursor: pointer; }}
</style></head><body><main>
<h1>{esc(meta.get("client", ""))} · {esc(meta.get("sujet", ""))}</h1>
<p class="sub">Livraison du {datetime.date.today():%d/%m/%Y} · {len(made)} format(s)</p>
<div class="grid">{cards}</div>
<h2>Texte du post</h2><pre id="post">{esc(text.strip()) or "(à écrire : work/" + esc(a.slug) + "_post.json)"}</pre>
<button onclick="navigator.clipboard.writeText(document.getElementById('post').innerText);this.textContent='Copié'">Copier le texte</button>
{f'<h2>Premier commentaire</h2><pre>{esc(post["first_comment"])}</pre>' if post.get("first_comment") else ""}
</main></body></html>"""
    (dst / "livraison.html").write_text(page, encoding="utf-8")
    out(ok=all(m["verdict"] == "OK" for m in made), dossier=str(dst), formats=made, couverture_a=cover_t,
        post="présent" if post else "absent (écris work/<slug>_post.json)", page=str(dst / "livraison.html"))


if __name__ == "__main__":
    main()

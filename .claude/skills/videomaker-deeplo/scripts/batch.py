"""LOT : plusieurs vidéos × langues × formats en une commande, une seule page récap pour le client.

  python batch.py plan <lot.json>    # ce qui est prêt, ce qui manque (traductions, textes de post), durée estimée
  python batch.py run  <lot.json>    # livraisons (deliver.py) puis jobs/_lots/<nom>/index.html

lot.json :
  {"name": "promo-printemps", "client": "Boulangerie Martin",
   "items": [{"job": "2026-04-02-martin-promo-printemps", "slug": "short"}, …],
   "langs": ["fr", "nl"], "formats": ["9:16", "1:1"], "quality": "delivery", "reuse": true}
"reuse": true garde une livraison déjà faite (même vidéo, langue et format) au lieu de la refaire.
La langue « fr » est la version d'origine ; les autres demandent translate.py (export, traduction, apply).
"""
import datetime
import html
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from common import FORMATS, ROOT, config, fail, job_dir, out, probe, read_json

HERE = Path(__file__).resolve().parent
RENDER_X = 6.6  # secondes de rendu (couvertures comprises) par seconde de vidéo et par format, mesuré sur un lot de 6


def item_info(it, lang):
    job = job_dir(it["job"])
    sl = it.get("slug", "short")
    work = job / "work"
    scenes = (work / f"{sl}_storyboard.json").exists()
    sfx = "" if lang == "fr" else f"_{lang}"
    ready, why = True, []
    if not ((work / f"{sl}_map.json").exists() or scenes):
        ready, why = False, why + ["pas encore monté (map.json / storyboard absent)"]
    if lang != "fr" and not (work / f"{sl}_text{sfx}.json").exists():
        ready, why = False, why + [f"à traduire : translate.py export {job.name} {sl} --to {lang}"]
    if not (work / f"{sl}_post{sfx}.json").exists():
        why.append("texte du post absent (livré sans)")
    dur = 0.0
    m = work / f"{sl}_map.json"
    if m.exists():
        dur = float(read_json(m)["out_duration"])
    elif (work / f"{sl}_timing.json").exists():
        dur = float(read_json(work / f"{sl}_timing.json")["duration"])
    br = config(job).get("branding", {})
    dur += (1.15 if br.get("intro") else 0) + (3.4 if br.get("outro") else 0)
    hook = work / f"{sl}_hook{sfx}.json"
    title = read_json(hook)["text"] if hook.exists() else read_json(job / "job.json").get("sujet", job.name)
    return {"job": job, "slug": sl, "lang": lang, "sfx": sfx, "ready": ready, "notes": why, "dur": dur, "title": title,
            "dir": job / "renders" / ("livraison" + sfx)}


def outputs(info, fmts):
    return [info["dir"] / f"{info['slug']}_{f.replace(':', 'x')}{info['sfx']}.mp4" for f in fmts]


def plan(spec):
    fmts = spec.get("formats", ["9:16"])
    rows, total = [], 0.0
    for it in spec["items"]:
        for lang in spec.get("langs", ["fr"]):
            i = item_info(it, lang)
            done = spec.get("reuse", True) and all(p.exists() for p in outputs(i, fmts))
            cost = 0 if done else i["dur"] * RENDER_X * len(fmts)
            total += cost if i["ready"] else 0
            rows.append({"video": i["job"].name, "langue": lang, "pret": i["ready"], "deja_livre": done,
                         "rendu_min": round(cost / 60, 1), "notes": i["notes"]})
    return rows, total


def page(spec, lot, entries, vis):
    esc = html.escape
    bg, ink, acc = vis.get("bgColor", "#f6f4f0"), vis.get("inkColor", "#1a1a1a"), vis["accentColor"]
    secs = []
    for e in entries:
        vids = "".join(f'<figure><video src="{v["src"]}" poster="{v["cover"]}" controls playsinline preload="none"></video>'
                       f'<figcaption>{esc(v["format"])} · <a href="{v["src"]}" download>MP4</a> · '
                       f'<a href="{v["cover"]}" download>couverture</a></figcaption></figure>' for v in e["videos"])
        pid = f'p{len(secs)}'
        post = (f'<pre id="{pid}">{esc(e["post"])}</pre><button onclick="navigator.clipboard.writeText('
                f'document.getElementById(\'{pid}\').innerText);this.textContent=\'Copié\'">Copier le texte</button>') if e["post"] else ""
        secs.append(f'<section><h2>{esc(e["title"])} <span class="lg">{esc(e["lang"].upper())}</span></h2>'
                    f'<div class="grid">{vids}</div>{post}</section>')
    return f"""<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(spec.get("client", ""))} · {esc(spec["name"])}</title><style>
:root {{ --bg: {bg}; --ink: {ink}; --acc: {acc}; }}
* {{ box-sizing: border-box; }} body {{ margin: 0; background: var(--bg); color: var(--ink); font: 16px/1.5 system-ui, "Segoe UI", sans-serif; }}
main {{ max-width: 1200px; margin: 0 auto; padding: 40px 16px 64px; }} h1 {{ margin: 0 0 4px; font-size: 28px; }}
.sub {{ opacity: .7; margin: 0 0 24px; }} section {{ border-top: 2px solid var(--acc); padding: 16px 0 28px; }}
h2 {{ font-size: 19px; margin: 0 0 12px; }} .lg {{ font-size: 12px; background: var(--acc); color: #fff; border-radius: 99px; padding: 2px 8px; vertical-align: middle; }}
.grid {{ display: flex; flex-wrap: wrap; gap: 16px; align-items: flex-start; }} figure {{ margin: 0; flex: 1 1 220px; max-width: 320px; }}
video {{ width: 100%; border-radius: 10px; background: #000; display: block; }} figcaption {{ font-size: 13px; margin-top: 6px; }}
figcaption a {{ color: var(--acc); }} pre {{ white-space: pre-wrap; background: rgba(0,0,0,.05); padding: 14px; border-radius: 10px; font: 14px/1.5 inherit; }}
button {{ background: var(--acc); color: #fff; border: 0; padding: 9px 14px; border-radius: 8px; font-weight: 600; cursor: pointer; }}
</style></head><body><main><h1>{esc(spec.get("client", ""))} · {esc(spec["name"])}</h1>
<p class="sub">{len(entries)} vidéo(s) · livré le {datetime.date.today():%d/%m/%Y}</p>{"".join(secs)}</main></body></html>"""


def run(spec, spec_path):
    fmts = spec.get("formats", ["9:16"])
    for f in fmts:
        if f not in FORMATS:
            fail(f"format inconnu : {f}")
    rows, _ = plan(spec)
    blocked = [r for r in rows if not r["pret"]]
    if blocked:
        fail("lot incomplet : lance d'abord batch.py plan et termine ce qui manque", bloques=blocked)
    lot = ROOT / "jobs" / "_lots" / spec["name"]
    lot.mkdir(parents=True, exist_ok=True)
    entries, rendered, vis = [], 0, None
    for it in spec["items"]:
        for lang in spec.get("langs", ["fr"]):
            i = item_info(it, lang)
            vis = vis or config(i["job"])["visual"]
            if not (spec.get("reuse", True) and all(p.exists() for p in outputs(i, fmts))):
                args = [sys.executable, str(HERE / "deliver.py"), str(i["job"]), i["slug"], "--formats", ",".join(fmts),
                        "--quality", spec.get("quality", "delivery")] + (["--lang", lang] if lang != "fr" else [])
                r = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace",
                                   env={**os.environ, "PYTHONUTF8": "1"})
                if r.returncode != 0:
                    fail(f"livraison échouée : {i['job'].name} ({lang})", out=(r.stdout + r.stderr)[-600:])
                rendered += 1
            sub = lot / f"{i['job'].name}{i['sfx']}"
            sub.mkdir(exist_ok=True)
            vids = []
            for f, mp4 in zip(fmts, outputs(i, fmts)):
                cover = mp4.with_name(mp4.stem + "_cover.jpg")
                shutil.copy2(mp4, sub / mp4.name)
                if cover.exists():
                    shutil.copy2(cover, sub / cover.name)
                vids.append({"format": f, "src": f"{sub.name}/{mp4.name}", "cover": f"{sub.name}/{cover.name}"})
            post = (i["dir"] / "post.txt").read_text(encoding="utf-8").strip() if (i["dir"] / "post.txt").exists() else ""
            entries.append({"title": i["title"], "lang": lang, "videos": vids, "post": post})
    (lot / "index.html").write_text(page(spec, lot, entries, vis), encoding="utf-8")
    shutil.copy2(spec_path, lot / "lot.json")
    size = sum(p.stat().st_size for p in lot.rglob("*.mp4")) / 1e6
    out(ok=True, lot=str(lot), page=str(lot / "index.html"), videos=sum(len(e["videos"]) for e in entries),
        rendues=rendered, reutilisees=len(entries) - rendered, taille_mo=round(size, 1))


def main():
    if len(sys.argv) < 3 or sys.argv[1] not in ("plan", "run"):
        fail("usage : batch.py plan|run <lot.json>")
    sp = Path(sys.argv[2]).resolve()
    spec = read_json(sp)
    if sys.argv[1] == "plan":
        rows, total = plan(spec)
        out(ok=all(r["pret"] for r in rows), lignes=rows, rendu_total_min=round(total / 60, 1),
            suite="batch.py run quand tout est prêt")
    else:
        run(spec, sp)


if __name__ == "__main__":
    main()

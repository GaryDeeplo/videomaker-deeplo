"""BIBLIOTHÈQUE de motions validées (le « hack » de Wissam) -> library/<type>/<nom>/ + library/index.html

  python library.py save --type scene --name hook-photo-titre --title "…" --desc "…" --use "quand l'utiliser"
         --tags elegant,photo --job <job> --clip renders/x.mp4 --at 0.2 --dur 4 [--file compositions/x.html …]
         [--usage '<snippet ou extrait de storyboard>']
  python library.py search "titre photo élégant" [--type scene]      # à lancer AVANT de créer un motion
  python library.py list [--type caption]
  python library.py use <nom> <job>                                   # copie le bloc dans le job, affiche le montage
  python library.py gallery                                           # régénère library/index.html

Types : block (sous-composition HyperFrames : compositions/<nom>.html, monté par data-composition-src),
component (extrait à fusionner dans une scène), scene (type de scène de build_scenes.py + extrait de storyboard),
caption (style de sous-titres), transition, intro, outro, lower-third.
Chaque entrée : meta.json, preview.mp4 (extrait du rendu VALIDÉ, 480 px, muet), poster.jpg, fichiers source.
On ne sauvegarde que ce que l'utilisateur a validé.
"""
import argparse
import datetime
import html
import json
import re
import shutil
import unicodedata
from pathlib import Path

from common import ROOT, fail, job_dir, out, read_json, sh, write_json

LIB = ROOT / "library"
TYPES = ["block", "component", "scene", "caption", "transition", "intro", "outro", "lower-third", "lottie", "registre"]


def norm(s):
    s = unicodedata.normalize("NFD", str(s).lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def entries(kind=None):
    res = []
    for m in sorted(LIB.glob("*/*/meta.json")):
        e = read_json(m)
        e["path"] = str(m.parent.relative_to(ROOT)).replace("\\", "/")
        if not kind or e["type"] == kind:
            res.append(e)
    return res


def save(a):
    if a.type not in TYPES:
        fail(f"type inconnu : {a.type}", types=TYPES)
    name = re.sub(r"[^a-z0-9-]+", "-", norm(a.name)).strip("-")
    d = LIB / a.type / name
    if d.exists() and not a.force:
        fail(f"{d} existe déjà (--force pour remplacer)")
    d.mkdir(parents=True, exist_ok=True)
    job = job_dir(a.job) if a.job else None
    files = []
    for f in a.file or []:
        p = Path(f)
        if not p.is_absolute() and job:
            p = job / p
        if not p.exists():
            fail(f"fichier introuvable : {p}")
        if p.resolve() != (d / p.name).resolve():
            shutil.copy2(p, d / p.name)
        files.append(p.name)
    if a.clip:
        clip = Path(a.clip)
        if not clip.is_absolute() and job:
            clip = job / clip
        if not clip.exists():
            fail(f"rendu introuvable : {clip}")
        sh(["ffmpeg", "-y", "-loglevel", "error", "-ss", str(a.at), "-t", str(a.dur), "-i", str(clip), "-an",
            "-vf", "scale='if(gt(iw,ih),640,360)':-2,fps=30", "-c:v", "libx264", "-crf", "27", "-preset", "slow",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(d / "preview.mp4")], "ffmpeg (aperçu)")
        sh(["ffmpeg", "-y", "-loglevel", "error", "-ss", str(a.dur * 0.6), "-i", str(d / "preview.mp4"),
            "-frames:v", "1", "-q:v", "3", str(d / "poster.jpg")], "ffmpeg (vignette)")
    meta = {"name": name, "type": a.type, "title": a.title or name, "description": a.desc or "",
            "when_to_use": a.use or "", "tags": [t.strip() for t in (a.tags or "").split(",") if t.strip()],
            "files": files, "usage": a.usage or "", "source_job": job.name if job else None,
            "preview": "preview.mp4" if a.clip else None, "created": str(datetime.date.today()), "uses": 0}
    old = d / "meta.json"
    if old.exists():
        meta["uses"] = read_json(old).get("uses", 0)
    write_json(d / "meta.json", meta)
    gallery()
    out(ok=True, saved=str(d), type=a.type, name=name, preview=bool(a.clip), galerie=str(LIB / "index.html"))


def search(q, kind=None):
    words = [w for w in re.split(r"\W+", norm(q)) if len(w) > 2]
    scored = []
    for e in entries(kind):
        hay = norm(" ".join([e["name"], e["title"], e["description"], e["when_to_use"], " ".join(e["tags"])]))
        s = sum(hay.count(w) for w in words) + 2 * sum(w in norm(" ".join(e["tags"])) for w in words)
        if s or not words:
            scored.append((s, e))
    scored.sort(key=lambda x: (-x[0], x[1]["name"]))
    out(ok=True, query=q, resultats=[{"score": s, "type": e["type"], "name": e["name"], "title": e["title"],
                                       "quand": e["when_to_use"], "tags": e["tags"], "path": e["path"]}
                                      for s, e in scored[:12]])


def use(name, job_arg):
    hits = [e for e in entries() if e["name"] == name]
    if not hits:
        fail(f"aucune entrée « {name} »")
    e = hits[0]
    src = ROOT / e["path"]
    job = job_dir(job_arg)
    copied = []
    if e["type"] == "registre":  # élément du registre HyperFrames : installé dans le job par la CLI officielle
        import subprocess, sys as _s
        npx = ["cmd", "/c", "npx"] if _s.platform == "win32" else ["npx"]
        r = subprocess.run(npx + ["--yes", "hyperframes@0.9.71", "add", name, "--no-clipboard"], cwd=job, capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        if r.returncode:
            fail(f"hyperframes add {name} a échoué", detail=(r.stderr or r.stdout)[-600:])
        copied = [ln.strip() for ln in (r.stdout or "").splitlines() if "compositions" in ln][:6]
    sub = {"block": "compositions", "component": "compositions/components"}.get(e["type"])
    if sub:
        (job / sub).mkdir(parents=True, exist_ok=True)
        for f in e["files"]:
            shutil.copy2(src / f, job / sub / f)
            copied.append(f"{sub}/{f}")
    meta = read_json(src / "meta.json")
    meta["uses"] = meta.get("uses", 0) + 1
    write_json(src / "meta.json", meta)
    out(ok=True, name=name, type=e["type"], copie=copied, usage=e["usage"], quand=e["when_to_use"])


def gallery():
    # les plus récentes d'abord (date de création, puis dernière sauvegarde) : les nouveautés sont en haut
    es = sorted(entries(), key=lambda e: (str(e.get("created", "")), (ROOT / e["path"] / "meta.json").stat().st_mtime), reverse=True)
    esc = html.escape
    cards = []
    for e in es:
        media = (f'<video src="{e["path"].split("/", 1)[1]}/preview.mp4" poster="{e["path"].split("/", 1)[1]}/poster.jpg" '
                 f'muted loop playsinline preload="none"></video>' if (ROOT / e["path"] / "preview.mp4").exists() else '<div class="nop">pas d\'aperçu</div>')
        tags = "".join(f"<span>{esc(t)}</span>" for t in e["tags"])
        usage = f'<details><summary>Utilisation</summary><pre>{esc(e["usage"])}</pre></details>' if e["usage"] else ""
        cards.append(f'''<article data-type="{e["type"]}" data-text="{esc(norm(" ".join([e["name"], e["title"], e["description"], " ".join(e["tags"])])))}">
<div class="m">{media}</div><div class="b"><p class="k">{esc(e["type"])} · {esc(e["name"])}</p><h3>{esc(e["title"])}</h3>
<p>{esc(e["description"])}</p>{f'<p class="u"><b>Quand :</b> {esc(e["when_to_use"])}</p>' if e["when_to_use"] else ""}
<div class="t">{tags}</div>{usage}<p class="s">{esc(e.get("source_job") or "")} · {esc(e["created"])} · utilisé {e.get("uses", 0)} fois</p></div></article>''')
    chips = "".join(f'<button data-f="{t}">{t}</button>' for t in TYPES if any(e["type"] == t for e in es))
    page = f"""<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Bibliothèque de motions</title><style>
:root {{ --bg: #f4f2ee; --card: #fff; --ink: #1b1a18; --mute: #6b675f; --acc: #c2410c; --line: #e4e0d8; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg: #141413; --card: #1e1d1b; --ink: #f1efe9; --mute: #a39e93; --line: #2e2c29; }} }}
* {{ box-sizing: border-box; }} body {{ margin: 0; background: var(--bg); color: var(--ink); font: 15px/1.5 system-ui, "Segoe UI", sans-serif; }}
header {{ position: sticky; top: 0; background: var(--bg); padding: 20px 16px 12px; border-bottom: 1px solid var(--line); z-index: 2; }}
h1 {{ margin: 0 0 10px; font-size: 22px; }} .bar {{ display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }}
input {{ flex: 1 1 220px; padding: 9px 12px; border: 1px solid var(--line); border-radius: 8px; background: var(--card); color: var(--ink); font: inherit; }}
.bar button {{ border: 1px solid var(--line); background: var(--card); color: var(--ink); border-radius: 99px; padding: 6px 12px; cursor: pointer; font: inherit; }}
.bar button.on {{ background: var(--ink); color: var(--bg); }}
main {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 16px; padding: 16px; max-width: 1400px; margin: 0 auto; }}
article {{ background: var(--card); border: 1px solid var(--line); border-radius: 12px; overflow: hidden; display: flex; flex-direction: column; }}
.m {{ background: #000; aspect-ratio: 9 / 12; display: flex; align-items: center; justify-content: center; }}
.m video {{ width: 100%; height: 100%; object-fit: contain; }} .nop {{ color: #888; font-size: 13px; }}
.b {{ padding: 12px 14px 14px; }} .k {{ margin: 0; font-size: 12px; color: var(--acc); text-transform: uppercase; letter-spacing: .06em; }}
h3 {{ margin: 4px 0 6px; font-size: 16px; }} .b p {{ margin: 0 0 6px; }} .u {{ color: var(--mute); font-size: 14px; }}
.t span {{ display: inline-block; font-size: 12px; border: 1px solid var(--line); border-radius: 99px; padding: 1px 8px; margin: 0 4px 4px 0; }}
pre {{ white-space: pre-wrap; font-size: 12px; background: var(--bg); padding: 8px; border-radius: 6px; overflow-x: auto; }}
.s {{ font-size: 12px; color: var(--mute); }} details summary {{ cursor: pointer; font-size: 13px; }}
</style></head><body><header><h1>Bibliothèque de motions · {len(es)} entrées</h1><div class="bar">
<input id="q" placeholder="Chercher : photo, chiffre, sous-titres, élégant…"><button data-f="" class="on">Tout</button>{chips}</div></header>
<main id="g">{"".join(cards) or "<p>Vide : sauvegarde un premier motion validé.</p>"}</main>
<script>
let f = "", q = "";
const norm = s => s.normalize("NFD").replace(/[\\u0300-\\u036f]/g, "").toLowerCase();
function apply() {{ document.querySelectorAll("article").forEach(a => {{
  a.hidden = (f && a.dataset.type !== f) || (q && !norm(q).split(/\\s+/).every(w => a.dataset.text.includes(w))); }}); }}
document.querySelectorAll(".bar button").forEach(b => b.onclick = () => {{
  document.querySelectorAll(".bar button").forEach(x => x.classList.remove("on")); b.classList.add("on"); f = b.dataset.f; apply(); }});
document.getElementById("q").oninput = e => {{ q = e.target.value.trim(); apply(); }};
document.querySelectorAll("article video").forEach(v => {{ const a = v.closest("article");
  a.onmouseenter = () => v.play().catch(() => {{}}); a.onmouseleave = () => {{ v.pause(); }}; }});
</script></body></html>"""
    LIB.mkdir(exist_ok=True)
    (LIB / "index.html").write_text(page, encoding="utf-8")
    return LIB / "index.html"


def main():
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    s = sp.add_parser("save")
    for k in ("--type", "--name"):
        s.add_argument(k, required=True)
    for k in ("--title", "--desc", "--use", "--tags", "--job", "--clip", "--usage"):
        s.add_argument(k)
    s.add_argument("--at", type=float, default=0.0)
    s.add_argument("--dur", type=float, default=4.0)
    s.add_argument("--file", nargs="*")
    s.add_argument("--force", action="store_true")
    q = sp.add_parser("search")
    q.add_argument("query")
    q.add_argument("--type")
    li = sp.add_parser("list")
    li.add_argument("--type")
    u = sp.add_parser("use")
    u.add_argument("name")
    u.add_argument("job")
    sp.add_parser("gallery")
    a = ap.parse_args()
    if a.cmd == "save":
        save(a)
    elif a.cmd == "search":
        search(a.query, a.type)
    elif a.cmd == "list":
        search("", a.type)
    elif a.cmd == "use":
        use(a.name, a.job)
    else:
        out(ok=True, galerie=str(gallery()), entrees=len(entries()))


if __name__ == "__main__":
    main()

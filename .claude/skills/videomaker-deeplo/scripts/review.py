"""VALIDATION CLIENT avant le rendu final -> work/review/validation.html (une seule page, à envoyer au client)

  python review.py <job> [--slug short] [--video renders/x.mp4] [--max 40] [--qa]
  python review.py <job> --valide [--note "ok par WhatsApp"]     # le client a dit oui -> work/valide.json

La page (d'après ghost-editor, approval_sheet.py, MIT) montre une image à chaque moment à juger : le début, ce que l'on
voit à 1,5 s, juste après chaque coupe (work/<slug>_map.json, issu de build_cut.py), chaque temps fort quand il arrive
(mots dynamiques, accroche, notes, blocs animés, b-roll : tout ce que index.html pose sur la timeline) et la fin.
Sous chaque image : le timecode, ce qui apparaît, le texte dit jusqu'à l'image suivante et les bruitages. Puis la
musique et les sons (crédits), et les points du contrôle qualité s'il y a un rapport (work/<slug>_qa.json ; --qa le
crée avec qa.py sur l'aperçu, sans rendu).
Le client écrit une remarque sous une image ; « Copier la liste des changements » met un texte propre (timecode +
remarque) dans son presse-papier, à coller dans un message ; « Tout est bon » copie son accord.

Images : extraites avec ffmpeg de l'aperçu le plus récent (renders/), sinon de la vidéo coupée (assets/<slug>_cut.mp4),
en JPEG légers intégrés à la page : un seul fichier, sans dépendance externe, lisible sur téléphone. Uniquement des
images de CE job (jamais d'aperçu de la bibliothèque ni d'un autre client).
Les timecodes sont ceux de la vidéo montée (intro comprise) ; work/review/review.json garde le plan des images
(temps de la composition et de la vidéo coupée) pour retrouver les mots visés par une remarque.
"""
import argparse
import base64
import datetime
import hashlib
import html
import json
import re
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path

from common import config, fail, job_dir, out, probe, read_json, write_json

esc = lambda s: html.escape(str(s), quote=True)  # noqa: E731
VOID = {"img", "br", "source", "input", "meta", "link", "hr", "wbr", "track", "area", "base", "col", "embed", "param"}
SONS = {"whoosh": "whoosh (passage)", "swoosh": "swoosh (passage)", "pop": "pop", "click": "clic", "tick": "tic",
        "ding": "ding", "hit": "impact", "boom": "boum", "sparkle": "scintillement", "chime": "carillon", "swell": "montée",
        "typing": "clavier", "cash": "caisse", "paper": "papier"}
TXT_KEYS = ("big", "title", "titre", "headline", "text", "texte", "label", "value", "valeur", "card", "name", "nom")


def fmt(t):
    t = round(max(0.0, t), 1)  # au dixième : deux images peuvent tomber dans la même seconde
    return f"{int(t // 60)}:{int(t % 60):02d},{int(round(t * 10)) % 10}"


# ---------------------------------------------------------------- lecture du montage
class Timeline(HTMLParser):
    """Chaque élément de index.html qui a un data-start, avec son texte (mots dynamiques, notes, accroches…)."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.items, self.stack, self.skip = [], [], 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ("script", "style"):
            self.skip += 1
        if tag in VOID:
            if "data-start" in a:
                self.items.append({"tag": tag, **a, "_txt": []})
            return
        it = {"tag": tag, **a, "_txt": []} if "data-start" in a else None
        if it:
            self.items.append(it)
        self.stack.append((tag, it))

    def handle_startendtag(self, tag, attrs):
        a = dict(attrs)
        if "data-start" in a:
            self.items.append({"tag": tag, **a, "_txt": []})

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.skip = max(0, self.skip - 1)
        for k in range(len(self.stack) - 1, -1, -1):  # HTML tolérant : on referme jusqu'à la balise correspondante
            if self.stack[k][0] == tag:
                del self.stack[k:]
                break

    def handle_data(self, data):
        if self.skip or not data.strip():
            return
        for _, it in self.stack:
            if it is not None:
                it["_txt"].append(data.strip())


def num(x, d=0.0):
    try:
        return float(x)
    except (TypeError, ValueError):
        return d


def label_of(it):
    txt = re.sub(r"\s+", " ", " ".join(it["_txt"])).strip()
    if not txt and it.get("data-variable-values"):
        try:
            v = json.loads(it["data-variable-values"])
            if "to" in v:  # compteur : la valeur d'arrivée et son libellé
                return f'{v.get("prefix") or ""}{v["to"]}{v.get("suffix") or ""} {v.get("label") or ""}'.strip()
            txt = next((str(v[k]) for k in TXT_KEYS if isinstance(v.get(k), (str, int, float)) and str(v[k]).strip()), "")
        except ValueError:
            pass
    return (txt[:70] + "…") if len(txt) > 70 else txt


def read_montage(job):
    """(T0 = début du contenu après l'intro, temps forts, débuts de plans b-roll, sons) depuis index.html."""
    idx = job / "index.html"
    if not idx.exists():
        return 0.0, [], [], []
    src = idx.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"master\.add\(\s*tl\s*,\s*([\d.]+)\s*\)", src)
    t0 = float(m.group(1)) if m else 0.0
    p = Timeline()
    p.feed(src)
    forts, plans, sons = [], [], []
    for it in p.items:
        s, d = num(it.get("data-start")), num(it.get("data-duration"), 1.0)
        cls, iid, vsrc = it.get("class") or "", it.get("id") or "", it.get("src") or ""
        if it["tag"] == "audio":
            if iid.startswith("sfx") or "/sfx/" in vsrc or vsrc.startswith("assets/sfx"):
                fam = Path(vsrc).stem.split("_")[0].lower()
                sons.append({"t": s, "famille": fam, "fichier": Path(vsrc).name})
            continue
        if iid == "root" or "cap" in cls.split() or "acut" in cls.split():
            continue  # racine, sous-titres (montrés à part), détourages (doublent les mots dynamiques)
        if it["tag"] == "video" and ("_cut" in vsrc or iid in ("a-roll", "a-fill")):
            continue  # la vidéo coupée elle-même : ses coupes viennent de map.json
        if it["tag"] == "video" and not iid.startswith("mo-"):
            plans.append({"t": s, "quoi": "plan " + Path(vsrc).stem[:40]})
            continue
        if it["tag"] == "video":  # animation Lottie posée sur un mot
            forts.append({"t": s + 0.4, "quoi": f"Animation ({Path(vsrc).stem.split('-')[0]})"})
            continue
        comp = it.get("data-composition-id") or ""
        lab = label_of(it)
        if "intro" in comp or iid == "brand-intro":
            quoi = "Intro"
        elif "outro" in comp or iid == "brand-outro":
            quoi = "Fin (logo)"
        elif "hook" in cls.split() or comp.startswith("accroche"):
            quoi = "Accroche" + (f" « {lab} »" if lab else "")
        else:
            quoi = f"« {lab} »" if lab else "Animation"
        land = s + min(0.6, 0.4 * max(d, 0.2))  # quand il a fini d'arriver
        forts.append({"t": land, "quoi": quoi})
    return t0, forts, plans, sons


def find_slug(job, slug):
    if slug:
        return slug
    cands = [(f.stat().st_mtime, f.name.rsplit("_", 1)[0]) for pat in ("*_map.json", "*_text.json")
             for f in (job / "work").glob(pat)]
    return max(cands)[1] if cands else None


def spoken_words(job, slug, t0):
    """Mots dits, en temps de la vidéo montée : sous-titres de text.json (temps de la vidéo coupée) + T0 ;
    sinon mots de words.json (temps du rush) ramenés sur la vidéo coupée par map.json."""
    w = job / "work"
    if slug and (w / f"{slug}_text.json").exists():
        caps = read_json(w / f"{slug}_text.json").get("captions", [])
        return [{"w": x["w"], "t": x["start"] + t0} for g in caps for x in g.get("words", [])]
    if slug and (w / f"{slug}_words.json").exists():
        ws = read_json(w / f"{slug}_words.json").get("words", [])
        mp = read_json(w / f"{slug}_map.json")["segments"] if (w / f"{slug}_map.json").exists() else None
        res = []
        for x in ws:
            if mp is None:
                res.append({"w": x["w"], "t": x["start"] + t0})
                continue
            seg = next((s for s in mp if s["src_start"] <= x["start"] < s["src_end"]), None)
            if seg:
                res.append({"w": x["w"], "t": seg["out_start"] + x["start"] - seg["src_start"] + t0})
        return res
    return []


def pick_video(job, slug, arg):
    """L'aperçu le plus récent (son nom commence par le slug de préférence), sinon la vidéo coupée."""
    if arg:
        v = Path(arg) if Path(arg).is_absolute() else job / arg
        if not v.exists():
            fail(f"vidéo introuvable : {v}")
        return v, "_cut" in v.stem
    rend = sorted((job / "renders").rglob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True) if (job / "renders").exists() else []
    rend = [p for p in rend if "avant_apres" not in p.stem and "comparaison" not in p.stem
            and not p.parent.name.startswith("livraison_") and not re.search(r"_[a-z]{2}$", p.stem)]  # pas les traductions
    mine = [p for p in rend if slug and p.stem.startswith(slug)]
    if mine or rend:
        return (mine or rend)[0], False
    cut = job / "assets" / f"{slug}_cut.mp4" if slug else None
    if cut and cut.exists():
        return cut, True
    fail("ni aperçu (renders/) ni vidéo coupée (assets/<slug>_cut.mp4) : lance d'abord build_cut.py ou un aperçu -q draft")


# ---------------------------------------------------------------- plan des images
def plan_frames(dur, t0, cuts, forts, plans, maxn):
    """d'après ghost-editor (MIT) : ouverture, 1,5 s, après chaque coupe, temps forts, fin ; fusion < 0,35 s ;
    au-delà de maxn images, on garde ouverture / fin / temps forts et on éclaircit les coupes régulièrement."""
    ms = [{"t": 0.05, "tags": ["Début"], "prio": 0}]
    if dur > 3:
        ms.append({"t": 1.5, "tags": ["À 1,5 s (ce qu'on voit en premier)"], "prio": 0})
    for n, c in enumerate(cuts, 1):
        ms.append({"t": c + 0.12, "tags": [f"Coupe {n}"], "prio": 2})
    for p in plans:
        ms.append({"t": p["t"] + 0.15, "tags": ["Changement de plan"], "prio": 2})
    for f in forts:
        ms.append({"t": f["t"], "tags": [f["quoi"]], "prio": 1})
    ms.append({"t": max(0.0, dur - 0.3), "tags": ["Fin"], "prio": 0})
    ms = sorted((m for m in ms if 0 <= m["t"] <= dur), key=lambda m: m["t"])
    merged = []
    for m in ms:
        if merged and m["t"] - merged[-1]["t"] < 0.35:
            merged[-1]["tags"] += [x for x in m["tags"] if x not in merged[-1]["tags"]]
            merged[-1]["prio"] = min(merged[-1]["prio"], m["prio"])
            continue
        merged.append(dict(m))
    if len(merged) > maxn:
        keep = [m for m in merged if m["prio"] < 2]
        rest = [m for m in merged if m["prio"] == 2]
        if len(keep) > maxn:  # trop de temps forts : on les éclaircit aussi
            rest, keep = keep, [m for m in keep if m["prio"] == 0]
        room = max(0, maxn - len(keep))
        step = len(rest) / room if room else 0
        keep += [rest[int(i * step)] for i in range(room)]
        merged = sorted(keep, key=lambda m: m["t"])
    for m in merged:
        m["t"] = round(m["t"], 3)
    return merged


def grab(video, t, width):
    """Une image JPEG légère (ffmpeg, seek rapide), en base64."""
    r = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{max(0.0, t):.3f}", "-i", str(video), "-frames:v", "1",
                        "-vf", f"scale={width}:-2", "-q:v", "6", "-f", "image2pipe", "-vcodec", "mjpeg", "-"],
                       capture_output=True)
    if (r.returncode or not r.stdout) and t > 0.6:  # dernière image : la vidéo finit un peu avant le son
        return grab(video, t - 0.5, width)
    return base64.b64encode(r.stdout).decode() if r.returncode == 0 and r.stdout else None


def montage_hash(job, slug):
    h = hashlib.sha1()
    for f in [job / "index.html"] + ([job / "work" / f"{slug}_map.json"] if slug else []):
        if f.exists():
            h.update(f.read_bytes())
    return h.hexdigest()[:8]


def read_qa(job, slug):
    for f in ([job / "work" / f"{slug}_qa.json"] if slug else []) + [job / "work" / "qa.json"]:
        if f.exists():
            raw = f.read_bytes()
            for enc in ("utf-8-sig", "utf-16"):  # « > fichier » sous PowerShell 5 écrit en UTF-16
                try:
                    return json.loads(raw.decode(enc)), f
                except (UnicodeDecodeError, ValueError):
                    continue
    return None, None


def run_qa(job, slug, video):
    r = subprocess.run([sys.executable, str(Path(__file__).with_name("qa.py")), str(job), slug, "--video", str(video)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    try:
        q = json.loads(r.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return None
    write_json(job / "work" / f"{slug}_qa.json", q)
    return q


# ---------------------------------------------------------------- page
CSS = """
:root{--bg:#f6f5f2;--card:#fff;--ink:#1b1b1b;--mute:#666;--line:#e3e0da;--acc:ACC;--warn:#b45309;--ok:#15803d}
@media (prefers-color-scheme:dark){:root{--bg:#121316;--card:#1c1e23;--ink:#f1f1f1;--mute:#a3a3a3;--line:#2e3138}}
*{box-sizing:border-box}html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif;padding-bottom:96px}
main{max-width:1100px;margin:0 auto;padding:20px 16px}
h1{font-size:22px;margin:4px 0 6px}h2{font-size:17px;margin:32px 0 10px;padding-top:12px;border-top:2px solid var(--acc)}
.sub{color:var(--mute);font-size:13px}.how{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px 14px;margin:14px 0}
.how ol{margin:6px 0 0;padding-left:20px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:14px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;overflow:hidden;display:flex;flex-direction:column}
.card.on{border-color:var(--acc);box-shadow:0 0 0 2px var(--acc)}
.shot{position:relative;background:#000;cursor:zoom-in}.shot img{width:100%;display:block}
.tc{position:absolute;left:8px;top:8px;background:rgba(0,0,0,.72);color:#fff;border-radius:6px;padding:2px 8px;font:600 13px ui-monospace,Menlo,Consolas,monospace}
.qa{position:absolute;right:8px;top:8px;background:var(--warn);color:#fff;border-radius:6px;padding:2px 7px;font-size:12px;font-weight:700}
.meta{padding:10px 12px 12px;display:grid;gap:6px;font-size:13.5px}
.tags{display:flex;flex-wrap:wrap;gap:4px}.tag{font-size:12px;font-weight:600;padding:1px 8px;border-radius:999px;border:1px solid var(--line);background:var(--bg)}
.said{color:var(--ink)}.said:before{content:"Dit : ";color:var(--mute);font-size:12px}.said.none{color:var(--mute);font-style:italic}.said.none:before{content:""}
.sx{color:var(--mute);font-size:12.5px}
textarea{width:100%;min-height:44px;border:1px solid var(--line);border-radius:8px;padding:8px;font:inherit;font-size:14px;background:var(--bg);color:var(--ink);resize:vertical}
ul.l{margin:0;padding-left:20px}ul.l li{margin:3px 0}.w{color:var(--warn)}
.bar{position:fixed;left:0;right:0;bottom:0;background:var(--card);border-top:1px solid var(--line);padding:10px 16px;display:flex;gap:10px;justify-content:center;z-index:5}
.btn{border:0;border-radius:10px;padding:12px 16px;font-family:inherit;font-weight:600;font-size:15px;cursor:pointer;flex:1;max-width:320px}
.btn.go{background:var(--ok);color:#fff}.btn.ch{background:var(--acc);color:#fff}
.lb{position:fixed;inset:0;background:rgba(0,0,0,.9);display:none;align-items:center;justify-content:center;z-index:9}.lb img{max-height:94vh;max-width:94vw;border-radius:8px}
.toast{position:fixed;left:50%;bottom:84px;transform:translateX(-50%);background:var(--ink);color:var(--bg);font-weight:600;padding:10px 16px;border-radius:10px;display:none;z-index:10;max-width:90vw;text-align:center}
footer{color:var(--mute);font-size:12px;margin-top:36px}
@media (max-width:560px){.grid{grid-template-columns:repeat(2,1fr);gap:10px}.meta{font-size:12.5px;padding:8px}.btn{padding:12px 8px;font-size:14px}}
"""

JS = """
const B=document.body.dataset,KEY='validation:'+B.job+':'+B.hash;
const st=(()=>{try{return JSON.parse(localStorage.getItem(KEY)||'{}')}catch(e){return {}}})();
const save=()=>{try{localStorage.setItem(KEY,JSON.stringify(st))}catch(e){}};
document.querySelectorAll('.card').forEach(c=>{const n=c.querySelector('textarea');if(st[c.id]){n.value=st[c.id];c.classList.add('on')}
 n.oninput=()=>{st[c.id]=n.value;c.classList.toggle('on',!!n.value.trim());save()}});
const g=document.getElementById('gnote');if(st._g)g.value=st._g;g.oninput=()=>{st._g=g.value;save()};
document.querySelectorAll('.shot').forEach(s=>s.onclick=()=>{const lb=document.getElementById('lb');lb.querySelector('img').src=s.querySelector('img').src;lb.style.display='flex'});
document.getElementById('lb').onclick=e=>e.currentTarget.style.display='none';
function toast(m){const x=document.getElementById('toast');x.textContent=m;x.style.display='block';setTimeout(()=>x.style.display='none',2600)}
function fb(t){const a=document.createElement('textarea');a.value=t;a.style.position='fixed';a.style.opacity='0';document.body.appendChild(a);a.focus();a.select();
 let ok=false;try{ok=document.execCommand('copy')}catch(e){}a.remove();return ok}
function copy(t,m){const done=()=>toast(m),fail=()=>{if(fb(t))done();else prompt('Copiez ce texte :',t)};
 if(navigator.clipboard&&window.isSecureContext){navigator.clipboard.writeText(t).then(done,fail)}else fail()}
const head='la vidéo « '+B.title+' » (version '+B.hash+')';
document.getElementById('changes').onclick=()=>{const L=[];
 document.querySelectorAll('.card').forEach(c=>{const n=c.querySelector('textarea').value.trim();if(n)L.push('- '+c.dataset.tc+' : '+n.replace(/\\s*\\n\\s*/g,' / '))});
 if(g.value.trim())L.push('- En général : '+g.value.trim());
 if(!L.length){toast('Écrivez d\\'abord une remarque sous une image (ou appuyez sur « Tout est bon »).');return}
 copy('Changements pour '+head+' :\\n'+L.join('\\n'),'Liste copiée : collez-la dans votre message.')};
document.getElementById('approve').onclick=()=>copy('Tout est bon pour '+head+' : vous pouvez lancer la version finale.'+(g.value.trim()?'\\nRemarque : '+g.value.trim():''),
 'Accord copié : collez-le dans votre message.');
"""


def page(meta, accent, frames, sound_lines, qa, qa_file, hsh, job_name, dur, src_name, stale):
    title = meta.get("sujet") or job_name
    o = [f'<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
         f'<title>Validation · {esc(title)}</title><style>{CSS.replace("ACC", accent)}</style></head>'
         f'<body data-job="{esc(job_name)}" data-hash="{hsh}" data-title="{esc(title)}"><main>']
    o.append(f'<div class="sub">Vidéo à valider · {esc(meta.get("client") or "")}</div><h1>{esc(title)}</h1>')
    o.append(f'<div class="sub">Durée {fmt(dur)} · {len(frames)} images · version {hsh} · '
             f'{datetime.date.today():%d/%m/%Y}</div>')
    o.append('<div class="how"><b>Comment valider</b><ol><li>Regardez chaque image et le texte dit dessous (touchez une image '
             'pour l\'agrandir).</li><li>Si quelque chose ne va pas, écrivez-le dans la case sous l\'image.</li>'
             '<li>Appuyez sur « Copier la liste des changements » et collez-la dans votre message. Si tout vous convient, '
             'appuyez sur « Tout est bon ».</li></ol></div>')
    o.append('<div class="grid">')
    for i, f in enumerate(frames):
        tags = "".join(f'<span class="tag">{esc(t)}</span>' for t in f["tags"])
        said = f'<div class="said">{esc(f["texte"])}</div>' if f["texte"] else '<div class="said none">(pas de parole)</div>'
        sx = f'<div class="sx">Sons : {esc(", ".join(f["sons"]))}</div>' if f["sons"] else ""
        qa_b = f'<span class="qa" title="{esc(" ; ".join(f["qa"]))}">!</span>' if f["qa"] else ""
        img = f'<img alt="Image à {fmt(f["t"])}" loading="lazy" src="data:image/jpeg;base64,{f["img"]}">' if f["img"] else \
            '<div style="aspect-ratio:9/16;color:#999;padding:20px">image indisponible</div>'
        o.append(f'<div class="card" id="f{i}" data-tc="{fmt(f["t"])}"><div class="shot">{img}<span class="tc">{fmt(f["t"])}</span>{qa_b}</div>'
                 f'<div class="meta"><div class="tags">{tags}</div>{said}{sx}'
                 f'<textarea placeholder="Remarque sur ce moment (facultatif)"></textarea></div></div>')
    o.append('</div>')
    o.append('<h2>Remarque générale</h2><textarea id="gnote" placeholder="Une remarque qui vaut pour toute la vidéo (facultatif)"></textarea>')
    if sound_lines:
        o.append('<h2>Musique et sons</h2><ul class="l">' + "".join(f"<li>{esc(x)}</li>" for x in sound_lines) + "</ul>")
    if qa:
        bad, info = qa.get("a_revoir") or [], qa.get("infos") or []
        o.append(f'<h2>Contrôle automatique</h2><p class="sub">Mesuré sur {esc(Path(qa.get("video") or "aperçu").name)} : '
                 f'{esc(qa.get("verdict") or "")}. Ces points seront corrigés avant la version finale.</p><ul class="l">')
        o += [f'<li class="w">{esc(x)}</li>' for x in bad] + [f"<li>{esc(x)}</li>" for x in info]
        if not bad and not info:
            o.append("<li>Rien à signaler.</li>")
        o.append("</ul>")
    o.append(f'<footer>Images tirées de {esc(src_name)}{" (aperçu antérieur au dernier montage)" if stale else ""}. '
             f'Les timecodes sont ceux de la vidéo montée.</footer></main>')
    o.append('<div class="bar"><button class="btn ch" id="changes">Copier la liste des changements</button>'
             '<button class="btn go" id="approve">Tout est bon</button></div>')
    o.append(f'<div class="lb" id="lb"><img alt=""></div><div class="toast" id="toast"></div><script>{JS}</script></body></html>')
    return "".join(o)


# ---------------------------------------------------------------- commandes
def valide(job, slug, note):
    rv = job / "work" / "review" / "review.json"
    r = read_json(rv) if rv.exists() else {}
    hsh = montage_hash(job, slug)
    d = {"valide": True, "date": datetime.datetime.now().isoformat(timespec="seconds"), "version": hsh,
         "page": r.get("page"), "version_page": r.get("hash")}
    if note:
        d["note"] = note
    write_json(job / "work" / "valide.json", d)
    out(ok=True, fichier=str(job / "work" / "valide.json"), version=hsh,
        attention=None if not r or r.get("hash") == hsh else "le montage a changé depuis la page envoyée au client (version "
        f"{r.get('hash')}) : vérifie que l'accord porte bien sur cette version")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("job")
    ap.add_argument("--slug")
    ap.add_argument("--video", help="vidéo d'où tirer les images (défaut : aperçu le plus récent, sinon la vidéo coupée)")
    ap.add_argument("--max", type=int, default=40, help="nombre maximal d'images")
    ap.add_argument("--qa", action="store_true", help="lance qa.py sur l'aperçu (mesures ffmpeg, pas de rendu) -> work/<slug>_qa.json")
    ap.add_argument("--valide", action="store_true", help="le client a validé : écrit work/valide.json avec la date")
    ap.add_argument("--note", default="")
    a = ap.parse_args()
    job = job_dir(a.job)
    slug = find_slug(job, a.slug)
    if a.valide:
        return valide(job, slug, a.note)
    meta = read_json(job / "job.json")
    accent = (config(job).get("visual") or {}).get("accentColor") or "#c2410c"
    if not re.fullmatch(r"#[0-9a-fA-F]{3,8}", str(accent)):
        accent = "#c2410c"

    t0, forts, plans, sons = read_montage(job)
    video, is_cut = pick_video(job, slug, a.video)
    info = probe(video)
    shift = t0 if is_cut else 0.0  # la vidéo coupée n'a pas l'intro : temps de la vidéo = temps du montage - T0
    dur = info["duration"] + shift
    stale = (not is_cut and (job / "index.html").exists()  # deliver.py retouche index.html juste après son rendu : 2 min de marge
             and (job / "index.html").stat().st_mtime > video.stat().st_mtime + 120)

    w = job / "work"
    segs = read_json(w / f"{slug}_map.json")["segments"] if slug and (w / f"{slug}_map.json").exists() else []
    cuts = [s["out_start"] + t0 for s in segs if s["out_start"] > 0.05]
    if is_cut:  # sans l'habillage, seuls la coupe et les mots comptent
        forts, plans, sons = [], [], []
    words = spoken_words(job, slug, t0)
    frames = plan_frames(dur, t0, cuts, forts, plans, a.max)

    qa, qa_file = (run_qa(job, slug, video), None) if a.qa and slug and not is_cut else read_qa(job, slug)
    qa_pts = []
    for line in (qa or {}).get("a_revoir", []) + (qa or {}).get("infos", []):
        m = re.search(r"à\s*([\d.]+)\s*s", line)
        if m:
            qa_pts.append((float(m.group(1)), line))

    W = 360 if info["height"] and info["width"] and info["height"] >= info["width"] else 480
    for i, f in enumerate(frames):
        end = frames[i + 1]["t"] if i + 1 < len(frames) else dur + 1
        start = 0.0 if i == 0 else f["t"]
        f["texte"] = " ".join(x["w"] for x in words if start <= x["t"] < end)
        fam = []
        for s in sons:  # un bruitage de coupe part un peu avant l'image : fenêtre décalée de 0,3 s
            if start - 0.3 <= s["t"] < end - 0.3 and SONS.get(s["famille"], s["famille"]) not in fam:
                fam.append(SONS.get(s["famille"], s["famille"]))
        f["sons"] = fam
        f["qa"] = [ln for t, ln in qa_pts if start <= t < end]
        f["img"] = grab(video, f["t"] - shift, W)
        f["t_coupee"] = round(f["t"] - t0, 3) if f["t"] >= t0 else None

    sound_lines = []
    mj = w / f"{slug}_music.json" if slug else None
    if mj and mj.exists():
        m = read_json(mj)
        sound_lines.append(f"Musique : « {m.get('title') or Path(m.get('file', '')).stem} »"
                           + (f" de {m['creator']}" if m.get("creator") else "")
                           + (f", licence {str(m['license']).upper()}" if m.get("license") else "")
                           + (" (baissée sous la voix)" if m.get("ducked") else ""))
    if sons:
        cnt = {}
        for s in sons:
            k = SONS.get(s["famille"], s["famille"])
            cnt[k] = cnt.get(k, 0) + 1
        sound_lines.append("Bruitages : " + ", ".join(f"{k} × {n}" for k, n in cnt.items()))
    cred = job / "renders" / "credits.txt"
    if cred.exists():
        sound_lines += [f"Crédit : {ln.strip()}" for ln in cred.read_text(encoding="utf-8").splitlines()
                        if ln.strip() and not ln.lower().startswith("musique")]

    hsh = montage_hash(job, slug)
    dst = w / "review"
    dst.mkdir(parents=True, exist_ok=True)
    pg = dst / "validation.html"
    pg.write_text(page(meta, accent, frames, sound_lines, qa, qa_file, hsh, job.name, dur, video.name, stale), encoding="utf-8")
    write_json(dst / "review.json", {"hash": hsh, "slug": slug, "video": str(video.relative_to(job)), "t0": t0,
                                     "cree": datetime.datetime.now().isoformat(timespec="seconds"), "page": str(pg),
                                     "images": [{k: f[k] for k in ("t", "t_coupee", "tags", "texte", "sons", "qa")} for f in frames]})
    out(ok=True, page=str(pg), taille_ko=round(pg.stat().st_size / 1024), images=len(frames),
        sans_image=sum(1 for f in frames if not f["img"]), video=str(video.relative_to(job)), version=hsh,
        coupes=len(cuts), temps_forts=len(forts), qa=(qa or {}).get("verdict") if qa else None,
        attention="aperçu plus ancien que index.html : refais un aperçu -q draft pour des images à jour" if stale else None,
        suite="envoie la page au client ; ses changements reviennent en « m:ss : remarque » ; s'il dit oui : review.py <job> --valide")


if __name__ == "__main__":
    main()

"""VITRINE et DÉMO autour d'un montage rendu (pour montrer ce que fait le skill) -> renders/<slug>_vitrine.mp4 | _demo.mp4

  python showcase.py vitrine <job> <slug> [--montage renders/x.mp4] [--par "Claude"] [--cta "Clique sur le *lien en bas*"]
         [--sous "pour en savoir plus"] [--render draft|delivery]
      « Brut » (le rush d'origine, calé sur le montage : il saute à chaque coupe, « ✂ −1,2 s » montre ce qui part, timecode
      et barre de lecture) au-dessus de « Montage fait par “Claude” » (le rendu, avec son son), pied « Clique sur le lien ».
      Montage vertical : les deux côte à côte ; paysage : l'un sous l'autre.
  python showcase.py demo <job> <slug> [--montage …] [--app Claude] [--logo logo:claude] [--objection "pseudo: phrase"]
         [--demande "Monte mon rush avec mon skill."] [--skill videomaker-deeplo] [--effets "a;b;c"] [--render …]
      Fausse appli d'agent : objection épinglée en haut (le sceptique), la demande (vignette du rush + skill + phrase),
      « Voilà ton reel ✓ », le montage qui joue, les effets qui se cochent un par un, Download cliqué -> « Enregistré ».
      Effets lus dans le job si --effets est absent (blancs coupés, sous-titres, maquettes, zooms, musique…).

  python showcase.py portfolio <job> <slug> --videos renders/a.mp4,renders/b.mp4,… | --lib nom1,nom2,…
         [--entete "*Premium* Motion Graphics"] [--duree 10] [--rythme 2.6] [--musique assets/x.mp3] [--render …]
      Vitrine de portfolio : 3 écrans verticaux en quinconce (2 en haut, 1 en bas qui chevauche) qui jouent en même temps,
      chacun enchaîne les vidéos toutes les --rythme s, décalé des autres (toujours quelque chose qui bouge) ; titre fixe
      (*mot* en serif italique sur sa ligne). --lib : aperçus de la bibliothèque (library/<type>/<nom>/preview.mp4).

Le rush brut vient de work/<slug>_plan.json (source) et work/<slug>_map.json (coupes) ; --brut <fichier> sinon.
Les logos d'outils (logo:claude…) sont un usage informatif : ta propre utilisation de l'outil, jamais un faux partenariat.
"""
import argparse
import html
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import panel as pn
from common import ROOT, config, fail, job_dir, out, probe, read_json

NPX = ["cmd", "/c", "npx"] if sys.platform == "win32" else ["npx"]
esc = lambda s: html.escape(str(s), quote=True)
W, H = 1080, 1920


def vinfo(v):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height:format=duration",
                        "-of", "json", str(v)], capture_output=True, text=True)
    d = json.loads(r.stdout)
    return int(d["streams"][0]["width"]), int(d["streams"][0]["height"]), float(d["format"]["duration"])


def montage_of(job, slug, arg):
    if arg:
        v = Path(arg) if Path(arg).is_absolute() else job / arg
        if not v.exists():
            fail(f"{v} introuvable")
        return v
    cands = [p for p in (job / "renders").glob("*.mp4") if not re.search(r"_(vitrine|demo)", p.stem)]
    pref = [p for p in cands if p.stem.startswith(slug)]
    if not (pref or cands):
        fail("aucun rendu du montage : rends-le d'abord (render -q draft ou delivery)")
    return max(pref or cands, key=lambda p: p.stat().st_mtime)


def raw_of(job, slug, arg):
    """(fichier brut, segments [(src_start, src_end, out_start, out_end)], décalage du contenu dans le rendu)."""
    if arg:
        p = Path(arg) if Path(arg).is_absolute() else job / arg
        return (p if p.exists() else fail(f"{p} introuvable")), None, 0.0
    plan, mp = job / "work" / f"{slug}_plan.json", job / "work" / f"{slug}_map.json"
    if not plan.exists() or not mp.exists():
        fail("pas de rush dérushé pour ce slug : --brut <fichier>")
    src = Path(read_json(plan)["source"])
    segs = [(s["src_start"], s["src_end"], s["out_start"], s["out_end"]) for s in read_json(mp)["segments"]]
    t0 = 0.0
    if (job / "index.html").exists():  # accroche / intro avant le contenu : le brut attend sous elle
        m = re.search(r"master\.add\(tl, ([\d.]+)\)", (job / "index.html").read_text(encoding="utf-8"))
        t0 = float(m.group(1)) if m else 0.0
    return src, segs, t0


def project(job, name):
    d = job / "work" / name
    shutil.rmtree(d, ignore_errors=True)
    (d / "assets").mkdir(parents=True)
    shutil.copy2(ROOT / "studio" / "hyperframes.json", d / "hyperframes.json")
    return d


def proxy(src, dst, height=960):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-vf", f"scale=-2:{height}", "-an", "-c:v", "libx264", "-preset", "veryfast",
                    "-crf", "22", "-g", "15", str(dst)], check=True)


def mmss(t):
    return f"{int(t // 60)}:{int(t % 60):02d}"


def accent_md(s, cls="k"):
    return re.sub(r"\*([^*]+)\*", rf'<span class="{cls}">\1</span>', esc(s))


def page(title, css, body, js, dur, fonts):
    return f"""<!doctype html>
<html lang="fr">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width={W}, height={H}" />
<title>{esc(title)}</title>
<script src="https://cdn.jsdelivr.net/npm/gsap@3.15.0/dist/gsap.min.js"></script>
<style>
  {fonts}
  html, body {{ margin: 0; width: {W}px; height: {H}px; overflow: hidden; background: #000; }}
  #root {{ position: relative; width: {W}px; height: {H}px; overflow: hidden; font-family: 'Inter', sans-serif; }}
{css}
</style>
</head>
<body>
  <div id="root" data-composition-id="{title}" data-start="0" data-width="{W}" data-height="{H}" data-duration="{round(dur, 3)}">
{body}
  </div>
<script>
  window.__timelines = window.__timelines || {{}};
  const tl = gsap.timeline({{ paused: true }});
{js}
  window.__timelines["{title}"] = tl;
</script>
</body>
</html>
"""


def render(d, dst, quality):
    cmd = NPX + ["--yes", "hyperframes@0.9.71", "render", "-q", quality, "-w", "8"] + (["-f", "15"] if quality == "draft" else []) + ["-o", str(dst)]
    r = subprocess.run(cmd, cwd=d, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0 or not dst.exists():
        fail("rendu échoué", detail=(r.stdout + r.stderr)[-800:])
    return dst


def vitrine(a, job):
    c = config(job)
    acc = a.accent or "#c8541f"  # orange brûlé : lisible sur le fond crème
    mv = montage_of(job, a.slug, a.montage)
    mw, mh, mdur = vinfo(mv)
    src, segs, t0 = raw_of(job, a.slug, a.brut)
    rdur = probe(src)["duration"]
    d = project(job, "vitrine")
    shutil.copy2(mv, d / "assets" / "montage.mp4")
    proxy(src, d / "assets" / "brut.mp4")
    side = mw < mh  # montage vertical : côte à côte
    if side:
        cw = 500
        ch = round(cw * mh / mw)
        x1, x2 = 27, W - 27 - cw
        y0 = round((H - (ch + 150 + 200)) / 2) + 150
        boxes = {"brut": (x1, y0, cw, ch), "mont": (x2, y0, cw, ch)}
        labs = {"brut": (x1, y0 - 140, cw), "mont": (x2, y0 - 140, cw)}
        foot_y = y0 + ch + 60
    else:
        cw = 900
        ch = round(cw * mh / mw)
        y0 = round((H - (2 * ch + 2 * 96 + 50 + 200)) / 2) + 96
        boxes = {"brut": ((W - cw) // 2, y0, cw, ch), "mont": ((W - cw) // 2, y0 + ch + 50 + 96, cw, ch)}
        labs = {"brut": ((W - cw) // 2, y0 - 96, cw), "mont": ((W - cw) // 2, y0 + ch + 50, cw)}
        foot_y = y0 + 2 * ch + 50 + 96 + 60
    # le brut, calé sur le montage : un plan par morceau gardé (data-media-start), il saute à chaque coupe
    vids, cuts, js = [], [], []
    if segs:
        for k, (s0, s1, o0, o1) in enumerate(segs):
            st = 0.0 if k == 0 else t0 + o0
            ms = max(0.0, s0 - t0) if k == 0 else s0
            ln = (t0 + o1) - st if k + 1 < len(segs) else mdur - st
            if ln <= 0.02:
                continue
            vids.append(f'      <video id="bv{k}" class="clip bv" src="assets/brut.mp4" data-start="{round(st, 3)}" data-duration="{round(ln, 3)}" '
                        f'data-media-start="{round(ms, 3)}" data-track-index="{2 + k % 2}" muted playsinline></video>')
            if k:
                gone = s0 - segs[k - 1][1]
                if gone >= 0.15:
                    cid = f"ct{k}"
                    cuts.append(f'      <div class="clip cut" id="{cid}" data-start="{round(t0 + o0, 3)}" data-duration="0.8" data-track-index="{6 + k % 2}">'
                                f'<span>✂ −{f"{gone:.1f}".replace(".", ",")} s</span></div>')
                    js.append(f'  tl.fromTo("#{cid} span", {{ opacity: 0, scale: 0.6, y: 10 }}, {{ opacity: 1, scale: 1, y: 0, duration: 0.18, ease: "back.out(2.6)", '
                              f'immediateRender: false }}, {round(t0 + o0, 3)});')
                    js.append(f'  tl.to("#{cid} span", {{ opacity: 0, duration: 0.2 }}, {round(t0 + o0 + 0.58, 3)});')
        seg_js = json.dumps([[round(t0 + o0, 3), round(s0, 3)] for s0, s1, o0, o1 in segs])
    else:
        vids.append(f'      <video id="bv0" class="clip bv" src="assets/brut.mp4" data-start="0" data-duration="{round(min(mdur, rdur), 3)}" '
                    f'data-track-index="2" muted playsinline></video>')
        seg_js = "[[0, 0]]"
    n_cuts = len(cuts)
    js.append(f'  (function () {{ const S = {seg_js}, tc = document.querySelector("#tc"), pb = document.querySelector("#pb"), o = {{ v: 0 }};'
              f' function f(t) {{ return Math.floor(t / 60).toString().padStart(2, "0") + ":" + (t % 60).toFixed(1).padStart(4, "0"); }}'
              f' tl.fromTo(o, {{ v: 0 }}, {{ v: {round(mdur, 3)}, duration: {round(mdur, 3)}, ease: "none", immediateRender: true, onUpdate: function () {{'
              f' let s = S[0]; for (const x of S) {{ if (x[0] <= o.v) s = x; }} const r = Math.max(0, Math.min({rdur:.3f}, s[1] + o.v - s[0]));'
              f' tc.textContent = f(r); pb.style.width = (100 * r / {rdur:.3f}) + "%"; }} }}, 0); }})();')
    js.append('  tl.fromTo(".lab, .card, .foot > *", { opacity: 0, y: 30 }, { opacity: 1, y: 0, duration: 0.5, stagger: 0.08, ease: "power3.out", immediateRender: false }, 0.05);')
    bx, by, bw, bh = boxes["brut"]
    mx, my, mw_, mh_ = boxes["mont"]
    lb, lm = labs["brut"], labs["mont"]
    par = esc(a.par)
    body = f"""    <div id="bg"></div>
    <div class="lab" style="left:{lb[0]}px;top:{lb[1]}px;width:{lb[2]}px"><b>Brut</b>{'<em>&nbsp;</em>' if side else ''}<small>{mmss(rdur)} de rush</small></div>
    <div class="card" style="left:{bx}px;top:{by}px;width:{bw}px;height:{bh}px">
{chr(10).join(vids)}
      <div class="rec"><i></i>BRUT <span id="tc">00:00.0</span> / {f"{int(rdur // 60):02d}:{rdur % 60:04.1f}"}</div>
{chr(10).join(cuts)}
      <div class="pbar"><i id="pb"></i></div>
    </div>
    <div class="lab" style="left:{lm[0]}px;top:{lm[1]}px;width:{lm[2]}px">{f'<b>Montage</b><em>fait par <span class="k">“{par}”</span></em>' if side else f'<b>Montage fait par <span class="k">“{par}”</span></b>'}
      <small>{mmss(mdur)}{f" · {n_cuts} coupes" if n_cuts else ""}</small></div>
    <div class="card mont" style="left:{mx}px;top:{my}px;width:{mw_}px;height:{mh_}px">
      <video id="mv" class="clip" src="assets/montage.mp4" data-start="0" data-duration="{round(mdur, 3)}" data-track-index="1" playsinline data-has-audio="true" data-volume="1"></video>
    </div>
    <div class="foot" style="top:{foot_y}px"><b>{accent_md(a.cta)}</b>{f"<small>{esc(a.sous)}</small>" if a.sous else ""}</div>"""
    side_lab = "text-align: center;" if side else "text-align: center;"
    css = f"""  #bg {{ position: absolute; inset: 0; background: radial-gradient(ellipse 120% 80% at 50% 0%, #fbf7f2 0%, #f6ebe0 55%, #f1d9c6 100%); }}
  .lab {{ position: absolute; {side_lab} color: #1d1b19; }}
  .lab b {{ display: block; font-size: 56px; font-weight: 800; letter-spacing: -.02em; line-height: 1.05; white-space: nowrap; }}
  .lab em {{ display: block; font-style: normal; font-size: 32px; font-weight: 700; line-height: 1.2; white-space: nowrap; }}
  .lab small {{ display: block; margin-top: 8px; font: 500 22px 'IBM Plex Mono', monospace; letter-spacing: .06em; color: #1d1b19c0; }}
  .k {{ color: {acc}; }}
  .card {{ position: absolute; border-radius: 26px; overflow: hidden; background: #111; box-shadow: 0 30px 70px rgba(80,40,10,.22), 0 6px 16px rgba(0,0,0,.12); }}
  .card video {{ position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; object-position: {c["visual"].get("focusX", 50)}% 50%; }}
  .card.mont video {{ object-position: 50% 50%; }}
  .rec {{ position: absolute; left: 18px; top: 18px; z-index: 5; display: flex; align-items: center; gap: 10px; padding: 8px 14px; border-radius: 10px;
         background: rgba(0,0,0,.55); color: #fff; font: 500 22px 'IBM Plex Mono', monospace; letter-spacing: .04em; }}
  .rec i {{ width: 12px; height: 12px; border-radius: 50%; background: #ff3b30; box-shadow: 0 0 10px #ff3b30; }}
  .pbar {{ position: absolute; left: 0; right: 0; bottom: 0; height: 8px; background: rgba(255,255,255,.25); z-index: 5; }}
  .pbar i {{ display: block; height: 100%; width: 0; background: {acc}; }}
  .cut {{ position: absolute; right: 18px; bottom: 30px; z-index: 6; }}
  .cut span {{ display: inline-block; padding: 8px 14px; border-radius: 10px; background: #ff3b30; color: #fff; font: 700 24px 'IBM Plex Mono', monospace; opacity: 0; }}
  .foot {{ position: absolute; left: 60px; right: 60px; text-align: center; color: #1d1b19; }}
  .foot b {{ display: block; font-size: 58px; font-weight: 800; letter-spacing: -.02em; line-height: 1.1; }}
  .foot small {{ display: block; margin-top: 10px; font-size: 30px; font-weight: 600; color: #1d1b19c8; }}"""
    doc = page("vitrine", css, body, "\n".join(js), mdur, pn.fonts(d))
    (d / "index.html").write_text(doc, encoding="utf-8")
    res = {"projet": str(d), "brut": str(src), "montage": str(mv), "coupes": n_cuts, "duree": round(mdur, 2), "disposition": "côte à côte" if side else "empilé"}
    if a.render:
        res["rendu"] = str(render(d, job / "renders" / f"{a.slug}_vitrine.mp4", a.render))
    out(ok=True, **res, suite="check + snapshot dans le projet, puis --render draft (aperçu) / delivery")


def auto_effects(job, slug):
    w, e = job / "work", []
    c = config(job)
    if (w / f"{slug}_map.json").exists():
        e.append("Blancs et « euh » coupés")
    if (w / f"{slug}_mots.json").exists():
        e += ["Mot géant + carte de verre", "Transition fouettée aux coupes"]
    elif (w / f"{slug}_text.json").exists():
        e.append("Sous-titres mot à mot")
    if (w / f"{slug}_panels.json").exists() or c["visual"].get("layout") in ("split", "cards"):
        e.append("Maquettes calées sur la parole")
    if c["camera"].get("zooms"):
        e.append("Zooms sur les mots forts")
    if (w / f"{slug}_broll.json").exists():
        e.append("Plans de coupe")
    if (w / f"{slug}_outils.json").exists():
        e.append("Cartes des outils cités")
    if (c.get("hook") or {}).get("style"):
        e.append("Accroche animée")
    if (w / f"{slug}_music.json").exists():
        e.append("Musique + bruitages")
    return e[:6] or ["Montage par le texte", "Sous-titres mot à mot", "Musique + bruitages"]


def demo(a, job):
    c = config(job)
    acc = a.accent or "#d97757"
    mv = montage_of(job, a.slug, a.montage)
    mw, mh, mdur = vinfo(mv)
    d = project(job, "demo")
    shutil.copy2(mv, d / "assets" / "montage.mp4")
    try:
        src, _, _ = raw_of(job, a.slug, a.brut)
        rdur = probe(src)["duration"]
    except SystemExit:
        src, rdur = mv, mdur
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(round(rdur * 0.3, 2)), "-i", str(src), "-frames:v", "1", "-vf", "scale=-2:320",
                    str(d / "assets" / "thumb.jpg")], check=True)
    effets = [x.strip() for x in a.effets.split(";") if x.strip()] if a.effets else auto_effects(job, a.slug)
    L = 1.2  # le résultat arrive après la demande
    total = round(L + mdur, 3)
    pseudo, _, phrase = (a.objection or "").partition(":") if a.objection else ("", "", "")
    side = mw < mh
    vw = 500 if side else 880
    vh = round(vw * mh / mw)
    logo = pn.icon(a.logo) if a.logo else ""
    chips = "".join(f'<div class="fx f{j}"><i>✓</i><span>{esc(x)}</span></div>' for j, x in enumerate(effets))
    body = f"""    <div id="bg"><div class="stripes"></div><div class="glow"></div></div>
    {f'''<div class="obj"><span class="oav"></span><span class="otx"><small>{esc(pseudo.strip())}</small><b>{esc(phrase.strip())}</b></span></div>''' if phrase else ""}
    <div class="app">
      <div class="ah"><span class="alogo">{logo}</span><b>{esc(a.app)}</b><span class="at">{esc(a.titre)}</span></div>
      <div class="umsg"><img src="assets/thumb.jpg" alt=""><div class="ut"><b>{esc(re.sub(r"[-_ .]+$", "", Path(str(src)).stem[:16]) if src != mv else "rush")}.mp4</b>
        <small>{mmss(rdur)}</small><span class="skill">✱ {esc(a.skill)}</span><p>{esc(a.demande)}</p></div></div>
      <div class="ans"><span class="star">✱</span> {esc(a.reponse)} <i>✓</i></div>
      <div class="res {'side' if side else 'stack'}">
        <div class="rv" style="width:{vw}px;height:{vh}px"><video id="mv" class="clip" src="assets/montage.mp4" data-start="{L}" data-duration="{round(mdur, 3)}"
          data-track-index="1" playsinline data-has-audio="true" data-volume="1"></video></div>
        <div class="rc"><b>reel.mp4</b><small>{mw}×{mh} · {mmss(mdur)}</small>{chips}
          <div class="dl"><span class="d1">↓ Télécharger</span><span class="d2">✓ Enregistré</span><div class="cur">{pn.icon("mouse-pointer-2")}</div></div></div>
      </div>
    </div>"""
    js = [
        '  tl.fromTo(".stripes", { x: 0 }, { x: -120, duration: %s, ease: "none", immediateRender: false }, 0);' % total,
        '  tl.fromTo(".obj", { opacity: 0, y: -30, scale: 0.9 }, { opacity: 1, y: 0, scale: 1, duration: 0.4, ease: "back.out(2)", immediateRender: false }, 0.05);',
        '  tl.fromTo(".app", { opacity: 0, y: 40 }, { opacity: 1, y: 0, duration: 0.45, ease: "power3.out", immediateRender: false }, 0.1);',
        '  tl.fromTo(".umsg", { opacity: 0, y: 24, scale: 0.96 }, { opacity: 1, y: 0, scale: 1, duration: 0.35, ease: "power3.out", immediateRender: false }, 0.3);',
        '  tl.fromTo(".ans", { opacity: 0, x: -16 }, { opacity: 1, x: 0, duration: 0.3, ease: "power2.out", immediateRender: false }, 0.85);',
        f'  tl.fromTo(".res", {{ opacity: 0, y: 30 }}, {{ opacity: 1, y: 0, duration: 0.4, ease: "power3.out", immediateRender: false }}, {L - 0.1});',
    ]
    span = max(0.35, (mdur * 0.7) / max(1, len(effets)))
    for j in range(len(effets)):
        tj = round(L + 0.4 + j * span, 3)
        js.append(f'  tl.fromTo(".f{j}", {{ opacity: 0.35 }}, {{ opacity: 1, duration: 0.2, immediateRender: false }}, {tj});')
        js.append(f'  tl.fromTo(".f{j} i", {{ scale: 0, opacity: 0 }}, {{ scale: 1, opacity: 1, duration: 0.25, ease: "back.out(3)", immediateRender: false }}, {tj});')
    tc = round(total - 1.3, 3)
    js += [f'  tl.fromTo(".cur", {{ opacity: 0, x: 160, y: 190 }}, {{ opacity: 1, x: 0, y: 0, duration: 0.5, ease: "power2.out", immediateRender: false }}, {round(tc - 0.6, 3)});',
           f'  tl.fromTo(".cur", {{ scale: 1 }}, {{ scale: 0.82, duration: 0.09, yoyo: true, repeat: 1, immediateRender: false }}, {tc});',
           f'  tl.fromTo(".dl", {{ scale: 1 }}, {{ scale: 0.94, duration: 0.09, yoyo: true, repeat: 1, immediateRender: false }}, {tc});',
           f'  tl.fromTo(".dl .d2", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.15, immediateRender: false }}, {round(tc + 0.15, 3)});',
           f'  tl.to(".dl .d1", {{ opacity: 0, duration: 0.1 }}, {round(tc + 0.15, 3)});']
    css = f"""  #bg {{ position: absolute; inset: 0; background: #07080f; overflow: hidden; }}
  .stripes {{ position: absolute; top: 0; bottom: 0; left: -200px; right: -200px;
             background: repeating-linear-gradient(90deg, rgba(90,110,255,.0) 0px, rgba(90,110,255,.16) 18px, rgba(20,22,40,.0) 40px, rgba(150,90,255,.12) 62px, rgba(0,0,0,0) 80px); }}
  .glow {{ position: absolute; inset: 0; background: radial-gradient(ellipse 60% 40% at 20% 30%, rgba(80,110,255,.35), transparent 70%),
          radial-gradient(ellipse 60% 45% at 85% 80%, rgba(150,80,255,.35), transparent 70%), linear-gradient(180deg, rgba(0,0,0,.2), rgba(0,0,0,.55)); }}
  .obj {{ position: absolute; left: 50%; top: 150px; transform: translateX(-50%); display: flex; align-items: center; gap: 18px; padding: 16px 30px 16px 16px;
         border-radius: 999px; background: #fff; box-shadow: 0 16px 40px rgba(0,0,0,.4); white-space: nowrap; opacity: 0; }}
  .oav {{ width: 64px; height: 64px; border-radius: 50%; background: linear-gradient(135deg, #c9c9d1, #8d8d99); flex: none; }}
  .otx small {{ display: block; font-size: 22px; color: #6b6b75; }}
  .otx b {{ display: block; font-size: 34px; font-weight: 800; color: #111; }}
  .app {{ position: absolute; left: 50px; right: 50px; top: 300px; padding-bottom: 30px !important; border-radius: 30px; background: #1f1e1d; border: 1px solid rgba(255,255,255,.08);
         box-shadow: 0 40px 100px rgba(0,0,0,.6); color: #f2f0eb; padding: 0 30px; opacity: 0; }}
  .ah {{ display: flex; align-items: center; gap: 14px; height: 90px; border-bottom: 1px solid rgba(255,255,255,.07); font-size: 34px; }}
  .alogo {{ width: 38px; height: 38px; color: {acc}; }}
  .ah b {{ font-family: 'Instrument Serif', Georgia, serif; font-weight: 400; font-size: 40px; }}
  .at {{ font-size: 24px; color: #a8a49c; }}
  .umsg {{ margin: 28px 0 0 auto; width: 74%; display: flex; gap: 22px; padding: 20px; border-radius: 22px; background: #2b2a28; opacity: 0; }}
  .umsg img {{ width: 150px; height: 220px; object-fit: cover; border-radius: 14px; flex: none; }}
  .ut b {{ display: block; font-size: 28px; }}
  .ut small {{ display: block; font: 500 20px 'IBM Plex Mono', monospace; color: #a8a49c; margin-top: 2px; }}
  .skill {{ display: inline-block; margin-top: 14px; padding: 6px 14px; border-radius: 10px; border: 1px solid {acc}88; color: {acc}; font-size: 22px; font-weight: 700; }}
  .ut p {{ margin: 14px 0 0; font-size: 30px; line-height: 1.25; }}
  .ans {{ margin: 26px 0 18px; font-size: 30px; display: flex; align-items: center; gap: 12px; opacity: 0; }}
  .ans .star {{ color: {acc}; font-size: 34px; }}
  .ans i {{ font-style: normal; color: #7bd88f; }}
  .res {{ display: flex; gap: 24px; padding: 20px; border-radius: 22px; background: #262523; border: 1px solid rgba(255,255,255,.06); opacity: 0; }}
  .res.stack {{ flex-direction: column; }}
  .rv {{ position: relative; border-radius: 16px; overflow: hidden; background: #000; flex: none; }}
  .rv video {{ position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }}
  .rc {{ flex: 1; display: flex; flex-direction: column; gap: 12px; min-width: 0; position: relative; }}
  .rc > b {{ font-size: 30px; }}
  .rc > small {{ font: 500 20px 'IBM Plex Mono', monospace; color: #a8a49c; margin-bottom: 8px; }}
  .fx {{ display: flex; align-items: center; gap: 12px; padding: 12px 16px; border-radius: 12px; background: #34302c; border: 1px solid rgba(255,255,255,.06);
        font-size: 23px; font-weight: 600; opacity: .35; }}
  .fx i {{ font-style: normal; width: 30px; height: 30px; border-radius: 8px; background: {acc}; color: #fff; display: flex; align-items: center; justify-content: center;
          font-size: 18px; flex: none; opacity: 0; background: {pn._mix(acc, "#000000", 0.25)}; }}
  .dl {{ margin-top: auto; position: relative; align-self: flex-end; height: 64px; width: 250px; border-radius: 14px; background: #f2f0eb; color: #1f1e1d;
        font-size: 26px; font-weight: 800; }}
  .dl span {{ position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; }}
  .dl .d2 {{ opacity: 0; background: #7bd88f; border-radius: 14px; }}
  .cur {{ position: absolute; left: 58%; top: 45%; width: 56px; height: 56px; color: #fff; z-index: 50; opacity: 0; filter: drop-shadow(0 4px 8px rgba(0,0,0,.6)); }}
  .cur svg {{ fill: #111; stroke-width: 1.6; }}"""
    doc = page("demo", css, body, "\n".join(js), total, pn.fonts(d))
    (d / "index.html").write_text(doc, encoding="utf-8")
    res = {"projet": str(d), "montage": str(mv), "effets": effets, "duree": total}
    if a.render:
        res["rendu"] = str(render(d, job / "renders" / f"{a.slug}_demo.mp4", a.render))
    out(ok=True, **res, suite="check + snapshot dans le projet (curseur sur le bouton ?), puis --render draft / delivery")


def portfolio(a, job):
    vids = []
    for x in [v.strip() for v in (a.videos or "").split(",") if v.strip()]:
        p_ = Path(x) if Path(x).is_absolute() else job / x
        vids.append(p_ if p_.exists() else fail(f"{x} introuvable"))
    for n in [v.strip() for v in (a.lib or "").split(",") if v.strip()]:
        f = sorted((ROOT / "library").glob(f"*/{n}/preview.mp4"))
        vids.append(f[0] if f else fail(f"aperçu introuvable dans la bibliothèque : {n}"))
    if not vids:
        fail("--videos ou --lib")
    d = project(job, "portfolio")
    srcs = []
    for k, v in enumerate(vids):
        dst = d / "assets" / f"v{k}.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(v), "-vf", "scale=540:-2", "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                        "-g", "15", str(dst)], check=True)
        srcs.append((dst.name, vinfo(dst)[2]))
    T, R_ = float(a.duree), float(a.rythme)
    tiles = [(40, 330, 470, 836), (570, 290, 470, 836), (305, 990, 470, 836)]
    body, n = [], len(srcs)
    for i, (x, y, w, h) in enumerate(tiles):
        segs, t, k = [], -i * R_ / 3, 0
        while t < T:
            name, ln = srcs[(i + 3 * k) % n]
            a0, a1 = max(0.0, t), min(T, t + R_)
            if a1 - a0 > 0.05:
                ms = (a0 - t) % max(0.1, ln - 0.05) if ln > 0.2 else 0
                segs.append(f'        <video id="p{i}_{k}" class="clip" src="assets/{name}" data-start="{round(a0, 3)}" data-duration="{round(a1 - a0, 3)}" '
                            f'data-media-start="{round(ms, 3)}" data-track-index="{1 + i * 2 + k % 2}" muted playsinline></video>')
            t += R_
            k += 1
        body.append(f'    <div class="tile t{i}" style="left:{x}px;top:{y}px;width:{w}px;height:{h}px">\n' + "\n".join(segs) + '\n    </div>')
    m = re.match(r"\*([^*]+)\*\s*(.*)", a.entete or "")
    title = (f'<div class="ti"><em>{esc(m.group(1))}</em><b>{esc(m.group(2))}</b></div>' if m else f'<div class="ti"><b>{esc(a.entete)}</b></div>') if a.entete else ""
    mus = Path(a.musique) if a.musique else None
    if mus and not mus.is_absolute():
        mus = job / mus
    audio = ""
    if not mus and (job / "work" / f"{a.slug}_music.json").exists():
        mus = job / read_json(job / "work" / f"{a.slug}_music.json")["file"]
    if mus and mus.exists():
        shutil.copy2(mus, d / "assets" / ("music" + mus.suffix))
        audio = f'    <audio id="mu" class="clip" src="assets/music{mus.suffix}" data-start="0" data-duration="{T}" data-track-index="20" data-volume="1"></audio>'
    js = ['  tl.fromTo(".ti > *", { opacity: 0, y: 20 }, { opacity: 1, y: 0, duration: 0.5, stagger: 0.1, ease: "power3.out", immediateRender: false }, 0.05);',
          '  tl.fromTo(".tile", { opacity: 0, y: 40, scale: 0.96 }, { opacity: 1, y: 0, scale: 1, duration: 0.5, stagger: 0.1, ease: "power3.out", immediateRender: false }, 0.1);']
    css = f"""  #bg {{ position: absolute; inset: 0; background: radial-gradient(ellipse 90% 60% at 50% 40%, #2a1612 0%, #1a0c09 70%, #120806 100%); }}
  .ti {{ position: absolute; left: 70px; top: 110px; color: #f3e6d3; line-height: 1; }}
  .ti em {{ display: block; font-family: 'Bodoni Moda', Georgia, serif; font-style: italic; font-weight: 400; font-size: 52px; margin-left: 4px; }}
  .ti b {{ display: block; font-size: 76px; font-weight: 800; letter-spacing: -.02em; }}
  .tile {{ position: absolute; border-radius: 34px; overflow: hidden; background: #000; box-shadow: 0 30px 70px rgba(0,0,0,.55); }}
  .tile video {{ position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }}
  .tile.t2 {{ z-index: 3; }}"""
    fonts = pn.fonts(d) + " " + collage_fonts(d)
    html_ = "\n".join(['    <div id="bg"></div>'] + ([f"    {title}"] if title else []) + body + ([audio] if audio else []))
    doc = page("portfolio", css, html_, "\n".join(js), T, fonts)
    (d / "index.html").write_text(doc, encoding="utf-8")
    res = {"projet": str(d), "videos": [str(v) for v in vids], "duree": T, "musique": bool(audio)}
    if a.render:
        res["rendu"] = str(render(d, job / "renders" / f"{a.slug}_portfolio.mp4", a.render))
    out(ok=True, **res, suite="check + snapshot dans le projet, puis --render draft / delivery")


def collage_fonts(d):
    """Bodoni Moda (OFL) : la serif Didone des titres éditoriaux (portfolio, collage)."""
    v = Path(__file__).resolve().parent.parent / "vendor" / "fonts"
    (d / "assets" / "fonts").mkdir(parents=True, exist_ok=True)
    css = []
    for f, w, st in (("BodoniModa-700-normal.woff2", 700, "normal"), ("BodoniModa-700-italic.woff2", 700, "italic"), ("BodoniModa-400-italic.woff2", 400, "italic")):
        shutil.copy2(v / f, d / "assets" / "fonts" / f)
        css.append(f"@font-face {{ font-family: 'Bodoni Moda'; src: url('assets/fonts/{f}') format('woff2'); font-weight: {w}; font-style: {st}; }}")
    return " ".join(css)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["vitrine", "demo", "portfolio"])
    ap.add_argument("job")
    ap.add_argument("slug")
    ap.add_argument("--montage", help="rendu du montage (défaut : le dernier rendu du slug)")
    ap.add_argument("--brut", help="rush brut si le job n'a pas de dérush (plan + map)")
    ap.add_argument("--accent")
    ap.add_argument("--render", choices=["draft", "delivery"])
    ap.add_argument("--par", default="Claude")
    ap.add_argument("--cta", default="Clique sur le *lien en bas*")
    ap.add_argument("--sous", default="pour en savoir plus")
    ap.add_argument("--app", default="Claude")
    ap.add_argument("--logo", default="logo:claude")
    ap.add_argument("--titre", default="Monte mon reel")
    ap.add_argument("--objection", help='« pseudo: phrase » épinglée en haut (ex. "un_monteur: Claude sait pas monter.")')
    ap.add_argument("--demande", default="Monte mon rush avec mon skill.")
    ap.add_argument("--reponse", default="Voilà ton reel")
    ap.add_argument("--skill", default="videomaker-deeplo")
    ap.add_argument("--effets", help="« a;b;c » (défaut : lus dans le job)")
    ap.add_argument("--videos", help="portfolio : vidéos séparées par des virgules")
    ap.add_argument("--lib", help="portfolio : noms de la bibliothèque (aperçus)")
    ap.add_argument("--entete", default="", help='portfolio : titre fixe "*Premium* Motion Graphics"')
    ap.add_argument("--duree", type=float, default=10.0)
    ap.add_argument("--rythme", type=float, default=2.6)
    ap.add_argument("--musique")
    a = ap.parse_args()
    job = job_dir(a.job)
    {"vitrine": vitrine, "demo": demo, "portfolio": portfolio}[a.mode](a, job)


if __name__ == "__main__":
    main()

"""EXPLAINER PAPIER (pack « explainer ») -> <job>/index.html : vidéo sans rush entièrement animée, façon fiche pratique.

  python build_explainer.py <job> <slug> [--size 9:16] [--no-outro]

Carte papier sur fond à carreaux (couleurs de la charte), bandeau d'étapes fixe en haut de la carte (une puce par
chapitre, celle en cours s'allume) et barre de progression du récit, temps forts du panneau (panel.py, thème papier)
posés sur les mots de la voix off, sous-titres karaoké dans un cadre (mot dit en encre, mot fort dans une boîte
d'accent), voix + musique, fin de marque facultative.

Avant : storyboard avec un champ "voice" par phrase -> voice.py (Gemini, Fish ou enregistrement) -> build_text.py ->
add_music.py ; puis work/<slug>_panels.json : temps forts avec "chapter" (2 à 5 chapitres courts : « AVANT »,
« LE SOIN », « APRÈS », « RÉSERVER ») ; sans fichier, un titre par phrase forte.
"""
import argparse
import html
import json
import shutil
from pathlib import Path

import panel as pn
from build_composition import caption_spans
import sound_design
from common import ROOT, block_file, brand_info, config, fail, job_dir, mount, out, read_json, scale_of, size_of

esc = lambda s: html.escape(str(s), quote=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("job")
    ap.add_argument("slug")
    ap.add_argument("--size")
    ap.add_argument("--no-outro", action="store_true")
    ap.add_argument("--lang", help="sous-titres traduits (translate.py apply) : nl, en…")
    ap.add_argument("--no-captions", action="store_true", help="sans sous-titres (couverture)")
    a = ap.parse_args()
    job = job_dir(a.job)
    c = config(job)
    vis = c["visual"]
    W, H = size_of(a.size, vis)
    u = scale_of(W, H)
    wide = W / H > 1.2  # paysage : fiche à gauche, sous-titres en colonne à droite
    mj, tj = job / "work" / f"{a.slug}_map.json", job / "work" / f"{a.slug}_text.json"
    for p in (mj, tj):
        if not p.exists():
            fail(f"{p} absent (voice.py puis build_text.py)")
    m, t = read_json(mj), read_json(tj)
    dur = float(m["out_duration"])
    voice = Path(m["cut"]).name
    fam = vis["fontFamily"]
    bg, ink, acc, paper = pn.paper_colors(vis)

    # polices : charte + serif italique et mono du pack
    from fonts import brand_faces
    faces = [brand_faces(job, vis), pn.fonts(job)]

    # géométrie : carte, bandeau d'étapes, scène des temps forts, cadre des sous-titres
    mx, top, bottom = round(W * 0.055), round(H * 0.045), round(H * 0.80)
    sw, chrome_h = W - 2 * mx, round(170 * u)
    if wide:
        mx, top, bottom = round(H * 0.06), round(H * 0.06), round(H * 0.94)
        sw, chrome_h = round(W * 0.6), round(120 * u)
    capx = mx + sw + round(60 * u)  # colonne des sous-titres en paysage
    stage_h = bottom - top - chrome_h
    pj = job / "work" / f"{a.slug}_panels.json"
    beats = read_json(pj) if pj.exists() else pn.default_beats(t)
    words = [w for g in t.get("captions", []) for w in g["words"]]
    panel_html, pjs, prep, layers = pn.nodes(job, beats, words, dur, 0.0, sw, stage_h, vis, theme="paper",
                                             origin=(mx + max(2, round(4 * u)), top + max(2, round(4 * u)) + chrome_h))

    # bandeau d'étapes : une puce par chapitre (ordre d'apparition), la courante s'allume
    chapters = []
    for b in beats:
        ch = (b.get("chapter") or "").strip()
        if ch and ch not in chapters:
            chapters.append(ch)
    chips = "".join(f'<span class="chip" data-ch="{esc(ch)}">{k + 1} · {esc(ch)}</span>' for k, ch in enumerate(chapters[:5]))
    chrome = (f'<div class="chrome"><div class="chips">{chips}</div><div class="prog"><span>PROGRESSION</span><i><b></b></i></div></div>'
              if chapters else "")
    cjs = [f'  tl.fromTo(".prog b", {{ scaleX: 0 }}, {{ scaleX: 1, duration: {dur}, ease: "none", immediateRender: false }}, 0);']
    for r in prep:  # la puce du chapitre s'allume quand son premier temps fort arrive
        b = next((x for x in beats if x.get("word") == r.get("mot") and x.get("type") == r.get("type")), None)
        if b and b.get("chapter") and r.get("a") is not None:
            cjs.append(f'  tl.call(function () {{ document.querySelectorAll(".chip").forEach(function (e) {{ '
                       f'e.classList.toggle("on", e.dataset.ch === {json.dumps(b["chapter"], ensure_ascii=False)}); }}); }}, null, {r["a"]});')

    # sous-titres karaoké dans un cadre
    caps, capjs, last_emo = [], [], -99.0
    tl_ = t
    if a.lang and (job / "work" / f"{a.slug}_text_{a.lang}.json").exists():
        tl_ = read_json(job / "work" / f"{a.slug}_text_{a.lang}.json")
    groups = [] if a.no_captions else tl_.get("captions", [])
    for i, g in enumerate(groups):
        st = round(max(0.05, g["words"][0]["start"] - 0.05), 3)
        nxt = groups[i + 1]["words"][0]["start"] - 0.05 if i + 1 < len(groups) else dur
        en = round(min(dur, max(g["end"] + 0.25, st + 0.4), nxt), 3)
        if en - st <= 0.1:
            continue
        spans, _, last_emo = caption_spans(g["words"], "seam", False, st, last_emo)
        caps.append(f'      <div class="clip cap" id="cap-{g["id"]}" data-start="{st}" data-duration="{round(en - st, 3)}" '
                    f'data-track-index="6"><div class="in">{spans}</div></div>')
        times = [round(max(st, w["start"]), 3) for w in g["words"]]
        capjs.append(f'  kar("cap-{g["id"]}", {st}, {en}, {json.dumps(times)});')

    audio = [f'    <audio id="voice" class="clip" src="assets/{esc(voice)}" data-start="0" data-duration="{dur}" data-track-index="8" data-volume="1"></audio>']
    mu = job / "work" / f"{a.slug}_music.json"
    if mu.exists():
        audio.append(f'    <audio id="music" class="clip" src="{read_json(mu)["file"]}" data-start="0" data-duration="{dur}" '
                     f'data-track-index="9" data-volume="1"></audio>')

    total, outro = dur, ""
    br = c.get("branding", {})
    if br.get("outro") and not a.no_outro:
        block_file(job, br["outro"])
        od = float(br.get("outroDuration", 3.4))
        brand = brand_info(job)
        logo = ""
        if vis.get("logo"):
            lp = ROOT / vis["logo"]
            (job / "assets" / "img").mkdir(parents=True, exist_ok=True)
            shutil.copy2(lp, job / "assets" / "img" / lp.name)
            logo = f"assets/img/{lp.name}"
        outro = mount(br["outro"], "brand-outro", dur, od, W, H, 22,
                      {"logo": logo, "bg": vis.get("bgColor", "#f6f4f0"), "ink": vis.get("inkColor", "#1a1a1a"), "accent": vis["accentColor"],
                       "font": fam, "blend": vis.get("logoBlend", "normal"), "tagline": brand.get("tagline", ""),
                       "info": (brand.get("contact") or {}).get("site", "")}, z=200)
        total = round(dur + od, 3)

    shadow = f"{round(10*u)}px {round(10*u)}px 0 {ink}"
    wide_css = (f"  .cap {{ left: {capx}px; right: {mx}px; top: 0; bottom: 0; display: flex; align-items: center; justify-content: flex-start; text-align: left; }}" + chr(10) +
                f"  .cap .in {{ white-space: normal; max-width: 100%; font-size: {round(76*u)}px; line-height: 1.12; }}" + chr(10) +
                f"  .chips {{ flex-wrap: nowrap; }} .chip {{ font-size: {round(24*u)}px; white-space: nowrap; }} .prog {{ font-size: {round(20*u)}px; }}") if wide else ""
    doc = f"""<!doctype html>
<html lang="fr">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width={W}, height={H}" />
<title>{esc(a.slug)}</title>
<script src="https://cdn.jsdelivr.net/npm/gsap@3.15.0/dist/gsap.min.js"></script>
<style>
  {' '.join(faces)}
  html, body {{ margin: 0; padding: 0; width: {W}px; height: {H}px; overflow: hidden; background: {bg}; }}
  #root {{ position: relative; width: {W}px; height: {H}px; overflow: hidden; font-family: '{fam}', 'Inter', sans-serif; color: {ink}; }}
  .bgpat {{ position: absolute; inset: -{round(60*u)}px; background-color: {bg};
           background-image: linear-gradient(90deg, {acc}1f 50%, transparent 50%), linear-gradient({acc}1f 50%, transparent 50%);
           background-size: {round(56*u)}px {round(56*u)}px; }}
  .sheet {{ position: absolute; left: {mx}px; top: {top}px; width: {sw}px; height: {bottom - top}px; background: {paper};
           border: {max(2, round(4*u))}px solid {ink}; border-radius: {round(12*u)}px; box-shadow: {shadow}; overflow: hidden; }}
  .chrome {{ position: absolute; left: {round(36*u)}px; right: {round(36*u)}px; top: {round(30*u)}px; }}
  .chips {{ display: flex; flex-wrap: wrap; gap: {round(12*u)}px; }}
  .chip {{ font: 500 {round(22*u)}px 'IBM Plex Mono', monospace; text-transform: uppercase; letter-spacing: .06em; padding: .35em .7em;
          border: 2px solid {ink}; border-radius: {round(8*u)}px; background: #fff; }}
  .chip.on {{ background: {acc}; color: #fff; }}
  .prog {{ display: flex; align-items: center; gap: {round(14*u)}px; margin-top: {round(18*u)}px; font: 500 {round(18*u)}px 'IBM Plex Mono', monospace;
          letter-spacing: .1em; }}
  .prog i {{ flex: 1; height: {round(14*u)}px; border: 2px solid {ink}; border-radius: 99px; overflow: hidden; background: #fff; }}
  .prog b {{ display: block; height: 100%; background: {acc}; transform-origin: 0 50%; transform: scaleX(0); }}
  .stage {{ position: absolute; left: 0; top: {chrome_h}px; width: {sw}px; height: {stage_h}px; }}
  .cap {{ position: absolute; left: 0; right: 0; top: {round(H * 0.855)}px; text-align: center; z-index: 50; }}
  .cap .in {{ display: inline-block; max-width: 86%; padding: .22em .55em; background: #fff; border: {max(2, round(4*u))}px solid {ink};
             box-shadow: {round(7*u)}px {round(7*u)}px 0 {ink}; font-weight: 800; font-size: {round(54*u)}px; line-height: 1.15;
             text-transform: uppercase; letter-spacing: -.01em; white-space: nowrap; opacity: 0; }}
  .cap .w {{ display: inline-block; margin: 0 .08em; color: {ink}55; position: relative; z-index: 0; }}
  .cap .w.k {{ color: #fff; background: {acc}; padding: 0 .18em; border-radius: .1em; }}
{wide_css}
{pn.css_paper(sw, stage_h, fam, vis)}
</style>
</head>
<body>
  <div id="root" data-composition-id="explainer" data-start="0" data-width="{W}" data-height="{H}" data-duration="{total}">
    <div class="bgpat"></div>
    <div class="sheet">{chrome}<div class="stage">
{panel_html}
    </div></div>
{chr(10).join(layers)}
{chr(10).join(caps)}
{chr(10).join(audio)}
{outro}
  </div>
<script>
  window.__timelines = window.__timelines || {{}};
  const tl = gsap.timeline({{ paused: true }});
  const INK = {json.dumps(ink)};
  function kar(id, st, en, ts) {{
    const g = "#" + id, ws = document.querySelectorAll(g + " .w");
    tl.fromTo(g + " .in", {{ opacity: 0, y: 14, rotation: -1.5 }}, {{ opacity: 1, y: 0, rotation: 0, duration: 0.2, ease: "back.out(2)", immediateRender: false }}, st);
    ts.forEach(function (t, i) {{ if (!ws[i].classList.contains("k")) tl.to(ws[i], {{ color: INK, duration: 0.08 }}, t); }});
    tl.to(g + " .in", {{ opacity: 0, duration: 0.1 }}, en - 0.1);
    tl.set(g + " .in", {{ opacity: 0 }}, en);
  }}
{chr(10).join(capjs)}
{chr(10).join(pjs)}
{chr(10).join(cjs)}
  tl.fromTo(".sheet", {{ y: 40, opacity: 0 }}, {{ y: 0, opacity: 1, duration: 0.5, ease: "power3.out", immediateRender: false }}, 0);
  tl.fromTo(".bgpat", {{ x: 0, y: 0 }}, {{ x: -{round(56*u)}, y: -{round(56*u)}, duration: {total}, ease: "none", immediateRender: false }}, 0);
  window.__timelines["explainer"] = tl;
</script>
</body>
</html>
"""
    (job / "index.html").write_text(doc, encoding="utf-8")
    from build_composition import cli_args
    from common import write_json as _wj
    _wj(job / "work" / f"{a.slug}_build.json", {"script": "build_explainer.py", "args": cli_args(ap, a)})  # deliver.py rejoue ces options
    if not getattr(a, "no_sfx", False):  # bruitages sur ce qui apparaît (sound_design.py ; "sfx": {"design": false} pour s'en passer)
        sound_design.auto(job)
    out(ok=True, format=f"{W}x{H}", duree=total, chapitres=chapters, temps_forts=prep, sous_titres=len(caps),
        suite="npx hyperframes check, puis snapshot")


if __name__ == "__main__":
    main()

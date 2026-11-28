"""CATALOGUE « N trucs que X sait faire » ET EFFETS SUR LE RUSH (face caméra, plein écran recadré). Appelé par
build_composition.py dès que l'un des deux fichiers existe ; rien à lancer à part.

Catalogue : work/<slug>_catalogue.json
  {"titre": "17 effets que Claude sait faire",
   "items": [{"nom": "orbit", "mot": "orbit", "occurrence": 1, "demo": "library:scan-visage", "depuis": 0.5}, …],
   "fin": "<mot dit où l'habillage part en flou>", "decaler": true}
  Titre en haut (le chiffre en accent), sommaire numéroté à droite (l'élément DIT passe en accent), téléphone qui joue
  la démo de l'élément avec son compteur « 04/17 », personne décalée à gauche pour faire la place ; au mot `fin`, tout
  l'habillage part en flou et le cadrage revient. Pas de sous-titres pendant le catalogue (l'écran est déjà plein).
  `demo` : `library:<nom>` (aperçu d'un motion de library/), une vidéo ou une image du job (`inbox/…`) ; absent = carte
  au nom de l'élément. `depuis` : seconde de la démo où commencer.

Effets : work/<slug>_effets.json, une liste de {"effet": …, "mot": "<mot dit>", "occurrence": 1, "dur": …}
  vertigo  : la personne garde sa taille, le décor recule (dolly zoom) ; 1,8 s
  cadre    : « frame break » : l'image se range dans un cadre de Reel, la personne en déborde ; 2,6 s
  contour  : « doodle boil » : contour dessiné qui tremble autour de la personne + petits dessins ; 2,6 s
  traverse : « zoom-through cut » : zoom à travers l'image sur la coupe du dérush la plus proche du mot
  Les trois premiers utilisent le détourage local (cutout.py, ~20 s par seconde d'effet, mis en cache).
"""
import base64
import html
import re
import shutil
import subprocess
from pathlib import Path

import numpy as np

from common import ROOT, word_hit

TR = 30  # pistes HyperFrames de ce module : 30 et plus (libres dans build_composition)
EFFETS = {"vertigo": 1.8, "cadre": 2.6, "contour": 2.6, "traverse": 0.5}


def esc(s):
    return html.escape(str(s), quote=True)


def _words_t(words, item):
    hit = word_hit(words, item.get("mot") or item.get("nom", ""), item.get("occurrence", 1))
    return None if hit is None else round(max(0.0, float(hit["start"]) - 0.08), 3)


def catalogue_window(cfg, words, dur):
    """(début, fin) du catalogue dans le contenu (avant l'intro), ou None si aucun élément n'est dit."""
    ts = [x for x in (_words_t(words, it) for it in cfg.get("items", [])) if x is not None]
    if not ts:
        return None
    t0 = 0.0 if ts[0] < 2.0 else round(ts[0] - 0.3, 3)
    fin = word_hit(words, cfg["fin"], cfg.get("fin_occurrence", 1)) if cfg.get("fin") else None
    if fin is not None and float(fin["start"]) > ts[-1]:
        t1 = float(fin["start"]) - 0.05
    else:
        gaps = [b - a for a, b in zip(ts, ts[1:])] or [1.2]
        t1 = ts[-1] + max(0.8, sorted(gaps)[len(gaps) // 2])
    return t0, round(min(dur - 0.1, t1), 3)


def _demo(job, it):
    """-> (type, chemin relatif au job) : video | image | None."""
    d = str(it.get("demo") or "").strip()
    if not d:
        return None, None
    if d.startswith("library:"):
        name = d.split(":", 1)[1]
        hits = sorted((ROOT / "library").glob(f"*/{name}/preview.mp4")) + sorted((ROOT / "library").glob(f"*/{name}/preview.*"))
        if not hits:
            return None, None
        p = hits[0]
    else:
        p = Path(d) if Path(d).is_absolute() else job / d
        if not p.exists():
            return None, None
    kind = "image" if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp") else "video"
    try:
        rel = p.relative_to(job).as_posix()
    except ValueError:
        dst = job / "assets" / "catalogue" / f"{p.parent.name}-{p.name}"
        dst.parent.mkdir(parents=True, exist_ok=True)
        if not dst.exists() or dst.stat().st_size != p.stat().st_size:
            shutil.copy2(p, dst)
        rel = dst.relative_to(job).as_posix()
    return kind, rel


def catalogue(job, cfg, words, dur, W, H, T0, accent, title_stack, family):
    """-> nodes, js, css, calques, rapport. Temps du timeline de contenu (tl), data-start décalés de T0."""
    win = catalogue_window(cfg, words, dur)
    if not win:
        return [], [], "", [], {"pose": False, "raison": "aucun élément du catalogue n'est dit"}
    c0, c1 = win
    items, missing = [], []
    for k, it in enumerate(cfg.get("items", [])):
        t = _words_t(words, it)
        if t is None:
            missing.append(it)
        else:
            items.append({**it, "_t": t, "_k": k})
    items.sort(key=lambda x: x["_t"])
    N = len(cfg.get("items", []))
    u = W / 1080
    # titre : 2 lignes équilibrées, le premier chiffre en accent
    words_ = str(cfg.get("titre", "")).split()
    half = (len(words_) + 1) // 2
    lines = [" ".join(words_[:half]), " ".join(words_[half:])] if len(words_) > 3 else [" ".join(words_)]
    tl_html = "".join(f'<span class="ct-l">{re.sub(r"^(\d+)", lambda mm: f"<em>{mm.group(1)}</em>", esc(x))}</span>' for x in lines if x)
    li = "".join(f'<li id="ci{k}"><b data-layout-ignore>{k + 1:02d}</b>{esc(it.get("nom", ""))}</li>' for k, it in enumerate(cfg.get("items", [])))
    phone_w = round(W * 0.31)
    phone_h = round(phone_w * 16 / 9)
    px, py = round(W * 0.965 - phone_w), round(H * 0.445)  # colonne de droite, sous le sommaire : à l'écart du visage décalé
    if py + phone_h > H * 0.9:
        py = round(H * 0.9 - phone_h)
    nodes = [f'    <div class="clip" id="cat" data-start="{round(T0 + c0, 3)}" data-duration="{round(c1 - c0 + 0.45, 3)}" data-track-index="{TR}">'
             f'<div class="ct-t">{tl_html}</div><ol class="ct-s">{li}</ol>'
             f'<div class="ct-p" style="left:{px}px;top:{py}px;width:{phone_w}px;height:{phone_h}px"></div></div>']
    js, rep = [], []
    for j, it in enumerate(items):
        k, a = it["_k"], it["_t"]
        b = items[j + 1]["_t"] if j + 1 < len(items) else c1 + 0.45  # le dernier reste pendant la sortie en flou
        d = round(max(0.3, b - a), 3)
        kind, rel = _demo(job, it)
        box = f'left:{px}px;top:{py}px;width:{phone_w}px;height:{phone_h}px'
        if kind == "video":  # aperçu de library/ : on saute l'entrée (1 s) pour montrer l'effet en place
            dep = it.get("depuis", 1.0 if str(it.get("demo", "")).startswith("library:") else 0)
            ms = f' data-media-start="{float(dep)}"' if dep else ""
            nodes.append(f'    <video class="clip ct-v" id="cv{j}" src="{esc(rel)}" data-start="{round(T0 + a, 3)}" data-duration="{d}"{ms} '
                         f'data-track-index="{TR + 1}" muted playsinline style="{box}"></video>')
        elif kind == "image":
            nodes.append(f'    <div class="clip ct-v" id="cv{j}" data-start="{round(T0 + a, 3)}" data-duration="{d}" data-track-index="{TR + 1}" style="{box}">'
                         f'<img src="{esc(rel)}" alt=""></div>')
            js.append(f'  tl.fromTo("#cv{j} img", {{ scale: 1.08 }}, {{ scale: 1, duration: {d}, ease: "none", immediateRender: false }}, {a});')
        else:
            nodes.append(f'    <div class="clip ct-v ct-x" id="cv{j}" data-start="{round(T0 + a, 3)}" data-duration="{d}" data-track-index="{TR + 1}" style="{box}">'
                         f'<span>{esc(it.get("nom", ""))}</span></div>')
        nodes.append(f'    <div class="clip ct-n" id="cn{j}" data-start="{round(T0 + a, 3)}" data-duration="{d}" data-track-index="{TR + 2}" '
                     f'style="left:{px + round(22 * u)}px;top:{py + round(22 * u)}px">{k + 1:02d}<i>/{N}</i></div>')
        js.append(f'  tl.fromTo("#cv{j}", {{ scale: 1.06, opacity: .4 }}, {{ scale: 1, opacity: 1, duration: 0.22, ease: "power2.out", immediateRender: false }}, {a});')
        js.append(f'  tl.set("#ci{k}", {{ color: "{accent}", fontWeight: 800 }}, {a});')
        if j + 1 < len(items):
            js.append(f'  tl.set("#ci{k}", {{ color: "rgba(255,255,255,.86)", fontWeight: 600 }}, {b});')
        rep.append({"nom": it.get("nom"), "a": a, "duree": d, "demo": rel or "carte au nom"})
    js.insert(0, f'  tl.fromTo("#cat .ct-t, #cat .ct-s, #cat .ct-p", {{ opacity: 0, y: 24 }}, {{ opacity: 1, y: 0, duration: 0.35, stagger: 0.06, '
                 f'ease: "power3.out", immediateRender: false }}, {c0});')
    if cfg.get("decaler", True):  # la personne glisse à gauche pour laisser la place au sommaire et au téléphone
        js.append(f'  tl.set("#fxv", {{ scale: 1.14, x: {-round(W * 0.065)} }}, {c0});')
        js.append(f'  tl.to("#fxv", {{ scale: 1, x: 0, duration: 0.4, ease: "power2.inOut" }}, {c1});')
    js.append(f'  tl.to("#cat, .ct-v, .ct-n", {{ filter: "blur(26px)", opacity: 0, scale: 1.03, duration: 0.35, ease: "power2.in" }}, {round(c1 - 0.05, 3)});')
    fs, ls = round(70 * u), round(30 * u)
    css = f"""
  #cat {{ position: absolute; inset: 0; z-index: 35; pointer-events: none; }}
  #cat .ct-t {{ position: absolute; left: 0; right: 0; top: {round(H * 0.058)}px; text-align: center; font-family: {title_stack};
               font-weight: 800; font-size: {fs}px; line-height: .98; letter-spacing: -.03em; color: #fff;
               text-shadow: 0 .04em .2em rgba(0,0,0,.45); }}
  #cat .ct-l {{ display: block; }}
  #cat .ct-t em {{ font-style: normal; color: {accent}; }}
  #cat .ct-s {{ position: absolute; right: {round(W * 0.035)}px; top: {round(H * 0.098)}px; margin: 0; padding: {round(14 * u)}px {round(18 * u)}px;
               list-style: none; border-radius: {round(14 * u)}px; background: linear-gradient(90deg, rgba(0,0,0,0), rgba(0,0,0,.32));
               font-family: '{family}', 'Inter', sans-serif; font-size: {ls}px; line-height: 1.22; font-weight: 600; color: rgba(255,255,255,.86);
               text-shadow: 0 1px 6px rgba(0,0,0,.6); }}
  #cat .ct-s b {{ display: inline-block; width: 1.6em; font-size: .62em; font-weight: 500; opacity: .7; font-family: 'IBM Plex Mono', monospace; }}
  #cat .ct-p {{ position: absolute; border-radius: {round(30 * u)}px; border: {max(3, round(5 * u))}px solid #fff; background: #111;
               box-shadow: 0 {round(18 * u)}px {round(50 * u)}px rgba(0,0,0,.5); box-sizing: border-box; }}
  .ct-v {{ position: absolute; z-index: 36; object-fit: cover; border-radius: {round(30 * u)}px; overflow: hidden; border: {max(3, round(5 * u))}px solid #fff;
          box-sizing: border-box; background: #111; }}
  .ct-v img {{ width: 100%; height: 100%; object-fit: cover; display: block; }}
  .ct-x {{ display: flex; align-items: center; justify-content: center; text-align: center; background: linear-gradient(160deg, {accent}, #111 85%); }}
  .ct-x span {{ font-family: {title_stack}; font-weight: 800; font-size: {round(54 * u)}px; color: #fff; padding: 0 .4em; line-height: 1; }}
  .ct-n {{ position: absolute; z-index: 37; padding: {round(5 * u)}px {round(12 * u)}px; border-radius: 99px; background: rgba(0,0,0,.6);
          font: 600 {round(22 * u)}px 'IBM Plex Mono', monospace; color: #fff; }}
  .ct-n i {{ font-style: normal; opacity: .6; }}"""
    nl = len(cfg.get("items", []))
    calques = [{"type": "texte", "nom": "catalogue : titre", "t0": c0, "t1": c1, "box": [round(W * 0.08), round(H * 0.058), round(W * 0.92), round(H * 0.058 + fs * 2.1)]},
               {"type": "bloc", "nom": "catalogue : sommaire", "t0": c0, "t1": c1,
                "box": [round(W * 0.62), round(H * 0.098), round(W * 0.965), round(H * 0.098 + ls * 1.22 * nl + 28 * u)], "estime": True},
               {"type": "bloc", "nom": "catalogue : téléphone", "t0": c0, "t1": c1, "box": [px, py, px + phone_w, py + phone_h]}]
    report = {"pose": True, "a": c0, "fin": c1, "elements": rep, "non_dits": [x.get("mot") or x.get("nom") for x in missing]}
    if cfg.get("decaler", True):
        report["decal"] = [c0, round(c1 + 0.2, 3), 1.14, -round(W * 0.065)]
    return nodes, js, css, calques, report


# ---------------------------------------------------------------- effets sur le rush (détourage)

def matte_box(job, rel):
    """Boîte du sujet dans le détourage (parts de la largeur / hauteur), médiane sur l'extrait : x0, y0, x1, y1."""
    from cutout import vsize
    w, h = vsize(job / rel)
    hh = 240
    ww = round(w * hh / h / 2) * 2
    p = subprocess.run(["ffmpeg", "-v", "error", "-c:v", "libvpx-vp9", "-i", str(job / rel), "-vf", f"fps=4,alphaextract,scale={ww}:{hh}",
                        "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True)
    n = len(p.stdout) // (ww * hh)
    boxes = []
    for k in range(n):
        a = np.frombuffer(p.stdout[k * ww * hh:(k + 1) * ww * hh], np.uint8).reshape(hh, ww) > 128
        ys, xs = np.where(a)
        if len(xs) > 50:
            boxes.append([np.percentile(xs, 1) / ww, ys.min() / hh, np.percentile(xs, 99) / ww, np.percentile(ys, 99) / hh])
    return [float(v) for v in np.median(np.array(boxes), axis=0)] if boxes else [0.25, 0.2, 0.75, 1.0]


def to_screen(box, src, W, H, focusX):
    """Boîte en parts de la source -> pixels à l'écran (object-fit: cover, object-position focusX% 50%)."""
    sw, sh = src
    s = max(W / sw, H / sh)
    dw, dh = sw * s, sh * s
    ox, oy = (W - dw) * focusX / 100, (H - dh) / 2
    return [ox + box[0] * dw, oy + box[1] * dh, ox + box[2] * dw, oy + box[3] * dh]


def _svg_mask(W, H, x0, y0, x1, y1, r):
    """Masque CSS : tout l'écran SAUF le cadre arrondi (evenodd) -> data URI."""
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">'
           f'<path fill-rule="evenodd" fill="#000" d="M0 0H{W}V{H}H0Z M{x0 + r} {y0}H{x1 - r}A{r} {r} 0 0 1 {x1} {y0 + r}V{y1 - r}'
           f'A{r} {r} 0 0 1 {x1 - r} {y1}H{x0 + r}A{r} {r} 0 0 1 {x0} {y1 - r}V{y0 + r}A{r} {r} 0 0 1 {x0 + r} {y0}Z"/></svg>')
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()


DOODLES = [  # traits dessinés à la main (viewBox 100), posés autour de la tête
    "M50 82 C20 60 8 42 22 28 C34 17 46 24 50 36 C54 24 66 17 78 28 C92 42 80 60 50 82 Z",          # cœur
    "M50 8 L58 40 L92 50 L58 60 L50 92 L42 60 L8 50 L42 40 Z",                                     # étincelle
    "M10 70 C30 20 60 90 90 30 M72 26 L91 29 L87 48",                                              # flèche en vague
    "M12 50 Q24 30 36 50 T60 50 T84 50",                                                           # gribouillis
]


def effets(job, cfg, words, segments, dur, W, H, T0, cut, src, focusX, accent, avoid=None):
    """-> html (dans #cam, au-dessus de la vidéo), js, css, svg (filtres), whoosh (temps), rapport."""
    from cutout import person_matte
    out_html, js, rep, whoosh = [], [], [], []
    css = f"""
  .fxcut {{ position: absolute; left: 0; top: 0; width: {W}px; height: {H}px; object-fit: cover; object-position: {focusX}% 50%; }}
  .fxo {{ position: absolute; inset: 0; opacity: 0; }}
  .fxw {{ position: absolute; inset: 0; }}
  .fxbg {{ position: absolute; left: 0; top: 0; width: {W}px; height: {H}px; object-fit: cover; z-index: -1;
          filter: blur(34px) brightness(.42); transform: scale(1.15); }}
  .fxd path {{ fill: none; stroke: #fff; stroke-width: 6; stroke-linecap: round; stroke-linejoin: round; }}"""
    svg, cuts = [], [float(s["out_start"]) for s in segments[1:]]
    def label(i, e, a, d):  # nom de l'effet à l'écran (démo, tuto) : pastille en haut
        if e.get("titre"):
            out_html.append(f'        <div class="clip fxt" id="fxt{i}" data-start="{round(T0 + a, 3)}" data-duration="{round(d, 3)}" '
                            f'data-track-index="{TR + 7}"><span>{esc(e["titre"])}</span></div>')
            js.append(f'  tl.fromTo("#fxt{i} span", {{ opacity: 0, y: -20, scale: .9 }}, {{ opacity: 1, y: 0, scale: 1, duration: 0.3, ease: "back.out(2)", immediateRender: false }}, {a});')
            js.append(f'  tl.to("#fxt{i} span", {{ opacity: 0, y: -12, duration: 0.2 }}, {round(a + d - 0.22, 3)});')

    for i, e in enumerate(cfg):
        kind = e.get("effet")
        if kind not in EFFETS:
            rep.append({"effet": kind, "pose": False, "raison": f"effet inconnu ({', '.join(EFFETS)})"})
            continue
        hit = word_hit(words, e.get("mot", ""), e.get("occurrence", 1))
        if hit is None:
            rep.append({"effet": kind, "mot": e.get("mot"), "pose": False, "raison": "mot non dit"})
            continue
        t0 = round(max(0.0, float(hit["start"]) - 0.05), 3)
        d = round(min(float(e.get("dur", EFFETS[kind])), dur - t0 - 0.1), 3)
        if avoid and t0 < avoid[1] and t0 + d > avoid[0]:
            rep.append({"effet": kind, "mot": e.get("mot"), "pose": False, "raison": "pendant le catalogue"})
            continue
        if kind == "traverse":
            near = [c for c in cuts if abs(c - t0) <= 1.2]
            tc = round(min(near, key=lambda c: abs(c - t0)) if near else t0, 3)
            js.append(f'  tl.set("#fxv", {{ transformOrigin: "{focusX}% 40%" }}, {round(max(0, tc - 0.2), 3)});')
            js.append(f'  tl.fromTo("#fxv", {{ scale: 1, filter: "blur(0px)" }}, {{ scale: 2.1, filter: "blur(14px)", duration: 0.2, ease: "power3.in", immediateRender: false }}, {round(max(0, tc - 0.2), 3)});')
            js.append(f'  tl.fromTo("#fxv", {{ scale: 2.1, filter: "blur(14px)" }}, {{ scale: 1, filter: "blur(0px)", duration: 0.34, ease: "power3.out", immediateRender: false }}, {tc});')
            whoosh.append(tc)
            label(i, e, max(0.0, tc - 0.3), 1.6)
            rep.append({"effet": kind, "mot": e.get("mot"), "a": tc, "sur_coupe": bool(near)})
            continue
        if d < 0.8:
            rep.append({"effet": kind, "mot": e.get("mot"), "pose": False, "raison": "trop près de la fin"})
            continue
        rel = person_matte(job, job / "assets" / cut, t0, d, model=e.get("model", "u2net_human_seg"))
        bx = to_screen(matte_box(job, rel), src, W, H, focusX)
        cx, cy = (bx[0] + bx[2]) / 2, bx[1] + (bx[3] - bx[1]) * 0.35
        org = f"{round(100 * cx / W, 1)}% {round(100 * cy / H, 1)}%"
        st = round(T0 + t0, 3)
        vid = (f'        <div class="fxw" id="fxw{i}"><video id="fx{i}" class="clip fxcut" src="{esc(rel)}" data-start="{st}" data-duration="{d}" '
               f'data-track-index="{TR + 5}" muted playsinline></video></div>')
        if kind == "vertigo":  # décor qui recule sous la personne de taille fixe ; coup sec à l'entrée et à la sortie
            P = float(e.get("force", 1.28))
            out_html.append(vid)
            js.append(f'  tl.set("#fxv, #fxw{i}", {{ transformOrigin: "{org}" }}, {t0});')
            js.append(f'  tl.set("#fxw{i}", {{ scale: {P} }}, {t0});')
            js.append(f'  tl.fromTo("#fxv", {{ scale: {P} }}, {{ scale: 1, duration: {d}, ease: "power2.inOut", immediateRender: false }}, {t0});')
            whoosh.append(t0)
        elif kind == "cadre":  # l'image rétrécit dans un cadre de Reel sur fond flouté ; la personne (détourée) en déborde
            k = float(e.get("echelle", 0.74))
            ox, oy = cx, cy
            sc = lambda x, o: o + (x - o) * k
            vy1 = sc(H, oy)
            fw = round(min(W * float(e.get("largeur", 0.6)), (sc(W, ox) - sc(0, ox)) * 0.86))
            fx0 = round(min(max(sc(0, ox) + W * 0.02, ox - fw / 2), sc(W, ox) - W * 0.02 - fw))
            fy0 = round(max(sc(0, oy) + H * 0.02, sc(bx[1], oy) + H * 0.055))  # le haut de la tête sort du cadre
            fy1 = round(max(fy0 + H * 0.3, min(vy1 - H * 0.015, H * 0.93)))
            r = round(W * 0.04)
            mask = _svg_mask(W, H, fx0, fy0, fx0 + fw, fy1, r)
            ic = round(W * 0.05)
            icons = "".join(f'<i style="top:{n * round(ic * 1.6)}px">{g}</i>' for n, g in enumerate(("♥", "💬", "➤")))
            out_html.append(f'        <video class="clip fxbg" id="fxg{i}" src="assets/{esc(cut)}" data-start="{st}" data-duration="{d}" data-media-start="{t0}" '
                            f'data-track-index="{TR + 2}" muted playsinline></video>')
            out_html.append(f'        <div class="clip fxo fxb" id="fxb{i}" data-start="{st}" data-duration="{d}" data-track-index="{TR + 3}" '
                            f'style="-webkit-mask-image:url({mask});mask-image:url({mask})"></div>')
            out_html.append(f'        <div class="clip fxo" id="fxf{i}" data-start="{st}" data-duration="{d}" data-track-index="{TR + 4}">'
                            f'<div class="fxr" style="left:{fx0}px;top:{fy0}px;width:{fw}px;height:{fy1 - fy0}px;border-radius:{r}px"></div></div>')
            out_html.append(vid)
            out_html.append(f'        <div class="clip fxo" id="fxu{i}" data-start="{st}" data-duration="{d}" data-track-index="{TR + 6}" data-layout-ignore>'
                            f'<div style="position:absolute;left:{fx0}px;top:{fy0}px;width:{fw}px;height:{fy1 - fy0}px">'
                            f'<div class="fxi" style="font-size:{ic}px">{icons}</div><div class="fxh" style="font-size:{round(ic * 0.5)}px">@{esc(e.get("compte", "toncompte"))}</div></div></div>')
            js.append(f'  tl.set("#fxv, #fxw{i}", {{ transformOrigin: "{org}" }}, {t0});')
            js.append(f'  tl.fromTo("#fxv, #fxw{i}", {{ scale: 1 }}, {{ scale: {k}, duration: 0.4, ease: "power3.out", immediateRender: false }}, {t0});')
            js.append(f'  tl.to("#fxb{i}", {{ opacity: 1, duration: 0.3, ease: "power2.out" }}, {round(t0 + 0.1, 3)});')
            js.append(f'  tl.fromTo("#fxf{i}, #fxu{i}", {{ opacity: 0, scale: 1.08 }}, {{ opacity: 1, scale: 1, duration: 0.35, ease: "back.out(1.6)", immediateRender: false }}, {round(t0 + 0.15, 3)});')
            js.append(f'  tl.to("#fxb{i}, #fxf{i}, #fxu{i}", {{ opacity: 0, duration: 0.22 }}, {round(t0 + d - 0.32, 3)});')
            js.append(f'  tl.to("#fxv, #fxw{i}", {{ scale: 1, duration: 0.3, ease: "power2.inOut" }}, {round(t0 + d - 0.3, 3)});')
            whoosh.append(t0)
        elif kind == "contour":  # contour blanc qui tremble (« boil ») + petits dessins autour de la tête
            svg.append(f'<filter id="boil{i}" x="-10%" y="-10%" width="120%" height="120%"><feTurbulence id="boilt{i}" type="fractalNoise" '
                       f'baseFrequency="0.03" numOctaves="2" seed="1" result="n"/><feDisplacementMap in="SourceGraphic" in2="n" scale="11" '
                       f'xChannelSelector="R" yChannelSelector="G"/></filter>')
            o = max(3, round(W * 0.007))
            sh = " ".join(f"drop-shadow({dx * o}px {dy * o}px 0 #fff)" for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
            out_html.append(f'        <video id="fxl{i}" class="clip fxcut" src="{esc(rel)}" data-start="{st}" data-duration="{d}" data-track-index="{TR + 4}" '
                            f'muted playsinline style="filter: brightness(0) invert(1) {sh} url(#boil{i})"></video>')
            out_html.append(vid)
            sz = round(W * 0.15)  # autour de la tête (haut du détourage), jamais hors de l'image
            spots = [(cx - W * 0.3, bx[1] + H * 0.02, 0), (cx + W * 0.3, bx[1] - H * 0.01, 1),
                     (cx + W * 0.36, bx[1] + H * 0.14, 2), (cx - W * 0.36, bx[1] + H * 0.17, 3)]
            dd = "".join(f'<svg class="fxd" viewBox="0 0 100 100" style="position:absolute;left:{round(min(W * 0.97 - sz, max(W * 0.03, x - sz / 2)))}px;'
                         f'top:{round(min(H - sz, max(H * 0.03, y - sz / 2)))}px;width:{sz}px;height:{sz}px;filter:url(#boil{i})">'
                         f'<path d="{DOODLES[k]}" style="stroke:{accent if k == 0 else "#fff"}"/></svg>' for x, y, k in spots)
            out_html.append(f'        <div class="clip" id="fxd{i}" data-start="{st}" data-duration="{d}" data-track-index="{TR + 6}" '
                            f'style="position:absolute;inset:0">{dd}</div>')
            js.append(f'  document.querySelectorAll("#fxd{i} path").forEach(function (p) {{ var L = p.getTotalLength(); p.style.strokeDasharray = L; p.style.strokeDashoffset = L; }});')
            js.append(f'  tl.to("#fxd{i} path", {{ strokeDashoffset: 0, duration: 0.4, stagger: 0.12, ease: "power2.out" }}, {round(t0 + 0.15, 3)});')
            js.append(f'  tl.fromTo("#fxl{i}", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.2, immediateRender: false }}, {t0});')
            k_, tt = 0, t0
            while tt < t0 + d:  # le trait « bout » : nouveau bruit toutes les 0,12 s (≈ 8 images/s, comme un dessin animé)
                k_ += 1
                js.append(f'  tl.set("#boilt{i}", {{ attr: {{ seed: {k_ % 5 + 1} }} }}, {round(tt, 3)});')
                tt += 0.12
            js.append(f'  tl.to("#fxl{i}, #fxd{i}", {{ opacity: 0, duration: 0.25 }}, {round(t0 + d - 0.27, 3)});')
        label(i, e, t0, d)
        rep.append({"effet": kind, "mot": e.get("mot"), "a": t0, "duree": d, "detourage": rel})
    css += f"""
  .fxb {{ backdrop-filter: blur(22px) brightness(.42) saturate(.8); -webkit-backdrop-filter: blur(22px) brightness(.42) saturate(.8);
         -webkit-mask-size: 100% 100%; mask-size: 100% 100%; }}
  .fxr {{ position: absolute; box-sizing: border-box; border: {max(3, round(W * 0.006))}px solid rgba(255,255,255,.92);
         box-shadow: 0 0 0 1px rgba(0,0,0,.2), 0 {round(H * 0.01)}px {round(H * 0.03)}px rgba(0,0,0,.45); }}
  .fxi {{ position: absolute; right: 4%; bottom: 22%; width: 1.2em; height: 5em; color: #fff; text-shadow: 0 2px 8px rgba(0,0,0,.5); }}
  .fxi i {{ position: absolute; left: 0; font-style: normal; }}
  .fxt {{ position: absolute; left: 0; right: 0; top: {round(H * 0.07)}px; text-align: center; z-index: 60; }}
  .fxt span {{ display: inline-block; padding: .3em .75em; border-radius: 99px; background: {accent}; color: #111; font: 800 {round(W * 0.036)}px 'Inter', sans-serif;
              letter-spacing: .02em; text-transform: uppercase; box-shadow: 0 8px 24px rgba(0,0,0,.35); }}
  .fxh {{ position: absolute; left: 5%; bottom: 4%; color: #fff; font-family: 'Inter', sans-serif; font-weight: 700; text-shadow: 0 2px 8px rgba(0,0,0,.6); }}"""
    svg_html = f'    <svg width="0" height="0" style="position:absolute">{"".join(svg)}</svg>' if svg else ""
    return "\n".join(out_html), js, css, svg_html, whoosh, rep

"""MOTS DYNAMIQUES (rush plein écran) : un mot géant par idée, DERRIÈRE la personne détourée, les petits mots de la phrase
posés autour (« name / is » autour de « gabe »), une carte de verre en bas qui reprend la phrase avec un picto, et pour un
chiffre une grille d'icônes qui s'allument (≤ 60) ou une barre qui se remplit, compteur à côté. Le mot sort en traînée
de flou ; à chaque coupe du dérush, transition fouettée (flou + glissé) et légère secousse.

work/<slug>_mots.json (proposé par build_composition.py --mots s'il manque ; Claude relit et corrige) :
  [{"word": "<mot dit où le mot géant arrive>", "big": "50", "before": "over", "after": "properties",
    "card": "bought and sold", "icon": "house", "count": {"to": 50, "icon": "house"} | {"to": 365, "unit": "days"}}]
Les mots viennent de la phrase dite (jamais inventés) ; un mot géant toutes les 1,5 à 3 s.
"""
import html
import re

from common import word_hit

esc = lambda s: html.escape(str(s), quote=True)

STOP = {"le", "la", "les", "un", "une", "des", "de", "du", "et", "en", "à", "a", "au", "aux", "que", "qui", "pour", "dans", "sur",
        "par", "avec", "ce", "cette", "ces", "est", "sont", "je", "tu", "il", "elle", "on", "nous", "vous", "ils", "mon", "ton", "son",
        "ma", "ta", "sa", "mes", "tes", "ses", "the", "a", "an", "of", "to", "and", "is", "in", "on", "my", "i", "it", "that", "this",
        "donc", "alors", "aussi", "fait", "c'est", "j'ai", "euh", "ben", "bah", "genre", "vraiment", "notamment", "plus", "très"}
WEAK = re.compile(r"^(d'|l'|qu')?(permet\w*|fai\w*|utilis\w*|cré\w*|met\w*|mett\w*|peu\w*|veu\w*|pouv\w*|dev\w*|avoir|être|voir|"
                  r"aller|dire|donn\w*|prend\w*|sorte|chose\w*|vraiment|notamment|toujours|beaucoup|quelque\w*|really|actually)$", re.I)
ICON_HINTS = [(r"maison|appart|immo|propri|house|home", "house"), (r"jour|semaine|mois|an\b|ans\b|day|year|week", "calendar"),
              (r"€|euro|prix|argent|chiffre|vente|vend|sold|money", "badge-euro"), (r"client|personne|gens|people|abonn", "users"),
              (r"vidéo|video|montage|reel", "clapperboard"), (r"skill|outil|ia\b|claude|tool", "sparkles"), (r"ville|lyon|paris|market|marché", "map-pin")]
clean = lambda w: re.sub(r"^[^\wÀ-ÿ%€]+|[^\wÀ-ÿ%€]+$", "", w)


def sentences(words):
    cur, out_ = [], []
    for i, w in enumerate(words):
        cur.append(w)
        gap = words[i + 1]["start"] - w["end"] if i + 1 < len(words) else 9
        if re.search(r"[.!?…]$", w["w"]) or gap > 0.45 or len(cur) >= 10:
            out_.append(cur)
            cur = []
    if cur:
        out_.append(cur)
    return out_


def suggest(words):
    """Une entrée par phrase : le chiffre, sinon le mot le plus long qui porte le sens ; 2 mots avant / après en satellites."""
    res, last = [], -9.0
    for s in sentences(words):
        ws = [clean(w["w"]) for w in s]
        cand = [j for j, x in enumerate(ws) if re.search(r"\d", x)] or \
               sorted([j for j, x in enumerate(ws) if len(x) >= 5 and x.lower() not in STOP and not WEAK.match(x)], key=lambda j: -len(ws[j]))
        if not cand:
            continue
        j = cand[0]
        if s[j]["start"] - last < 1.4:
            continue
        before = [x for x in ws[max(0, j - 2):j] if x]
        after = [x for x in ws[j + 1:j + 3] if x]
        e = {"word": s[j]["w"], "big": ws[j].lower() if not re.search(r"\d", ws[j]) else ws[j], "before": " ".join(before),
             "after": " ".join(after), "card": " ".join(x for x in ws[max(0, j - 3):j + 3] if x).lower()}
        txt = " ".join(ws).lower()
        for rx, ic in ICON_HINTS:
            if re.search(rx, txt):
                e["icon"] = ic
                break
        n = re.sub(r"\D", "", ws[j])
        if n and 2 <= int(n) <= 1000 and not re.search(r"[%€]", ws[j]):
            e["count"] = {"to": int(n), **({"icon": e.get("icon", "circle")} if int(n) <= 60 else {"unit": after[0] if after else ""})}
        res.append(e)
        last = s[j]["start"]
    return res


def scene_color(video):
    """Couleur du texte tirée de l'image (comme la référence : bleu clair sur une lumière froide) : teinte dominante du rush ;
    scène déjà très colorée (fond vert, rideau rouge) -> teinte opposée, pour que le mot ressorte. -> "#rrggbb" clair."""
    import colorsys
    import subprocess
    import numpy as np
    p = subprocess.run(["ffmpeg", "-v", "error", "-i", str(video), "-vf", "fps=1/4,scale=64:-2", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                       capture_output=True)
    px = np.frombuffer(p.stdout, np.uint8).reshape(-1, 3).astype(float) / 255
    if not len(px):
        return "#8fc8ff"
    hsv = np.array([colorsys.rgb_to_hsv(*c) for c in px[:: max(1, len(px) // 6000)]])
    w = hsv[:, 1] * hsv[:, 2]  # les pixels colorés et lumineux pèsent le plus
    ang = hsv[:, 0] * 2 * np.pi
    h = (np.arctan2((np.sin(ang) * w).sum(), (np.cos(ang) * w).sum()) / (2 * np.pi)) % 1.0
    sat = float(np.average(hsv[:, 1], weights=hsv[:, 2] + 1e-6))
    if sat > 0.3:
        h = (h + 0.5) % 1.0
    if 0.1 < h < 0.18:  # jaune-vert terne : poussé vers l'orange clair, plus lisible
        h = 0.08
    elif 0.18 <= h < 0.45:  # vert acide : peu flatteur sur la peau -> bleu clair, lisible partout
        h = 0.58
    r, g, b = colorsys.hsv_to_rgb(h, 0.55, 0.98)
    return "#{:02x}{:02x}{:02x}".format(round(r * 255), round(g * 255), round(b * 255))


def windows(spans, pad=0.25, gap=0.6):
    """Intervalles des mots géants fusionnés : le détourage n'est calculé que là où il sert."""
    out_ = []
    for a, b in sorted(spans):
        a, b = max(0.0, a - pad), b + pad
        if out_ and a - out_[-1][1] < gap:
            out_[-1][1] = max(out_[-1][1], b)
        else:
            out_.append([a, b])
    return out_


def head_box(job, rel):
    """[(instant dans l'extrait, haut de la tête, largeur de la tête)] à 4 i/s, en parts de la hauteur / largeur du détourage."""
    import subprocess
    import numpy as np
    from cutout import vsize
    w, h = vsize(job / rel)
    hh = 240
    ww = round(w * hh / h / 2) * 2
    p = subprocess.run(["ffmpeg", "-v", "error", "-c:v", "libvpx-vp9", "-i", str(job / rel), "-vf", f"fps=4,alphaextract,scale={ww}:{hh}",
                        "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True)
    res = []
    for k in range(len(p.stdout) // (ww * hh)):
        a = np.frombuffer(p.stdout[k * ww * hh:(k + 1) * ww * hh], np.uint8).reshape(hh, ww) > 128
        rows = np.where(a.mean(axis=1) > 0.004)[0]
        if not len(rows):
            continue
        top = rows[0]
        band = a[top + round(hh * 0.03): top + round(hh * 0.07)]  # hauteur du front : la largeur de la tête
        if band.size and band.any():
            cols = np.where(band.any(axis=0))[0]
            res.append((k / 4, top / hh, (cols[-1] - cols[0] + 1) / ww))
    return res, (w, h)


def nodes(job, entries, words, dur, W, H, T0, cut_path, acc, family, segments=None, icon=None, mix=None):
    """-> (html dans la caméra, html par-dessus, js, css, rapport)."""
    from cutout import head_top, person_matte
    placed = []
    for e in entries:
        hit = word_hit(words, e.get("word", ""), e.get("occurrence", 1)) if e.get("word") else None
        if hit:
            placed.append((max(0.0, hit["start"] - 0.1), e))
    placed.sort(key=lambda x: x[0])
    spans = []
    for k, (t, e) in enumerate(placed):
        nxt = placed[k + 1][0] if k + 1 < len(placed) else dur
        spans.append((t, min(nxt - 0.05, t + float(e.get("dur", 3.0)), dur - 0.05)))
    wins = windows(spans)
    cuts = [(a, round(b - a, 3), person_matte(job, cut_path, a, b - a)) for a, b in wins if b - a > 0.4]
    import numpy as np
    samples = []  # (instant du montage, haut de la tête, largeur affichée) : ramenée au cadre affiché (recadrage « cover »)
    for a, d, rel in cuts:
        fr, (sw, sh) = head_box(job, rel)
        sc_ = max(W / sw, H / sh)
        samples += [(a + tt, tp, wd * sw * sc_ / W) for tt, tp, wd in fr]
    cam, over, js, rep = [], [], [], []
    for a, d, rel in cuts:
        cam.append(f'        <video id="acut{len(cam)}" class="clip acut" data-layout-allow-occlusion src="{rel}" data-start="{round(a + T0, 3)}" data-duration="{d}" data-track-index="{5 + len(cam) % 2}" '
                   f'muted playsinline></video>')
    light = mix(acc, "#ffffff", 0.45)
    for k, ((t, e), (_, t1)) in enumerate(zip(placed, spans)):
        if t1 - t < 0.6:
            continue
        big = str(e.get("big", ""))
        S = round(min(H * (0.16 if re.search(r"\d", big) else 0.13), W * 0.9 / max(2.5, 0.62 * len(big))))
        win = [x for x in samples if t <= x[0] <= min(t1, t + 1.2)] or samples  # la tête quand CE mot arrive (les plans changent)
        head = float(np.median([x[1] for x in win])) if win else 0.3
        hw = float(np.percentile([x[2] for x in win], 75)) if win else 0.5
        # derrière seulement si la tête est assez étroite pour laisser lire le mot (plan large) ; sinon devant, en haut
        front = hw > 0.3
        if front:  # plan serré, tête collée au haut : le visage cacherait le mot -> devant, en haut
            S = round(S * 0.85)
            top = round(H * 0.07)
        else:  # comme la référence : le mot posé juste au-dessus, le haut de la tête mord le bas des lettres
            top = max(round(H * 0.03), round(head * H - 0.6 * S))
        did = f"dw{k}"
        cam.append(f'        <div class="clip dw{" front" if front else ""}" id="{did}" data-start="{round(t + T0, 3)}" data-duration="{round(t1 - t, 3)}" data-track-index="3" '
                   f'style="top:{top}px"><div class="dwi" style="font-size:{S}px">'
                   + (f'<span class="dws b" data-layout-allow-overlap>{esc(e["before"])}</span>' if e.get("before") else "")
                   + f'<span class="dwb" data-layout-allow-occlusion data-layout-allow-overlap>{esc(big)}</span>'
                   + (f'<span class="dws a" data-layout-allow-overlap>{esc(e["after"])}</span>' if e.get("after") else "") + '</div></div>')
        js.append(f'  tl.fromTo("#{did} .dwb", {{ opacity: 0, scale: 1.18, filter: "blur(14px)" }}, {{ opacity: 1, scale: 1, filter: "blur(0px)", duration: 0.32, '
                  f'ease: "power3.out", immediateRender: false }}, {round(t, 3)});')
        js.append(f'  tl.fromTo("#{did} .dws", {{ opacity: 0, y: 14 }}, {{ opacity: 1, y: 0, duration: 0.3, stagger: 0.12, ease: "power2.out", immediateRender: false }}, '
                  f'{round(t + 0.12, 3)});')
        js.append(f'  tl.to("#{did} .dwi", {{ x: -{round(W * 0.12)}, scaleX: 1.35, opacity: 0, filter: "blur(18px)", duration: 0.2, ease: "power2.in" }}, '
                  f'{round(t1 - 0.2, 3)});')  # sortie en traînée de flou
        if e.get("card"):
            gid = f"gc{k}"
            ic = icon(e["icon"]) if e.get("icon") and icon else ""
            over.append(f'      <div class="clip gcard" id="{gid}" data-start="{round(t + T0, 3)}" data-duration="{round(t1 - t, 3)}" data-track-index="{60 + k % 2}">'
                        f'<div class="gci"><span class="gico">{ic or "<i></i>"}</span><span class="gct">{esc(e["card"])}</span></div></div>')
            js.append(f'  tl.fromTo("#{gid} .gci", {{ opacity: 0, x: -40, filter: "blur(8px)" }}, {{ opacity: 1, x: 0, filter: "blur(0px)", duration: 0.35, '
                      f'ease: "power3.out", immediateRender: false }}, {round(t + 0.05, 3)});')
            js.append(f'  tl.to("#{gid} .gci", {{ opacity: 0, duration: 0.15 }}, {round(t1 - 0.15, 3)});')
        cn = e.get("count")
        if cn and cn.get("to"):
            n = int(cn["to"])
            cid = f"cn{k}"
            grid = n <= 60
            ic = icon(cn.get("icon", "circle")) if icon else ""
            inner = ("".join(f'<i class="ci c{j}">{ic}</i>' for j in range(n)) if grid else '<div class="cbar"><b></b></div>')
            over.append(f'      <div class="clip cnt" id="{cid}" data-start="{round(t + T0, 3)}" data-duration="{round(t1 - t, 3)}" data-track-index="{62 + k % 2}">'
                        f'<div class="cbox{" grid" if grid else ""}"><span class="cnum">0</span><div class="cin">{inner}</div></div>'
                        + (f'<div class="cunit">{esc(cn["unit"])}</div>' if cn.get("unit") else "") + '</div>')
            span = round(max(0.6, min(1.4, (t1 - t) * 0.55)), 2)
            js.append(f'  tl.fromTo("#{cid} .cbox", {{ opacity: 0, y: 30 }}, {{ opacity: 1, y: 0, duration: 0.3, ease: "power3.out", immediateRender: false }}, {round(t + 0.15, 3)});')
            js.append(f'  (function () {{ const el = document.querySelector("#{cid} .cnum"), cs = document.querySelectorAll("#{cid} .ci"), b = document.querySelector("#{cid} .cbar b"), o = {{ v: 0 }};'
                      f' tl.fromTo(o, {{ v: 0 }}, {{ v: {n}, duration: {span}, ease: "power2.out", immediateRender: false, onUpdate: function () {{'
                      f' const v = Math.round(o.v); el.textContent = v; cs.forEach(function (c, i) {{ c.classList.toggle("on", i < v); }});'
                      f' if (b) b.style.width = (100 * o.v / {n}) + "%"; }} }}, {round(t + 0.3, 3)}); }})();')
            if cn.get("unit"):
                js.append(f'  tl.fromTo("#{cid} .cunit", {{ opacity: 0, y: 12 }}, {{ opacity: 1, y: 0, duration: 0.3, immediateRender: false }}, {round(t + 0.3 + span, 3)});')
            js.append(f'  tl.to("#{cid} .cbox, #{cid} .cunit", {{ opacity: 0, duration: 0.15 }}, {round(t1 - 0.15, 3)});')
        rep.append({"mot": e.get("word"), "a": round(t, 2), "duree": round(t1 - t, 2), "geant": big, "place": "devant (cadrage serré)" if front else "derrière",
                    "box": [round(W * 0.05), top, round(W * 0.95), top + round(S * 1.15)]})  # boîte estimée (face.py)
    # transition fouettée à chaque coupe du dérush (flou + glissé) puis petite secousse
    for sg in (segments or [])[1:]:
        tc = float(sg["out_start"])
        if 0.2 < tc < dur - 0.3:
            js.append(f'  tl.fromTo("#zm", {{ x: {round(W * 0.07)}, filter: "blur(16px)" }}, {{ x: 0, filter: "blur(0px)", duration: 0.24, ease: "power3.out", '
                      f'immediateRender: false }}, {round(tc, 3)});')
            js.append(f'  tl.fromTo("#zm", {{ y: 0 }}, {{ y: 5, duration: 0.04, yoyo: true, repeat: 5, ease: "none", immediateRender: false }}, {round(tc + 0.24, 3)});')
    u = W / 1080
    css = f"""
  .acut {{ position: absolute; left: 0; top: 0; width: {W}px; height: {H}px; object-fit: cover; z-index: 3; }}
  .dw {{ position: absolute; left: 0; right: 0; text-align: center; z-index: 2; }}
  .dw.front {{ z-index: 4; }}
  .dwi {{ display: inline-block; position: relative; line-height: .84; font-family: '{family}', 'Inter', sans-serif; transform-origin: 50% 60%; }}
  .dwb {{ display: inline-block; font-weight: 600; letter-spacing: -.045em; padding: .12em .04em .2em; margin: -.12em -.04em -.2em; background: linear-gradient(180deg, {light} 0%, {acc} 100%);
         -webkit-background-clip: text; background-clip: text; color: transparent; filter: drop-shadow(0 .02em .06em rgba(0,0,0,.25)); }}
  .dws {{ position: absolute; font-size: .2em; font-weight: 500; color: #fff; letter-spacing: 0; white-space: nowrap; text-shadow: 0 2px 10px rgba(0,0,0,.5); }}
  .dws.b {{ left: 6%; bottom: 92%; }}
  .dws.a {{ right: 4%; top: 108%; }}
  .gcard {{ position: absolute; left: 0; right: 0; bottom: {round(H * 0.1)}px; z-index: 60; text-align: center; }}
  .gci {{ display: inline-flex; align-items: center; gap: {round(18*u)}px; max-width: 84%; padding: {round(16*u)}px {round(30*u)}px {round(16*u)}px {round(16*u)}px;
         border-radius: {round(26*u)}px; background: rgba(255,255,255,.14); border: 1px solid rgba(255,255,255,.28); backdrop-filter: blur(18px);
         -webkit-backdrop-filter: blur(18px); box-shadow: 0 {round(14*u)}px {round(40*u)}px rgba(0,0,0,.3); color: #fff;
         font-family: '{family}', 'Inter', sans-serif; }}
  .gico {{ flex: none; width: {round(62*u)}px; height: {round(62*u)}px; border-radius: {round(16*u)}px; background: rgba(255,255,255,.18); color: #fff;
          display: flex; align-items: center; justify-content: center; }}
  .gico svg {{ width: 56%; height: 56%; }}
  .gico i {{ width: {round(14*u)}px; height: {round(14*u)}px; border-radius: 50%; background: {acc}; }}
  .gct {{ font-size: {round(38*u)}px; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
  .cnt {{ position: absolute; left: {round(W * 0.07)}px; right: {round(W * 0.07)}px; top: {round(H * 0.56)}px; z-index: 55; text-align: center; }}
  .cbox {{ display: flex; align-items: center; gap: {round(24*u)}px; padding: {round(20*u)}px {round(26*u)}px; border-radius: {round(24*u)}px;
          background: rgba(10,14,24,.45); border: 1px solid rgba(255,255,255,.22); backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px); opacity: 0; }}
  .cnt {{ font-family: '{family}', 'Inter', sans-serif; }}
  .cnum {{ flex: none; min-width: 2.2em; font: 600 {round(56*u)}px 'IBM Plex Mono', monospace; color: #fff; text-align: left; }}
  .cin {{ flex: 1; display: flex; flex-wrap: wrap; gap: {round(8*u)}px; }}
  .ci {{ width: {round(40*u)}px; height: {round(40*u)}px; color: rgba(255,255,255,.22); font-style: normal; }}
  .ci svg {{ width: 100%; height: 100%; }}
  .ci.on {{ color: {light}; filter: drop-shadow(0 0 {round(8*u)}px {acc}); }}
  .cbar {{ flex: 1; height: {round(34*u)}px; border-radius: {round(8*u)}px; background: rgba(255,255,255,.15); overflow: hidden; }}
  .cbar b {{ display: block; height: 100%; width: 0; background: repeating-linear-gradient(90deg, {light} 0 {round(6*u)}px, transparent {round(6*u)}px {round(10*u)}px); }}
  .cunit {{ margin-top: {round(10*u)}px; font-size: {round(80*u)}px; font-weight: 600; letter-spacing: -.03em; color: {light}; opacity: 0;
           text-shadow: 0 4px 20px rgba(0,0,0,.4); }}"""
    return "\n".join(cam), over, js, css, rep

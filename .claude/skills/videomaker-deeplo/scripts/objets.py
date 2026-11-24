"""OBJETS DU PANNEAU (temps forts en plus de panel.py) : carte du monde, calendrier, timeline de montage, devis, revenus,
horloge. Même JSON que les autres temps forts (work/<slug>_panels.json), posés sur un mot dit :

  {"type": "map", "word": "…", "title": "…", "countries": ["France", "Belgique", "Suisse", "Canada"], "from": "France",
   "zoom": true, "label": "créateurs francophones", "notes": [{"text": "Résultats", "sub": "…"}]}
      (fond de carte Natural Earth via world-atlas, ISC ; noms en français ou en anglais ; arcs depuis "from")
  {"type": "calendar", "word": "…", "month": 10, "year": 2026, "marks": [5, 12, 19, 26], "title": "chaque semaine.", "cards": ["Méthode · Septembre"]}
  {"type": "timeline", "word": "…", "title": "Ce montage entier", "tracks": 4, "label": "monté par Claude"}   (pistes qui se remplissent)
  {"type": "invoice", "word": "…", "title": "Spot produit", "ref": "Devis n° 2026-118", "items": [{"label": "Tournage · 1 jour", "value": 1850}, …],
   "currency": "€", "stamp": "ACCEPTÉ"}   (total qui monte ; "total" pour l'imposer)
  {"type": "revenue", "word": "…", "title": "Ceux qui ont compris en premier", "value": 8431.65, "currency": "€", "points": [2, 3, 3, 5, 8],
   "payments": [{"label": "Paiement reçu", "sub": "Campagne UGC", "amount": "+1 200,00 €"}]}
  {"type": "clock", "word": "…", "to": 30, "unit": "minutes" | "jours", "label": "Temps de création"}
      (minutes : chronomètre + « 30 minutes. » ; jours : horloge qui tourne + « J+30 »)
Chiffres, devis, revenus : uniquement des données réelles ou annoncées comme exemple.
"""
import json
import math
import re
from pathlib import Path

TYPES = ("map", "calendar", "timeline", "invoice", "revenue", "clock")
WORLD = Path(__file__).resolve().parent.parent / "vendor" / "world" / "countries-110m.json"
FR = {"france": "France", "belgique": "Belgium", "suisse": "Switzerland", "canada": "Canada", "québec": "Canada", "quebec": "Canada",
      "maroc": "Morocco", "algérie": "Algeria", "tunisie": "Tunisia", "sénégal": "Senegal", "côte d'ivoire": "Côte d'Ivoire",
      "cameroun": "Cameroon", "mali": "Mali", "madagascar": "Madagascar", "luxembourg": "Luxembourg", "espagne": "Spain",
      "italie": "Italy", "allemagne": "Germany", "royaume-uni": "United Kingdom", "angleterre": "United Kingdom",
      "états-unis": "United States of America", "usa": "United States of America", "portugal": "Portugal", "pays-bas": "Netherlands",
      "brésil": "Brazil", "mexique": "Mexico", "chine": "China", "japon": "Japan", "inde": "India", "australie": "Australia",
      "congo": "Dem. Rep. Congo", "rdc": "Dem. Rep. Congo", "gabon": "Gabon", "bénin": "Benin", "togo": "Togo", "niger": "Niger",
      "burkina faso": "Burkina Faso", "guinée": "Guinea", "haïti": "Haiti", "liban": "Lebanon", "russie": "Russia", "ukraine": "Ukraine"}
MONTHS = ["", "janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]


def _p():
    import panel
    return panel


def world_shapes():
    """{nom anglais: [anneaux [(lon, lat)…]]} décodé du TopoJSON (arcs quantifiés, codés en écarts)."""
    d = json.loads(WORLD.read_text(encoding="utf-8"))
    (sx, sy), (tx, ty) = d["transform"]["scale"], d["transform"]["translate"]
    arcs = []
    for a in d["arcs"]:
        x = y = 0
        pts = []
        for dx, dy in a:
            x += dx
            y += dy
            pts.append((x * sx + tx, y * sy + ty))
        arcs.append(pts)

    def ring(ids):
        out = []
        for i in ids:
            seg = arcs[i] if i >= 0 else arcs[~i][::-1]
            out += seg[1:] if out else seg
        return out
    shapes = {}
    for g in d["objects"]["countries"]["geometries"]:
        polys = g["arcs"] if g["type"] == "MultiPolygon" else [g["arcs"]] if g["type"] == "Polygon" else []
        shapes[g["properties"]["name"]] = [ring(r) for poly in polys for r in poly]
    return shapes


def beat(job, typ, b, sid, s0, d, W, ph, u):
    p = _p()
    esc, icon, glue = p.esc, p.icon, p.glue
    bj = []
    card_in = (f'  tl.fromTo("#{sid} .card", {{ opacity: 0, y: 46, scale: 0.97 }}, {{ opacity: 1, y: 0, scale: 1, duration: 0.5, '
               f'ease: "power3.out", immediateRender: false }}, {s0 + 0.05});')
    head = f'<div class="chead">{esc(b["title"])}</div>' if b.get("title") else ""
    if typ == "map":
        MW = W - round(140 * u)
        MH = round(MW * 0.52)
        X = lambda lon: (lon + 180) / 360 * MW
        Y = lambda lat: (84 - lat) / 142 * MH
        shapes = world_shapes()
        want = [FR.get(str(c).lower(), str(c)) for c in b.get("countries", [])]
        src = FR.get(str(b.get("from", "")).lower(), b.get("from"))
        paths, boxes = [], {}
        for name, rings in shapes.items():
            kept = [[(lo, la) for lo, la in r if la > -58] for r in rings]
            dd = " ".join("M " + " L ".join(f"{X(lo):.1f} {Y(la):.1f}" for lo, la in r) + " Z" for r in kept if len(r) > 2)
            if not dd.strip():
                continue
            hit = name in want
            cls = f' class="on w{want.index(name)}"' if hit else ""
            paths.append(f'<path{cls} d="{dd}" />')
            big = max(rings, key=len)
            xs, ys = [X(lo) for lo, la in big], [Y(la) for lo, la in big]
            boxes[name] = (min(xs), min(ys), max(xs), max(ys))
        arcs_ = ""
        if src in boxes:
            sx0, sy0, sx1, sy1 = boxes[src]
            cx, cy = (sx0 + sx1) / 2, (sy0 + sy1) / 2
            for j, name in enumerate(n for n in want if n in boxes and n != src):
                x0, y0, x1, y1 = boxes[name]
                tx_, ty_ = (x0 + x1) / 2, (y0 + y1) / 2
                mx, my = (cx + tx_) / 2, min(cy, ty_) - abs(tx_ - cx) * 0.35 - 10
                arcs_ += f'<path class="arc a{j}" d="M {cx:.0f} {cy:.0f} Q {mx:.0f} {my:.0f} {tx_:.0f} {ty_:.0f}" pathLength="1000" />'
        hb = [boxes[n] for n in want if n in boxes]
        g_tr = ""
        if b.get("zoom") and hb:
            x0, y0 = min(x[0] for x in hb), min(x[1] for x in hb)
            x1, y1 = max(x[2] for x in hb), max(x[3] for x in hb)
            s = max(1.0, min(4.0, 0.8 * min(MW / max(1, x1 - x0), MH / max(1, y1 - y0))))
            g_tr = (s, MW / 2 - s * (x0 + x1) / 2, MH / 2 - s * (y0 + y1) / 2)
        notes = "".join(f'<div class="mnote n{j}"><b>{esc(n_.get("text", ""))}</b>' + (f'<small>{esc(n_["sub"])}</small>' if n_.get("sub") else "") + '</div>'
                        for j, n_ in enumerate(b.get("notes", [])[:3]))
        inner = (f'<div class="card win mapc">' + (f'<div class="chead" style="margin:{round(24*u)}px {round(30*u)}px 0">{esc(b["title"])}</div>' if b.get("title") else "")
                 + f'<svg class="wmap" width="{MW}" height="{MH}" viewBox="0 0 {MW} {MH}"><g class="mg">{"".join(paths)}{arcs_}</g></svg>'
                 + (f'<div class="mlab">{esc(b["label"])}</div>' if b.get("label") else "") + (f'<div class="mnotes">{notes}</div>' if notes else "") + '</div>')
        bj.append(card_in)
        span = max(0.12, min(0.35, d * 0.35 / max(1, len(want))))
        for j in range(len(want)):
            bj.append(p._cls_at(f"#{sid} .wmap .w{j}", "lit", True, round(s0 + 0.5 + j * span, 3)))
        ta = round(s0 + 0.6 + len(want) * span, 3)
        bj.append(f'  tl.fromTo("#{sid} .arc", {{ attr: {{ "stroke-dashoffset": 1000 }} }}, {{ attr: {{ "stroke-dashoffset": 0 }}, duration: 0.6, stagger: 0.1, '
                  f'ease: "power2.inOut", immediateRender: true }}, {ta});')
        if g_tr:
            s, gx, gy = g_tr
            bj.append(f'  tl.fromTo("#{sid} .mg", {{ x: 0, y: 0, scale: 1, transformOrigin: "0 0" }}, {{ x: {gx:.0f}, y: {gy:.0f}, scale: {s:.2f}, '
                      f'duration: {round(min(1.2, d * 0.35), 2)}, ease: "power3.inOut", immediateRender: false }}, {round(ta + 0.3, 3)});')
        bj.append(f'  tl.fromTo("#{sid} .mlab, #{sid} .mnote", {{ opacity: 0, y: 14 }}, {{ opacity: 1, y: 0, duration: 0.35, stagger: 0.15, ease: "power2.out", '
                  f'immediateRender: false }}, {round(ta + 0.5, 3)});')
    elif typ == "calendar":
        import calendar as cal
        mo, yr = int(b.get("month", 10)), int(b.get("year", 2026))
        first, ndays = cal.monthrange(yr, mo)
        marks = [int(x) for x in b.get("marks", [])]
        cells = "".join('<i class="cd e"></i>' for _ in range(first)) + "".join(
            f'<i class="cd{" mk m" + str(marks.index(k)) if k in marks else ""}">{k}</i>' for k in range(1, ndays + 1))
        heads = "".join(f'<b>{x}</b>' for x in ("L", "M", "M", "J", "V", "S", "D"))
        cards = "".join(f'<div class="ccard c{j}">{esc(x)}</div>' for j, x in enumerate(b.get("cards", [])[:3]))
        inner = ((f'<div class="ihead calt">{esc(b["title"])}</div>' if b.get("title") else "")
                 + f'<div class="card calc"><div class="chead">{MONTHS[mo]} {yr}</div><div class="cgrid">{heads}{cells}</div>{cards}</div>')
        bj.append(card_in)
        bj.append(f'  tl.fromTo("#{sid} .cd", {{ opacity: 0, scale: 0.6 }}, {{ opacity: 1, scale: 1, duration: 0.2, stagger: 0.012, ease: "back.out(2)", '
                  f'immediateRender: false }}, {s0 + 0.25});')
        span = max(0.15, min(0.45, (d * 0.5) / max(1, len(marks))))
        for j in range(len(marks)):
            bj.append(p._cls_at(f"#{sid} .m{j}", "on", True, round(s0 + 0.9 + j * span, 3)))
            bj.append(f'  tl.fromTo("#{sid} .m{j}", {{ scale: 1 }}, {{ scale: 1.25, duration: 0.12, yoyo: true, repeat: 1, immediateRender: false }}, {round(s0 + 0.9 + j * span, 3)});')
        for j in range(len(b.get("cards", [])[:3])):
            bj.append(f'  tl.fromTo("#{sid} .ccard.c{j}", {{ opacity: 0, x: 40 }}, {{ opacity: 1, x: 0, duration: 0.35, ease: "back.out(1.8)", immediateRender: false }}, '
                      f'{round(s0 + 1.0 + len(marks) * span + j * 0.25, 3)});')
    elif typ == "timeline":
        n = max(2, min(5, int(b.get("tracks", 4))))
        TW = W - round(140 * u) - round(2 * 30 * u) - round(70 * u)
        rows = []
        for r in range(n):
            x, k, clips = 0, 0, []
            while x < TW - 20:
                w = TW * (0.08 + ((r * 7 + k * 5) % 9) / 40)
                w = min(w, TW - x)
                clips.append(f'<i class="tc t{r}" style="left:{x:.0f}px;width:{max(8, w - 6):.0f}px"></i>')
                x += w
                k += 1
            rows.append(f'<div class="tr"><span>{("V" if r < n - 1 else "A") + str(r + 1 if r < n - 1 else 1)}</span><div class="tt">{"".join(clips)}</div></div>')
        inner = (f'<div class="card win tlc"><div class="wbar"><b></b><b></b><b></b><span class="url">{esc(b.get("title", "montage_final.prproj"))}</span></div>'
                 f'<div class="tbody">{"".join(rows)}<i class="tph"></i></div>' + (f'<div class="tlab">{esc(b["label"])}</div>' if b.get("label") else "") + '</div>')
        bj.append(card_in)
        tf = round(max(0.9, min(2.4, d * 0.6)), 2)
        bj.append(f'  tl.fromTo("#{sid} .tph", {{ x: 0 }}, {{ x: {TW}, duration: {tf}, ease: "none", immediateRender: false }}, {s0 + 0.3});')
        bj.append(f'  tl.fromTo("#{sid} .tc", {{ scaleX: 0 }}, {{ scaleX: 1, duration: 0.18, stagger: {{ each: {round(tf / 40, 3)}, from: "start" }}, ease: "power2.out", '
                  f'immediateRender: false }}, {s0 + 0.3});')
        if b.get("label"):
            bj.append(f'  tl.fromTo("#{sid} .tlab", {{ opacity: 0, y: 12 }}, {{ opacity: 1, y: 0, duration: 0.3, immediateRender: false }}, {round(s0 + 0.4 + tf, 3)});')
    elif typ == "invoice":
        items = b.get("items", [])[:6]
        cur = b.get("currency", "€")
        total = float(b.get("total") or sum(float(it.get("value", 0)) for it in items))
        fmt = lambda v: f"{v:,.0f}".replace(",", " ") + f" {cur}"
        rows = "".join(f'<div class="ivr r{j}"><span>{esc(it.get("label", ""))}</span><b>{esc(fmt(float(it.get("value", 0))))}</b></div>' for j, it in enumerate(items))
        inner = (f'<div class="card ivc"><div class="ivh"><small>{esc(b.get("ref", ""))}</small><b>{esc(b.get("title", "Devis"))}</b></div>{rows}'
                 f'<div class="ivt"><span>TOTAL HT</span><b><span class="ivn">0</span> {esc(cur)}</b></div>'
                 + (f'<div class="ivs">{esc(b["stamp"])}</div>' if b.get("stamp") else "") + '</div>')
        bj.append(f'  tl.fromTo("#{sid} .card", {{ opacity: 0, y: 46, rotation: -3 }}, {{ opacity: 1, y: 0, rotation: -1.5, duration: 0.5, ease: "power3.out", '
                  f'immediateRender: false }}, {s0 + 0.05});')
        bj.append(f'  tl.fromTo("#{sid} .ivr", {{ opacity: 0, x: -16 }}, {{ opacity: 1, x: 0, duration: 0.25, stagger: 0.12, immediateRender: false }}, {s0 + 0.3});')
        tt = round(s0 + 0.4 + 0.12 * len(items), 3)
        bj.append(f'  (function () {{ const el = document.querySelector("#{sid} .ivn"), o = {{ v: 0 }}; tl.fromTo(o, {{ v: 0 }}, {{ v: {total}, duration: '
                  f'{round(min(1.2, d * 0.35), 2)}, ease: "power2.out", immediateRender: false, onUpdate: function () {{ el.textContent = Math.round(o.v).toLocaleString("fr-FR"); }} }}, {tt}); }})();')
        if b.get("stamp"):
            bj.append(f'  tl.fromTo("#{sid} .ivs", {{ opacity: 0, scale: 2.2, rotation: -20 }}, {{ opacity: 1, scale: 1, rotation: -10, duration: 0.35, ease: "back.out(2)", '
                      f'immediateRender: false }}, {round(tt + min(1.2, d * 0.35) + 0.15, 3)});')
    elif typ == "revenue":
        cur = b.get("currency", "€")
        v = float(b.get("value", 0))
        dec = 2 if v % 1 else 0
        pts = [float(x) for x in b.get("points", [1, 2, 2, 3, 5, 8])][:14]
        CW, CH = round((W - round(140 * u) - round(76 * u)) * 0.44), round(ph * 0.26)
        top = max(pts) * 1.1 or 1
        path = "M " + " L ".join(f"{CW * i / max(1, len(pts) - 1):.0f} {CH - CH * y / top:.0f}" for i, y in enumerate(pts))
        pays = "".join(f'<div class="pay p{j}"><span class="pic">{icon("arrow-down-left")}</span><span class="ptx"><b>{esc(x.get("label", "Paiement reçu"))}</b>'
                       f'<small>{esc(x.get("sub", ""))}</small></span><span class="pam">{esc(x.get("amount", ""))}</span></div>'
                       for j, x in enumerate(b.get("payments", [])[:3]))
        inner = (f'<div class="card revc">{head}<div class="rvn"><span class="rvv">0</span> {esc(cur)}</div>'
                 f'<div class="rvup">▲ {esc(b.get("trend", "en hausse"))}</div><div class="rvb"><svg width="{CW}" height="{CH}" viewBox="0 0 {CW} {CH}">'
                 f'<path class="rvl" d="{path}" pathLength="1000" /></svg><div class="pays">{pays}</div></div></div>')
        bj.append(card_in)
        bj.append(f'  (function () {{ const el = document.querySelector("#{sid} .rvv"), o = {{ v: 0 }}; tl.fromTo(o, {{ v: 0 }}, {{ v: {v}, duration: {round(min(1.6, d * 0.5), 2)}, '
                  f'ease: "power2.out", immediateRender: false, onUpdate: function () {{ el.textContent = o.v.toLocaleString("fr-FR", {{ minimumFractionDigits: {dec}, '
                  f'maximumFractionDigits: {dec} }}); }} }}, {s0 + 0.3}); }})();')
        bj.append(f'  tl.fromTo("#{sid} .rvl", {{ attr: {{ "stroke-dashoffset": 1000 }} }}, {{ attr: {{ "stroke-dashoffset": 0 }}, duration: {round(min(1.6, d * 0.5), 2)}, '
                  f'ease: "power1.inOut", immediateRender: true }}, {s0 + 0.3});')
        span = max(0.3, min(0.6, d * 0.4 / max(1, len(b.get("payments", [])))))
        for j in range(len(b.get("payments", [])[:3])):
            bj.append(f'  tl.fromTo("#{sid} .p{j}", {{ opacity: 0, x: 30, scale: 0.9 }}, {{ opacity: 1, x: 0, scale: 1, duration: 0.3, ease: "back.out(2)", '
                      f'immediateRender: false }}, {round(s0 + 0.6 + j * span, 3)});')
    else:  # clock : chronomètre (minutes) ou horloge qui tourne (jours)
        to = float(b.get("to", 30))
        days = str(b.get("unit", "minutes")).startswith("jour") or b.get("unit") == "days"
        R = round(min(W * 0.27, ph * 0.3))
        ticks = "".join(f'<line x1="0" y1="{-R + (14 if k % 5 else 26) * u:.0f}" x2="0" y2="{-R + 4 * u:.0f}" transform="rotate({k * 6})" class="{"tk5" if k % 5 == 0 else "tk"}" />'
                        for k in range(60))
        nums = "" if days else "".join(f'<text x="{math.sin(math.radians(a)) * (R - 50 * u):.0f}" y="{-math.cos(math.radians(a)) * (R - 50 * u) + 10 * u:.0f}" '
                                       f'text-anchor="middle">{n}</text>' for a, n in ((0, 0), (90, 15), (180, 30), (270, 45)))
        svg = (f'<svg class="clk" width="{2 * R + 40}" height="{2 * R + 40}" viewBox="{-R - 20} {-R - 20} {2 * R + 40} {2 * R + 40}">'
               f'<circle r="{R}" class="cf" />{ticks}{nums}<path class="csw" d="" /><line class="chand" x1="0" y1="{round(12 * u)}" x2="0" y2="{-R + round(30 * u)}" />'
               f'<circle r="{round(9 * u)}" class="hub" />' + ('' if days else f'<rect class="btn" x="{-round(22 * u)}" y="{-R - round(34 * u)}" width="{round(44 * u)}" height="{round(22 * u)}" rx="4" />')
               + '</svg>')
        lab = f'<div class="ckk">{esc(b["label"])}</div>' if b.get("label") else ""
        big = (f'<div class="ckb">J+<span class="ckn">1</span></div>' if days else f'<div class="ckb"><span class="ckn">0</span> <small>{esc(b.get("unit", "minutes"))}.</small></div>')
        inner = f'<div class="clkw"><div class="ckt">{lab}{big}</div>{svg}</div>'
        tf = round(max(1.0, min(2.6, d * 0.6)), 2)
        turns = 1 if not days else max(2, min(8, int(to // 4)))
        endang = (to / 60 * 360) if not days else turns * 360
        bj.append(f'  tl.fromTo("#{sid} .clkw", {{ opacity: 0, y: 30 }}, {{ opacity: 1, y: 0, duration: 0.4, ease: "power3.out", immediateRender: false }}, {s0 + 0.05});')
        bj.append(f'  (function () {{ const h = document.querySelector("#{sid} .chand"), sw = document.querySelector("#{sid} .csw"), n = document.querySelector("#{sid} .ckn"), o = {{ v: 0 }};'
                  f' tl.fromTo(o, {{ v: 0 }}, {{ v: 1, duration: {tf}, ease: "power2.inOut", immediateRender: true, onUpdate: function () {{'
                  f' const a = o.v * {endang:.1f}; h.setAttribute("transform", "rotate(" + a + ")");'
                  f' const r = {R - round(6 * u)}, aa = Math.min(a, 359.9) * Math.PI / 180, x = Math.sin(aa) * r, y = -Math.cos(aa) * r;'
                  f' sw.setAttribute("d", {"''" if days else '"M 0 0 L 0 " + (-r) + " A " + r + " " + r + " 0 " + (a > 180 ? 1 : 0) + " 1 " + x + " " + y + " Z"'});'
                  f' n.textContent = Math.max({1 if days else 0}, Math.round(o.v * {to})); }} }}, {s0 + 0.35}); }})();')
    return inner, bj


def css(W, ph, acc, on_acc):
    u = W / 1080
    mono = "'IBM Plex Mono', monospace"
    return f"""
  .mapc {{ padding: 0 0 {round(26*u)}px; }}
  .wmap {{ display: block; margin: {round(16*u)}px 0 0; overflow: hidden; }}
  .wmap path {{ fill: var(--ui-soft); stroke: var(--ui-line); stroke-width: 0.6; vector-effect: non-scaling-stroke; }}
  .wmap path.lit {{ fill: {acc}; stroke: {acc}; filter: drop-shadow(0 0 {round(8*u)}px {acc}88); }}
  .wmap .arc {{ fill: none; stroke: {acc}; stroke-width: {max(2, round(3*u))}; stroke-dasharray: 1000; stroke-linecap: round; filter: none; }}
  .mlab {{ margin: {round(14*u)}px {round(30*u)}px 0; font-size: {round(54*u)}px; font-weight: 800; letter-spacing: -.02em; line-height: 1.05; opacity: 0; }}
  .mnotes {{ display: flex; gap: {round(14*u)}px; margin: {round(16*u)}px {round(30*u)}px 0; }}
  .mnote {{ flex: 1; padding: {round(14*u)}px {round(18*u)}px; border-radius: {round(14*u)}px; background: var(--ui-soft); border: 1px solid var(--ui-line); opacity: 0; }}
  .mnote b {{ display: block; font-size: {round(28*u)}px; }}
  .mnote small {{ display: block; font: 500 {round(20*u)}px {mono}; color: var(--ui-mute); }}
  .calt {{ top: {round(ph*0.06)}px; font: 800 {round(64*u)}px 'Inter', sans-serif; letter-spacing: -.02em; text-transform: none; opacity: 1; }}
  .calc {{ top: {round(ph*0.2)}px; }}
  .cgrid {{ display: grid; grid-template-columns: repeat(7, 1fr); gap: {round(10*u)}px; }}
  .cgrid b {{ text-align: center; font: 500 {round(22*u)}px {mono}; color: var(--ui-mute); }}
  .cd {{ display: flex; align-items: center; justify-content: center; height: {round(64*u)}px; border-radius: {round(12*u)}px; background: var(--ui-soft);
        border: 1px solid var(--ui-line); font: 500 {round(24*u)}px {mono}; font-style: normal; }}
  .cd.e {{ background: none; border: none; }}
  .cd.mk.on {{ background: {acc}; color: {on_acc}; border-color: {acc}; box-shadow: 0 0 {round(16*u)}px {acc}66; }}
  .ccard {{ margin-top: {round(14*u)}px; display: inline-block; margin-right: {round(10*u)}px; padding: {round(10*u)}px {round(18*u)}px; border-radius: {round(12*u)}px;
           background: var(--ui-solid); border: 1px solid var(--ui-line); font-size: {round(26*u)}px; font-weight: 700; opacity: 0; }}
  .tlc .tbody {{ position: relative; padding: {round(24*u)}px {round(30*u)}px {round(26*u)}px; }}
  .tr {{ display: flex; align-items: center; gap: {round(16*u)}px; margin-bottom: {round(12*u)}px; }}
  .tr span {{ width: {round(54*u)}px; font: 500 {round(22*u)}px {mono}; color: var(--ui-mute); }}
  .tt {{ position: relative; flex: 1; height: {round(46*u)}px; border-radius: {round(8*u)}px; background: var(--ui-soft); overflow: hidden; }}
  .tc {{ position: absolute; top: {round(4*u)}px; bottom: {round(4*u)}px; border-radius: {round(6*u)}px; transform-origin: 0 50%; transform: scaleX(0); }}
  .tc.t0 {{ background: {acc}; }} .tc.t1 {{ background: #4f8f7a; }} .tc.t2 {{ background: #7a6ab0; }} .tc.t3 {{ background: #3d7bd9; }} .tc.t4 {{ background: #c9a227; }}
  .tph {{ position: absolute; top: {round(14*u)}px; bottom: {round(14*u)}px; left: {round(30*u + 70*u)}px; width: {max(2, round(3*u))}px; background: #ff3b30;
         box-shadow: 0 0 {round(10*u)}px #ff3b30; }}
  .tlab {{ margin: 0 {round(30*u)}px {round(26*u)}px; font-size: {round(40*u)}px; font-weight: 800; opacity: 0; }}
  .ivc {{ background: #fbfaf7 !important; color: #151515; border-radius: {round(10*u)}px !important; left: {round(120*u)}px !important; right: {round(120*u)}px !important; }}
  .ivh small {{ display: block; font: 500 {round(20*u)}px {mono}; color: #15151588; letter-spacing: .08em; text-transform: uppercase; }}
  .ivh b {{ display: block; font-size: {round(48*u)}px; font-weight: 800; letter-spacing: -.02em; margin-bottom: {round(16*u)}px; }}
  .ivr {{ display: flex; justify-content: space-between; padding: {round(12*u)}px 0; border-top: 1px solid #15151514; font-size: {round(28*u)}px; opacity: 0; }}
  .ivr b {{ font: 600 {round(26*u)}px {mono}; }}
  .ivt {{ display: flex; justify-content: space-between; align-items: baseline; padding-top: {round(16*u)}px; border-top: 2px solid #151515; }}
  .ivt > span {{ font: 600 {round(22*u)}px {mono}; letter-spacing: .1em; }}
  .ivt b {{ font-size: {round(64*u)}px; font-weight: 800; letter-spacing: -.03em; }}
  .ivs {{ position: absolute; right: {round(30*u)}px; top: {round(30*u)}px; padding: .1em .4em; border: {round(5*u)}px solid #1f9d55; color: #1f9d55; font-weight: 900;
         font-size: {round(40*u)}px; border-radius: {round(8*u)}px; opacity: 0; }}
  .rvn {{ font-size: {round(96*u)}px; font-weight: 800; letter-spacing: -.03em; line-height: 1; font-variant-numeric: tabular-nums; }}
  .rvup {{ margin-top: {round(8*u)}px; font: 600 {round(22*u)}px {mono}; color: #1f9d55; }}
  .rvb {{ display: flex; gap: {round(20*u)}px; align-items: flex-end; margin-top: {round(16*u)}px; }}
  .rvb svg {{ flex: none; overflow: visible; }}
  .rvl {{ fill: none; stroke: {acc}; stroke-width: {round(5*u)}; stroke-linejoin: round; stroke-linecap: round; stroke-dasharray: 1000; }}
  .pays {{ flex: 1; display: flex; flex-direction: column; gap: {round(10*u)}px; min-width: 0; }}
  .pay {{ display: flex; align-items: center; gap: {round(10*u)}px; padding: {round(10*u)}px {round(12*u)}px; border-radius: {round(12*u)}px; background: var(--ui-soft);
         border: 1px solid var(--ui-line); opacity: 0; }}
  .pic {{ flex: none; width: {round(46*u)}px; height: {round(46*u)}px; border-radius: 50%; background: {acc}; color: {on_acc}; display: flex; align-items: center; justify-content: center; }}
  .pic svg {{ width: 60%; height: 60%; }}
  .ptx {{ flex: 1; min-width: 0; }}
  .ptx b {{ display: block; font-size: {round(26*u)}px; white-space: nowrap; }}
  .ptx small {{ display: block; font-size: {round(20*u)}px; color: var(--ui-mute); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
  .pam {{ font: 600 {round(24*u)}px {mono}; color: #1f9d55; white-space: nowrap; }}
  .clkw {{ position: absolute; left: {round(70*u)}px; right: {round(40*u)}px; top: {round(ph*0.14)}px; display: flex; align-items: center; justify-content: space-between; opacity: 0; }}
  .ckk {{ font: 500 {round(24*u)}px {mono}; letter-spacing: .14em; text-transform: uppercase; color: {acc}; margin-bottom: {round(10*u)}px; }}
  .ckb {{ font-size: {round(130*u)}px; font-weight: 800; letter-spacing: -.04em; line-height: 1; white-space: nowrap; }}
  .ckb small {{ font-size: .32em; font-style: italic; font-weight: 700; letter-spacing: -.01em; }}
  .clk .cf {{ fill: #f6f4ef; stroke: rgba(0,0,0,.15); stroke-width: 2; filter: drop-shadow(0 {round(14*u)}px {round(30*u)}px rgba(0,0,0,.35)); }}
  .clk .tk {{ stroke: #15151555; stroke-width: 1.5; }}
  .clk .tk5 {{ stroke: #151515; stroke-width: 3; }}
  .clk text {{ font: 700 {round(28*u)}px 'Inter', sans-serif; fill: #151515; }}
  .clk .csw {{ fill: {acc}33; }}
  .clk .chand {{ stroke: {acc}; stroke-width: {round(5*u)}; stroke-linecap: round; }}
  .clk .hub {{ fill: #151515; }}
  .clk .btn {{ fill: #151515; }}"""

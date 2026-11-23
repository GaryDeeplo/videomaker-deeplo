"""ACCROCHES ANIMÉES PAR STYLE (3 s) -> library/block/accroche-<style>/accroche-<style>.html.

Un même titre, dix styles d'animation (idée : « un sujet, plusieurs styles », réécrite ici en CSS / SVG / GSAP) :
papier, plan, pate, neon, aquarelle, pixel, isometrique, mosaique, encre, relief. Variables : text (titre court),
sub (petite ligne), accent, bg, ink, font. Sortie en volet vers le haut sur les 0,45 dernières secondes : la vidéo
démarre dessous. Montage : "hook": {"style": "neon", "text": "…", "sub": "…"} (build_composition, build_footage)
ou une scène {"kind": "block", "block": "accroche-neon", "vars": {…}, "hold": 3} (vidéo sans rush).
Relancer après modification, puis tester (check + snapshot) et library.py save.
"""
import json
from pathlib import Path

LIB = Path(__file__).resolve().parents[4] / "library" / "block"
DUR = 3.0

# entrée du dessin selon le style (PIECES = éléments de premier niveau du SVG, STROKES = formes à tracer)
ART_ANIM = {
    "_": """          tl.fromTo(PIECES, { opacity: 0, scale: 0.6 }, { opacity: 1, scale: 1, duration: 0.5, stagger: 0.06, ease: "back.out(2)" }, 0.5);""",
    "papier": """          tl.fromTo(PIECES, { opacity: 0, y: -90, rotation: function (i) { return i % 2 ? 16 : -14; } }, { opacity: 1, y: 0, rotation: 0, duration: 0.5, stagger: 0.07, ease: "back.out(2)" }, 0.35);""",
    "plan": """          STROKES.forEach(function (e, i) { tl.fromTo(e, { strokeDashoffset: e.dataset.l || 0 }, { strokeDashoffset: 0, duration: 0.8, ease: "power1.inOut" }, 0.3 + i * 0.05); });""",
    "pate": """          tl.fromTo(PIECES, { scale: 0 }, { scale: 1, duration: 0.7, stagger: 0.08, ease: "elastic.out(1, 0.5)" }, 0.4);""",
    "neon": """          STROKES.forEach(function (e, i) { tl.fromTo(e, { strokeDashoffset: e.dataset.l || 0 }, { strokeDashoffset: 0, duration: 0.6, ease: "power2.out" }, 0.3 + i * 0.04); });
          [0.95, 1.02, 1.1].forEach(function (t, i) { tl.to(ART, { opacity: i % 2 ? 1 : 0.3, duration: 0.03 }, t); });""",
    "aquarelle": """          tl.fromTo(ART, { opacity: 0, scale: 0.92, filter: "blur(2vmin)" }, { opacity: 1, scale: 1, filter: "blur(0vmin)", duration: 1.1, ease: "power2.out" }, 0.3);""",
    "pixel": """          tl.fromTo(PIECES, { opacity: 0 }, { opacity: 1, duration: 0.2, stagger: 0.05, ease: "steps(3)" }, 0.3);""",
    "isometrique": """          tl.fromTo(PIECES, { opacity: 0, y: 70 }, { opacity: 1, y: 0, duration: 0.55, stagger: 0.07, ease: "back.out(1.6)" }, 0.3);""",
    "mosaique": """          tl.fromTo(PIECES, { opacity: 0, rotationY: 90 }, { opacity: 1, rotationY: 0, duration: 0.45, stagger: 0.05, ease: "power2.out" }, 0.5);""",
    "encre": """          STROKES.forEach(function (e, i) { tl.fromTo(e, { strokeDashoffset: e.dataset.l || 0 }, { strokeDashoffset: 0, duration: 0.7, ease: "power2.inOut" }, 0.2 + i * 0.06); });""",
    "relief": """          tl.fromTo(ART, { opacity: 0, rotationY: -50, scale: 0.7 }, { opacity: 1, rotationY: 0, scale: 1, duration: 0.9, ease: "power3.out" }, 0.3);""",
}

READ = """function V(id) {
          var out = {}, root = document.getElementById(id);
          try { JSON.parse(root.getAttribute("data-composition-variables")).forEach(function (d) { out[d.id] = d.default; }); } catch (e) {}
          var hf = window.__hyperframes;
          var o = hf && typeof hf.getVariables === "function" ? hf.getVariables() : window.__hfVariables;
          if (o && typeof o === "object") { for (var k in o) { if (o[k] !== undefined) out[k] = o[k]; } }
          return out;
        }"""

# titre découpé en lettres (mots insécables) ; taille selon la longueur
SPLIT = """        const T = String(v.text || ""), host = document.querySelector(r + ".hk-t");
        T.split(" ").forEach(function (w, wi) {
          const ws = document.createElement("span"); ws.className = "wd";
          Array.from(w).forEach(function (c) { const s = document.createElement("span"); s.className = "ch"; s.textContent = c; ws.appendChild(s); });
          host.appendChild(ws); if (wi < T.split(" ").length - 1) host.appendChild(document.createTextNode(" "));
        });
        const LW = Math.max.apply(null, T.split(" ").map(function (w) { return w.length; }).concat([1]));  // le mot le plus long tient dans la largeur
        host.style.fontSize = Math.max(5, Math.min(15, 150 / Math.max(6, T.length * 0.95), 82 / (0.74 * LW))) + "vmin";
        const CH = document.querySelectorAll(r + ".ch");
        const EXIT = Math.max(1.2, D - 0.45);"""
EXIT = """        tl.fromTo(r + ".hk", { clipPath: "inset(0% 0% 0% 0%)" }, { clipPath: "inset(0% 0% 100% 0%)", duration: 0.42, ease: "power3.in" }, EXIT);"""


def scope(css, name):
    """Chaque règle du style est préfixée par #<bloc> : rien ne déborde sur la vidéo qui monte le bloc."""
    import re
    return re.sub(r"(^|\})(\s*)([^{}@]+?)\s*\{",
                  lambda m: m.group(1) + m.group(2) + ", ".join(f"#{name} {x.strip()}" for x in m.group(3).split(",")) + " {", css)


def hook(style, desc, defaults, deco, css, js):
    name = f"accroche-{style}"
    css = scope(css, name)
    vars_ = [{"id": "text", "type": "string", "label": "Titre (2 à 6 mots)", "default": "Votre titre ici"},
             {"id": "sub", "type": "string", "label": "Petite ligne", "default": ""},
             {"id": "accent", "type": "color", "label": "Accent", "default": defaults["accent"]},
             {"id": "bg", "type": "color", "label": "Fond", "default": defaults["bg"]},
             {"id": "ink", "type": "color", "label": "Encre", "default": defaults["ink"]},
             {"id": "font", "type": "string", "label": "Police", "default": "Inter"},
             {"id": "art", "type": "string", "label": "Dessin du sujet (SVG, facultatif)", "default": ""},
             {"id": "dur", "type": "number", "label": "Durée (s, remplie automatiquement)", "default": 0, "min": 0, "max": 10}]
    decl = json.dumps(vars_, ensure_ascii=False).replace("'", "&#39;")
    return f"""<!-- deeplo-library-block: {name} · {desc} -->
<!doctype html>
<html lang="fr">
  <head>
    <meta charset="UTF-8" />
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.15.0/dist/gsap.min.js"></script>
  </head>
  <body>
    <div id="{name}" data-composition-id="{name}" data-start="0" data-duration="{DUR}" data-width="1080" data-height="1920"
      data-composition-variables='{decl}'>
      <div class="hk">
{deco}
        <div class="hk-art"></div>
        <div class="hk-box"><div class="hk-t"></div><div class="hk-s" data-var-text="sub"></div></div>
      </div>
      <style>
        #{name} {{ position: absolute; inset: 0; font-family: var(--font, "Inter"), "Inter", sans-serif; }}
        #{name} .hk {{ position: absolute; inset: 0; overflow: hidden; background: var(--bg); color: var(--ink); }}
        #{name} .hk-box {{ position: absolute; left: 7vmin; right: 7vmin; top: 50%; transform: translateY(-50%); text-align: center; z-index: 5; }}
        #{name} .hk-t {{ font-weight: 900; line-height: 1.02; letter-spacing: -0.02em; }}
        #{name} .hk-t .wd {{ display: inline-block; white-space: nowrap; }}
        #{name} .hk-t .ch {{ display: inline-block; }}
        #{name} .hk-s {{ margin-top: 3vmin; font-size: 4.4vmin; font-weight: 600; opacity: 0; overflow-wrap: anywhere; }}
        #{name} .hk-art {{ position: absolute; left: 12%; right: 12%; top: 40%; height: 44%; z-index: 4; display: none; }}
        #{name} .hk-art svg {{ width: 100%; height: 100%; overflow: visible; }}
        #{name} .hk-art svg > * {{ transform-box: fill-box; transform-origin: 50% 50%; }}
        #{name} .hk.has-art .hk-box {{ top: 22%; }}
{css}
      </style>
      <script>
        (function () {{
        {READ}
        const v = V("{name}");
        const r = '[data-composition-id="{name}"] ';
        const tl = gsap.timeline({{ paused: true }});
        const D = Number(v.dur) > 0 ? Number(v.dur) : {DUR};
{SPLIT}
        // dessin du sujet (variable "art" : SVG écrit par Claude dans le style) : la mise en page lui fait de la place
        const ART = document.querySelector(r + ".hk-art");
        let PIECES = [], STROKES = [];
        if (v.art) {{
          ART.innerHTML = String(v.art); ART.style.display = "block"; document.querySelector(r + ".hk").classList.add("has-art");
          const sv = ART.querySelector("svg"); if (sv) {{ sv.removeAttribute("width"); sv.removeAttribute("height"); }}
          PIECES = Array.from(ART.querySelectorAll("svg > *"));
          STROKES = Array.from(ART.querySelectorAll("path, line, polyline, polygon, circle, ellipse, rect"));
          STROKES.forEach(function (e) {{ try {{ const L = e.getTotalLength(); e.style.strokeDasharray = L; e.dataset.l = L; }} catch (x) {{}} }});
        }}
{js}
        if (PIECES.length) {{
{ART_ANIM.get(style, ART_ANIM["_"])}
        }}
        tl.fromTo(r + ".hk-s", {{ opacity: 0, y: 14 }}, {{ opacity: 1, y: 0, duration: 0.4, ease: "power2.out" }}, Math.min(1.2, D * 0.4));
{EXIT}
        window.__timelines = window.__timelines || {{}};
        window.__timelines["{name}"] = tl;
        }})();
      </script>
    </div>
  </body>
</html>
"""


H = {}
H["papier"] = hook("papier", "papier découpé : couches de papier qui montent, lettres en papier qui se posent",
    {"accent": "#e4572e", "bg": "#f3ead8", "ink": "#2b2118"},
    """        <i class="pl p1"></i><i class="pl p2"></i><i class="pl p3"></i>""",
    """        .pl { position: absolute; left: -20%; width: 140%; height: 60%; border-radius: 50% 50% 0 0 / 22% 22% 0 0; box-shadow: 0 -1.2vmin 2.4vmin rgba(0,0,0,.18); }
        .p1 { bottom: -18%; background: var(--accent); }
        .p2 { bottom: -30%; background: color-mix(in srgb, var(--accent) 55%, var(--bg)); left: -40%; }
        .p3 { bottom: -42%; background: color-mix(in srgb, var(--accent) 30%, var(--ink)); left: -5%; }
        .hk-t .ch { text-shadow: 0.5vmin 0.6vmin 0 rgba(0,0,0,.22); }""",
    """        tl.fromTo(r + ".pl", { y: "60%" }, { y: "0%", duration: 0.8, stagger: 0.12, ease: "back.out(1.4)" }, 0);
        CH.forEach(function (c, i) {
          tl.fromTo(c, { opacity: 0, y: -60, rotation: (i % 2 ? 14 : -12) }, { opacity: 1, y: 0, rotation: (i % 3 - 1) * 3, duration: 0.45, ease: "back.out(2.2)" }, 0.25 + i * 0.035);
        });""")
H["plan"] = hook("plan", "plan technique (blueprint) : grille qui se trace, titre au trait puis rempli, cote et repères d'angle",
    {"accent": "#ffd166", "bg": "#0f3b8c", "ink": "#ffffff"},
    """        <i class="grid"></i><i class="cn c1"></i><i class="cn c2"></i><i class="cn c3"></i><i class="cn c4"></i>
        <div class="cote"><i class="cl"></i><span>1 : 50</span></div>""",
    """        .grid { position: absolute; inset: 0; background-image: linear-gradient(rgba(255,255,255,.14) 1px, transparent 1px),
                linear-gradient(90deg, rgba(255,255,255,.14) 1px, transparent 1px), linear-gradient(rgba(255,255,255,.06) 1px, transparent 1px),
                linear-gradient(90deg, rgba(255,255,255,.06) 1px, transparent 1px);
                background-size: 12vmin 12vmin, 12vmin 12vmin, 3vmin 3vmin, 3vmin 3vmin; transform-origin: 0 0; }
        .cn { position: absolute; width: 8vmin; height: 8vmin; border: 0.5vmin solid var(--ink); opacity: 0; }
        .c1 { left: 5vmin; top: 5vmin; border-right: 0; border-bottom: 0; } .c2 { right: 5vmin; top: 5vmin; border-left: 0; border-bottom: 0; }
        .c3 { left: 5vmin; bottom: 5vmin; border-right: 0; border-top: 0; } .c4 { right: 5vmin; bottom: 5vmin; border-left: 0; border-top: 0; }
        .hk-t { color: transparent; -webkit-text-stroke: 0.35vmin var(--ink); font-family: monospace; text-transform: uppercase; letter-spacing: 0.04em; }
        .cote { position: absolute; left: 12vmin; right: 12vmin; top: 64%; text-align: center; font: 600 3.2vmin monospace; color: var(--accent); }
        .cote .cl { display: block; height: 0.4vmin; background: var(--accent); margin-bottom: 1.6vmin; transform-origin: 50% 50%; }
        .hk-s { color: var(--accent); font-family: monospace; text-transform: uppercase; letter-spacing: .12em; }
        .hk.has-art .cote { display: none; }""",
    """        tl.fromTo(r + ".grid", { scaleY: 0 }, { scaleY: 1, duration: 0.7, ease: "power2.inOut" }, 0);
        tl.fromTo(r + ".cn", { opacity: 0, scale: 1.6 }, { opacity: 1, scale: 1, duration: 0.35, stagger: 0.06, ease: "power2.out" }, 0.3);
        tl.fromTo(CH, { opacity: 0 }, { opacity: 1, duration: 0.05, stagger: 0.04 }, 0.4);
        tl.to(r + ".hk-t", { color: "rgba(255,255,255,.95)", duration: 0.5, ease: "power1.in" }, 0.4 + CH.length * 0.04);
        tl.fromTo(r + ".cote .cl", { scaleX: 0 }, { scaleX: 1, duration: 0.5, ease: "power3.out" }, 0.9);
        tl.fromTo(r + ".cote span", { opacity: 0 }, { opacity: 1, duration: 0.3 }, 1.2);""")
H["pate"] = hook("pate", "pâte à modeler : formes molles qui rebondissent, lettres épaisses qui s'écrasent en tombant",
    {"accent": "#ff7a59", "bg": "#ffe9c7", "ink": "#3b2a6e"},
    """        <i class="bl b1"></i><i class="bl b2"></i><i class="bl b3"></i>""",
    """        .bl { position: absolute; border-radius: 42% 58% 63% 37% / 41% 44% 56% 59%; box-shadow: inset -2vmin -2.5vmin 0 rgba(0,0,0,.12), inset 1.5vmin 1.5vmin 0 rgba(255,255,255,.35); }
        .b1 { width: 40vmin; height: 34vmin; left: -8vmin; top: 12%; background: var(--accent); }
        .b2 { width: 30vmin; height: 30vmin; right: -6vmin; top: 22%; background: #7bd389; }
        .b3 { width: 48vmin; height: 36vmin; left: 22%; bottom: 6%; background: #8ec5ff; }
        .hk-t { color: var(--ink); text-shadow: 0 0.9vmin 0 color-mix(in srgb, var(--ink) 60%, #000), 0 1.6vmin 2vmin rgba(0,0,0,.18); }
        .hk-t .ch { transform-origin: 50% 100%; }
        .hk.has-art .b3 { display: none; }""",
    """        tl.fromTo(r + ".bl", { scale: 0 }, { scale: 1, duration: 0.7, stagger: 0.1, ease: "elastic.out(1, 0.5)" }, 0);
        tl.to(r + ".bl", { borderRadius: "58% 42% 37% 63% / 59% 56% 44% 41%", duration: 1.2, yoyo: true, repeat: 1, ease: "sine.inOut" }, 0.6);
        CH.forEach(function (c, i) {
          const t = 0.3 + i * 0.04;
          tl.fromTo(c, { y: -120, scaleY: 1.3, scaleX: 0.8, opacity: 0 }, { y: 0, scaleY: 1, scaleX: 1, opacity: 1, duration: 0.35, ease: "power2.in" }, t);
          tl.to(c, { scaleY: 0.72, scaleX: 1.2, duration: 0.08, yoyo: true, repeat: 1, ease: "power1.out" }, t + 0.35);
        });""")
H["neon"] = hook("neon", "néon synthwave : soleil rayé qui se lève, sol quadrillé qui avance, titre néon qui clignote",
    {"accent": "#ff3cac", "bg": "#160033", "ink": "#ffffff"},
    """        <i class="sky"></i><i class="sun"></i><div class="floor"><i class="fg"></i></div>""",
    """        .sky { position: absolute; inset: 0; background: linear-gradient(#0c0024 0%, var(--bg) 55%, #3a0a5c 100%); }
        .sun { position: absolute; left: 50%; top: 18%; width: 56vmin; height: 56vmin; margin-left: -28vmin; border-radius: 50%;
               background: linear-gradient(#ffe66d, var(--accent));
               -webkit-mask: repeating-linear-gradient(transparent 0 58%, #000 58% 100%) , linear-gradient(#000 0 52%, transparent 52%);
               -webkit-mask: linear-gradient(#000 0 54%, transparent 54% 60%, #000 60% 66%, transparent 66% 71%, #000 71% 77%, transparent 77% 81%, #000 81% 87%, transparent 87% 90%, #000 90%);
               filter: drop-shadow(0 0 4vmin var(--accent)); }
        .floor { position: absolute; left: -50%; right: -50%; bottom: -10%; height: 50%; perspective: 40vmin; overflow: hidden; }
        .fg { position: absolute; left: 0; right: 0; top: 0; height: 300%; transform-origin: 50% 0; transform: rotateX(68deg);
              background-image: linear-gradient(var(--accent) 0.3vmin, transparent 0.3vmin), linear-gradient(90deg, var(--accent) 0.3vmin, transparent 0.3vmin);
              background-size: 10vmin 10vmin; opacity: .95; filter: drop-shadow(0 0 1vmin var(--accent)); }
        .hk-box { top: 42%; }
        .hk-t { color: #fff; text-transform: uppercase; font-style: italic;
                text-shadow: 0 0 1vmin #fff, 0 0 2.5vmin var(--accent), 0 0 6vmin var(--accent); }
        .hk-s { color: #7df9ff; text-shadow: 0 0 1.5vmin #7df9ff; letter-spacing: .2em; text-transform: uppercase; }""",
    """        tl.fromTo(r + ".sun", { y: "40vmin", opacity: 0 }, { y: 0, opacity: 1, duration: 1.0, ease: "power2.out" }, 0);
        tl.fromTo(r + ".fg", { y: 0 }, { y: "10vmin", duration: 0.5, ease: "none", repeat: Math.ceil(D / 0.5) }, 0);
        tl.fromTo(r + ".hk-t", { opacity: 0 }, { opacity: 1, duration: 0.05 }, 0.5);
        [0.58, 0.66, 0.74, 0.9].forEach(function (t, i) { tl.to(r + ".hk-t", { opacity: i % 2 ? 1 : 0.25, duration: 0.03 }, t); });
        tl.to(r + ".hk-t", { opacity: 1, duration: 0.05 }, 0.96);""")
H["aquarelle"] = hook("aquarelle", "aquarelle : taches de couleur qui diffusent sur le papier, titre qui se révèle au pinceau",
    {"accent": "#2a9d8f", "bg": "#f7f2e8", "ink": "#264653"},
    """        <i class="wc w1"></i><i class="wc w2"></i><i class="wc w3"></i><i class="grainp"></i>""",
    """        .wc { position: absolute; border-radius: 50%; filter: blur(3.5vmin); mix-blend-mode: multiply; }
        .w1 { width: 70vmin; height: 60vmin; left: -10vmin; top: 18%; background: radial-gradient(circle, color-mix(in srgb, var(--accent) 70%, transparent) 0%, transparent 70%); }
        .w2 { width: 60vmin; height: 70vmin; right: -14vmin; top: 34%; background: radial-gradient(circle, rgba(233,196,106,.75) 0%, transparent 70%); }
        .w3 { width: 64vmin; height: 50vmin; left: 18%; top: 52%; background: radial-gradient(circle, rgba(231,111,81,.55) 0%, transparent 70%); }
        .grainp { position: absolute; inset: 0; opacity: .25; background-image: radial-gradient(rgba(0,0,0,.08) 1px, transparent 1px); background-size: 0.6vmin 0.6vmin; }
        .hk-t { color: var(--ink); font-weight: 800; }
        .hk-s { font-style: italic; }""",
    """        tl.fromTo(r + ".wc", { scale: 0.2, opacity: 0 }, { scale: 1, opacity: 1, duration: 1.4, stagger: 0.18, ease: "power2.out" }, 0);
        tl.fromTo(r + ".hk-t", { clipPath: "inset(0% 100% 0% 0%)" }, { clipPath: "inset(0% 0% 0% 0%)", duration: 0.9, ease: "power2.inOut" }, 0.45);""")
H["pixel"] = hook("pixel", "pixel art : étoiles qui clignotent, lettres qui apparaissent par à-coups avec ombre en blocs",
    {"accent": "#ffcd1f", "bg": "#1b1b3a", "ink": "#ffffff"},
    """        <i class="px s1"></i><i class="px s2"></i><i class="px s3"></i><i class="px s4"></i><i class="px s5"></i><i class="ground"></i>""",
    """        .px { position: absolute; width: 1.6vmin; height: 1.6vmin; background: #fff; }
        .s1 { left: 14%; top: 14%; } .s2 { left: 78%; top: 20%; } .s3 { left: 30%; top: 30%; } .s4 { left: 64%; top: 70%; } .s5 { left: 22%; top: 76%; }
        .ground { position: absolute; left: 0; right: 0; bottom: 0; height: 14%; background:
                  repeating-linear-gradient(90deg, #3ec15b 0 6vmin, #2fa34a 6vmin 12vmin); box-shadow: 0 -2vmin 0 #2fa34a; }
        .hk-t { color: var(--ink); text-transform: uppercase; letter-spacing: 0.06em; text-shadow: 0.9vmin 0.9vmin 0 var(--accent), 1.8vmin 1.8vmin 0 rgba(0,0,0,.35); }
        .hk-s { color: var(--accent); text-transform: uppercase; letter-spacing: .1em; }""",
    """        tl.fromTo(r + ".px", { opacity: 0 }, { opacity: 1, duration: 0.3, ease: "steps(3)", stagger: { each: 0.2, repeat: Math.ceil(D / 1.2), yoyo: true } }, 0);
        tl.fromTo(r + ".ground", { y: "100%" }, { y: "0%", duration: 0.4, ease: "steps(4)" }, 0.1);
        tl.fromTo(CH, { opacity: 0, y: -30 }, { opacity: 1, y: 0, duration: 0.2, ease: "steps(3)", stagger: 0.05 }, 0.35);""")
H["isometrique"] = hook("isometrique", "isométrique : blocs en perspective qui montent comme des immeubles, titre posé au-dessus",
    {"accent": "#4361ee", "bg": "#eef1f8", "ink": "#14213d"},
    """        <div class="iso">""" + "".join(f'<i class="pr q{k}"><b></b></i>' for k in range(6)) + """</div>""",
    """        .iso { position: absolute; left: 50%; top: 66%; width: 0; height: 0; }
        .pr { position: absolute; width: 14vmin; bottom: 0; height: 30vmin; transform-origin: 50% 100%;
              background: linear-gradient(90deg, color-mix(in srgb, var(--accent) 80%, #000) 0 50%, var(--accent) 50% 100%); }
        .pr b { position: absolute; left: 0; top: -4vmin; width: 14vmin; height: 8vmin; background: color-mix(in srgb, var(--accent) 45%, #fff);
                clip-path: polygon(50% 0, 100% 50%, 50% 100%, 0 50%); }
        .q0 { left: -40vmin; height: 18vmin; } .q1 { left: -26vmin; height: 30vmin; } .q2 { left: -12vmin; height: 42vmin; }
        .q3 { left: 2vmin; height: 26vmin; } .q4 { left: 16vmin; height: 36vmin; } .q5 { left: 30vmin; height: 20vmin; }
        .hk-box { top: 24%; }
        .hk-t { color: var(--ink); }""",
    """        tl.fromTo(r + ".pr", { scaleY: 0 }, { scaleY: 1, duration: 0.6, stagger: 0.08, ease: "back.out(1.6)" }, 0.1);
        tl.fromTo(CH, { opacity: 0, y: 30 }, { opacity: 1, y: 0, duration: 0.4, stagger: 0.03, ease: "power3.out" }, 0.5);""")
H["mosaique"] = hook("mosaique", "mosaïque : carreaux qui se retournent depuis le centre, titre sur un bandeau",
    {"accent": "#e63946", "bg": "#1d3557", "ink": "#ffffff"},
    """        <div class="mz">""" + "".join(f'<i class="tl t{k}"></i>' for k in range(8 * 14)) + """</div><i class="band"></i>""",
    """        .mz { position: absolute; inset: 0; display: grid; grid-template-columns: repeat(8, 1fr); grid-template-rows: repeat(14, 1fr); gap: 0.5vmin; padding: 0.5vmin; perspective: 80vmin; }
        .mz .tl { background: var(--accent); border-radius: 0.6vmin; }
        .mz .tl:nth-child(3n) { background: #f1faee; } .mz .tl:nth-child(4n+1) { background: #a8dadc; } .mz .tl:nth-child(5n+2) { background: #457b9d; }
        .band { position: absolute; left: 0; right: 0; top: 50%; height: 30vmin; margin-top: -15vmin; background: var(--bg); transform-origin: 50% 50%; }
        .hk-t { color: var(--ink); } .hk-s { color: #a8dadc; }""",
    """        tl.fromTo(r + ".mz .tl", { rotationY: 90, opacity: 0 }, { rotationY: 0, opacity: 1, duration: 0.45, ease: "power2.out", stagger: { each: 0.006, from: "center", grid: [14, 8] } }, 0);
        tl.fromTo(r + ".band", { scaleY: 0 }, { scaleY: 1, duration: 0.4, ease: "power3.inOut" }, 0.7);
        tl.fromTo(CH, { opacity: 0, rotationX: -90 }, { opacity: 1, rotationX: 0, duration: 0.35, stagger: 0.03, ease: "back.out(2)" }, 0.95);""")
H["encre"] = hook("encre", "encre de Chine : grand coup de pinceau qui se trace, titre qui se dépose, sceau rouge",
    {"accent": "#c1121f", "bg": "#f4efe4", "ink": "#111111"},
    """        <svg class="brush" viewBox="0 0 1000 400" preserveAspectRatio="none"><defs><filter id="rough" filterUnits="userSpaceOnUse" x="-100" y="-300" width="1200" height="1000"><feTurbulence type="fractalNoise" baseFrequency="0.04" numOctaves="3" />
          <feDisplacementMap in="SourceGraphic" scale="22" /></filter></defs>
          <path d="M 60 215 C 300 175, 650 245, 940 190" pathLength="1000" /></svg><i class="seal"></i>""",
    """        .brush { position: absolute; left: 0; width: 100%; top: 54%; height: 18%; overflow: visible; }
        .brush path { fill: none; stroke: var(--ink); stroke-width: 70; stroke-linecap: round; filter: url(#rough); stroke-dasharray: 1000; opacity: .9; }
        .seal { position: absolute; right: 12vmin; bottom: 22%; width: 13vmin; height: 13vmin; background: var(--accent); border-radius: 1.2vmin;
                box-shadow: inset 0 0 0 1vmin color-mix(in srgb, var(--accent) 70%, #fff); opacity: 0; }
        .hk-box { top: 44%; } .hk-t { color: var(--ink); }
        .hk-s { color: var(--ink); margin-top: 14vmin; letter-spacing: .3em; }""",
    """        tl.fromTo(r + ".brush path", { attr: { "stroke-dashoffset": 1000 } }, { attr: { "stroke-dashoffset": 0 }, duration: 0.8, ease: "power2.inOut" }, 0.05);
        tl.fromTo(CH, { opacity: 0, filter: "blur(1.5vmin)" }, { opacity: 1, filter: "blur(0vmin)", duration: 0.5, stagger: 0.03, ease: "power2.out" }, 0.55);
        tl.fromTo(r + ".seal", { opacity: 0, scale: 2.2, rotation: -20 }, { opacity: 1, scale: 1, rotation: -6, duration: 0.3, ease: "back.out(2)" }, 1.3);""")
H["relief"] = hook("relief", "relief 3D : titre extrudé qui pivote dans la lumière, faisceau qui le balaie",
    {"accent": "#f72585", "bg": "#0b0b12", "ink": "#ffffff"},
    """        <i class="spot"></i>""",
    """        .hk { perspective: 120vmin; background: radial-gradient(ellipse 80% 60% at 50% 45%, color-mix(in srgb, var(--accent) 28%, var(--bg)) 0%, var(--bg) 70%); }
        .spot { position: absolute; top: -20%; left: -40%; width: 40%; height: 140%; transform: rotate(16deg); background: linear-gradient(90deg, transparent, rgba(255,255,255,.12), transparent); }
        .hk-box { transform-style: preserve-3d; }
        .hk-t { color: var(--ink); text-transform: uppercase;
                text-shadow: 0 0.3vmin 0 color-mix(in srgb, var(--accent) 90%, #000), 0 0.6vmin 0 color-mix(in srgb, var(--accent) 80%, #000),
                             0 0.9vmin 0 color-mix(in srgb, var(--accent) 70%, #000), 0 1.2vmin 0 color-mix(in srgb, var(--accent) 60%, #000),
                             0 1.5vmin 0 color-mix(in srgb, var(--accent) 50%, #000), 0 1.8vmin 0 color-mix(in srgb, var(--accent) 40%, #000),
                             0 3vmin 4vmin rgba(0,0,0,.6); }
        .hk-s { color: var(--accent); letter-spacing: .2em; text-transform: uppercase; }""",
    """        tl.fromTo(r + ".hk-t", { rotationX: 70, rotationY: -30, opacity: 0, scale: 0.7 }, { rotationX: 12, rotationY: 0, opacity: 1, scale: 1, duration: 0.9, ease: "power3.out" }, 0.1);
        tl.to(r + ".hk-t", { rotationY: 10, rotationX: 6, duration: D - 1.2, ease: "sine.inOut" }, 1.0);
        tl.fromTo(r + ".spot", { x: 0 }, { x: "260%", duration: 1.6, ease: "power1.inOut" }, 0.4);""")

for style, html in H.items():
    d = LIB / f"accroche-{style}"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"accroche-{style}.html").write_text(html, encoding="utf-8")
print(len(H), "accroches écrites :", ", ".join(H))

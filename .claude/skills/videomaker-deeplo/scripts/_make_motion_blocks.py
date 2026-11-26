"""Génère les blocs de motion design de la bibliothèque (library/block/<nom>/<nom>.html). Relancer après modification ; puis library.py save pour l'aperçu."""
import json
from pathlib import Path

LIB = Path(__file__).resolve().parents[4] / "library" / "block"
PIX = "data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw=="

COMMON = [
    {"id": "accent", "type": "color", "label": "Accent", "default": "#c2410c"},
    {"id": "text", "type": "color", "label": "Texte", "default": "#ffffff"},
    {"id": "card", "type": "color", "label": "Fond de carte", "default": "rgba(20,18,16,0.78)"},
    {"id": "fill", "type": "color", "label": "Fond plein cadre (transparent en surimpression)", "default": "transparent"},
    {"id": "font", "type": "string", "label": "Police", "default": "Inter"},
    {"id": "top", "type": "number", "label": "Hauteur (% du cadre)", "default": 40, "min": 0, "max": 90},
    {"id": "dur", "type": "number", "label": "Durée du montage (s, remplie automatiquement)", "default": 0, "min": 0, "max": 60},
]

READ = """function V(id) {
          var out = {}, root = document.getElementById(id);
          try { JSON.parse(root.getAttribute("data-composition-variables")).forEach(function (d) { out[d.id] = d.default; }); } catch (e) {}
          var hf = window.__hyperframes;
          var o = hf && typeof hf.getVariables === "function" ? hf.getVariables() : window.__hfVariables;
          if (o && typeof o === "object") { for (var k in o) { if (o[k] !== undefined) out[k] = o[k]; } }
          return out;
        }"""


def block(name, desc, dur, extra_vars, html_body, css, js):
    vars_ = COMMON + extra_vars
    decl = json.dumps(vars_, ensure_ascii=False).replace("'", "&#39;")
    return f"""<!-- deeplo-library-block: {name} · {desc} -->
<!doctype html>
<html lang="fr">
  <head>
    <meta charset="UTF-8" />
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.15.0/dist/gsap.min.js"></script>
  </head>
  <body>
    <div id="{name}" data-composition-id="{name}" data-start="0" data-duration="{dur}" data-width="1080" data-height="1920"
      data-composition-variables='{decl}'>
      <div class="mf-fill"></div>
{html_body}
      <style>
        #{name} {{ position: absolute; inset: 0; font-family: var(--font, "Inter"), "Inter", sans-serif; color: var(--text, #fff); }}
        #{name} .mf-fill {{ position: absolute; inset: 0; background: var(--fill, transparent); }}
        #{name} .mf-pos {{ position: absolute; left: 0; right: 0; top: calc(var(--top, 40) * 1%); display: flex; justify-content: center; }}
{css}
      </style>
      <script>
        (function () {{
        {READ}
        const v = V("{name}");
        const r = '[data-composition-id="{name}"] ';
        const tl = gsap.timeline({{ paused: true }});
        const D = Number(v.dur) > 0 ? Number(v.dur) : {dur};
        const K = Math.min(1, D / {dur});  // tout se resserre si le bloc est monté plus court que prévu
{js}
        window.__timelines = window.__timelines || {{}};
        window.__timelines["{name}"] = tl;
        }})();
      </script>
    </div>
  </body>
</html>
"""


B = {}

B["compteur"] = block(
    "compteur", "nombre qui compte jusqu'à sa valeur (préfixe, suffixe, décimales), légende ; ex. +250 clients", 3.2,
    [{"id": "from", "type": "number", "label": "Départ", "default": 0},
     {"id": "to", "type": "number", "label": "Valeur", "default": 250},
     {"id": "decimals", "type": "number", "label": "Décimales", "default": 0, "min": 0, "max": 2},
     {"id": "prefix", "type": "string", "label": "Préfixe", "default": "+"},
     {"id": "suffix", "type": "string", "label": "Suffixe", "default": ""},
     {"id": "label", "type": "string", "label": "Légende", "default": "clients satisfaits"}],
    """      <div class="mf-pos"><div class="ct-card">
        <div class="ct-num"><span class="ct-pre" data-var-text="prefix">+</span><span class="ct-val">0</span><span class="ct-suf" data-var-text="suffix"></span></div>
        <div class="ct-lbl" data-var-text="label">clients satisfaits</div></div></div>""",
    """        #compteur .ct-card { padding: 3vmin 6vmin 3.4vmin; border-radius: 3vmin; background: var(--card); text-align: center; opacity: 0;
                              box-shadow: 0 2vmin 6vmin rgba(0,0,0,.25); }
        #compteur .ct-num { font-size: 19vmin; font-weight: 800; line-height: 1; color: var(--accent); font-variant-numeric: tabular-nums; letter-spacing: -0.02em; }
        #compteur .ct-lbl { font-size: 4.4vmin; font-weight: 600; margin-top: 1.2vmin; opacity: 0; }""",
    """        const el = document.querySelector(r + ".ct-val"), o = { n: Number(v.from) || 0 };
        const dec = Math.max(0, Math.min(2, Number(v.decimals) || 0)), to = Number(v.to) || 0;
        const fmt = function (n) { return n.toLocaleString("fr-BE", { minimumFractionDigits: dec, maximumFractionDigits: dec }); };
        el.textContent = fmt(o.n);
        tl.fromTo(r + ".ct-card", { y: 40, scale: 0.9 }, { y: 0, scale: 1, duration: 0.5, ease: "back.out(1.8)" }, 0);
        tl.fromTo(r + ".ct-card", { opacity: 0 }, { opacity: 1, duration: 0.1 }, 0);  // opaque tout de suite : contraste
        tl.to(o, { n: to, duration: Math.min(1.6, D * 0.45), ease: "power2.out", onUpdate: function () { el.textContent = fmt(o.n); } }, 0.25 * K);
        tl.fromTo(r + ".ct-num", { scale: 1 }, { scale: 1.08, duration: 0.14, yoyo: true, repeat: 1, ease: "power1.inOut" }, 0.25 + Math.min(1.6, D * 0.45));
        tl.fromTo(r + ".ct-lbl", { opacity: 0, y: 12 }, { opacity: 1, y: 0, duration: 0.4 }, 0.6 * K);
        tl.to(r + ".ct-card", { opacity: 0, y: -24, duration: 0.3, ease: "power2.in" }, D - 0.35);""")

B["note-etoiles"] = block(
    "note-etoiles", "note sur 5 : étoiles qui se remplissent jusqu'à la note réelle, nombre d'avis", 3.4,
    [{"id": "rating", "type": "number", "label": "Note (sur 5)", "default": 4.9, "min": 0, "max": 5},
     {"id": "count", "type": "string", "label": "Nombre d'avis + source", "default": "127 avis Google"}],
    """      <div class="mf-pos"><div class="st-card">
        <div class="st-row"><span class="st-score">4,9</span><span class="st-stars"></span></div>
        <div class="st-count" data-var-text="count">127 avis Google</div></div></div>""",
    """        #note-etoiles .st-card { padding: 3vmin 5vmin; border-radius: 3vmin; background: var(--card); opacity: 0; text-align: center;
                                  box-shadow: 0 2vmin 6vmin rgba(0,0,0,.25); }
        #note-etoiles .st-row { display: flex; align-items: center; gap: 3vmin; }
        #note-etoiles .st-score { font-size: 13vmin; font-weight: 800; line-height: 1; }
        #note-etoiles .st-stars { display: flex; gap: 1vmin; }
        #note-etoiles .st-star { position: relative; width: 8vmin; height: 8vmin; }
        #note-etoiles .st-star svg { position: absolute; inset: 0; width: 100%; height: 100%; }
        #note-etoiles .st-on { clip-path: inset(0 100% 0 0); }
        #note-etoiles .st-count { font-size: 4vmin; margin-top: 1.6vmin; opacity: 0; }""",
    """        const P = "M12 2l2.9 6.6 7.1.6-5.4 4.7 1.6 7L12 17.3 5.8 20.9l1.6-7L2 9.2l7.1-.6z";
        const rating = Math.max(0, Math.min(5, Number(v.rating) || 0));
        document.querySelector(r + ".st-score").textContent = rating.toLocaleString("fr-BE", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
        const box = document.querySelector(r + ".st-stars");
        for (let i = 0; i < 5; i++) {
          box.insertAdjacentHTML("beforeend", '<span class="st-star"><svg viewBox="0 0 24 24"><path d="' + P + '" fill="rgba(255,255,255,.22)"/></svg>' +
            '<svg class="st-on" viewBox="0 0 24 24"><path d="' + P + '" fill="#FFC527"/></svg></span>');
        }
        tl.fromTo(r + ".st-card", { y: 40, scale: 0.9 }, { y: 0, scale: 1, duration: 0.5, ease: "back.out(1.8)" }, 0);
        tl.fromTo(r + ".st-card", { opacity: 0 }, { opacity: 1, duration: 0.1 }, 0);  // opaque tout de suite : contraste
        document.querySelectorAll(r + ".st-on").forEach(function (el, i) {
          const part = Math.max(0, Math.min(1, rating - i));
          if (part > 0) tl.fromTo(el, { clipPath: "inset(0 100% 0 0)" }, { clipPath: "inset(0 " + (100 - part * 100) + "% 0 0)", duration: 0.22, ease: "power1.out" }, (0.4 + i * 0.16) * K);
          if (part > 0) tl.fromTo(el.parentNode, { scale: 1 }, { scale: 1.18, duration: 0.11, yoyo: true, repeat: 1 }, (0.4 + i * 0.16) * K);
        });
        tl.fromTo(r + ".st-count", { opacity: 0, y: 10 }, { opacity: 1, y: 0, duration: 0.4 }, 1.3 * K);
        tl.to(r + ".st-card", { opacity: 0, y: -24, duration: 0.3, ease: "power2.in" }, D - 0.35);""")

B["jauge"] = block(
    "jauge", "anneau qui se remplit jusqu'à un pourcentage, chiffre au centre, légende", 3.2,
    [{"id": "value", "type": "number", "label": "Pourcentage", "default": 92, "min": 0, "max": 100},
     {"id": "label", "type": "string", "label": "Légende", "default": "de clients satisfaits"}],
    """      <div class="mf-pos"><div class="jg-card">
        <div class="jg-ring"><svg viewBox="0 0 120 120"><circle cx="60" cy="60" r="52" class="jg-bg"/><circle cx="60" cy="60" r="52" class="jg-fg"/></svg>
        <div class="jg-val">0 %</div></div><div class="jg-lbl" data-var-text="label">de clients satisfaits</div></div></div>""",
    """        #jauge .jg-card { padding: 3vmin 5vmin 3.4vmin; border-radius: 3vmin; background: var(--card); text-align: center; opacity: 0;
                           box-shadow: 0 2vmin 6vmin rgba(0,0,0,.25); }
        #jauge .jg-ring { position: relative; width: 40vmin; height: 40vmin; margin: 0 auto; }
        #jauge svg { width: 100%; height: 100%; transform: rotate(-90deg); }
        #jauge .jg-bg { fill: none; stroke: rgba(255,255,255,.16); stroke-width: 11; }
        #jauge .jg-fg { fill: none; stroke: var(--accent); stroke-width: 11; stroke-linecap: round; stroke-dasharray: 326.7; stroke-dashoffset: 326.7; }
        #jauge .jg-val { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; font-size: 11vmin; font-weight: 800; }
        #jauge .jg-lbl { font-size: 4.4vmin; font-weight: 600; margin-top: 2vmin; opacity: 0; max-width: 60vmin; }""",
    """        const val = Math.max(0, Math.min(100, Number(v.value) || 0)), el = document.querySelector(r + ".jg-val"), o = { n: 0 };
        tl.fromTo(r + ".jg-card", { y: 40, scale: 0.9 }, { y: 0, scale: 1, duration: 0.5, ease: "back.out(1.8)" }, 0);
        tl.fromTo(r + ".jg-card", { opacity: 0 }, { opacity: 1, duration: 0.1 }, 0);  // opaque tout de suite : contraste
        tl.fromTo(r + ".jg-fg", { strokeDashoffset: 326.7 }, { strokeDashoffset: 326.7 * (1 - val / 100), duration: 1.4 * K, ease: "power2.out" }, 0.3 * K);
        tl.to(o, { n: val, duration: 1.4 * K, ease: "power2.out", onUpdate: function () { el.textContent = Math.round(o.n) + " %"; } }, 0.3 * K);
        tl.fromTo(r + ".jg-lbl", { opacity: 0, y: 12 }, { opacity: 1, y: 0, duration: 0.4 }, 0.9);
        tl.to(r + ".jg-card", { opacity: 0, y: -24, duration: 0.3, ease: "power2.in" }, D - 0.35);""")

B["bouton-cta"] = block(
    "bouton-cta", "bouton d'action qui apparaît, pulse, puis un doigt le touche (onde) ; ex. Réserver", 3.0,
    [{"id": "label", "type": "string", "label": "Texte du bouton", "default": "Réserver maintenant"},
     {"id": "sub", "type": "string", "label": "Sous-texte", "default": "lien en bio"}],
    """      <div class="mf-pos"><div class="bt-wrap">
        <div class="bt-btn"><span data-var-text="label">Réserver maintenant</span><i class="bt-ripple"></i></div>
        <div class="bt-sub" data-var-text="sub">lien en bio</div>
        <svg class="bt-hand" viewBox="0 0 64 64"><path d="M26 6c-3 0-5 2-5 5v22l-4-4c-2-2-5-2-7 0s-2 5 0 7l14 15c3 3 6 5 11 5h6c8 0 14-6 14-14V30c0-3-2-5-5-5s-5 2-5 5v-2c0-3-2-5-5-5s-5 2-5 5v-1c0-3-2-5-5-5-1 0-2 0-3 1V11c0-3-2-5-5-5z" fill="#fff" stroke="#111" stroke-width="2.5"/></svg>
      </div></div>""",
    """        #bouton-cta .bt-wrap { position: relative; text-align: center; }
        #bouton-cta .bt-btn { position: relative; overflow: hidden; display: inline-block; padding: 3.4vmin 8vmin; border-radius: 99px; background: var(--accent);
                               color: #fff; font-size: 6vmin; font-weight: 800; opacity: 0; box-shadow: 0 2vmin 5vmin rgba(0,0,0,.3); }
        #bouton-cta .bt-ripple { position: absolute; left: 50%; top: 50%; width: 10vmin; height: 10vmin; margin: -5vmin 0 0 -5vmin; border-radius: 50%;
                                  background: rgba(255,255,255,.55); transform: scale(0); opacity: 0; }
        #bouton-cta .bt-sub { display: inline-block; font-size: 4vmin; margin-top: 2.4vmin; opacity: 0; padding: .3em .9em; border-radius: 99px;
                               background: var(--card); color: var(--text); }
        #bouton-cta .bt-hand { position: absolute; width: 14vmin; height: 14vmin; left: 55%; top: 55%; opacity: 0; }""",
    """        tl.fromTo(r + ".bt-btn", { opacity: 0, scale: 0.6 }, { opacity: 1, scale: 1, duration: 0.5, ease: "back.out(2.2)" }, 0);
        tl.fromTo(r + ".bt-sub", { opacity: 0, y: 10 }, { opacity: 1, y: 0, duration: 0.35 }, 0.35 * K);
        tl.to(r + ".bt-btn", { scale: 1.06, duration: 0.25, yoyo: true, repeat: 1, ease: "sine.inOut" }, 0.7 * K);
        tl.fromTo(r + ".bt-hand", { opacity: 0, x: 120, y: 160 }, { opacity: 1, x: 0, y: 0, duration: 0.55, ease: "power3.out" }, 1.05 * K);
        tl.to(r + ".bt-hand", { scale: 0.85, duration: 0.12, yoyo: true, repeat: 1 }, 1.62 * K);
        tl.to(r + ".bt-btn", { scale: 0.94, duration: 0.12, yoyo: true, repeat: 1 }, 1.62 * K);
        tl.fromTo(r + ".bt-ripple", { scale: 0, opacity: 0.9 }, { scale: 9, opacity: 0, duration: 0.7, ease: "power2.out" }, 1.66 * K);
        tl.to(r + ".bt-hand", { opacity: 0, y: 40, duration: 0.3 }, 2.3 * K);
        tl.to(r + ".bt-wrap", { opacity: 0, y: -20, duration: 0.3, ease: "power2.in" }, D - 0.35);""")

B["compte-rebours"] = block(
    "compte-rebours", "compte à rebours en chiffres qui basculent (ex. J-3, 3 2 1), légende", 3.4,
    [{"id": "from", "type": "number", "label": "Départ", "default": 5},
     {"id": "to", "type": "number", "label": "Arrivée", "default": 3},
     {"id": "prefix", "type": "string", "label": "Préfixe", "default": "J-"},
     {"id": "label", "type": "string", "label": "Légende", "default": "avant la fin de l'offre"}],
    """      <div class="mf-pos"><div class="cr-card">
        <div class="cr-row"><span class="cr-pre" data-var-text="prefix">J-</span><span class="cr-digit"><span class="cr-cur">5</span><span class="cr-next">4</span></span></div>
        <div class="cr-lbl" data-var-text="label">avant la fin de l'offre</div></div></div>""",
    """        #compte-rebours .cr-card { padding: 3vmin 6vmin; border-radius: 3vmin; background: var(--card); text-align: center; opacity: 0;
                                    box-shadow: 0 2vmin 6vmin rgba(0,0,0,.25); }
        #compte-rebours .cr-row { display: flex; align-items: center; justify-content: center; font-size: 20vmin; font-weight: 800; line-height: 1; color: var(--accent); }
        #compte-rebours .cr-digit { position: relative; display: inline-block; height: 1em; overflow: hidden; min-width: 0.65em; }
        #compte-rebours .cr-cur, #compte-rebours .cr-next { display: block; height: 1em; }
        #compte-rebours .cr-next { position: absolute; left: 0; right: 0; top: 100%; }
        #compte-rebours .cr-lbl { font-size: 4.4vmin; font-weight: 600; margin-top: 1.4vmin; opacity: 0; }""",
    """        const a = Math.round(Number(v.from) || 0), b = Math.round(Number(v.to) || 0), steps = Math.max(1, Math.abs(a - b)), dir = a > b ? -1 : 1;
        const cur = document.querySelector(r + ".cr-cur"), nxt = document.querySelector(r + ".cr-next");
        cur.textContent = a; nxt.textContent = a + dir;
        tl.fromTo(r + ".cr-card", { y: 40, scale: 0.9 }, { y: 0, scale: 1, duration: 0.5, ease: "back.out(1.8)" }, 0);
        tl.fromTo(r + ".cr-card", { opacity: 0 }, { opacity: 1, duration: 0.1 }, 0);  // opaque tout de suite : contraste
        tl.fromTo(r + ".cr-lbl", { opacity: 0, y: 10 }, { opacity: 1, y: 0, duration: 0.4 }, 0.4);
        const span = Math.max(0.35, (D - 1.4) / steps);
        for (let k = 0; k < steps; k++) {
          const t = 0.7 + k * span, n0 = a + dir * k, n1 = a + dir * (k + 1);
          tl.set(cur, { textContent: n0, yPercent: 0 }, t - 0.001);
          tl.set(nxt, { textContent: n1, yPercent: 0 }, t - 0.001);
          tl.to([cur, nxt], { yPercent: -100, duration: 0.3, ease: "power2.inOut" }, t);
          tl.set(cur, { textContent: n1, yPercent: 0 }, t + 0.31);
          tl.set(nxt, { yPercent: 0 }, t + 0.31);
        }
        tl.to(r + ".cr-card", { opacity: 0, y: -24, duration: 0.3, ease: "power2.in" }, D - 0.35);""")

B["notification"] = block(
    "notification", "bannière de notification façon smartphone qui descend, rebondit, puis remonte", 3.2,
    [{"id": "icon", "type": "string", "label": "Icône (chemin assets/…)", "default": PIX},
     {"id": "app", "type": "string", "label": "Nom de l'app / marque", "default": "Votre boutique"},
     {"id": "title", "type": "string", "label": "Titre", "default": "Nouvelle commande !"},
     {"id": "message", "type": "string", "label": "Message", "default": "Julie vient de réserver sa démonstration"},
     {"id": "when", "type": "string", "label": "Moment", "default": "maintenant"}],
    """      <div class="mf-pos"><div class="nt-card">
        <img class="nt-icon" data-var-src="icon" src="__PIX__" alt="" />
        <div class="nt-txt"><div class="nt-head"><span class="nt-app" data-var-text="app">Votre boutique</span><span class="nt-when" data-var-text="when">maintenant</span></div>
        <div class="nt-title" data-var-text="title">Nouvelle commande !</div><div class="nt-msg" data-var-text="message">…</div></div></div></div>""".replace("__PIX__", PIX),
    """        #notification .nt-card { width: 86%; display: flex; gap: 3vmin; align-items: flex-start; padding: 3vmin 3.4vmin; border-radius: 4vmin;
                                  background: rgba(245,245,247,.92); color: #111; box-shadow: 0 2vmin 6vmin rgba(0,0,0,.3); opacity: 0;
                                  backdrop-filter: blur(20px); }
        #notification .nt-icon { width: 11vmin; height: 11vmin; border-radius: 2.6vmin; object-fit: contain; background: #fff; flex: none; }
        #notification .nt-txt { flex: 1; min-width: 0; }
        #notification .nt-head { display: flex; justify-content: space-between; font-size: 3.3vmin; color: #6b6b70; text-transform: uppercase; letter-spacing: .04em; }
        #notification .nt-title { font-size: 4.6vmin; font-weight: 700; margin-top: .6vmin; }
        #notification .nt-msg { font-size: 4.1vmin; line-height: 1.25; color: #333; }""",
    """        tl.fromTo(r + ".nt-card", { opacity: 0, y: -260, scale: 0.96 }, { opacity: 1, y: 0, scale: 1, duration: 0.65, ease: "back.out(1.6)" }, 0);
        tl.to(r + ".nt-card", { x: 10, duration: 0.05, yoyo: true, repeat: 5, ease: "none" }, 0.7);
        tl.to(r + ".nt-card", { opacity: 0, y: -260, duration: 0.45, ease: "power3.in" }, D - 0.5);""")

B["sticker"] = block(
    "sticker", "sticker étoilé qui surgit en tournant (NOUVEAU, -20 %, OFFERT…), légère rotation continue", 2.8,
    [{"id": "label", "type": "string", "label": "Texte", "default": "NOUVEAU"},
     {"id": "left", "type": "number", "label": "Position horizontale (%)", "default": 50, "min": 0, "max": 100}],
    """      <div class="sk-wrap"><div class="sk-badge">
        <svg viewBox="0 0 200 200"><path class="sk-star" d=""/></svg><span class="sk-txt" data-var-text="label">NOUVEAU</span></div></div>""",
    """        #sticker .sk-wrap { position: absolute; top: calc(var(--top, 40) * 1%); left: calc(var(--left, 50) * 1%); width: 0; height: 0; }
        #sticker .sk-badge { position: absolute; width: 36vmin; height: 36vmin; left: -18vmin; top: -18vmin; opacity: 0; }
        #sticker svg { position: absolute; inset: 0; width: 100%; height: 100%; filter: drop-shadow(0 1.4vmin 2.4vmin rgba(0,0,0,.3)); }
        #sticker .sk-star { fill: var(--accent); }
        #sticker .sk-txt { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; text-align: center;
                           padding: 0 5vmin; font-size: 6.4vmin; font-weight: 900; line-height: 1; color: #fff; text-transform: uppercase; }""",
    """        let d = "";
        for (let i = 0; i < 32; i++) {
          const ang = (Math.PI * 2 * i) / 32, rad = i % 2 ? 84 : 98;
          d += (i ? "L" : "M") + (100 + rad * Math.cos(ang)).toFixed(1) + " " + (100 + rad * Math.sin(ang)).toFixed(1);
        }
        document.querySelector(r + ".sk-star").setAttribute("d", d + "Z");
        tl.fromTo(r + ".sk-badge", { opacity: 0, scale: 0, rotation: -40 }, { opacity: 1, scale: 1, rotation: -8, duration: 0.6, ease: "back.out(2.6)" }, 0);
        tl.to(r + ".sk-badge svg", { rotation: 40, duration: D, ease: "none" }, 0);
        tl.to(r + ".sk-badge", { scale: 1.06, duration: 0.3, yoyo: true, repeat: 1, ease: "sine.inOut" }, 0.9);
        tl.to(r + ".sk-badge", { opacity: 0, scale: 0.6, duration: 0.25, ease: "power2.in" }, D - 0.3);""")

B["surligneur"] = block(
    "surligneur", "phrase forte dont un mot-clé est surligné au marqueur (balayage), pour une accroche", 3.0,
    [{"id": "before", "type": "string", "label": "Texte avant le mot-clé", "default": "Le pain le plus"},
     {"id": "mark", "type": "string", "label": "Mot-clé surligné", "default": "croustillant"},
     {"id": "after", "type": "string", "label": "Texte après", "default": "de Lyon"}],
    """      <div class="mf-pos"><div class="sl-txt"><span class="sl-a" data-var-text="before">Le pain le plus</span>
        <span class="sl-m"><i class="sl-hl"></i><span data-var-text="mark">croustillant</span></span>
        <span class="sl-b" data-var-text="after">de Lyon</span></div></div>""",
    """        #surligneur .sl-txt { color: var(--ink, var(--text)); width: 86%; text-align: center; font-size: 10vmin; font-weight: 800; line-height: 1.15; text-wrap: balance;
                               text-shadow: 0 0.6vmin 2vmin rgba(0,0,0,.45); }
        #surligneur .sl-a, #surligneur .sl-b, #surligneur .sl-m { display: inline-block; opacity: 0; }
        #surligneur .sl-m { position: relative; padding: 0 1.2vmin; }
        #surligneur .sl-m span { position: relative; }
        #surligneur .sl-hl { position: absolute; left: 0; right: 0; top: 18%; bottom: 8%; background: var(--accent); border-radius: 1vmin;
                              transform-origin: 0 50%; transform: scaleX(0) skewX(-6deg); }""",
    """        tl.fromTo(r + ".sl-a", { opacity: 0, y: 30 }, { opacity: 1, y: 0, duration: 0.45, ease: "power3.out" }, 0);
        tl.fromTo(r + ".sl-m", { opacity: 0, y: 30 }, { opacity: 1, y: 0, duration: 0.45, ease: "power3.out" }, 0.15 * K);
        tl.fromTo(r + ".sl-b", { opacity: 0, y: 30 }, { opacity: 1, y: 0, duration: 0.45, ease: "power3.out" }, 0.3 * K);
        tl.fromTo(r + ".sl-hl", { scaleX: 0 }, { scaleX: 1, duration: 0.5, ease: "power2.inOut" }, 0.7 * K);
        tl.to(r + ".sl-m", { scale: 1.06, duration: 0.18, yoyo: true, repeat: 1 }, 1.15 * K);
        tl.to(r + ".sl-txt", { opacity: 0, y: -20, duration: 0.3, ease: "power2.in" }, D - 0.35);""")

B["fleche"] = block(
    "fleche", "flèche dessinée à la main qui se trace vers un point de l'image, avec une étiquette manuscrite", 3.0,
    [{"id": "label", "type": "string", "label": "Étiquette", "default": "fait main !"},
     {"id": "x", "type": "number", "label": "Cible horizontale (%)", "default": 62, "min": 0, "max": 100},
     {"id": "y", "type": "number", "label": "Cible verticale (%)", "default": 48, "min": 0, "max": 100}],
    """      <div class="fl-wrap"><span class="fl-lbl" data-var-text="label">fait main !</span>
        <svg class="fl-svg" viewBox="0 0 220 220"><path class="fl-path" d="M20 30 C 90 20, 160 60, 182 160"/>
        <path class="fl-head" d="M160 146 L 184 170 L 200 140"/><ellipse class="fl-circ" cx="190" cy="186" rx="26" ry="20"/></svg></div>""",
    """        #fleche .fl-wrap { position: absolute; left: calc(var(--x, 62) * 1% - 38vmin); top: calc(var(--y, 48) * 1% - 40vmin); width: 40vmin; height: 40vmin; }
        #fleche .fl-svg { position: absolute; inset: 0; width: 100%; height: 100%; overflow: visible; }
        #fleche .fl-path, #fleche .fl-head, #fleche .fl-circ { fill: none; stroke: var(--accent); stroke-width: 7; stroke-linecap: round; stroke-linejoin: round;
                                                                filter: drop-shadow(0 0.4vmin 0.8vmin rgba(0,0,0,.35)); }
        #fleche .fl-lbl { position: absolute; left: -4vmin; top: -9vmin; font-family: var(--font, "Inter"), sans-serif; font-style: italic; font-size: 8vmin; font-weight: 800;
                          color: var(--text); transform: rotate(-6deg); opacity: 0; text-shadow: 0 0.4vmin 1.6vmin rgba(0,0,0,.55); white-space: nowrap; }""",
    """        const path = document.querySelector(r + ".fl-path"), head = document.querySelector(r + ".fl-head"), circ = document.querySelector(r + ".fl-circ");
        [path, head, circ].forEach(function (p) { const L = p.getTotalLength ? p.getTotalLength() : 300; p.style.strokeDasharray = L; p.style.strokeDashoffset = L; p.dataset.l = L; });
        tl.fromTo(r + ".fl-lbl", { opacity: 0, y: 10 }, { opacity: 1, y: 0, duration: 0.35 }, 0);
        tl.fromTo(path, { strokeDashoffset: Number(path.dataset.l) }, { strokeDashoffset: 0, duration: 0.6, ease: "power1.inOut" }, 0.2 * K);
        tl.fromTo(head, { strokeDashoffset: Number(head.dataset.l) }, { strokeDashoffset: 0, duration: 0.2, ease: "power1.out" }, 0.8 * K);
        tl.fromTo(circ, { strokeDashoffset: Number(circ.dataset.l) }, { strokeDashoffset: 0, duration: 0.45, ease: "power1.inOut" }, 1.0 * K);
        tl.to(r + ".fl-wrap", { opacity: 0, duration: 0.3 }, D - 0.35);""")

B["suivre"] = block(
    "suivre", "carte réseau social : photo, nom, @compte, bouton Suivre touché qui devient Abonné ✓", 3.2,
    [{"id": "avatar", "type": "string", "label": "Avatar / logo (chemin assets/…)", "default": PIX},
     {"id": "name", "type": "string", "label": "Nom", "default": "Votre boutique"},
     {"id": "handle", "type": "string", "label": "@compte", "default": "@votreboutique"},
     {"id": "cta", "type": "string", "label": "Bouton", "default": "Suivre"},
     {"id": "done", "type": "string", "label": "Bouton après le tap", "default": "Abonné ✓"}],
    """      <div class="mf-pos"><div class="sv-card">
        <img class="sv-av" data-var-src="avatar" src="__PIX__" alt="" />
        <div class="sv-id"><div class="sv-name" data-var-text="name">Votre boutique</div><div class="sv-handle" data-var-text="handle">@votreboutique</div></div>
        <div class="sv-btn" data-layout-allow-overlap><span class="sv-a" data-var-text="cta">Suivre</span><span class="sv-b" data-var-text="done">Abonné ✓</span></div>
        <i class="sv-tap"></i></div></div>""".replace("__PIX__", PIX),
    """        #suivre .sv-card { position: relative; width: 86%; display: flex; align-items: center; gap: 3vmin; padding: 3vmin 3.4vmin; border-radius: 4vmin;
                            background: #fff; color: #111; box-shadow: 0 2vmin 6vmin rgba(0,0,0,.3); opacity: 0; }
        #suivre .sv-av { width: 15vmin; height: 15vmin; border-radius: 50%; object-fit: contain; background: #f2f2f2; flex: none; border: 0.6vmin solid var(--accent); }
        #suivre .sv-id { flex: 1; min-width: 0; }
        #suivre .sv-name { font-size: 5vmin; font-weight: 800; }
        #suivre .sv-handle { font-size: 3.8vmin; color: #666; }
        #suivre .sv-btn { position: relative; flex: none; padding: 2.2vmin 4.4vmin; border-radius: 2vmin; background: var(--accent); color: #fff;
                           font-size: 4.2vmin; font-weight: 800; overflow: hidden; }
        #suivre .sv-b { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; background: #e9e9ec; color: #111; opacity: 0; }
        #suivre .sv-tap { position: absolute; right: 9vmin; top: 50%; width: 8vmin; height: 8vmin; margin-top: -4vmin; border-radius: 50%;
                           background: rgba(0,0,0,.18); transform: scale(0); opacity: 0; }""",
    """        tl.fromTo(r + ".sv-card", { y: 60, scale: 0.94 }, { y: 0, scale: 1, duration: 0.55, ease: "back.out(1.7)" }, 0);
        tl.fromTo(r + ".sv-card", { opacity: 0 }, { opacity: 1, duration: 0.1 }, 0);  // opaque tout de suite : contraste
        tl.fromTo(r + ".sv-tap", { scale: 0, opacity: 0.9 }, { scale: 2.6, opacity: 0, duration: 0.5, ease: "power2.out" }, 1.2 * K);
        tl.to(r + ".sv-btn", { scale: 0.92, duration: 0.1, yoyo: true, repeat: 1 }, 1.2 * K);
        tl.fromTo(r + ".sv-b", { opacity: 0 }, { opacity: 1, duration: 0.2 }, 1.35 * K);
        tl.to(r + ".sv-a", { opacity: 0, duration: 0.15 }, 1.35 * K);
        tl.to(r + ".sv-card", { opacity: 0, y: -30, duration: 0.3, ease: "power2.in" }, D - 0.35);""")


# --- portés depuis Onda (github.com/degueba/onda, MIT, © 2026 Rodrigo Botelho) : même mouvement, réécrit en GSAP ---
ONDA = "porté depuis Onda (MIT, Rodrigo Botelho) · "

B["confetti"] = block(
    "confetti", ONDA + "explosion de confettis : départ d'un point, éventail, gravité, rotation ; tirage fixe (graine)", 3.0,
    [{"id": "count", "type": "number", "label": "Nombre de confettis", "default": 90, "min": 10, "max": 250},
     {"id": "ox", "type": "number", "label": "Départ horizontal (%)", "default": 50, "min": 0, "max": 100},
     {"id": "oy", "type": "number", "label": "Départ vertical (%)", "default": 62, "min": 0, "max": 100},
     {"id": "spread", "type": "number", "label": "Ouverture (degrés)", "default": 110, "min": 10, "max": 360},
     {"id": "seed", "type": "number", "label": "Graine (tirage)", "default": 7},
     {"id": "colors", "type": "string", "label": "Couleurs (séparées par des virgules)", "default": "#FFC527,#ffffff,#69CD3A,#3B82F6"}],
    """      <div class="cf-layer"></div>""",
    """        #confetti .cf-layer { position: absolute; inset: 0; overflow: hidden; }
        #confetti .cf-p { position: absolute; left: 0; top: 0; border-radius: 1px; will-change: transform, opacity; }""",
    """        function mulberry32(a) { return function () { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a);
          t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
        const layer = document.querySelector(r + ".cf-layer"), W = layer.clientWidth || 1080, H = layer.clientHeight || 1920;
        const rand = mulberry32(Number(v.seed) || 7), n = Math.max(10, Math.min(250, Number(v.count) || 90));
        const cols = [v.accent].concat(String(v.colors || "").split(",").map(function (c) { return c.trim(); }).filter(Boolean));
        const ox = (Number(v.ox) || 50) / 100 * W, oy = (Number(v.oy) || 62) / 100 * H, spr = (Number(v.spread) || 110) * Math.PI / 180;
        const sc = Math.min(W, H) / 1080, FPS = 30, pieces = [];
        for (let i = 0; i < n; i++) {
          const aJit = rand(), speed = 9 + rand() * 13, spin = (rand() - 0.5) * 28, spin0 = rand() * 360;
          const col = cols[Math.floor(rand() * cols.length)] || cols[0], wf = 0.7 + rand() * 0.6, sj = 0.7 + rand() * 0.8;
          const life = (D * FPS) * (0.8 + rand() * 0.4) * 0.95, drift = (rand() - 0.5) * 4, size = 18 * sc;
          const el = document.createElement("i"); el.className = "cf-p";
          el.style.width = (size * sj * wf) + "px"; el.style.height = (size * sj) + "px"; el.style.background = col; el.style.opacity = 0;
          layer.appendChild(el);
          const ang = -Math.PI / 2 + (aJit - 0.5) * spr;
          pieces.push({ el: el, vx: Math.cos(ang) * speed * sc, vy: Math.sin(ang) * speed * sc, spin: spin, spin0: spin0, life: life, drift: drift, i: i,
                        w: size * sj * wf, h: size * sj });
        }
        const g = 0.55 * sc, clock = { f: 0 };
        function draw(f) {
          pieces.forEach(function (p) {
            if (f > p.life) { p.el.style.opacity = 0; return; }
            const x = ox + p.vx * f + Math.sin(f * 0.18 + p.i) * p.drift, y = oy + p.vy * f + 0.5 * g * f * f;
            const u = f / p.life, op = u < 0.15 ? u / 0.15 : u > 0.7 ? Math.max(0, (1 - u) / 0.3) : 1;
            p.el.style.opacity = op;
            p.el.style.transform = "translate(" + (x - p.w / 2) + "px," + (y - p.h / 2) + "px) rotate(" + (p.spin0 + p.spin * f) + "deg)";
          });
        }
        draw(0);
        tl.fromTo(clock, { f: 0 }, { f: D * FPS, duration: D, ease: "none", onUpdate: function () { draw(clock.f); } }, 0);""")

B["marquee"] = block(
    "marquee", ONDA + "bandeau qui défile en continu : logos, partenaires, services, « ils nous font confiance »", 4.0,
    [{"id": "title", "type": "string", "label": "Titre au-dessus (facultatif)", "default": ""},
     {"id": "items", "type": "string", "label": "Éléments séparés par |", "default": "Rideaux|Voilages|Stores|Tapisserie|Coussins"},
     {"id": "speed", "type": "number", "label": "Vitesse (px/s)", "default": 160, "min": 20, "max": 800},
     {"id": "direction", "type": "enum", "label": "Sens", "default": "left", "options": [{"value": "left", "label": "vers la gauche"}, {"value": "right", "label": "vers la droite"}]}],
    """      <div class="mf-pos"><div class="mq-wrap"><div class="mq-title" data-var-text="title"></div>
        <div class="mq-band"><div class="mq-track"></div></div></div></div>""",
    """        #marquee .mq-wrap { width: 100%; opacity: 0; }
        #marquee .mq-title { color: var(--ink, var(--text)); text-align: center; font-size: 4vmin; letter-spacing: .2em; text-transform: uppercase; margin-bottom: 2vmin;
                             text-shadow: 0 2px 8px rgba(0,0,0,.5); }
        #marquee .mq-title:empty { display: none; }
        #marquee .mq-band { width: 100%; overflow: hidden; background: var(--card); padding: 3vmin 0; }
        #marquee .mq-track { display: flex; gap: 7vmin; white-space: nowrap; will-change: transform; }
        #marquee .mq-item { font-size: 6.4vmin; font-weight: 700; letter-spacing: .02em; display: inline-flex; align-items: center; gap: 7vmin; }
        #marquee .mq-item::after { content: ""; width: 1.6vmin; height: 1.6vmin; border-radius: 50%; background: var(--accent); }""",
    """        const items = String(v.items || "").split("|").map(function (x) { return x.trim(); }).filter(Boolean);
        const track = document.querySelector(r + ".mq-track");
        for (let k = 0; k < 4; k++) items.forEach(function (it) { const e = document.createElement("span"); e.className = "mq-item"; e.textContent = it; track.appendChild(e); });
        const setW = track.scrollWidth / 4 || 1000, sp = Number(v.speed) || 160, dir = v.direction === "right" ? 1 : -1, clock = { t: 0 };
        function place(t) { const off = ((t * sp) % setW + setW) % setW; track.style.transform = "translateX(" + (dir < 0 ? -off : off - setW) + "px)"; }
        place(0);
        tl.fromTo(r + ".mq-wrap", { opacity: 0, y: 30 }, { opacity: 1, y: 0, duration: 0.45, ease: "power3.out" }, 0);
        tl.fromTo(clock, { t: 0 }, { t: D, duration: D, ease: "none", onUpdate: function () { place(clock.t); } }, 0);
        tl.to(r + ".mq-wrap", { opacity: 0, duration: 0.3 }, D - 0.35);""")

B["mot-tournant"] = block(
    "mot-tournant", ONDA + "phrase dont un mot change en place (Pour les restaurants / commerces / artisans)", 4.0,
    [{"id": "before", "type": "string", "label": "Texte avant", "default": "Pour les"},
     {"id": "words", "type": "string", "label": "Mots qui tournent, séparés par |", "default": "restaurants|commerces|artisans"},
     {"id": "after", "type": "string", "label": "Texte après", "default": ""}],
    """      <div class="mf-pos"><div class="wr-line"><span class="wr-a" data-var-text="before">Pour les</span>
        <span class="wr-slot"></span><span class="wr-b" data-var-text="after"></span></div></div>""",
    """        #mot-tournant .wr-line { color: var(--ink, var(--text)); width: 88%; text-align: center; font-size: 9vmin; font-weight: 800; line-height: 1.2; opacity: 0;
                                  text-shadow: 0 0.6vmin 2vmin rgba(0,0,0,.4); }
        #mot-tournant .wr-slot { display: inline-grid; vertical-align: bottom; }
        #mot-tournant .wr-w { grid-area: 1 / 1; color: var(--accent); opacity: 0; white-space: nowrap; }""",
    """        const ws = String(v.words || "").split("|").map(function (x) { return x.trim(); }).filter(Boolean);
        const slot = document.querySelector(r + ".wr-slot");
        ws.forEach(function (w) { const e = document.createElement("span"); e.className = "wr-w"; e.textContent = w; slot.appendChild(e); });
        const els = slot.querySelectorAll(".wr-w"), per = Math.max(0.6, (D - 0.6) / Math.max(1, ws.length)), tr = Math.min(0.35, per * 0.3);
        tl.fromTo(r + ".wr-line", { opacity: 0, y: 24 }, { opacity: 1, y: 0, duration: 0.4, ease: "power3.out" }, 0);
        els.forEach(function (e, i) {
          const t = 0.15 + i * per;
          tl.fromTo(e, { opacity: 0, y: 30 }, { opacity: 1, y: 0, duration: tr, ease: "power3.out" }, t);
          if (i < els.length - 1) tl.to(e, { opacity: 0, y: -30, duration: tr, ease: "power2.in" }, t + per - tr);
        });
        tl.to(r + ".wr-line", { opacity: 0, duration: 0.3 }, D - 0.35);""")


B["barres"] = block(
    "barres", ONDA + "graphique en barres horizontales qui poussent, valeurs qui comptent, une barre mise en avant", 3.6,
    [{"id": "title", "type": "string", "label": "Titre", "default": "Délai de livraison (jours)"},
     {"id": "items", "type": "string", "label": "Barres « libellé:valeur » séparées par |", "default": "Concurrent A:21|Concurrent B:14|Nous:7"},
     {"id": "suffix", "type": "string", "label": "Unité après la valeur", "default": ""},
     {"id": "highlight", "type": "number", "label": "Barre mise en avant (1 = première, 0 = dernière)", "default": 0},
     {"id": "max", "type": "number", "label": "Maximum (0 = plus grande valeur)", "default": 0}],
    """      <div class="mf-pos"><div class="br-card"><div class="br-title" data-var-text="title"></div><div class="br-rows"></div></div></div>""",
    """        #barres .br-card { width: 86%; padding: 4vmin 5vmin; border-radius: 3vmin; background: var(--card); opacity: 0; box-shadow: 0 2vmin 6vmin rgba(0,0,0,.25); }
        #barres .br-title { font-size: 4.6vmin; font-weight: 700; margin-bottom: 3vmin; }
        #barres .br-title:empty { display: none; }
        #barres .br-row { margin-bottom: 2.6vmin; opacity: 0; }
        #barres .br-head { display: flex; justify-content: space-between; font-size: 3.8vmin; margin-bottom: 1vmin; }
        #barres .br-val { font-weight: 800; font-variant-numeric: tabular-nums; }
        #barres .br-track { height: 3.4vmin; border-radius: 99px; background: rgba(255,255,255,.12); overflow: hidden; }
        #barres .br-bar { height: 100%; border-radius: 99px; background: rgba(255,255,255,.55); transform-origin: 0 50%; transform: scaleX(0); }
        #barres .br-row.hi .br-bar { background: var(--accent); }
        #barres .br-row.hi .br-val { color: var(--accent); }""",
    """        const rows = String(v.items || "").split("|").map(function (x) { const k = x.lastIndexOf(":"); return { l: x.slice(0, k).trim(), v: Number(x.slice(k + 1)) || 0 }; })
          .filter(function (x) { return x.l; });
        const mx = Number(v.max) > 0 ? Number(v.max) : Math.max.apply(null, rows.map(function (x) { return x.v; }).concat([1]));
        const hi = Number(v.highlight) > 0 ? Number(v.highlight) - 1 : rows.length - 1, box = document.querySelector(r + ".br-rows");
        rows.forEach(function (x, i) {
          box.insertAdjacentHTML("beforeend", '<div class="br-row' + (i === hi ? ' hi' : '') + '"><div class="br-head"><span class="br-l"></span><span class="br-val">0</span></div>' +
            '<div class="br-track"><div class="br-bar"></div></div></div>');
          box.lastChild.querySelector(".br-l").textContent = x.l;
        });
        tl.fromTo(r + ".br-card", { y: 40, scale: 0.94 }, { y: 0, scale: 1, duration: 0.5, ease: "back.out(1.6)" }, 0);
        tl.fromTo(r + ".br-card", { opacity: 0 }, { opacity: 1, duration: 0.1 }, 0);
        const per = Math.min(0.35, (D * 0.45) / Math.max(1, rows.length)), grow = Math.min(1.0, D * 0.3);
        document.querySelectorAll(r + ".br-row").forEach(function (row, i) {
          const t = 0.3 * K + i * per, o = { n: 0 }, val = row.querySelector(".br-val");
          tl.fromTo(row, { opacity: 0, x: -20 }, { opacity: 1, x: 0, duration: 0.3 }, t);
          tl.fromTo(row.querySelector(".br-bar"), { scaleX: 0 }, { scaleX: rows[i].v / mx, duration: grow, ease: "power2.out" }, t + 0.1);
          tl.to(o, { n: rows[i].v, duration: grow, ease: "power2.out", onUpdate: function () { val.textContent = Math.round(o.n).toLocaleString("fr-BE") + (v.suffix || ""); } }, t + 0.1);
        });
        tl.to(r + ".br-card", { opacity: 0, y: -24, duration: 0.3, ease: "power2.in" }, D - 0.35);""")

B["frise"] = block(
    "frise", ONDA + "frise chronologique verticale : la ligne se trace, les étapes apparaissent une à une", 3.8,
    [{"id": "title", "type": "string", "label": "Titre", "default": "Notre histoire"},
     {"id": "items", "type": "string", "label": "Étapes « date:libellé » séparées par |", "default": "1895:Création de la maison|1960:Deuxième génération|2026:Cinquième génération"}],
    """      <div class="mf-pos"><div class="fr-box"><div class="fr-title" data-var-text="title"></div><div class="fr-list"><i class="fr-line"></i></div></div></div>""",
    """        #frise .fr-box { width: 80%; color: var(--ink, var(--text)); }
        #frise .fr-title { font-size: 7vmin; font-weight: 800; margin-bottom: 4vmin; opacity: 0; }
        #frise .fr-title:empty { display: none; }
        #frise .fr-list { position: relative; padding-left: 9vmin; }
        #frise .fr-line { position: absolute; left: 2.2vmin; top: 1vmin; bottom: 1vmin; width: 0.6vmin; background: var(--accent); opacity: .35;
                          transform-origin: 50% 0; transform: scaleY(0); }
        #frise .fr-it { position: relative; margin-bottom: 4.4vmin; opacity: 0; }
        #frise .fr-dot { position: absolute; left: -9vmin; top: 0.6vmin; width: 5vmin; height: 5vmin; border-radius: 50%; background: var(--accent);
                         box-shadow: 0 0 0 1.2vmin color-mix(in srgb, var(--accent) 25%, transparent); transform: scale(0); }
        #frise .fr-date { font-size: 6vmin; font-weight: 800; color: var(--accent); line-height: 1; }
        #frise .fr-lbl { font-size: 4.4vmin; margin-top: 0.8vmin; }""",
    """        const items = String(v.items || "").split("|").map(function (x) { const k = x.indexOf(":"); return { d: x.slice(0, k).trim(), l: x.slice(k + 1).trim() }; })
          .filter(function (x) { return x.d || x.l; });
        const list = document.querySelector(r + ".fr-list");
        items.forEach(function (x) {
          list.insertAdjacentHTML("beforeend", '<div class="fr-it"><i class="fr-dot"></i><div class="fr-date"></div><div class="fr-lbl"></div></div>');
          list.lastChild.querySelector(".fr-date").textContent = x.d; list.lastChild.querySelector(".fr-lbl").textContent = x.l;
        });
        tl.fromTo(r + ".fr-title", { opacity: 0, y: 20 }, { opacity: 1, y: 0, duration: 0.4 }, 0);
        const span = Math.max(0.8, D - 1.2), per = span / Math.max(1, items.length);
        tl.fromTo(r + ".fr-line", { scaleY: 0 }, { scaleY: 1, duration: span, ease: "none" }, 0.3 * K);
        document.querySelectorAll(r + ".fr-it").forEach(function (it, i) {
          const t = 0.3 * K + i * per;
          tl.fromTo(it, { opacity: 0, x: 24 }, { opacity: 1, x: 0, duration: 0.35, ease: "power3.out" }, t);
          tl.fromTo(it.querySelector(".fr-dot"), { scale: 0 }, { scale: 1, duration: 0.35, ease: "back.out(2.4)" }, t);
        });
        tl.to(r + ".fr-box", { opacity: 0, duration: 0.3 }, D - 0.35);""")

B["machine-a-ecrire"] = block(
    "machine-a-ecrire", ONDA + "texte tapé lettre par lettre avec curseur ; mode « barre de recherche » façon moteur de recherche", 3.2,
    [{"id": "text", "type": "string", "label": "Texte tapé", "default": "boulanger à Lyon"},
     {"id": "search", "type": "boolean", "label": "Dans une barre de recherche", "default": True}],
    """      <div class="mf-pos"><div class="tw-box"><svg class="tw-loupe" viewBox="0 0 24 24"><circle cx="10.5" cy="10.5" r="6.5" fill="none" stroke="#5f6368" stroke-width="2.4"/>
        <path d="M15.5 15.5 L21 21" stroke="#5f6368" stroke-width="2.4" stroke-linecap="round"/></svg><span class="tw-txt"></span><span class="tw-cur">|</span></div></div>""",
    """        #machine-a-ecrire .tw-box { display: inline-flex; align-items: center; gap: 2.4vmin; font-size: 7vmin; font-weight: 600; opacity: 0; max-width: 88%;
                                    color: var(--ink, var(--text)); white-space: nowrap; }
        #machine-a-ecrire .tw-box.sb { padding: 2.6vmin 4.4vmin; border-radius: 99px; background: #fff; color: #202124; font-size: 5.6vmin; font-weight: 500;
                                       box-shadow: 0 1vmin 4vmin rgba(0,0,0,.18), 0 0 0 0.3vmin rgba(0,0,0,.06); min-width: 70%; }
        #machine-a-ecrire .tw-loupe { width: 5.4vmin; height: 5.4vmin; flex: none; display: none; }
        #machine-a-ecrire .tw-box.sb .tw-loupe { display: block; }
        #machine-a-ecrire .tw-cur { color: var(--accent); font-weight: 400; margin-left: -1.4vmin; }""",
    """        const box = document.querySelector(r + ".tw-box"), txt = document.querySelector(r + ".tw-txt"), cur = document.querySelector(r + ".tw-cur");
        if (v.search === true || v.search === "true") box.classList.add("sb");
        const full = String(v.text || ""), clock = { t: 0 }, typeDur = Math.min(Math.max(0.6, full.length * 0.06), D * 0.6);
        function show(t) {
          const n = Math.max(0, Math.min(full.length, Math.floor(((t - 0.35) / typeDur) * full.length)));
          txt.textContent = full.slice(0, n);
          cur.style.opacity = Math.floor(t / 0.5) % 2 === 0 ? 1 : 0;  // clignotement déterministe
        }
        show(0);
        tl.fromTo(box, { opacity: 0, y: 24, scale: 0.96 }, { opacity: 1, y: 0, scale: 1, duration: 0.35, ease: "power3.out" }, 0);
        tl.fromTo(clock, { t: 0 }, { t: D, duration: D, ease: "none", onUpdate: function () { show(clock.t); } }, 0);
        tl.to(box, { opacity: 0, duration: 0.3 }, D - 0.35);""")

B["tarif"] = block(
    "tarif", ONDA + "carte tarifaire : offre, prix, période, atouts cochés un par un, bouton, badge recommandé", 3.8,
    [{"id": "tier", "type": "string", "label": "Nom de l'offre", "default": "Formule Confort"},
     {"id": "price", "type": "string", "label": "Prix (réel)", "default": "490 €"},
     {"id": "period", "type": "string", "label": "Période / mention", "default": "pose comprise"},
     {"id": "features", "type": "string", "label": "Atouts séparés par |", "default": "Prise de mesures|Confection sur mesure|Pose par nos soins"},
     {"id": "cta", "type": "string", "label": "Bouton", "default": "Demander un devis"},
     {"id": "badge", "type": "string", "label": "Badge (vide = aucun)", "default": "Le plus choisi"}],
    """      <div class="mf-pos"><div class="tf-card"><div class="tf-badge" data-var-text="badge"></div>
        <div class="tf-tier" data-var-text="tier">Formule</div><div class="tf-price"><span data-var-text="price">490 €</span><small data-var-text="period"></small></div>
        <ul class="tf-feats"></ul><div class="tf-cta" data-var-text="cta">Demander un devis</div></div></div>""",
    """        #tarif .tf-card { position: relative; width: 74%; padding: 5vmin 5.4vmin; border-radius: 3.4vmin; background: var(--card); opacity: 0;
                          box-shadow: 0 2vmin 6vmin rgba(0,0,0,.28), 0 0 0 0.5vmin var(--accent); }
        #tarif .tf-badge { position: absolute; top: -2.8vmin; left: 50%; transform: translateX(-50%); padding: .5em 1.2em; border-radius: 99px;
                           background: var(--accent); color: #fff; font-size: 3.2vmin; font-weight: 800; white-space: nowrap; }
        #tarif .tf-badge:empty { display: none; }
        #tarif .tf-tier { font-size: 4.6vmin; font-weight: 700; opacity: .85; }
        #tarif .tf-price { margin: 1.4vmin 0 3vmin; font-size: 13vmin; font-weight: 800; line-height: 1; color: var(--accent); }
        #tarif .tf-price small { display: block; font-size: 3.6vmin; font-weight: 500; color: var(--text); opacity: .8; margin-top: 1vmin; }
        #tarif .tf-feats { list-style: none; margin: 0 0 3.4vmin; padding: 0; }
        #tarif .tf-feats li { display: flex; align-items: center; gap: 2vmin; font-size: 4.2vmin; margin-bottom: 1.6vmin; opacity: 0; }
        #tarif .tf-feats li i { flex: none; width: 4.4vmin; height: 4.4vmin; border-radius: 50%; background: var(--accent); position: relative; }
        #tarif .tf-feats li i::after { content: ""; position: absolute; left: 1.5vmin; top: 0.8vmin; width: 1vmin; height: 2vmin; border: solid #fff;
                                       border-width: 0 0.55vmin 0.55vmin 0; transform: rotate(45deg); }
        #tarif .tf-cta { text-align: center; padding: 2.6vmin; border-radius: 99px; background: var(--accent); color: #fff; font-size: 4.4vmin; font-weight: 800; opacity: 0; }""",
    """        const fs = String(v.features || "").split("|").map(function (x) { return x.trim(); }).filter(Boolean), ul = document.querySelector(r + ".tf-feats");
        fs.forEach(function (f) { const li = document.createElement("li"); li.innerHTML = "<i></i><span></span>"; li.querySelector("span").textContent = f; ul.appendChild(li); });
        tl.fromTo(r + ".tf-card", { y: 50, scale: 0.94 }, { y: 0, scale: 1, duration: 0.55, ease: "back.out(1.6)" }, 0);
        tl.fromTo(r + ".tf-card", { opacity: 0 }, { opacity: 1, duration: 0.1 }, 0);
        const per = Math.min(0.3, (D * 0.4) / Math.max(1, fs.length));
        document.querySelectorAll(r + ".tf-feats li").forEach(function (li, i) {
          tl.fromTo(li, { opacity: 0, x: -16 }, { opacity: 1, x: 0, duration: 0.3, ease: "power2.out" }, 0.55 * K + i * per);
        });
        tl.fromTo(r + ".tf-cta", { opacity: 0, scale: 0.9 }, { opacity: 1, scale: 1, duration: 0.35, ease: "back.out(2)" }, 0.6 * K + fs.length * per);
        tl.to(r + ".tf-card", { opacity: 0, y: -24, duration: 0.3, ease: "power2.in" }, D - 0.35);""")

# --- blocs « verre » (pubs immobilières de luxe) : verre dépoli = backdrop-filter ; aucun parent animé en filter / opacité < 1
#     au repos (sinon le verre ne voit plus la vidéo derrière)
GLASS = ("background: rgba(255,255,255,.2); border: 0.25vmin solid rgba(255,255,255,.5); backdrop-filter: blur(22px) saturate(1.4); "
         "-webkit-backdrop-filter: blur(22px) saturate(1.4); box-shadow: 0 2vmin 6vmin rgba(0,0,0,.25), inset 0 0.2vmin 0 rgba(255,255,255,.6);")
PIN = ('<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2a7 7 0 0 0-7 7c0 5.2 7 13 7 13s7-7.8 7-13a7 7 0 0 0-7-7zm0 9.5a2.5 2.5 0 1 1 '
       '0-5 2.5 2.5 0 0 1 0 5z"/></svg>')

B["recherche-verre"] = block(
    "recherche-verre", "barre de recherche en verre dépoli qui se tape, bouton pressé, pastille lieu qui tombe dessous ; ex. « villa surin, marbella »", 3.2,
    [{"id": "query", "type": "string", "label": "Texte tapé", "default": "villa surin, marbella"},
     {"id": "button", "type": "string", "label": "Bouton", "default": "Rechercher"},
     {"id": "place", "type": "string", "label": "Pastille lieu (vide = aucune)", "default": "Marbella"}],
    f"""      <div class="mf-pos"><div class="rv-wrap">
        <div class="rv-bar"><svg class="rv-mag" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="M20 20l-4-4"/></svg>
          <span class="rv-q"></span><i class="rv-caret"></i><span class="rv-btn" data-var-text="button">Rechercher</span></div>
        <div class="rv-chip"><span class="rv-pin">{PIN}</span><span class="rv-place" data-var-text="place">Marbella</span></div></div></div>""",
    f"""        #recherche-verre .rv-wrap {{ width: 84%; display: flex; flex-direction: column; align-items: center; gap: 2.4vmin; }}
        #recherche-verre .rv-bar {{ position: relative; width: 100%; display: flex; align-items: center; gap: 2.2vmin; padding: 2.2vmin 2.2vmin 2.2vmin 3.4vmin;
                                    border-radius: 99px; {GLASS} color: #fff; opacity: 0; }}
        #recherche-verre .rv-mag {{ width: 5vmin; height: 5vmin; flex: none; opacity: .9; }}
        #recherche-verre .rv-q {{ font-size: 4.4vmin; font-weight: 500; white-space: nowrap; text-shadow: 0 0.2vmin 1vmin rgba(0,0,0,.3); }}
        #recherche-verre .rv-caret {{ width: 0.4vmin; height: 5vmin; background: #fff; margin-left: -1.6vmin; }}
        #recherche-verre .rv-btn {{ margin-left: auto; padding: 1.8vmin 3.6vmin; border-radius: 99px; background: var(--accent); color: #fff;
                                    font-size: 3.6vmin; font-weight: 700; box-shadow: 0 1vmin 3vmin rgba(0,0,0,.25); }}
        #recherche-verre .rv-chip {{ display: inline-flex; align-items: center; gap: 1.2vmin; padding: 1.4vmin 3vmin 1.4vmin 2.2vmin; border-radius: 99px;
                                     {GLASS} color: #fff; font-size: 3.6vmin; font-weight: 600; opacity: 0; }}
        #recherche-verre .rv-pin {{ width: 3.8vmin; height: 3.8vmin; color: var(--accent); display: flex; }}""",
    """        const q = String(v.query || ""), qs = document.querySelector(r + ".rv-q"), o = { n: 0 };
        if (!String(v.place || "").trim()) document.querySelector(r + ".rv-chip").style.display = "none";
        tl.fromTo(r + ".rv-bar", { opacity: 0, y: 40, scale: 0.92 }, { opacity: 1, y: 0, scale: 1, duration: 0.5, ease: "back.out(1.6)" }, 0);
        tl.fromTo(o, { n: 0 }, { n: q.length, duration: Math.max(0.6, 1.25 * K), ease: "none", onUpdate: function () { qs.textContent = q.slice(0, Math.round(o.n)); } }, 0.35 * K);
        tl.fromTo(r + ".rv-caret", { opacity: 1 }, { opacity: 0, duration: 0.25, repeat: Math.floor(D / 0.5), yoyo: true, ease: "steps(1)" }, 0);
        tl.to(r + ".rv-btn", { scale: 0.9, duration: 0.09, yoyo: true, repeat: 1, ease: "power1.inOut" }, 1.75 * K);
        tl.fromTo(r + ".rv-chip", { opacity: 0, y: -26, scale: 0.8 }, { opacity: 1, y: 0, scale: 1, duration: 0.45, ease: "back.out(2.4)" }, 1.95 * K);
        tl.to(r + ".rv-wrap", { y: -18, duration: Math.max(0.5, D - 2.5 * K), ease: "sine.inOut" }, 0.5);
        tl.to(r + ".rv-bar, " + r + ".rv-chip", { opacity: 0, y: -30, duration: 0.3, ease: "power2.in" }, D - 0.35);""")

B["lieu-photo"] = block(
    "lieu-photo", "carte photo d'un lieu en verre, nom en haut à gauche, épingle qui tombe et pulse ; ex. Marbella vue du ciel", 3.5,
    [{"id": "image", "type": "string", "label": "Photo du lieu (assets/…)", "default": PIX},
     {"id": "name", "type": "string", "label": "Nom du lieu", "default": "Marbella"},
     {"id": "pinx", "type": "number", "label": "Épingle x (%)", "default": 62, "min": 0, "max": 100},
     {"id": "piny", "type": "number", "label": "Épingle y (%)", "default": 42, "min": 0, "max": 100}],
    f"""      <div class="mf-pos"><div class="lp-card"><div class="lp-ph"><img class="lp-img" data-var-src="image" src="{PIX}" alt="" /></div>
        <div class="lp-name" data-var-text="name">Marbella</div><div class="lp-pin">{PIN}<i class="lp-ring"></i></div></div></div>""",
    f"""        #lieu-photo .mf-pos {{ perspective: 160vmin; }}
        #lieu-photo .lp-card {{ position: relative; width: 78%; aspect-ratio: 16 / 10; padding: 1.2vmin; border-radius: 3.6vmin; {GLASS} opacity: 0; transform-origin: 50% 0; }}
        #lieu-photo .lp-ph {{ width: 100%; height: 100%; border-radius: 2.6vmin; overflow: hidden; }}
        #lieu-photo .lp-img {{ width: 100%; height: 100%; object-fit: cover; display: block; transform-origin: 50% 50%; }}
        #lieu-photo .lp-name {{ position: absolute; left: 4vmin; top: 3.4vmin; color: #fff; font-size: 4vmin; font-weight: 700; text-shadow: 0 0.3vmin 1.4vmin rgba(0,0,0,.55); }}
        #lieu-photo .lp-pin {{ position: absolute; width: 7vmin; height: 7vmin; margin: -7vmin 0 0 -3.5vmin; color: var(--accent);
                               filter: drop-shadow(0 0.6vmin 1vmin rgba(0,0,0,.4)); opacity: 0; }}
        #lieu-photo .lp-pin svg {{ width: 100%; height: 100%; position: relative; z-index: 1; }}
        #lieu-photo .lp-ring {{ position: absolute; left: 50%; bottom: -0.6vmin; width: 6vmin; height: 2vmin; margin-left: -3vmin; border-radius: 50%;
                                border: 0.4vmin solid var(--accent); opacity: 0; }}""",
    """        const pin = document.querySelector(r + ".lp-pin");
        pin.style.left = (Number(v.pinx) || 62) + "%"; pin.style.top = (Number(v.piny) || 42) + "%";
        tl.fromTo(r + ".lp-card", { opacity: 0, y: -50, rotationX: 28, scale: 0.94 }, { opacity: 1, y: 0, rotationX: 0, scale: 1, duration: 0.6, ease: "power3.out" }, 0);
        tl.fromTo(r + ".lp-img", { scale: 1.16 }, { scale: 1.0, duration: D, ease: "none" }, 0);
        tl.fromTo(r + ".lp-pin", { opacity: 0, y: -90 }, { opacity: 1, y: 0, duration: 0.5, ease: "bounce.out" }, 0.55 * K);
        tl.fromTo(r + ".lp-ring", { opacity: 0.9, scale: 0.4 }, { opacity: 0, scale: 2.2, duration: 0.8, repeat: 2, ease: "power2.out" }, 1.0 * K);
        tl.to(r + ".lp-card", { y: -14, duration: Math.max(0.5, D - 1.2), ease: "sine.inOut" }, 0.6);
        tl.to(r + ".lp-card", { opacity: 0, scale: 0.94, duration: 0.3, ease: "power2.in" }, D - 0.35);""")

B["cartes-3d"] = block(
    "cartes-3d", "deux cartes photo en verre inclinées en 3D de chaque côté de la personne, qui flottent ; pastille au-dessus de chacune", 3.6,
    [{"id": "image1", "type": "string", "label": "Photo gauche (assets/…)", "default": PIX},
     {"id": "image2", "type": "string", "label": "Photo droite (assets/…)", "default": PIX},
     {"id": "label1", "type": "string", "label": "Pastille gauche (vide = aucune)", "default": ""},
     {"id": "label2", "type": "string", "label": "Pastille droite (vide = aucune)", "default": ""}],
    f"""      <div class="c3-stage"><div class="c3 c3l"><span class="c3-lab" data-var-text="label1"></span><div class="c3-f"><img data-var-src="image1" src="{PIX}" alt="" /></div></div>
        <div class="c3 c3r"><span class="c3-lab" data-var-text="label2"></span><div class="c3-f"><img data-var-src="image2" src="{PIX}" alt="" /></div></div></div>""",
    f"""        #cartes-3d .c3-stage {{ position: absolute; left: 0; right: 0; top: calc(var(--top, 30) * 1%); height: 30%; perspective: 120vmin; }}
        #cartes-3d .c3 {{ position: absolute; top: 0; width: 34%; visibility: hidden; }}
        #cartes-3d .c3l {{ left: 3%; transform-origin: 0 50%; }}
        #cartes-3d .c3r {{ right: 3%; transform-origin: 100% 50%; }}
        #cartes-3d .c3-f {{ aspect-ratio: 4 / 5; padding: 1vmin; border-radius: 3vmin; {GLASS} }}
        #cartes-3d .c3-f img {{ width: 100%; height: 100%; object-fit: cover; border-radius: 2.2vmin; display: block; }}
        #cartes-3d .c3-lab {{ display: inline-block; margin: 0 0 1.4vmin 1vmin; padding: 0.8vmin 2vmin; border-radius: 99px; {GLASS} color: #fff;
                              font-size: 3vmin; font-weight: 700; white-space: nowrap; }}
        #cartes-3d .c3-lab:empty {{ display: none; }}""",
    """        tl.set(r + ".c3", { visibility: "visible" }, 0);
        tl.fromTo(r + ".c3l", { x: -520, rotationY: 70 }, { x: 0, rotationY: 24, duration: 0.7, ease: "power3.out" }, 0);
        tl.fromTo(r + ".c3r", { x: 520, rotationY: -70 }, { x: 0, rotationY: -24, duration: 0.7, ease: "power3.out" }, 0.12 * K);
        tl.to(r + ".c3l", { y: -22, rotationY: 18, duration: Math.max(0.6, D - 1.1), ease: "sine.inOut" }, 0.7);
        tl.to(r + ".c3r", { y: 18, rotationY: -18, duration: Math.max(0.6, D - 1.1), ease: "sine.inOut" }, 0.8);
        tl.fromTo(r + ".c3-lab", { y: 12, scale: 0.6 }, { y: 0, scale: 1, duration: 0.3, stagger: 0.12, ease: "back.out(2)" }, 0.55 * K);
        tl.to(r + ".c3l", { x: -520, rotationY: 60, duration: 0.38, ease: "power2.in" }, D - 0.4);
        tl.to(r + ".c3r", { x: 520, rotationY: -60, duration: 0.38, ease: "power2.in" }, D - 0.4);""")

B["chiffre-verre"] = block(
    "chiffre-verre", "chiffre géant en verre dégradé qui compte, petit texte avant / après en deux tailles, cote fléchée en option ; ex. 6 bedrooms, 20 meter infinity pool", 3.4,
    [{"id": "from", "type": "number", "label": "Départ", "default": 0},
     {"id": "to", "type": "number", "label": "Valeur", "default": 6},
     {"id": "decimals", "type": "number", "label": "Décimales", "default": 0, "min": 0, "max": 2},
     {"id": "unit", "type": "string", "label": "Unité collée au chiffre (€, %, vide)", "default": ""},
     {"id": "before", "type": "string", "label": "Petit texte avant", "default": "beautiful"},
     {"id": "after", "type": "string", "label": "Petit texte après", "default": "bedrooms"},
     {"id": "cote", "type": "string", "label": "Cote fléchée sous le chiffre (vide = aucune)", "default": ""}],
    """      <div class="mf-pos"><div class="cv-box"><div class="cv-before" data-var-text="before">beautiful</div>
        <div class="cv-num"><span class="cv-val">0</span><span class="cv-unit" data-var-text="unit"></span></div>
        <div class="cv-after" data-var-text="after">bedrooms</div>
        <div class="cv-cote"><i class="cv-line"></i><span data-var-text="cote"></span></div></div></div>""",
    """        #chiffre-verre .cv-box { position: relative; display: flex; flex-direction: column; align-items: center; }
        #chiffre-verre .cv-before { align-self: flex-start; margin-left: 8%; font-size: 4.6vmin; font-weight: 400; color: #fff; text-shadow: 0 0.3vmin 1.4vmin rgba(0,0,0,.45); opacity: 0; }
        #chiffre-verre .cv-num { font-size: 30vmin; font-weight: 800; line-height: .9; letter-spacing: -0.04em; white-space: nowrap;
                                 background: linear-gradient(165deg, rgba(255,255,255,.98) 8%, var(--accent) 52%, rgba(255,255,255,.55) 100%);
                                 -webkit-background-clip: text; background-clip: text; color: transparent; -webkit-text-stroke: 0.25vmin rgba(255,255,255,.6);
                                 filter: drop-shadow(0 1.2vmin 2.4vmin rgba(0,0,0,.35)); opacity: 0; }
        #chiffre-verre .cv-unit { font-size: .5em; margin-left: .06em; }
        #chiffre-verre .cv-after { align-self: flex-end; margin: -1vmin 8% 0 0; font-size: 5.4vmin; font-weight: 400; color: #fff; text-shadow: 0 0.3vmin 1.4vmin rgba(0,0,0,.45); opacity: 0; }
        #chiffre-verre .cv-cote { position: relative; width: 70vmin; margin-top: 2.4vmin; text-align: center; color: #fff; font-size: 3.4vmin; opacity: 0;
                                  text-shadow: 0 0.3vmin 1.4vmin rgba(0,0,0,.45); }
        #chiffre-verre .cv-line { display: block; height: 0.35vmin; margin-bottom: 1.4vmin; background: #fff; transform-origin: 50% 50%; position: relative; }
        #chiffre-verre .cv-line::before, #chiffre-verre .cv-line::after { content: ""; position: absolute; top: -1.2vmin; width: 0; height: 0;
                                 border-top: 1.35vmin solid transparent; border-bottom: 1.35vmin solid transparent; }
        #chiffre-verre .cv-line::before { left: -0.4vmin; border-right: 2vmin solid #fff; }
        #chiffre-verre .cv-line::after { right: -0.4vmin; border-left: 2vmin solid #fff; }""",
    """        const el = document.querySelector(r + ".cv-val"), dec = Number(v.decimals) || 0, o = { n: Number(v.from) || 0 };
        const fmt = function (x) { return x.toLocaleString("fr-FR", { minimumFractionDigits: dec, maximumFractionDigits: dec }); };
        ["before", "after"].forEach(function (k) { if (!String(v[k] || "").trim()) document.querySelector(r + ".cv-" + k).style.display = "none"; });
        if (!String(v.cote || "").trim()) document.querySelector(r + ".cv-cote").style.display = "none";
        const box = document.querySelector(r + ".cv-num"), fin = fmt(Number(v.to) || 0) + String(v.unit || "");
        box.style.fontSize = Math.min(30, 86 / Math.max(1, fin.length * 0.58)) + "vmin";  // le chiffre final tient sur la largeur
        el.textContent = fmt(o.n);
        tl.fromTo(r + ".cv-num", { opacity: 0, scale: 1.3 }, { opacity: 1, scale: 1, duration: 0.5, ease: "power3.out" }, 0);
        tl.fromTo(o, { n: Number(v.from) || 0 }, { n: Number(v.to) || 0, duration: Math.max(0.5, 1.1 * K), ease: "power2.out", onUpdate: function () { el.textContent = fmt(o.n); } }, 0.15);
        tl.fromTo(r + ".cv-before", { opacity: 0, x: -20 }, { opacity: 1, x: 0, duration: 0.35, ease: "power2.out" }, 0.2 * K);
        tl.fromTo(r + ".cv-after", { opacity: 0, x: 20 }, { opacity: 1, x: 0, duration: 0.35, ease: "power2.out" }, 0.45 * K);
        tl.fromTo(r + ".cv-cote", { opacity: 0 }, { opacity: 1, duration: 0.2 }, 0.7 * K);
        tl.fromTo(r + ".cv-line", { scaleX: 0 }, { scaleX: 1, duration: 0.6, ease: "power3.inOut" }, 0.7 * K);
        tl.to(r + ".cv-box", { y: -16, duration: Math.max(0.5, D - 1), ease: "sine.inOut" }, 0.5);
        tl.to(r + ".cv-box", { opacity: 0, scale: 0.92, duration: 0.3, ease: "power2.in" }, D - 0.35);""")

B["fin-logo"] = block(
    "fin-logo", "fin de vidéo : la vidéo se floute sous un voile, le logo apparaît au centre avec une ligne de texte (site, slogan)", 3.2,
    [{"id": "logo", "type": "string", "label": "Logo (assets/…)", "default": PIX},
     {"id": "tagline", "type": "string", "label": "Ligne sous le logo (vide = aucune)", "default": ""},
     {"id": "veil", "type": "color", "label": "Voile sur la vidéo floutée", "default": "rgba(255,255,255,.32)"},
     {"id": "ink", "type": "color", "label": "Couleur de la ligne", "default": "#1a1a1a"}],
    f"""      <div class="fl-veil"></div><div class="mf-pos"><div class="fl-box"><img class="fl-logo" data-var-src="logo" src="{PIX}" alt="" />
        <div class="fl-tag" data-var-text="tagline"></div></div></div>""",
    """        #fin-logo .fl-veil { position: absolute; inset: 0; background: var(--veil, rgba(255,255,255,.32)); backdrop-filter: blur(26px) saturate(1.2);
                             -webkit-backdrop-filter: blur(26px) saturate(1.2); opacity: 0; }
        #fin-logo .fl-box { display: flex; flex-direction: column; align-items: center; gap: 3vmin; }
        #fin-logo .fl-logo { width: 62vmin; max-height: 26vmin; object-fit: contain; opacity: 0; }
        #fin-logo .fl-tag { font-size: 4vmin; font-weight: 600; letter-spacing: .04em; color: var(--ink, #1a1a1a); opacity: 0; }""",
    """        if (!String(v.tagline || "").trim()) document.querySelector(r + ".fl-tag").style.display = "none";
        tl.fromTo(r + ".fl-veil", { opacity: 0 }, { opacity: 1, duration: 0.6, ease: "power2.out" }, 0);
        tl.fromTo(r + ".fl-logo", { opacity: 0, scale: 0.88, filter: "blur(10px)" }, { opacity: 1, scale: 1, filter: "blur(0px)", duration: 0.7, ease: "power3.out" }, 0.3 * K);
        tl.fromTo(r + ".fl-tag", { opacity: 0, y: 14 }, { opacity: 1, y: 0, duration: 0.4, ease: "power2.out" }, 0.8 * K);
        tl.to(r + ".fl-logo", { scale: 1.04, duration: Math.max(0.5, D - 1.2), ease: "sine.inOut" }, 1.0 * K);""")

for name, html in B.items():
    d = LIB / name
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{name}.html").write_text(html, encoding="utf-8")
print(len(B), "blocs écrits :", ", ".join(B))

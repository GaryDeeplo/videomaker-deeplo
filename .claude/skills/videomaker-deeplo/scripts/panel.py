"""PANNEAU D'ANIMATION de la mise en page « écran partagé » (layout split) : animation en haut, visage en bas,
sous-titres sur la jointure.

Temps forts (work/<slug>_panels.json), chacun posé sur un MOT dit (jamais un timecode), visible jusqu'au suivant :
  {"type": "title",  "word": "…", "text": "Vos photos ne *vendent* pas", "tag": "LE PROBLÈME", "flash": false, "mark": true}
  {"type": "check",  "word": "…", "title": "Ce qu'on vérifie", "items": ["…", "…", "…"], "stamp": "VALIDÉ", "tag": "…"}
  {"type": "stat",   "word": "…", "value": 1200, "prefix": "+", "suffix": "", "label": "clientes servies", "tag": "…"}
  {"type": "search", "word": "…", "query": "fleuriste lyon", "results": ["Fleurs & Co · 4,9 ★", "…"], "tag": "…"}
  {"type": "image",  "word": "…", "image": "inbox/x.jpg | assets/broll/…", "caption": "…", "tag": "…"}   ("fit": "contain" : capture d'écran entière)
  {"type": "steps",  "word": "…", "items": ["Réservez", "Venez", "Repartez"], "tag": "…"}
  {"type": "icons",  "word": "…", "title": "…", "items": [{"icon": "clock", "label": "1 h"}, {"icon": "heart", "label": "…"}]}
Visuels en plus :
  - pictos Lucide (licence ISC, lucide.dev/icons) : "icon" sur un titre, items {"text": "…", "icon": "nom"} dans check / steps ;
  - "image" : photo OU vidéo (client, site, Pixabay) dans un cadre ; "query": "1-2 mots anglais" sans "image" ->
    panel.py fetch la cherche sur Pixabay (planche de choix, panel.py pick) ;
  - "lottie": {"name": "valide", "x": 78, "y": 72, "size": 26} sur n'importe quel temps fort : emoji animé (library/lottie)
    posé dans la scène (x / y en % de la scène, taille en % de sa largeur).
Maquettes d'interface :
  {"type": "form", "word": "…", "url": "site.be/contact", "title": "Demande de devis",
   "fields": [{"label": "Prénom", "value": "Camille"}], "button": "Envoyer", "done": "Envoyé"}
  {"type": "chat", "word": "…", "title": "Messages", "messages": [{"from": "them", "text": "…"}, {"from": "me", "text": "…"}]}
  {"type": "rank", "word": "…", "title": "Google · coiffeur lyon", "items": [{"text": "Concurrent A", "sub": "…"}, "…"], "highlight": 2, "to": 0}
  {"type": "progress", "word": "…", "label": "/seo audit monsite.be", "to": 128, "unit": "pages", "done": "Audit terminé"}
  {"type": "hub", "word": "…", "title": "…", "center": {"icon": "store"} | {"image": "inbox/logo.png"} | "Texte",
   "items": [{"icon": "mail", "label": "Mails"}, …]}   (8 au plus)
  {"type": "browser", "word": "…", "url": "…", "site": {"title": "…", "sub": "…", "button": "…", "tiles": ["…", "…", "…"]},
   "notes": [{"on": "title", "text": "Titre trop long"}]}   (ou "image": capture + notes {"text", "x", "y", "w", "h"} en %)
  {"type": "funnel", "word": "…", "title": "…", "steps": [{"label": "Accueil", "value": 100}, {"label": "Offre", "value": 70},
   {"label": "Formulaire", "value": 25}, {"label": "Paiement", "value": 12}], "leak": 2, "note": "Vos clients partent ici"}
  {"type": "chart", "word": "…", "title": "Visites du site", "points": [5, 8, 20, 64, 208], "label": "208 / jour", "xlabels": ["janv.", "…"]}
  {"type": "feed", "word": "…", "title": "Commandes", "badge": "EN DIRECT", "items": [{"text": "…", "sub": "il y a 2 min", "icon": "shopping-bag"}]}
  {"type": "palette", "word": "…", "title": "Votre marque"}   (couleurs et police de la charte si "colors" / "font" absents)
  {"type": "repo", "word": "…", "name": "owner/repo", "badge": "Gratuit"}   (étoiles, description, langage, avatar lus sur GitHub si absents)
  {"type": "code", "word": "…", "file": "formatPrice.js", "before": ["…", "…"], "after": ["…"], "label": "-53 % de code"}
  {"type": "paths", "word": "…", "count": 6, "label": "Le plus simple", "start": "Reels d'essai"}   (lignes emmêlées, une droite en accent)
  {"type": "settings", "word": "…", "app": "ChatGPT", "logo": "logo:openai", "title": "Instructions personnalisées",
   "label": "Comment doit-il répondre ?", "text": "<la consigne exacte>", "toggle": "Activer", "action": "save|copy", "done": "Enregistré"}
  {"type": "post", "word": "…", "platform": "x|linkedin|threads", "name": "…", "handle": "@…", "verified": true, "date": "12 nov.",
   "text": "<texte exact de la publication>", "avatar": "inbox/a.jpg" | "logo": "logo:…", "replies": 830, "reposts": 2100, "likes": 12400}
   (citation réelle et datée uniquement, jamais inventée ni attribuée à quelqu'un qui ne l'a pas écrite)
  {"type": "loupe", "word": "…", "title": "Conditions générales", "find": "non remboursables", "label": "Le piège", "text": "<texte du mur>"}
   (mur de texte illisible ; la loupe le parcourt et s'arrête sur "find", qui passe en couleur)
  {"type": "flap", "word": "…", "title": "Départs", "rows": ["+312 %", "EN 30 JOURS"], "sub": "…"}   (tableau à palettes, 14 caractères par ligne)
Alternance : {"type": "face", "word": "…"} -> visage plein écran (coupe franche) jusqu'au temps fort suivant, qui ramène le panneau.
Objets (objets.py) : map (carte du monde), calendar, timeline (montage), invoice (devis), revenue (revenus + paiements),
  clock (chrono minutes / horloge J+) — JSON dans objets.py.
Logos de marques (Simple Icons, CC0) : "icon": "logo:claude" | "logo:github" | "logo:notion"… partout où un picto est accepté
  (hub, listes, en-tête de liste, flux, titres) ; les marques restent à leurs propriétaires (usage informatif).
Liste : "list": {"n": 1, "of": 5, "name": "…", "icon": "…"} sur les temps forts d'un élément -> en-tête « 1 SUR 5 » ;
  "style": "tabs" -> rangée d'onglets numérotés 1 2 3 4 (celui en cours en couleur).
Thèmes : dark (écran partagé), light (écran partagé clair), cards (cartes sur la vidéo plein écran), glass (cartes en verre
dépoli sur la vidéo, visual.panelTheme: "glass" avec layout cards, + cardsBlur), paper (explainer).
Cartes (cards, glass) : entrées variées prises à tour de rôle (pivot 3D, rideau, zoom), sortie dans le sens opposé, la carte
suivante chevauche la sortie ; "side": "left" | "right" pose la carte d'un côté, tournée en 3D.
"word" peut être une suite de mots (« trois hectares ») ; un mot introuvable est signalé dans le rapport (pose: false).
stat : "from": 12 (compte de 12 à value), "style": "glass" (chiffre en dégradé), "dim": "3 ha" (cote fléchée sous le chiffre).
*mot* = mot fort en italique serif. Chiffres, avis, résultats : uniquement des données réelles du client.
Sans fichier : un temps fort « title » par phrase forte (overlays gardés de text.json).

  python panel.py suggest <job> <slug>     # squelette work/<slug>_panels_suggested.json (une entrée par phrase)
  python panel.py fetch   <job> <slug>     # temps forts "image" avec "query" : Pixabay -> planche work/broll/planche.jpg
  python panel.py pick    <job> <slug> <n> <a-f|none>
"""
import html
import json
import re
import shutil
import sys
from pathlib import Path

from common import ROOT, job_dir, out, read_json, word_hit, write_json

VENDOR = ROOT / ".claude" / "skills" / "videomaker-deeplo" / "vendor" / "fonts"
LUCIDE = ROOT / ".claude" / "skills" / "videomaker-deeplo" / "vendor" / "lucide"
SIMPLE = ROOT / ".claude" / "skills" / "videomaker-deeplo" / "vendor" / "simple-icons"


def find_word(words, word, occurrence=1, lo=0.0, hi=1e9):
    """Mot dit (word_hit) ou suite de mots (« trois hectares », « 50 000 ») : -> le premier mot de la suite n° occurrence,
    avec la fin ("end") du dernier ; None si introuvable."""
    from common import _norm_word
    keys = [k for k in (_norm_word(x) for x in re.split(r"\s+", str(word).strip())) if k]
    if len(keys) <= 1:
        return word_hit(words, word, occurrence, lo, hi)

    def parts(w):
        return [x for x in (_norm_word(y) for y in re.split(r"[\s’'\-]+", w["w"])) if x]
    seen = 0
    for i, w in enumerate(words):
        ps = parts(w)
        if not (lo <= w["start"] <= hi) or keys[0] not in ps:
            continue
        stream, kk, j, ok = ps[ps.index(keys[0]):], 0, i, True
        while kk < len(keys):
            if not stream:
                j += 1
                if j >= len(words):
                    ok = False
                    break
                stream = parts(words[j])
                continue
            if stream[0] != keys[kk]:
                ok = False
                break
            stream, kk = stream[1:], kk + 1
        if ok:
            seen += 1
            if seen == int(occurrence):
                return {**w, "end": words[j]["end"]}
    return None


def logo(name):
    """Logo de marque en SVG (Simple Icons, CC0 ; les marques restent à leurs propriétaires) : « logo:claude », « logo:github »."""
    slug = re.sub(r"[^a-z0-9]", "", str(name).lower())
    if not slug:
        return ""
    f = SIMPLE / f"{slug}.svg"
    if not f.exists():
        import urllib.request
        try:
            with urllib.request.urlopen(f"https://cdn.jsdelivr.net/npm/simple-icons@latest/icons/{slug}.svg", timeout=20) as r:
                SIMPLE.mkdir(parents=True, exist_ok=True)
                f.write_bytes(r.read())
        except Exception:  # noqa: BLE001 — logo inconnu : on s'en passe
            return ""
    svg = re.sub(r"<title>.*?</title>", "", f.read_text(encoding="utf-8"))
    return svg.replace("<svg ", '<svg fill="currentColor" width="100%" height="100%" ', 1)


def icon(name):
    """Picto Lucide en SVG inline (téléchargé une fois depuis le paquet npm lucide-static, gardé dans vendor/lucide) ;
    « logo:<marque> » -> logo Simple Icons."""
    if str(name).lower().startswith("logo:"):
        return logo(str(name)[5:])
    name = re.sub(r"[^a-z0-9-]", "", str(name).lower())
    if not name:
        return ""
    f = LUCIDE / f"{name}.svg"
    if not f.exists():
        import urllib.request
        try:
            with urllib.request.urlopen(f"https://cdn.jsdelivr.net/npm/lucide-static@latest/icons/{name}.svg", timeout=20) as r:
                LUCIDE.mkdir(parents=True, exist_ok=True)
                f.write_bytes(r.read())
        except Exception:  # noqa: BLE001 — picto inconnu : on s'en passe
            return ""
    svg = re.sub(r"<!--.*?-->", "", f.read_text(encoding="utf-8"), flags=re.S).strip()
    return re.sub(r'\swidth="24"\s+height="24"', ' width="100%" height="100%"', svg, count=1)


def glue(text):
    """Texte court à l'écran : espace insécable avant ? ! : ; » et après un petit mot (de, la, à…), pour que la
    ligne ne se coupe jamais au mauvais endroit."""
    from build_text import HARD, deac
    nb = " "
    t = re.sub(r"\s+([?!:;»])", nb + r"\1", str(text))
    t = re.sub(r"«\s+", "«" + nb, t)
    ws = t.split(" ")
    return "".join(w + ((nb if deac(re.sub(r"[^\w'’]", "", w).lower()) in HARD else " ") if i + 1 < len(ws) else "")
                   for i, w in enumerate(ws))


def item_text(it):
    return glue(it.get("text") or it.get("label") or "" if isinstance(it, dict) else str(it))


def item_icon(it):
    return icon(it.get("icon")) if isinstance(it, dict) and it.get("icon") else ""


def media_box(W, ph, theme):
    """Intérieur du cadre « image » (mêmes valeurs que le CSS), pour poser une vidéo hors du temps fort minuté."""
    u = W / 1080
    if theme == "paper":
        l, t, b, bw, rad = round(110 * u), round(ph * 0.12), round(ph * 0.16), max(2, round(3 * u)), round(10 * u)
    elif theme in ("light", "cards", "glass"):
        l, t, b, bw, rad = round(110 * u), round(ph * 0.12), round(ph * 0.16), 1, round(26 * u)
    else:
        l, t, b, bw, rad = round(110 * u), round(120 * u), round(ph * 0.14), 2, round(24 * u)
    return l + bw, t + bw, W - 2 * l - 2 * bw, ph - t - b - 2 * bw, max(0, rad - bw)


def esc(s):
    return html.escape(str(s), quote=True)


def _hex(c):
    c = c.lstrip("#")
    return [int(c[i:i + 2], 16) for i in (0, 2, 4)] if len(c) == 6 else [128, 128, 128]


def _mix(a, b, t):
    pa, pb = _hex(a), _hex(b)
    return "#" + "".join(f"{round(pa[i] * (1 - t) + pb[i] * t):02x}" for i in range(3))


def _lum(c):
    r, g, b = _hex(c)
    return 0.299 * r + 0.587 * g + 0.114 * b


def _contrast(a, b):
    def rl(c):
        v = [x / 255 for x in _hex(c)]
        v = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in v]
        return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]
    la, lb = sorted((rl(a), rl(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def colors(vis):
    """Fond sombre teinté par la charte ; accent assez lumineux pour se lire sur ce fond."""
    acc = vis.get("panelAccent") or vis.get("accentColor", "#7CE3A1")
    if _lum(acc) < 110:  # accent sombre (espresso, marine) : on l'éclaircit pour le panneau
        acc = _mix(acc, "#ffffff", 0.45)
    base = vis.get("panelBg") or _mix("#0b0c0e", acc, 0.035)  # presque noir : l'accent ne vit que dans la lueur
    return base, _mix(base, acc, 0.16), acc, ("#111111" if _lum(acc) > 160 else "#ffffff")


def fonts(job):
    d = job / "assets" / "fonts"
    d.mkdir(parents=True, exist_ok=True)
    for f in ("InstrumentSerif-Italic.ttf", "IBMPlexMono-Medium.ttf"):
        shutil.copy2(VENDOR / f, d / f)
    return ("@font-face { font-family: 'Instrument Serif'; src: url('assets/fonts/InstrumentSerif-Italic.ttf'); font-style: italic; font-weight: 400; } "
            "@font-face { font-family: 'IBM Plex Mono'; src: url('assets/fonts/IBMPlexMono-Medium.ttf'); font-weight: 500; }")


def css(W, ph, fam, vis):
    base, tint, acc, on_acc = colors(vis)
    u = W / 1080
    from fonts import title_stack, title_weight
    tfont = (f"\n  .ttl, .big {{ font-family: {title_stack(vis, fam)}; font-weight: {title_weight(vis)}; }}  /* police des titres de la charte */"
             if (vis.get("titleFont") or {}).get("family") else "")
    noise = ("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='240' height='240'><filter id='n'>"
             "<feTurbulence type='fractalNoise' baseFrequency='.9' numOctaves='2' stitchTiles='stitch'/></filter>"
             "<rect width='100%' height='100%' filter='url(%23n)' opacity='.55'/></svg>")
    return f"""
  #panel {{ position: absolute; left: 0; top: 0; width: {W}px; height: {ph}px; overflow: hidden; z-index: 20; background: {base};
           font-family: '{fam}', 'Inter', sans-serif; color: #f4f4f2; }}
  #panel .pbg {{ position: absolute; inset: 0; background: radial-gradient(ellipse 80% 70% at 50% 38%, {tint} 0%, {base} 72%); }}
  #panel .floor {{ position: absolute; left: -{round(W*0.5)}px; width: {round(W*2)}px; height: {round(ph*1.6)}px; top: {round(ph*0.52)}px;
           transform-origin: 50% 0; transform: perspective({round(900*u)}px) rotateX(64deg); overflow: hidden; opacity: .55;
           -webkit-mask-image: linear-gradient(to bottom, transparent 0%, #000 30%, #000 60%, transparent 100%); }}
  #panel .floor .fl {{ position: absolute; left: 0; right: 0; top: 0; height: 600%;
           background-image: linear-gradient({acc}26 2px, transparent 2px), linear-gradient(90deg, {acc}26 2px, transparent 2px);
           background-size: {round(120*u)}px {round(120*u)}px; }}
  #panel .sweep {{ position: absolute; top: -20%; left: -60%; width: 45%; height: 140%; transform: rotate(18deg);
           background: linear-gradient(90deg, transparent, rgba(255,255,255,.06), transparent); }}
  #panel .grain {{ position: absolute; inset: 0; background-image: url("{noise}"); opacity: .10; mix-blend-mode: overlay; }}
  #panel .vig {{ position: absolute; inset: 0; background: radial-gradient(ellipse 90% 85% at 50% 45%, transparent 55%, rgba(0,0,0,.55) 100%); }}
  #panel .flash {{ position: absolute; left: 50%; top: 45%; width: {round(900*u)}px; height: {round(900*u)}px; margin: -{round(450*u)}px 0 0 -{round(450*u)}px;
           border-radius: 50%; background: radial-gradient(circle, rgba(255,255,255,.9) 0%, {acc}55 35%, transparent 70%); opacity: 0; z-index: 9; }}
  .beat {{ position: absolute; inset: 0; z-index: 5; }}
  .beat .bi {{ position: absolute; inset: 0; opacity: 0; }}
  .tag {{ position: absolute; right: {round(56*u)}px; top: {round(52*u)}px; font: 500 {round(24*u)}px 'IBM Plex Mono', monospace; letter-spacing: .14em;
         text-transform: uppercase; color: rgba(244,244,242,.6); display: flex; align-items: center; gap: {round(12*u)}px; }}
  .tag::before {{ content: ""; width: {round(10*u)}px; height: {round(10*u)}px; border-radius: 50%; background: {acc}; box-shadow: 0 0 {round(14*u)}px {acc}; }}
  .ttl {{ position: absolute; left: {round(70*u)}px; right: {round(70*u)}px; top: {round(ph*0.15)}px; font-weight: 800; font-size: {round(112*u)}px;
         line-height: 1.02; letter-spacing: -.025em; text-wrap: balance; }}
  .ttl .w {{ display: inline-block; opacity: 0; margin-right: .22em; }}
  .ttl .it {{ font-family: 'Instrument Serif', Georgia, serif; font-style: italic; font-weight: 400; letter-spacing: 0; color: {acc};
             font-size: 1.12em; }}
  .mark {{ position: absolute; left: 50%; top: {round(ph*0.62)}px; width: {round(150*u)}px; height: {round(150*u)}px; margin-left: -{round(75*u)}px;
          background: {acc}; clip-path: polygon(50% 0%, 61% 39%, 100% 50%, 61% 61%, 50% 100%, 39% 61%, 0% 50%, 39% 39%);
          filter: drop-shadow(0 0 {round(30*u)}px {acc}); opacity: 0; }}
  .card {{ position: absolute; left: {round(70*u)}px; right: {round(70*u)}px; top: {round(ph*0.17)}px; border-radius: {round(26*u)}px;
          background: linear-gradient(180deg, rgba(255,255,255,.085), rgba(255,255,255,.035)); border: 1px solid rgba(255,255,255,.14);
          box-shadow: 0 {round(30*u)}px {round(80*u)}px rgba(0,0,0,.45), inset 0 1px 0 rgba(255,255,255,.12); padding: {round(34*u)}px {round(38*u)}px; }}
  .chead {{ font: 500 {round(24*u)}px 'IBM Plex Mono', monospace; letter-spacing: .12em; text-transform: uppercase; color: rgba(244,244,242,.55);
           margin-bottom: {round(22*u)}px; }}
  .row {{ display: flex; align-items: center; gap: {round(22*u)}px; padding: {round(22*u)}px 0; font-size: {round(56*u)}px; font-weight: 600;
         border-top: 1px solid rgba(255,255,255,.08); opacity: 0; }}
  .box {{ flex: 0 0 auto; width: {round(56*u)}px; height: {round(56*u)}px; border-radius: {round(12*u)}px; border: 2px solid rgba(255,255,255,.35);
         position: relative; }}
  .box i {{ position: absolute; inset: -2px; border-radius: {round(10*u)}px; background: {acc}; display: flex; align-items: center;
           justify-content: center; color: {on_acc}; font-style: normal; font-weight: 900; font-size: {round(32*u)}px; transform: scale(0); }}
  .stamp {{ position: absolute; right: {round(150*u)}px; bottom: {round(ph*0.15)}px; padding: .1em .4em; border: {round(6*u)}px solid {acc}; color: {acc};
           font-weight: 900; font-size: {round(62*u)}px; letter-spacing: .04em; text-transform: uppercase; border-radius: {round(10*u)}px;
           transform: rotate(-8deg); opacity: 0; background: rgba(0,0,0,.25); box-shadow: 0 0 {round(40*u)}px {acc}55; }}
  .big {{ position: absolute; left: 0; right: 0; top: {round(ph*0.22)}px; text-align: center; font-weight: 800; font-size: {round(230*u)}px;
         letter-spacing: -.04em; line-height: 1; font-variant-numeric: tabular-nums; }}
  .big .px {{ color: {acc}; }}
  .stat {{ position: absolute; left: 0; right: 0; top: {round(ph*0.2)}px; display: flex; flex-direction: column; align-items: center;
          gap: {round(22*u)}px; }}
  .stat .big, .stat .bar, .stat .lbl {{ position: static; }}
  .stat .big {{ white-space: nowrap; }}
  .stat .num {{ display: inline-block; text-align: right; }}  /* largeur réservée : le compteur ne glisse pas */
  .stat .bar {{ width: 40%; }}
  .stat .lbl {{ max-width: 84%; text-align: center; text-wrap: balance; }}
  .stat.sg .big {{ background: linear-gradient(180deg, #ffffff 0%, {acc} 100%); -webkit-background-clip: text; background-clip: text; color: transparent;
                  padding: .06em .08em .1em; box-shadow: none; }}
  .stat.sg .big .px {{ color: transparent; }}
  .dim {{ display: flex; flex-direction: column; align-items: center; gap: {round(10*u)}px; width: 52%; }}
  .dim i {{ position: relative; display: block; width: 100%; height: {max(2, round(3*u))}px; background: currentColor; transform: scaleX(0); }}
  .dim i::before, .dim i::after {{ content: ""; position: absolute; top: 50%; margin-top: -{round(11*u)}px; border: {round(11*u)}px solid transparent; }}
  .dim i::before {{ left: -{round(4*u)}px; border-left-width: 0; border-right: {round(18*u)}px solid currentColor; }}
  .dim i::after {{ right: -{round(4*u)}px; border-right-width: 0; border-left: {round(18*u)}px solid currentColor; }}
  .dim span {{ font: 500 {round(28*u)}px 'IBM Plex Mono', monospace; letter-spacing: .12em; text-transform: uppercase; opacity: 0; }}
  .tico {{ display: inline-flex; width: .9em; height: .9em; margin-right: .25em; vertical-align: -.1em; color: {acc}; }}
  .tico svg {{ width: 100%; height: 100%; }}{tfont}
  .lbl {{ position: absolute; left: 0; right: 0; top: {round(ph*0.22 + 250*u)}px; text-align: center; font-family: 'Instrument Serif', Georgia, serif;
         font-style: italic; font-size: {round(70*u)}px; color: rgba(244,244,242,.85); opacity: 0; }}
  .bar {{ position: absolute; left: {round(W*0.3)}px; right: {round(W*0.3)}px; top: {round(ph*0.22 + 236*u)}px; height: {round(6*u)}px;
         background: {acc}; transform-origin: 0 50%; transform: scaleX(0); box-shadow: 0 0 {round(20*u)}px {acc}; }}
  .win {{ padding: 0; overflow: hidden; }}
  .wbar {{ display: flex; align-items: center; gap: {round(12*u)}px; padding: {round(20*u)}px {round(26*u)}px; background: rgba(255,255,255,.05);
          border-bottom: 1px solid rgba(255,255,255,.08); }}
  .wbar b {{ width: {round(16*u)}px; height: {round(16*u)}px; border-radius: 50%; background: rgba(255,255,255,.25); }}
  .field {{ margin: {round(28*u)}px {round(30*u)}px {round(10*u)}px; padding: {round(20*u)}px {round(26*u)}px; border-radius: {round(16*u)}px;
           border: 2px solid {acc}; font-size: {round(50*u)}px; font-weight: 600; min-height: {round(56*u)}px; box-shadow: 0 0 {round(26*u)}px {acc}40; }}
  .field .q::after {{ content: ""; display: inline-block; width: {round(4*u)}px; height: .9em; background: {acc}; margin-left: 4px; vertical-align: -.1em; }}
  .res {{ margin: {round(14*u)}px {round(30*u)}px; padding: {round(18*u)}px {round(24*u)}px; border-radius: {round(14*u)}px;
         background: rgba(255,255,255,.04); font-size: {round(44*u)}px; font-weight: 600; opacity: 0; }}
  .res small {{ display: block; height: {round(10*u)}px; width: 60%; margin-top: {round(12*u)}px; border-radius: 6px; background: rgba(255,255,255,.12); }}
  .res.top {{ border: 1px solid {acc}; box-shadow: 0 0 {round(30*u)}px {acc}40; }}
  .ph {{ position: absolute; left: {round(110*u)}px; right: {round(110*u)}px; top: {round(120*u)}px; bottom: {round(ph*0.14)}px; border-radius: {round(24*u)}px;
        overflow: hidden; border: 2px solid {acc}; box-shadow: 0 0 {round(50*u)}px {acc}44, 0 {round(30*u)}px {round(70*u)}px rgba(0,0,0,.5); }}
  .ph img, .ph video {{ width: 100%; height: 100%; object-fit: cover; display: block; }}
  .cap2 {{ position: absolute; left: 0; right: 0; bottom: {round(ph*0.045)}px; text-align: center; font: 500 {round(26*u)}px 'IBM Plex Mono', monospace;
          letter-spacing: .12em; text-transform: uppercase; color: rgba(244,244,242,.65); }}
  .stp {{ display: flex; align-items: center; gap: {round(26*u)}px; margin: 0 0 {round(22*u)}px; padding: {round(28*u)}px {round(32*u)}px;
         border-radius: {round(22*u)}px; background: rgba(255,255,255,.05); border: 1px solid rgba(255,255,255,.10); font-size: {round(60*u)}px;
         font-weight: 700; opacity: 0; }}
  .stp .n {{ flex: 0 0 auto; width: {round(70*u)}px; height: {round(70*u)}px; border-radius: 50%; display: flex; align-items: center; justify-content: center;
            font: 500 {round(32*u)}px 'IBM Plex Mono', monospace; border: 2px solid rgba(255,255,255,.3); }}
  .stp.on {{ background: {acc}22; border-color: {acc}; }}
  .stp.on .n {{ background: {acc}; color: {on_acc}; border-color: {acc}; }}
  .stps {{ position: absolute; left: {round(80*u)}px; right: {round(80*u)}px; top: {round(ph*0.2)}px; }}
  .ico {{ display: inline-flex; flex: 0 0 auto; width: 1.05em; height: 1.05em; color: {acc}; }}
  .ico svg {{ stroke-width: 2.2; }}
  .stp .n svg {{ width: 62%; height: 62%; }}
  .bigico {{ position: absolute; left: 50%; top: {round(ph*0.58)}px; width: {round(190*u)}px; height: {round(190*u)}px; margin-left: -{round(95*u)}px;
            color: {acc}; opacity: 0; filter: drop-shadow(0 0 {round(24*u)}px {acc}66); }}
  .igrid {{ position: absolute; left: {round(60*u)}px; right: {round(60*u)}px; top: {round(ph*0.2)}px; display: grid; gap: {round(46*u)}px {round(30*u)}px; }}
  .ic {{ text-align: center; opacity: 0; }}
  .ic .cir {{ width: {round(200*u)}px; height: {round(200*u)}px; border-radius: 50%; margin: 0 auto; background: {acc}; color: {on_acc};
             display: flex; align-items: center; justify-content: center; box-shadow: 0 {round(14*u)}px {round(40*u)}px {acc}55; }}
  .ic .cir svg {{ width: 50%; height: 50%; stroke-width: 2; }}
  .ic .lab {{ margin-top: {round(22*u)}px; font-size: {round(46*u)}px; font-weight: 700; line-height: 1.1; }}
  .ihead {{ position: absolute; left: 0; right: 0; top: {round(ph*0.08)}px; text-align: center; font: 500 {round(26*u)}px 'IBM Plex Mono', monospace;
           letter-spacing: .12em; text-transform: uppercase; opacity: .65; }}
  .kick {{ font: 500 {round(24*u)}px 'IBM Plex Mono', monospace; letter-spacing: .16em; text-transform: uppercase; color: {acc}; margin-bottom: {round(18*u)}px;
          opacity: 0; }}
  .kick.kabs {{ position: absolute; left: {round(70*u)}px; right: {round(70*u)}px; top: {round(ph*0.09)}px; margin: 0; }}
  .thread {{ position: absolute; left: 0; top: 0; z-index: 4; overflow: visible; pointer-events: none; }}
  .thread .thp {{ fill: none; stroke: {acc}; stroke-width: {max(2, round(4*u))}; stroke-linecap: round; stroke-dasharray: 1000; opacity: .85; }}
  .thread .thd {{ fill: {acc}; filter: drop-shadow(0 0 {round(10*u)}px {acc}); }}
  .hud {{ position: absolute; z-index: 8; font: 500 {round(18*u)}px 'IBM Plex Mono', monospace; letter-spacing: .14em; text-transform: uppercase;
         color: rgba(140,140,140,.85); }}
  .hud.tl {{ left: {round(30*u)}px; top: {round(22*u)}px; }}
  .hud.tr {{ right: {round(30*u)}px; top: {round(22*u)}px; }}
  .hud.bl {{ left: {round(30*u)}px; bottom: {round(84*u)}px; }}
  .hud.br {{ right: {round(30*u)}px; bottom: {round(84*u)}px; }}
  .paperbg {{ position: absolute; inset: 0; z-index: 3; opacity: 0; background-color: #f3f1ec;
             background-image: linear-gradient(rgba(20,20,20,.06) 1px, transparent 1px), linear-gradient(90deg, rgba(20,20,20,.06) 1px, transparent 1px);
             background-size: {round(56*u)}px {round(56*u)}px; }}
  .beat.pb {{ color: #151515; --ui-ink: #151515; --ui-line: rgba(21,21,21,.14); --ui-soft: rgba(21,21,21,.05); --ui-mute: rgba(21,21,21,.6); --ui-solid: #ffffff; }}
  .beat.pb .card {{ background: #fff; border: 1px solid rgba(21,21,21,.1); box-shadow: 0 {round(18*u)}px {round(50*u)}px rgba(0,0,0,.12); }}
  .beat.pb .chead, .beat.pb .ihead, .beat.pb .tag, .beat.pb .cap2 {{ color: rgba(21,21,21,.6); opacity: 1; }}
  .beat.pb .lbl {{ color: #151515; }}
  .beat.pb .row {{ border-top-color: rgba(21,21,21,.1); }}
  .beat.pb .box {{ border-color: rgba(21,21,21,.35); }}
  .beat.pb .stp {{ background: #fff; border-color: rgba(21,21,21,.12); }}
  .beat.pb .res {{ background: rgba(21,21,21,.04); }}
  .beat.pb .res small {{ background: rgba(21,21,21,.12); }}
  .beat.pb .wbar {{ background: rgba(21,21,21,.04); border-bottom-color: rgba(21,21,21,.1); }}
  .beat.pb .wbar b {{ background: rgba(21,21,21,.25); }}
  .beat.pb .kick {{ color: {_mix(acc, "#151515", 0.55) if _lum(acc) > 120 else acc}; }}
  .beat.pb .lbl {{ color: #151515; }}
  .beat.pb .big .px, .beat.pb .ttl .it {{ color: {_mix(acc, "#151515", 0.25) if _lum(acc) > 165 else acc}; }}""" + css_ui(W, ph, acc, on_acc)


def css_ui(W, ph, acc, on_acc):
    """Maquettes d'interface (formulaire, chat, classement, progression, étoile d'icônes, site annoté) et en-tête de
    liste « 1 SUR 5 ». Couleurs en variables : le thème papier / clair ne redéfinit que les variables."""
    u = W / 1080
    rh = round(104 * u)
    mono = "'IBM Plex Mono', monospace"
    return f"""
  #panel {{ --acc: {acc}; --on-acc: {on_acc}; --ui-ink: #f4f4f2; --ui-line: rgba(255,255,255,.13); --ui-soft: rgba(255,255,255,.07);
           --ui-mute: rgba(244,244,242,.55); --ui-solid: #17181b; }}
  .url {{ margin-left: {round(14*u)}px; flex: 1; padding: {round(8*u)}px {round(18*u)}px; border-radius: 999px; background: var(--ui-soft);
         font: 500 {round(24*u)}px {mono}; color: var(--ui-mute); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
  .fbody {{ padding: {round(26*u)}px {round(34*u)}px {round(32*u)}px; }}
  .ftitle {{ font-size: {round(50*u)}px; font-weight: 800; margin-bottom: {round(16*u)}px; }}
  .ff {{ margin-bottom: {round(16*u)}px; }}
  .ff label {{ display: block; font: 500 {round(24*u)}px {mono}; letter-spacing: .08em; text-transform: uppercase; color: var(--ui-mute);
              margin-bottom: {round(8*u)}px; }}
  .fv {{ height: {round(76*u)}px; border-radius: {round(14*u)}px; border: 2px solid var(--ui-line); padding: 0 {round(22*u)}px; display: flex;
        align-items: center; font-size: {round(42*u)}px; font-weight: 600; }}
  .fv .q::after {{ content: ""; display: inline-block; width: {round(4*u)}px; height: .9em; background: var(--acc); margin-left: 4px; vertical-align: -.1em; opacity: 0; }}
  .fv.on {{ border-color: var(--acc); box-shadow: 0 0 0 {round(5*u)}px {acc}33; }}
  .fv.on .q::after {{ opacity: 1; }}
  .fbtn {{ margin-top: {round(8*u)}px; height: {round(86*u)}px; border-radius: {round(16*u)}px; background: var(--acc); color: var(--on-acc);
          font-size: {round(42*u)}px; font-weight: 800; display: flex; align-items: center; justify-content: center; position: relative; overflow: hidden; }}
  .fbtn .t2 {{ position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; background: #1f9d55; color: #fff; opacity: 0; }}
  .hand {{ position: absolute; left: 0; top: 0; width: {round(84*u)}px; height: {round(84*u)}px; color: var(--ui-ink); z-index: 4; opacity: 0;
          filter: drop-shadow(0 {round(6*u)}px {round(10*u)}px rgba(0,0,0,.35)); }}
  .hand svg {{ fill: var(--ui-solid); stroke-width: 1.6; }}
  .chat .msg {{ display: flex; margin: {round(14*u)}px 0; opacity: 0; }}
  .chat .msg span {{ max-width: 80%; padding: {round(20*u)}px {round(26*u)}px; border-radius: {round(28*u)}px; font-size: {round(42*u)}px;
                    font-weight: 600; line-height: 1.2; }}
  .chat .them span {{ background: var(--ui-soft); border: 1px solid var(--ui-line); border-bottom-left-radius: {round(8*u)}px; }}
  .chat .me {{ justify-content: flex-end; }}
  .chat .me span {{ background: var(--acc); color: var(--on-acc); border-bottom-right-radius: {round(8*u)}px; }}
  .dots i {{ display: inline-block; width: {round(14*u)}px; height: {round(14*u)}px; margin: 0 {round(4*u)}px; border-radius: 50%; background: currentColor; opacity: .5; }}
  .rk {{ position: relative; }}
  .rrow {{ position: absolute; left: {round(70*u)}px; right: 0; height: {rh - round(14*u)}px; display: flex; align-items: center; gap: {round(18*u)}px;
          padding: 0 {round(24*u)}px; border-radius: {round(16*u)}px; background: var(--ui-soft); border: 1px solid var(--ui-line);
          font-size: {round(42*u)}px; font-weight: 700; opacity: 0; white-space: nowrap; overflow: hidden; }}
  .rrow small {{ margin-left: auto; font: 500 {round(24*u)}px {mono}; color: var(--ui-mute); }}
  .rrow.hl {{ background: var(--acc); color: var(--on-acc); border-color: var(--acc); box-shadow: 0 {round(12*u)}px {round(30*u)}px {acc}55; z-index: 2; }}
  .rrow.hl small {{ color: inherit; opacity: .8; }}
  .rnum {{ position: absolute; left: 0; width: {round(54*u)}px; height: {rh - round(14*u)}px; display: flex; align-items: center; justify-content: center;
          font: 500 {round(30*u)}px {mono}; color: var(--ui-mute); }}
  .cmd {{ font: 500 {round(38*u)}px {mono}; padding: {round(22*u)}px {round(26*u)}px; border-radius: {round(14*u)}px; background: var(--ui-soft);
         border: 1px solid var(--ui-line); min-height: {round(50*u)}px; }}
  .cmd .q::after {{ content: ""; display: inline-block; width: {round(4*u)}px; height: .9em; background: var(--acc); margin-left: 4px; vertical-align: -.1em; }}
  .pbar {{ margin-top: {round(30*u)}px; height: {round(22*u)}px; border-radius: 99px; background: var(--ui-soft); overflow: hidden; }}
  .pbar i {{ display: block; height: 100%; background: var(--acc); transform-origin: 0 50%; transform: scaleX(0); border-radius: inherit; }}
  .pmeta {{ margin-top: {round(16*u)}px; display: flex; justify-content: space-between; font: 500 {round(28*u)}px {mono}; color: var(--ui-mute); }}
  .pdone {{ margin-top: {round(26*u)}px; display: inline-flex; align-items: center; gap: {round(12*u)}px; padding: {round(12*u)}px {round(24*u)}px;
           border-radius: 99px; background: #1f9d55; color: #fff; font-size: {round(36*u)}px; font-weight: 800; opacity: 0; }}
  .hubl {{ position: absolute; left: 0; top: 0; overflow: visible; }}
  .hubl line {{ stroke: var(--acc); stroke-width: {max(2, round(4*u))}px; stroke-linecap: round; }}
  .hc, .hs {{ position: absolute; border-radius: 50%; display: flex; align-items: center; justify-content: center; opacity: 0; }}
  .hc {{ background: var(--acc); color: var(--on-acc); box-shadow: 0 0 {round(50*u)}px {acc}66; font-weight: 800; text-align: center; overflow: hidden; }}
  .hc svg {{ width: 52%; height: 52%; }}
  .hc img {{ width: 72%; height: 72%; object-fit: contain; }}
  .hs {{ background: var(--ui-solid); border: 2px solid var(--ui-line); color: var(--acc); }}
  .hs svg {{ width: 50%; height: 50%; }}
  .hlab {{ position: absolute; text-align: center; white-space: nowrap; font-size: {round(30*u)}px; font-weight: 700; color: var(--ui-ink); opacity: 0; }}
  .site .hero {{ margin: {round(24*u)}px; padding: {round(38*u)}px {round(34*u)}px; border-radius: {round(18*u)}px; background: var(--acc); color: var(--on-acc); }}
  .site .h1 {{ font-size: {round(62*u)}px; font-weight: 800; line-height: 1.05; position: relative; display: inline-block; }}
  .site .h2 {{ margin-top: {round(14*u)}px; font-size: {round(34*u)}px; opacity: .85; position: relative; display: inline-block; }}
  .site .btn {{ margin-top: {round(24*u)}px; display: table; padding: {round(14*u)}px {round(28*u)}px; border-radius: {round(12*u)}px; background: var(--ui-solid);
               color: var(--ui-ink); font-size: {round(34*u)}px; font-weight: 800; position: relative; }}
  .site .tiles {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: {round(16*u)}px; margin: 0 {round(24*u)}px {round(28*u)}px; }}
  .site .tiles div {{ padding: {round(22*u)}px {round(16*u)}px; border-radius: {round(14*u)}px; background: var(--ui-soft); border: 1px solid var(--ui-line);
                     font-size: {round(30*u)}px; font-weight: 700; position: relative; }}
  .site .shotw {{ position: relative; margin: {round(24*u)}px; border-radius: {round(14*u)}px; overflow: visible; }}
  .site .shotw img {{ display: block; width: 100%; max-height: {round(ph*0.5)}px; object-fit: cover; object-position: top; border-radius: {round(14*u)}px; }}
  .note {{ position: absolute; right: -{round(10*u)}px; top: -{round(36*u)}px; padding: {round(6*u)}px {round(14*u)}px; border-radius: {round(8*u)}px;
          background: #d62f33; color: #fff; font: 700 {round(26*u)}px 'Inter', sans-serif; white-space: nowrap; transform: rotate(-3deg); opacity: 0; z-index: 3; }}
  .note.side {{ right: auto; left: calc(100% + {round(18*u)}px); top: 50%; margin-top: -.8em; }}
  .ring {{ position: absolute; inset: -{round(8*u)}px; border: {max(2, round(4*u))}px solid #d62f33; border-radius: {round(12*u)}px; opacity: 0; pointer-events: none; }}
  #panel.haslist .beat .bi {{ top: {round(128*u)}px; }}
  .lhead {{ position: absolute; left: 0; right: 0; top: {round(34*u)}px; height: {round(96*u)}px; z-index: 6; }}
  .lhead .ll {{ position: absolute; left: {round(130*u)}px; right: {round(130*u)}px; top: {round(47*u)}px; height: {max(2, round(4*u))}px; background: var(--acc);
               transform: scaleX(0); }}
  .lhead .le {{ position: absolute; top: {round(10*u)}px; width: {round(76*u)}px; height: {round(76*u)}px; border-radius: 50%; background: var(--ui-solid);
               border: 2px solid var(--acc); color: var(--acc); display: flex; align-items: center; justify-content: center; opacity: 0; }}
  .lhead .le svg {{ width: 52%; height: 52%; }}
  .lhead .le.l {{ left: {round(54*u)}px; }}
  .lhead .le.r {{ right: {round(54*u)}px; }}
  .lhead .lp {{ position: absolute; left: 50%; top: 0; transform: translateX(-50%); padding: {round(8*u)}px {round(30*u)}px {round(10*u)}px;
               border-radius: {round(16*u)}px; border: 2px solid var(--acc); background: var(--ui-solid); text-align: center; white-space: nowrap; opacity: 0; }}
  .lhead .lp small {{ display: block; font: 500 {round(20*u)}px {mono}; letter-spacing: .14em; color: var(--ui-mute); }}
  .lhead .lp b {{ display: block; font-size: {round(42*u)}px; font-weight: 800; line-height: 1.1; color: var(--ui-ink); }}
  .ltabs {{ position: absolute; left: 50%; top: {round(10*u)}px; transform: translateX(-50%); display: flex; align-items: center; gap: {round(10*u)}px;
           padding: {round(10*u)}px {round(14*u)}px; border-radius: {round(18*u)}px; background: var(--ui-solid); border: 1px solid var(--ui-line);
           box-shadow: 0 {round(10*u)}px {round(30*u)}px rgba(0,0,0,.18); white-space: nowrap; opacity: 0; }}
  .ltabs i {{ font: 600 {round(30*u)}px {mono}; font-style: normal; width: {round(56*u)}px; height: {round(56*u)}px; border-radius: {round(12*u)}px;
             display: flex; align-items: center; justify-content: center; color: var(--ui-mute); }}
  .ltabs i.on {{ background: var(--acc); color: var(--on-acc); }}
  .ltabs b {{ margin: 0 {round(10*u)}px 0 {round(6*u)}px; font-size: {round(36*u)}px; font-weight: 800; color: var(--ui-ink); }}
  .fun {{ position: absolute; left: {round(70*u)}px; right: {round(70*u)}px; top: {round(ph*0.2)}px; height: {round(ph*0.56)}px; }}
  .fbar {{ position: absolute; bottom: {round(60*u)}px; border-radius: {round(12*u)}px {round(12*u)}px 0 0; background: var(--acc); transform-origin: 50% 100%; }}
  .fbar.leak {{ background: #d62f33; }}
  .flab {{ position: absolute; bottom: 0; text-align: center; font-weight: 700; color: var(--ui-ink); line-height: 1.08; text-wrap: balance;
          overflow-wrap: anywhere; display: flex; align-items: flex-start; justify-content: center; }}  /* deux lignes au plus, jamais sur le voisin */
  .fval {{ position: absolute; text-align: center; font: 600 {round(28*u)}px {mono}; color: var(--ui-mute); opacity: 0; }}
  .fdot {{ position: absolute; width: {round(12*u)}px; height: {round(12*u)}px; border-radius: 50%; background: var(--ui-mute); opacity: 0; }}
  .fnote {{ position: absolute; padding: {round(10*u)}px {round(20*u)}px; border-radius: {round(12*u)}px; background: #d62f33; color: #fff; font-size: {round(32*u)}px;
           font-weight: 800; line-height: 1.1; text-align: center; transform: rotate(-3deg); opacity: 0; box-sizing: border-box; }}
  .chartc svg {{ display: block; overflow: visible; }}
  .chartc .gl {{ stroke: var(--ui-line); stroke-width: {max(1, round(2*u))}; }}
  .chartc .gt {{ font: 500 {round(22*u)}px {mono}; fill: var(--ui-mute); }}
  .chartc .ln {{ fill: none; stroke: var(--acc); stroke-width: {round(6*u)}; stroke-linejoin: round; stroke-linecap: round; stroke-dasharray: 1000; }}
  .chartc .dot {{ fill: var(--acc); }}
  .chartc .cval {{ position: absolute; padding: {round(6*u)}px {round(16*u)}px; border-radius: 99px; border: 2px solid var(--acc); background: var(--ui-solid);
                  font-size: {round(34*u)}px; font-weight: 800; color: var(--ui-ink); white-space: nowrap; opacity: 0; }}
  .live {{ position: absolute; right: {round(34*u)}px; top: {round(30*u)}px; display: inline-flex; align-items: center; gap: {round(10*u)}px;
          padding: {round(6*u)}px {round(16*u)}px; border-radius: 99px; background: #d62f33; color: #fff; font: 700 {round(22*u)}px {mono}; letter-spacing: .08em; }}
  .live::before {{ content: ""; width: {round(12*u)}px; height: {round(12*u)}px; border-radius: 50%; background: #fff; }}
  .feed {{ position: relative; overflow: hidden; }}
  .fi {{ position: absolute; left: 0; right: 0; display: flex; align-items: center; gap: {round(18*u)}px; padding: {round(16*u)}px {round(20*u)}px;
        border-radius: {round(16*u)}px; background: var(--ui-soft); border: 1px solid var(--ui-line); opacity: 0; }}
  .fi .fic {{ flex: 0 0 auto; width: {round(64*u)}px; height: {round(64*u)}px; border-radius: 50%; background: var(--acc); color: var(--on-acc);
             display: flex; align-items: center; justify-content: center; }}
  .fi .fic svg {{ width: 52%; height: 52%; }}
  .fi b {{ display: block; font-size: {round(36*u)}px; font-weight: 700; line-height: 1.15; }}
  .fi small {{ display: block; font: 500 {round(22*u)}px {mono}; color: var(--ui-mute); margin-top: {round(4*u)}px; }}
  .sw {{ display: flex; gap: {round(16*u)}px; margin: {round(10*u)}px 0 {round(26*u)}px; }}
  .sw i {{ flex: 1; height: {round(130*u)}px; border-radius: {round(16*u)}px; border: 1px solid var(--ui-line); opacity: 0; }}
  .swf {{ display: flex; align-items: baseline; gap: {round(24*u)}px; }}
  .swf .aa {{ font-size: {round(150*u)}px; line-height: .9; font-weight: 700; }}
  .swf span {{ font: 500 {round(26*u)}px {mono}; color: var(--ui-mute); }}
  .rhead {{ display: flex; align-items: center; gap: {round(18*u)}px; }}
  .rav {{ flex: 0 0 auto; width: {round(72*u)}px; height: {round(72*u)}px; border-radius: 50%; background: var(--acc); color: var(--on-acc); overflow: hidden;
         display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: {round(34*u)}px; }}
  .rav img {{ width: 100%; height: 100%; object-fit: cover; }}
  .rav svg {{ width: 56%; height: 56%; }}
  .rname {{ flex: 1; font-size: {round(40*u)}px; line-height: 1.1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
  .rname small {{ font-size: .8em; color: var(--ui-mute); }}
  .rstar {{ flex: 0 0 auto; display: inline-flex; align-items: center; gap: {round(10*u)}px; padding: {round(8*u)}px {round(18*u)}px; border-radius: {round(12*u)}px;
           border: 1px solid var(--ui-line); background: var(--ui-soft); font: 600 {round(28*u)}px {mono}; }}
  .rstar.on {{ background: var(--acc); color: var(--on-acc); border-color: var(--acc); }}
  .rdesc {{ margin-top: {round(18*u)}px; font-size: {round(34*u)}px; color: var(--ui-mute); line-height: 1.25; }}
  .rmeta {{ margin-top: {round(18*u)}px; display: flex; align-items: center; gap: {round(16*u)}px; font: 500 {round(26*u)}px {mono}; color: var(--ui-mute); }}
  .rmeta .ld {{ width: {round(18*u)}px; height: {round(18*u)}px; border-radius: 50%; background: var(--acc); }}
  .rmeta .rb {{ padding: {round(4*u)}px {round(14*u)}px; border-radius: 99px; background: #1f9d55; color: #fff; font-weight: 700; }}
  .rbig {{ margin-top: {round(22*u)}px; font-size: {round(96*u)}px; font-weight: 800; line-height: 1; font-variant-numeric: tabular-nums; }}
  .rbig small {{ font-size: .34em; font-weight: 600; color: var(--ui-mute); margin-left: .3em; }}
  .cbody {{ padding: {round(18*u)}px 0 {round(22*u)}px; font: 500 {round(28*u)}px {mono}; }}
  .cl {{ height: {round(44*u)}px; line-height: {round(44*u)}px; padding: 0 {round(26*u)}px; white-space: pre; overflow: hidden; }}
  .cl::before {{ content: attr(data-n); display: inline-block; width: 2.2em; color: var(--ui-mute); opacity: .6; }}
  .cl.add {{ height: 0; background: rgba(31,157,85,.18); }}
  .cl.add::before {{ content: "+"; color: #1f9d55; opacity: 1; }}
  .cstat {{ display: inline-block; margin: 0 0 {round(22*u)}px {round(26*u)}px; padding: {round(10*u)}px {round(22*u)}px; border-radius: 99px; background: var(--acc);
           color: var(--on-acc); font-weight: 800; font-size: {round(34*u)}px; opacity: 0; }}
  .pathsv path {{ fill: none; stroke-linecap: round; }}
  .pathsv .pg {{ stroke: var(--ui-mute); opacity: .45; }}
  .pathsv .pk {{ stroke: var(--ui-ink); opacity: .85; }}
  .pathsv .pa {{ stroke: var(--acc); }}
  .pathsv .ps {{ fill: var(--ui-solid); stroke: var(--ui-ink); stroke-width: {max(2, round(4*u))}; }}
  .plab {{ position: absolute; padding: {round(8*u)}px {round(18*u)}px; border-radius: {round(10*u)}px; font-weight: 800; font-size: {round(30*u)}px; white-space: nowrap;
          opacity: 0; }}
  .plab.e {{ background: var(--acc); color: var(--on-acc); text-transform: uppercase; }}
  .plab.s {{ background: var(--ui-solid); color: var(--ui-ink); border: 2px solid var(--ui-ink); font-size: {round(24*u)}px; text-transform: uppercase; }}
  .sgh {{ display: flex; align-items: center; gap: {round(18*u)}px; padding: {round(26*u)}px {round(34*u)}px {round(10*u)}px; }}
  .sgh .sgl {{ flex: 0 0 auto; width: {round(64*u)}px; height: {round(64*u)}px; border-radius: {round(16*u)}px; background: var(--ui-ink); color: var(--ui-solid);
              display: flex; align-items: center; justify-content: center; }}
  .sgh .sgl svg {{ width: 60%; height: 60%; }}
  .sgn b {{ display: block; font-size: {round(40*u)}px; font-weight: 800; line-height: 1.1; }}
  .sgn small {{ display: block; font: 500 {round(24*u)}px {mono}; color: var(--ui-mute); letter-spacing: .06em; }}
  .sgl2 {{ margin: {round(18*u)}px {round(34*u)}px {round(10*u)}px; font-size: {round(30*u)}px; font-weight: 600; color: var(--ui-mute); }}
  .stx {{ margin: 0 {round(34*u)}px; min-height: {round(160*u)}px; padding: {round(20*u)}px {round(24*u)}px; border-radius: {round(16*u)}px;
         border: 2px solid var(--ui-line); background: var(--ui-soft); font-size: {round(36*u)}px; font-weight: 500; line-height: 1.3; white-space: pre-wrap; }}
  .stx.on {{ border-color: var(--acc); box-shadow: 0 0 0 {round(5*u)}px {acc}33; }}
  .stx .q::after {{ content: ""; display: inline-block; width: {round(4*u)}px; height: .95em; background: var(--acc); margin-left: 3px; vertical-align: -.12em; opacity: 0; }}
  .stx.on .q::after {{ opacity: 1; }}
  .sgt {{ display: flex; align-items: center; justify-content: space-between; margin: {round(22*u)}px {round(34*u)}px 0; font-size: {round(32*u)}px; font-weight: 600; }}
  .sw2 {{ width: {round(84*u)}px; height: {round(46*u)}px; border-radius: 99px; background: var(--ui-line); position: relative; }}
  .sw2 b {{ position: absolute; left: {round(5*u)}px; top: {round(5*u)}px; width: {round(36*u)}px; height: {round(36*u)}px; border-radius: 50%; background: #fff; }}
  .sgt.on .sw2 {{ background: var(--acc); }}
  .sgt.on .sw2 b {{ left: auto; right: {round(5*u)}px; }}
  .sgf {{ display: flex; justify-content: space-between; align-items: center; margin: {round(24*u)}px {round(34*u)}px {round(30*u)}px; }}
  .sgb {{ display: inline-flex; align-items: center; gap: {round(12*u)}px; padding: {round(16*u)}px {round(32*u)}px; border-radius: {round(14*u)}px;
         background: var(--acc); color: var(--on-acc); font-size: {round(36*u)}px; font-weight: 800; }}
  .sgb svg {{ width: {round(34*u)}px; height: {round(34*u)}px; }}
  .sgok {{ padding: {round(12*u)}px {round(26*u)}px; border-radius: 99px; background: #1f9d55;
          color: #fff; font-size: {round(36*u)}px; font-weight: 800; opacity: 0; }}
  .post {{ padding: {round(32*u)}px {round(36*u)}px; }}
  .poh {{ display: flex; align-items: center; gap: {round(18*u)}px; }}
  .pon {{ flex: 1; min-width: 0; }}
  .pon b {{ display: flex; align-items: center; gap: {round(10*u)}px; font-size: {round(38*u)}px; font-weight: 800; line-height: 1.1; }}
  .pon small {{ display: block; font-size: {round(28*u)}px; color: var(--ui-mute); }}
  .pov {{ display: inline-flex; align-items: center; justify-content: center; width: {round(34*u)}px; height: {round(34*u)}px; border-radius: 50%;
         background: #1d9bf0; color: #fff; font-style: normal; font-size: {round(22*u)}px; font-weight: 900; }}
  .pol {{ flex: 0 0 auto; width: {round(44*u)}px; height: {round(44*u)}px; color: var(--ui-ink); }}
  .pot {{ margin-top: {round(24*u)}px; font-size: {round(44*u)}px; font-weight: 500; line-height: 1.28; }}
  .poi {{ margin-top: {round(20*u)}px; border-radius: {round(18*u)}px; overflow: hidden; border: 1px solid var(--ui-line); }}
  .poi img {{ display: block; width: 100%; max-height: {round(ph*0.3)}px; object-fit: cover; }}
  .pos {{ margin-top: {round(26*u)}px; display: flex; gap: {round(40*u)}px; font: 500 {round(28*u)}px {mono}; color: var(--ui-mute); }}
  .pos span {{ display: inline-flex; align-items: center; gap: {round(10*u)}px; }}
  .pos svg {{ width: {round(34*u)}px; height: {round(34*u)}px; }}
  .pos .ps-likes.on {{ color: #f91880; }}
  .pos .ps-likes.on svg {{ fill: #f91880; }}
  .loupe .lpt {{ margin: {round(26*u)}px {round(34*u)}px 0; }}
  .lw {{ position: relative; margin: {round(26*u)}px {round(34*u)}px {round(34*u)}px; }}
  .lr {{ position: absolute; left: 0; right: 0; height: {round(46*u)}px; line-height: {round(46*u)}px; white-space: nowrap; overflow: hidden;
        font-size: {round(30*u)}px; color: var(--ui-mute); }}
  .lr .hit {{ border-radius: {round(6*u)}px; }}
  .lw.found .hit {{ background: var(--acc); color: var(--on-acc); font-weight: 700; padding: 0 .15em; }}
  .lens {{ position: absolute; left: 0; top: 0; border-radius: 50%; overflow: hidden; z-index: 3; opacity: 0; background: var(--ui-solid);
          border: {round(7*u)}px solid var(--acc); box-shadow: 0 {round(20*u)}px {round(50*u)}px rgba(0,0,0,.45), inset 0 0 {round(30*u)}px rgba(0,0,0,.25); }}
  .lens .lz {{ position: absolute; left: 0; top: 0; }}
  .lens .lr {{ color: var(--ui-ink); }}
  .lpl {{ position: absolute; right: {round(30*u)}px; top: {round(16*u)}px; padding: {round(10*u)}px {round(22*u)}px; border-radius: {round(12*u)}px;
         background: #d62f33; color: #fff; font-size: {round(34*u)}px; font-weight: 800; white-space: nowrap; transform: rotate(-3deg); opacity: 0; z-index: 4; }}
  .flap {{ position: absolute; left: {round(70*u)}px; right: {round(70*u)}px; top: {round(ph*0.24)}px; display: flex; flex-direction: column; align-items: center;
          gap: {round(12*u)}px; }}
  .fr {{ display: flex; gap: {round(8*u)}px; opacity: 0; }}
  .fc {{ position: relative; display: flex; align-items: center; justify-content: center; border-radius: {round(8*u)}px; overflow: hidden;
        background: linear-gradient(180deg, #232429 0%, #1a1b1f 50%, #141518 50%, #18191d 100%); font-style: normal;
        box-shadow: 0 {round(8*u)}px {round(20*u)}px rgba(0,0,0,.45); }}
  .fc::after {{ content: ""; position: absolute; left: 0; right: 0; top: 50%; height: {max(2, round(3*u))}px; background: rgba(0,0,0,.65); }}
  .fc b {{ font-family: {mono}; font-weight: 600; color: rgba(244,244,242,.55); line-height: 1; }}
  .fc.set b {{ color: #f4f4f2; }}
  .fsub {{ position: absolute; left: 0; right: 0; top: {round(ph*0.72)}px; text-align: center; font-size: {round(46*u)}px; font-weight: 700; opacity: 0; }}""" + __import__("objets").css(W, ph, acc, on_acc)


def title_words(text):
    """*mot* -> italique serif ; renvoie le HTML des mots."""
    out_ = []
    for m in re.finditer(r"\*([^*]+)\*|(\S+)", text):
        if m.group(1):
            out_ += [f'<span class="w it">{esc(w)}</span>' for w in m.group(1).split()]
        else:
            out_.append(f'<span class="w">{esc(m.group(2))}</span>')
    # un petit mot (de, le, à, ça…) ne finit jamais une ligne : il reste collé au mot suivant
    from build_text import WEAK, deac
    raw = re.findall(r"\*[^*]+\*|\S+", text)
    flat = [w for tok in raw for w in (tok.strip("*").split() if tok.startswith("*") else [tok])]
    glued, k = [], 0
    while k < len(out_):
        j = k
        while j + 1 < len(out_) and deac(re.sub(r"[^\w'’]", "", flat[j] if j < len(flat) else "").lower()) in WEAK:
            j += 1
        glued.append(out_[k] if j == k else '<span class="u" style="white-space:nowrap">' + " ".join(out_[k:j + 1]) + "</span>")
        k = j + 1
    out_ = glued
    h = " ".join(out_)
    # ponctuation jamais seule en début de ligne : collée au mot d'avant (espace insécable devant ? ! : ; à la française)
    h = re.sub(r'</span> <span class="w">([?!:;»]+)</span>', lambda m_: "&nbsp;" + m_.group(1) + "</span>", h)
    return re.sub(r'</span> <span class="w">([,.…]+)</span>', lambda m_: m_.group(1) + "</span>", h)


def background_js(dur, T0):
    """Le sol en perspective avance lentement, un reflet traverse le panneau toutes les 7 s."""
    total = round(dur + T0, 2)
    return (f'  tl.fromTo("#panel .floor .fl", {{ y: 0 }}, {{ y: -{round(total * 40)}, duration: {total}, ease: "none", immediateRender: false }}, 0);\n'
            f'  tl.fromTo("#panel .sweep", {{ x: 0 }}, {{ x: 2400, duration: 7, ease: "power1.inOut", repeat: {max(0, int(total // 7))}, '
            f'immediateRender: false }}, 0.5);')


def paper_colors(vis):
    """Thème papier : fond de la charte, encre, accent assez soutenu pour porter du texte blanc."""
    bg, ink = vis.get("bgColor", "#f4efe6"), vis.get("inkColor", "#1d1b19")
    if _lum(bg) < 150:  # charte sombre : le papier reste clair
        bg = "#f4efe6"
    acc = vis.get("paperAccent") or vis.get("accentColor", "#9b1b30")
    if _lum(acc) > 165:
        acc = _mix(acc, ink, 0.45)
    base = acc
    for t in (0.1, 0.2, 0.3, 0.4, 0.5, 0.6):  # texte blanc lisible (WCAG 4,5:1) sur l'accent
        if _contrast(acc, "#ffffff") >= 4.6:
            break
        acc = _mix(base, ink if _lum(ink) < 90 else "#000000", t)
    return bg, ink, acc, _mix(bg, "#ffffff", 0.65)


def css_paper(W, ph, fam, vis):
    """Thème « explainer papier » : mêmes temps forts, rendu carte papier, encre, ombres franches (surcharge du thème sombre)."""
    bg, ink, acc, paper = paper_colors(vis)
    u = W / 1080
    sh = f"{round(8*u)}px {round(8*u)}px 0 {ink}"
    return css(W, ph, fam, {**vis, "panelAccent": acc}) + f"""
  #panel.paper {{ position: absolute; inset: 0; width: auto; height: auto; background: transparent; color: {ink}; z-index: 5; }}
  #panel.paper .tag {{ display: none; }}
  #panel.paper .flash {{ background: radial-gradient(circle, {acc}66 0%, transparent 65%); }}
  #panel.paper .ttl {{ color: {ink}; }}
  #panel.paper .ttl .it {{ color: {acc}; }}
  #panel.paper .mark {{ background: {acc}; filter: none; }}
  #panel.paper .card {{ background: #fff; border: {max(2, round(3*u))}px solid {ink}; border-radius: {round(10*u)}px; box-shadow: {sh}; color: {ink}; }}
  #panel.paper .chead {{ color: {ink}; opacity: .6; }}
  #panel.paper .row {{ border-top: 1px solid {ink}22; }}
  #panel.paper .box {{ border-color: {ink}; }}
  #panel.paper .box i {{ background: {acc}; color: #fff; }}
  #panel.paper .stamp {{ background: #fff; color: {acc}; border-color: {acc}; box-shadow: {sh}; }}
  #panel.paper .big, #panel.paper .lbl {{ color: {ink}; }}
  #panel.paper .big .px {{ color: {acc}; }}
  #panel.paper .bar {{ background: {acc}; box-shadow: none; }}
  #panel.paper .wbar {{ background: {ink}0d; border-bottom: 2px solid {ink}; }}
  #panel.paper .wbar b {{ background: {ink}55; }}
  #panel.paper .field {{ border-color: {ink}; box-shadow: none; }}
  #panel.paper .field .q::after {{ background: {acc}; }}
  #panel.paper .res {{ background: {ink}08; }}
  #panel.paper .res small {{ background: {ink}22; }}
  #panel.paper .res.top {{ border: 2px solid {acc}; box-shadow: none; }}
  #panel.paper .ph {{ border: {max(2, round(3*u))}px solid {ink}; box-shadow: {sh}; border-radius: {round(10*u)}px; }}
  #panel.paper .cap2 {{ color: {ink}; opacity: .7; }}
  #panel.paper .stp {{ background: #fff; border: {max(2, round(3*u))}px solid {ink}; box-shadow: {sh}; color: {ink}; }}
  #panel.paper .stp .n {{ border-color: {ink}; }}
  #panel.paper .stp.on {{ background: {acc}; color: #fff; border-color: {ink}; }}
  #panel.paper .stp.on .n {{ background: #fff; color: {acc}; border-color: #fff; }}
  #panel.paper .ttl {{ top: {round(ph*0.24)}px; font-size: {round(118*u)}px; }}
  #panel.paper .mark {{ top: {round(ph*0.66)}px; }}
  #panel.paper .card {{ top: {round(ph*0.22)}px; }}
  #panel.paper .row {{ font-size: {round(62*u)}px; padding: {round(26*u)}px 0; }}
  #panel.paper .chead {{ font-size: {round(28*u)}px; }}
  #panel.paper .big {{ top: {round(ph*0.24)}px; font-size: {round(300*u)}px; }}
  #panel.paper .bar {{ top: {round(ph*0.24 + 320*u)}px; }}
  #panel.paper .lbl {{ top: {round(ph*0.24 + 345*u)}px; font-size: {round(84*u)}px; }}
  #panel.paper .stat {{ top: {round(ph*0.24)}px; }}
  #panel.paper .stps {{ top: {round(ph*0.2)}px; }}
  #panel.paper .stp {{ font-size: {round(64*u)}px; padding: {round(32*u)}px {round(34*u)}px; margin-bottom: {round(28*u)}px; }}
  #panel.paper .ph {{ top: {round(ph*0.12)}px; bottom: {round(ph*0.16)}px; }}
  #panel.paper .ic .cir {{ border: {max(2, round(3*u))}px solid {ink}; box-shadow: {sh}; color: #fff; }}
  #panel.paper .ic .lab {{ color: {ink}; }}
  #panel.paper .bigico {{ filter: none; top: {round(ph*0.68)}px; }}
  #panel.paper .igrid {{ top: {round(ph*0.24)}px; }}
  #panel.paper .ic .cir {{ width: {round(270*u)}px; height: {round(270*u)}px; }}
  #panel.paper .ic .lab {{ font-size: {round(58*u)}px; margin-top: {round(28*u)}px; }}
  #panel.paper .ihead {{ top: {round(ph*0.1)}px; font-size: {round(30*u)}px; }}
  #panel.paper .ihead {{ color: {ink}; }}
  #panel.paper {{ --acc: {acc}; --on-acc: #fff; --ui-ink: {ink}; --ui-line: {ink}24; --ui-soft: {ink}0b; --ui-mute: {ink}99; --ui-solid: #fff; }}
  #panel.paper .rrow.hl {{ box-shadow: none; }}"""


def css_light(W, ph, fam, vis, cards=False):
    """Thème clair de l'écran partagé (fond blanc cassé, cartes à ombre douce) ; cards=True : rien derrière, les
    temps forts deviennent des cartes blanches posées sur la vidéo plein écran."""
    bg, ink, acc, paper = paper_colors(vis)
    u = W / 1080
    soft = f"0 {round(18*u)}px {round(50*u)}px rgba(0,0,0,.14)"
    line = f"1px solid {ink}1c"
    s = css_paper(W, ph, fam, vis) + f"""
  #panel.paper.light {{ inset: auto; left: 0; top: 0; width: {W}px; height: {ph}px; z-index: 20; background: {_mix(bg, '#ffffff', 0.7)}; }}
  #panel.light .card, #panel.light .stp, #panel.light .ph, #panel.light .ic .cir {{ border: {line}; box-shadow: {soft};
             border-radius: {round(26*u)}px; }}
  #panel.light .stamp {{ background: #fff; box-shadow: {soft}; }}  /* garde son cadre d'accent */
  #panel.light .tag {{ display: flex; color: {ink}99; }}
  #panel.light .stp.on {{ border-color: {acc}; }}
  #panel.light .wbar {{ border-bottom: {line}; background: {ink}06; }}
  #panel.light .field {{ border: 2px solid {acc}; }}
  #panel.light .bigico {{ top: {round(ph*0.6)}px; }}
  #panel.light .ttl {{ top: {round(ph*0.13)}px; font-size: {round(108*u)}px; }}"""
    if cards:
        s += f"""
  #panel.paper.light.cards {{ background: transparent; overflow: visible; }}
  #panel.cards .beat .bi {{ transform: scale(.88); transform-origin: 50% 0; }}
  #panel.cards .hlab {{ background: #fff; padding: {round(4*u)}px {round(14*u)}px; border-radius: 99px; box-shadow: {soft}; }}
  #panel.cards .ttl {{ left: {round(60*u)}px; right: auto; max-width: {round(W - 120*u)}px; top: {round(ph*0.14)}px; padding: {round(26*u)}px {round(34*u)}px;
             background: #fff; border-radius: {round(28*u)}px; box-shadow: {soft}; font-size: {round(74*u)}px; }}
  #panel.cards .big {{ left: 8%; right: 8%; white-space: nowrap; top: {round(ph*0.12)}px; padding: {round(20*u)}px 0; background: #fff; border-radius: {round(30*u)}px;
             box-shadow: {soft}; font-size: {round(190*u)}px; }}
  #panel.cards .bar {{ display: none; }}
  #panel.cards .lbl {{ left: 18%; right: 18%; top: {round(ph*0.12 + 250*u)}px; padding: {round(12*u)}px {round(20*u)}px; background: #fff;
             border-radius: {round(20*u)}px; box-shadow: {soft}; font-size: {round(58*u)}px; }}
  #panel.cards .ihead, #panel.cards .cap2 {{ left: 50%; right: auto; transform: translateX(-50%); white-space: nowrap; padding: {round(10*u)}px {round(22*u)}px;
             background: #fff; border-radius: 99px; box-shadow: {soft}; opacity: 1; }}
  #panel.cards .mark {{ display: none; }}
  #panel.cards .bigico {{ display: none; }}  /* icône du titre : dans la carte (.tico) */
  #panel.cards .tag {{ padding: {round(8*u)}px {round(18*u)}px; border-radius: 99px; background: #fff; box-shadow: {soft}; }}
  #panel.cards .kick.kabs {{ left: {round(60*u)}px; right: auto; padding: {round(8*u)}px {round(18*u)}px; border-radius: 99px; background: #fff; box-shadow: {soft};
             color: {_mix(acc, "#151515", 0.2)}; }}
  #panel.cards .stat {{ top: {round(ph*0.12)}px; }}
  #panel.cards .stat .big {{ padding: {round(20*u)}px {round(46*u)}px; }}
  #panel.cards .stat .lbl {{ padding: {round(12*u)}px {round(26*u)}px; }}
  #panel.cards .beat.sl .bi {{ transform: perspective({round(1400*u)}px) rotateY(12deg) scale(.74); transform-origin: 0 0; }}  /* "side": "left" */
  #panel.cards .beat.sr .bi {{ transform: perspective({round(1400*u)}px) rotateY(-12deg) scale(.74); transform-origin: 100% 0; }}
  #panel.cards .hs, #panel.cards .hc {{ box-shadow: {soft}; }}
  #panel.cards .ic .lab {{ display: inline-block; white-space: nowrap; background: #fff; color: {ink}; padding: {round(8*u)}px {round(20*u)}px;
             border-radius: 99px; box-shadow: {soft}; font-size: {round(38*u)}px; }}  /* lisible sur la vidéo floutée */"""
    return s


def css_glass(W, ph, fam, vis):
    """Thème « glass » : cartes en verre dépoli sur la vidéo (fond qui se devine, texte blanc). Aucun parent d'une surface en
    verre n'anime filter ni opacity (le verre ne verrait plus la vidéo) : entrées et sorties en transformations."""
    _, _, acc_t, on_t = colors(vis)  # accent éclairci, lisible sur le verre
    u = W / 1080
    surf = ", ".join(f"#panel.glass {x}" for x in (".card", ".ttl", ".stat .big", ".stat .lbl", ".stp", ".ihead", ".cap2", ".ph", ".hs", ".ic .lab",
                                                     ".hlab", ".tag", ".kick.kabs", ".stamp", ".lhead .lp", ".ltabs", ".cval"))
    return css_light(W, ph, fam, vis, cards=True) + f"""
  #panel.glass {{ color: #fff; --ui-ink: #ffffff; --ui-line: rgba(255,255,255,.24); --ui-soft: rgba(255,255,255,.10); --ui-mute: rgba(255,255,255,.72);
                 --ui-solid: rgba(255,255,255,.16); --acc: {acc_t}; --on-acc: {on_t}; }}
  {surf} {{ background: rgba(255,255,255,.12); -webkit-backdrop-filter: blur(24px) saturate(1.4); backdrop-filter: blur(24px) saturate(1.4);
            border: 1px solid rgba(255,255,255,.38); box-shadow: 0 {round(18*u)}px {round(50*u)}px rgba(0,0,0,.22), inset 0 1px 0 rgba(255,255,255,.35);
            color: #fff; text-shadow: 0 1px {round(10*u)}px rgba(0,0,0,.18); }}
  #panel.glass .beat .bi {{ opacity: 1; }}
  #panel.glass .ttl, #panel.glass .big, #panel.glass .lbl, #panel.glass .stp, #panel.glass .ic .lab, #panel.glass .chead, #panel.glass .ihead,
  #panel.glass .cap2, #panel.glass .tag {{ color: #fff; }}
  #panel.glass .chead, #panel.glass .tag {{ color: rgba(255,255,255,.78); }}
  #panel.glass .ttl .it, #panel.glass .big .px, #panel.glass .kick, #panel.glass .tico, #panel.glass .hs {{ color: {acc_t}; }}
  #panel.glass .stamp {{ color: {acc_t}; border: {round(6*u)}px solid {acc_t}; }}
  #panel.glass .row {{ border-top-color: rgba(255,255,255,.18); }}
  #panel.glass .box, #panel.glass .stp .n {{ border-color: rgba(255,255,255,.6); }}
  #panel.glass .stp.on {{ background: {acc_t}33; border-color: {acc_t}; }}
  #panel.glass .res {{ background: rgba(255,255,255,.08); }}
  #panel.glass .field {{ border-color: {acc_t}; }}
  #panel.glass .stat.sg .big {{ background: linear-gradient(180deg, #ffffff 0%, {acc_t} 100%); -webkit-background-clip: text; background-clip: text;
                               -webkit-backdrop-filter: none; backdrop-filter: none; border: 0; box-shadow: none; }}
  #panel.glass .beat.sl .bi {{ transform: perspective({round(1400*u)}px) rotateY(12deg) scale(.74); transform-origin: 0 0; }}
  #panel.glass .beat.sr .bi {{ transform: perspective({round(1400*u)}px) rotateY(-12deg) scale(.74); transform-origin: 100% 0; }}"""


# entrées des cartes, prises à tour de rôle ; la sortie part dans le sens opposé
ENTRIES = ("turn", "clip", "zoom")


def card_motion(sid, k, s0, t1, d, last, W, glass, side=None):
    """Entrée / dérive / sortie d'une carte (thèmes cards et glass). Verre : jamais de filter ni d'opacité sur la carte
    entière (parent du verre), les flous finissent par clearProps."""
    u = W / 1080
    kind = ENTRIES[k % len(ENTRIES)]
    dr = -1 if side == "left" else (1 if side == "right" else (1 if k % 2 == 0 else -1))
    js, sel = [], f"#{sid}"
    if kind == "turn":
        js.append(f'  tl.fromTo("{sel}", {{ rotationY: {25 * dr}, x: {round(120 * u * dr)}, transformPerspective: {round(1200 * u)} }}, '
                  f'{{ rotationY: 0, x: 0, duration: 0.55, ease: "power3.out", immediateRender: false }}, {s0});')
        out_ = f'{{ rotationY: {-25 * dr}, x: {-round(W * 1.15) * dr}, duration: 0.3, ease: "power2.in" }}'
    elif kind == "clip":
        js.append(f'  tl.fromTo("{sel}", {{ clipPath: "inset(0% 0% 100% 0%)", y: {round(24 * u)} }}, {{ clipPath: "inset(0% 0% 0% 0%)", y: 0, duration: 0.5, '
                  f'ease: "power3.inOut", immediateRender: false, clearProps: "clipPath" }}, {s0});')
        out_ = '{ clipPath: "inset(100% 0% 0% 0%)", y: -20, duration: 0.28, ease: "power2.in" }'
    elif glass:  # zoom sans flou (le verre doit voir la vidéo)
        js.append(f'  tl.fromTo("{sel}", {{ scale: 0.84, y: {round(60 * u)} }}, {{ scale: 1, y: 0, duration: 0.55, ease: "back.out(1.6)", immediateRender: false }}, {s0});')
        out_ = '{ scale: 0.9, yPercent: -110, duration: 0.3, ease: "power2.in" }'
    else:
        js.append(f'  tl.fromTo("{sel}", {{ scale: 0.86, filter: "blur(12px)" }}, {{ scale: 1, filter: "blur(0px)", duration: 0.5, ease: "back.out(1.7)", '
                  f'immediateRender: false, clearProps: "filter" }}, {s0});')
        out_ = '{ scale: 1.08, filter: "blur(10px)", duration: 0.25, ease: "power2.in", clearProps: "filter" }'
    if d > 2.0:  # dérive au repos
        js.append(f'  tl.fromTo("{sel}", {{ y: 0, rotation: 0 }}, {{ y: -{round(14 * u)}, rotation: {0.8 * dr}, duration: {round(d - 0.9, 3)}, '
                  f'ease: "sine.inOut", immediateRender: false }}, {round(s0 + 0.55, 3)});')
    if not last:
        js.append(f'  tl.to("{sel}", {out_}, {round(max(s0 + 0.6, t1 - 0.28), 3)});')
    return js


def lottie_layers(job, lo, k, s0, t1, T0, W, ph, ox, oy):
    """Emoji animé (library/lottie) posé dans la scène, rejoué en boucle pendant le temps fort (ou lo["dur"] s)."""
    layers = []
    if lo:  # emoji animé (library/lottie) posé dans la scène, rejoué en boucle pendant le temps fort
        import math
        lm = ROOT / "library" / "lottie" / str(lo.get("name", "")) / "lottie.json"
        if lm.exists() and "webm" in read_json(lm):
            meta = read_json(lm)
            (job / "assets" / "lottie").mkdir(parents=True, exist_ok=True)
            shutil.copy2(lm.parent / meta["webm"], job / "assets" / "lottie" / meta["webm"])
            from common import add_credit
            add_credit(job, meta["credit"])
            size = round(W * float(lo.get("size", 26)) / 100)
            lx = ox + round(W * float(lo.get("x", 78)) / 100) - size // 2
            ly = oy + round(ph * float(lo.get("y", 72)) / 100) - size // 2
            one = float(meta.get("rendered_duration") or meta.get("duration") or 1.5)
            start = s0 + float(lo.get("delay", 0.4))
            if lo.get("dur"):  # sur un passage « face » long : l'emoji ne reste que dur s
                t1 = min(t1, start + float(lo["dur"]))
            n = max(1, math.ceil((t1 - start - 0.25) / one - 0.05))
            for r_ in range(n):
                layers.append(f'    <video id="lo{k}_{r_}" class="clip" src="assets/lottie/{meta["webm"]}" data-start="{round(start + T0 + r_ * one, 3)}" '
                              f'data-duration="{round(min(one, t1 - start - r_ * one), 3)}" data-track-index="{90 + k}" muted playsinline '
                              f'style="position:absolute;left:{lx}px;top:{ly}px;width:{size}px;height:{size}px;z-index:35"></video>')
    return layers


def nodes(job, beats, words, dur, T0, W, ph, vis, theme="dark", origin=(0, 0)):
    """-> (html du panneau, lignes JS, rapport, calques). Temps : contenu (avant intro) ; T0 ajouté aux data-start.
    Calques : vidéos et emojis animés posés HORS du panneau (une vidéo minutée ne s'imbrique pas dans un temps fort),
    positionnés par rapport à la racine grâce à origin = coin haut-gauche de la scène."""
    u = W / 1080
    ox, oy = origin
    layers = []
    placed, lost = [], []
    for b in beats or []:
        hit = find_word(words, b.get("word", ""), b.get("occurrence", 1)) if b.get("word") else None
        t = (hit["start"] - 0.12) if hit else (b.get("_t") if b.get("_t") is not None else None)
        if t is None:  # jamais perdu en silence : le rapport dit pourquoi
            lost.append({"type": b.get("type", "title"), "mot": b.get("word"), "pose": False,
                         "raison": f"mot introuvable : {b['word']}" if b.get("word") else "pas de mot (word) où le poser"})
            continue
        placed.append((max(0.0, t), b))
    placed.sort(key=lambda x: x[0])
    if placed:
        placed[0] = (0.0, placed[0][1])  # le panneau n'est jamais vide au début
    kept, dropped = [], []
    for t, b in placed:  # un temps fort reste au moins 1 s : trop proche du précédent, il est écarté (pas de trou ni de flash)
        if kept and t - kept[-1][0] < 1.0:
            dropped.append({"type": b.get("type", "title"), "mot": b.get("word"), "pose": False,
                            "raison": f"à {t - kept[-1][0]:.2f} s du temps fort précédent (1 s au moins) : choisis un mot plus loin"})
            continue
        kept.append((t, b))
    if len(kept) > 1 and dur - kept[-1][0] < 1.0:
        t, b = kept.pop()
        dropped.append({"type": b.get("type", "title"), "mot": b.get("word"), "pose": False, "raison": "à moins d'1 s de la fin"})
    placed = kept
    html_, js, rep = [], ([background_js(dur, T0)] if theme == "dark" else []), lost + dropped
    cardlike, glass, nb = theme in ("cards", "glass"), theme == "glass", 0
    paper_on = []
    has_list = any(b.get("list") for _, b in placed)
    if has_list:
        hh, hj = list_heads(placed, dur, T0, W)
        html_ += hh
        js += hj
    for k, (t0, b) in enumerate(placed):
        t1 = placed[k + 1][0] if k + 1 < len(placed) else dur
        if t1 - t0 < 0.5:
            continue
        d, s0 = round(t1 - t0, 3), round(t0, 3)
        sid, typ = f"bt{k}", b.get("type", "title")
        if typ == "face":  # visage plein écran jusqu'au temps fort suivant (alternance) : build_composition replie le panneau
            rep.append({"type": "face", "a": s0, "duree": d, "mot": b.get("word") or ("(retour auto)" if b.get("_auto") else None)})
            if b.get("lottie"):  # emoji animé sur le visage (ex. « c'est magique »)
                layers += lottie_layers(job, b["lottie"], k, s0, t1, T0, W, ph, ox, oy)
            continue
        tag = f'<div class="tag">{esc(b["tag"])}</div>' if b.get("tag") else ""
        kick = esc(b.get("kicker", ""))
        inner, bj = "", []
        if typ == "title":
            big = icon(b["icon"]) if b.get("icon") else ""
            tico = f'<span class="tico">{big}</span>' if big and cardlike else ""  # cartes : l'icône dans la carte, devant le titre
            inner = (f'<div class="ttl">' + (f'<div class="kick">{kick}</div>' if kick else "") + f'{tico}{title_words(b.get("text", ""))}</div>'
                     + (f'<div class="bigico">{big}</div>' if big else ('<div class="mark"></div>' if b.get("mark") else "")))
            if big:
                bj.append(f'  tl.fromTo("#{sid} .bigico", {{ opacity: 0, scale: 0.3, rotation: -25 }}, {{ opacity: 1, scale: 1, rotation: 0, '
                          f'duration: 0.65, ease: "back.out(2.4)", immediateRender: false }}, {s0 + 0.45});')
                bj.append(f'  tl.to("#{sid} .bigico", {{ y: -{round(14*u)}, duration: 1.2, ease: "sine.inOut", yoyo: true, repeat: {max(0, int((d - 1.2) // 1.2))} }}, {s0 + 1.1});')
            bj.append(f'  tl.fromTo("#{sid} .ttl .w", {{ opacity: 0, y: 34, filter: "blur(10px)" }}, {{ opacity: 1, y: 0, filter: "blur(0px)", '
                      f'duration: 0.42, stagger: 0.11, ease: "power3.out", immediateRender: false }}, {s0 + 0.08});')
            bj.append(f'  tl.fromTo("#{sid} .ttl .it", {{ scale: 1.25, rotation: -5 }}, {{ scale: 1, rotation: 0, duration: 0.6, '
                      f'ease: "back.out(2.4)", immediateRender: false }}, {s0 + 0.2});')
            if b.get("mark"):
                bj.append(f'  tl.fromTo("#{sid} .mark", {{ opacity: 0, scale: 0.2, rotation: -90 }}, {{ opacity: 1, scale: 1, rotation: 0, '
                          f'duration: 0.7, ease: "back.out(2.2)", immediateRender: false }}, {s0 + 0.45});')
                bj.append(f'  tl.to("#{sid} .mark", {{ rotation: 45, duration: {max(0.5, d - 1.2)}, ease: "none" }}, {s0 + 1.15});')
        elif typ == "check":
            items = b.get("items", [])[:5]
            rows = "".join(f'<div class="row r{j}"><span class="box"><i>✓</i></span>'
                           + (f'<span class="ico">{item_icon(it)}</span>' if item_icon(it) else "")
                           + f'<span>{esc(item_text(it))}</span></div>' for j, it in enumerate(items))
            inner = (f'<div class="card"><div class="chead">{esc(b.get("title", ""))}</div>{rows}</div>'
                     + (f'<div class="stamp">{esc(b["stamp"])}</div>' if b.get("stamp") else ""))
            bj.append(f'  tl.fromTo("#{sid} .card", {{ opacity: 0, y: 50, rotationX: 14, transformPerspective: 900 }}, {{ opacity: 1, y: 0, '
                      f'rotationX: 0, duration: 0.55, ease: "power3.out", immediateRender: false }}, {s0 + 0.05});')
            span = max(0.35, (d * 0.7 - 0.5) / max(1, len(items)))
            for j in range(len(items)):
                tj = round(s0 + 0.35 + j * span, 3)
                bj.append(f'  tl.fromTo("#{sid} .r{j}", {{ opacity: 0, x: -24 }}, {{ opacity: 1, x: 0, duration: 0.3, ease: "power2.out", immediateRender: false }}, {tj});')
                bj.append(f'  tl.fromTo("#{sid} .r{j} .box i", {{ scale: 0 }}, {{ scale: 1, duration: 0.32, ease: "back.out(3)", immediateRender: false }}, {round(tj + 0.18, 3)});')
            if b.get("stamp"):
                ts = round(s0 + 0.35 + len(items) * span + 0.1, 3)
                bj.append(f'  tl.fromTo("#{sid} .stamp", {{ opacity: 0, scale: 2.4, rotation: -20 }}, {{ opacity: 1, scale: 1, rotation: -8, '
                          f'duration: 0.38, ease: "back.out(2)", immediateRender: false }}, {ts});')
                bj.append(f'  tl.fromTo("#panel .flash", {{ opacity: 0.7, scale: 0.3 }}, {{ opacity: 0, scale: 1.3, duration: 0.5, ease: "power2.out", '
                          f'immediateRender: false }}, {ts});')
        elif typ == "stat":
            num_ = lambda x: float(str(x).replace(" ", "").replace("\u202f", "").replace(",", "."))
            v, v0 = num_(b.get("value", 0)), num_(b.get("from", 0))
            dec = 1 if (v % 1 or v0 % 1) else 0
            nfin = max(f"{v:,.{dec}f}", f"{v0:,.{dec}f}", key=len).replace(",", " ")
            fin = f'{b.get("prefix", "")}{nfin}{b.get("suffix", "")}'
            # tous les thèmes : le chiffre final tient sur une ligne (« dès 50 000 € ») ; largeur du compteur réservée
            base_ = {"paper": 300, "cards": 190, "glass": 190}.get(theme, 230) * u
            fs = round(min(base_, W * (0.74 if cardlike else 0.86) / max(1, len(fin) * 0.6)))
            eur = " eur" if "€" in f'{b.get("prefix", "")}{b.get("suffix", "")}' else ""  # prix : bruitage de caisse
            sg = " sg" if b.get("style") == "glass" else ""
            mid = (f'<div class="dim"><i></i><span>{esc(b["dim"])}</span></div>' if b.get("dim") else '<div class="bar"></div>')
            start_txt = f"{v0:,.{dec}f}".replace(",", " ").replace(".", ",")
            inner = (f'<div class="stat{sg}"><div class="big{eur}" style="font-size:{fs}px"><span class="px">{esc(b.get("prefix", ""))}</span>'
                     f'<span class="num" style="min-width:{round(len(nfin) * 0.6, 2)}em">{start_txt}</span>'
                     f'<span class="px">{esc(b.get("suffix", ""))}</span></div>{mid}'
                     + (f'<div class="lbl">{esc(glue(b["label"]))}</div>' if b.get("label") else "") + '</div>')
            bj.append(f'  tl.fromTo("#{sid} .big", {{ opacity: 0, scale: 0.85 }}, {{ opacity: 1, scale: 1, duration: 0.5, ease: "back.out(1.8)", immediateRender: false }}, {s0 + 0.05});')
            bj.append(f'  (function () {{ const el = document.querySelector("#{sid} .num"), o = {{ v: {v0} }};'
                      f' tl.fromTo(o, {{ v: {v0} }}, {{ v: {v}, duration: {round(min(1.6, d * 0.5), 2)}, ease: "power2.out", immediateRender: false,'
                      f' onUpdate: function () {{ el.textContent = o.v.toLocaleString("fr-FR", {{ minimumFractionDigits: {dec}, maximumFractionDigits: {dec} }}); }} }}, {s0 + 0.1}); }})();')
            if b.get("dim"):  # cote fléchée qui s'ouvre depuis le centre, puis sa valeur
                bj.append(f'  tl.fromTo("#{sid} .dim i", {{ scaleX: 0 }}, {{ scaleX: 1, duration: 0.6, ease: "power3.out", immediateRender: false }}, {s0 + 0.4});')
                bj.append(f'  tl.fromTo("#{sid} .dim span", {{ opacity: 0, y: 8 }}, {{ opacity: 1, y: 0, duration: 0.3, immediateRender: false }}, {s0 + 0.85});')
            else:
                bj.append(f'  tl.fromTo("#{sid} .bar", {{ scaleX: 0 }}, {{ scaleX: 1, duration: 0.7, ease: "power3.inOut", immediateRender: false }}, {s0 + 0.4});')
            if b.get("label"):
                bj.append(f'  tl.fromTo("#{sid} .lbl", {{ opacity: 0, y: 20 }}, {{ opacity: 1, y: 0, duration: 0.45, ease: "power2.out", immediateRender: false }}, {s0 + 0.7});')
        elif typ == "search":
            q, res = b.get("query", ""), b.get("results", [])[:4]
            hi = int(b.get("highlight", 0))  # la ligne du client
            rows = "".join(f'<div class="res{" top" if j == hi else ""} s{j}">{esc(item_text(r))}<small></small></div>' for j, r in enumerate(res))
            inner = (f'<div class="card win"><div class="wbar"><b></b><b></b><b></b></div><div class="field"><span class="q"></span></div>{rows}</div>')
            bj.append(f'  tl.fromTo("#{sid} .card", {{ opacity: 0, y: 40, scale: 0.96 }}, {{ opacity: 1, y: 0, scale: 1, duration: 0.5, ease: "power3.out", immediateRender: false }}, {s0 + 0.05});')
            tq = round(min(0.9, 0.04 * len(q) + 0.15), 2)
            bj.append(f'  (function () {{ const el = document.querySelector("#{sid} .q"), q = {json.dumps(q, ensure_ascii=False)}, o = {{ n: 0 }};'
                      f' tl.fromTo(o, {{ n: 0 }}, {{ n: q.length, duration: {tq}, ease: "none", immediateRender: false,'
                      f' onUpdate: function () {{ el.textContent = q.slice(0, Math.round(o.n)); }} }}, {s0 + 0.4}); }})();')
            for j in range(len(res)):
                bj.append(f'  tl.fromTo("#{sid} .s{j}", {{ opacity: 0, y: 26 }}, {{ opacity: 1, y: 0, duration: 0.35, ease: "power2.out", immediateRender: false }}, {round(s0 + 0.5 + tq + j * 0.18, 3)});')
        elif typ == "image":
            src = b.get("image", "")
            p = Path(src)
            if not (job / p).exists():
                for base in (job / "inbox", ROOT):
                    if (base / p).exists():
                        (job / "assets" / "img").mkdir(parents=True, exist_ok=True)
                        shutil.copy2(base / p, job / "assets" / "img" / p.name)
                        src = f"assets/img/{p.name}"
                        break
            if not src:
                rep.append({"type": typ, "pose": False, "raison": "pas d'image (panel.py fetch pour une query)"})
                continue
            is_vid = src.lower().endswith((".mp4", ".webm", ".mov"))
            med = "" if is_vid else (f'<img src="{esc(src)}" alt=""' + (' style="object-fit:contain;background:#fff;padding:6%;box-sizing:border-box"'
                                                                          if b.get("fit") == "contain" else "") + '>')
            inner = f'<div class="ph">{med}</div>' + (f'<div class="cap2">{esc(b["caption"])}</div>' if b.get("caption") else "")
            if is_vid:  # le cadre est dans le temps fort, la vidéo dans un calque à la même place
                x, y, w, h, rad = media_box(W, ph, theme)
                lid = f"lv{k}"
                layers.append(f'    <div class="mlayer" id="{lid}" style="position:absolute;left:{ox + x}px;top:{oy + y}px;width:{w}px;height:{h}px;'
                              f'border-radius:{rad}px;overflow:hidden;z-index:30;opacity:0"><video id="{lid}v" class="clip" src="{esc(src)}" '
                              f'data-start="{round(s0 + T0, 3)}" data-duration="{d}" data-track-index="{80 + k}" muted playsinline '
                              f'style="width:100%;height:100%;object-fit:{"contain" if b.get("fit") == "contain" else "cover"};display:block;background:#fff"></video></div>')
                bj.append(f'  tl.fromTo("#{sid} .ph", {{ opacity: 0, y: 60 }}, {{ opacity: 1, y: 0, duration: 0.6, ease: "power3.out", immediateRender: false }}, {s0 + 0.05});')
                bj.append(f'  tl.fromTo("#{lid}", {{ opacity: 0, y: 60 }}, {{ opacity: 1, y: 0, duration: 0.6, ease: "power3.out", immediateRender: false }}, {s0 + 0.05});')
                if k + 1 < len(placed):
                    bj.append(f'  tl.to("#{lid}", {{ opacity: 0, y: -16, duration: 0.22, ease: "power2.in" }}, {round(t1 - 0.22, 3)});')
            else:
                bj.append(f'  tl.fromTo("#{sid} .ph", {{ opacity: 0, y: 60, rotationX: 16, transformPerspective: 1000 }}, {{ opacity: 1, y: 0, rotationX: 0, '
                          f'duration: 0.6, ease: "power3.out", immediateRender: false }}, {s0 + 0.05});')
                bj.append(f'  tl.fromTo("#{sid} .ph img", {{ scale: 1.0 }}, {{ scale: 1.1, duration: {d}, ease: "none", immediateRender: false }}, {s0});')
        elif typ == "steps":
            items = b.get("items", [])[:4]
            rows = "".join(f'<div class="stp p{j}"><span class="n">{item_icon(it) or j + 1}</span><span>{esc(item_text(it))}</span></div>'
                           for j, it in enumerate(items))
            inner = f'<div class="stps">{rows}</div>'
            span = max(0.4, (d - 0.6) / max(1, len(items)))
            for j in range(len(items)):
                tj = round(s0 + 0.15 + j * span, 3)
                bj.append(f'  tl.fromTo("#{sid} .p{j}", {{ opacity: 0, x: 40 }}, {{ opacity: 1, x: 0, duration: 0.4, ease: "power3.out", immediateRender: false }}, {tj});')
                bj.append(_cls_at(f"#{sid} .p{j}", "on", True, tj))  # étape allumée, la précédente s'éteint
                if j:
                    bj.append(_cls_at(f"#{sid} .p{j - 1}", "on", False, tj))
        elif typ == "icons":
            items = b.get("items", [])[:6]
            cols = 2 if len(items) == 4 else min(3, max(1, len(items)))
            cells = "".join(f'<div class="ic c{j}"><div class="cir">{item_icon(it)}</div><div class="lab">{esc(item_text(it))}</div></div>'
                            for j, it in enumerate(items))
            inner = ((f'<div class="ihead">{esc(b["title"])}</div>' if b.get("title") else "")
                     + f'<div class="igrid" style="grid-template-columns:repeat({cols},1fr)">{cells}</div>')
            span = max(0.25, min(0.6, (d * 0.6) / max(1, len(items))))
            for j in range(len(items)):
                tj = round(s0 + 0.15 + j * span, 3)
                bj.append(f'  tl.fromTo("#{sid} .c{j}", {{ opacity: 0, y: -{round(120*u)}, rotation: {(-12, 10, -6, 8, -10, 6)[j]} }}, {{ opacity: 1, y: 0, rotation: 0, '
                          f'duration: 0.7, ease: "bounce.out", immediateRender: false }}, {tj});')
        elif typ in UI_TYPES:
            if typ == "palette" and not b.get("colors"):
                b = {**b, "colors": [c for c in (vis.get("bgColor"), vis.get("inkColor"), vis.get("accentColor"), vis.get("panelAccent"))
                                     if c][:5], "font": b.get("font") or vis.get("fontFamily", "")}
            inner, bj = ui_beat(job, typ, b, sid, s0, d, W, ph - (round(128 * u) if has_list else 0))
        else:
            rep.append({"type": typ, "pose": False, "raison": "type inconnu"})
            continue
        if kick and typ != "title":  # sur-titre posé au-dessus du contenu
            inner = f'<div class="kick kabs">{kick}</div>' + inner
        if kick:
            bj.append(f'  tl.fromTo("#{sid} .kick", {{ opacity: 0, y: 10 }}, {{ opacity: 1, y: 0, duration: 0.3, ease: "power2.out", immediateRender: false }}, {s0 + 0.02});')
        if b.get("fond") == "papier" and theme == "dark":  # alternance : ce temps fort sur papier quadrillé
            paper_on.append((s0, t1))
        if b.get("lottie"):
            layers += lottie_layers(job, b["lottie"], k, s0, t1, T0, W, ph, ox, oy)
        side = b.get("side") if b.get("side") in ("left", "right") and cardlike else None
        cls = (" pb" if b.get("fond") == "papier" and theme == "dark" else "") + {"left": " sl", "right": " sr", None: ""}[side]
        e0 = round(max(0.0, s0 - 0.15), 3) if cardlike and k else s0  # cartes : la suivante chevauche la sortie de la précédente
        html_.append(f'      <div class="clip beat{cls}" id="{sid}" data-start="{round(e0 + T0, 3)}" data-duration="{round(t1 - e0, 3)}" data-track-index="{70 + k % 2}">'
                     f'<div class="bi">{tag}{inner}</div></div>')
        if not glass:  # verre : jamais d'opacité sur un parent du verre
            js.append(f'  tl.fromTo("#{sid} .bi", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.25, ease: "power1.out", immediateRender: false }}, {e0});')
        if cardlike:  # entrées variées à tour de rôle, dérive au repos, sortie dans le sens opposé
            js += card_motion(sid, nb, e0, t1, d, k + 1 >= len(placed), W, glass, side)
            nb += 1
        if b.get("tag"):
            js.append(f'  tl.fromTo("#{sid} .tag", {{ opacity: 0, x: 20 }}, {{ opacity: 1, x: 0, duration: 0.4, ease: "power2.out", immediateRender: false }}, {s0 + 0.05});')
        if b.get("flash") and typ != "check":
            js.append(f'  tl.fromTo("#panel .flash", {{ opacity: 0.8, scale: 0.3 }}, {{ opacity: 0, scale: 1.4, duration: 0.55, ease: "power2.out", immediateRender: false }}, {s0 + 0.15});')
        js += bj
        if k + 1 < len(placed) and not glass:
            js.append(f'  tl.to("#{sid} .bi", {{ opacity: 0, y: -16, duration: 0.22, ease: "power2.in" }}, {round(t1 - 0.22, 3)});')
        rep.append({"type": typ, "a": s0, "duree": d, "mot": b.get("word")})
    for a_, b_ in paper_on:  # fond papier allumé pendant ces temps forts (le fil passe par-dessus)
        js.append(f'  tl.set("#panel .paperbg", {{ opacity: 1 }}, {a_}); tl.set("#panel .paperbg", {{ opacity: 0 }}, {b_});')
    deco = ""
    if vis.get("panelThread"):  # fil conducteur : une courbe d'accent qui traverse tout le panneau, sa pointe avance
        pts = [(-40, 0.66), (W * 0.22, 0.52), (W * 0.48, 0.7), (W * 0.74, 0.5), (W + 40, 0.62)]
        dpath = f"M {pts[0][0]:.0f} {ph * pts[0][1]:.0f} " + " ".join(
            f"C {(x0 + x1) / 2:.0f} {ph * y0:.0f}, {(x0 + x1) / 2:.0f} {ph * y1:.0f}, {x1:.0f} {ph * y1:.0f}" for (x0, y0), (x1, y1) in zip(pts, pts[1:]))
        deco += (f'<svg class="thread" width="{W}" height="{round(ph)}" viewBox="0 0 {W} {round(ph)}"><path class="thp" d="{dpath}" pathLength="1000" />'
                 f'<circle class="thd" r="{round(9 * u)}" cx="0" cy="0" /></svg>')
        total = round(dur, 2)
        js.append(f'  (function () {{ const p = document.querySelector("#panel .thp"), c = document.querySelector("#panel .thd"), L = p.getTotalLength(), o = {{ v: 0 }};'
                  f' tl.fromTo(o, {{ v: 0 }}, {{ v: 1, duration: {total}, ease: "none", immediateRender: true, onUpdate: function () {{'
                  f' const k = 0.08 + 0.92 * o.v, q = p.getPointAtLength(L * k); p.style.strokeDashoffset = 1000 * (1 - k);'
                  f' c.setAttribute("cx", q.x); c.setAttribute("cy", q.y); }} }}, 0); }})();')
    if vis.get("panelHud"):  # repères mono dans les coins du cadre : nom, timecode qui défile, temps fort n / N
        nb = len(placed)
        lab = esc(vis.get("hudLabel") or (read_json(job / "job.json").get("client", "") if (job / "job.json").exists() else ""))
        deco += (f'<div class="hud tl" data-layout-ignore>{lab}</div><div class="hud tr" data-layout-ignore><span class="htc">00:00:00</span></div>'
                 f'<div class="hud bl" data-layout-ignore><span class="hn">01</span> / {nb:02d}</div><div class="hud br" data-layout-ignore>{esc(vis.get("hudNote", "4K · 24 i/s"))}</div>')
        starts = json.dumps([round(t_, 3) for t_, _ in placed])
        js.append(f'  (function () {{ const tc = document.querySelector("#panel .htc"), hn = document.querySelector("#panel .hn"), S = {starts}, o = {{ v: 0 }};'
                  f' tl.fromTo(o, {{ v: 0 }}, {{ v: {round(dur, 2)}, duration: {round(dur, 2)}, ease: "none", immediateRender: true, onUpdate: function () {{'
                  f' const t = o.v, f = Math.floor((t % 1) * 24); tc.textContent = String(Math.floor(t / 60)).padStart(2, "0") + ":" +'
                  f' String(Math.floor(t % 60)).padStart(2, "0") + ":" + String(f).padStart(2, "0");'
                  f' let n = 1; S.forEach(function (s, i) {{ if (s <= t) n = i + 1; }}); hn.textContent = String(n).padStart(2, "0"); }} }}, 0); }})();')
    deco = f'<div class="paperbg"></div>{deco}' if paper_on else deco
    panel = (f'    <div id="panel"><div class="pbg"></div><div class="floor"><div class="fl"></div></div><div class="sweep"></div>{deco}'
             f'\n{chr(10).join(html_)}\n      <div class="flash"></div><div class="grain"></div><div class="vig"></div></div>')
    hl = " haslist" if has_list else ""
    if theme == "dark" and has_list:
        panel = panel.replace('<div id="panel">', f'<div id="panel" class="{hl.strip()}">', 1)
    if theme == "paper":  # pas de décor sombre : le papier et le motif sont dessinés par build_explainer
        panel = f'    <div id="panel" class="paper{hl}">{deco}\n{chr(10).join(html_)}\n      <div class="flash"></div></div>'
    elif theme in ("light", "cards", "glass"):
        cls = "paper light" + (" cards" if theme in ("cards", "glass") else "") + (" glass" if glass else "") + hl
        panel = f'    <div id="panel" class="{cls}">{deco}\n{chr(10).join(html_)}\n      <div class="flash"></div></div>'
    return panel, js, rep, layers


UI_TYPES = ("form", "chat", "rank", "progress", "hub", "browser", "funnel", "chart", "feed", "palette", "repo", "code", "paths",
            "settings", "post", "loupe", "flap", "map", "calendar", "timeline", "invoice", "revenue", "clock")  # 6 derniers : objets.py
LOREM_FR = ("En utilisant ce service, vous acceptez que vos données soient traitées conformément aux présentes conditions, "
            "lesquelles peuvent être modifiées à tout moment sans préavis. Le prestataire décline toute responsabilité en cas "
            "d'interruption, de perte ou d'usage non conforme. Les sommes versées ne sont pas remboursables sauf mention contraire. ")


def github_repo(name):
    """Étoiles, description, langage et avatar d'un dépôt public (API GitHub, sans clé) ; {} hors ligne."""
    import urllib.request
    try:
        with urllib.request.urlopen(f"https://api.github.com/repos/{name}", timeout=15) as r:
            d = json.loads(r.read().decode("utf-8"))
        return {"stars": d.get("stargazers_count"), "desc": d.get("description") or "", "lang": d.get("language") or "",
                "avatar": (d.get("owner") or {}).get("avatar_url", "")}
    except Exception:  # noqa: BLE001
        return {}


def _typing(sel, text, dur, at):
    """Texte qui se tape (état calculé depuis le temps : juste à n'importe quelle image)."""
    return (f'  (function () {{ const el = document.querySelector("{sel}"), q = {json.dumps(text, ensure_ascii=False)}, o = {{ n: 0 }};'
            f' tl.fromTo(o, {{ n: 0 }}, {{ n: q.length, duration: {dur}, ease: "none", immediateRender: false,'
            f' onUpdate: function () {{ el.textContent = q.slice(0, Math.round(o.n)); }} }}, {at}); }})();')


def _cls_at(sel, cls, on, at):
    """Ajoute / retire une classe à un instant, de façon réversible (un petit tween porte l'état)."""
    return (f'  (function () {{ const el = document.querySelector("{sel}"), o = {{ v: 0 }};'
            f' tl.fromTo(o, {{ v: 0 }}, {{ v: 1, duration: 0.01, immediateRender: false, onUpdate: function () {{'
            f' el.classList.toggle("{cls}", {"o.v > 0.5" if on else "o.v < 0.5"}); }} }}, {at}); }})();')


def ui_beat(job, typ, b, sid, s0, d, W, ph):
    """Maquettes d'interface animées -> (html, lignes JS). ph : hauteur utile (sous l'en-tête de liste s'il y en a un)."""
    u = W / 1080
    import objets
    if typ in objets.TYPES:  # carte du monde, calendrier, timeline, devis, revenus, horloge
        return objets.beat(job, typ, b, sid, s0, d, W, ph, u)
    bj = []
    card_in = (f'  tl.fromTo("#{sid} .card", {{ opacity: 0, y: 46, scale: 0.97 }}, {{ opacity: 1, y: 0, scale: 1, duration: 0.5, '
               f'ease: "power3.out", immediateRender: false }}, {s0 + 0.05});')
    wbar = (f'<div class="wbar"><b></b><b></b><b></b>' + (f'<span class="url">{esc(b["url"])}</span>' if b.get("url") else "") + '</div>')
    if typ == "form":
        fields = b.get("fields", [])[:3]
        rows = "".join(f'<div class="ff"><label>{esc(f.get("label", ""))}</label><div class="fv v{j}"><span class="q"></span></div></div>'
                       for j, f in enumerate(fields))
        inner = (f'<div class="card win">{wbar}<div class="fbody">'
                 + (f'<div class="ftitle">{esc(b["title"])}</div>' if b.get("title") else "")
                 + f'{rows}<div class="fbtn"><span>{esc(b.get("button", "Envoyer"))}</span><span class="t2">✓ {esc(b.get("done", "Envoyé"))}</span></div>'
                 f'</div><div class="hand">{icon("pointer")}</div></div>')
        bj.append(card_in)
        # position de la main : calculée sur les hauteurs fixes du CSS (barre, titre, champs)
        top0 = round(64 * u + 26 * u + (66 * u if b.get("title") else 0))
        fh = round((24 + 8 + 76 + 16) * u)
        span = max(0.55, (d * 0.72 - 0.9) / max(1, len(fields) + 1))
        hx = round(W * 0.56)
        t = s0 + 0.45
        bj.append(f'  tl.fromTo("#{sid} .hand", {{ opacity: 0, x: {hx + 60}, y: {top0 + fh} }}, {{ opacity: 1, x: {hx}, y: {top0 + round(50*u)}, '
                  f'duration: 0.35, ease: "power2.out", immediateRender: false }}, {round(t, 3)});')
        for j, f in enumerate(fields):
            tj = round(t + j * span, 3)
            fy = top0 + j * fh + round(52 * u)
            if j:
                bj.append(f'  tl.to("#{sid} .hand", {{ x: {hx}, y: {fy}, duration: 0.28, ease: "power2.inOut" }}, {tj});')
            bj.append(f'  tl.fromTo("#{sid} .hand", {{ scale: 1 }}, {{ scale: 0.82, duration: 0.09, yoyo: true, repeat: 1, immediateRender: false }}, {round(tj + 0.28, 3)});')
            bj.append(_cls_at(f"#{sid} .v{j}", "on", True, round(tj + 0.3, 3)))
            val = str(f.get("value", ""))
            bj.append(_typing(f"#{sid} .v{j} .q", val, round(min(span - 0.35, 0.05 * len(val) + 0.15), 2), round(tj + 0.32, 3)))
            bj.append(_cls_at(f"#{sid} .v{j}", "on", False, round(tj + span - 0.02, 3)))
        tb = round(t + len(fields) * span, 3)
        by = top0 + len(fields) * fh + round(50 * u)
        bj.append(f'  tl.to("#{sid} .hand", {{ x: {round(W * 0.42)}, y: {by}, duration: 0.3, ease: "power2.inOut" }}, {tb});')
        bj.append(f'  tl.fromTo("#{sid} .fbtn", {{ scale: 1 }}, {{ scale: 0.95, duration: 0.1, yoyo: true, repeat: 1, immediateRender: false }}, {round(tb + 0.3, 3)});')
        bj.append(f'  tl.fromTo("#{sid} .fbtn .t2", {{ opacity: 0, y: 30 }}, {{ opacity: 1, y: 0, duration: 0.3, ease: "back.out(2)", immediateRender: false }}, {round(tb + 0.42, 3)});')
        bj.append(f'  tl.to("#{sid} .fbtn > span:first-child", {{ opacity: 0, duration: 0.15 }}, {round(tb + 0.42, 3)});')
        bj.append(f'  tl.to("#{sid} .hand", {{ opacity: 0, duration: 0.3 }}, {round(tb + 0.8, 3)});')
    elif typ == "chat":
        msgs = b.get("messages", [])[:4]
        rows = "".join(f'<div class="msg {"me" if m.get("from") in ("me", "client", "moi") else "them"} m{j}"><span>'
                       f'{esc(glue(m.get("text", "")))}</span></div>' for j, m in enumerate(msgs))
        inner = f'<div class="card chat">' + (f'<div class="chead">{esc(b["title"])}</div>' if b.get("title") else "") + f'{rows}</div>'
        bj.append(card_in)
        span = max(0.6, (d * 0.75 - 0.5) / max(1, len(msgs)))
        for j, m in enumerate(msgs):
            tj = round(s0 + 0.4 + j * span, 3)
            them = m.get("from") not in ("me", "client", "moi")
            bj.append(f'  tl.fromTo("#{sid} .m{j}", {{ opacity: 0, y: 24, scale: 0.85 }}, {{ opacity: 1, y: 0, scale: 1, duration: 0.32, '
                      f'ease: "back.out(2)", transformOrigin: "{"0% 100%" if them else "100% 100%"}", immediateRender: false }}, {tj});')
            if them:  # « … » le temps d'écrire, puis le texte
                txt = json.dumps(glue(m.get("text", "")), ensure_ascii=False)
                bj.append(f'  (function () {{ const el = document.querySelector("#{sid} .m{j} span"), o = {{ v: 0 }};'
                          f' tl.fromTo(o, {{ v: 0 }}, {{ v: 1, duration: 0.55, ease: "none", immediateRender: true, onUpdate: function () {{'
                          f' if (o.v < 1) {{ el.innerHTML = \'<span class="dots"><i></i><i></i><i></i></span>\'; }} else {{ el.textContent = {txt}; }} }} }}, {tj}); }})();')
    elif typ == "rank":
        items = b.get("items", [])[:5]
        n = len(items)
        hi = int(b.get("highlight", n - 1))
        to = int(b.get("to", hi))
        rh = round(104 * u)
        nums = "".join(f'<div class="rnum" style="top:{j * rh}px">{j + 1}</div>' for j in range(n))
        rows = "".join(f'<div class="rrow{" hl" if j == hi else ""} q{j}" style="top:{j * rh}px"><span>{esc(item_text(it))}</span>'
                       + (f'<small>{esc(it.get("sub", ""))}</small>' if isinstance(it, dict) and it.get("sub") else "") + '</div>'
                       for j, it in enumerate(items))
        inner = (f'<div class="card">' + (f'<div class="chead">{esc(b["title"])}</div>' if b.get("title") else "")
                 + f'<div class="rk" style="height:{n * rh}px">{nums}{rows}</div></div>')
        bj.append(card_in)
        for j in range(n):
            bj.append(f'  tl.fromTo("#{sid} .q{j}", {{ opacity: 0, x: 30 }}, {{ opacity: 1, x: 0, duration: 0.3, ease: "power2.out", immediateRender: false }}, '
                      f'{round(s0 + 0.35 + j * 0.14, 3)});')
        if to != hi and 0 <= to < n and 0 <= hi < n:
            tm = round(s0 + max(1.2, d * 0.45), 3)
            bj.append(f'  tl.to("#{sid} .q{hi}", {{ y: {(to - hi) * rh}, scale: 1.04, duration: 0.7, ease: "power3.inOut" }}, {tm});')
            bj.append(f'  tl.to("#{sid} .q{hi}", {{ scale: 1, duration: 0.25 }}, {round(tm + 0.7, 3)});')
            step = 1 if to < hi else -1
            for j in range(to, hi, 1) if to < hi else range(hi + 1, to + 1):
                bj.append(f'  tl.to("#{sid} .q{j}", {{ y: {step * rh}, duration: 0.7, ease: "power3.inOut" }}, {tm});')
    elif typ == "progress":
        to = b.get("to", 100)
        inner = (f'<div class="card">' + (f'<div class="chead">{esc(b["title"])}</div>' if b.get("title") else "")
                 + f'<div class="cmd"><span class="q"></span></div><div class="pbar"><i></i></div>'
                 f'<div class="pmeta"><span><span class="pn">0</span> / {esc(to)} {esc(b.get("unit", ""))}</span><span class="pp">0 %</span></div>'
                 + (f'<div class="pdone">✓ {esc(b["done"])}</div>' if b.get("done") else "") + '</div>')
        bj.append(card_in)
        lab = str(b.get("label", ""))
        tq = round(min(0.8, 0.035 * len(lab) + 0.15), 2)
        bj.append(_typing(f"#{sid} .cmd .q", lab, tq, round(s0 + 0.35, 3)))
        tf = round(max(0.6, min(2.2, d - tq - 1.0)), 2)
        t2 = round(s0 + 0.5 + tq, 3)
        bj.append(f'  tl.fromTo("#{sid} .pbar i", {{ scaleX: 0 }}, {{ scaleX: 1, duration: {tf}, ease: "power1.inOut", immediateRender: false }}, {t2});')
        bj.append(f'  (function () {{ const a = document.querySelector("#{sid} .pn"), p = document.querySelector("#{sid} .pp"), o = {{ v: 0 }};'
                  f' tl.fromTo(o, {{ v: 0 }}, {{ v: 1, duration: {tf}, ease: "power1.inOut", immediateRender: false, onUpdate: function () {{'
                  f' a.textContent = Math.round(o.v * {float(to)}).toLocaleString("fr-FR"); p.textContent = Math.round(o.v * 100) + " %"; }} }}, {t2}); }})();')
        if b.get("done"):
            bj.append(f'  tl.fromTo("#{sid} .pdone", {{ opacity: 0, scale: 0.6 }}, {{ opacity: 1, scale: 1, duration: 0.35, ease: "back.out(2.4)", '
                      f'immediateRender: false }}, {round(t2 + tf + 0.1, 3)});')
    elif typ == "hub":
        items = b.get("items", [])[:8]
        cx, cy = W / 2, ph * (0.53 if b.get("title") else 0.48)
        cs, ss = round(220 * u), round(124 * u)
        R = max(ss, min(W * 0.32, ph * 0.27, ph * 0.86 - cy - ss / 2 - 50 * u))  # le libellé du bas reste au-dessus de la couture
        import math
        c = b.get("center", {})
        if isinstance(c, str):
            c = {"text": c}
        if c.get("image"):  # logo de la charte ou du client : copié dans le job
            ip = Path(c["image"])
            for base in (job, job / "inbox", ROOT):
                if (base / ip).exists() and base != job:
                    (job / "assets" / "img").mkdir(parents=True, exist_ok=True)
                    shutil.copy2(base / ip, job / "assets" / "img" / ip.name)
                    c = {**c, "image": f"assets/img/{ip.name}"}
                    break
        cin = icon(c["icon"]) if c.get("icon") else (f'<img src="{esc(c["image"])}" alt="">' if c.get("image")
                                                    else f'<span style="font-size:{round(38*u)}px;padding:0 .3em">{esc(c.get("text", ""))}</span>')
        pts = [(cx + R * math.cos(-math.pi / 2 + 2 * math.pi * j / max(1, len(items))),
                cy + R * math.sin(-math.pi / 2 + 2 * math.pi * j / max(1, len(items)))) for j in range(len(items))]
        def seg(x, y):  # du bord du cercle central au bord du satellite (jamais caché dessous, ni arrêté avant)
            L_ = max(1.0, math.hypot(x - cx, y - cy))
            ux, uy = (x - cx) / L_, (y - cy) / L_
            return cx + ux * cs / 2, cy + uy * cs / 2, x - ux * ss / 2, y - uy * ss / 2
        lines = "".join('<line class="h{}" x1="{:.0f}" y1="{:.0f}" x2="{:.0f}" y2="{:.0f}" />'.format(j, *seg(x, y)) for j, (x, y) in enumerate(pts))
        sats = "".join(f'<div class="hs s{j}" style="left:{x - ss / 2:.0f}px;top:{y - ss / 2:.0f}px;width:{ss}px;height:{ss}px">{item_icon(it)}</div>'
                       + (f'<span class="hlab s{j}" style="left:{x - ss:.0f}px;top:{(y - ss / 2 - round(46*u)) if y < cy - 1 else (y + ss / 2 + round(6*u)):.0f}px;'
                          f'width:{2 * ss}px">{esc(item_text(it))}</span>'
                          if item_text(it) else "")
                       for j, ((x, y), it) in enumerate(zip(pts, items)))
        inner = ((f'<div class="ihead">{esc(b["title"])}</div>' if b.get("title") else "")
                 + f'<svg class="hubl" width="{W}" height="{round(ph)}" viewBox="0 0 {W} {round(ph)}">{lines}</svg>'
                 + f'<div class="hc" style="left:{cx - cs / 2:.0f}px;top:{cy - cs / 2:.0f}px;width:{cs}px;height:{cs}px">{cin}</div>{sats}')
        bj.append(f'  tl.fromTo("#{sid} .hc", {{ opacity: 0, scale: 0.3 }}, {{ opacity: 1, scale: 1, duration: 0.55, ease: "back.out(2.2)", immediateRender: false }}, {s0 + 0.08});')
        span = max(0.16, min(0.4, (d * 0.6 - 0.6) / max(1, len(items))))
        for j, (x, y) in enumerate(pts):
            L = max(1, math.hypot(x - cx, y - cy) - cs / 2 - ss / 2)
            tj = round(s0 + 0.5 + j * span, 3)
            bj.append(f'  tl.fromTo("#{sid} .h{j}", {{ attr: {{ "stroke-dasharray": {L + 2:.0f}, "stroke-dashoffset": {L + 2:.0f} }} }}, '
                      f'{{ attr: {{ "stroke-dashoffset": 0 }}, duration: 0.4, ease: "power2.out", immediateRender: true }}, {tj});')
            bj.append(f'  tl.fromTo("#{sid} .s{j}", {{ opacity: 0, scale: 0.4 }}, {{ opacity: 1, scale: 1, duration: 0.4, ease: "back.out(2.6)", '
                      f'immediateRender: false }}, {round(tj + 0.28, 3)});')
    elif typ == "funnel":
        steps = b.get("steps", [])[:6]
        n = max(1, len(steps))
        fw, fh = W - round(140 * u), round(ph * 0.56)
        mx = max([float(x.get("value", 1)) for x in steps] or [1]) or 1
        gap = round(24 * u)
        bw = (fw - gap * (n - 1)) / n
        leak = b.get("leak")
        longest = max([len(w_) for x_ in steps for w_ in str(x_.get("label", "")).split()] or [4])
        lfs = round(max(20 * u, min(30 * u, bw / max(1, longest * 0.58))))  # le plus long mot tient dans sa colonne
        lab_h = round(lfs * 1.08 * 2 + 6 * u)  # deux lignes
        hmax = fh - lab_h - round(110 * u)
        parts = []
        for j, st_ in enumerate(steps):
            h = max(round(12 * u), round(hmax * float(st_.get("value", 0)) / mx))
            x = round(j * (bw + gap))
            parts.append(f'<i class="fbar f{j}{" leak" if j == leak else ""}" style="left:{x}px;width:{round(bw)}px;height:{h}px;bottom:{lab_h + round(10*u)}px"></i>'
                         f'<span class="flab" style="left:{x}px;width:{round(bw)}px;height:{lab_h}px;font-size:{lfs}px">{esc(st_.get("label", ""))}</span>'
                         + (f'<span class="fval v{j}" style="left:{x}px;width:{round(bw)}px;bottom:{h + lab_h + round(20*u)}px">{esc(st_["show"])}</span>'
                            if st_.get("show") else ""))
        dots = "".join(f'<i class="fdot d{k}" style="left:{round(fw * (k + .5) / 14)}px;top:{round(10*u)}px"></i>' for k in range(14))
        note = ""
        if leak is not None and 0 <= int(leak) < n and b.get("note"):
            lx = round(int(leak) * (bw + gap) + bw / 2)
            nw = min(fw, round(len(str(b["note"])) * 32 * u * 0.56 + 44 * u))  # largeur estimée : la note reste dans le cadre
            nl = round(min(max(0, lx - nw / 2), fw - nw))
            note = f'<span class="fnote" style="left:{nl}px;width:{nw}px;top:{round(46*u)}px">{esc(glue(b["note"]))}</span>'
        inner = ((f'<div class="ihead">{esc(b["title"])}</div>' if b.get("title") else "")
                 + f'<div class="fun">{dots}{"".join(parts)}{note}</div>')
        bj.append(f'  tl.fromTo("#{sid} .fbar", {{ scaleY: 0 }}, {{ scaleY: 1, duration: 0.55, stagger: 0.12, ease: "power3.out", immediateRender: false }}, {s0 + 0.15});')
        bj.append(f'  tl.fromTo("#{sid} .fdot", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.15, stagger: {round(min(0.08, d * 0.3 / 14), 3)}, immediateRender: false }}, {s0 + 0.3});')
        if any(x_.get("show") for x_ in steps):  # valeurs au-dessus des barres, quand chaque barre a poussé
            bj.append(f'  tl.fromTo("#{sid} .fval", {{ opacity: 0, y: 12 }}, {{ opacity: 1, y: 0, duration: 0.3, stagger: 0.12, ease: "back.out(2)", '
                      f'immediateRender: false }}, {s0 + 0.55});')
        if note:
            tn = round(s0 + min(d * 0.5, 1.6), 3)
            bj.append(f'  tl.fromTo("#{sid} .fnote", {{ opacity: 0, y: 16, scale: 0.6 }}, {{ opacity: 1, y: 0, scale: 1, duration: 0.35, ease: "back.out(2.6)", '
                      f'immediateRender: false }}, {tn});')
            bj.append(f'  tl.fromTo("#{sid} .fbar.leak", {{ x: 0 }}, {{ x: {round(6*u)}, duration: 0.06, yoyo: true, repeat: 5, immediateRender: false }}, {tn});')
    elif typ == "chart":
        pts = [float(x) for x in b.get("points", [])][:14] or [0, 1]
        cw, chh = W - round(140 * u) - round(76 * u), round(ph * 0.34)
        top_v = max(pts) * 1.15 or 1
        x0 = round(80 * u)
        X = lambda i: x0 + (cw - x0) * i / max(1, len(pts) - 1)
        Y = lambda v: chh - chh * v / top_v
        path = "M " + " L ".join(f"{X(i):.0f} {Y(v):.0f}" for i, v in enumerate(pts))
        grid = "".join(f'<line class="gl" x1="{x0}" x2="{cw}" y1="{Y(top_v * k / 3):.0f}" y2="{Y(top_v * k / 3):.0f}" />'
                       f'<text class="gt" x="{x0 - round(12*u)}" y="{Y(top_v * k / 3) + round(8*u):.0f}" text-anchor="end">'
                       f'{esc(b.get("ylabels", [""] * 4)[k] if b.get("ylabels") else "")}</text>' for k in range(4))
        xl = "".join(f'<text class="gt" x="{X(i * (len(pts) - 1) / max(1, len(b["xlabels"]) - 1)):.0f}" y="{chh + round(40*u)}" text-anchor="middle">{esc(t)}</text>'
                     for i, t in enumerate(b.get("xlabels", [])))
        ex, ey = X(len(pts) - 1), Y(pts[-1])
        inner = (f'<div class="card chartc">' + (f'<div class="chead">{esc(b["title"])}</div>' if b.get("title") else "")
                 + f'<div style="position:relative"><svg width="{cw}" height="{chh + round(50*u)}" viewBox="0 0 {cw} {chh + round(50*u)}">{grid}{xl}'
                 f'<path class="ln" d="{path}" pathLength="1000" /><circle class="dot" cx="{ex:.0f}" cy="{ey:.0f}" r="{round(12*u)}" /></svg>'
                 + (f'<span class="cval" style="right:{round(cw - ex + 22 * u)}px;top:{round(max(-30 * u, ey - 84 * u))}px">{esc(b["label"])}</span>'
                    if b.get("label") else "")
                 + '</div></div>')
        bj.append(card_in)
        tl_ = round(max(0.9, min(2.2, d * 0.55)), 2)
        bj.append(f'  tl.fromTo("#{sid} .ln", {{ attr: {{ "stroke-dashoffset": 1000 }} }}, {{ attr: {{ "stroke-dashoffset": 0 }}, duration: {tl_}, ease: "power1.inOut", '
                  f'immediateRender: true }}, {s0 + 0.35});')
        bj.append(f'  tl.fromTo("#{sid} .dot", {{ opacity: 0, scale: 0 }}, {{ opacity: 1, scale: 1, transformOrigin: "50% 50%", duration: 0.3, ease: "back.out(3)", '
                  f'immediateRender: false }}, {s0 + 0.35 + tl_});')
        if b.get("label"):
            bj.append(f'  tl.fromTo("#{sid} .cval", {{ opacity: 0, y: 12, scale: 0.7 }}, {{ opacity: 1, y: 0, scale: 1, duration: 0.35, ease: "back.out(2.4)", '
                      f'immediateRender: false }}, {s0 + 0.45 + tl_});')
    elif typ == "feed":
        items = b.get("items", [])[:4]
        rh = round(118 * u)
        rows = "".join(f'<div class="fi q{j}" style="top:{j * rh}px"><span class="fic">{icon(it.get("icon", "bell")) if isinstance(it, dict) else icon("bell")}</span>'
                       f'<span><b>{esc(item_text(it))}</b>' + (f'<small>{esc(it["sub"])}</small>' if isinstance(it, dict) and it.get("sub") else "")
                       + '</span></div>' for j, it in enumerate(items))
        inner = (f'<div class="card">' + (f'<div class="chead">{esc(b["title"])}</div>' if b.get("title") else "")
                 + (f'<span class="live">{esc(b.get("badge", "EN DIRECT"))}</span>' if b.get("badge", "EN DIRECT") else "")
                 + f'<div class="feed" style="height:{len(items) * rh}px">{rows}</div></div>')
        bj.append(card_in)
        bj.append(f'  tl.fromTo("#{sid} .live", {{ opacity: 1 }}, {{ opacity: 0.35, duration: 0.5, yoyo: true, repeat: {max(1, int(d / 0.5))}, immediateRender: false }}, {s0 + 0.3});')
        span = max(0.35, min(0.8, (d * 0.7 - 0.5) / max(1, len(items))))
        n_ = len(items)
        for j in range(n_):  # le plus récent arrive en haut (case 1) et pousse les autres d'une case vers le bas
            tj = s0 + 0.4 + (n_ - 1 - j) * span
            bj.append(f'  tl.fromTo("#{sid} .q{j}", {{ opacity: 0, y: {-j * rh - round(rh * 0.5)}, scale: 0.95 }}, {{ opacity: 1, y: {-j * rh}, scale: 1, duration: 0.4, '
                      f'ease: "back.out(1.8)", immediateRender: false }}, {round(tj, 3)});')
            for k_ in range(1, j + 1):
                bj.append(f'  tl.to("#{sid} .q{j}", {{ y: {-(j - k_) * rh}, duration: 0.35, ease: "power2.out" }}, {round(tj + k_ * span, 3)});')
    elif typ == "palette":
        cols = b.get("colors", [])[:6]
        sw = "".join(f'<i class="c{j}" style="background:{esc(c)}"></i>' for j, c in enumerate(cols))
        inner = (f'<div class="card">' + (f'<div class="chead">{esc(b.get("title", "La marque"))}</div>')
                 + f'<div class="sw">{sw}</div><div class="swf"><span class="aa">Aa</span><span>{esc(b.get("font", ""))}</span></div></div>')
        bj.append(card_in)
        bj.append(f'  tl.fromTo("#{sid} .sw i", {{ opacity: 0, y: 30, scaleY: 0.4 }}, {{ opacity: 1, y: 0, scaleY: 1, duration: 0.4, stagger: 0.1, ease: "back.out(2)", '
                  f'immediateRender: false }}, {s0 + 0.35});')
        bj.append(f'  tl.fromTo("#{sid} .swf", {{ opacity: 0, x: -30 }}, {{ opacity: 1, x: 0, duration: 0.45, ease: "power3.out", immediateRender: false }}, '
                  f'{round(s0 + 0.5 + 0.1 * len(cols), 3)});')
    elif typ == "repo":
        name = str(b.get("name", "owner/repo"))
        info = {} if b.get("stars") is not None else github_repo(name)
        stars = b.get("stars", info.get("stars") or 0)
        desc = b.get("desc", info.get("desc", ""))
        lang = b.get("lang", info.get("lang", ""))
        owner, _, repo = name.partition("/")
        av = icon(b["logo"]) if b.get("logo") else ""
        if not av and info.get("avatar"):
            import urllib.request
            try:
                (job / "assets" / "img").mkdir(parents=True, exist_ok=True)
                fn = job / "assets" / "img" / f"av-{re.sub(r'[^a-z0-9]', '', owner.lower())}.png"
                if not fn.exists():
                    with urllib.request.urlopen(info["avatar"] + "&s=120", timeout=15) as r:
                        fn.write_bytes(r.read())
                av = f'<img src="assets/img/{fn.name}" alt="">'
            except Exception:  # noqa: BLE001
                av = ""
        av = av or esc(owner[:1].upper())
        inner = (f'<div class="card repo"><div class="rhead"><span class="rav">{av}</span><span class="rname"><small>{esc(owner)} /</small> '
                 f'<b>{esc(repo or owner)}</b></span><span class="rstar">★ Star</span></div>'
                 + (f'<div class="rdesc">{esc(glue(desc))}</div>' if desc else "")
                 + f'<div class="rbig"><span class="sn">0</span><small>étoiles</small></div>'
                 + '<div class="rmeta">' + (f'<i class="ld"></i><span>{esc(lang)}</span>' if lang else "")
                 + (f'<span class="rb">{esc(b["badge"])}</span>' if b.get("badge") else "") + '</div></div>')
        bj.append(card_in)
        bj.append(f'  (function () {{ const el = document.querySelector("#{sid} .sn"), o = {{ v: 0 }};'
                  f' tl.fromTo(o, {{ v: 0 }}, {{ v: {float(stars)}, duration: {round(min(1.6, d * 0.5), 2)}, ease: "power2.out", immediateRender: false,'
                  f' onUpdate: function () {{ el.textContent = Math.round(o.v).toLocaleString("fr-FR"); }} }}, {s0 + 0.4}); }})();')
        if b.get("star", True):
            ts = round(s0 + 0.5 + min(1.6, d * 0.5), 3)
            bj.append(_cls_at(f"#{sid} .rstar", "on", True, ts))
            bj.append(f'  tl.fromTo("#{sid} .rstar", {{ scale: 1 }}, {{ scale: 1.2, duration: 0.12, yoyo: true, repeat: 1, immediateRender: false }}, {ts});')
    elif typ == "code":
        import difflib
        before, after = [str(x) for x in b.get("before", [])][:14], [str(x) for x in b.get("after", [])][:14]
        rows, dels, adds = [], [], []
        k = 0
        for op, a1, a2, b1, b2 in difflib.SequenceMatcher(None, before, after, autojunk=False).get_opcodes():
            if op == "equal":
                rows += [("eq", before[i]) for i in range(a1, a2)]
            if op in ("delete", "replace"):
                rows += [("del", before[i]) for i in range(a1, a2)]
            if op in ("insert", "replace"):
                rows += [("add", after[i]) for i in range(b1, b2)]
        html_rows, n = [], 0
        for j, (kind, line) in enumerate(rows):
            if kind != "add":
                n += 1
            html_rows.append(f'<div class="cl {kind} c{j}" data-n="{n if kind != "add" else ""}">{esc(line) or " "}</div>')
            (dels if kind == "del" else adds if kind == "add" else []).append(j)
        stat = b.get("label") or (f"{len(before)} → {len(after)} lignes" if after else "")
        bar = f'<div class="wbar"><b></b><b></b><b></b><span class="url">{esc(b.get("file", ""))}</span></div>'
        inner = (f'<div class="card win code" style="position:absolute">{bar}<div class="cbody">{"".join(html_rows)}</div>'
                 + (f'<span class="cstat">{esc(stat)}</span>' if stat else "") + '</div>')
        bj.append(card_in)
        lh = round(44 * u)
        bj.append(f'  tl.fromTo("#{sid} .cl:not(.add)", {{ opacity: 0, x: -14 }}, {{ opacity: 1, x: 0, duration: 0.2, stagger: 0.04, immediateRender: false }}, {s0 + 0.3});')
        tc = round(s0 + max(1.0, d * 0.4), 3)
        for j in dels:
            bj.append(f'  tl.to("#{sid} .c{j}", {{ backgroundColor: "rgba(214,47,51,.28)", color: "#d62f33", textDecoration: "line-through", duration: 0.15 }}, {tc});')
            bj.append(f'  tl.to("#{sid} .c{j}", {{ height: 0, opacity: 0, duration: 0.35, ease: "power2.in" }}, {round(tc + 0.45, 3)});')
        for i, j in enumerate(adds):
            bj.append(f'  tl.fromTo("#{sid} .c{j}", {{ height: 0 }}, {{ height: {lh}, duration: 0.3, ease: "power2.out", immediateRender: false }}, {round(tc + 0.85 + i * 0.12, 3)});')
        if stat:
            bj.append(f'  tl.fromTo("#{sid} .cstat", {{ opacity: 0, scale: 0.6 }}, {{ opacity: 1, scale: 1, duration: 0.35, ease: "back.out(2.4)", immediateRender: false }}, '
                      f'{round(tc + 1.0 + len(adds) * 0.12, 3)});')
    elif typ == "paths":
        import math
        n = max(3, min(8, int(b.get("count", 6))))
        hi = int(b.get("highlight", n // 2))
        x0, x1 = round(90 * u), W - round(90 * u)
        y_top, y_bot = ph * 0.22, ph * 0.78
        sw_ = round(22 * u)
        paths = []
        for j in range(n):
            ya = y_top + (y_bot - y_top) * j / (n - 1)
            yb = y_top + (y_bot - y_top) * ((j * 5 + 2) % n) / (n - 1)
            c1y = y_top + (y_bot - y_top) * ((j * 3 + 1) % n) / (n - 1)
            c2y = y_top + (y_bot - y_top) * ((j * 7 + 3) % n) / (n - 1)
            d_ = (f"M {x0} {ya:.0f} C {x0 + (x1 - x0) * .3:.0f} {c1y:.0f}, {x0 + (x1 - x0) * .45:.0f} {c2y:.0f}, {x0 + (x1 - x0) * .6:.0f} {(c1y + c2y) / 2:.0f} "
                  f"S {x0 + (x1 - x0) * .85:.0f} {yb:.0f}, {x1} {yb:.0f}")
            if j == hi:  # le chemin simple : presque droit
                ye = y_top + (y_bot - y_top) * 0.12
                d_ = f"M {x0} {ya:.0f} C {x0 + (x1 - x0) * .35:.0f} {ya:.0f}, {x0 + (x1 - x0) * .55:.0f} {ye:.0f}, {x1} {ye:.0f}"
                end = (x1, ye)
            paths.append((j, d_))
        svg = "".join(f'<path class="{"pa" if j == hi else ("pk" if j % 2 else "pg")} pp{j}" d="{d_}" stroke-width="{sw_}" pathLength="1000" '
                      f'stroke-dasharray="1000" />' for j, d_ in paths if j != hi)
        svg += next(f'<path class="pa pp{j}" d="{d_}" stroke-width="{sw_}" pathLength="1000" stroke-dasharray="1000" />' for j, d_ in paths if j == hi)
        svg += "".join(f'<circle class="ps" cx="{x0}" cy="{y_top + (y_bot - y_top) * j / (n - 1):.0f}" r="{round(16*u)}" />' for j in range(n))
        inner = (f'<svg class="pathsv" width="{W}" height="{round(ph)}" viewBox="0 0 {W} {round(ph)}" style="position:absolute;left:0;top:0">{svg}</svg>'
                 + (f'<span class="plab e" style="right:{round(40*u)}px;top:{round(end[1] - 70 * u)}px">{esc(b["label"])}</span>' if b.get("label") else "")
                 + (f'<span class="plab s" style="left:{round(40*u)}px;top:{round(y_bot + 40 * u)}px">{esc(b["start"])}</span>' if b.get("start") else ""))
        span = max(0.05, min(0.14, d * 0.25 / n))
        for k_, (j, _) in enumerate([p_ for p_ in paths if p_[0] != hi]):
            bj.append(f'  tl.fromTo("#{sid} .pp{j}", {{ attr: {{ "stroke-dashoffset": 1000 }} }}, {{ attr: {{ "stroke-dashoffset": 0 }}, duration: 0.8, ease: "power1.inOut", '
                      f'immediateRender: true }}, {round(s0 + 0.1 + k_ * span, 3)});')
        ta = round(s0 + min(0.9, 0.2 + n * span + 0.2), 3)
        bj.append(f'  tl.fromTo("#{sid} .pp{hi}", {{ attr: {{ "stroke-dashoffset": 1000 }} }}, {{ attr: {{ "stroke-dashoffset": 0 }}, duration: 0.7, ease: "power2.inOut", '
                  f'immediateRender: true }}, {ta});')
        bj.append(f'  tl.fromTo("#{sid} .plab", {{ opacity: 0, scale: 0.6 }}, {{ opacity: 1, scale: 1, duration: 0.35, stagger: 0.15, ease: "back.out(2.4)", '
                  f'immediateRender: false }}, {round(ta + 0.5, 3)});')
    elif typ == "settings":  # panneau de réglages : la consigne se tape, on enregistre (ou copie), « ✓ Enregistré »
        txt = str(b.get("text", ""))[:260]
        copy = b.get("action") == "copy"
        head = ((f'<span class="sgl">{icon(b["logo"])}</span>' if b.get("logo") else "")
                + f'<span class="sgn"><b>{esc(b.get("app", ""))}</b><small>{esc(b.get("title", "Réglages"))}</small></span>')
        inner = (f'<div class="card win sett">{wbar}<div class="sgh">{head}</div>'
                 + (f'<div class="sgl2">{esc(b["label"])}</div>' if b.get("label") else "")
                 + f'<div class="stx"><span class="q"></span></div>'
                 + (f'<div class="sgt"><span>{esc(b["toggle"])}</span><i class="sw2"><b></b></i></div>' if b.get("toggle") else "")
                 + f'<div class="sgf"><span class="sgok">✓ {esc(b.get("done", "Copié" if copy else "Enregistré"))}</span>'
                 f'<span class="sgb">{icon("copy") if copy else ""}{esc(b.get("button", "Copier" if copy else "Enregistrer"))}</span></div></div>')
        bj.append(card_in)
        tq = round(max(0.5, min(d * 0.5, 0.03 * len(txt) + 0.2)), 2)
        bj.append(_cls_at(f"#{sid} .stx", "on", True, round(s0 + 0.4, 3)))
        bj.append(_typing(f"#{sid} .stx .q", txt, tq, round(s0 + 0.45, 3)))
        tb = round(s0 + 0.55 + tq, 3)
        bj.append(_cls_at(f"#{sid} .stx", "on", False, tb))
        if b.get("toggle"):
            bj.append(_cls_at(f"#{sid} .sgt", "on", True, tb))
            tb = round(tb + 0.3, 3)
        bj.append(f'  tl.fromTo("#{sid} .sgb", {{ scale: 1 }}, {{ scale: 0.92, duration: 0.1, yoyo: true, repeat: 1, immediateRender: false }}, {tb});')
        bj.append(f'  tl.fromTo("#{sid} .sgok", {{ opacity: 0, y: 24, scale: 0.8 }}, {{ opacity: 1, y: 0, scale: 1, duration: 0.32, ease: "back.out(2.4)", '
                  f'immediateRender: false }}, {round(tb + 0.15, 3)});')
    elif typ == "post":  # publication recréée (X, LinkedIn, Threads) : la source citée, mot pour mot
        plat = str(b.get("platform", "x")).lower()
        av = (icon(b["logo"]) if b.get("logo") else "")
        if not av and b.get("avatar"):
            ip = Path(b["avatar"])
            for base in (job, job / "inbox", ROOT):
                if (base / ip).exists():
                    if base != job:
                        (job / "assets" / "img").mkdir(parents=True, exist_ok=True)
                        shutil.copy2(base / ip, job / "assets" / "img" / ip.name)
                        ip = Path("assets/img") / ip.name
                    av = f'<img src="{esc(ip.as_posix())}" alt="">'
                    break
        av = av or esc(str(b.get("name", "?"))[:1].upper())
        words_ = esc(glue(str(b.get("text", "")))).split(" ")
        body = " ".join(f'<span class="pw">{w}</span>' for w in words_ if w)
        stats = [(k, ic) for k, ic in (("replies", "message-circle"), ("reposts", "repeat-2"), ("likes", "heart"), ("views", "eye"))
                 if b.get(k) is not None]
        inner = (f'<div class="card post"><div class="poh"><span class="rav">{av}</span><span class="pon"><b>{esc(b.get("name", ""))}'
                 + ('<i class="pov">✓</i>' if b.get("verified") else "") + f'</b><small>{esc(b.get("handle", ""))}'
                 + (f' · {esc(b["date"])}' if b.get("date") else "") + f'</small></span><span class="pol">{icon("logo:" + plat)}</span></div>'
                 f'<div class="pot">{body}</div>'
                 + (f'<div class="poi"><img src="{esc(b["image"])}" alt=""></div>' if b.get("image") else "")
                 + '<div class="pos">' + "".join(f'<span class="ps-{k}">{icon(ic)}<b class="pc" data-v="{float(b[k])}">0</b></span>' for k, ic in stats)
                 + '</div></div>')
        bj.append(card_in)
        nw = max(1, len(words_))
        bj.append(f'  tl.fromTo("#{sid} .pw", {{ opacity: 0.12 }}, {{ opacity: 1, duration: 0.12, stagger: {round(min(0.09, d * 0.45 / nw), 3)}, '
                  f'immediateRender: false }}, {s0 + 0.35});')
        tc = round(s0 + 0.45 + min(d * 0.45, nw * 0.09), 3)
        bj.append(f'  document.querySelectorAll("#{sid} .pc").forEach(function (el) {{ const v = +el.dataset.v, o = {{ v: 0 }};'
                  f' tl.fromTo(o, {{ v: 0 }}, {{ v: v, duration: {round(min(1.2, d * 0.35), 2)}, ease: "power2.out", immediateRender: false,'
                  f' onUpdate: function () {{ el.textContent = o.v >= 1e6 ? (o.v / 1e6).toFixed(1).replace(".", ",") + " M" : o.v >= 1e4 ?'
                  f' Math.round(o.v / 1e3) + " k" : Math.round(o.v).toLocaleString("fr-FR"); }} }}, {tc}); }});')
        if b.get("likes") is not None:
            bj.append(_cls_at(f"#{sid} .ps-likes", "on", True, round(tc + 0.5, 3)))
            bj.append(f'  tl.fromTo("#{sid} .ps-likes svg", {{ scale: 1 }}, {{ scale: 1.35, duration: 0.14, yoyo: true, repeat: 1, ease: "back.out(3)", '
                      f'immediateRender: false }}, {round(tc + 0.5, 3)});')
    elif typ == "loupe":  # mur de texte illisible, une loupe le parcourt et s'arrête sur la phrase qui compte
        fs, rh_ = round(30 * u), round(46 * u)
        filler = str(b.get("text") or LOREM_FR)
        n = max(7, min(14, int((ph * 0.5) // rh_)))
        hi = int(b.get("row", round(n * 0.62)))
        cpl = int((W - round(220 * u)) / (fs * 0.5))  # caractères par ligne (estimation, la ligne est coupée en CSS)
        rows_ = [(filler * 4)[(j * cpl) % len(filler):][:cpl + 10] for j in range(n)]
        find = str(b.get("find", ""))
        rows_html = "".join(f'<div class="lr" data-layout-allow-overlap style="top:{j * rh_}px">'
                            + (f'<span class="hit">{esc(find)}</span> ' if j == hi and find else "") + f'{esc(rows_[j])}</div>' for j in range(n))
        L, S = round(300 * u), 2.2
        wh = n * rh_
        ww = W - round(140 * u) - round(2 * 34 * u)  # largeur du mur (carte moins ses marges)
        inner = (f'<div class="card win loupe">' + (f'{wbar}' if b.get("url") else "")
                 + (f'<div class="chead lpt">{esc(b["title"])}</div>' if b.get("title") else "")
                 + f'<div class="lw" style="height:{wh}px">{rows_html}'
                 f'<div class="lens" data-layout-allow-occlusion style="width:{L}px;height:{L}px"><div class="lz" data-layout-ignore style="width:{ww}px;height:{wh}px">{rows_html}</div></div></div>'
                 + (f'<span class="lpl">{esc(b["label"])}</span>' if b.get("label") else "") + '</div>')
        bj.append(card_in)
        tx = max(L * 0.42, min(ww * 0.8, round(len(find) * fs * 0.27))) if find else ww * 0.5
        path = [(ww * 0.78, wh * 0.18), (ww * 0.3, wh * 0.4), (ww * 0.62, wh * 0.85), (tx, hi * rh_ + rh_ / 2)]
        span = max(0.35, (d * 0.6 - 0.4) / len(path))
        t = s0 + 0.35
        cx, cy = path[0]
        bj.append(f'  tl.fromTo("#{sid} .lens", {{ opacity: 0, scale: 0.6, x: {cx - L / 2:.0f}, y: {cy - L / 2:.0f} }}, {{ opacity: 1, scale: 1, duration: 0.3, '
                  f'ease: "back.out(2)", immediateRender: false }}, {round(t, 3)});')
        bj.append(f'  tl.fromTo("#{sid} .lz", {{ scale: {S}, transformOrigin: "0 0", x: {L / 2 - S * cx:.0f}, y: {L / 2 - S * cy:.0f} }}, {{ scale: {S}, x: {L / 2 - S * cx:.0f}, '
                  f'y: {L / 2 - S * cy:.0f}, duration: 0.01, immediateRender: true }}, {round(t, 3)});')
        for cx, cy in path[1:]:
            t += span
            bj.append(f'  tl.to("#{sid} .lens", {{ x: {cx - L / 2:.0f}, y: {cy - L / 2:.0f}, duration: {round(span * 0.85, 3)}, ease: "power2.inOut" }}, {round(t - span * 0.85, 3)});')
            bj.append(f'  tl.to("#{sid} .lz", {{ x: {L / 2 - S * cx:.0f}, y: {L / 2 - S * cy:.0f}, duration: {round(span * 0.85, 3)}, ease: "power2.inOut" }}, '
                      f'{round(t - span * 0.85, 3)});')
        bj.append(_cls_at(f"#{sid} .lw", "found", True, round(t + 0.05, 3)))
        bj.append(f'  tl.fromTo("#{sid} .lens", {{ scale: 1 }}, {{ scale: 1.12, duration: 0.3, ease: "back.out(2.4)", immediateRender: false }}, {round(t + 0.05, 3)});')
        if b.get("label"):
            bj.append(f'  tl.fromTo("#{sid} .lpl", {{ opacity: 0, y: 16, scale: 0.6 }}, {{ opacity: 1, y: 0, scale: 1, duration: 0.35, ease: "back.out(2.6)", '
                      f'immediateRender: false }}, {round(t + 0.25, 3)});')
    elif typ == "flap":  # tableau d'affichage à palettes : les caractères défilent puis se posent, de gauche à droite
        rows_ = [str(x).upper() for x in (b.get("rows") or [b.get("text", "")])][:4]
        cols = max(4, min(14, max(len(x) for x in rows_)))
        rows_ = [x[:cols].ljust(cols) if b.get("align") == "left" else x[:cols].center(cols) for x in rows_]
        cw_ = (W - round(140 * u) - (cols - 1) * round(8 * u)) // cols
        chh = round(cw_ * 1.45)
        cells = "".join(f'<div class="fr">' + "".join(f'<i class="fc" style="width:{cw_}px;height:{chh}px;font-size:{round(cw_ * 0.95)}px">'
                                                       f'<b data-c="{esc(ch)}"></b></i>' for ch in row) + '</div>' for row in rows_)
        inner = ((f'<div class="ihead">{esc(b["title"])}</div>' if b.get("title") else "")
                 + f'<div class="flap">{cells}</div>' + (f'<div class="fsub">{esc(b["sub"])}</div>' if b.get("sub") else ""))
        tf = round(max(0.9, min(1.6, d * 0.5)), 2)
        bj.append(f'  tl.fromTo("#{sid} .fr", {{ opacity: 0, y: 30 }}, {{ opacity: 1, y: 0, duration: 0.35, stagger: 0.08, ease: "power3.out", immediateRender: false }}, {s0 + 0.05});')
        bj.append(f'  (function () {{ const els = document.querySelectorAll("#{sid} .fc b"), C = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789%+€", o = {{ v: 0 }};'
                  f' tl.fromTo(o, {{ v: 0 }}, {{ v: 1, duration: {tf}, ease: "none", immediateRender: true, onUpdate: function () {{'
                  f' els.forEach(function (el, i) {{ const c = el.dataset.c, col = i % {cols}, row = Math.floor(i / {cols});'
                  f' const at = 0.25 + 0.6 * col / {cols} + 0.08 * row;'
                  f' el.textContent = (o.v >= at || c === " ") ? c : C[(i * 7 + Math.floor(o.v * 46)) % C.length];'
                  f' el.parentNode.classList.toggle("set", o.v >= at && c !== " "); }}); }} }}, {s0 + 0.2}); }})();')
        if b.get("sub"):
            bj.append(f'  tl.fromTo("#{sid} .fsub", {{ opacity: 0, y: 14 }}, {{ opacity: 1, y: 0, duration: 0.35, ease: "power2.out", immediateRender: false }}, '
                      f'{round(s0 + 0.3 + tf, 3)});')
    else:  # browser : site maquette (ou capture) annoté
        notes = b.get("notes", [])[:4]
        on = {n_.get("on"): n_ for n_ in notes if n_.get("on")}

        def mark(key, j):
            n_ = on.get(key)
            if not n_:
                return ""
            side = " side" if key == "button" else ""
            return f'<i class="ring k{notes.index(n_)}"></i><span class="note{side} k{notes.index(n_)}">{esc(glue(n_.get("text", "")))}</span>'
        if b.get("image"):
            src = b["image"]
            p = Path(src)
            for base in (job / "inbox", ROOT):
                if not (job / p).exists() and (base / p).exists():
                    (job / "assets" / "img").mkdir(parents=True, exist_ok=True)
                    shutil.copy2(base / p, job / "assets" / "img" / p.name)
                    src = f"assets/img/{p.name}"
            free = "".join(f'<i class="ring k{j}" style="left:{n_.get("x", 50)}%;top:{n_.get("y", 50)}%;width:{n_.get("w", 30)}%;'
                           f'height:{n_.get("h", 10)}%;inset:auto"></i><span class="note k{j}" style="left:{n_.get("x", 50)}%;'
                           f'top:calc({n_.get("y", 50)}% - {round(40*u)}px);right:auto">{esc(n_.get("text", ""))}</span>'
                           for j, n_ in enumerate(notes) if not n_.get("on"))
            body = f'<div class="shotw"><img src="{esc(src)}" alt="">{free}</div>'
        else:
            s_ = b.get("site", {})
            tiles = s_.get("tiles", [])[:3]
            body = (f'<div class="hero"><div class="h1">{esc(s_.get("title", ""))}{mark("title", 0)}</div><br>'
                    + (f'<div class="h2">{esc(s_.get("sub", ""))}{mark("sub", 1)}</div>' if s_.get("sub") else "")
                    + (f'<div class="btn">{esc(s_.get("button", ""))}{mark("button", 2)}</div>' if s_.get("button") else "") + '</div>'
                    + (f'<div class="tiles">' + "".join(f'<div>{esc(t_)}{mark(f"tile{j + 1}", 3 + j)}</div>' for j, t_ in enumerate(tiles)) + '</div>'
                       if tiles else ""))
        inner = f'<div class="card win site">{wbar}{body}</div>'
        bj.append(card_in)
        span = max(0.45, (d * 0.7 - 0.8) / max(1, len(notes)))
        for j in range(len(notes)):
            tj = round(s0 + 0.8 + j * span, 3)
            bj.append(f'  tl.fromTo("#{sid} .ring.k{j}", {{ opacity: 0, scale: 1.25 }}, {{ opacity: 1, scale: 1, duration: 0.3, ease: "power2.out", '
                      f'immediateRender: false }}, {tj});')
            bj.append(f'  tl.fromTo("#{sid} .note.k{j}", {{ opacity: 0, y: 14, scale: 0.6 }}, {{ opacity: 1, y: 0, scale: 1, duration: 0.32, '
                      f'ease: "back.out(2.6)", immediateRender: false }}, {round(tj + 0.12, 3)});')
    return inner, bj


def list_heads(placed, dur, T0, W):
    """En-tête de liste « 1 SUR 5 · Nom » : un par élément de la liste, posé au-dessus des temps forts qui le portent."""
    u = W / 1080
    segs = []
    for k, (t0, b) in enumerate(placed):
        L = b.get("list")
        if not L:
            continue
        key = (L.get("n"), L.get("name"))
        t1 = placed[k + 1][0] if k + 1 < len(placed) else dur
        if segs and segs[-1]["key"] == key and abs(segs[-1]["t1"] - t0) < 0.05:
            segs[-1]["t1"] = t1
        else:
            segs.append({"key": key, "t0": t0, "t1": t1, "L": L})
    html_, js = [], []
    for i, s in enumerate(segs):
        L, s0, d = s["L"], round(s["t0"], 3), round(s["t1"] - s["t0"], 3)
        hid = f"lh{i}"
        of = L.get("of")
        top = f'{L.get("n")} SUR {of}' if of else str(L.get("n", ""))
        if L.get("style") == "tabs":
            tabs = "".join(f'<i class="{"on" if k + 1 == L.get("n") else ""}">{k + 1}</i>' for k in range(int(of or L.get("n", 1))))
            html_.append(f'      <div class="clip lhead" id="{hid}" data-start="{round(s0 + T0, 3)}" data-duration="{d}" data-track-index="{66 + i % 2}">'
                         f'<div class="ltabs">{tabs}' + (f'<b>{esc(L["name"])}</b>' if L.get("name") else "") + '</div></div>')
            js.append(f'  tl.fromTo("#{hid} .ltabs", {{ opacity: 0, y: -14 }}, {{ opacity: 1, y: 0, duration: 0.35, ease: "back.out(2)", immediateRender: false }}, {s0 + 0.05});')
            js.append(f'  tl.fromTo("#{hid} .ltabs i.on", {{ scale: 0.5 }}, {{ scale: 1, duration: 0.35, ease: "back.out(3)", immediateRender: false }}, {s0 + 0.2});')
            if i + 1 < len(segs):
                js.append(f'  tl.to("#{hid} > *", {{ opacity: 0, duration: 0.2 }}, {round(s["t1"] - 0.2, 3)});')
            continue
        html_.append(f'      <div class="clip lhead" id="{hid}" data-start="{round(s0 + T0, 3)}" data-duration="{d}" data-track-index="{66 + i % 2}">'
                     f'<i class="ll"></i><span class="le l">{icon(L.get("left", "sparkles"))}</span>'
                     + (f'<span class="le r">{icon(L["icon"])}</span>' if L.get("icon") else "")
                     + f'<div class="lp"><small>{esc(top)}</small><b>{esc(L.get("name", ""))}</b></div></div>')
        js.append(f'  tl.fromTo("#{hid} .ll", {{ scaleX: 0 }}, {{ scaleX: 1, duration: 0.45, ease: "power3.out", immediateRender: false }}, {s0 + 0.05});')
        js.append(f'  tl.fromTo("#{hid} .le", {{ opacity: 0, scale: 0.4 }}, {{ opacity: 1, scale: 1, duration: 0.4, stagger: 0.1, ease: "back.out(2.4)", '
                  f'immediateRender: false }}, {s0 + 0.15});')
        js.append(f'  tl.fromTo("#{hid} .lp", {{ opacity: 0, y: -16, scale: 0.85 }}, {{ opacity: 1, y: 0, scale: 1, duration: 0.42, ease: "back.out(2.2)", '
                  f'immediateRender: false }}, {s0 + 0.1});')
        if i + 1 < len(segs):
            js.append(f'  tl.to("#{hid} > *", {{ opacity: 0, duration: 0.2 }}, {round(s["t1"] - 0.2, 3)});')
    return html_, js


def default_beats(text_json):
    """Sans panels.json : un titre par phrase forte gardée (overlays de text.json), mot fort = le plus long."""
    beats = []
    for o in (text_json.get("overlays") or []):
        if not o.get("keep") or not o.get("words"):
            continue
        ws = [w["w"].strip(".,!?…;:") for w in o["words"]]
        j = max(range(len(ws)), key=lambda i: len(ws[i]))
        txt = " ".join(f"*{w}*" if i == j else w for i, w in enumerate(ws))
        beats.append({"type": "title", "_t": float(o["start"]), "text": txt})
    return beats


def fetch(job_name, slug):
    """Temps forts "image" avec "query" et sans "image" : Pixabay (vidéos assez longues puis photos), 1re posée, planche."""
    import argparse as _a

    from broll import candidates, download, planche
    from common import config, size_of
    job = job_dir(job_name)
    pj = job / "work" / f"{slug}_panels.json"
    beats = read_json(pj)
    items, rep_ = [], []
    for i, b in enumerate(beats):
        if b.get("type") != "image" or b.get("image") or not b.get("query"):
            continue
        alts = [x for x in candidates(job, b["query"], True, None, "wide") if float(x.get("duree") or 0) >= 4][:3]
        alts += candidates(job, b["query"], False, None, "wide")[:3]
        if not alts:
            rep_.append({"temps_fort": i, "query": b["query"], "raison": "aucun résultat"})
            continue
        b["image"], _ = download(job, _a.Namespace(id=alts[0]["id"]))
        items.append({"beat": i, "query": b["query"], "phrase": b.get("text") or b.get("caption") or b.get("word", ""),
                      "alts": [x["id"] for x in alts], "_alts": alts})
        rep_.append({"temps_fort": i, "query": b["query"], "image": b["image"]})
    from common import write_json as _w
    _w(pj, beats)
    _w(job / "work" / f"{slug}_panels_alts.json", [{k: v for k, v in it.items() if k != "_alts"} for it in items])
    pl = planche(job, items) if items else None
    out(ok=True, images=rep_, planche=str(pl) if pl else None, suite="regarde la planche ; panel.py pick <job> <slug> <n> a-f|none")


def pick(job_name, slug, n, choice):
    import argparse as _a

    from broll import download
    job = job_dir(job_name)
    pj, aj = job / "work" / f"{slug}_panels.json", job / "work" / f"{slug}_panels_alts.json"
    beats, alts = read_json(pj), read_json(aj)
    it = alts[int(n) - 1]
    b = beats[it["beat"]]
    if choice == "none":
        b.pop("image", None)
        b["type"] = "title" if b.get("text") else b["type"]
    else:
        b["image"], _ = download(job, _a.Namespace(id=it["alts"]["abcdef".index(choice)] if len(choice) == 1 else choice))
    write_json(pj, beats)
    out(ok=True, temps_fort=it["beat"], image=b.get("image"))


def suggest(job_name, slug):
    from broll import find_moments
    job = job_dir(job_name)
    rows, _ = find_moments(job, slug, 3.0)
    sk = [{"type": "title", "word": r["word"], "occurrence": r["occurrence"], "text": r["phrase"][:60], "tag": "",
           "phrase": r["phrase"]} for r in rows]
    dst = job / "work" / f"{slug}_panels_suggested.json"
    write_json(dst, sk)
    out(ok=True, temps_forts=len(sk), fichier=str(dst),
        suite="réécris chaque temps fort (type, texte court avec *mot fort*, tag de chapitre), puis enregistre work/<slug>_panels.json")


if __name__ == "__main__":
    if len(sys.argv) >= 4 and sys.argv[1] == "suggest":
        suggest(sys.argv[2], sys.argv[3])
    elif len(sys.argv) >= 4 and sys.argv[1] == "fetch":
        fetch(sys.argv[2], sys.argv[3])
    elif len(sys.argv) >= 6 and sys.argv[1] == "pick":
        pick(*sys.argv[2:6])
    else:
        print(__doc__)

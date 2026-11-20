"""VIDÉO SANS RUSH -> <job>/index.html : scènes animées + voix off + sous-titres + musique + SFX.

  python build_scenes.py <job> <slug> [--no-captions] [--no-sfx]

Entrées : work/<slug>_storyboard.json (Claude), work/<slug>_timing.json (voice.py), work/<slug>_text.json
(build_text.py, sous-titres), work/<slug>_music.json (add_music.py, facultatif), charte (brand.json).
Types de scènes : hook, photo, points, stat, offer, quote, gallery, cta, steps, beforeafter, address, team,
product, device, browser, block (bloc de library/ ou compositions/,
variables remplies depuis la charte ; voir references/storyboard.md).
Les temps viennent de la voix réelle ; un élément qui correspond à un mot dit (un point de liste, un prix)
apparaît quand ce mot est prononcé, trouvé dans la transcription (jamais estimé par Claude).
"""
import argparse
import html
import json
import re
import shutil
import unicodedata
from pathlib import Path

from build_composition import SHADOW, STYLES, caption_css, caption_js, caption_spans, emoji_tween, sfx_asset
from common import (ROOT, add_credit, block_file, brand_info, config, fail, job_dir, motion_nodes, mount, out, read_json,
                    size_of)

OV = 0.45  # chevauchement des scènes (transition)


def esc(s):
    return html.escape(str(s), quote=True)


def norm(s):
    s = unicodedata.normalize("NFD", s.lower())
    return "".join(c for c in s if c.isalnum() and unicodedata.category(c) != "Mn")


def asset(job, rel, sub):
    p = Path(rel)
    for base in (job / "inbox", job, ROOT):
        if not p.is_absolute() and (base / p).exists():
            p = base / p
            break
    if not p.exists():
        fail(f"fichier introuvable : {rel}")
    cj = job / "work" / "broll_credits.json"  # image / vidéo de banque (broll.py get) : crédit livré
    if cj.exists() and read_json(cj).get(str(rel).replace("\\", "/")):
        add_credit(job, read_json(cj)[str(rel).replace("\\", "/")])
    (job / "assets" / sub).mkdir(parents=True, exist_ok=True)
    if p.resolve() != (job / "assets" / sub / p.name).resolve():
        shutil.copy2(p, job / "assets" / sub / p.name)
    return f"assets/{sub}/{p.name}"


def spoken_at(words, text, lo, hi, after=0.0):
    """Instant où le premier mot significatif de `text` est dit entre lo et hi (sinon None)."""
    keys = [norm(t) for t in re.split(r"[\s'’-]+", text) if len(norm(t)) >= 3 or norm(t).isdigit()]
    if not keys:
        return None
    for w in words:
        if lo <= w["start"] <= hi and w["start"] >= after and norm(w["w"]) == keys[0]:
            return w["start"]
    return None


def split_words(text, cls="w"):
    return " ".join(f'<span class="{cls}">{esc(t)}</span>' for t in str(text).split())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("job")
    ap.add_argument("slug")
    ap.add_argument("--no-captions", action="store_true")
    ap.add_argument("--no-sfx", action="store_true")
    ap.add_argument("--size", help="9:16 | 1:1 | 4:5 | 16:9 | LxH (défaut : config)")
    ap.add_argument("--lang", help="sous-titres traduits (translate.py) : nl, en…")
    ap.add_argument("--style", help="style des sous-titres : pop | karaoke | minimal | boite | impact | duo")
    ap.add_argument("--emoji", action="store_true", help="emoji après les mots-clés")
    a = ap.parse_args()
    job = job_dir(a.job)
    c = config(job)
    vis, txt, sfxc = c["visual"], c["text"], c["sfx"]
    W, H = size_of(a.size, vis)
    work = job / "work"
    sb, tm = read_json(work / f"{a.slug}_storyboard.json"), read_json(work / f"{a.slug}_timing.json")
    words = read_json(work / f"{a.slug}_words.json")["words"]
    dur = float(tm["duration"])
    fam = vis["fontFamily"]
    bg, ink, accent = vis.get("bgColor", "#111111"), vis.get("inkColor", "#ffffff"), vis["accentColor"]
    _rgb = [int(accent.lstrip("#")[k:k + 2], 16) for k in (0, 2, 4)] if len(accent.lstrip("#")) == 6 else [0, 0, 0]
    box_ink = "#111111" if (0.299 * _rgb[0] + 0.587 * _rgb[1] + 0.114 * _rgb[2]) > 160 else "#ffffff"  # texte dans la boîte
    soft = vis.get("softColor", accent)

    faces = []
    for f in vis.get("fonts", []):
        src = asset(job, f["file"], "fonts")
        faces.append(f"@font-face {{ font-family: '{fam}'; src: url('{src}') format('{f.get("format", "woff2")}'); "
                     f"font-weight: {f.get('weight', 400)}; font-style: normal; }}")
    if vis.get("fontFile"):  # police variable (toutes les graisses dans un fichier)
        src = asset(job, vis["fontFile"], "fonts")
        faces.append(f"@font-face {{ font-family: '{fam}'; src: url('{src}'); font-weight: 100 900; font-style: normal; }}")
    tf = vis.get("titleFont")  # police des titres de la charte (ex. Playfair Display), sinon celle du texte
    if tf:
        src = asset(job, tf["file"], "fonts")
        faces.append(f"@font-face {{ font-family: '{tf['family']}'; src: url('{src}'); font-weight: {tf.get('weight', 400)}; "
                     f"font-style: normal; }}")
    logo = asset(job, vis["logo"], "img") if vis.get("logo") else None

    nodes, js, sfx_times, pops = [], [], [], []
    video_bg = []  # vidéos de fond des scènes photo / accroche
    extra_nodes, motion_report = [], []
    scenes = sb["scenes"]
    for i, sc in enumerate(scenes):
        t = tm["scenes"][i]
        s, e = float(t["start"]), float(t["end"])
        vs = t.get("voice_start") or s
        last = i == len(scenes) - 1
        d = round((e - s) + (0 if last else OV), 3)
        sid, kind = f"s{i}", sc["kind"]
        k0 = round(max(s + 0.12, vs - 0.15), 3)  # le contenu arrive juste avant la voix
        body, dark = "", kind in ("photo",) or (kind == "hook" and sc.get("image"))
        if kind == "block":  # bloc de la bibliothèque / du registre, monté comme sous-composition HyperFrames
            name = sc["block"]
            block_file(job, name)
            brand = brand_info(job)
            vals = {"logo": logo or "", "tagline": sc.get("text") or brand.get("tagline", ""), "info": sc.get("sub", ""),
                    "bg": bg, "ink": ink, "accent": accent, "font": fam, "blend": vis.get("logoBlend", "normal"),
                    "fill": bg, "icon": logo or "", "avatar": logo or "",  # fill : bloc de motion en scène plein écran
                    "card": ink}  # carte opaque (encre de la charte) : sur fond clair, une carte translucide manque de contraste
            vals.update(sc.get("vars", {}))
            nodes.append(mount(name, sid, s, d, W, H, 1 + i % 2, vals, z=i + 1))
            if i:
                sfx_times.append(s)
            continue
        if i:
            js.append(f'  enter("#{sid}", {s}, {json.dumps(sc.get("transition", "wipe-up" if i % 2 else "wipe-left"))});')
            sfx_times.append(s)

        is_vid = bool(sc.get("image")) and str(sc["image"]).lower().endswith((".mp4", ".webm", ".mov"))
        if sc.get("image") and kind in ("photo", "hook") and is_vid:
            # vidéo de fond : hors de la scène minutée (une vidéo minutée ne s'imbrique pas), même transition, dessous
            src = asset(job, sc["image"], "img")
            video_bg.append(f'    <div id="vb{i}" class="vbg" style="z-index:{i + 1}"><div class="wrap"><video id="vbv{i}" class="kb clip" '
                            f'src="{src}" data-start="{s}" data-duration="{d}" data-track-index="{60 + i}" muted playsinline></video></div></div>')
            body += '<div class="shade"></div>'
            js.append(f'  tl.set("#vb{i}", {{ opacity: 1 }}, {s}); tl.set("#vb{i}", {{ opacity: 0 }}, {round(s + d, 3)});')
            if i:
                js.append(f'  enter("#vb{i}", {s}, {json.dumps(sc.get("transition", "wipe-up" if i % 2 else "wipe-left"))});')
            js.append(f'  tl.fromTo("#vb{i} .kb", {{ scale: 1.04 }}, {{ scale: 1.12, duration: {d}, ease: "none", immediateRender: false }}, {s});')
        elif sc.get("image") and kind in ("photo", "hook"):
            img = asset(job, sc["image"], "img")
            body += f'<div class="ph"><img class="kb" src="{img}" alt=""></div><div class="shade"></div>'
            dx = 2.5 if i % 2 else -2.5
            js.append(f'  tl.fromTo("#{sid} .kb", {{ scale: 1.06, xPercent: {-dx} }}, '
                      f'{{ scale: 1.17, xPercent: {dx}, duration: {d}, ease: "none", immediateRender: false }}, {s});')

        if kind == "hook":
            if sc.get("kicker"):
                body += f'<div class="kicker a">{esc(sc["kicker"])}</div>'
                js.append(f'  rise("#{sid} .kicker", {k0});')
            body += f'<h1 class="hl">{split_words(sc["text"])}</h1><div class="rule a"></div>'
            js.append(f'  words("#{sid} .hl .w", {round(k0 + 0.1, 3)}, 0.07);')
            js.append(f'  draw("#{sid} .rule", {round(k0 + 0.5, 3)});')
        elif kind == "photo":
            if sc.get("kicker"):
                body += f'<div class="kicker on a">{esc(sc["kicker"])}</div>'
                js.append(f'  rise("#{sid} .kicker", {k0});')
            if sc.get("text"):
                body += f'<h2 class="ptitle">{split_words(sc["text"])}</h2>'
                js.append(f'  words("#{sid} .ptitle .w", {round(k0 + 0.12, 3)}, 0.06);')
        elif kind == "points":
            if sc.get("image"):
                img = asset(job, sc["image"], "img")
                body += f'<div class="strip"><img class="kb" src="{img}" alt=""></div>'
                js.append(f'  tl.fromTo("#{sid} .strip .kb", {{ scale: 1.04 }}, {{ scale: 1.14, duration: {d}, ease: "none", immediateRender: false }}, {s});')
            body += f'<div class="pbox"><h2 class="ttl a">{esc(sc.get("title", ""))}</h2><ul>'
            js.append(f'  rise("#{sid} .ttl", {k0});')
            items, prev = sc.get("items", []), k0
            span = max(0.6, (e - k0 - 0.8) / max(1, len(items)))
            for j, it in enumerate(items):
                at = spoken_at(words, it, k0, e, prev) or (k0 + 0.5 + j * span)
                at = round(max(at - 0.1, prev + 0.25 if j else k0 + 0.3), 3)
                prev = at
                body += f'<li class="it it{j}"><span class="dot"></span><span>{esc(it)}</span></li>'
                js.append(f'  rise("#{sid} .it{j}", {at}, 30);')
                pops.append(at)
            body += "</ul></div>"
        elif kind == "stat":
            val = str(sc["value"])
            num = re.sub(r"[^\d]", "", val)
            body += (f'<div class="sbox"><div class="kicker a">{esc(sc.get("kicker", ""))}</div>'
                     f'<div class="big a"><span class="pre">{esc(sc.get("prefix", ""))}</span><span class="num" '
                     f'data-to="{num}">{esc(val)}</span><span class="suf">{esc(sc.get("suffix", ""))}</span></div>'
                     f'<div class="rule a"></div><div class="lbl a">{esc(sc.get("label", ""))}</div></div>')
            at = spoken_at(words, val, s, e) or k0
            js.append(f'  rise("#{sid} .kicker", {k0});')
            js.append(f'  rise("#{sid} .big", {round(at - 0.2, 3)}, 40);')
            if num and sc.get("count", True):
                js.append(f'  count("#{sid} .num", {int(sc.get("from", 0))}, {int(num)}, {round(at - 0.2, 3)}, 1.2, {json.dumps(len(num) == 4)});')
            js.append(f'  draw("#{sid} .rule", {round(at + 0.4, 3)});')
            js.append(f'  rise("#{sid} .lbl", {round(at + 0.5, 3)});')
            pops.append(round(at - 0.2, 3))
        elif kind == "offer":
            body += (f'<div class="obox"><h2 class="ttl a">{esc(sc.get("title", ""))}</h2>'
                     f'<div class="old a">{esc(sc.get("old", ""))}<i class="strike"></i></div>'
                     f'<div class="new a">{esc(sc.get("new", ""))}</div>'
                     + (f'<div class="badge a">{esc(sc["badge"])}</div>' if sc.get("badge") else "") + "</div>")
            at = spoken_at(words, sc.get("new", ""), s, e) or (k0 + 1.2)
            js.append(f'  rise("#{sid} .ttl", {k0});')
            js.append(f'  rise("#{sid} .old", {round(k0 + 0.35, 3)});')
            js.append(f'  draw("#{sid} .strike", {round(at - 0.45, 3)});')
            js.append(f'  pop("#{sid} .new", {round(at - 0.1, 3)});')
            if sc.get("badge"):
                js.append(f'  pop("#{sid} .badge", {round(at + 0.5, 3)});')
            pops.append(round(at - 0.1, 3))
        elif kind == "quote":
            body += (f'<div class="qbox"><div class="qm a">“</div><blockquote>{split_words(sc["text"])}</blockquote>'
                     f'<div class="who a">{esc(sc.get("author", ""))}</div></div>')
            js.append(f'  rise("#{sid} .qm", {k0});')
            js.append(f'  words("#{sid} blockquote .w", {round(k0 + 0.15, 3)}, 0.04);')
            js.append(f'  rise("#{sid} .who", {round(min(e - 1.2, k0 + 1.4), 3)});')
        elif kind == "gallery":
            imgs = [asset(job, p, "img") for p in sc.get("images", [])[:3]]
            for j, src in enumerate(imgs):
                body += f'<div class="gal g{j} a"><img src="{src}" alt=""></div>'
                js.append(f'  card("#{sid} .g{j}", {round(k0 + j * 0.35, 3)}, {[-6, 4, -2][j]});')
            if sc.get("text"):
                body += f'<h2 class="gtitle">{split_words(sc["text"])}</h2>'
                js.append(f'  words("#{sid} .gtitle .w", {round(k0 + 1.0, 3)}, 0.06);')
        elif kind == "cta":
            if logo:
                body += f'<img class="logo a" src="{logo}" alt="">'
                js.append(f'  rise("#{sid} .logo", {k0}, 20);')
            body += (f'<h2 class="ctat">{split_words(sc.get("text", ""))}</h2><div class="rule a"></div>'
                     f'<div class="sub a">{esc(sc.get("sub", ""))}</div>')
            js.append(f'  words("#{sid} .ctat .w", {round(k0 + 0.35, 3)}, 0.06);')
            js.append(f'  draw("#{sid} .rule", {round(k0 + 0.8, 3)});')
            js.append(f'  rise("#{sid} .sub", {round(k0 + 1.0, 3)});')
        elif kind == "steps":  # étapes numérotées, chacune quand elle est dite
            body += f'<div class="sxbox"><h2 class="ttl a">{esc(sc.get("title", ""))}</h2><div class="sx"><i class="sxline"></i>'
            js.append(f'  rise("#{sid} .ttl", {k0});')
            stp, prev = sc.get("steps", []), k0
            span = max(0.7, (e - k0 - 0.8) / max(1, len(stp)))
            for j, it in enumerate(stp):
                at = spoken_at(words, it, k0, e, prev) or (k0 + 0.5 + j * span)
                at = round(max(at - 0.1, prev + 0.3 if j else k0 + 0.35), 3)
                prev = at
                body += (f'<div class="st st{j}"><span class="num">{j + 1}</span>'
                         f'<span class="stt">{esc(it)}</span></div>')
                js.append(f'  pop("#{sid} .st{j} .num", {at});')
                js.append(f'  rise("#{sid} .st{j} .stt", {round(at + 0.08, 3)}, 18);')
                pops.append(at)
            body += "</div></div>"
            js.append(f'  grow("#{sid} .sxline", {round(k0 + 0.3, 3)}, {round(max(0.8, prev - k0), 3)});')
        elif kind == "beforeafter":  # avant / après : volet qui balaie de droite à gauche
            ib, ia = asset(job, sc["before"], "img"), asset(job, sc["after"], "img")
            lb, la = (sc.get("labels") or ["Avant", "Après"])[:2]
            body += (f'<div class="ph"><img class="kb" src="{ib}" alt=""></div>'
                     f'<div class="ph after"><img class="kb2" src="{ia}" alt=""></div><i class="divider"></i>'
                     f'<span class="lab lb a">{esc(lb)}</span><span class="lab la a">{esc(la)}</span>')
            if sc.get("text"):
                body += f'<h2 class="ptitle">{split_words(sc["text"])}</h2><div class="shade"></div>'
                js.append(f'  words("#{sid} .ptitle .w", {round(k0 + 0.1, 3)}, 0.06);')
            at = spoken_at(words, la, k0, e) or round(k0 + 0.9, 3)
            js.append(f'  rise("#{sid} .lb", {k0}, 14);')
            wd = round(min(1.6, max(0.8, (e - at) * 0.55)), 2)  # le volet finit avant la scène suivante
            js.append(f'  wipe("#{sid}", {round(at - 0.15, 3)}, {wd});')
            js.append(f'  rise("#{sid} .la", {round(at - 0.15 + wd * 0.5, 3)}, 14);')
            js.append(f'  tl.fromTo("#{sid} .kb, #{sid} .kb2", {{ scale: 1.04 }}, {{ scale: 1.12, duration: {d}, ease: "none", immediateRender: false }}, {s});')
            sfx_times.append(round(at - 0.15, 3))
            dark = True
        elif kind == "address":  # adresse + horaires, épingle qui tombe
            if sc.get("image"):
                img = asset(job, sc["image"], "img")
                body += f'<div class="strip"><img class="kb" src="{img}" alt=""></div>'
                js.append(f'  tl.fromTo("#{sid} .strip .kb", {{ scale: 1.04 }}, {{ scale: 1.14, duration: {d}, ease: "none", immediateRender: false }}, {s});')
            body += (f'<div class="adbox"><svg class="pin a" viewBox="0 0 48 64" aria-hidden="true"><path d="M24 0C10.7 0 0 10.7 0 24c0 18 24 40 24 40s24-22 24-40C48 10.7 37.3 0 24 0z" fill="{accent}"/>'
                     f'<circle cx="24" cy="23" r="9" fill="{bg}"/></svg><h2 class="ttl a">{esc(sc.get("title", ""))}</h2>'
                     f'<div class="addr a">{esc(sc.get("address", ""))}</div>')
            js.append(f'  drop("#{sid} .pin", {k0});')
            js.append(f'  rise("#{sid} .ttl", {round(k0 + 0.35, 3)});')
            js.append(f'  rise("#{sid} .addr", {round(k0 + 0.6, 3)});')
            for j, h in enumerate(sc.get("hours", [])[:4]):
                body += f'<div class="hr hr{j} a">{esc(h)}</div>'
                js.append(f'  rise("#{sid} .hr{j}", {round(k0 + 0.95 + j * 0.25, 3)}, 16);')
            body += "</div>"
            pops.append(k0)
        elif kind == "team":  # 1 à 4 personnes : photo ronde, nom, fonction
            mem = sc.get("members", [])[:4]
            body += f'<div class="tmbox"><h2 class="ttl a">{esc(sc.get("title", ""))}</h2><div class="tm n{len(mem)}">'
            js.append(f'  rise("#{sid} .ttl", {k0});')
            prev = k0
            for j, mb in enumerate(mem):
                ph = asset(job, mb["photo"], "img")
                at = spoken_at(words, mb.get("name", ""), k0, e, prev) or (k0 + 0.45 + j * 0.45)
                at = round(max(at - 0.1, prev + 0.25 if j else k0 + 0.3), 3)
                prev = at
                body += (f'<div class="mb mb{j} a"><div class="av"><img src="{ph}" alt=""></div>'
                         f'<div class="mn">{esc(mb.get("name", ""))}</div><div class="mr">{esc(mb.get("role", ""))}</div></div>')
                js.append(f'  pop("#{sid} .mb{j}", {at});')
                pops.append(at)
            body += "</div></div>"
        elif kind == "product":  # produit détouré (PNG transparent) qui flotte, atouts qui apparaissent
            img = asset(job, sc["image"], "img")
            body += (f'<div class="pdglow"></div><div class="pdwrap"><img class="pd a" src="{img}" alt=""><i class="pdshadow a"></i></div>'
                     f'<div class="pdtop"><div class="kicker a">{esc(sc.get("kicker", ""))}</div>'
                     f'<h2 class="pdname">{split_words(sc.get("name", ""))}</h2></div><div class="feats">')
            js.append(f'  rise("#{sid} .kicker", {k0});')
            js.append(f'  words("#{sid} .pdname .w", {round(k0 + 0.1, 3)}, 0.06);')
            js.append(f'  tl.fromTo("#{sid} .pd", {{ opacity: 0, y: 140, scale: 0.86 }}, {{ opacity: 1, y: 0, scale: 1, duration: 0.9, ease: "power3.out", immediateRender: false }}, {round(k0 + 0.2, 3)});')
            js.append(f'  tl.fromTo("#{sid} .pdshadow", {{ opacity: 0, scaleX: 0.4 }}, {{ opacity: 1, scaleX: 1, duration: 0.9, ease: "power3.out", immediateRender: false }}, {round(k0 + 0.2, 3)});')
            js.append(f'  tl.to("#{sid} .pd", {{ y: -18, duration: {round(max(1.0, e - k0 - 1.2), 3)}, ease: "sine.inOut" }}, {round(k0 + 1.1, 3)});')
            prev = k0 + 0.8
            for j, ft in enumerate(sc.get("features", [])[:3]):
                at = spoken_at(words, ft, k0, e, prev) or (prev + 0.5)
                at = round(max(at - 0.1, prev + 0.25), 3)
                prev = at
                body += f'<span class="ft ft{j} a">{esc(ft)}</span>'
                js.append(f'  pop("#{sid} .ft{j}", {at});')
                pops.append(at)
            body += "</div>"
            if sc.get("price"):
                body += f'<div class="pprice a">{esc(sc["price"])}</div>'
                js.append(f'  pop("#{sid} .pprice", {round(spoken_at(words, sc["price"], k0, e) or prev + 0.5, 3)});')
        elif kind == "browser":  # navigateur (cadre inspiré d'Onda, MIT) : barre d'adresse + capture du site qui défile
            src = asset(job, sc["image"], "img")
            body += (f'<div class="dvbox"><div class="kicker a">{esc(sc.get("kicker", ""))}</div>'
                     f'<h2 class="dvt">{split_words(sc.get("title", ""))}</h2></div>'
                     f'<div class="browser a"><div class="bw-bar"><i></i><i></i><i></i><span class="bw-url">{esc(sc.get("url", ""))}</span></div>'
                     f'<div class="bw-screen"><img class="dv-media" src="{src}" alt=""></div></div>')
            js.append(f'  rise("#{sid} .kicker", {k0});')
            js.append(f'  words("#{sid} .dvt .w", {round(k0 + 0.1, 3)}, 0.06);')
            js.append(f'  tl.fromTo("#{sid} .browser", {{ opacity: 0, y: 160, scale: 0.92 }}, {{ opacity: 1, y: 0, scale: 1, duration: 0.8, '
                      f'ease: "power3.out", immediateRender: false }}, {round(k0 + 0.2, 3)});')
            if sc.get("scroll", True):
                from common import probe as _probe
                pi = _probe(job / src)
                ratio, scr = (pi["height"] or 1) / (pi["width"] or 1), 0.62  # écran du navigateur : hauteur / largeur
                pct = 0 if ratio <= scr else min((ratio - scr) / ratio, scr * float(sc.get("screens", 2)) / ratio) * 100
                if pct > 1:
                    js.append(f'  tl.fromTo("#{sid} .dv-media", {{ yPercent: 0 }}, {{ yPercent: -{round(pct, 2)}, '
                              f'duration: {round(max(1.0, e - k0 - 1.2), 3)}, ease: "power1.inOut", immediateRender: false }}, {round(k0 + 1.0, 3)});')
        elif kind == "device":  # téléphone (cadre inspiré d'Onda, MIT) : capture ou vidéo d'écran, défilement facultatif
            src = asset(job, sc["image"], "img")
            is_vid = src.lower().endswith((".mp4", ".webm", ".mov"))
            screen = (f'<video class="dv-media clip" src="{src}" data-start="{s}" data-duration="{d}" data-track-index="{20 + i}" muted playsinline></video>'
                      if is_vid else f'<img class="dv-media" src="{src}" alt="">')
            body += (f'<div class="dvbox"><div class="kicker a">{esc(sc.get("kicker", ""))}</div>'
                     f'<h2 class="dvt">{split_words(sc.get("title", ""))}</h2></div>'
                     f'<div class="phone a"><div class="notch"></div><div class="screen">{screen}</div></div>')
            js.append(f'  rise("#{sid} .kicker", {k0});')
            js.append(f'  words("#{sid} .dvt .w", {round(k0 + 0.1, 3)}, 0.06);')
            js.append(f'  tl.fromTo("#{sid} .phone", {{ opacity: 0, y: 220, rotation: 4 }}, {{ opacity: 1, y: 0, rotation: 0, duration: 0.8, '
                      f'ease: "power3.out", immediateRender: false }}, {round(k0 + 0.2, 3)});')
            if sc.get("scroll", True) and not is_vid:  # longue capture : défile d'environ un écran et demi (taille réelle)
                from common import probe as _probe
                pi = _probe(job / src)
                ratio = (pi["height"] or 1) / (pi["width"] or 1)  # hauteur affichée / largeur d'écran
                scr = 2.09  # hauteur / largeur de l'écran du téléphone
                pct = 0 if ratio <= scr else min((ratio - scr) / ratio, scr * float(sc.get("screens", 1.5)) / ratio) * 100
                if pct > 1:
                    js.append(f'  tl.fromTo("#{sid} .dv-media", {{ yPercent: 0 }}, {{ yPercent: -{round(pct, 2)}, '
                              f'duration: {round(max(1.0, e - k0 - 1.2), 3)}, ease: "power1.inOut", immediateRender: false }}, {round(k0 + 1.0, 3)});')
        else:
            fail(f"type de scène inconnu : {kind}")

        if sc.get("motions"):  # blocs de motion design par-dessus la scène, calés sur un mot de sa phrase
            mn, mrep = motion_nodes(job, sc["motions"], words, W, H, lo=s, hi=e,
                                    base_vals={"accent": accent, "font": fam, "icon": logo or "", "avatar": logo or "",
                                               "top": 22 if H > W else 18}, track=40 + i * 5, z=100 + i * 5)
            extra_nodes += mn
            motion_report += mrep
        nodes.append(f'    <div id="{sid}" class="clip scene k-{kind}{" dark" if dark else ""}{" vid" if is_vid and kind in ("photo", "hook") else ""}" data-start="{s}" '
                     f'data-duration="{d}" data-track-index="{1 + i % 2}" style="z-index:{i + 1}">'
                     f'<div class="wrap">{body}</div></div>')

    # sous-titres (voix) : bandeau lisible sur fond clair comme sur photo
    caps_nodes, caps_js = [], []
    tj = work / f"{a.slug}_text{'_' + a.lang if a.lang else ''}.json"
    style = a.style or txt.get("captionStyle", "minimal")
    if style not in STYLES:
        style = "pop"
    use_emoji, last_emo = a.emoji or txt.get("captionEmoji", False), -99.0
    if not a.no_captions and tj.exists():
        caps = read_json(tj)["captions"]
        for i, g in enumerate(caps):
            st = round(max(0.1, g["words"][0]["start"] - 0.05), 3)
            nxt = caps[i + 1]["words"][0]["start"] - 0.05 if i + 1 < len(caps) else dur
            en = round(min(dur, max(g["end"] + 0.25, st + 0.4), max(nxt, g["end"])), 3)
            if en - st <= 0.1:
                continue
            spans, emo, last_emo = caption_spans(g["words"], style, use_emoji, st, last_emo)
            caps_nodes.append(f'    <div class="clip cap" id="cap-{g["id"]}" data-start="{st}" data-duration="{round(en - st, 3)}" '
                              f'data-track-index="6"><div class="in">{spans}</div></div>')
            times = [[round(max(st, w["start"]), 3), round(w["end"], 3)] for w in g["words"]]
            caps_js.append(f'  cap("cap-{g["id"]}", {st}, {en}, {json.dumps(times)});')
            if emo is not None:
                caps_js.append(emoji_tween(f'cap-{g["id"]}', emo))

    audio = [f'    <audio id="voice" class="clip" src="assets/{a.slug}_voice.wav" data-start="0" data-duration="{dur}" '
             f'data-track-index="8" data-volume="1"></audio>']
    mj = work / f"{a.slug}_music.json"
    if mj.exists():
        audio.append(f'    <audio id="music" class="clip" src="{read_json(mj)["file"]}" data-start="0" data-duration="{dur}" '
                     f'data-track-index="9" data-volume="1"></audio>')
    if not a.no_sfx and sfxc["enabled"]:
        wsrc, wpeak, wdur = sfx_asset(job, sfxc["whoosh"])
        for k, t0 in enumerate(sfx_times):
            st = round(max(0, t0 + 0.12 - wpeak), 3)
            audio.append(f'    <audio id="sfx-w{k}" class="clip" src="{wsrc}" data-start="{st}" data-duration="{min(wdur, dur - st)}" '
                         f'data-track-index="11" data-volume="{sfxc["whooshVolume"] * 0.8}"></audio>')
        if sfxc.get("pop"):
            psrc, ppeak, pdur = sfx_asset(job, sfxc["pop"])
            for k, t0 in enumerate(pops):
                st = round(max(0, t0 + 0.08 - ppeak), 3)
                audio.append(f'    <audio id="sfx-p{k}" class="clip" src="{psrc}" data-start="{st}" data-duration="{min(pdur, dur - st)}" '
                             f'data-track-index="12" data-volume="{sfxc.get("popVolume", 0.35)}"></audio>')

    wide = W >= H
    u = W / 1080 if not wide else H / 1080 * 0.92
    css = f"""
  {chr(10).join(faces)}
  html, body {{ margin: 0; background: {bg}; width: {W}px; height: {H}px; overflow: hidden; }}
  #root {{ position: relative; width: {W}px; height: {H}px; overflow: hidden; background: {bg};
           font-family: '{fam}', 'Inter', sans-serif; color: {ink}; }}
  .scene {{ position: absolute; inset: 0; }}
  .wrap {{ position: absolute; inset: 0; background: {bg}; overflow: hidden; }}
  .wrap .a, .wrap .w, .wrap .kicker, .wrap .rule, .wrap .it, .wrap .logo {{ opacity: 0; }}
  .wrap .w {{ display: inline-block; }}
  .ph {{ position: absolute; inset: 0; overflow: hidden; }}
  .vbg {{ position: absolute; inset: 0; opacity: 0; }}  /* visible seulement pendant sa scène (tl.set) */
  .vbg .wrap {{ background: #000; }}
  .vbg video {{ width: 100%; height: 100%; object-fit: cover; display: block; }}
  .scene.vid .wrap {{ background: transparent; }}  /* la vidéo de fond (.vbg) est juste dessous */
  .ph img, .strip img, .gal img {{ width: 100%; height: 100%; object-fit: cover; display: block; }}
  .shade {{ position: absolute; inset: 0; background: linear-gradient(180deg, rgba(0,0,0,.05) 35%, rgba(0,0,0,.62) 100%); }}
  .kicker {{ position: absolute; left: {round(90*u)}px; top: {round(H*0.20)}px; font-size: {round(30*u)}px;
             letter-spacing: .32em; text-transform: uppercase; color: {accent}; }}
  .kicker.on {{ color: #fff; top: auto; bottom: {round(H*0.47)}px; text-shadow: {SHADOW}; }}
  .hl {{ position: absolute; left: {round(90*u)}px; right: {round(90*u)}px; top: {round(H*0.25)}px; margin: 0;
         font-size: {round(118*u)}px; line-height: 1.02; font-weight: 700; letter-spacing: -.01em; text-wrap: balance; }}
  .dark .hl, .dark .ptitle {{ color: #fff; text-shadow: {SHADOW}; }}
  .dark .kicker {{ color: #fff; text-shadow: {SHADOW}; }}
  .dark .rule {{ background: #fff; }}
  .rule {{ position: absolute; left: {round(90*u)}px; width: {round(180*u)}px; height: {max(3, round(6*u))}px;
           background: {accent}; transform-origin: 0 50%; top: {round(H*0.47)}px; }}
  .ptitle {{ position: absolute; left: {round(90*u)}px; right: {round(90*u)}px; bottom: {round(H*0.36)}px; margin: 0;
             font-size: {round(92*u)}px; line-height: 1.04; font-weight: 700; text-wrap: balance; }}
  .strip {{ position: absolute; left: 0; right: 0; top: 0; height: {round(H*0.36)}px; overflow: hidden; }}
  .pbox {{ position: absolute; left: {round(90*u)}px; right: {round(90*u)}px; top: {round(H*0.40)}px; }}
  .k-points:not(:has(.strip)) .pbox {{ top: {round(H*0.18)}px; }}
  .ttl {{ margin: 0 0 {round(56*u)}px; font-size: {round(84*u)}px; line-height: 1.05; font-weight: 700; }}
  ul {{ list-style: none; margin: 0; padding: 0; }}
  .it {{ display: flex; align-items: center; gap: {round(32*u)}px; font-size: {round(68*u)}px; line-height: 1.15;
         margin: 0 0 {round(40*u)}px; }}
  .dot {{ flex: none; width: {round(24*u)}px; height: {round(24*u)}px; background: {accent}; }}
  .sbox, .obox, .qbox {{ position: absolute; left: {round(90*u)}px; right: {round(90*u)}px; top: {round(H*0.27)}px; }}
  .sbox .kicker {{ position: static; margin-bottom: {round(24*u)}px; }}
  .big {{ font-size: {round(330*u)}px; line-height: .95; font-weight: 700; letter-spacing: -.03em; color: {accent};
          font-variant-numeric: tabular-nums; }}
  .sbox .rule, .obox .rule {{ position: static; margin: {round(36*u)}px 0; }}
  .lbl {{ font-size: {round(66*u)}px; line-height: 1.12; text-wrap: balance; }}
  .old {{ position: relative; display: inline-block; font-size: {round(84*u)}px; color: {ink}; opacity: 0; margin-top: {round(10*u)}px; }}
  .strike {{ position: absolute; left: -4%; right: -4%; top: 52%; height: {max(3, round(7*u))}px; background: {accent};
             transform-origin: 0 50%; transform: scaleX(0); }}
  .new {{ font-size: {round(210*u)}px; line-height: 1; font-weight: 700; color: {accent}; margin-top: {round(16*u)}px; }}
  .badge {{ display: inline-block; margin-top: {round(36*u)}px; padding: {round(16*u)}px {round(30*u)}px; background: {ink};
            color: {bg}; font-size: {round(40*u)}px; letter-spacing: .12em; text-transform: uppercase; }}
  .qm {{ font-size: {round(260*u)}px; line-height: .6; color: {accent}; height: {round(130*u)}px; }}
  blockquote {{ margin: 0; font-size: {round(70*u)}px; line-height: 1.16; font-style: italic; text-wrap: balance; }}
  .who {{ margin-top: {round(40*u)}px; font-size: {round(40*u)}px; letter-spacing: .18em; text-transform: uppercase; color: {accent}; }}
  .gal {{ position: absolute; width: {round(540*u)}px; height: {round(640*u)}px; overflow: hidden;
          box-shadow: 0 {round(24*u)}px {round(60*u)}px rgba(0,0,0,.28); border: {round(14*u)}px solid #fff; }}
  .g0 {{ left: {round(70*u)}px; top: {round(H*0.21)}px; }}
  .g1 {{ right: {round(70*u)}px; top: {round(H*0.30)}px; }}
  .g2 {{ left: {round(210*u)}px; top: {round(H*0.43)}px; }}
  .gtitle {{ position: absolute; left: {round(90*u)}px; right: {round(90*u)}px; top: {round(H*0.07)}px; margin: 0;
             font-size: {round(84*u)}px; font-weight: 700; line-height: 1.05; }}
  .k-cta .wrap {{ display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center;
                  padding: 0 {round(90*u)}px {round(H*0.18)}px; box-sizing: border-box; }}
  .logo {{ width: {round(760*u)}px; height: auto; mix-blend-mode: {vis.get("logoBlend", "normal")}; margin-bottom: {round(70*u)}px; }}
  .ctat {{ margin: 0; font-size: {round(88*u)}px; line-height: 1.05; font-weight: 700; text-wrap: balance; }}
  .k-cta .rule {{ position: static; margin: {round(40*u)}px auto; transform-origin: 50% 50%; }}
  .sub {{ font-size: {round(42*u)}px; letter-spacing: .08em; }}
  .cap {{ position: absolute; left: 0; right: 0; top: {round(H * 0.80)}px; text-align: center; z-index: 100; }}
  .cap .in {{ display: inline-block; max-width: 84%; padding: .16em .5em; border-radius: .25em;
              background: rgba(20,18,16,.80); color: #fff; font-family: '{fam}', 'Inter', sans-serif; font-weight: 700;
              font-size: {round(50*u)}px; line-height: 1.2; }}
  .cap .w {{ display: inline-block; margin: 0 .06em; {"opacity: 0;" if style in ("pop", "duo") else ""} }}"""
    css += caption_css(style, accent, "0 2px 6px rgba(0,0,0,.5)")  # styles boîte / impact / duo dans le bandeau
    css += f"""
  .sxbox, .tmbox, .adbox {{ position: absolute; left: {round(90*u)}px; right: {round(90*u)}px; top: {round(H*0.16)}px; }}
  .sxbox, .tmbox {{ top: {round(H*0.22)}px; }}
  .sx {{ position: relative; }}
  .sxline {{ position: absolute; left: {round(68*u)}px; top: {round(70*u)}px; bottom: {round(150*u)}px; width: {max(3, round(5*u))}px;
             background: {soft}; transform-origin: 50% 0; transform: scaleY(0); }}
  .st {{ position: relative; display: flex; align-items: center; gap: {round(40*u)}px; margin: 0 0 {round(84*u)}px; }}
  .num {{ flex: none; width: {round(140*u)}px; height: {round(140*u)}px; border-radius: 50%; border: {max(3, round(6*u))}px solid {accent};
          background: {bg}; color: {accent}; display: flex; align-items: center; justify-content: center;
          font-size: {round(70*u)}px; font-weight: 700; opacity: 0; }}
  .stt {{ font-size: {round(74*u)}px; line-height: 1.12; opacity: 0; text-wrap: balance; }}
  .after {{ clip-path: inset(0 0 0 100%); }}
  .divider {{ position: absolute; top: 0; bottom: 0; left: 0; width: {max(4, round(6*u))}px; margin-left: -{max(2, round(3*u))}px;
              background: #fff; box-shadow: 0 0 {round(24*u)}px rgba(0,0,0,.45); opacity: 0; }}
  .lab {{ position: absolute; top: {round(H*0.07)}px; padding: .3em .7em; border-radius: .3em; font-size: {round(40*u)}px;
          font-weight: 700; letter-spacing: .1em; text-transform: uppercase; background: rgba(20,18,16,.72); color: #fff; }}
  .lb {{ left: {round(60*u)}px; }} .la {{ right: {round(60*u)}px; background: {accent}; }}
  .k-beforeafter .ptitle {{ z-index: 2; }} .k-beforeafter .shade {{ z-index: 1; }}
  .k-address .strip ~ .adbox {{ top: {round(H*0.40)}px; }}
  .pin {{ width: {round(84*u)}px; height: auto; display: block; margin-bottom: {round(24*u)}px; }}
  .addr {{ font-size: {round(56*u)}px; line-height: 1.15; font-weight: 700; margin-bottom: {round(30*u)}px; text-wrap: balance; }}
  .hr {{ font-size: {round(44*u)}px; line-height: 1.3; }}
  .tm {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: {round(56*u)}px {round(40*u)}px; }}
  .tm.n1 {{ grid-template-columns: 1fr; justify-items: center; }}
  .mb {{ text-align: center; }}
  .av {{ width: {round(400*u)}px; height: {round(400*u)}px; margin: 0 auto {round(22*u)}px; border-radius: 50%; overflow: hidden;
         border: {round(10*u)}px solid {accent}; }}
  .av img {{ width: 100%; height: 100%; object-fit: cover; }}
  .mn {{ font-size: {round(56*u)}px; font-weight: 700; line-height: 1.1; }} .mr {{ font-size: {round(36*u)}px; opacity: .8; }}
  .pdglow {{ position: absolute; left: 50%; top: 52%; width: {round(900*u)}px; height: {round(900*u)}px; margin: -{round(450*u)}px 0 0 -{round(450*u)}px;
             border-radius: 50%; background: radial-gradient(circle, {soft} 0%, transparent 68%); }}
  .pdwrap {{ position: absolute; left: 10%; right: 10%; top: {round(H*0.27)}px; height: {round(H*0.42)}px; display: flex;
             align-items: flex-end; justify-content: center; }}
  .pd {{ max-width: 100%; max-height: 100%; object-fit: contain; position: relative; z-index: 1;
         filter: drop-shadow(0 {round(30*u)}px {round(40*u)}px rgba(0,0,0,.18)); }}
  .pdshadow {{ position: absolute; bottom: -{round(18*u)}px; left: 25%; right: 25%; height: {round(36*u)}px; border-radius: 50%;
               background: radial-gradient(ellipse, rgba(0,0,0,.28), transparent 70%); }}
  .pdtop {{ position: absolute; left: {round(90*u)}px; right: {round(90*u)}px; top: {round(H*0.08)}px; text-align: center; }}
  .pdtop .kicker {{ position: static; margin-bottom: {round(16*u)}px; }}
  .pdname {{ margin: 0; font-size: {round(92*u)}px; line-height: 1.04; font-weight: 700; }}
  .feats {{ position: absolute; left: {round(60*u)}px; right: {round(60*u)}px; top: {round(H*0.71)}px; display: flex; flex-wrap: wrap;
            justify-content: center; gap: {round(18*u)}px; }}
  .ft {{ padding: .35em .8em; border-radius: 99px; background: {ink}; color: {bg}; font-size: {round(40*u)}px; font-weight: 700; }}
  .pprice {{ position: absolute; right: {round(70*u)}px; top: {round(H*0.30)}px; padding: .3em .55em; border-radius: .3em;
             background: {accent}; color: #fff; font-size: {round(64*u)}px; font-weight: 700; transform: rotate(-6deg); }}"""
    css += f"""
  .dvbox {{ position: absolute; left: {round(90*u)}px; right: {round(90*u)}px; top: {round(H*0.07)}px; text-align: center; }}
  .dvbox .kicker {{ position: static; margin-bottom: {round(14*u)}px; }}
  .dvt {{ margin: 0; font-size: {round(80*u)}px; line-height: 1.05; font-weight: 700; text-wrap: balance; }}
  .phone {{ position: absolute; left: 50%; top: {round(H*0.235)}px; width: {round(H*0.51*0.495)}px; height: {round(H*0.51)}px;
            margin-left: -{round(H*0.51*0.495/2)}px; border-radius: {round(76*u)}px; background: #111; padding: {round(18*u)}px;
            box-shadow: 0 {round(40*u)}px {round(90*u)}px rgba(0,0,0,.35), inset 0 0 0 {round(3*u)}px #333; }}
  .screen {{ position: relative; width: 100%; height: 100%; border-radius: {round(60*u)}px; overflow: hidden; background: #fff; }}
  .dv-media {{ position: absolute; left: 0; top: 0; width: 100%; height: auto; min-height: 100%; object-fit: cover; object-position: top; }}
  video.dv-media {{ height: 100%; }}
  .browser {{ position: absolute; left: 50%; top: {round(H*0.27)}px; width: {round(W*0.9)}px; margin-left: -{round(W*0.45)}px;
              border-radius: {round(22*u)}px; overflow: hidden; background: #fff; box-shadow: 0 {round(36*u)}px {round(80*u)}px rgba(0,0,0,.3); }}
  .bw-bar {{ display: flex; align-items: center; gap: {round(10*u)}px; padding: {round(16*u)}px {round(20*u)}px; background: #ececef; }}
  .bw-bar i {{ width: {round(16*u)}px; height: {round(16*u)}px; border-radius: 50%; background: #ff5f57; }}
  .bw-bar i:nth-child(2) {{ background: #febc2e; }} .bw-bar i:nth-child(3) {{ background: #28c840; }}
  .bw-url {{ flex: 1; margin-left: {round(14*u)}px; padding: {round(8*u)}px {round(18*u)}px; border-radius: 99px; background: #fff; color: #555;
             font-size: {round(26*u)}px; font-family: system-ui, sans-serif; }}
  .bw-screen {{ position: relative; width: 100%; height: {round(W*0.9*0.62)}px; overflow: hidden; }}
  .notch {{ position: absolute; left: 50%; top: {round(30*u)}px; width: {round(150*u)}px; height: {round(40*u)}px;
            margin-left: -{round(75*u)}px; border-radius: 99px; background: #111; z-index: 2; }}"""
    if wide:  # carré et paysage : texte à gauche, image à droite ou en fond
        L, R = round(W * 0.07), round(W * (0.46 if W > H * 1.2 else 0.40))
        css += f"""
  .kicker {{ left: {L}px; top: {round(H*0.16)}px; }}
  .kicker.on {{ left: {L}px; top: auto; bottom: {round(H*0.50)}px; }}
  .hl {{ left: {L}px; right: {R}px; top: {round(H*0.22)}px; }}
  .rule {{ left: {L}px; top: {round(H*0.62)}px; }}
  .ptitle {{ left: {L}px; right: {R}px; bottom: {round(H*0.24)}px; }}
  .shade {{ background: linear-gradient(90deg, rgba(0,0,0,.62) 0%, rgba(0,0,0,.25) 55%, rgba(0,0,0,0) 80%); }}
  .strip {{ left: auto; right: 0; top: 0; bottom: 0; width: {round(W*0.45)}px; height: auto; }}
  .pbox {{ left: {L}px; right: {round(W*0.50)}px; top: {round(H*0.14)}px; }}
  .k-points:not(:has(.strip)) .pbox {{ top: {round(H*0.14)}px; right: {L}px; }}
  .sbox, .obox, .qbox {{ left: {L}px; right: {L}px; top: {round(H*0.16)}px; }}
  .gal {{ width: {round(H*0.40)}px; height: {round(H*0.50)}px; border-width: {round(10*u)}px; }}
  .g0 {{ left: auto; right: {round(W*0.30)}px; top: {round(H*0.08)}px; }}
  .g1 {{ right: {round(W*0.05)}px; top: {round(H*0.14)}px; }}
  .g2 {{ left: auto; right: {round(W*0.17)}px; top: {round(H*0.40)}px; }}
  .gtitle {{ left: {L}px; right: {round(W*0.62 if W > H * 1.2 else W*0.55)}px; top: {round(H*0.22)}px; }}
  .k-cta .wrap {{ padding-bottom: {round(H*0.12)}px; }}
  .logo {{ width: {round(H*0.62)}px; margin-bottom: {round(40*u)}px; }}
  .cap {{ top: {round(H*0.83)}px; }}
  .dvbox {{ left: {L}px; right: {round(W*0.50)}px; top: {round(H*0.30)}px; text-align: left; }}
  .browser {{ left: auto; right: {round(W*0.05)}px; margin-left: 0; width: {round(W*0.5)}px; top: {round(H*0.16)}px; }}
  .bw-screen {{ height: {round(W*0.5*0.62)}px; }}
  .phone {{ left: auto; right: {round(W*0.14)}px; top: {round(H*0.06)}px; height: {round(H*0.88)}px; width: {round(H*0.88*0.495)}px;
            margin-left: 0; }}
  .sxbox, .tmbox, .adbox {{ left: {L}px; top: {round(H*0.12)}px; }}
  .k-address .strip ~ .adbox {{ top: {round(H*0.14)}px; right: {round(W*0.50)}px; }}
  .tm {{ grid-template-columns: repeat(4, 1fr); }}
  .tm.n2 {{ grid-template-columns: repeat(2, 1fr); }} .tm.n3 {{ grid-template-columns: repeat(3, 1fr); }}
  .av {{ width: {round(H*0.27)}px; height: {round(H*0.27)}px; }}
  .pdwrap {{ left: auto; right: 6%; width: {round(W*0.45)}px; top: {round(H*0.12)}px; height: {round(H*0.66)}px; }}
  .pdglow {{ left: 72%; top: 48%; }}
  .pdtop {{ left: {L}px; right: {round(W*0.52)}px; top: {round(H*0.18)}px; text-align: left; }}
  .feats {{ left: {L}px; right: {round(W*0.52)}px; top: {round(H*0.56)}px; justify-content: flex-start; }}
  .pprice {{ right: {round(W*0.06)}px; top: {round(H*0.10)}px; }}"""
        if W <= H * 1.2:  # carré / 4:5 : moins de largeur, on resserre
            css += f"""
  .hl {{ font-size: {round(100*u)}px; right: {round(W*0.30)}px; }}
  .rule {{ top: {round(H*0.72)}px; }}
  .gal {{ width: {round(H*0.30)}px; height: {round(H*0.38)}px; }}
  .g0 {{ right: {round(W*0.27)}px; top: {round(H*0.10)}px; }}
  .g1 {{ right: {round(W*0.04)}px; top: {round(H*0.18)}px; }}
  .g2 {{ right: {round(W*0.16)}px; top: {round(H*0.46)}px; }}
  .gtitle {{ right: {round(W*0.58)}px; top: {round(H*0.26)}px; font-size: {round(70*u)}px; }}"""

    title_css = (f"""
  .hl, .ptitle, .ttl, .gtitle, .ctat, .pdname, .dvt, .addr, .qbox p, .big, .new {{ font-family: '{tf['family']}', Georgia, serif;
    font-weight: {tf.get('weight', 400)}; letter-spacing: 0; }}""" if tf else "")
    doc = f"""<!doctype html>
<html lang="fr">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width={W}, height={H}" />
<title>{esc(a.slug)}</title>
<script src="https://cdn.jsdelivr.net/npm/gsap@3.15.0/dist/gsap.min.js"></script>
<style>{css}{title_css}
</style>
</head>
<body>
  <div id="root" data-composition-id="film" data-start="0" data-width="{W}" data-height="{H}" data-duration="{dur}">
{chr(10).join(video_bg)}
{chr(10).join(nodes)}
{chr(10).join(extra_nodes)}
{chr(10).join(caps_nodes)}
{chr(10).join(audio)}
  </div>
<script>
  window.__timelines = window.__timelines || {{}};
  const tl = gsap.timeline({{ paused: true }});
  const INK = {json.dumps("#ffffff")}, ACCENT = {json.dumps(accent)}, BOXINK = {json.dumps(box_ink)};
  function rise(sel, t, y) {{
    tl.fromTo(sel, {{ opacity: 0, y: y || 24 }}, {{ opacity: 1, y: 0, duration: 0.6, ease: "power3.out", immediateRender: false }}, t);
  }}
  function words(sel, t, gap) {{
    tl.fromTo(sel, {{ opacity: 0, yPercent: 60 }}, {{ opacity: 1, yPercent: 0, duration: 0.55, ease: "power3.out",
      stagger: gap, immediateRender: false }}, t);
  }}
  function draw(sel, t) {{
    tl.fromTo(sel, {{ opacity: 1, scaleX: 0 }}, {{ opacity: 1, scaleX: 1, duration: 0.6, ease: "power2.inOut", immediateRender: false }}, t);
  }}
  function pop(sel, t) {{
    tl.fromTo(sel, {{ opacity: 0, scale: 0.7 }}, {{ opacity: 1, scale: 1, duration: 0.5, ease: "back.out(2.2)", immediateRender: false }}, t);
  }}
  function card(sel, t, rot) {{
    tl.fromTo(sel, {{ opacity: 0, y: 120, rotation: rot * 2 }}, {{ opacity: 1, y: 0, rotation: rot, duration: 0.8,
      ease: "power3.out", immediateRender: false }}, t);
  }}
  function count(sel, from, to, t, d, plain) {{
    const el = document.querySelector(sel), o = {{ v: from }};
    const fmt = function (v) {{ v = Math.round(v); return plain ? String(v) : v.toLocaleString("fr-BE"); }};
    tl.fromTo(o, {{ v: from }}, {{ v: to, duration: d, ease: "power2.out", immediateRender: false,
      onUpdate: function () {{ el.textContent = fmt(o.v); }} }}, t);
  }}
  function grow(sel, t, d) {{
    tl.fromTo(sel, {{ scaleY: 0 }}, {{ scaleY: 1, duration: d, ease: "power1.inOut", immediateRender: false }}, t);
  }}
  function drop(sel, t) {{
    tl.fromTo(sel, {{ opacity: 0, y: -160 }}, {{ opacity: 1, y: 0, duration: 0.7, ease: "bounce.out", immediateRender: false }}, t);
  }}
  function wipe(sid, t, d) {{
    tl.fromTo(sid + " .after", {{ clipPath: "inset(0 0 0 100%)" }}, {{ clipPath: "inset(0 0 0 0%)", duration: d, ease: "power2.inOut", immediateRender: false }}, t);
    tl.fromTo(sid + " .divider", {{ x: {W}, opacity: 1 }}, {{ x: 0, opacity: 1, duration: d, ease: "power2.inOut", immediateRender: false }}, t);
    tl.to(sid + " .divider", {{ opacity: 0, duration: 0.2 }}, t + d);
  }}
  function enter(sel, t, how) {{
    const w = sel + " .wrap";
    if (how === "iris") {{  // transitions iris / zoom / flou : portées depuis Onda (MIT)
      tl.fromTo(w, {{ clipPath: "circle(0% at 50% 50%)" }}, {{ clipPath: "circle(75% at 50% 50%)", duration: {OV} + 0.1,
        ease: "power2.inOut", immediateRender: false }}, t);
      return;
    }}
    if (how === "zoom") {{
      tl.fromTo(w, {{ scale: 1.25, opacity: 0 }}, {{ scale: 1, opacity: 1, duration: {OV} + 0.1, ease: "power3.out", immediateRender: false }}, t);
      return;
    }}
    if (how === "blur") {{
      tl.fromTo(w, {{ filter: "blur(30px)", opacity: 0 }}, {{ filter: "blur(0px)", opacity: 1, duration: {OV} + 0.1, ease: "power2.out",
        immediateRender: false }}, t);
      return;
    }}
    const from = how === "wipe-left" ? "inset(0 0 0 100%)" : how === "fade" ? "inset(0 0 0 0)" : "inset(100% 0 0 0)";
    tl.fromTo(w, {{ clipPath: from, opacity: how === "fade" ? 0 : 1 }},
      {{ clipPath: "inset(0 0 0 0)", opacity: 1, duration: {OV}, ease: "power3.inOut", immediateRender: false }}, t);
  }}
{caption_js(style)}

{chr(10).join(js)}
{chr(10).join(caps_js)}

  window.__timelines["film"] = tl;
</script>
</body>
</html>
"""
    (job / "index.html").write_text(doc, encoding="utf-8")
    out(ok=True, format=f"{W}x{H}", duree=round(dur, 1), scenes=len(scenes), sous_titres=len(caps_nodes),
        sfx=len(sfx_times) + len(pops), musique=mj.exists(), motions=motion_report, suite="npx hyperframes check, snapshot, puis rendu")


if __name__ == "__main__":
    main()

"""PILES DE CARTES D'OUTILS : le format « outils à sauvegarder ». Captures des sites, étiquetées, par piles de 3 sur la
vidéo floutée et assombrie ; une nouvelle pile sur chaque temps fort de la musique (ou à intervalle régulier).

  python tools_stack.py capture <job> <slug>     # captures des sites (Chrome sans fenêtre, en local) -> assets/outils/
  build_composition.py <job> <slug>              # pose les piles si work/<slug>_outils.json existe

work/<slug>_outils.json :
  {"word": "Claude", "occurrence": 1, "dur": 8.0, "par_pile": 3,
   "outils": [{"nom": "Rive", "url": "https://rive.app", "logo": "rive"},
              {"nom": "HyperFrames", "url": "https://hyperframes.dev", "image": "inbox/hf.png"}]}
Apparition calée sur le mot dit (jamais un timecode) ; "until" (mot de fin) à la place de "dur" possible.
Capture : le haut de la page d'accueil (1280 × 640, sans le bas où s'affichent les bandeaux cookies) ; "image" pour
fournir sa propre capture (meilleure : page produit, démo). Logos : "logo" = nom Simple Icons (voir logos-outils), sinon
le nom seul. Usage informatif : jamais présenté comme un partenariat.
"""
import argparse
import hashlib
import html
import shutil
import subprocess
import tempfile
from pathlib import Path

from common import fail, job_dir, out, read_json, word_hit

esc = lambda s: html.escape(str(s), quote=True)
CHROME = [Path(r"C:/Program Files/Google/Chrome/Application/chrome.exe"), Path(r"C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"),
          Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"), Path("/usr/bin/google-chrome"), Path("/usr/bin/chromium")]


def capture(job, url, w=1280, h=640):
    """Capture du haut d'une page -> assets/outils/<hash>.png (profil Chrome temporaire, rien n'est gardé)."""
    d = job / "assets" / "outils"
    d.mkdir(parents=True, exist_ok=True)
    dst = d / (hashlib.md5(url.encode()).hexdigest()[:10] + ".png")
    if dst.exists():
        return dst
    exe = next((c for c in CHROME if c.exists()), None)
    if not exe:
        fail("Chrome ou Edge introuvable : fournis des captures (champ \"image\")")
    prof = Path(tempfile.mkdtemp(prefix="vm-capture-"))
    full = prof / "full.png"
    try:  # page qui charge sans fin (vidéos, flux) : on coupe à 40 s ; --timeout fait prendre la capture avant
        subprocess.run([str(exe), "--headless=new", "--disable-gpu", "--hide-scrollbars", "--mute-audio", f"--user-data-dir={prof}",
                        "--no-first-run", f"--window-size={w},{h + 420}", f"--screenshot={full}", "--timeout=12000",
                        "--virtual-time-budget=6000", url], capture_output=True, timeout=40)
    except subprocess.TimeoutExpired:
        pass
    ok = full.exists() and full.stat().st_size > 5000
    if ok:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(full), "-vf", f"crop={w}:{h}:0:0", str(dst)], check=True)
        ok = not empty_page(dst)
        if not ok:  # page de chargement, vérification anti-robots, page vide : pas de capture (jamais de contournement)
            dst.unlink(missing_ok=True)
    shutil.rmtree(prof, ignore_errors=True)
    return dst if ok else None


def empty_page(png):
    """Capture inutilisable : presque tout l'image d'une seule couleur (écran de chargement, « vérification de sécurité »)."""
    import cv2
    import numpy as np
    img = cv2.imread(str(png))
    if img is None:
        return True
    q = (cv2.resize(img, (160, 80)) // 24).reshape(-1, 3)
    _, counts = np.unique(q, axis=0, return_counts=True)
    return counts.max() / len(q) > 0.82


def capture_all(job, slug):
    spec = read_json(job / "work" / f"{slug}_outils.json")
    done, failed = [], []
    for o in spec.get("outils", []):
        if o.get("image"):
            done.append(o["nom"])
            continue
        if not o.get("url"):
            failed.append(o.get("nom", "?"))
            continue
        (done if capture(job, o["url"]) else failed).append(o["nom"])
    out(ok=True, captures=done, echecs=failed, dossier=str(job / "assets" / "outils"),
        suite="regarde les captures (bandeau, page vide ?) ; remplace une mauvaise par \"image\"")


def image_of(job, o):
    if o.get("image"):
        src = Path(o["image"])
        for base in (job, job / "inbox"):
            if (base / src).exists():
                src = base / src
                break
        if src.exists():
            d = job / "assets" / "outils"
            d.mkdir(parents=True, exist_ok=True)
            if src.resolve() != (d / src.name).resolve():
                shutil.copy2(src, d / src.name)
            return f"assets/outils/{src.name}"
    if o.get("url"):
        p = capture(job, o["url"])
        if p:
            return f"assets/outils/{p.name}"
    return None


def stack_nodes(job, slug, words, dur, W, H, T0, beats=None, logo_fn=None):
    """-> (html, js, rapport) ; temps du contenu (T0 ajouté aux data-start)."""
    sj = job / "work" / f"{slug}_outils.json"
    if not sj.exists():
        return [], [], None
    spec = read_json(sj)
    tools = [o for o in spec.get("outils", []) if o.get("nom")]
    if not tools:
        return [], [], None
    hit = word_hit(words, spec["word"], spec.get("occurrence", 1)) if spec.get("word") else None
    t0 = max(0.0, (hit["start"] - 0.1) if hit else 0.3)
    end_w = word_hit(words, spec["until"], 1, lo=t0) if spec.get("until") else None
    t1 = min(dur - 0.1, end_w["end"] + 0.2 if end_w else t0 + float(spec.get("dur", 2.6 * ((len(tools) + 2) // 3))))
    per = max(1, int(spec.get("par_pile", 3)))
    piles = [tools[i:i + per] for i in range(0, len(tools), per)]
    span = t1 - t0
    if span < 1.2 * len(piles):
        return [], [], {"pose": False, "raison": "trop court pour le nombre de piles"}
    # changements de pile : réguliers, recalés sur un temps de la musique s'il y en a un tout près
    cuts = [t0 + span * k / len(piles) for k in range(len(piles))] + [t1]
    if beats:
        from common import snap_beat
        cuts = [cuts[0]] + [snap_beat(c, beats, tol=0.3, lo=cuts[k] + 1.2) for k, c in enumerate(cuts[1:-1])] + [t1]
    zone = H * 0.72 if H > W else H * 0.78  # la pile laisse le bas libre : les sous-titres y descendent pendant ce temps
    cw = round(W * 0.8) if H > W else round(H * 0.95)
    ch = round(min(cw * 0.46, (zone - H * 0.04 - H * 0.015 * (per - 1)) / per))
    gap = round(H * 0.015)
    nodes = [f'      <div class="clip tsbg" id="tsbg" data-start="{round(T0 + t0, 3)}" data-duration="{round(span, 3)}" data-track-index="44"></div>']
    js = [f'  tl.fromTo("#tsbg", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.3, ease: "power2.out", immediateRender: false }}, {round(t0, 3)});',
          f'  tl.to("#tsbg", {{ opacity: 0, duration: 0.25 }}, {round(t1 - 0.25, 3)});']
    rep = []
    for k, pile in enumerate(piles):
        a, b = cuts[k], cuts[k + 1]
        cards = []
        for j, o in enumerate(pile):
            img = image_of(job, o)
            lg = logo_fn(o["logo"]) if (logo_fn and o.get("logo")) else ""
            body = (f'<img src="{esc(img)}" alt="">' if img else
                    f'<div class="tsph">{lg}<b>{esc(o["nom"])}</b></div>')  # pas de capture : carte logo + nom
            cards.append(f'<div class="tsc c{j}"><div class="tsl">{lg}<span>{esc(o["nom"])}</span></div>{body}</div>')
            rep.append({"outil": o["nom"], "pile": k + 1, "capture": bool(img)})
        top = round(H * 0.04 + (zone - H * 0.04 - (ch * len(pile) + gap * (len(pile) - 1))) / 2)
        nodes.append(f'      <div class="clip tsp" id="tsp{k}" data-start="{round(T0 + a, 3)}" data-duration="{round(b - a, 3)}" '
                     f'data-track-index="{45 + k % 2}" style="top:{top}px">' + "".join(cards) + '</div>')
        js.append(f'  tl.fromTo("#tsp{k} .tsc", {{ opacity: 0, y: 70, scale: 0.92 }}, {{ opacity: 1, y: 0, scale: 1, duration: 0.38, stagger: 0.07, '
                  f'ease: "back.out(1.5)", immediateRender: false }}, {round(a, 3)});')
        if b < t1 - 0.05:
            js.append(f'  tl.to("#tsp{k} .tsc", {{ opacity: 0, y: -50, duration: 0.2, stagger: 0.03, ease: "power2.in" }}, {round(b - 0.22, 3)});')
    css = (f"  .tsbg {{ position: absolute; inset: 0; z-index: 44; backdrop-filter: blur(22px) brightness(.42); -webkit-backdrop-filter: blur(22px) brightness(.42);"
           f" background: rgba(0,0,0,.25); }}\n"
           f"  .tsp {{ position: absolute; left: {(W - cw) // 2}px; width: {cw}px; z-index: 46; display: flex; flex-direction: column; gap: {gap}px; }}\n"
           f"  .tsc {{ position: relative; height: {ch}px; border-radius: {round(W * 0.022)}px; overflow: hidden; background: #111;"
           f" box-shadow: 0 {round(H * 0.012)}px {round(H * 0.03)}px rgba(0,0,0,.55); border: 2px solid rgba(255,255,255,.12); }}\n"
           f"  .tsc img {{ width: 100%; height: 100%; object-fit: cover; object-position: top center; display: block; }}\n"
           f"  .tsl {{ position: absolute; left: {round(W * 0.018)}px; top: {round(W * 0.018)}px; z-index: 2; display: flex; align-items: center;"
           f" gap: .35em; padding: .3em .7em; border-radius: .5em; background: rgba(12,12,14,.82); color: #fff;"
           f" font: 700 {round(W * 0.03)}px 'Inter', sans-serif; }}\n"
           f"  .tsl svg {{ width: 1em; height: 1em; }}\n"
           f"  .tsph {{ display: flex; align-items: center; justify-content: center; gap: .4em; height: 100%; color: #fff; font: 800 {round(W * 0.06)}px 'Inter', sans-serif;"
           f" background: radial-gradient(circle at 30% 30%, #2a2a33, #0d0d10); }}" + chr(10) +
           f"  .tsph svg {{ width: 1.1em; height: 1.1em; }}")
    return nodes, js, {"pose": True, "t0": round(t0, 3), "t1": round(t1, 3), "bas_libre": round(zone / H, 3), "a": round(t0, 2), "duree": round(span, 2), "piles": len(piles), "outils": rep, "css": css}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["capture"])
    ap.add_argument("job")
    ap.add_argument("slug")
    a = ap.parse_args()
    capture_all(job_dir(a.job), a.slug)


if __name__ == "__main__":
    main()

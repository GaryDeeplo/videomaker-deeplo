"""COUVERTURES AVEC TITRE (vignettes Reels / TikTok / YouTube) -> renders/covers/

  python covers.py <job> <slug> [--title "…" --title "…"] [--sizes 9:16,1:1,16:9]
  python covers.py pick <job> <slug> <a|b|c>          # la couverture choisie part dans la livraison

1. Images : dans la vidéo dérushée, l'outil cherche les meilleurs plans du visage (YuNet, local : grand visage, net,
   bien détecté), 3 moments espacés d'au moins 2 s. Vidéo sans rush : les photos des scènes accroche / photo.
2. Titres : --title (2 ou 3, ≤ 6 mots, la promesse dite dans la vidéo, jamais une promesse inventée), sinon
   work/<slug>_cover.json {"titles": [...]}, sinon l'accroche du short (work/<slug>_hook.json).
3. Trois maquettes aux couleurs et à la police de la charte : a « bandeau » (titre dans des pavés couleur d'accent),
   b « impact » (gros titre contour noir en haut, mot fort en couleur), c « côté » (dégradé sombre, titre aligné à
   gauche ; en 16:9 la personne passe à droite). Une planche renders/covers/planche.jpg pour choisir.
"""
import argparse
import html
import json
import shutil
import subprocess
import sys
from pathlib import Path

from common import ROOT, config, fail, job_dir, out, probe, read_json, size_of, write_json

MODEL = ROOT / ".claude" / "skills" / "videomaker-deeplo" / "vendor" / "yunet" / "face_detection_yunet_2023mar.onnx"
NPX = ["cmd", "/c", "npx"] if sys.platform == "win32" else ["npx"]
VARIANTS = ["bandeau", "impact", "cote"]


def esc(s):
    return html.escape(s, quote=True)


def best_frames(src, n=3, gap=2.0):
    """Meilleurs plans du visage : surface × confiance × netteté, moments espacés d'au moins `gap` secondes."""
    import cv2
    cap = cv2.VideoCapture(str(src))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    sw, sh = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    k = 640 / max(sw, sh)
    dw, dh = int(sw * k), int(sh * k)
    det = cv2.FaceDetectorYN.create(str(MODEL), "", (dw, dh), 0.75, 0.3, 20)
    step, cands = max(1, round(fps / 2)), []
    for f in range(total):
        if f % step:
            if not cap.grab():
                break
            continue
        ok, img = cap.read()
        if not ok:
            break
        if f / fps < 0.5:  # pas la toute première image (souvent bouche ouverte, flou de départ)
            continue
        small = cv2.resize(img, (dw, dh))
        _, faces = det.detect(small)
        if faces is None or not len(faces):
            continue
        fc = max(faces, key=lambda x: x[2] * x[3])
        x, y, w, h = [int(v) for v in fc[:4]]
        crop = cv2.cvtColor(small[max(0, y):y + h, max(0, x):x + w], cv2.COLOR_BGR2GRAY)
        sharp = cv2.Laplacian(crop, cv2.CV_64F).var() if crop.size else 0
        area = (w * h) / (dw * dh)
        cands.append({"t": round(f / fps, 2), "score": area * float(fc[14]) * min(1.0, sharp / 150),
                      "cx": (x + w / 2) / dw, "cy": (y + h / 2) / dh})
    cap.release()
    cands.sort(key=lambda c: -c["score"])
    pick = []
    for c in cands:
        if all(abs(c["t"] - p["t"]) >= gap for p in pick):
            pick.append(c)
        if len(pick) == n:
            break
    return pick, (sw, sh)


def fonts_css(job, vis, dst):
    """Polices de la charte copiées à côté de la page de couverture (fonts.py)."""
    from fonts import brand_faces
    return brand_faces(job, vis, dst=dst, url="")


def title_html(title, accent_last=True):
    ws = title.split()
    return " ".join(f'<span class="k">{esc(w)}</span>' if (accent_last and i == len(ws) - 1) else esc(w)
                    for i, w in enumerate(ws))


def page(W, H, items, vis, font_css):
    """Une composition de 3 s : une maquette par seconde (snapshot à 0,5 / 1,5 / 2,5)."""
    fam, accent = vis["fontFamily"], vis["accentColor"]
    rgb = [int(accent.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)] if len(accent.lstrip("#")) == 6 else [0, 0, 0]
    on_acc = "#111111" if (0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]) > 160 else "#ffffff"
    wide = W / H > 1.2
    u = min(W, H) / 1080
    blocks = []
    for i, it in enumerate(items):
        v, img, title = it["variant"], it["img"], it["title"]
        iw, ih = it["img_size"]
        same = (W / H) / (iw / ih) <= 1.85  # carré tiré d'un 9:16 : on recadre sur le visage ; 16:9 tiré d'un 9:16 : fond flouté
        fx, fy = round(it["cx"] * 100), round(it["cy"] * 100)
        if same:  # même sens que le format : plein cadre, centré sur le visage
            fy_ = max(0, fy - 30) if v == "impact" else max(20, fy - 10)  # impact : titre en haut, le visage descend
            bg = f'<img class="full" src="{img}" style="object-position: {fx}% {fy_}%">'
        else:  # sens différent : fond flouté + image entière (à droite en paysage pour la maquette côté)
            side = "right" if (wide and v == "cote") else "center"
            bg = (f'<img class="blur" src="{img}"><img class="fit fit-{side}" src="{img}">')
        if v == "bandeau":
            lines = title.upper().split()
            mid = (len(lines) + 1) // 2
            txt = (f'<div class="t-band"><span>{esc(" ".join(lines[:mid]))}</span>'
                   + (f'<span>{esc(" ".join(lines[mid:]))}</span>' if lines[mid:] else "") + "</div>")
        elif v == "impact":
            txt = f'<div class="t-impact">{title_html(title.upper())}</div>'
        else:
            txt = f'<div class="shade-side"></div><div class="t-side">{title_html(title)}</div>'
        blocks.append(f'<div class="clip v v-{v}" id="v{i}" data-start="{i}" data-duration="1" data-track-index="{i}">{bg}{txt}</div>')
    side_w = round(W * (0.5 if wide else 0.84))
    return f"""<!doctype html>
<html lang="fr"><head><meta charset="UTF-8"><meta name="viewport" content="width={W}, height={H}">
<script src="https://cdn.jsdelivr.net/npm/gsap@3.15.0/dist/gsap.min.js"></script>
<style>
{font_css}
html, body {{ margin: 0; width: {W}px; height: {H}px; overflow: hidden; background: #000; }}
#root {{ position: relative; width: {W}px; height: {H}px; overflow: hidden; }}
.v {{ position: absolute; inset: 0; overflow: hidden; font-family: '{fam}', 'Inter', sans-serif; }}
.full, .blur {{ position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }}
.blur {{ filter: blur(40px) brightness(.55); transform: scale(1.15); }}
.fit {{ position: absolute; top: 0; height: 100%; width: auto; max-width: 100%; object-fit: contain; }}
.fit-center {{ left: 50%; transform: translateX(-50%); }}
.fit-right {{ right: 0; }}
.k {{ color: {accent}; }}
.t-band {{ position: absolute; left: {round(60*u)}px; right: {round(60*u)}px; bottom: {round(H*0.14)}px; display: flex;
          flex-direction: column; align-items: flex-start; gap: {round(14*u)}px; transform: rotate(-2deg); }}
.t-band span {{ background: {accent}; color: {on_acc}; font-weight: 900; font-size: {round((96 if not wide else 84)*u)}px;
               line-height: 1.05; padding: .08em .3em .12em; border-radius: .12em; box-shadow: 0 .12em .4em rgba(0,0,0,.35); }}
.t-impact {{ position: absolute; left: {round(50*u)}px; right: {round(50*u)}px; top: {round(H*0.07)}px; text-align: center;
            color: #fff; font-weight: 900; font-size: {round((130 if not wide else 110)*u)}px; line-height: .98; text-wrap: balance;
            -webkit-text-stroke: .08em #000; paint-order: stroke fill; text-shadow: 0 .06em 0 #000, 0 .2em .5em rgba(0,0,0,.5); }}
.v-impact::before {{ content: ""; position: absolute; inset: 0 0 55% 0; background: linear-gradient(rgba(0,0,0,.55), rgba(0,0,0,0)); }}
.shade-side {{ position: absolute; inset: 0; background: {"linear-gradient(90deg, rgba(0,0,0,.85) 0%, rgba(0,0,0,.55) 45%, rgba(0,0,0,0) 70%)" if wide
               else "linear-gradient(180deg, rgba(0,0,0,.8) 0%, rgba(0,0,0,.35) 40%, rgba(0,0,0,0) 60%)"}; }}
.t-side {{ position: absolute; left: {round(70*u)}px; width: {side_w}px; {"top: 50%; transform: translateY(-50%);" if wide else f"top: {round(H*0.08)}px;"}
          color: #fff; font-weight: 800; font-size: {round((112 if not wide else 96)*u)}px; line-height: 1.02; text-wrap: balance; }}
</style></head><body>
<div id="root" data-composition-id="covers" data-start="0" data-width="{W}" data-height="{H}" data-duration="{len(items)}">
{chr(10).join(blocks)}
</div>
<script>
  window.__timelines = window.__timelines || {{}};
  const tl = gsap.timeline({{ paused: true }});
  tl.set({{}}, {{}}, {len(items)});
  window.__timelines["covers"] = tl;
</script></body></html>"""


def make(a):
    job = job_dir(a.job)
    c = config(job)
    vis = c["visual"]
    titles = a.title or []
    cj = job / "work" / f"{a.slug}_cover.json"
    if not titles and cj.exists():
        titles = read_json(cj).get("titles", [])
    if not titles and (job / "work" / f"{a.slug}_hook.json").exists():
        titles = [read_json(job / "work" / f"{a.slug}_hook.json")["text"]]
    if not titles:
        fail("pas de titre : --title \"…\" (2 ou 3 variantes, ≤ 6 mots, la promesse dite dans la vidéo)")
    out_dir = job / "renders" / "covers"
    out_dir.mkdir(parents=True, exist_ok=True)
    work = job / "work" / "covers"
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)

    frames = []
    mj = job / "work" / f"{a.slug}_map.json"
    if mj.exists():  # rush : meilleurs plans du visage dans la vidéo dérushée (sans sous-titres ni habillage)
        src = Path(read_json(mj)["cut"])
        picks, (sw, sh) = best_frames(src)
        for i, p in enumerate(picks):
            f = work / f"frame{i}.jpg"
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", str(p["t"]), "-i", str(src), "-frames:v", "1",
                            "-q:v", "2", str(f)], check=True)
            frames.append({"file": f, "size": (sw, sh), "cx": p["cx"], "cy": p["cy"], "t": p["t"]})
    sbj = job / "work" / f"{a.slug}_storyboard.json"
    if not frames and sbj.exists():  # sans rush : images des scènes accroche / photo
        for sc in read_json(sbj)["scenes"]:
            im = sc.get("image")
            if im and sc["kind"] in ("hook", "photo", "product") and not str(im).lower().endswith((".mp4", ".webm", ".mov")):
                for base in (job / "inbox", job, ROOT):
                    if (base / im).exists():
                        pi = probe(base / im)
                        frames.append({"file": base / im, "size": (pi.get("width") or 1080, pi.get("height") or 1920),
                                       "cx": 0.5, "cy": 0.45, "t": None})
                        break
    if not frames:
        fail("aucune image utilisable (pas de visage détecté, pas de photo de scène)")

    made = {}
    for size in a.sizes.split(","):
        W, H = size_of(size, vis)
        d = work / f"{W}x{H}"
        d.mkdir()
        items = []
        for i, v in enumerate(VARIANTS):
            fr = frames[i % len(frames)]
            shutil.copy2(fr["file"], d / f"img{i}{Path(fr['file']).suffix}")
            items.append({"variant": v, "img": f"img{i}{Path(fr['file']).suffix}", "img_size": fr["size"],
                          "cx": fr["cx"], "cy": fr["cy"], "title": titles[i % len(titles)]})
        (d / "index.html").write_text(page(W, H, items, vis, fonts_css(job, vis, d)), encoding="utf-8")
        shutil.copy2(job / "hyperframes.json", d / "hyperframes.json")
        snap = d / "snap"
        subprocess.run(NPX + ["--yes", "hyperframes@0.9.71", "snapshot", "--at", "0.5,1.5,2.5", "--no-end", "-o", str(snap)],
                       cwd=d, capture_output=True, text=True, encoding="utf-8", errors="replace")
        pngs = sorted(snap.glob("frame-*.png"))
        if len(pngs) < 3:
            fail(f"snapshot incomplet pour {size}", dossier=str(d))
        for i, v in enumerate(VARIANTS):
            dst = out_dir / f"{a.slug}_{'abc'[i]}-{v}_{W}x{H}.jpg"
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(pngs[i]), "-q:v", "2", str(dst)], check=True)
            made.setdefault("abc"[i], []).append(dst.name)
    pl = planche(out_dir, a.slug)
    write_json(cj, {"titles": titles, "variants": {k: v for k, v in made.items()},
                    "frames": [fr["t"] for fr in frames], "choice": read_json(cj).get("choice") if cj.exists() else None})
    out(ok=True, couvertures=made, planche=str(pl), titres=titles,
        suite="montre la planche ; le choix : covers.py pick <job> <slug> a|b|c (deliver.py l'utilise)")


def planche(out_dir, slug):
    from PIL import Image, ImageDraw, ImageFont
    files = sorted(out_dir.glob(f"{slug}_*_*.jpg"))
    rows = {}
    for f in files:
        size = f.stem.rsplit("_", 1)[1]
        rows.setdefault(size, []).append(f)
    TH, PAD = 420, 16
    try:
        font = ImageFont.truetype("arialbd.ttf", 30)
    except OSError:
        font = ImageFont.load_default()
    ims = []
    for size, fs in rows.items():
        row = [Image.open(f).convert("RGB") for f in sorted(fs)]
        row = [im.resize((round(im.width * TH / im.height), TH)) for im in row]
        ims.append((size, row, [f.stem.split("_")[-2] for f in sorted(fs)]))
    Wt = max(sum(im.width + PAD for im in r) for _, r, _ in ims) + PAD + 200
    canvas = Image.new("RGB", (Wt, len(ims) * (TH + PAD + 40) + PAD), "#16181d")
    dr = ImageDraw.Draw(canvas)
    y = PAD
    for size, row, names in ims:
        x = PAD
        for im, nm in zip(row, names):
            canvas.paste(im, (x, y + 40))
            dr.text((x, y + 4), nm.split("-")[0], fill="#FFD60A", font=font)
            x += im.width + PAD
        dr.text((x + 10, y + 40 + TH // 2), size, fill="#888888", font=font)
        y += TH + PAD + 40
    dst = out_dir / "planche.jpg"
    canvas.save(dst, quality=88)
    return dst


def pick(a):
    job = job_dir(a.job)
    cj = job / "work" / f"{a.slug}_cover.json"
    if not cj.exists():
        fail("lance d'abord covers.py <job> <slug>")
    d = read_json(cj)
    if a.choice not in d.get("variants", {}):
        fail(f"choix inconnu : {a.choice}", choix=list(d.get("variants", {})))
    d["choice"] = a.choice
    write_json(cj, d)
    out(ok=True, choix=a.choice, fichiers=d["variants"][a.choice], suite="deliver.py utilisera cette couverture")


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "pick":
        ap = argparse.ArgumentParser()
        ap.add_argument("cmd")
        ap.add_argument("job")
        ap.add_argument("slug")
        ap.add_argument("choice")
        return pick(ap.parse_args())
    ap = argparse.ArgumentParser()
    ap.add_argument("job")
    ap.add_argument("slug")
    ap.add_argument("--title", action="append", help="titre (répéter pour 2 ou 3 variantes)")
    ap.add_argument("--sizes", default="9:16,1:1,16:9")
    make(ap.parse_args())


if __name__ == "__main__":
    main()

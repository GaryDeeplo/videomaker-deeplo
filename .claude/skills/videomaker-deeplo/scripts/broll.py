"""PLANS DE COUPE (b-roll) posés sur ce qui est DIT -> work/<slug>_broll.json

  python broll.py moments <job> <slug> [--every 7]          # moments candidats + photos/vidéos de l'inbox
  python broll.py search  <job> "<requête en anglais>" [--n 8] [--orient tall|wide|square] [--video] [--source pixabay|pexels|openverse]
  python broll.py get     <job> <id>                        # télécharge, réduit, note le crédit
  python broll.py auto    <job> <slug> [--kind mix|photo|video] [--max 6]   # EN UN CLIC : moments -> recherche ->
                                                            # 1er choix téléchargé -> broll.json + planche à regarder
  python broll.py pick    <job> <slug> <n> <a-f|none|id>    # remplace (ou retire) le plan n par une autre proposition

auto : reprend work/<slug>_broll_suggested.json s'il existe (requêtes "query" et images déjà choisies par Claude,
moments retirés), sinon trouve les moments lui-même et tire la requête des mots de la phrase (moins précis : mieux vaut
que Claude écrive "query" : 1 à 2 mots anglais, concrets et filmables, « delivery van » plutôt qu'une phrase). Une planche work/broll/planche.jpg montre pour chaque
moment la phrase et jusqu'à 6 propositions (vidéos puis photos, a = posée) : Claude la REGARDE et corrige avec pick avant de monter.

Ordre des sources : 1) les photos / vidéos du client (inbox/) ; 2) Pixabay (photos et vidéos, licence Pixabay : usage
commercial libre, sans attribution obligatoire ; clé PIXABAY_API_KEY dans .env) ou Pexels (PEXELS_API_KEY, même
principe ; nouvelles clés suspendues en 2026) ; 3) Openverse (CC0, CC BY, domaine public, souvent amateur) sans clé.
Crédits livrés dans tous les cas. Claude regarde les miniatures (search) avant de choisir : une image qui ne colle pas au
propos ou qui montre une autre marque ne passe pas. Jamais d'image présentée comme celle du client si elle n'en est pas.

work/<slug>_broll.json : [{"word": "boutique", "occurrence": 1, "until": "clients", "image": "inbox/vitrine.jpg",
  "mode": "full" | "carte", "query": "…"}]   — calé sur un mot dit (jamais un timecode), "until" (mot de fin, facultatif)
  ou "dur" (s, défaut 2,5). build_composition.py les pose sur le rush, sous les sous-titres.
"""
import argparse
import json
import re
import subprocess
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from common import _norm_word, env_key, fail, job_dir, out, read_json, write_json

API = "https://api.openverse.org/v1/images/"
PEXELS = "https://api.pexels.com/"
PIXABAY = "https://pixabay.com/api/"
PB_ORIENT = {"tall": "vertical", "wide": "horizontal"}
ORIENT = {"tall": "portrait", "wide": "landscape", "square": "square"}
UA = {"User-Agent": "deeplo-video-maker/1.0 (b-roll)"}
MEDIA = (".jpg", ".jpeg", ".png", ".webp", ".mp4", ".mov", ".webm")


def fetch(url, dst):
    tmp = dst.with_suffix(dst.suffix + ".part")
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90) as r, open(tmp, "wb") as f:
        f.write(r.read())
    if tmp.stat().st_size < 2000:
        tmp.unlink()
        raise OSError("fichier vide")
    tmp.replace(dst)


def api(path, qs=None):
    url = API + path + ("?" + urllib.parse.urlencode(qs) if qs else "")
    for k in range(4):  # Openverse renvoie parfois 502/504 : on réessaie
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40) as r:
                return json.load(r)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
            if k == 3 or (isinstance(e, urllib.error.HTTPError) and e.code < 500):
                fail(f"Openverse indisponible ({e}) : réessaie plus tard ou utilise les photos du client")
            time.sleep(2 + 3 * k)


def pexels(path, qs=None):
    key = env_key("PEXELS_API_KEY")
    if not key:
        fail("PEXELS_API_KEY vide dans .env (clé gratuite sur pexels.com/api) ; ou --source openverse")
    url = PEXELS + path + ("?" + urllib.parse.urlencode(qs) if qs else "")
    req = urllib.request.Request(url, headers={**UA, "Authorization": key})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        fail(f"Pexels HTTP {e.code}" + (" : clé refusée" if e.code in (401, 403) else ""))


def pixabay(path, qs):
    key = env_key("PIXABAY_API_KEY")
    if not key:
        fail("PIXABAY_API_KEY vide dans .env (clé gratuite sur pixabay.com/api/docs) ; ou --source openverse")
    url = PIXABAY + path + "?" + urllib.parse.urlencode({"key": key, **qs})
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        fail(f"Pixabay HTTP {e.code}" + (" : clé refusée" if e.code in (400, 401, 403) else ""))


def search_pixabay(a, d):
    qs = {"q": a.query[:100], "per_page": str(max(3, a.n)), "safesearch": "true"}
    if getattr(a, "lang", None):
        qs["lang"] = a.lang
    if a.video:
        hits = pixabay("videos/", qs).get("hits", [])
        res = [{"id": f"pbv-{h['id']}", "thumb": (h["videos"].get("medium") or h["videos"]["small"]).get("thumbnail"),
                "titre": h.get("tags", "")[:80], "licence": "pixabay", "duree": h.get("duration"),
                "taille": f"{h['videos']['large'].get('width')}x{h['videos']['large'].get('height')}" if h["videos"].get("large", {}).get("url")
                else f"{h['videos']['medium'].get('width')}x{h['videos']['medium'].get('height')}", "source": "pixabay (vidéo)"}
               for h in hits]
        if a.orient == "tall":  # l'API vidéo ne filtre pas le sens : on met les vidéos verticales devant
            res.sort(key=lambda x: -int(x["taille"].split("x")[1]) / max(1, int(x["taille"].split("x")[0])))
    else:
        if a.orient in PB_ORIENT:
            qs["orientation"] = PB_ORIENT[a.orient]
        hits = pixabay("", {**qs, "image_type": "photo"}).get("hits", [])
        res = [{"id": f"pb-{h['id']}", "thumb": h["webformatURL"], "titre": h.get("tags", "")[:80], "licence": "pixabay",
                "taille": f"{h.get('imageWidth')}x{h.get('imageHeight')}", "source": "pixabay"} for h in hits]
    rows = []
    for i, x in enumerate(res[:a.n], 1):
        th = d / f"{i:02d}.jpg"
        try:
            fetch(x.pop("thumb"), th)
        except (OSError, TypeError):
            continue
        rows.append({"n": i, **x, "miniature": str(th)})
    return rows


def get_pixabay(a, job, dst_dir):
    if a.id.startswith("pbv-"):
        h = pixabay("videos/", {"id": a.id[4:]})["hits"][0]
        f = next(h["videos"][q] for q in ("large", "medium", "small") if h["videos"].get(q, {}).get("url"))
        dst = dst_dir / f"{a.id}.mp4"
        with tempfile.TemporaryDirectory() as tmp:
            raw = Path(tmp) / "raw.mp4"
            fetch(f["url"], raw)
            to_mp4(raw, dst)
        line = f"Vidéo par {h.get('user') or 'auteur inconnu'} sur Pixabay — {h.get('pageURL', '')}"
    else:
        h = pixabay("", {"id": a.id[3:]})["hits"][0]
        dst = dst_dir / f"{a.id}.jpg"
        with tempfile.TemporaryDirectory() as tmp:
            raw = Path(tmp) / "raw.jpg"
            fetch(h.get("largeImageURL") or h["webformatURL"], raw)
            shrink(raw, dst)
        line = f"Photo par {h.get('user') or 'auteur inconnu'} sur Pixabay — {h.get('pageURL', '')}"
    rel = f"assets/broll/{dst.name}"
    save_credit(job, rel, line)
    return rel, line


def to_mp4(raw, dst):
    """Vidéo de coupe : 10 s max, sans son, 1080p max, h264 (léger et lisible partout)."""
    r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(raw), "-t", "10", "-an", "-vf",
                        "scale='min(1920,iw)':'min(1920,ih)':force_original_aspect_ratio=decrease:force_divisible_by=2",
                        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", str(dst)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        fail("conversion de la vidéo impossible", detail=r.stderr[-300:])


def best_file(v, portrait):
    """Fichier vidéo Pexels le plus proche du 1080p dans le bon sens, en mp4."""
    fs = [f for f in v.get("video_files", []) if f.get("file_type") == "video/mp4" and f.get("width")]
    side = (lambda f: f["width"]) if portrait else (lambda f: f["height"])
    ok = [f for f in fs if side(f) >= 1080]
    return min(ok, key=side) if ok else max(fs, key=side)


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:40] or "x"


def credit_of(x):
    lic = "CC0" if x["license"] == "cc0" else "domaine public" if x["license"] == "pdm" else f"CC {x['license'].upper()} {x.get('license_version', '')}".strip()
    return f"Image « {x.get('title') or 'sans titre'} » par {x.get('creator') or 'auteur inconnu'} ({lic}) — {x.get('foreign_landing_url', '')}"


def search_pexels(a, d):
    qs = {"query": a.query, "per_page": str(a.n)}
    if a.orient:
        qs["orientation"] = ORIENT[a.orient]
    if a.video:
        items = pexels("videos/search", qs).get("videos", [])
        res = [{"id": f"pxv-{v['id']}", "thumb": v.get("image"), "titre": Path(urllib.parse.urlparse(v.get("url", "")).path).name[:80],
                "licence": "pexels", "taille": f"{v.get('width')}x{v.get('height')}", "duree": v.get("duration"),
                "source": "pexels (vidéo)"} for v in items]
    else:
        items = pexels("v1/search", qs).get("photos", [])
        res = [{"id": f"px-{p['id']}", "thumb": p["src"]["medium"], "titre": (p.get("alt") or "")[:80], "licence": "pexels",
                "taille": f"{p.get('width')}x{p.get('height')}", "source": "pexels"} for p in items]
    rows = []
    for i, x in enumerate(res, 1):
        th = d / f"{i:02d}.jpg"
        try:
            fetch(x.pop("thumb"), th)
        except OSError:
            continue
        rows.append({"n": i, **x, "miniature": str(th)})
    return rows


def cmd_search(a):
    job = job_dir(a.job)
    src = a.source or ("pixabay" if env_key("PIXABAY_API_KEY") else "pexels" if env_key("PEXELS_API_KEY") else "openverse")
    if a.video and src == "openverse":
        fail("vidéos de coupe : Pixabay ou Pexels (clé dans .env)")
    if src in ("pixabay", "pexels"):
        d = job / "work" / "broll" / "candidats" / (src + "-" + slugify(a.query) + ("-video" if a.video else ""))
        d.mkdir(parents=True, exist_ok=True)
        rows = (search_pixabay if src == "pixabay" else search_pexels)(a, d)
        write_json(d / "candidats.json", rows)
        out(ok=True, source=src, requete=a.query, candidats=rows, suite="regarde les miniatures, puis : broll.py get <job> <id>")
        return
    qs = {"q": a.query, "license": "cc0,by,pdm", "page_size": str(max(a.n * 2, 10)), "mature": "false"}
    if a.orient:
        qs["aspect_ratio"] = a.orient
    res = [x for x in api("", qs).get("results", []) if (x.get("width") or 0) >= 900][:a.n]
    d = job / "work" / "broll" / "candidats" / slugify(a.query)
    d.mkdir(parents=True, exist_ok=True)
    rows = []
    for i, x in enumerate(res, 1):
        th = d / f"{i:02d}.jpg"
        try:
            fetch(x["thumbnail"], th)
        except OSError:
            continue
        rows.append({"n": i, "id": x["id"], "miniature": str(th), "titre": x.get("title", "")[:80],
                     "licence": x["license"], "taille": f"{x.get('width')}x{x.get('height')}", "source": x.get("source")})
    write_json(d / "candidats.json", rows)
    out(ok=True, requete=a.query, candidats=rows,
        suite="regarde les miniatures, puis : broll.py get <job> <id>")


def shrink(raw, dst):
    """Réduit à 2160 px max (image) : le rendu reste rapide et la netteté suffit en 1080p."""
    r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(raw), "-vf",
                        "scale='min(2160,iw)':'min(2160,ih)':force_original_aspect_ratio=decrease", "-q:v", "3",
                        str(dst)], capture_output=True, text=True)
    if r.returncode != 0:
        fail("conversion de l'image impossible", detail=r.stderr[-300:])


def save_credit(job, rel, line):
    cj = job / "work" / "broll_credits.json"
    cr = read_json(cj) if cj.exists() else {}
    cr[rel] = line
    write_json(cj, cr)


def get_pexels(a, job, dst_dir):
    if a.id.startswith("pxv-"):  # vidéo : 10 s max, sans son, 1080p, h264 (léger et lisible partout)
        v = pexels(f"videos/videos/{a.id[4:]}")
        f = best_file(v, (v.get("height") or 0) >= (v.get("width") or 1))
        dst = dst_dir / f"{a.id}.mp4"
        with tempfile.TemporaryDirectory() as tmp:
            raw = Path(tmp) / "raw.mp4"
            fetch(f["link"], raw)
            to_mp4(raw, dst)
        who = (v.get("user") or {}).get("name") or "auteur inconnu"
        line = f"Vidéo par {who} sur Pexels — {v.get('url', '')}"
    else:
        p = pexels(f"v1/photos/{a.id[3:]}")
        dst = dst_dir / f"{a.id}.jpg"
        with tempfile.TemporaryDirectory() as tmp:
            raw = Path(tmp) / "raw.jpg"
            fetch(p["src"].get("large2x") or p["src"]["original"], raw)
            shrink(raw, dst)
        line = f"Photo par {p.get('photographer') or 'auteur inconnu'} sur Pexels — {p.get('url', '')}"
    rel = f"assets/broll/{dst.name}"
    save_credit(job, rel, line)
    return rel, line


def download(job, a):
    dst_dir = job / "assets" / "broll"
    dst_dir.mkdir(parents=True, exist_ok=True)
    if a.id.startswith(("pb-", "pbv-")):
        return get_pixabay(a, job, dst_dir)
    if a.id.startswith(("px-", "pxv-")):
        return get_pexels(a, job, dst_dir)
    x = api(f"{a.id}/")
    dst = dst_dir / f"ov-{a.id[:8]}.jpg"
    with tempfile.TemporaryDirectory() as tmp:
        raw = Path(tmp) / ("raw" + (Path(urllib.parse.urlparse(x["url"]).path).suffix or ".jpg"))
        try:
            fetch(x["url"], raw)
        except OSError:
            fetch(x["thumbnail"], raw)  # certaines sources refusent le téléchargement direct
        shrink(raw, dst)
    rel = f"assets/broll/{dst.name}"
    save_credit(job, rel, credit_of(x))
    return rel, credit_of(x)


def cmd_get(a):
    rel, line = download(job_dir(a.job), a)
    out(ok=True, image=rel, credit=line, suite=f'dans work/<slug>_broll.json : "image": "{rel}"')


def sentences(words):
    cur = []
    for w in words:
        cur.append(w)
        if re.search(r"[.!?…]$", w["w"]):
            yield cur
            cur = []
    if cur:
        yield cur


def find_moments(job, slug, every):
    from build_text import remap
    a = argparse.Namespace(slug=slug, every=every)
    m = read_json(job / "work" / f"{a.slug}_map.json")
    words = remap(read_json(job / "work" / f"{a.slug}_words.json")["words"], m["segments"])
    dur = float(m["out_duration"])
    hook = 3.6 if (job / "work" / f"{a.slug}_hook.json").exists() else 2.0  # on montre d'abord la personne
    busy = []
    mj = job / "work" / f"{a.slug}_motions.json"
    for mo in (read_json(mj) if mj.exists() else []):  # pas de plan de coupe sous un bloc de motion
        k = _norm_word(mo.get("word", ""))
        hit = [w["start"] for w in words if _norm_word(w["w"]) == k]
        if len(hit) >= int(mo.get("occurrence", 1)):
            t = hit[int(mo.get("occurrence", 1)) - 1]
            busy.append((t - 0.5, t + float(mo.get("dur", 3)) + 0.5))
    rows, last = [], -99.0
    for s in sentences(words):
        t0, t1 = s[0]["start"], s[-1]["end"]
        if t0 < hook or t1 > dur - 1.5 or t0 - last < a.every or any(b0 < t1 and t0 < b1 for b0, b1 in busy):
            continue
        first = s[0]  # le plan démarre avec la phrase : la coupe tombe sur un temps de parole
        occ = sum(1 for w in words if w["start"] < first["start"] and _norm_word(w["w"]) == _norm_word(first["w"])) + 1
        rows.append({"word": first["w"].strip(".,!?…;:"), "occurrence": occ, "until": s[-1]["w"].strip(".,!?…;:"),
                     "phrase": " ".join(w["w"] for w in s), "a": round(first["start"], 2),
                     "duree": round(t1 - first["start"], 2), "image": "", "query": "", "mode": "full"})
        last = t0
    inbox = sorted(str(p.relative_to(job)).replace("\\", "/") for p in (job / "inbox").rglob("*")
                   if p.suffix.lower() in MEDIA and p.stat().st_size < 400e6 and "_words" not in p.name)
    return rows, inbox


def cmd_moments(a):
    job = job_dir(a.job)
    rows, inbox = find_moments(job, a.slug, a.every)
    dst = job / "work" / f"{a.slug}_broll_suggested.json"
    write_json(dst, rows)
    out(ok=True, moments=len(rows), fichier=str(dst), medias_inbox=inbox,
        suite="choisis pour chaque moment une image (inbox d'abord, sinon search/get), retire les autres, "
              f"enregistre work/{a.slug}_broll.json, puis build_composition.py")


STOP = set("""alors aussi autre avant avec avez avoir avons bien cela cette ceux chez comme dans depuis donc elle elles
encore entre être fait faire faut leur leurs lorsque mais même moins nous notre parce pendant peut plus pour pourquoi
quand quel quelle quelque sans sera sont tous tout toute toutes très vers voilà vos votre vous ainsi juste vraiment
chaque déjà ensuite enfin ici uniquement seulement mois jour jours fois chose choses euros euro""".split())


def guess_query(phrase):
    """Requête de secours tirée de la phrase (Claude écrit mieux : "query" dans le fichier suggéré)."""
    ws = [w.strip(".,!?…;:«»\"()").lower() for w in phrase.split()]
    ws = [w.split("'")[-1].split("’")[-1] for w in ws]
    keep = [w for w in ws if len(w) >= 4 and w not in STOP and not re.search(r"\d", w) and not w.endswith(("ez", "ons"))]
    return " ".join(list(dict.fromkeys(keep))[:3])


def source_name():
    return "pixabay" if env_key("PIXABAY_API_KEY") else "pexels" if env_key("PEXELS_API_KEY") else "openverse"


def candidates(job, query, video, lang, orient, n=3):
    src = source_name()
    if video and src == "openverse":
        return []
    d = job / "work" / "broll" / "candidats" / (src + "-" + slugify(query) + ("-video" if video else ""))
    d.mkdir(parents=True, exist_ok=True)
    ns = argparse.Namespace(query=query, n=n + 3, orient=orient, video=video, lang=lang)
    if src == "pixabay":
        return search_pixabay(ns, d)
    if src == "pexels":
        return search_pexels(ns, d)
    qs = {"q": query, "license": "cc0,by,pdm", "page_size": "12", "mature": "false", "aspect_ratio": orient or "tall"}
    rows = []
    for i, x in enumerate([x for x in api("", qs).get("results", []) if (x.get("width") or 0) >= 900][:n], 1):
        th = d / f"{i:02d}.jpg"
        try:
            fetch(x["thumbnail"], th)
        except OSError:
            continue
        rows.append({"n": i, "id": x["id"], "miniature": str(th), "titre": x.get("title", "")[:80], "source": "openverse"})
    return rows


def planche(job, items):
    """Planche à regarder : une ligne par plan, la phrase dite et les propositions a / b / c (a = posée)."""
    from PIL import Image, ImageDraw, ImageFont
    TH, PAD, TXT = 170, 12, 440
    try:
        font, small = ImageFont.truetype("arial.ttf", 22), ImageFont.truetype("arialbd.ttf", 26)
    except OSError:
        font = small = ImageFont.load_default()
    rows = [(n, it) for n, it in enumerate(items, 1) if it.get("_alts")]  # n = numéro attendu par pick
    W = TXT + 6 * (TH * 16 // 9 + PAD) + PAD
    img = Image.new("RGB", (W, max(1, len(rows)) * (TH + PAD) + PAD), "#16181d")
    dr = ImageDraw.Draw(img)
    for r, (n, it) in enumerate(rows):
        y = PAD + r * (TH + PAD)
        dr.text((PAD, y), f"{n}. {it.get('query', '')}", fill="#FFD60A", font=small)
        words, line, ly = it.get("phrase", "").split(), "", y + 40
        for w in words:  # retour à la ligne simple
            if dr.textlength(line + " " + w, font=font) > TXT - 2 * PAD:
                dr.text((PAD, ly), line.strip(), fill="#e8e8e8", font=font)
                line, ly = "", ly + 28
            line += " " + w
        dr.text((PAD, ly), line.strip(), fill="#e8e8e8", font=font)
        x = TXT
        for k, alt in enumerate(it["_alts"][:6]):
            try:
                th = Image.open(alt["miniature"]).convert("RGB")
            except OSError:
                continue
            th.thumbnail((TH * 16 // 9, TH))
            img.paste(th, (x, y))
            col = "#22c55e" if k == 0 else "#ffffff"
            dr.rectangle([x, y, x + th.width, y + th.height], outline=col, width=5 if k == 0 else 1)
            tag = "abcdef"[k] + ("  vidéo" if str(alt["id"]).startswith(("pbv-", "pxv-")) else "")
            dr.rectangle([x, y, x + 12 + int(dr.textlength(tag, font=small)), y + 34], fill=col)
            dr.text((x + 6, y + 3), tag, fill="#000000", font=small)
            x += th.width + PAD
    dst = job / "work" / "broll" / "planche.jpg"
    dst.parent.mkdir(parents=True, exist_ok=True)
    img.save(dst, quality=88)
    return dst


def usable(alt, need, video):
    if not video:
        return True
    return float(alt.get("duree") or 0) >= need + 0.3


def cmd_auto(a):
    job = job_dir(a.job)
    from common import config, size_of
    c = config(job)
    W, H = size_of(None, c["visual"])
    sbp = job / "work" / f"{a.slug}_storyboard.json"
    if a.storyboard:  # vidéo sans rush : une image / vidéo par scène qui a une "query" et pas encore d'"image"
        sb = read_json(sbp)
        rows = [{"scene": i, "query": sc["query"], "phrase": sc.get("voice", ""), "duree": 6,
                 "mode": "full" if sc["kind"] in ("photo", "hook") else "photo"}
                for i, sc in enumerate(sb["scenes"]) if sc.get("query") and not sc.get("image")]
    else:
        sug = job / "work" / f"{a.slug}_broll_suggested.json"
        rows = read_json(sug) if sug.exists() else find_moments(job, a.slug, a.every)[0]
    portrait = H > W
    items, rep_ = [], []
    for row in rows[:a.max]:
        it = {k: row[k] for k in ("scene", "word", "occurrence", "until", "phrase") if k in row}
        it["mode"] = row.get("mode") or "full"
        if row.get("image"):  # média du client déjà choisi par Claude
            it["image"] = row["image"]
            items.append(it)
            rep_.append({"n": len(items), "image": row["image"], "source": "client"})
            continue
        q = row.get("query") or guess_query(row.get("phrase", ""))
        if not q:
            continue
        lang = None if row.get("query") else c.get("language", "fr")  # requête écrite par Claude : en anglais
        need = float(row.get("duree") or 3)
        alts = []  # jusqu'à 3 vidéos (assez longues) puis 3 photos : Claude choisit sur la planche
        if a.kind in ("mix", "video") and it["mode"] == "full":
            alts = [x for x in candidates(job, q, True, lang, "tall" if portrait else "wide") if usable(x, need, True)][:3]
        if a.kind in ("mix", "photo"):
            alts += candidates(job, q, False, lang, "tall" if portrait else "wide")[:3]
        if not alts:
            rep_.append({"phrase": row.get("phrase", "")[:60], "query": q, "pose": False, "raison": "aucun résultat"})
            continue
        it.update(query=q, lang=lang, alts=[x["id"] for x in alts[:6]], _alts=alts[:6])
        it["image"], _ = download(job, argparse.Namespace(id=alts[0]["id"]))
        items.append(it)
        rep_.append({"n": len(items), "query": q, "image": it["image"]})
    pl = planche(job, items)
    write_json(job / "work" / f"{a.slug}_broll_alts.json", [{**{k: v for k, v in it.items() if k != "_alts"},
                                                             "miniatures": [x["miniature"] for x in it.get("_alts", [])]} for it in items])
    if a.storyboard:
        for it in items:
            sb["scenes"][it["scene"]]["image"] = it["image"]
        write_json(sbp, sb)
        return out(ok=True, source=source_name(), plans=rep_, planche=str(pl), fichier=str(sbp),
                   suite="REGARDE la planche ; corrige avec broll.py pick <job> <slug> <n> a-f|none ; puis build_scenes.py")
    write_json(job / "work" / f"{a.slug}_broll.json", [{k: v for k, v in it.items() if k not in ("_alts", "alts", "lang")} for it in items])
    out(ok=True, source=source_name(), plans=rep_, planche=str(pl), fichier=str(job / "work" / f"{a.slug}_broll.json"),
        suite="REGARDE la planche ; corrige avec broll.py pick <job> <slug> <n> b|c|none ; puis build_composition.py")


def cmd_pick(a):
    job = job_dir(a.job)
    alts_p, bj = job / "work" / f"{a.slug}_broll_alts.json", job / "work" / f"{a.slug}_broll.json"
    alts = read_json(alts_p)
    n = int(a.n) - 1
    if not 0 <= n < len(alts):
        fail(f"plan {a.n} inconnu (1 à {len(alts)})")
    if "scene" in alts[n]:  # storyboard : l'image de la scène change (none = la scène garde son fond de charte)
        sbp = job / "work" / f"{a.slug}_storyboard.json"
        sb = read_json(sbp)
        sc = sb["scenes"][alts[n]["scene"]]
        if a.choice == "none":
            sc.pop("image", None)
            write_json(sbp, sb)
            return out(ok=True, scene=alts[n]["scene"], image=None)
        ids = alts[n].get("alts", [])
        new_id = ids["abcdef".index(a.choice)] if len(a.choice) == 1 and a.choice in "abcdef"[:len(ids)] else a.choice
        sc["image"], line = download(job, argparse.Namespace(id=new_id))
        write_json(sbp, sb)
        return out(ok=True, scene=alts[n]["scene"], image=sc["image"], credit=line)
    items = read_json(bj)
    key = {k: alts[n].get(k) for k in ("word", "occurrence")}
    idx = next((i for i, it in enumerate(items) if {k: it.get(k) for k in key} == key), None)
    if a.choice == "none":
        if idx is not None:
            items.pop(idx)
        write_json(bj, items)
        return out(ok=True, retire=a.n, plans=len(items))
    if len(a.choice) == 1 and a.choice in "abcdef":
        ids = alts[n].get("alts", [])
        if "abcdef".index(a.choice) >= len(ids):
            fail(f"pas de proposition {a.choice} pour le plan {a.n}")
        new_id = ids["abcdef".index(a.choice)]
    else:
        new_id = a.choice  # identifiant venu d'une recherche manuelle (search)
    rel, line = download(job, argparse.Namespace(id=new_id))
    entry = {k: v for k, v in alts[n].items() if k not in ("alts", "lang", "miniatures")}
    entry["image"] = rel
    if idx is None:
        items.append(entry)
    else:
        items[idx] = {**items[idx], "image": rel}
    write_json(bj, items)
    out(ok=True, plan=a.n, image=rel, credit=line)


def main():
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("moments")
    p.add_argument("job")
    p.add_argument("slug")
    p.add_argument("--every", type=float, default=7.0, help="écart minimal entre deux plans de coupe (s)")
    p = sp.add_parser("search")
    p.add_argument("job")
    p.add_argument("query")
    p.add_argument("--n", type=int, default=8)
    p.add_argument("--orient", choices=["tall", "wide", "square"])
    p.add_argument("--video", action="store_true", help="vidéos de coupe (Pixabay ou Pexels)")
    p.add_argument("--source", choices=["pixabay", "pexels", "openverse"], help="défaut : la première dont la clé est là")
    p = sp.add_parser("get")
    p.add_argument("job")
    p.add_argument("id")
    p = sp.add_parser("auto")
    p.add_argument("job")
    p.add_argument("slug")
    p.add_argument("--kind", choices=["mix", "photo", "video"], default="mix", help="mix : vidéo si elle tient la durée, sinon photo")
    p.add_argument("--max", type=int, default=6)
    p.add_argument("--every", type=float, default=7.0)
    p.add_argument("--storyboard", action="store_true", help="vidéo sans rush : remplit l'image des scènes qui ont une query")
    p = sp.add_parser("pick")
    p.add_argument("job")
    p.add_argument("slug")
    p.add_argument("n")
    p.add_argument("choice", help="a à f | none | <id>")
    a = ap.parse_args()
    {"moments": cmd_moments, "search": cmd_search, "get": cmd_get, "auto": cmd_auto, "pick": cmd_pick}[a.cmd](a)


if __name__ == "__main__":
    main()

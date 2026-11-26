"""PAIRES DE POLICES (titres + texte) : choisir l'ambiance typographique d'une vidéo, polices Google libres (OFL).

  python polices.py list                                   # les paires, avec leur ambiance et leur usage
  python polices.py planche <job> [--titre "…"] [--texte "…"] [--paires a,b,c]   # work/polices.png : aperçu à montrer
  python polices.py apply <job> <paire>                    # télécharge si besoin et règle config.json du job
  python polices.py get --famille "Playfair Display"       # n'importe quelle police Google sous licence libre

Polices téléchargées depuis le dépôt officiel github.com/google/fonts (fichiers variables : toutes les graisses dans un
fichier), gardées avec leur licence (OFL.txt) dans vendor/fonts/google/<police>/. Seules les licences libres (ofl, apache,
ufl) sont acceptées. La charte du client gagne toujours : ne propose une paire que si la marque n'a pas de police.
apply écrit visual.fontFamily + visual.fontFile (texte, sous-titres) et visual.titleFont (accroche, titres des cartes,
grands chiffres) ; fonts.py les charge pour tous les monteurs.
"""
import argparse
import json
import re
import urllib.request
from pathlib import Path

from common import ROOT, SKILL, fail, job_dir, out, read_json, write_json

CACHE = SKILL / "vendor" / "fonts" / "google"
LOCAL = SKILL / "vendor" / "fonts"
API = "https://api.github.com/repos/google/fonts/contents/{lic}/{slug}"
RAW = "https://raw.githubusercontent.com/google/fonts/main/{lic}/{slug}/{name}"

# titre : (famille, italique, graisse) ; texte : famille ; "local" = déjà dans vendor/fonts
PAIRES = {
    "editorial": {"titre": ("Bodoni Moda", True, 700), "texte": "Inter", "ambiance": "luxe, éditorial",
                  "usage": "immobilier haut de gamme, mode, hôtellerie", "local": {"Bodoni Moda": "BodoniModa-700-italic.woff2"}},
    "chaleureux": {"titre": ("Fraunces", True, 600), "texte": "DM Sans", "ambiance": "chaleureux, artisanal",
                   "usage": "restaurant, boulangerie, bien-être, artisan"},
    "premium": {"titre": ("Cormorant Garamond", False, 600), "texte": "Manrope", "ambiance": "sobre, haut de gamme",
                "usage": "conseil, patrimoine, notaire, cabinet"},
    "moderne": {"titre": ("Space Grotesk", False, 700), "texte": "Inter", "ambiance": "moderne, tech",
                "usage": "tuto, SaaS, IA, agence digitale"},
    "creatif": {"titre": ("Instrument Serif", True, 400), "texte": "Instrument Sans", "ambiance": "créatif, design",
                "usage": "studio, architecte, photographe", "local": {"Instrument Serif": "InstrumentSerif-Italic.ttf"}},
    "punch": {"titre": ("Anton", False, 400), "texte": "Inter", "ambiance": "percutant, promo",
              "usage": "actu, promo, sport, événement", "local": {"Anton": "Anton-Regular.ttf"}},
    "ludique": {"titre": ("Bricolage Grotesque", False, 800), "texte": "Nunito", "ambiance": "ludique, familial",
                "usage": "enfants, food truck, loisirs, fête"},
    "net": {"titre": ("Sora", False, 700), "texte": "Manrope", "ambiance": "net, rassurant",
            "usage": "santé, assurance, services, B2B"},
}


def slug(family):
    return re.sub(r"[^a-z0-9]", "", family.lower())


def _get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "deeplo-video-maker", "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def _download(url, dst):
    req = urllib.request.Request(url, headers={"User-Agent": "deeplo-video-maker"})
    with urllib.request.urlopen(req, timeout=60) as r:
        dst.write_bytes(r.read())


def get(family, italic=False):
    """Fichier (variable si possible) de la police Google, téléchargé une fois -> chemin relatif à ROOT."""
    for pid in PAIRES.values():
        if family in pid.get("local", {}) and (LOCAL / pid["local"][family]).exists():
            return (LOCAL / pid["local"][family]).relative_to(ROOT).as_posix()
    s = slug(family)
    d = CACHE / s
    have = sorted(d.glob("*.ttf")) if d.exists() else []
    pick = [f for f in have if ("Italic" in f.name) == italic]
    if pick:
        return pick[0].relative_to(ROOT).as_posix()
    files, lic = None, None
    for lic in ("ofl", "apache", "ufl"):  # licences libres seulement
        try:
            files = _get_json(API.format(lic=lic, slug=s))
            break
        except Exception:  # noqa: BLE001
            continue
    if not isinstance(files, list):
        fail(f"police introuvable dans google/fonts (licences libres) : {family}")
    ttf = [x["name"] for x in files if x["name"].endswith(".ttf")]
    cand = [n for n in ttf if ("Italic" in n) == italic] or [n for n in ttf if "Italic" not in n]
    if not cand:
        fail(f"aucun fichier .ttf pour {family}")
    var = [n for n in cand if "[" in n]  # variable d'abord (toutes les graisses)
    name = (var or sorted(cand, key=lambda n: ("Regular" not in n, n)))[0]
    d.mkdir(parents=True, exist_ok=True)
    _download(RAW.format(lic=lic, slug=s, name=name.replace("[", "%5B").replace("]", "%5D").replace(",", "%2C")), d / name)
    for lname in ("OFL.txt", "LICENSE.txt"):
        try:
            _download(RAW.format(lic=lic, slug=s, name=lname), d / lname)
            break
        except Exception:  # noqa: BLE001
            continue
    return (d / name).relative_to(ROOT).as_posix()


def faces(p):
    """-> (titre {family, file, weight, style}, texte {family, file})."""
    fam, ital, w = p["titre"]
    return ({"family": fam, "file": get(fam, ital), "weight": w, "style": "italic" if ital else "normal"},
            {"family": p["texte"], "file": get(p["texte"])})


def cmd_planche(job, titre, texte, noms):
    from playwright.sync_api import sync_playwright
    noms = noms or list(PAIRES)
    titre = re.sub(r"(?<=\d) (?=\d)|\s(?=[€%])", " ", titre)  # « 50 000 € » ne se coupe pas
    cells, css = [], []
    for n in noms:
        t, x = faces(PAIRES[n])
        for i, f in enumerate((t, x)):
            css.append(f"@font-face {{ font-family: 'P{n}{i}'; src: url('{(ROOT / f['file']).as_uri()}'); font-weight: 100 900; "
                       f"font-style: {f.get('style', 'normal')}; }}")
        cells.append(f'<div class="c"><div class="n">{n} · {PAIRES[n]["ambiance"]}</div>'
                     f'<div class="t" style="font-family:\'P{n}0\';font-weight:{t["weight"]};font-style:{t["style"]}">{titre}</div>'
                     f'<div class="x" style="font-family:\'P{n}1\'">{texte}</div>'
                     f'<div class="f">{t["family"]} + {x["family"]}</div></div>')
    page = f"""<!doctype html><html><head><meta charset="utf-8"><style>{" ".join(css)}
  body {{ margin: 0; background: #1b1d21; width: 1200px; font-family: sans-serif; }}
  .g {{ display: grid; grid-template-columns: 1fr 1fr; gap: 18px; padding: 18px; }}
  .c {{ background: linear-gradient(160deg, #3a4048, #20242a); border-radius: 18px; padding: 26px 28px; color: #fff; min-height: 230px; }}
  .n {{ font-size: 15px; letter-spacing: .08em; text-transform: uppercase; color: #f2c14e; margin-bottom: 14px; }}
  .t {{ font-size: 58px; line-height: 1.02; margin-bottom: 14px; }}
  .x {{ font-size: 26px; line-height: 1.3; opacity: .92; }}
  .f {{ margin-top: 16px; font-size: 14px; opacity: .55; }}
</style></head><body><div class="g">{"".join(cells)}</div></body></html>"""
    dst = job / "work" if job else ROOT / "jobs"
    dst.mkdir(parents=True, exist_ok=True)
    h = dst / "polices.html"
    h.write_text(page, encoding="utf-8")
    png = dst / "polices.png"
    with sync_playwright() as pw:
        try:
            b = pw.chromium.launch(channel="chrome")
        except Exception:  # noqa: BLE001
            b = pw.chromium.launch()
        pg = b.new_page(viewport={"width": 1200, "height": 400})
        pg.goto(h.as_uri())
        pg.evaluate("document.fonts.ready")
        pg.wait_for_timeout(400)
        pg.screenshot(path=str(png), full_page=True)
        b.close()
    out(ok=True, planche=str(png), paires=noms, suite="montre la planche, puis question à choix (3 paires + « garder la charte »), puis polices.py apply")


def cmd_apply(job, nom):
    t, x = faces(PAIRES[nom])
    cf = job / "config.json"
    c = read_json(cf) if cf.exists() else {}
    vis = c.setdefault("visual", {})
    vis.update(fontFamily=x["family"], fontFile=x["file"], titleFont=t)
    vis.pop("fonts", None)
    c["polices"] = nom
    write_json(cf, c)
    out(ok=True, paire=nom, titre=t, texte=x, licence="OFL / libre (google/fonts), licence gardée dans vendor/fonts/google/")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    pl = sub.add_parser("planche")
    pl.add_argument("job", nargs="?")
    pl.add_argument("--titre", default="Un terrain dès 50 000 €")
    pl.add_argument("--texte", default="à 5 minutes du village, et une heure de la côte")
    pl.add_argument("--paires", help="noms séparés par des virgules (défaut : toutes)")
    a_ = sub.add_parser("apply")
    a_.add_argument("job")
    a_.add_argument("paire", choices=sorted(PAIRES))
    g = sub.add_parser("get")
    g.add_argument("--famille", required=True)
    g.add_argument("--italique", action="store_true")
    a = ap.parse_args()
    if a.cmd == "list":
        return out(ok=True, paires={k: {"titre": f"{v['titre'][0]}{' italique' if v['titre'][1] else ''}", "texte": v["texte"],
                                         "ambiance": v["ambiance"], "usage": v["usage"]} for k, v in PAIRES.items()})
    if a.cmd == "get":
        return out(ok=True, fichier=get(a.famille, a.italique))
    if a.cmd == "planche":
        noms = [x.strip() for x in a.paires.split(",")] if a.paires else None
        for n in noms or []:
            if n not in PAIRES:
                fail(f"paire inconnue : {n}", connues=sorted(PAIRES))
        return cmd_planche(job_dir(a.job) if a.job else None, a.titre, a.texte, noms)
    cmd_apply(job_dir(a.job), a.paire)


if __name__ == "__main__":
    main()

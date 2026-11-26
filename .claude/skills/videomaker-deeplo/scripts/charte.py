"""CHARTE EN CHIFFRES : crée (ou complète) brands/<marque>/brand.json après l'entretien de style d'une nouvelle marque.

  python charte.py creer <marque> nom="Boulangerie Martin" accent=#c2410c fond=#f6f4f0 encre=#1a1a1a \
      polices=chaleureux sous_titres=souligne vitesse=doux musique=acoustic ton="chaleureux, direct" \
      logo=inbox/logo.png site=boulangerie-martin.be interdits="jamais de rouge|pas d'emoji" references="@createur : coupes franches"
  python charte.py voir <marque>

Des chiffres, pas des adjectifs : couleurs en hex, paire de polices (polices.py, fichiers copiés dans
brands/<marque>/fonts/ avec leur licence), style de sous-titres, vitesse des animations (visual.motionStyle :
punchy = rebonds courts, doux = entrées longues amorties), ambiance musicale. Les interdits deviennent des goûts gardés
du client (gouts.py, origine « user ») : relus à chaque projet de la marque. Une clé absente garde la valeur actuelle.
"""
import argparse
import re
import shutil
from pathlib import Path

from common import ROOT, fail, out, read_json, write_json

STYLES = ["pop", "karaoke", "minimal", "boite", "impact", "duo", "mono", "bulle", "souligne", "geant", "editorial"]
KEYS = {"nom", "accent", "fond", "encre", "texte", "polices", "sous_titres", "vitesse", "musique", "ton", "logo", "site",
        "interdits", "references", "look", "ouverture"}
HEX = re.compile(r"^#[0-9a-fA-F]{6}$")


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def parse(pairs):
    vals = {}
    for kv in pairs:
        if "=" not in kv:
            fail(f"attendu clé=valeur : {kv}")
        k, v = kv.split("=", 1)
        k = k.strip().replace("-", "_")
        if k not in KEYS:
            fail(f"clé inconnue : {k}", connues=sorted(KEYS))
        vals[k] = v.strip()
    for k in ("accent", "fond", "encre", "texte"):
        if k in vals and not HEX.match(vals[k]):
            fail(f"{k} : couleur hex attendue (#rrggbb), reçu {vals[k]}")
    if vals.get("sous_titres") and vals["sous_titres"] not in STYLES:
        fail(f"sous_titres inconnu : {vals['sous_titres']}", styles=STYLES)
    if vals.get("vitesse") and vals["vitesse"] not in ("punchy", "doux"):
        fail("vitesse : punchy | doux")
    return vals


def creer(marque, vals):
    d = ROOT / "brands" / marque
    f = d / "brand.json"
    new = not f.exists()
    b = read_json(f) if not new else read_json(ROOT / "brands" / "_exemple" / "brand.json")
    b.pop("_aide", None)
    v = b.setdefault("video", {})
    vis, txt = v.setdefault("visual", {}), v.setdefault("text", {})
    if new:  # le modèle pointe vers des fichiers d'exemple : rien d'hérité
        vis.pop("logo", None)
        v.get("branding", {}).clear()
    if "nom" in vals:
        b["name"] = vals["nom"]
    if "ton" in vals:
        b["tone"] = vals["ton"]
    if "site" in vals:
        b.setdefault("contact", {})["site"] = vals["site"]
    for k, key in (("accent", "accentColor"), ("fond", "bgColor"), ("encre", "inkColor"), ("texte", "textColor")):
        if k in vals:
            vis[key] = vals[k]
    if "vitesse" in vals:
        vis["motionStyle"] = vals["vitesse"]
    if "sous_titres" in vals:
        txt["captionStyle"] = vals["sous_titres"]
    if "musique" in vals:
        v.setdefault("music", {})["mood"] = vals["musique"]
    if "logo" in vals:
        src = Path(vals["logo"])
        src = src if src.is_absolute() else ROOT / src
        if not src.exists():
            fail(f"logo introuvable : {vals['logo']}")
        d.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, d / f"logo{src.suffix.lower()}")
        vis["logo"] = f"brands/{marque}/logo{src.suffix.lower()}"
    if "polices" in vals:  # fichiers copiés dans la marque (le cache vendor/fonts/google n'est pas versionné)
        import polices
        if vals["polices"] not in polices.PAIRES:
            fail(f"paire inconnue : {vals['polices']}", paires=sorted(polices.PAIRES))
        t, x = polices.faces(polices.PAIRES[vals["polices"]])
        fd = d / "fonts"
        fd.mkdir(parents=True, exist_ok=True)
        for face in (t, x):
            p = ROOT / face["file"]
            shutil.copy2(p, fd / p.name)
            for lic in ("OFL.txt", "LICENSE.txt", "OFL-" + p.stem.split("-")[0] + ".txt"):
                if (p.parent / lic).exists():
                    shutil.copy2(p.parent / lic, fd / f"{slug(face['family'])}-{lic}")
            face["file"] = f"brands/{marque}/fonts/{p.name}"
        vis.update(fontFamily=x["family"], fontFile=x["file"], titleFont=t)
        vis.pop("fonts", None)
        b["polices"] = vals["polices"]
    for k in ("look", "ouverture"):
        if k in vals:
            b.setdefault("style", {})[k] = vals[k]
    if "references" in vals:
        b.setdefault("style", {})["references"] = [x.strip() for x in vals["references"].split("|") if x.strip()]
    b["source"] = b.get("source") or "entretien de style (charte.py)"
    write_json(f, b)
    gouts = []
    if vals.get("interdits"):  # « jamais de rouge » -> goût gardé du client, relu à chaque projet
        from gouts import path_of
        import subprocess
        import sys
        for it in [x.strip() for x in vals["interdits"].split("|") if x.strip()]:
            subprocess.run([sys.executable, str(Path(__file__).parent / "gouts.py"), "add", marque, it, "--from", "user"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
            gouts.append(it)
        gouts_file = str(path_of(marque))
    else:
        gouts_file = None
    return {"charte": str(f), "visual": vis, "text": txt, "interdits": gouts or None, "gouts": gouts_file}


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("creer")
    c.add_argument("marque")
    c.add_argument("pairs", nargs="*")
    v = sub.add_parser("voir")
    v.add_argument("marque")
    a = ap.parse_args()
    m = slug(a.marque)
    if a.cmd == "voir":
        f = ROOT / "brands" / m / "brand.json"
        if not f.exists():
            fail(f"pas de charte : brands/{m}/brand.json")
        return out(ok=True, charte=read_json(f))
    out(ok=True, marque=m, **creer(m, parse(a.pairs)))


if __name__ == "__main__":
    main()

"""POLICES DE LA CHARTE -> règles @font-face, pour tous les monteurs (composition, explainer, data, footage, punch,
scènes, couvertures).

  visual.fonts     : [{"file": "brands/x/fonts/X-Bold.ttf", "weight": 700, "format": "truetype", "style": "normal"}]
  visual.fontFile  : police variable (toutes les graisses dans un fichier), s'ajoute aux "fonts"
  visual.titleFont : {"family": "Playfair Display", "file": "…", "weight": 400} : police des titres (accroche, titres
                     des temps forts, grands chiffres) ; sans elle, les titres gardent fontFamily.
Chemins relatifs cherchés dans inbox/ du job, le job, puis la racine du projet ; copiés dans <job>/assets/fonts.
"""
import shutil
from pathlib import Path

from common import ROOT, fail

FMT = {".woff2": "woff2", ".woff": "woff", ".ttf": "truetype", ".otf": "opentype"}


def _copy(job, rel, dst):
    p = Path(rel)
    if not p.is_absolute():
        for base in (job / "inbox", job, ROOT):
            if (base / p).exists():
                p = base / p
                break
    if not p.exists():
        fail(f"police introuvable : {rel}")
    dst.mkdir(parents=True, exist_ok=True)
    if p.resolve() != (dst / p.name).resolve():
        shutil.copy2(p, dst / p.name)
    return p.name


def brand_faces(job, vis, dst=None, url=None):
    """@font-face de la charte (fonts + fontFile + titleFont). dst : dossier où copier (défaut <job>/assets/fonts) ;
    url : préfixe des url() (défaut « assets/fonts/ » ; « » quand la page est dans dst, comme les couvertures)."""
    dst = Path(dst) if dst else job / "assets" / "fonts"
    url = "assets/fonts/" if url is None else url
    fam, css = vis["fontFamily"], []

    def face(family, rel, weight, style="normal", fmt=None):
        name = _copy(job, rel, dst)
        fmt = fmt or FMT.get(Path(name).suffix.lower())
        css.append(f"@font-face {{ font-family: '{family}'; src: url('{url}{name}')" + (f" format('{fmt}')" if fmt else "")
                   + f"; font-weight: {weight}; font-style: {style}; }}")
    for f in vis.get("fonts", []):
        face(fam, f["file"], f.get("weight", 400), f.get("style", "normal"), f.get("format"))
    if vis.get("fontFile"):  # police variable : toutes les graisses
        face(fam, vis["fontFile"], "100 900")
    tf = vis.get("titleFont")
    if tf and tf.get("file"):
        face(tf["family"], tf["file"], tf.get("weight", 400), tf.get("style", "normal"))
    return " ".join(css)


def title_stack(vis, fallback=None):
    """Pile CSS de la police des titres : « 'Playfair Display', '<texte>', Georgia, serif », sinon celle du texte."""
    tf = vis.get("titleFont") or {}
    fam = fallback or vis["fontFamily"]
    return f"'{tf['family']}', '{fam}', Georgia, serif" if tf.get("family") else f"'{fam}', 'Inter', sans-serif"


def title_weight(vis, default=800):
    """Graisse des titres : celle de titleFont (une serif Regular ne doit pas être grossie en faux gras)."""
    tf = vis.get("titleFont") or {}
    return tf.get("weight", 400) if tf.get("family") else default

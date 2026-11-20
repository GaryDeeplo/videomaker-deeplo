"""GUIDE DE TOURNAGE à envoyer au client avant qu'il filme -> guide-tournage.html (une page, lisible sur téléphone,
imprimable, cases à cocher)

  python guide.py [--job <job>] [--client "Boulangerie Martin"] [--metier boutique|artisan|restaurant|service|recrutement]
                  [--brand <dossier brands/>] [--envoi "lien WeTransfer / Drive…"] [--contact "Prénom, 04…"] [--format vertical|horizontal]

Contenu : matériel, cadrage, lumière, son, comment parler (et se tromper sans stress), script type du métier
(accroche, problème, solution, preuve, appel à l'action, à compléter avec SES mots et SES vrais chiffres), plans de
coupe à filmer en plus, droits à l'image, envoi des fichiers sans compression. Rien n'est envoyé : la page est créée,
l'utilisateur la transmet lui-même (mail, WhatsApp, impression).
"""
import argparse
import html
from pathlib import Path

from common import ROOT, job_dir, out, read_json

SCRIPTS = {
    "boutique": ("Commerce / boutique", [
        ("Accroche (3 s)", "« Vous cherchez [ce que vos clients cherchent] à [ville] ? »"),
        ("Qui vous êtes", "« Moi c'est [prénom], et depuis [année] on [ce que vous faites] chez [nom de la boutique]. »"),
        ("Ce qui vous rend différent", "« Ici, [votre vraie différence : conseil, fait main, local, sur mesure…]. »"),
        ("Une preuve", "« [Un fait réel : nombre de clients, un avis, une réalisation, une récompense]. »"),
        ("Appel à l'action", "« Passez nous voir [adresse / quartier], on est ouverts [jours]. »")],
        ["la vitrine et l'enseigne", "les rayons ou le produit phare en gros plan", "vos mains qui emballent ou conseillent",
         "un client servi (avec son accord)", "la porte qui s'ouvre / l'entrée"]),
    "artisan": ("Artisan / chantier", [
        ("Accroche (3 s)", "« Voilà ce que [problème courant] devient en [durée]. »"),
        ("Qui vous êtes", "« Je suis [prénom], [métier] à [ville] depuis [x] ans. »"),
        ("Le problème", "« Beaucoup de [clients] ont [le problème] et ne savent pas que [ce qu'il faut savoir]. »"),
        ("Comment vous le réglez", "« Nous, on [votre méthode, en une ou deux phrases simples]. »"),
        ("Appel à l'action", "« Pour un devis, [comment vous contacter]. »")],
        ["l'avant (même angle que l'après)", "l'après", "vos outils et vos mains au travail (gros plan)",
         "le camion ou l'atelier", "un détail de finition"]),
    "restaurant": ("Restaurant / café / traiteur", [
        ("Accroche (3 s)", "« Le [plat signature], c'est [ce qui le rend spécial]. »"),
        ("Qui vous êtes", "« Moi c'est [prénom], chef / patron de [nom] à [ville]. »"),
        ("Le produit", "« On travaille [vos vrais produits / fournisseurs / fait maison]. »"),
        ("L'ambiance", "« Ici, on vient pour [l'ambiance réelle : terrasse, famille, afterwork…]. »"),
        ("Appel à l'action", "« Réservez au [numéro / lien], on est ouverts [jours]. »")],
        ["un plat qu'on dresse (vue du dessus et de côté)", "la cuisine en action", "la salle ou la terrasse",
         "un verre qu'on sert", "la devanture"]),
    "service": ("Service / indépendant / conseil", [
        ("Accroche (3 s)", "« L'erreur que je vois le plus souvent chez [vos clients] : [l'erreur]. »"),
        ("Qui vous êtes", "« Je suis [prénom], j'aide [type de clients] à [résultat]. »"),
        ("Le conseil", "« Le bon réflexe, c'est [un conseil utile et concret]. »"),
        ("Une preuve", "« [Un cas réel, avec l'accord du client, ou votre expérience chiffrée réelle]. »"),
        ("Appel à l'action", "« Si vous voulez en parler, [comment vous contacter]. »")],
        ["vous au bureau ou en rendez-vous", "vos mains sur le clavier / un document", "l'entrée de vos locaux",
         "un échange avec un client (avec son accord)", "un résultat à l'écran"]),
    "recrutement": ("Recrutement", [
        ("Accroche (3 s)", "« On recrute un·e [poste] à [ville] ! »"),
        ("L'équipe", "« Chez [nom], on est [x] et on [ce que fait l'équipe]. »"),
        ("Le poste", "« Vous allez [missions principales, en mots simples]. »"),
        ("Pourquoi nous", "« Ce qu'on offre : [avantages réels : horaires, ambiance, formation…]. »"),
        ("Appel à l'action", "« Envoyez-nous [CV / message] à [contact]. »")],
        ["l'équipe ensemble (tout le monde d'accord pour être filmé)", "le lieu de travail", "un geste du métier",
         "un moment convivial", "la personne qui recrute, face caméra"]),
}


def esc(s):
    return html.escape(str(s), quote=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--job")
    ap.add_argument("--client", default="")
    ap.add_argument("--metier", choices=list(SCRIPTS), default="boutique")
    ap.add_argument("--brand")
    ap.add_argument("--envoi", default="", help="lien ou méthode d'envoi des fichiers (WeTransfer, Google Drive…)")
    ap.add_argument("--contact", default="", help="qui contacter en cas de question")
    ap.add_argument("--format", choices=["vertical", "horizontal"], default="vertical")
    ap.add_argument("--out")
    a = ap.parse_args()

    accent, logo_html = "#2f5bea", ""
    brand = a.brand
    job = job_dir(a.job) if a.job else None
    if job and not brand:
        brand = read_json(job / "job.json").get("brand") or None
    bj = ROOT / "brands" / (brand or "") / "brand.json"
    if brand and bj.exists():
        vis = (read_json(bj).get("video") or {}).get("visual", {})
        accent = vis.get("accentColor", accent)
    titre_metier, script, plans = SCRIPTS[a.metier]
    vert = a.format == "vertical"

    def check(items):
        return "".join(f'<li><label><input type="checkbox"> <span>{esc(x)}</span></label></li>' for x in items)

    steps = "".join(f'<li><b>{esc(t)}</b><span>{esc(x)}</span></li>' for t, x in script)
    envoi = (f'<p>Envoyez-les ici : <b>{esc(a.envoi)}</b></p>' if a.envoi else
             "<p>Par <b>WeTransfer</b>, <b>Google Drive</b> ou <b>Swiss Transfer</b> (gratuits), jamais par WhatsApp ou Messenger.</p>")
    contact = f'<p class="contact">Une question ? {esc(a.contact)}</p>' if a.contact else ""
    page = f"""<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Guide de tournage</title><style>
:root {{ --bg: #f7f6f3; --card: #ffffff; --ink: #1c1c1e; --mute: #66666c; --acc: {accent}; --line: rgba(0,0,0,.08); }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg: #131315; --card: #1d1d20; --ink: #f1f1f3; --mute: #a0a0a8; --line: rgba(255,255,255,.1); }} }}
* {{ box-sizing: border-box; }}
body {{ margin: 0; background: var(--bg); color: var(--ink); font: 16px/1.55 system-ui, -apple-system, "Segoe UI", sans-serif; }}
main {{ max-width: 760px; margin: 0 auto; padding: 28px 16px 64px; }}
header {{ border-left: 6px solid var(--acc); padding: 4px 0 4px 16px; margin-bottom: 26px; }}
h1 {{ margin: 0; font-size: 28px; line-height: 1.15; }} .sub {{ color: var(--mute); margin: 6px 0 0; }}
section {{ background: var(--card); border-radius: 16px; padding: 18px 20px; margin: 0 0 14px; box-shadow: 0 1px 2px var(--line); }}
h2 {{ margin: 0 0 10px; font-size: 19px; }} h2 .n {{ display: inline-flex; width: 28px; height: 28px; border-radius: 50%;
     background: var(--acc); color: #fff; font-size: 15px; align-items: center; justify-content: center; margin-right: 8px; }}
ul {{ margin: 0; padding-left: 20px; }} li {{ margin: 4px 0; }}
ul.chk {{ list-style: none; padding: 0; }} ul.chk li label {{ display: flex; gap: 10px; align-items: flex-start; cursor: pointer; }}
ul.chk input {{ width: 20px; height: 20px; margin-top: 3px; accent-color: var(--acc); flex: 0 0 auto; }}
ol.script {{ padding-left: 22px; }} ol.script li {{ margin: 8px 0; }} ol.script b {{ display: block; }}
ol.script span {{ color: var(--mute); font-style: italic; }}
.tip {{ border-left: 4px solid var(--acc); padding: 8px 12px; margin: 12px 0 0; background: rgba(127,127,127,.08); border-radius: 0 10px 10px 0; }}
.big {{ font-size: 18px; font-weight: 700; }}
.contact {{ text-align: center; color: var(--mute); margin-top: 24px; }}
@media print {{ body {{ background: #fff; color: #000; }} section {{ box-shadow: none; border: 1px solid #ddd; break-inside: avoid; }} }}
</style></head><body><main>
<header><h1>Guide de tournage{(" · " + esc(a.client)) if a.client else ""}</h1>
<p class="sub">5 minutes de lecture pour des vidéos qu'on peut vraiment monter. Pas besoin d'être à l'aise : on coupe tout ce qui ne va pas.</p></header>

<section><h2><span class="n">1</span>Le matériel</h2><ul class="chk">{check([
    "Votre téléphone suffit. Nettoyez l'objectif (un coup de chiffon change tout).",
    f"Filmez en {'VERTICAL (téléphone debout)' if vert else 'HORIZONTAL (téléphone couché)'}, en 1080p ou 4K, 30 images/s.",
    "Posez le téléphone : trépied, pile de livres, étagère. Jamais à bout de bras.",
    "Micro-cravate si possible (15 à 60 €, se branche sur le téléphone) : c'est le meilleur investissement.",
    "Mode avion (pas d'appel en plein milieu) et assez de place sur le téléphone."])}</ul></section>

<section><h2><span class="n">2</span>Le cadrage</h2><ul class="chk">{check([
    "Téléphone à hauteur des yeux, à environ 1 mètre.",
    "Vos yeux dans le tiers haut de l'image, un peu d'espace au-dessus de la tête.",
    "Un fond rangé et qui vous ressemble (boutique, atelier, comptoir), pas un mur blanc collé dans le dos.",
    "Caméra principale (celle de derrière) si quelqu'un filme ; caméra selfie si vous êtes seul·e."])}</ul></section>

<section><h2><span class="n">3</span>La lumière</h2><ul class="chk">{check([
    "Face à une fenêtre : la lumière vient vers vous, jamais dans votre dos.",
    "Éteignez les néons ou lampes de couleurs différentes si la lumière du jour suffit.",
    "Pas de soleil direct sur le visage (ombres dures) : préférez une lumière douce."])}</ul></section>

<section><h2><span class="n">4</span>Le son (le plus important)</h2><ul class="chk">{check([
    "Une pièce calme : fermez les fenêtres, coupez musique, clim, frigo bruyant, hotte.",
    "Évitez les grandes pièces vides qui résonnent (un tapis, des rideaux aident).",
    "Faites un test de 10 secondes et réécoutez avec des écouteurs avant de tout tourner."])}</ul>
<p class="tip">On peut rattraper une image moyenne, beaucoup plus difficilement un son qui résonne ou qui grésille.</p></section>

<section><h2><span class="n">5</span>Comment parler</h2><ul class="chk">{check([
    "Regardez l'objectif, pas l'écran.",
    "Phrase par phrase. Vous vous trompez ? Faites une pause d'une seconde et redites la phrase EN ENTIER.",
    "Vous pouvez dire « je la refais » : on garde automatiquement la meilleure prise.",
    "Les 3 premières secondes comptent le plus : commencez directement par l'accroche, sans « bonjour, alors… ».",
    "Un peu plus d'énergie que d'habitude et un sourire : ça se voit à l'écran.",
    "30 à 60 secondes au total suffisent pour un Reel."])}</ul></section>

<section><h2><span class="n">6</span>Que dire ? Un plan simple ({esc(titre_metier)})</h2>
<ol class="script">{steps}</ol>
<p class="tip">Remplacez les [crochets] par VOS mots et VOS vrais chiffres. Pas besoin d'apprendre par cœur : notez les 5 idées
sur un papier posé à côté du téléphone et dites-les avec vos mots.</p></section>

<section><h2><span class="n">7</span>Filmez aussi des images d'illustration</h2>
<p>5 à 10 petits plans de <b>5 secondes</b>, sans parler, téléphone immobile, dans le même sens que vos vidéos :</p>
<ul class="chk">{check(plans)}</ul>
<p class="tip">Ces images passent pendant que vous parlez : la vidéo devient vivante. Envoyez aussi votre logo en bonne qualité
et quelques photos de vos produits.</p></section>

<section><h2><span class="n">8</span>Les autorisations</h2><ul class="chk">{check([
    "Toute personne reconnaissable (client, employé) doit être d'accord pour apparaître.",
    "N'ajoutez pas de musique vous-même : on s'en occupe, avec des musiques libres de droits.",
    "Évitez les marques et logos d'autres entreprises bien visibles (affiches, écrans, vêtements)."])}</ul></section>

<section><h2><span class="n">9</span>Envoyer les fichiers</h2>
<p class="big">Envoyez les fichiers ORIGINAUX, sans les retoucher.</p>
{envoi}
<p>WhatsApp et Messenger compressent les vidéos : l'image devient floue et on ne peut plus rien en faire.
Envoyez tout, même les essais ratés : on choisit les meilleures prises.</p></section>
{contact}
</main></body></html>"""
    dst = Path(a.out) if a.out else ((job / "renders" / "guide-tournage.html") if job else ROOT / "dist" / "guide-tournage.html")
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(page, encoding="utf-8")
    out(ok=True, page=str(dst), metier=a.metier, client=a.client or None,
        suite="ouvre la page ; l'utilisateur l'envoie lui-même (mail, WhatsApp, impression en PDF)")


if __name__ == "__main__":
    main()

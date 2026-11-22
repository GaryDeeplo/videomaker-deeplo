# Dessiner le sujet d'une accroche (SVG)

L'accroche anime le titre ; avec un dessin, elle montre aussi **le sujet de la vidéo** (le plat signature, la façade,
le produit, l'outil) dans le style choisi. Tu dessines toi-même un SVG simple, à partir d'une photo du client (regarde-la)
ou de la description. Ce n'est pas une image réaliste : une illustration lisible en 1 seconde.

## Règles communes
- `<svg viewBox="0 0 400 400" xmlns="http://www.w3.org/2000/svg">`, sujet centré, marge de 20 ; **15 à 40 éléments**.
- **Les éléments de premier niveau entrent un par un** (papier, pâte, isométrique, mosaïque, pixel) : regroupe en `<g>`
  les morceaux qui vont ensemble (la croûte, la sauce, les olives…) et mets-les dans l'ordre d'apparition.
- Pas de texte, pas d'image externe, pas de filtre ni de dégradé à id (un même bloc peut être monté deux fois).
- Couleurs en dur (hex), tirées de la charte et du style ci-dessous. Formes simples : `path`, `circle`, `ellipse`,
  `rect` (`rx` pour arrondir), `polygon`, `line`.
- Fichier : `work/<slug>_art.svg`, puis `"hook": {"style": "pate", "text": "…", "art": "work/<slug>_art.svg"}`
  (config, plan de montage) ou `"art": "work/<slug>_art.svg"` dans la scène `accroche-<style>` du storyboard.
- Vérifie au snapshot : le dessin est reconnaissable, ne touche pas le titre, se lit sur le fond.

## Par style
| Style | Comment dessiner | Entrée animée |
|---|---|---|
| `papier` | aplats de couleur, formes un peu irrégulières (papier découpé), 3 à 5 couleurs, pas de contour | les morceaux tombent et se posent |
| `plan` | **traits seuls** blancs (`fill="none"`, `stroke="#fff"`, épaisseur 3), cotes et axes en accent | les traits se tracent |
| `pate` | formes très arrondies et épaisses, couleurs vives et pastel, petit reflet blanc (`opacity .35`) | chaque morceau rebondit |
| `neon` | traits épais lumineux (`stroke` rose / cyan / jaune, `fill="none"`), formes géométriques | tracé puis clignotement |
| `aquarelle` | aplats translucides (`opacity .5–.7`) qui se chevauchent, couleurs douces, contours absents | apparition floue qui se précise |
| `pixel` | grille de `rect` carrés de même taille (10 ou 20), palette de 4 à 6 couleurs | blocs qui apparaissent par à-coups |
| `isometrique` | volumes en perspective 30° : 3 faces par volume (dessus clair, côtés plus foncés) | les volumes montent |
| `mosaique` | carreaux (`rect`) aux couleurs de la palette qui composent la forme | les carreaux se retournent |
| `encre` | traits noirs épais et irréguliers (`stroke="#111"`, bouts ronds), 1 touche de rouge | coups de pinceau tracés |
| `relief` | aplats francs + une ombre décalée plus foncée sous chaque forme | le dessin pivote dans la lumière |

Exemples d'idées : resto -> le plat signature ou la façade ; chantier -> la façade en plan ou la pièce en isométrique ;
coiffeur -> ciseaux et peigne ; boulangerie -> croissant en pâte à modeler ; tech -> l'écran ou le logo de l'outil
(logos : seulement pour parler de l'outil, jamais pour faire croire à un partenariat).

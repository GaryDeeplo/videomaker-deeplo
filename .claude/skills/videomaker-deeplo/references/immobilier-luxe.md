# Pack « immobilier / luxe »

Références Gold Estates, Villa Surin : `jobs/_references/exemple-279*`. Scripts depuis la racine du projet :
`PYTHONUTF8=1 python .claude/skills/videomaker-deeplo/scripts/<x>.py`.

Rush plein écran (pas de cartes), tout se pose DANS l'image :
- Sous-titres `editorial` (`text.captionStyle`, `captionMaxWords` 3) : petits mots en sans fine, le mot fort (chiffre,
  mot fort, sinon le mot plein le plus long) en serif Didone italique (Bodoni Moda, OFL) ivoire, empilé ;
  `text.editorialColor` pour une autre teinte (fond clair : couleur sombre de la charte). Les nombres restent entiers
  (« 50 000 »).
- Mots dans le décor : mots dynamiques (`references/mots-dynamiques.md`) avec
  `"mots": {"police": "serif", "couleur": "<accent>"}` (nom du bien, lieu, marque : 3 à 5 par vidéo dans
  `work/<slug>_mots.json`) ; `"sol": true` sur une entrée = mot posé au sol en perspective, derrière la personne (plan
  large : en selfie serré il est caché par le corps).
- Blocs en verre (`work/<slug>_motions.json`, sur un mot dit) : `recherche-verre` (`query`, `place` : barre qui se tape +
  pastille lieu), `lieu-photo` (`image` du VRAI lieu, `name`, épingle `pinx`/`piny`), `cartes-3d` (`image1`/`image2`,
  `label1`/`label2` : photos réelles du bien de chaque côté), `chiffre-verre` (`to`, `unit`, `before`, `after`, `cote` :
  chiffre géant qui compte + cote fléchée), `fin-logo` (`logo`, `tagline` : vidéo floutée sous un voile, logo au centre).
  Photos : celles du client ou des images tirées du rush (jamais une banque présentée comme le bien).
- Finitions : `visual.progressBar: true` (barre de progression en bas, couleur d'accent) ; petite source -> ni zoom ni
  dérive.
- Rythme « visite » : avec des rushs du bien, un plan de coupe toutes les 3-4 s (`broll.py` avec les clips du client,
  `references/plans-de-coupe.md`).

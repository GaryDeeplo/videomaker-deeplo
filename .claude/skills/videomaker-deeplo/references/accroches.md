# Accroches animées (3 s d'ouverture) et variantes A/B

Scripts depuis la racine du projet : `PYTHONUTF8=1 python .claude/skills/videomaker-deeplo/scripts/<x>.py`.

## Dix styles pour le même titre
`papier` (couches de papier, lettres qui se posent), `plan` (blueprint : grille, titre au trait, cote), `pate` (pâte à
modeler qui rebondit), `neon` (synthwave : soleil rayé, sol quadrillé, néon qui clignote), `aquarelle` (taches qui
diffusent, titre au pinceau), `pixel` (à-coups, ombre en blocs), `isometrique` (blocs qui montent), `mosaique` (carreaux
qui se retournent), `encre` (coup de pinceau, sceau rouge), `relief` (titre extrudé qui pivote).
Blocs `library/block/accroche-<style>` (variables text, sub, accent, bg, ink, font ; générés par `_make_hook_blocks.py`).
- Rush : `python .claude/skills/videomaker-deeplo/scripts/build_composition.py <job> <slug> --accroche neon --accroche-texte "…"` ou
  `"hook": {"style": "neon", "text": "…", "sub": "…"}` dans la config ; remplace l'intro de marque, la vidéo démarre
  sous son volet de sortie.
- Images sans paroles : `"hook": {…}` dans `work/<slug>_footage.json` (ou `--accroche`) ; le titre ne s'affiche pas deux fois.
- Vidéo sans rush : une scène `{"kind": "block", "block": "accroche-plan", "vars": {"text": "…"}, "hold": 3}`.
- Short : le `hook` de `work/<s>_shorts.json` (≤ 7 mots) s'affiche en titre les 3 premières secondes.

Choix du style selon le ton : chantier / artisan -> `plan`, enfant / food fun -> `pate`, tech / soirée -> `neon` ou
`relief`, haut de gamme / bien-être -> `aquarelle` ou `encre`, jeu / rétro -> `pixel`, chiffres / immobilier ->
`isometrique`.
Quand la recommander (série 3 de l'accueil) : « titre animé » pour un reel d'annonce ou un journal de chantier ; pas
d'accroche pour un témoignage ou un ton sobre. Brief : `accroche=titre` -> `"hook": {"style": <selon le ton>, "text":
<titre court>}` ; `accroche=dessin` -> en plus, le sujet dessiné (ci-dessous) ; `accroche=non` -> rien.

## Avec le sujet dessiné (brief `accroche=dessin`)
Lis `references/accroches-dessin.md`, regarde la photo du sujet (plat signature, façade, produit, outil), écris
`work/<slug>_art.svg` dans le style choisi (15 à 40 formes, morceaux groupés dans l'ordre d'apparition), puis
`"art": "work/<slug>_art.svg"` dans `hook` (ou dans la scène `accroche-…`). Le titre remonte, le dessin entre à la
manière du style (tracé, rebond, pièces de papier…). Snapshot obligatoire : le dessin doit être reconnaissable et ne
pas toucher le titre ; sinon, simplifie-le plutôt que d'ajouter des détails.

## Pour toute une marque
`python .claude/skills/videomaker-deeplo/scripts/onboard.py profil --marque <m> --parcours <p> accroche=titre accroche_style=<style>` (ou `accroche=dessin`,
avec accord), puis `"hook"` dans la charte : toutes ses vidéos s'ouvrent ainsi. Si la marque a déjà un réglage
`accroche`, ne propose pas l'accroche à la série 3.

## Variantes d'accroche A/B (après validation de l'aperçu, base rendue SANS accroche)
`python .claude/skills/videomaker-deeplo/scripts/variants.py propose <job> <slug>` -> réécris les titres de `work/<slug>_variantes.json` (3 promesses
différentes : bénéfice, question, contraste ; ≤ 6 mots ; rien que la vidéo ne tienne), puis
`python .claude/skills/videomaker-deeplo/scripts/variants.py make <job> <slug>` : seules les 3 premières secondes sont rendues par variante (≈ 40 s chacune),
recollées au reste de la base (voix d'origine dès le début, sous le titre). -> `renders/variantes/` + `variantes.html`
(lecteurs + tableau de suivi). Conseil à donner : « Reels d'essai » Instagram ou jours comparables, garder la meilleure
rétention à 3 s.

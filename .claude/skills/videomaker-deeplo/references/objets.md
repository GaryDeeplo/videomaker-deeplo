# Objets animés (carte, calendrier, devis, chrono…) et tableau à palettes

Scripts depuis la racine du projet : `PYTHONUTF8=1 python .claude/skills/videomaker-deeplo/scripts/<x>.py`.
Même JSON que les temps forts de l'écran partagé (`work/<slug>_panels.json`, `references/ecran-partage.md`), de
l'explainer et de l'infographie (`work/<slug>_data.json`). Détails et exemples dans `scripts/objets.py`.

- `map` : carte du monde, pays qui s'allument, arcs depuis `from`, `zoom`.
- `calendar` : mois qui se remplit, jours marqués, cartes.
- `timeline` : pistes de logiciel de montage qui se remplissent, tête de lecture.
- `invoice` : devis dont le total monte, tampon.
- `revenue` : montant qui monte, courbe, paiements reçus qui s'empilent.
- `clock` : `"unit": "minutes"` chronomètre « 30 minutes. » ; `"jours"` horloge qui tourne « J+30 ».
- `flap` : tableau d'affichage à palettes (2 à 4 lignes de 14 caractères) : chiffres ou mots qui défilent puis se posent.
- Bloc plein écran `scan-visage` (motions) : coins de cadrage, visage désaturé, ligne qui balaie, 0 -> 100 %, verdict.

Quand les proposer (habillage, série 3 de l'accueil) : lieux et distances -> `map` (pays qui s'allume) + `clock` ;
prix, fourchettes, chiffres -> `stat` (bruitage de caisse sur les €), `flap`, calcul en étapes (`steps`), devis
(`invoice`). Uniquement des chiffres, dates et montants réels, dits ou montrés dans la vidéo.

# S'inspirer d'un reel qui marche, vitrine « Brut / Montage », démo, portfolio

Scripts depuis la racine du projet : `PYTHONUTF8=1 python .claude/skills/videomaker-deeplo/scripts/<x>.py`.

## S'inspirer d'un reel qui marche (rythme d'une référence)
```bash
python .claude/skills/videomaker-deeplo/scripts/reference.py analyse <lien ou fichier> --nom <ref>   # jobs/_references/<ref>/ : profil.json + planche.jpg
#   TU regardes planche.jpg et complètes "grammaire" (le MÉCANISME réutilisable : accroche, structure, dispositifs, rythme,
#   fin, leçons — pas l'anecdote) et "lecture" : mise_en_page (full|split|cards), sous_titres (style), mots_par_groupe,
#   accroche, texte, alternance, fin, ton
python .claude/skills/videomaker-deeplo/scripts/reference.py apply <job> <slug> --ref <ref>          # config du job (zooms, mise en page, sous-titres) + durées des plans
python .claude/skills/videomaker-deeplo/scripts/reference.py synthese                               # toutes les références : accroches, dispositifs, fins, ce qui MANQUE au skill
```
Mesuré : plans (coupes confirmées), coupes par minute, plan médian, 1re coupe, débit de parole, tempo, coupes sur le
temps, volume. On reprend le RYTHME et la grammaire (mise en page, densité de texte, place de l'accroche), jamais le
contenu : ni images, ni musique, ni textes, ni marque de la référence. La vidéo téléchargée reste dans
`jobs/_references/` (analyse seulement). Lien privé ou connexion demandée : demande le fichier.

## Vitrine « Brut / Montage » et démo dans l'appli (montrer ce que fait le skill)
Pour tes propres Reels (ou pour présenter le skill à un client), autour d'un montage DÉJÀ rendu :
```bash
python .claude/skills/videomaker-deeplo/scripts/showcase.py vitrine <job> <slug> [--par "Claude"] [--cta "Clique sur le *lien en bas*"] [--render draft]
python .claude/skills/videomaker-deeplo/scripts/showcase.py demo <job> <slug> --objection "un_monteur: Claude sait pas monter." [--effets "a;b;c"] [--render draft]
python .claude/skills/videomaker-deeplo/scripts/showcase.py portfolio <job> <slug> --lib nom1,nom2 --entete "*Premium* Motion Design"   # ou --videos renders/a.mp4,…
```
- `vitrine` : « Brut » (le rush d'origine, calé sur le montage : il saute à chaque coupe, « ✂ −0,5 s », timecode et barre
  de lecture) à côté de « Montage fait par “Claude” » (avec son son) ; pied d'appel à l'action. Vertical : côte à côte ;
  paysage : l'un sous l'autre. La preuve du travail vaut mieux qu'un discours.
- `demo` : fausse appli d'agent : l'objection d'un sceptique épinglée en haut (accroche), la demande (vignette du rush +
  skill + phrase), « Voilà ton reel ✓ », le montage qui joue, les effets qui se cochent (lus dans le job), Télécharger
  cliqué -> « Enregistré ». Une objection réelle ou plausible et générique, jamais attribuée à une vraie personne.
- `portfolio` : 3 écrans verticaux en quinconce qui jouent en même temps, décalés (toujours quelque chose qui bouge),
  titre fixe ; idéal pour montrer la bibliothèque ou les réalisations d'un client.
- Projets dans `work/vitrine/` et `work/demo/` (check + snapshot là-bas), rendus dans `renders/<slug>_vitrine.mp4` /
  `_demo.mp4`.

# Contrôle avant de montrer, validation client, master, vitesse de rendu

Scripts depuis la racine du projet : `PYTHONUTF8=1 python .claude/skills/videomaker-deeplo/scripts/<x>.py`. `npx` depuis le job :
`( cd <job> && npx --yes hyperframes@0.9.71 <commande> )`.

## Contrôle avant de montrer
0. **`python .claude/skills/videomaker-deeplo/scripts/qa.py <job> <slug>`** sur l'aperçu rendu (le plus récent du job, ou `--video`) : plans trop courts
   (< 0,8 s, coupes confirmées par la couleur ET la structure de l'image), images noires ou figées, volume, trous de son,
   sous-titres lus trop vite (> 22 car/s), durée vs brief, micro-coupures du son (« à revoir » si coupure nette),
   images isolées et première image unie (« info » : nos éclairs de transition sont voulus), **visage couvert** par un
   calque (`face.py` : « à revoir » dès 25 % du visage ou sur les yeux / la bouche -> déplacer la carte ou le bloc, vars
   `top`, ou passer en plein écran). Verdict « à revoir » = tu corriges avant de montrer ; les « infos » se jugent.
   `deliver.py` le relance sur la livraison (clé `controle`) et vérifie la **conformité** de chaque fichier (h264
   yuv420p, taille exacte, cadence fixe, AAC 48 kHz stéréo, son = image, BT.709) : pastille dans `livraison.html`,
   `conforme` dans la réponse.
1. `check` : 0 erreur. Les avertissements `line_unread` sur des groupes mot à mot sont attendus en débit rapide.
2. `snapshot` : visage non couvert, texte dans la zone sûre (ni tout en haut ni dans le dernier quart), pas de
   sous-titres déjà incrustés dans la source (sinon `--mode overlays` ou pas de texte), cadrage 9:16 qui garde la
   personne (sinon `visual.focusX` dans `jobs/<job>/config.json`, 0 à 100).
3. Compte rendu court : durée avant / après, îlots jetés et pourquoi, nombre de sous-titres et de punchs, ce que
   l'utilisateur doit écouter. Ne dis jamais « parfait » : c'est lui qui juge. **Pas de rendu final sans accord.**

## Page de validation client (`review.py`)
`python .claude/skills/videomaker-deeplo/scripts/review.py <job> --qa` -> `work/review/validation.html` : une image à chaque coupe et temps fort, le texte
dit, les sons, les points du contrôle ; le client note ses remarques et copie la liste (`m:ss,d : remarque`) : retrouve
les mots visés dans `work/review/review.json`. Envoyée par l'utilisateur, jamais par toi. Changements reçus ->
corriger, nouvel aperçu, relancer `review.py` ; accord -> `python .claude/skills/videomaker-deeplo/scripts/review.py <job> --valide` (`work/valide.json`),
puis seulement le rendu final.

## Master
`python .claude/skills/videomaker-deeplo/scripts/finalize.py <job> <slug>.mp4` : master -14 LUFS -> `renders/<slug>_final.mp4` + verdict. Annonce `mode`
(linéaire / dynamique / limiteur) et ré-encode seul (256k, 320k, plafond abaissé) si la crête dépasse -1 dBTP après
l'AAC ; « À CORRIGER » seulement si tout a échoué.

## Vitesse de rendu (mesurée le 2026-11-20 sur ce PC : 16 cœurs, Radeon 860M)
~0,18 s par image capturée, quoi qu'on règle : nombre de workers (8 = 16), demi-résolution, capture rapide
(indisponible sous Windows) et rendus simultanés (HyperFrames les exécute l'un après l'autre) ne changent rien.
Seul levier : moins d'images. Aperçus à valider : `-f 15` ou `deliver.py … --apercu` (≈ -40 %) ; livraison finale
toujours à 30 i/s. Ne lance pas plusieurs rendus en parallèle : ça ne va pas plus vite. Compter ~3 à 4 min de rendu
par format pour 30 s de vidéo.

## Brouillons et rendu final
- Aperçus numérotés : `brouillon.py <job> "<ce qui change>" [--rapide]` -> `renders/v<N>-<ce-qui-change>.mp4`, une ligne
  par version dans `work/journal.md` (retrouver à quelle version répond chaque retour). `--liste` pour les voir.
- Livraison (`deliver.py --quality delivery`) : images vidéo extraites en PNG (pas de perte JPEG), plus lent mais plus net.

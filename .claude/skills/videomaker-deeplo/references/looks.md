# Looks (série 3 de l'accueil : « Quel look ? »)

Chaque look est un réglage de `jobs/<job>/config.json` + des options de `build_composition.py`. Les options passées en
ligne de commande sont gardées dans `work/<slug>_build.json` et rejouées à la livraison.

## Tuto cartes (style TikTok « tuto », référence `jobs/_references/tiktok-demande`)
Un mot énorme à la fois, cartes au milieu sur la vidéo floutée, retour au visage net entre deux cartes.
```json
{"visual": {"layout": "cards", "panelTheme": "glass", "cardsBlur": true, "cardsMax": 4},
 "text": {"captionStyle": "geant", "captionTopPct": 68, "syllabes": ["<mot fort dit>"]}}
```
`build_composition.py <job> <slug> --mode captions` ; temps forts dans `work/<slug>_panels.json` (title avec kicker,
icons, image d'une vraie capture `fit: contain`, search, steps, check, face) ; fin : bloc `suivre` (vrai compte) sur un
passage `face`. `panelTheme: "light"` pour des cartes blanches.

## Luxe éditorial (immobilier, hôtellerie : références `exemple-279`, `exemple-279_002`)
Sous-titres sans fine + mot fort en serif, mots géants dans le décor, blocs en verre, barre de progression.
```json
{"visual": {"accentColor": "<or ou couleur de marque>", "progressBar": true},
 "text": {"captionStyle": "editorial", "captionMaxWords": 3, "captionTopPct": 60},
 "camera": {"zooms": false},
 "mots": {"police": "serif", "couleur": "<accent>"}}
```
`work/<slug>_mots.json` : 3 à 5 mots (nom du bien, lieu, marque ; `"sol": true` au sol en plan large) ;
`work/<slug>_motions.json` : `chiffre-verre`, `recherche-verre`, `lieu-photo`, `cartes-3d` (photos réelles), `fin-logo`.
`build_composition.py <job> <slug> --mode captions`. Paire de polices conseillée : editorial ou premium.

## Écran partagé (conseil d'expert, preuves)
Animation en haut, visage en bas, sous-titres sur la jointure. `{"visual": {"layout": "split"}, "text": {"captionMaxWords": 3}}`
+ `work/<slug>_panels.json` (`pack.py draft`). Détails : references/ecran-partage.md.

## Classique (témoignage, ton sobre)
Visage plein écran, sous-titres `pop`, `boite` ou `minimal` selon le ton, plans de coupe (`broll.py`), zooms mesurés.
`{"text": {"captionStyle": "pop"}, "camera": {"zooms": true}}`.

## Ouvertures (« Quelle ouverture ? »)
- Sujet dessiné : `"hook": {"style": "plan|papier|…", "text": "<titre court>", "sub": "…", "art": "work/<slug>_art.svg"}`
  (dessin : references/accroches-dessin.md ; style « plan » = plan d'architecte, idéal immobilier / chantier).
- Nom ou mot-clé derrière la personne : premier mot de `work/<slug>_mots.json` sur le premier mot dit (luxe), ou
  `build_composition.py … --derriere "<titre>" --derriere-mot <mot>`.
- Titre animé : `"hook": {"style": <selon le ton>, "text": "<titre>"}` (styles : references/accroches.md).
- Sans : rien ; la vidéo commence sur la personne.

## Polices (« Quelles polices ? »)
`scripts/polices.py list` (paires : editorial, chaleureux, premium, moderne, creatif, punch, ludique, net),
`scripts/polices.py planche <job> --titre "<accroche>"` (aperçu `work/polices.png` à ouvrir), puis
`scripts/polices.py apply <job> <paire>` (écrit `visual.fontFamily`, `fontFile`, `titleFont`). Polices Google sous
licence libre (OFL), téléchargées une fois avec leur licence dans `vendor/fonts/google/` ; `polices.py get --famille
"<nom>"` pour une autre police Google. La charte du client gagne toujours.

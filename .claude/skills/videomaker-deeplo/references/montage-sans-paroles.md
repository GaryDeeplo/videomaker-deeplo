# Images sans paroles -> montage (journal de chantier, ambiance, événement, produit, voyage)

Scripts depuis la racine du projet : `PYTHONUTF8=1 python .claude/skills/videomaker-deeplo/scripts/<x>.py`.

Le montage par le texte ne s'applique pas : il n'y a pas de mots. Le où vient alors des **mesures** de `footage.py`
(netteté par zone, mouvement, tremblement, luminosité, voix détectée, date de tournage) ; le quoi garder reste ton choix.
```bash
python .claude/skills/videomaker-deeplo/scripts/footage.py scan <job>                       # work/footage.json + planche work/footage/planche.jpg (REGARDE-LA)
python .claude/skills/videomaker-deeplo/scripts/footage.py plan <job> <slug> --duree 30     # premier jet work/<slug>_footage.json, ordre chronologique
#   TU relis : keep (écarte les clips hors sujet ou ratés), ordre, seg (0 = meilleur passage mesuré, 1, 2), timelapse,
#   label (« JOUR 12 » automatique si les dates s'étalent), caption (« La cuisine »), title, series, compare (avant / après).
python .claude/skills/videomaker-deeplo/scripts/add_music.py <job> <slug> --mood upbeat     # ou une voix off : storyboard + voice.py + build_text.py (même slug)
python .claude/skills/videomaker-deeplo/scripts/build_footage.py <job> <slug> [--fit blur] [--style boite]   # puis check + snapshot
```
- **Coupes sur la musique** : avec une musique (`add_music.py`), chaque changement de plan tombe sur un temps de la piste
  (analysé par librosa, gardé dans `work/<slug>_beats.json`) ; avec voix off, la coupe ne glisse que de 0,3 s au plus.
  `"beat_sync": false` dans le plan pour s'en passer. Le pack punch fait de même (0,2 s au plus, les titres restent sur
  leurs mots).
- **Accéléré** : proposé pour un clip long filmé caméra posée (`timelapse: true`, vitesse calculée pour la durée).
- **Ralentis et accélérés** (automatique) : le geste fort d'un plan (pic de mouvement mesuré, pas une coupe du clip)
  passe à 40 % avec images intermédiaires ; un plan où rien ne bouge est accéléré ×1,6. `"ralenti": false` sur un plan
  ou `"ramps": "off"` dans le plan pour s'en passer ; `"speed"` imposé gagne toujours.
- **Stabilisation** : un passage filmé à main levée (tremblement de la caméra mesuré sur le décor, pas sur ce qui bouge
  dans l'image) est stabilisé tout seul (vidstab, deux passes) ; la version stabilisée n'est gardée que si elle tremble
  nettement moins (rapport : `"stabilise": true`). `"stab": true|false` sur un plan pour forcer, `"stab": false` dans le
  plan pour tout couper.
- **Recadrage sur le sujet** : clip paysage en 9:16, la fenêtre se pose sur le visage (YuNet) ou, sans visage, sur ce
  qui bouge ET est net (la personne qui peint, la main qui pétrit) ; plan large sans sujet net : milieu. `"focus": 0.3`
  (0 = gauche, 1 = droite) sur un plan pour imposer, `"focus": false` dans le plan pour recadrer au milieu. Vérifie sur
  le snapshot.
- **Avant / après** : `compare` avec deux clips filmés du même endroit -> volet qui découvre l'après.
- **Reel sans parole (musique + texte)** : `"bubble": "On dirait que tes vidéos sont faites *par IA*"` (ou une liste de
  2-3) sur un plan -> bulles blanches qui arrivent comme des messages sur les temps de la musique, la 2e de l'autre côté ;
  `*mot*` en couleur. Pas de voix : regardable sans le son, traduisible par le seul texte. Fin : bloc `commente-mot`
  (`references/motions-blocs.md`).
- **Série** : `series` (« Journal de chantier · Semaine 4 sur 12 ») en haut, barre de progression ; un job par épisode.
- **Voix off** : les plans changent sur les débuts de phrases (ou sur `word`), sous-titres au style choisi. Sinon musique.
- Un clip où quelqu'un parle (`parole` dans le scan, voix détectée) : `transcribe.py` pour en faire une prise de parole
  ou un repère (« jour 12, on casse le mur »). Le son des clips n'est pas gardé (machines, vent).
- Accroche : `"hook": {…}` dans `work/<slug>_footage.json` (ou `--accroche`), voir `references/accroches.md`.
- Avant que le client filme : `guide.py --metier chantier` (points fixes, plans de 10 s, accéléré posé, phrase repère ;
  `references/guide-tournage.md`).

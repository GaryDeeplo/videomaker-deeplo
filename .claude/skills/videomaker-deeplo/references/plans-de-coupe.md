# Plans de coupe (b-roll) sur un rush

Scripts depuis la racine du projet : `PYTHONUTF8=1 python .claude/skills/videomaker-deeplo/scripts/<x>.py`.

Pour qu'une vidéo face caméra ne reste pas statique : une image illustre ce qui est dit pendant 2 à 5 s, la voix
continue, les sous-titres restent au-dessus.

## En un clic (par défaut quand on te demande « ajoute des plans de coupe »)
1. `python .claude/skills/videomaker-deeplo/scripts/broll.py moments <job> <slug>` ; dans `work/<slug>_broll_suggested.json`, retire les moments sans
   intérêt, mets `"image"` pour ceux qu'illustre un média du client, et écris `"query"` pour les autres : **1 à 2 mots
   anglais concrets et filmables** (« handshake », « parcel delivery ») ; une phrase entière donne des résultats hors sujet.
2. `python .claude/skills/videomaker-deeplo/scripts/broll.py auto <job> <slug> [--kind mix|photo|video]` : cherche, pose la 1re proposition, écrit
   `<slug>_broll.json` et la planche `work/broll/planche.jpg` (jusqu'à 6 propositions par plan : vidéos assez longues
   puis photos).
3. **Regarde la planche** et corrige : `python .claude/skills/videomaker-deeplo/scripts/broll.py pick <job> <slug> <n> <a-f>` ou `none` pour retirer le plan.
   Écarte les autres marques (logos, véhicules siglés), les animations hors ton, les images floues.
4. `build_composition.py`, puis snapshot pendant chaque plan. Montre ensuite l'aperçu à l'utilisateur.

## À la main, plan par plan
1. `python .claude/skills/videomaker-deeplo/scripts/broll.py moments <job> <slug> [--every 7]` : une phrase toutes les ~7 s (pas sous l'accroche ni
   sous un bloc de motion), plus la liste des photos et vidéos de `inbox/`.
2. Pour chaque moment, **d'abord les médias du client** (regarde-les). Sinon une banque :
   `python .claude/skills/videomaker-deeplo/scripts/broll.py search <job> "<requête en anglais>" --orient tall [--video]` télécharge des miniatures que tu
   **regardes** avant de choisir, puis `python .claude/skills/videomaker-deeplo/scripts/broll.py get <job> <id>` (fichier réduit dans `assets/broll/`, crédit
   noté et livré). Source par défaut : **Pixabay** si `PIXABAY_API_KEY` est dans `.env` (photos et vidéos ; `--video`
   pour un plan vidéo de 10 s max, muet ; Pexels pris en charge aussi avec `PEXELS_API_KEY`), sinon Openverse (images
   seulement). Openverse a beaucoup de photos amateurs : écarte tout ce qui est flou, hors sujet, daté ou montre une
   autre marque. Mieux vaut 2 bons plans que 6 moyens ; aucun plan de coupe vaut mieux qu'une image qui fait banque
   d'images ratée. Jamais une image libre présentée comme la boutique, l'équipe ou le produit du client.
3. Garde les moments retenus dans `work/<slug>_broll.json` :
   `[{"word": "Lorsque", "occurrence": 1, "until": "euros", "image": "inbox/vitrine.jpg", "mode": "full"}]`
   — calé sur un mot dit (jamais un timecode), jusqu'au mot `until` (ou `"dur": 2.5`). `mode` : `full` (plein écran,
   léger travelling) ou `carte` (photo encadrée ; sur fond flouté elle se place dans la bande du haut, sinon en haut
   de l'écran). Une vidéo (`.mp4`) passe en muet.
4. `build_composition.py` les pose (whoosh discret à l'entrée) ; vérifie sur `snapshot` pendant chaque plan.

## Vidéo sans rush : pas assez de photos du client
Mets `"query": "<1-2 mots anglais>"` sur les scènes photo / accroche (ou liste, galerie) sans `image`, puis
`python .claude/skills/videomaker-deeplo/scripts/broll.py auto <job> <slug> --storyboard` (avant `build_scenes.py`) : Pixabay remplit `image` (vidéo de fond
pour photo / accroche, photo sinon) et dessine `work/broll/planche.jpg` ; regarde-la, corrige avec
`python .claude/skills/videomaker-deeplo/scripts/broll.py pick <job> <slug> <n> a-f|none`. Les photos du client passent toujours avant, et une image de
banque ne représente jamais la boutique, l'équipe ou le produit du client (ambiance, gestes, matières).

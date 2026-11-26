# Texte à l'écran : sous-titres, styles (dont `geant` et cartes), overlays, punchs

Scripts depuis la racine du projet : `PYTHONUTF8=1 python .claude/skills/videomaker-deeplo/scripts/<x>.py`.

## Décider le texte (`text.json`)
- Mode par défaut `captions` : la plupart regardent sans le son. Styles : `pop` (mots qui surgissent, défaut),
  `karaoke` (groupe entier, mot actif en couleur d'accent), `minimal` (sobre, institutionnel).
- `overlays` (doctrine reel-cut) : ~5 par minute, strictement verbatim ; garde promesses, chiffres, contrastes,
  noms de produit ; jette les connecteurs (« du coup », « en fait »).
- `punch` : max 2 par minute, sur l'affirmation clé, le chiffre fort, le nom du produit ou l'appel à l'action.
  Chaque punch reçoit un whoosh calé sur son pic.
- Un « euh » gardé au dérush n'apparaît jamais dans les sous-titres.

## Styles
- `boite` (le mot dit passe dans une boîte couleur d'accent, style CapCut), `impact` (gros, contour noir, le mot dit
  grossit en couleur d'accent, style Hormozi ; mettre `text.captionMaxWords` à 2 ou 3), `duo` (les nombres ou le mot
  fort du groupe en couleur d'accent).
- `mono` : majuscules machine à écrire, chaque mot dans sa boîte noire, le mot dit en couleur d'accent (ton tech / expert).
- `souligne` (éditorial) : petits, casse normale, les mots à venir en gris, le mot dit en blanc, le mot fort en couleur et
  souligné d'un trait qui se dessine. Ton premium, explicatif.
- `bulle` : chaque groupe dans une bulle blanche arrondie qui arrive comme un message, le mot fort en couleur d'accent
  (assombrie si l'accent est trop clair pour le blanc). Ton conversation, objection, citation.
- `editorial` (immobilier / luxe, serif Didone) : `references/immobilier-luxe.md`. `seam` : automatique en écran partagé.
- `geant` (tutos tech TikTok) : un seul mot énorme à la fois, en casse normale, les mots déjà dits du groupe en petit
  au-dessus ; `text.captionMaxWords` 4, `captionTopPct` ~68. Mot en escalier de syllabes (« IN- / CRO- / YABLE ») :
  `text.syllabes: ["incroyable"]`.
- `--emoji` (ou `text.captionEmoji: true`) : un emoji après les mots-clés (« gagnez » 🏆, « idée » 💡, « bravo » 👏…),
  un au plus par groupe et toutes les 4 s. Le dictionnaire est celui de `suggest_motions.py` (EMOJI).
- Vidéos sans rush : mêmes styles et `--emoji` sur `build_scenes.py` (`--style boite` ou `text.captionStyle`), dans le
  bandeau sombre qui garde le texte lisible sur fond clair.
- Shorts : `shorts.py make … --style <style>` accepte tous ces styles.

## Style `geant` + cartes sur vidéo floutée
Avec `visual.layout: "cards"` + `panelTheme: "light"` + `visual.cardsBlur: true` : cartes blanches au milieu, vidéo
floutée et assombrie derrière, nette sur les temps forts `face` (référence `tiktok-demande`).
Vraie capture d'écran : `{"type": "image", "image": "inbox/ecran.mp4", "fit": "contain"}` (enregistrer un vrai écran,
jamais une fausse interface). En mode cartes, les blocs (`motions.json`, ex. `suivre`) se posent sur un passage `face`.
Un temps fort à moins d'1 s du précédent est écarté : le rapport `panneau` le dit (`pose: false`, `raison`).
Vidéo floutée : une carte reste au plus `visual.cardsMax` s (4 par défaut), puis le visage revient net jusqu'au temps
fort suivant (« retour auto » dans le rapport) ; les cartes arrivent en rebond + flou, dérivent un peu, sortent en flou.
Piles de cartes d'outils sur la vidéo floutée : `references/motions-blocs.md`.

## Sous-titres qui évitent le visage
Vertical plein cadre, actif dès qu'un visage est vu sur ≥ 15 % des images : sous le menton, sinon au-dessus de la tête,
sinon en bas sur fond sombre, dans la zone sûre de la plateforme (`--plateforme tous|reels|tiktok|shorts` sur
`build_composition.py`, ou `text.platform`). `--no-visage` (ou `text.captionFace: false`) revient à `captionTopPct`.
Détections en cache dans `work/<vidéo>_visages.json` (partagé avec `reframe.py`) ; positions des calques dans
`work/<slug>_calques.json` ; `python .claude/skills/videomaker-deeplo/scripts/face.py <job> <slug> --placer` montre les positions.

## Réglages des sous-titres (mise à jour)
- Sans text.captionMaxWords, la taille des groupes suit le style (impact 3, geant 4, editorial 5, karaoke / souligne / minimal 6, bulle 8, sinon 4) ; plafond en caractères par style (text.captionMaxChars pour forcer). ? et ! gardés (espace insécable), « de la », « 20 % », « 4 à 7 » jamais coupés en fin de ligne, nombres entiers (« 50 000 »). Taille mesurée (2 lignes, une taille par vidéo).
- Fond clair sous un sous-titre (ciel, mur blanc) : mesuré groupe par groupe, voile sombre ou encre sombre (editorial) automatiques (text.captionLight: false pour couper, text.captionLightAt: 170). Accent trop sombre sur vidéo sombre : éclairci tout seul.
- text.editorialColor: "degrade" -> mot fort editorial en dégradé clair -> accent.
- En 1:1 / 16:9, sous-titres ancrés en bas (8 % de la hauteur).
- Chaque monteur écrit work/<slug>_build.json {"script", "args": [...]} : les options validées, rejouées par deliver.py dans chaque format.
- Polices : visual.fonts, visual.fontFile (police variable) et visual.titleFont {family, file, weight} (titres, accroche, grands chiffres), chargés par fonts.py pour tous les monteurs.
- build_footage / build_scenes : --style par défaut = text.captionStyle.

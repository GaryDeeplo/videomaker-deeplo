# Écran partagé, types de temps forts, visuels

Scripts depuis la racine du projet : `PYTHONUTF8=1 python .claude/skills/videomaker-deeplo/scripts/<x>.py`.
Objets (carte, calendrier, devis…) : `references/objets.md`. Ces temps forts servent aussi à l'explainer et à
l'infographie (`references/packs.md`).

## Pack « écran partagé » (layout split) : animation en haut, visage en bas
Le rendu « pro » des Reels d'experts : la moitié haute est un panneau animé (fond presque noir avec une lueur de
l'accent, grain, sol en perspective qui avance, reflet), la moitié basse le visage, les sous-titres (2-3 mots, mot
fort dans une boîte d'accent) sur la jointure. Pour un rush face caméra vertical.
1. `jobs/<job>/config.json` : `{"visual": {"layout": "split"}, "text": {"captionMaxWords": 3}}` (ou `--layout split`),
   AVANT `build_text.py`.
2. Écris `work/<slug>_panels.json` (`python .claude/skills/videomaker-deeplo/scripts/panel.py suggest <job> <slug>` donne un squelette, une entrée par
   phrase ; `pack.py draft` un premier jet plus riche, voir plus bas) : un temps fort par idée, posé sur le MOT qui
   l'introduit, visible jusqu'au suivant. Types de base : `title` (texte court avec le *mot fort* en italique serif,
   `mark` : étincelle, `flash` : éclair), `check` (liste qui se coche + tampon), `stat` (chiffre qui défile + libellé),
   `search` (fenêtre, frappe, résultats), `image` (photo du client ou de banque dans un cadre lumineux), `steps`
   (étapes 1-2-3 qui s'allument). `tag` : étiquette de chapitre en haut à droite (2-3 mots en capitales :
   « LE PROBLÈME », « ÉTAPE 2 »). Détails dans `scripts/panel.py`.
   Règles : une idée toutes les 2 à 6 s (rien de statique plus longtemps), textes de 2 à 6 mots, la même chose que
   ce qui est dit (jamais une info en plus), chiffres / avis / résultats uniquement réels.
   Sans `panels.json` : un titre par phrase forte (overlays de text.json), correct mais moins riche.
3. `build_composition.py` (style de sous-titres `seam` automatique). Les blocs posés par-dessus (`motions.json`) sont
   ignorés en écran partagé : leur idée va dans un temps fort. Les plans de coupe s'affichent dans le panneau.
   Formats 1:1 et 16:9 : retour à la mise en page classique.
Inspiré des Reels « split screen » d'experts tech : on reprend les principes (panneau, jointure, typo mêlée, interfaces
qui changent d'état), jamais leurs visuels ni leurs contenus.

## Premier jet automatique (`pack.py draft`)
Une fois la voix ou le dérush faits (`build_text.py`) : `python .claude/skills/videomaker-deeplo/scripts/pack.py draft <job> <slug>` écrit le premier jet des
temps forts (`<slug>_panels.json` ou `<slug>_punch.json`, ou `_draft.json` s'il en existe déjà un) : chiffre -> stat
ou prix, « pas de / ni » -> liste avec picto interdit, d'abord / puis / enfin -> étapes, appel à l'action -> titre +
picto, nom concret -> image (requête anglaise), médias de `inbox/` placés avant toute banque, chapitres (avant /
pendant / après / à vous) pour l'explainer ; maquettes quand la phrase en parle (réserver -> formulaire, Google ->
recherche, classement, messages -> chat, audit -> progression, site -> navigateur, 4 outils et plus -> étoile
d'icônes) ; « numéro 3 », « le deuxième conseil » -> en-tête « 3 SUR 5 ».
Infographie : `pack.py draft <job> <slug> --pack infographie` écrit `<slug>_data.json` (nombres en chiffres ou en
lettres : « mille huit cents », « soixante-quatre pour cent »). **C'est un brouillon : relis-le** — textes courts et
naturels, vrais chiffres, un visuel un temps fort sur deux, `TODO` remplacés (requêtes, horaires réels) — puis fetch /
pick et le build du pack.

## Maquettes d'interface, liste « 1 sur 5 », thème clair, cartes sur le visage
Ce qui donne l'air « vrai » : l'écran montre l'outil ou le parcours du client en train de se faire. Types de temps forts
en plus (détails et exemple JSON dans `scripts/panel.py`) :
- `form` : formulaire dans un navigateur qui se remplit (main qui clique, texte qui se tape, bouton « Réservé ✓ ») ;
- `chat` : bulles qui arrivent (« … » le temps d'écrire) ; `search` : recherche qui se tape, `highlight` = ligne du client ;
- `rank` : classement, la ligne du client (`highlight`) monte à la place `to` ; `progress` : commande + barre + compteur ;
- `hub` : logo ou picto au centre, outils / services autour, reliés par des traits ; `browser` : maquette de site (ou
  capture `image`) annotée de défauts en rouge (`notes`, `on`: title | sub | button | tile1-3, ou x / y sur une capture).
- `funnel` : entonnoir du parcours client, l'étape qui perd du monde (`leak`) en rouge + étiquette ; `chart` : courbe dans
  une carte ; `feed` : flux « EN DIRECT » (commandes, avis, messages qui arrivent) ; `palette` : nuancier + « Aa » de la charte.
- Contenu tech (tes propres vidéos aussi) : `repo` (carte de dépôt GitHub, étoiles lues en direct), `code` (avant / après,
  lignes barrées puis nouvelles en vert), `paths` (lignes emmêlées, le chemin simple en accent). **Vrais logos d'outils** :
  `"icon": "logo:claude"` (Simple Icons, CC0 ; usage informatif des marques, jamais pour faire croire à un partenariat).
- `settings` : panneau de réglages d'un outil (« Instructions personnalisées ») où la consigne exacte se tape, interrupteur,
  bouton puis « ✓ Enregistré » (`"action": "copy"` -> « Copié ») : la ressource copiable, prétexte du « Commente : MOT ».
- `post` : publication recréée (X, LinkedIn, Threads) comme source : texte qui se révèle, compteurs, cœur. **Texte exact
  et daté d'une vraie publication** uniquement, jamais une citation inventée ni prêtée à quelqu'un.
- `loupe` : mur de texte illisible (CGU, contrat, devis, ou `text` du client) ; une loupe le parcourt et s'arrête sur `find`,
  qui passe en couleur + étiquette (`label`) : le problème rendu visible.
- `flap` et les objets (`map`, `calendar`, `timeline`, `invoice`, `revenue`, `clock`, bloc `scan-visage`) :
  `references/objets.md`.
- **Pack éditorial** (ton premium, inspiré des pubs « montage fait par IA ») : `"kicker": "TEMPS DE CRÉATION"` sur un
  temps fort -> sur-titre mono en capitales au-dessus ; titres courts à point final (« Le montage *automatisé.* ») ;
  `"fond": "papier"` -> ce temps fort sur papier quadrillé clair (alternance sombre / papier, relance l'attention) ;
  `visual.panelThread: true` -> fil conducteur : une courbe d'accent traverse tout le panneau et avance avec la vidéo ;
  `visual.panelHud: true` -> repères mono dans les coins (nom `hudLabel`, timecode, temps fort n / N, `hudNote`) ;
  avec les sous-titres `souligne`.
- **Alternance plein écran / écran partagé** : `{"type": "face", "word": "…"}` -> visage plein écran (coupe franche)
  jusqu'au temps fort suivant, qui ramène le panneau. Une phrase perso, une émotion, une conclusion : face ; une preuve,
  une liste, un outil : panneau. Les sous-titres suivent (jointure / bas de l'image).
- Ces maquettes marchent aussi dans l'**infographie** (`build_data.py`) : même JSON dans `work/<slug>_data.json`.
- **Format liste** : `"list": {"n": 1, "of": 5, "name": "Perplexity", "icon": "search"}` sur les temps forts d'un même élément ->
  en-tête fixe « 1 SUR 5 · Nom » relié par un trait (top conseils, erreurs, outils, étapes) ; `"style": "tabs"` -> rangée
  d'onglets numérotés 1 2 3 4.
- **Thème clair** de l'écran partagé : `visual.panelTheme: "light"` ou `--panel-theme light` (fond blanc cassé, cartes à
  ombre douce). **Cartes sur le visage** : `visual.layout: "cards"` ou `--layout cards` (vidéo plein écran, temps forts en
  cartes blanches en haut) — seulement si le visage est au centre ou plus bas dans l'image (regarde le snapshot : si les
  cartes couvrent les yeux, repasse en écran partagé). Cartes sur vidéo floutée (style `geant`) :
  `references/sous-titres.md`.
Contenu réel uniquement : un classement, un formulaire ou un chat illustre ce qui est dit (jamais de faux avis, de faux
concurrent nommé ni de vraie conversation client sans accord) ; noms de concurrents remplacés par « Concurrent A ».

## Visuels dans les temps forts (écran partagé ET explainer) : à mélanger, pas que du texte
Un temps fort sur deux devrait montrer quelque chose : picto, vraie photo ou vidéo, emoji animé.
- **Pictos** (Lucide, ISC, ~1 500 sur lucide.dev/icons, téléchargés à la demande dans `vendor/lucide/`) : `"icon"` sur un
  `title` (grand picto qui flotte sous le titre) ; items `{"text": "…", "icon": "ban"}` dans `check` et `steps` ; type
  `icons` (2 à 6 pastilles qui tombent avec un rebond : `{"icon": "droplet-off", "label": "Pas d'eau"}`).
  Noms en anglais (clock, heart, calendar-check, eye-off, sparkles, package, message-circle, hand, ban…).
- **Vraie photo ou vidéo** : `{"type": "image", "image": "inbox/x.mp4 | photo.jpg", "caption": "…"}` (vidéos du client,
  de son site, ou de banque). Sans fichier : `"query": "1-2 mots anglais"` puis `python .claude/skills/videomaker-deeplo/scripts/panel.py fetch <job> <slug>`
  (Pixabay, vidéos assez longues puis photos, planche `work/broll/planche.jpg`) ; corrige avec `panel.py pick`.
  Une image de banque illustre (gestes, matières, ambiance), jamais présentée comme le client, son équipe ou ses résultats.
  Vraie capture d'écran : `{"type": "image", "image": "inbox/ecran.mp4", "fit": "contain"}` (enregistrer un vrai écran,
  jamais une fausse interface).
- **Emoji animé** : `"lottie": {"name": "valide", "x": 50, "y": 66, "size": 34}` sur n'importe quel temps fort (24 prêts,
  voir Lottie dans `references/motions-blocs.md` ; crédit Noto ajouté tout seul).

## Cartes et temps forts (mise à jour)
- Cartes : visual.panelTheme "glass" (layout cards, + cardsBlur) = cartes en verre dépoli ; "side": "left" | "right" sur un temps fort la pose d'un côté, tournée en 3D. Entrées variées (pivot, rideau, zoom) à tour de rôle, sortie dans l'autre sens, dérive au repos.
- Temps forts : "word" peut être une suite de mots ; un mot introuvable est signalé dans le rapport (pose: false) : corrige le mot.
- stat : "from": 12 (compte de 12 à value), "style": "glass" (chiffre en dégradé), "dim": "3 ha" (cote fléchée) ; le chiffre tient toujours sur une ligne.

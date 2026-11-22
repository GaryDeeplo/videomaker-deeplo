---
name: videomaker-deeplo
description: >-
  VideoMakerDeeplo (Deeplo Video Maker) : monte une vidéo prête à poster pour une entreprise, un indépendant ou un
  créateur (contenu tech compris), dans HyperFrames, à partir de rushs face caméra, de clips sans paroles (chantier,
  ambiance, plats, événement), de photos, de chiffres, de textes ou d'idées. Accueil en questions-réponses, dérush par
  le texte (meilleures prises, blancs et « euh » coupés), rendu choisi tout seul (écran partagé, explainer papier,
  actu / punch, infographie chiffrée, journal de chantier) avec animations calées sur les mots dits (maquettes
  d'interface, listes « 1 sur 5 », vrais logos d'outils, chiffres), accroches animées en 10 styles, sous-titres mot à
  mot (7 styles), voix off Gemini gratuite ou enregistrement, musique libre de droits, charte du client, formats
  9:16 / 1:1 / 16:9, shorts, traductions, mises à jour. Utiliser dès que l'utilisateur veut « monter une vidéo »,
  « faire un reel », « dérusher », « mettre des sous-titres », « couper les blancs », « faire une vidéo pour <client> »,
  « journal de chantier », « montage de mes clips », « une infographie », ou dépose un rush, ou tape /videomaker-deeplo.
---

# VideoMakerDeeplo (Deeplo Video Maker)

Scripts dans `scripts/` (lance-les avec `PYTHONUTF8=1 python scripts/<x>.py`). Chaque script répond en une ligne
JSON. Config : `config.default.json`, écrasée par `brands/<marque>/brand.json` (clé `video`), puis par
`jobs/<job>/config.json`. 

## Accueil (à chaque chargement du skill)

1. `python scripts/onboard.py status` (silencieux, une seconde) : installation, clés, marques, projets récents,
   réglages connus (par marque et par parcours), dernières vidéos / photos du dossier Téléchargements. Dès que la
   marque et le parcours sont connus : `onboard.py status --marque <m> --parcours rush|sans-rush|shorts`.
2. `installe` faux -> propose d'abord l'installation (`INSTALL.md`), rien d'autre.
   `mise_a_jour.maj` vrai -> une ligne (« Une mise à jour du skill est disponible : <2-3 nouveautés> ») et une question à
   choix « Installer maintenant (recommandé) » / « Plus tard » ; si oui : `python scripts/update.py install` puis
   `check.py` (vos chartes, projets, clés et motions ajoutées ne sont jamais touchés). Ne repose pas la question dans la
   même session. Hors ligne : rien à dire.
3. **La demande dit déjà quoi faire, avec quels fichiers ET pour quoi** (« monte ce rush pour un Reel de 30 s pour la Boulangerie Martin qui
   pousse la nouvelle offre ») -> pas de questions : complète le reste avec les réglages connus de CETTE marque et de CE
   parcours, écris le brief, annonce-le en une ligne et lance. Il manque le pourquoi -> tour 3 seulement.
4. **Demande vague** (« /videomaker-deeplo », « je veux faire une vidéo ») -> questions à choix (outil AskUserQuestion), **4 tours
   maximum** (2 pour le quoi / quels fichiers, 2 pour le brief), option recommandée en premier, jamais de question dont
   la réponse est déjà dans la demande ou les réglages connus. Demande précise mais sans brief (« monte ce rush pour
   la Boulangerie Martin ») : pose seulement le tour 3, en une fois, puis lance.
   - Tour 1 (ensemble) : **Quoi ?** (monter une vidéo filmée · vidéo à partir de photos et d'un texte · découper une
     longue vidéo en shorts · reprendre « <projet récent> » s'il y en a un) et **Pour quelle marque ?** (les marques
     de `brands/`, « nouvelle marque », « sans marque »). Les autres demandes (plusieurs clips, traduire, lot,
     couverture, planning, guide de tournage) passent par « Autre ».
   - Tour 2 (ensemble, selon le parcours) : **Les fichiers ?** (propose les fichiers récents de Téléchargements en
     options ; sinon l'utilisateur colle un chemin dans « Autre ») · **Où sera-t-elle publiée ?** (Reels / TikTok
     9:16 · tous les formats · YouTube 16:9) · **Quel rendu ?** (« comme la dernière fois pour <marque> » si des
     réglages existent pour cette marque et ce parcours, sinon
     « je choisis pour vous (recommandé) », style dynamique boîte + plans de coupe, style sobre minimal).
   - Vidéo sans rush : au tour 2, remplace « Les fichiers ? » par **le message** (« Décrivez en une phrase ce que la
     vidéo doit dire » via « Autre ») et **les photos** (dossier, ou « je n'en ai pas : images d'ambiance Pixabay »).
   - **Tour 3, le brief** (toujours, sauf si la demande y répond déjà) — 4 questions ensemble, chacune avec
     « Je ne sais pas, choisis pour moi (recommandé) » en premier :
     **Objectif ?** (vendre un produit ou une offre · faire connaître l'entreprise · recruter · informer / conseiller ·
     fidéliser) · **Pour qui ?** (particuliers · professionnels · candidats · clients actuels) · **Durée ?** (15 s ·
     30 s · 60 s · aussi long que le contenu le mérite) · **Ton ?** (dynamique · chaleureux · haut de gamme · sobre).
   - **Tour 4, les précisions** (si utile) : **Que doit faire la personne après ?** (réserver / acheter en ligne ·
     venir en boutique · écrire en message · appeler · suivre le compte ; lien ou numéro via « Autre ») ·
     **À ne pas oublier ?** (une promo, une date, un prix, un nom ; via « Autre », sinon « rien de spécial ») ·
     **À éviter ?** (prix, concurrents, un sujet sensible ; sinon « rien ») · **Langues ?** (FR · FR + NL · FR + EN).
   Écris le tout : `python scripts/onboard.py brief <job> objectif=… public=… duree=… ton=… cta="…" mentions="…"
   eviter="…" langues=…` (`work/brief.json`) et **relis-le à chaque décision** :
   | Brief | Effet sur le montage |
   |---|---|
   | durée | dérush : garde les phrases les plus fortes pour tenir la durée (dis ce que tu as retiré) ; sans rush : nombre de scènes |
   | objectif « vendre » | accroche sur le bénéfice, bloc `bouton-cta` ou `tarif` sur l'offre (vraie), fin sur l'appel à l'action |
   | objectif « recruter » | modèle recrutement, bandeau nom, appel « postulez » ; « informer » : sobre, `etapes` / `points` |
   | public « pros » | vouvoiement dans le post, style `minimal` ou `duo` ; « particuliers » : tutoiement possible si la marque le fait |
   | ton dynamique | musique upbeat / energetic, style `boite` ou `impact`, plans de coupe, emojis |
   | ton chaleureux | musique acoustic, style `pop`, plans de coupe doux ; « haut de gamme » : cinematic / ambient, `minimal`, pas d'emoji |
   | ton sobre | musique inspiring basse ou aucune, `minimal`, pas d'emoji ni de sticker |
   | cta | outro (`info`), texte du post (`cta`), bloc `bouton-cta` en fin de vidéo |
   | mentions | doivent apparaître à l'écran ET dans le post ; si la vidéo ne les dit pas, demande où les placer |
   | à éviter | jamais à l'écran, dans le post, les plans de coupe ni les suggestions de motion |
   | langues | `translate.py` pour chaque langue en plus, posts traduits |
   Le brief appartient à CETTE vidéo : il n'entre dans les réglages de la marque que si l'utilisateur le veut (même
   question à choix qu'au point 5 ; par exemple « public » et « ton » sont souvent stables pour une marque).
5. Récapitule en une ligne (« Reel 9:16 pour la Boulangerie Martin, style boîte, musique upbeat, plans de coupe : je lance. »)
   et lance le parcours. Ensuite, plus de questions de réglage : on montre un aperçu et l'utilisateur corrige en
   français.
   **Les réglages connus ne sont que des valeurs par défaut.** La demande du moment gagne toujours (« cette fois en
   16:9 pour YouTube », « plus sobre ») : tu l'appliques à CETTE vidéo sans toucher aux réglages. Ils sont rangés par
   marque et par parcours : ceux d'un Reel de la Boulangerie Martin ne s'appliquent ni à une autre marque ni à une vidéo sans rush.
   Enregistrement seulement après accord : quand l'utilisateur valide l'aperçu et que ses choix diffèrent des
   réglages connus (ou qu'il n'y en a pas), une question à choix « Je garde ces réglages pour les prochaines vidéos
   <marque> ? » (« Oui, pour <marque> » / « Non, juste pour cette vidéo »). Si oui :
   `onboard.py profil --marque <m> --parcours <p> format=… style=… reseaux=… musique=… broll=oui|non`.
   Une demande ponctuelle (« pour Noël », « juste celle-ci ») ne s'enregistre jamais.
6. Vidéo sans rush : demande **d'où vient la voix off** (question à choix, sauf si déjà dit) — « voix de synthèse
   naturelle (recommandé) » (Gemini, gratuit) · « j'ai un enregistrement » (mémo vocal, micro, ou une vidéo dont on garde
   le son : chemin via « Autre ») · « pas de voix, musique et textes seulement ». Ni clé Gemini ni Fish -> dis-le en une
   ligne (voix locale de test) avant de lancer.
7. **Le pack (rendu), choisi tout seul** : dès que les fichiers et le brief sont là,
   `python scripts/pack.py choose <job> [--slug s] --demande "<la demande>"` conseille un pack d'après les fichiers
   (rush où l'on parle = écran partagé ; clips sans paroles = montage), des chiffres dans le propos (= infographie), le brief (informer / conseiller = explainer ; vendre, annoncer, ≤ 20 s = punch ;
   ton sobre ou haut de gamme = classique) et ce qui est dit. Annonce-le en une ligne dans le récap du point 5
   (« écran partagé : animation en haut, visage en bas ») ; tu ne poses la question que si deux packs se valent
   vraiment. L'utilisateur peut toujours dire « plutôt en punch ».
   Une fois la voix ou le dérush faits (`build_text.py`) : `python scripts/pack.py draft <job> <slug>` écrit le
   premier jet des temps forts (`<slug>_panels.json` ou `<slug>_punch.json`, ou `_draft.json` s'il en existe déjà
   un) : chiffre -> stat ou prix, « pas de / ni » -> liste avec picto interdit, d'abord / puis / enfin -> étapes,
   appel à l'action -> titre + picto, nom concret -> image (requête anglaise), médias de `inbox/` placés avant toute
   banque, chapitres (avant / pendant / après / à vous) pour l'explainer ; maquettes quand la phrase en parle
   (réserver -> formulaire, Google -> recherche, classement, messages -> chat, audit -> progression, site ->
   navigateur, 4 outils et plus -> étoile d'icônes) ; « numéro 3 », « le deuxième conseil » -> en-tête « 3 SUR 5 ».
   Infographie : `pack.py draft <job> <slug> --pack infographie` écrit `<slug>_data.json` (nombres en chiffres ou en
   lettres : « mille huit cents », « soixante-quatre pour cent »). **C'est un brouillon : relis-le** —
   textes courts et naturels, vrais chiffres, un visuel un temps fort sur deux, `TODO` remplacés (requêtes, horaires
   réels) — puis fetch / pick et le build du pack.

## Quel parcours ?

| Demande | Parcours | Point de départ |
|---|---|---|
| Le client va filmer lui-même | « guide de tournage » | `guide.py` (à lui envoyer AVANT) |
| Rush face caméra, interview courte | « rush → reel » | `transcribe.py` |
| Clips sans paroles (chantier, ambiance, plats, événement, produit, voyage) | « montage » | `footage.py scan` |
| Plusieurs petits clips (téléphone) | « plusieurs rushs » puis « rush → reel » | `multi.py list` |
| Expliquer un service / un déroulé, sans rush | « explainer papier » | `build_explainer.py` |
| Photos + idée / texte, pas de rush | « sans rush » | un modèle de `templates/` (promo, boutique, recrutement, témoignage, produit) |
| Longue vidéo → plusieurs reels | « shorts » | `shorts.py sentences` |
| Même vidéo dans une autre langue | « versions traduites » | `translate.py export` |
| Plusieurs vidéos × langues × formats | « lot » | `templates/lot-exemple.json` + `batch.py plan` |
| Planning de publication d'un lot | « calendrier » | `planning.py` |
| Annonce / promo / récap rythmée | « actu / punch » | `build_punch.py` |
| Bilan, étude de cas, chiffres clés | « infographie » | `build_data.py` |

Toujours : charte du client dans `brands/` (sinon la créer depuis `brands/_exemple/`), recherche dans la bibliothèque
avant de créer, `check` + `snapshot` avant de montrer, pas de rendu final sans accord.

### Guide de tournage (avant que le client filme)
`python scripts/guide.py [--job <job>] --client "<nom>" --metier boutique|artisan|restaurant|service|recrutement
[--brand <marque>] [--envoi "<lien de dépôt>"] [--contact "<qui appeler>"] [--format vertical|horizontal]`
-> `guide-tournage.html` (job : `renders/`, sinon `dist/`) : matériel, cadrage, lumière, son, comment parler et se
tromper sans stress, plan de script du métier à compléter avec SES mots et SES vrais chiffres, plans d'illustration à
filmer, autorisations, envoi des originaux (jamais par WhatsApp). Couleur d'accent de la charte. Lisible sur téléphone,
imprimable en PDF. Tu ne l'envoies pas toi-même : l'utilisateur le transmet.

## La règle qui ne se négocie pas (reprise de reel-cut)

> **Tu n'écris JAMAIS un timestamp.** Le OÙ couper vient des outils (mots horodatés + silences mesurés) ;
> le QUOI garder vient de ton jugement. Dans les JSON, tu n'écris que `keep`, `punch`, `reason`, et tu peux
> corriger l'orthographe d'un mot (`w`), jamais ses temps.

## Parcours « rush → reel sous-titré »

```bash
python scripts/new_job.py "<client>" "<sujet>" [--brand <dossier>] --rush <fichier>   # crée jobs/<date>-<client>-<sujet>/
python scripts/transcribe.py <job> <rush> [--from S --to S]    # local par défaut (~2-3x temps réel), --engine groq si accord
python scripts/cut_plan.py <job> <slug> [--min-silence 0.45]   # îlots de parole, bords dans les silences
#   TU décides : keep / reason dans work/<slug>_plan.json
python scripts/build_cut.py <job> <slug> [--denoise]           # assets/<slug>_cut.mp4 + map.json (voix à -16 LUFS)
python scripts/build_text.py <job> <slug>                      # captions + overlays candidats + punchs proposés
#   TU vérifies : orthographe des captions, keep / punch / reason des overlays
python scripts/add_music.py <job> <slug> --mood upbeat         # ou --id <piste>, --file <fichier client>, --url <YouTube/SoundCloud>
python scripts/broll.py moments <job> <slug>                  # plans de coupe : moments candidats (facultatif, voir plus bas)
python scripts/build_composition.py <job> <slug> [--style pop|karaoke|minimal|boite|impact|duo|mono] [--emoji] [--mode captions|overlays|both]
cd <job> && npx --yes hyperframes@0.9.71 check                 # 0 erreur exigée
npx --yes hyperframes@0.9.71 snapshot --at T1,T2,T3            # REGARDE la planche avant de montrer quoi que ce soit
npx --yes hyperframes@0.9.71 preview                           # Studio pour l'utilisateur
npx --yes hyperframes@0.9.71 render -q draft -w 8 -f 15 -o renders/<slug>_draft.mp4   # aperçu (15 i/s : -40 %)
npx --yes hyperframes@0.9.71 render -q delivery -w 8 -o renders/<slug>.mp4        # final, après accord
python scripts/finalize.py <job> <slug>.mp4                    # master -14 LUFS -> renders/<slug>_final.mp4 + verdict
```

### Pack « écran partagé » (layout split) : animation en haut, visage en bas
Le rendu « pro » des Reels d'experts : la moitié haute est un panneau animé (fond presque noir avec une lueur de
l'accent, grain, sol en perspective qui avance, reflet), la moitié basse le visage, les sous-titres (2-3 mots, mot
fort dans une boîte d'accent) sur la jointure. Pour un rush face caméra vertical.
1. `jobs/<job>/config.json` : `{"visual": {"layout": "split"}, "text": {"captionMaxWords": 3}}` (ou `--layout split`),
   AVANT `build_text.py`.
2. Écris `work/<slug>_panels.json` (`python scripts/panel.py suggest <job> <slug>` donne un squelette, une entrée par
   phrase) : un temps fort par idée, posé sur le MOT qui l'introduit, visible jusqu'au suivant. Types : `title`
   (texte court avec le *mot fort* en italique serif, `mark` : étincelle, `flash` : éclair), `check` (liste qui se
   coche + tampon), `stat` (chiffre qui défile + libellé), `search` (fenêtre, frappe, résultats), `image` (photo du
   client ou de banque dans un cadre lumineux), `steps` (étapes 1-2-3 qui s'allument). `tag` : étiquette de chapitre
   en haut à droite (2-3 mots en capitales : « LE PROBLÈME », « ÉTAPE 2 »). Détails dans `scripts/panel.py`.
   Règles : une idée toutes les 2 à 6 s (rien de statique plus longtemps), textes de 2 à 6 mots, la même chose que
   ce qui est dit (jamais une info en plus), chiffres / avis / résultats uniquement réels.
   Sans `panels.json` : un titre par phrase forte (overlays de text.json), correct mais moins riche.
3. `build_composition.py` (style de sous-titres `seam` automatique). Les blocs posés par-dessus (`motions.json`) sont
   ignorés en écran partagé : leur idée va dans un temps fort. Les plans de coupe s'affichent dans le panneau.
   Formats 1:1 et 16:9 : retour à la mise en page classique.
Inspiré des Reels « split screen » d'experts tech : on reprend les principes (panneau, jointure, typo mêlée, interfaces
qui changent d'état), jamais leurs visuels ni leurs contenus.

### Accroches animées par style (3 s d'ouverture)
Dix styles pour le même titre : `papier` (couches de papier, lettres qui se posent), `plan` (blueprint : grille, titre au
trait, cote), `pate` (pâte à modeler qui rebondit), `neon` (synthwave : soleil rayé, sol quadrillé, néon qui clignote),
`aquarelle` (taches qui diffusent, titre au pinceau), `pixel` (à-coups, ombre en blocs), `isometrique` (blocs qui montent),
`mosaique` (carreaux qui se retournent), `encre` (coup de pinceau, sceau rouge), `relief` (titre extrudé qui pivote).
Blocs `library/block/accroche-<style>` (variables text, sub, accent, bg, ink, font ; générés par `_make_hook_blocks.py`).
- Rush : `build_composition.py … --accroche neon --accroche-texte "…"` ou `"hook": {"style": "neon", "text": "…", "sub": "…"}`
  dans la config ; remplace l'intro de marque, la vidéo démarre sous son volet de sortie.
- Images sans paroles : `"hook": {…}` dans `work/<slug>_footage.json` (ou `--accroche`) ; le titre ne s'affiche pas deux fois.
- Vidéo sans rush : une scène `{"kind": "block", "block": "accroche-plan", "vars": {"text": "…"}, "hold": 3}`.
Choix du style selon le ton : chantier / artisan -> `plan`, enfant / food fun -> `pate`, tech / soirée -> `neon` ou
`relief`, haut de gamme / bien-être -> `aquarelle` ou `encre`, jeu / rétro -> `pixel`, chiffres / immobilier ->
`isometrique`. Pour un sujet précis (le plat signature, le bâtiment), dessine-le en SVG dans une copie du bloc.

### Maquettes d'interface, liste « 1 sur 5 », thème clair, cartes sur le visage
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
- Ces maquettes marchent aussi dans l'**infographie** (`build_data.py`) : même JSON dans `work/<slug>_data.json`.
- **Format liste** : `"list": {"n": 1, "of": 5, "name": "Perplexity", "icon": "search"}` sur les temps forts d'un même élément ->
  en-tête fixe « 1 SUR 5 · Nom » relié par un trait (top conseils, erreurs, outils, étapes) ; `"style": "tabs"` -> rangée
  d'onglets numérotés 1 2 3 4.
- **Thème clair** de l'écran partagé : `visual.panelTheme: "light"` ou `--panel-theme light` (fond blanc cassé, cartes à
  ombre douce). **Cartes sur le visage** : `visual.layout: "cards"` ou `--layout cards` (vidéo plein écran, temps forts en
  cartes blanches en haut) — seulement si le visage est au centre ou plus bas dans l'image (regarde le snapshot : si les
  cartes couvrent les yeux, repasse en écran partagé).
Contenu réel uniquement : un classement, un formulaire ou un chat illustre ce qui est dit (jamais de faux avis, de faux
concurrent nommé ni de vraie conversation client sans accord) ; noms de concurrents remplacés par « Concurrent A ».

### Visuels dans les temps forts (écran partagé ET explainer) : à mélanger, pas que du texte
Un temps fort sur deux devrait montrer quelque chose : picto, vraie photo ou vidéo, emoji animé.
- **Pictos** (Lucide, ISC, ~1 500 sur lucide.dev/icons, téléchargés à la demande dans `vendor/lucide/`) : `"icon"` sur un
  `title` (grand picto qui flotte sous le titre) ; items `{"text": "…", "icon": "ban"}` dans `check` et `steps` ; type
  `icons` (2 à 6 pastilles qui tombent avec un rebond : `{"icon": "droplet-off", "label": "Pas d'eau"}`).
  Noms en anglais (clock, heart, calendar-check, eye-off, sparkles, package, message-circle, hand, ban…).
- **Vraie photo ou vidéo** : `{"type": "image", "image": "inbox/x.mp4 | photo.jpg", "caption": "…"}` (vidéos du client,
  de son site, ou de banque). Sans fichier : `"query": "1-2 mots anglais"` puis `python scripts/panel.py fetch <job> <slug>`
  (Pixabay, vidéos assez longues puis photos, planche `work/broll/planche.jpg`) ; corrige avec `panel.py pick`.
  Une image de banque illustre (gestes, matières, ambiance), jamais présentée comme le client, son équipe ou ses résultats.
- **Emoji animé** : `"lottie": {"name": "valide", "x": 50, "y": 66, "size": 34}` sur n'importe quel temps fort (24 prêts,
  voir Lottie plus bas ; crédit Noto ajouté tout seul).

### Pack « explainer papier » : vidéo sans rush façon fiche pratique
Pour expliquer un service, un déroulé, une offre : carte papier à ombre franche sur fond à carreaux (couleurs de la
charte), bandeau d'étapes fixe en haut (une puce par chapitre, la courante s'allume) + barre de progression du récit,
temps forts du panneau en thème papier, sous-titres karaoké dans un cadre (mot dit en encre, mot fort dans une boîte).
1. Storyboard : un champ `voice` par phrase (le `kind` n'est pas utilisé ici), avec les vraies infos du client.
   `jobs/<job>/config.json` : `{"text": {"captionMaxWords": 3}}`.
2. `voice.py` (Gemini / Fish / `--file`) -> `build_text.py` -> `add_music.py`.
3. `work/<slug>_panels.json` : mêmes temps forts que l'écran partagé (`title`, `check`, `stat`, `search`, `image`,
   `steps`), avec `"chapter"` (2 à 5 chapitres de 1-2 mots : « AVANT », « LE SOIN », « APRÈS », « RÉSERVER »).
4. `python scripts/build_explainer.py <job> <slug>` (fin de marque si la charte en a une ; `--no-outro` sinon), puis
   check + snapshot + aperçu. Inspiré des explainers « interface papier » : principes repris, jamais les visuels.

### Pack « actu / punch » : annonce, promo, récap d'événement
Images plein cadre coupées vite (léger zoom + éclair à chaque coupe), gros titres condensés (Anton) qui s'empilent en
haut et claquent sur leur mot, objets qui collent aux mots (notification, étiquette prix, étiquette, document qui se
tape, date, chiffre, picto, emoji animé), sous-titres « impact » en bas (`--no-captions` pour s'en passer).
1. Médias dans `inbox/` (vidéos et photos du client, de son site) ; voix : storyboard + `voice.py` (un ton plus
   énergique : `--style "Lis d'une voix énergique, rythmée comme une annonce"`), `build_text.py`, `add_music.py --mood upbeat`.
2. `work/<slug>_punch.json` (détails dans `scripts/build_punch.py`) : un temps fort par idée, posé sur un mot ; `media`
   (ou `query` puis `build_punch.py fetch` / `pick` : Pixabay + planche) — une coupe toutes les 1,5 à 3 s ; `title` :
   2-3 lignes de 1 à 3 mots (*mot* en couleur) ; `prop` : un objet par temps fort au plus.
3. `python scripts/build_punch.py <job> <slug>` puis check + snapshot. Couleur d'accent : `visual.punchAccent` (une couleur
   de la charte qui se lit sur les images). Inspiré des formats « actu » courts : principes repris, jamais leurs visuels.
   Une notification est une illustration (contenu vrai), jamais une capture présentée comme réelle.

### Pack « infographie chiffrée » : raconter des résultats avec des graphiques
Sans visage, façon page de journal de données : fond papier, rubrique en haut (« VUES PAR REEL · JOUR 03 ») sous un
double filet, un graphique par idée, la phrase dite en bas qui passe du gris à l'encre (chiffres et mot fort en boîte),
frise des jours avec drapeau. Pour un bilan, une étude de cas, une méthode « en 14 jours », des chiffres clés.
1. Storyboard + `voice.py` + `build_text.py` + `add_music.py` (comme une vidéo sans rush).
2. `work/<slug>_data.json` (détails dans `scripts/build_data.py`) : un temps fort par chiffre dit, posé sur un mot ;
   types `bars` (barres qui poussent + compteurs), `grid` (« ×10 » + tuiles), `people` (foule de pictos + étiquette),
   `flip` (compteur à volets), `line` (courbe, en escalier si `steps`, notes « version 2 »), `pct` (pourcentages, le
   plus fort entouré), `days` (cases cochées + tampon), `title`, `end` (nom + lien). `head` et `day` restent acquis.
3. `python scripts/build_data.py <job> <slug>` puis check + snapshot. Accent : `visual.dataAccent`.
   **Uniquement des chiffres réels du client.** Un scénario d'exemple doit être dit comme tel à l'oral et à l'écran.

### Images sans paroles → montage (journal de chantier, ambiance, événement, produit)
Le montage par le texte ne s'applique pas : il n'y a pas de mots. Le où vient alors des **mesures** de `footage.py`
(netteté par zone, mouvement, tremblement, luminosité, voix détectée, date de tournage) ; le quoi garder reste ton choix.
```bash
python scripts/footage.py scan <job>                 # work/footage.json + planche work/footage/planche.jpg (REGARDE-LA)
python scripts/footage.py plan <job> <slug> --duree 30   # premier jet work/<slug>_footage.json, ordre chronologique
#   TU relis : keep (écarte les clips hors sujet ou ratés), ordre, seg (0 = meilleur passage mesuré, 1, 2), timelapse,
#   label (« JOUR 12 » automatique si les dates s'étalent), caption (« La cuisine »), title, series, compare (avant / après).
python scripts/add_music.py <job> <slug> --mood upbeat   # ou une voix off : storyboard + voice.py + build_text.py (même slug)
python scripts/build_footage.py <job> <slug> [--fit blur] [--style boite]   # puis check + snapshot
```
- **Accéléré** : proposé pour un clip long filmé caméra posée (`timelapse: true`, vitesse calculée pour la durée).
- **Avant / après** : `compare` avec deux clips filmés du même endroit -> volet qui découvre l'après.
- **Série** : `series` (« Journal de chantier · Semaine 4 sur 12 ») en haut, barre de progression ; un job par épisode.
- **Voix off** : les plans changent sur les débuts de phrases (ou sur `word`), sous-titres au style choisi. Sinon musique.
- Un clip où quelqu'un parle (`parole` dans le scan, voix détectée) : `transcribe.py` pour en faire une prise de parole
  ou un repère (« jour 12, on casse le mur »). Le son des clips n'est pas gardé (machines, vent).
- Avant que le client filme : `guide.py --metier chantier` (points fixes, plans de 10 s, accéléré posé, phrase repère).

### Plusieurs rushs → une vidéo
Le client a filmé 5 ou 6 clips, dans le désordre, avec des reprises : mets-les tous dans `inbox/` (`new_job.py --rush a b c`).
```bash
python scripts/multi.py list <job>                       # transcrit chaque clip (une fois) : durée + texte
#   TU lis tout et choisis l'ORDRE DU PROPOS (accroche, explication, preuve, appel à l'action) ; tu laisses de côté
#   les clips en double, ratés ou hors sujet (dis lesquels et pourquoi dans le compte rendu).
python scripts/multi.py assemble <job> <slug> --order IMG_2.mp4,IMG_1.mp4,IMG_4.mp4
```
Les clips sont mis bout à bout au format du premier (un clip d'un autre sens sur fond flouté), séparés par un silence ;
les mots sont recalés sans retranscrire. Puis le parcours « rush → reel » normal à partir de `cut_plan.py` : la
meilleure prise de chaque phrase se choisit tous clips confondus.

## Parcours « sans rush » : photos + texte → vidéo animée

Lis `references/storyboard.md`, écris `work/<slug>_storyboard.json` à partir du brief et des photos (`inbox/`),
montre-le en texte à l'utilisateur (une ligne par scène : type, texte écran, voix), puis :

**Voix de synthèse** (Gemini TTS) : voix et ton dans la charte (`video.voice.geminiVoice`, `geminiStyle` en français :
« Lis d'une voix calme et douce, débit naturel ») ou `--voice` / `--style`. Le ton du brief se traduit ici. En gratuit,
Google peut utiliser les textes envoyés : rien de confidentiel dans la voix off.
**Noms propres** : prononciation par marque dans `video.voice.pronunciation` (`{"Lyons-la-Forêt": "Lion-la-Forêt"}`) : seule la voix
de synthèse lit la forme phonétique, sous-titres et post gardent l'orthographe. Orthographe à la transcription :
`video.transcribe.vocabulary` (`["Martin", "Lyons-la-Forêt"]`). Doute sur un nom de lieu, de personne ou de produit :
demande à l'utilisateur comment il se prononce AVANT de générer la voix, et ajoute-le au lexique de la marque.
**Voix enregistrée** (`--file`, audio ou vidéo) : lance d'abord `voice.py … --file x` SANS storyboard ou avec des scènes
sans `voice` -> l'outil transcrit et écrit `work/<slug>_voice_phrases.txt` ; écris alors le storyboard avec un champ
`voice` par scène qui reprend EXACTEMENT les phrases dites (dans l'ordre ; une scène peut en grouper plusieurs), puis
relance : chaque scène se cale sur sa phrase, l'orthographe vient du storyboard, les blancs du début sont retirés.
Les scènes sans voix (intro, outro) seulement au début ou à la fin. Les ratés et reprises dans l'enregistrement :
passe d'abord par le parcours rush (`cut_plan` / `build_cut`) sur ce fichier, puis `--file` sur la version nettoyée.

```bash
python scripts/voice.py <job> <slug>                   # Gemini si GEMINI_API_KEY, sinon Fish, sinon voix locale (test)
#   ou une VOIX ENREGISTRÉE : python scripts/voice.py <job> <slug> --file <audio ou vidéo> [--denoise]
python scripts/build_text.py <job> <slug>
python scripts/add_music.py <job> <slug> --mood <ambiance>
python scripts/build_scenes.py <job> <slug>            # scènes hook / photo / points / stat / offer / quote / gallery / cta
cd <job> && npx --yes hyperframes@0.9.71 check && npx --yes hyperframes@0.9.71 snapshot --at <milieu de chaque scène>
```
**Pas assez de photos du client ?** Mets `"query": "<1-2 mots anglais>"` sur les scènes photo / accroche (ou liste,
galerie) sans `image`, puis `python scripts/broll.py auto <job> <slug> --storyboard` (avant `build_scenes.py`) :
Pixabay remplit `image` (vidéo de fond pour photo / accroche, photo sinon) et dessine `work/broll/planche.jpg` ;
regarde-la, corrige avec `broll.py pick <job> <slug> <n> a-f|none`. Les photos du client passent toujours avant, et une
image de banque ne représente jamais la boutique, l'équipe ou le produit du client (ambiance, gestes, matières).
Charte : `brands/<marque>/brand.json` (`video.visual` : police + fichiers, bgColor, inkColor, accentColor, logo,
`logoBlend: multiply` pour un logo sur fond blanc). Regarde CHAQUE scène sur la planche : texte lisible sur la photo,
rien sous les sous-titres, pas de grand vide.

## Parcours « une longue vidéo → plusieurs shorts » (interview, webinaire, live)

```bash
python scripts/new_job.py "<client>" "<sujet>" --brand <marque>
python scripts/transcribe.py <job> <vidéo complète> --slug <s>     # local, ~3x temps réel
python scripts/shorts.py sentences <job> <s>                        # phrases numérotées -> work/<s>_sentences.txt
#   TU lis TOUTE la liste, corriges l'orthographe des noms propres dans words.json (champ w, jamais les temps),
#   ignores les phrases hallucinées (« Sous-titrage… »), puis écris work/<s>_shorts.json : 3 à 5 passages de
#   20 à 60 s qui se comprennent seuls (une question ou promesse, une réponse, si possible un chiffre),
#   avec from / to / skip (NUMÉROS de phrases), hook (titre des 3 premières secondes, ≤ 7 mots), why, post.
python scripts/shorts.py make <job> <s> [--mode overlays si la source a déjà des sous-titres] [--mood upbeat]
#   -> un job enfant par short (jobs/<job>-<nom>/), puis check + snapshot sur chacun
python scripts/deliver.py <job>-<nom> short --formats 9:16
```
Source paysage avec une personne à l'image : `shorts.py make` lance `reframe.py` et la fenêtre 9:16 **suit le visage**
(détection locale YuNet, caméra posée qui ne glisse que quand la personne sort de la zone centrale ; trajet recalculé
pour chaque format à la livraison). Moins de 40 % d'images avec un visage (diapos, écran partagé) : image entière sur
fond flouté. Forcer : `"visual": {"fit": "fill"}` (image entière) ou `"cover"` (recadrage fixe, `focusX`).
Rush paysage hors shorts : `python scripts/reframe.py <job> <slug>` après `build_cut.py`, puis `build_composition.py`.

## Blocs de motion design (library/block/)

`compteur`, `note-etoiles`, `jauge`, `bouton-cta`, `compte-rebours`, `notification`, `sticker`, `surligneur`, `fleche`,
`suivre`, `confetti`, `marquee`, `mot-tournant`, `barres`, `frise`, `machine-a-ecrire`, `tarif` (+ `intro-marque`, `outro-marque`,
`bandeau-nom`). Scènes `device` (téléphone) et `browser` (navigateur avec barre d'adresse) qui font défiler une vraie
capture du site / de l'app. Transitions de scène : `wipe-up`, `wipe-left`, `fade`, `iris`, `zoom`,
`blur`. Confetti, marquee, mot-tournant, barres, frise, machine-a-ecrire, tarif, device, browser et iris/zoom/flou sont portés
depuis Onda (MIT, Rodrigo Botelho). Chiffres des barres, prix des tarifs, dates des frises : uniquement des données réelles.
Nouveau bloc : l'ajouter dans `scripts/_make_motion_blocks.py`, relancer, tester (`check` + `snapshot`), puis `library.py save`. Couleurs, police et logo viennent de la charte ; le reste en `vars`
(voir l'`usage` de chaque entrée dans `library/index.html`). Trois façons de s'en servir :
- **Scène plein écran** (sans rush) : `{"kind": "block", "block": "compteur", "vars": {…}, "voice": "…"}` sur le fond de la charte.
- **Par-dessus une scène** (sans rush) : `"motions": [{"block": "note-etoiles", "word": "<mot de la phrase>", "dur": 3, "vars": {…}}]`.
- **Par-dessus un rush** : `work/<slug>_motions.json` = la même liste, puis `build_composition.py`.
Le bloc apparaît quand le **mot** est prononcé (`occurrence` pour la 2e fois qu'il est dit) : jamais de timecode écrit à la
main (les mots élidés comme « l'aventure » sont trouvés par « aventure »). Le rapport `motions` de la sortie dit
quels blocs sont posés ou ignorés. Positions : `top` (%), `left`, `x`/`y` selon le bloc. Durée : libre, le bloc cale ses
animations sur la durée réelle de son montage (scène courte = animations resserrées) ; 2 à 3,5 s conseillées.
En scène plein écran, la carte prend l'encre de la charte (contraste) ; en surimpression, elle reste translucide. Chiffres, notes, avis et compteurs : uniquement des
valeurs réelles du client ; `notification` est une illustration, pas une vraie commande.

### Suggestion automatique (à trier)
`python scripts/suggest_motions.py <job> <slug>` lit ce qui est DIT et propose : montant -> compteur, % -> jauge,
« 4,9 sur 5 » -> étoiles, « plus que 3 jours » -> compte à rebours, « nouveau / offert » -> sticker, « réservez… » ->
bouton, « abonnez-vous » -> suivre, mots-clés -> emoji animé ; variété, espacement, plafond par minute, rien sous
l'accroche. Sortie : `work/<slug>_motions_suggested.json` avec la phrase de chaque proposition. **Tu tries** : garde ce
qui sert le propos (pas d'ancienne valeur qui embrouille, pas deux fois la même idée), écris les légendes avec les mots
de la phrase, complète uniquement avec des infos réelles (nombre d'avis, @compte), puis copie dans
`work/<slug>_motions.json` (rush) ou le champ `motions` des scènes. `--apply` écrit directement, à relire quand même.

### Animations Lottie et emojis animés (library/lottie/)
```bash
python scripts/lottie.py get emoji 🔥 --name feu              # emoji animé Google Noto (CC BY 4.0, crédit auto)
python scripts/lottie.py get url <lien .json|.lottie> --name x --license "Lottie Simple License" --author "…"
python scripts/lottie.py render <nom>                         # une fois : WebM transparent + aperçu de galerie
```
Puis dans `motions` : `{"block": "lottie", "name": "feu", "word": "<mot dit>", "dur": 2, "vars": {"x": 50, "y": 24, "size": 30}}`
(centre x/y en %, taille en vmin, rejouée en boucle sur `dur`). Le crédit part dans `renders/credits.txt`.
Sources sûres : LottieFiles gratuit (Lottie Simple License, commercial OK), Noto (CC BY 4.0), Fluent (MIT).
Jamais une animation sans licence connue. Prêtes (24, `lottie.py list`) : valide ✅, coeur ❤️, etoile 🌟, pouce 👍, fusee 🚀,
cadeau 🎁, idee 💡, regard 👀, waouh 🤩, adore 😍, cent 💯, bravo 🙌, applaudir 👏, eclat ✨, cloche 🔔, alarme ⏰,
trophee 🏆, force 💪, reflexion 🤔, rire 😂, doigt 👉, cible 🎯, feu 🔥, fete 🎉. (💰 n'existe pas en animé chez Noto.)

### Skills d'appui installés
- `gsap-*` (officiels GSAP : SplitText, MorphSVG, DrawSVG gratuits) pour écrire de nouveaux blocs ;
- `remotion-to-hyperframes` pour porter un composant Remotion / Motion Canvas / Lottie / After Effects, vérifié image par image
  (attention à la licence du composant source) ;
- `motion-design` (LottieFiles), `motion-director`, `web-motion-auditor` : principes de timing, de courbes et de contrôle qualité.
  Le « Creator MCP » LottieFiles proposé par `motion-design` n'est pas branché (service en ligne : accord requis).

## Habillage de marque (intro, outro, bandeau nom)

Dans `brands/<marque>/brand.json` (clé `video`) ou `jobs/<job>/config.json` :
`"branding": {"intro": "intro-marque", "outro": "outro-marque", "lowerThird": {"name": "Prénom Nom", "role": "Fonction"}}`.
- Rush : `build_composition.py` ajoute l'intro (1,6 s, la vidéo démarre sous son volet de sortie), l'outro (3,4 s,
  accroche et site de la charte) et le bandeau nom à la première prise de parole (après l'accroche d'un short ;
  dans la bande floutée si la source est affichée entière). `--no-branding` pour une version sans.
- Sans rush : ajoute toi-même les scènes `{"kind": "block", "block": "intro-marque", "hold": 1.6}` en tête et
  `{"kind": "block", "block": "outro-marque", "hold": 3.4}` en fin du storyboard.
- **Nom et fonction** : uniquement ceux que l'utilisateur donne, avec l'accord de la personne. Jamais deviné.
- **Accroche de marque** : uniquement une accroche officielle du client (`tagline` de la charte) ; jamais inventée.

## Versions traduites (FR → NL / EN / …)

Sous-titres traduits sur la même vidéo, voix d'origine conservée (rush, short ou vidéo sans rush) :
```bash
python scripts/translate.py export <job> <slug> --to nl     # phrases + temps -> work/<slug>_tr_nl.json
#   TU remplis chaque "nl" (+ "hook_nl", "post_nl") : traduction naturelle, même sens, longueur proche,
#   registre « je » pour les réseaux (sauf consigne), noms propres et marques inchangés ; jamais les temps.
#   « role_nl » : fonction du bandeau nom (le nom ne se traduit pas). Ré-exporter garde les traductions faites.
python scripts/translate.py apply <job> <slug> --to nl
python scripts/build_composition.py <job> <slug> --lang nl   (ou build_scenes.py … --lang nl) ; check + snapshot
python scripts/deliver.py <job> <slug> --lang nl             # -> renders/livraison_nl/
```
Voix dans une autre langue (vidéo sans rush) : copie le storyboard sous un autre slug, traduis `voice` et les textes
à l'écran, puis `voice.py` avec Fish Audio (la voix locale Kokoro n'a pas de néerlandais). Fais relire une
traduction par un locuteur natif avant publication si le client est exigeant sur la langue.

## Lot : plusieurs vidéos × langues × formats

Écris `lot.json` (dans le job parent ou ailleurs) :
`{"name": "<lot>", "client": "<client>", "items": [{"job": "<job>", "slug": "<slug>"}], "langs": ["fr", "nl"],
"formats": ["9:16", "1:1"], "quality": "delivery", "reuse": true}` puis
`python scripts/batch.py plan lot.json` (ce qui manque : traductions, posts ; durée estimée ~5,5 s de rendu par
seconde de vidéo et par format) → termine ce qui manque → `python scripts/batch.py run lot.json`
→ `jobs/_lots/<lot>/index.html` : une page client avec toutes les vidéos, couvertures et textes par langue.
`reuse: true` garde les livraisons existantes ; mets `false` si la charte, l'habillage ou le montage a changé.

### Calendrier de publication
`python scripts/planning.py <lot.json | job:slug,job:slug> --start AAAA-MM-JJ [--days mar,jeu,sam]
[--networks instagram,tiktok,facebook,linkedin,youtube] [--langs fr,nl]` -> à côté de la page du lot (ou dans
`renders/`) : `planning.html` (une carte par jour × vidéo × langue : réseaux et heures, couverture, texte à copier,
lien de la vidéo), `planning.ics` (rappels 30 min avant, à importer dans l'agenda du client) et `planning.csv`.
Une vidéo par jour de publication, dans l'ordre du lot ; hashtags réduits par réseau (TikTok 5, Facebook 3…).
Horaires = repères génériques : dis au client de les ajuster selon les statistiques de son compte. Rien n'est publié.

## Vitesse de rendu (mesurée le 2026-11-20 sur ce PC : 16 cœurs, Radeon 860M)

~0,18 s par image capturée, quoi qu'on règle : nombre de workers (8 = 16), demi-résolution, capture rapide
(indisponible sous Windows) et rendus simultanés (HyperFrames les exécute l'un après l'autre) ne changent rien.
Seul levier : moins d'images. Aperçus à valider : `-f 15` ou `deliver.py … --apercu` (≈ -40 %) ; livraison finale
toujours à 30 i/s. Ne lance pas plusieurs rendus en parallèle : ça ne va pas plus vite.

## Livraison (les deux parcours)

1. Écris `work/<slug>_post.json` : `caption` (2-3 phrases dans le ton de la marque, sans promesse inventée),
   `cta`, `hashtags` (5 à 8, locaux + métier), `first_comment` facultatif. Marque-le « brouillon à valider ».
1 bis. **Couverture avec titre** (facultatif, conseillé pour YouTube et les Reels épinglés) :
   `python scripts/covers.py <job> <slug> --title "<titre 1>" --title "<titre 2>"` — titres de 6 mots max tirés de la
   promesse DITE dans la vidéo (jamais une promesse inventée). L'outil prend les 3 meilleurs plans du visage (net, grand,
   bien éclairé ; vidéo sans rush : photos des scènes) et compose 3 maquettes dans la charte : a « bandeau », b « impact »,
   c « côté », en 9:16, 1:1 et 16:9. Montre `renders/covers/planche.jpg`, puis `covers.py pick <job> <slug> a|b|c` :
   `deliver.py` livre alors cette couverture pour chaque format (sinon, image de la vidéo sans sous-titres).
2. `python scripts/deliver.py <job> <slug> [--formats 9:16,1:1,16:9] [--quality delivery] [--apercu]` : pour chaque format,
   composition à la bonne taille (texte à gauche et image à droite en carré / paysage ; rush en format différent =
   image entière sur fond flouté), rendu, master -14 LUFS, couverture ; puis `renders/livraison/` avec
   `livraison.html` (lecteurs, téléchargements, texte du post à copier, crédits), `post.txt`, `credits.txt`.
3. Avant de lancer : `--size 1:1` et `--size 16:9` sur le builder + `snapshot` pour vérifier la mise en page.
   Compter ~3 à 4 min de rendu par format pour 30 s de vidéo.
4. Ouvre `livraison.html` pour l'utilisateur. N'envoie jamais rien au client toi-même.

### Décider le dérush (`plan.json`)
- **Script connu** : aligne les îlots sur le script, garde la meilleure prise de chaque phrase.
- **Script inconnu** : reconstitue le texte voulu, garde la **dernière prise complète** de chaque phrase.
- Jette : faux départs, phrases interrompues, mots isolés, hésitations seules, consignes dites à la caméra
  (« celle-là est ratée, je la refais »), hors-sujet par rapport au but de la vidéo.
- Ne jette jamais un îlot que tu n'as pas lu. Remplis `reason` pour chaque îlot jeté.
- **Hésitations** (`fillers` du plan, repérées par l'outil dans les îlots gardés ; la transcription est amorcée pour
  écrire les « euh ») : `hesitation` (« euh », « hum ») et `repetition` (« je je ») sont retirées par défaut ;
  `pause` (blanc ≥ 0,6 s au milieu d'une phrase) est resserrée à 0,12 s de chaque côté ; `tic` (« du coup », « en fait »,
  « voilà », « genre », « bon », « quoi »…) reste **par défaut** : passe `remove: true` seulement quand le tic n'apporte
  rien (« Du coup, euh, on a… ») et laisse-le quand il porte le sens (« en fait, c'est gratuit » qui corrige une idée
  reçue, « voilà le résultat »). Dans le doute, garde. Un « euh » gardé n'apparaît jamais dans les sous-titres.
  Écoute les jointures signalées dans le compte rendu (une coupe au milieu d'une phrase peut claquer).
- Réglages : beaucoup de micro-îlots → `--min-silence 0.6` ou `--noise -25` ; un seul gros îlot (débit continu,
  musique de fond) → `--min-silence 0.3` ou `--noise -40`. Relancer est instantané.
- Un îlot ne se coupe pas en son milieu : si sa fin déborde (« … Ensuite, »), dis-le dans le compte rendu.

### Décider le texte (`text.json`)
- Mode par défaut `captions` : la plupart regardent sans le son. Styles : `pop` (mots qui surgissent, défaut),
  `karaoke` (groupe entier, mot actif en couleur d'accent), `minimal` (sobre, institutionnel).
- `overlays` (doctrine reel-cut) : ~5 par minute, strictement verbatim ; garde promesses, chiffres, contrastes,
  noms de produit ; jette les connecteurs (« du coup », « en fait »).
- `punch` : max 2 par minute, sur l'affirmation clé, le chiffre fort, le nom du produit ou l'appel à l'action.
  Chaque punch reçoit un whoosh calé sur son pic.

- `mono` : majuscules machine à écrire, chaque mot dans sa boîte noire, le mot dit en couleur d'accent (ton tech / expert).
- Styles en plus : `boite` (le mot dit passe dans une boîte couleur d'accent, style CapCut), `impact` (gros, contour
  noir, le mot dit grossit en couleur d'accent, style Hormozi ; mettre `text.captionMaxWords` à 2 ou 3), `duo` (les
  nombres ou le mot fort du groupe en couleur d'accent). `--emoji` (ou `text.captionEmoji: true`) : un emoji après les
  mots-clés (« gagnez » 🏆, « idée » 💡, « bravo » 👏…), un au plus par groupe et toutes les 4 s. Le dictionnaire est
  celui de `suggest_motions.py` (EMOJI). Vidéos sans rush : mêmes styles et `--emoji` sur `build_scenes.py`
  (`--style boite` ou `text.captionStyle`), dans le bandeau sombre qui garde le texte lisible sur fond clair.

### Plans de coupe (b-roll) sur un rush
Pour qu'une vidéo face caméra ne reste pas statique : une image illustre ce qui est dit pendant 2 à 5 s, la voix
continue, les sous-titres restent au-dessus.

**En un clic (par défaut quand on te demande « ajoute des plans de coupe »)** :
1. `broll.py moments <job> <slug>` ; dans `work/<slug>_broll_suggested.json`, retire les moments sans intérêt, mets
   `"image"` pour ceux qu'illustre un média du client, et écris `"query"` pour les autres : **1 à 2 mots anglais
   concrets et filmables** (« handshake », « parcel delivery ») ; une phrase entière donne des résultats hors sujet.
2. `broll.py auto <job> <slug> [--kind mix|photo|video]` : cherche, pose la 1re proposition, écrit `<slug>_broll.json`
   et la planche `work/broll/planche.jpg` (jusqu'à 6 propositions par plan : vidéos assez longues puis photos).
3. **Regarde la planche** et corrige : `broll.py pick <job> <slug> <n> <a-f>` ou `none` pour retirer le plan.
   Écarte les autres marques (logos, véhicules siglés), les animations hors ton, les images floues.
4. `build_composition.py`, puis snapshot pendant chaque plan. Montre ensuite l'aperçu à l'utilisateur.

**À la main**, plan par plan :
1. `python scripts/broll.py moments <job> <slug> [--every 7]` : une phrase toutes les ~7 s (pas sous l'accroche ni
   sous un bloc de motion), plus la liste des photos et vidéos de `inbox/`.
2. Pour chaque moment, **d'abord les médias du client** (regarde-les). Sinon une banque :
   `broll.py search <job> "<requête en anglais>" --orient tall [--video]` télécharge des miniatures que tu **regardes**
   avant de choisir, puis `broll.py get <job> <id>` (fichier réduit dans `assets/broll/`, crédit noté et livré).
   Source par défaut : **Pixabay** si `PIXABAY_API_KEY` est dans `.env` (photos et vidéos ; `--video` pour un plan
   vidéo de 10 s max, muet ; Pexels pris en charge aussi avec `PEXELS_API_KEY`), sinon Openverse (images seulement). Openverse a beaucoup de photos amateurs : écarte tout ce qui est flou, hors sujet, daté ou montre une autre marque. Mieux vaut
   2 bons plans que 6 moyens ; aucun plan de coupe vaut mieux qu'une image qui fait banque d'images ratée.
   Jamais une image libre présentée comme la boutique, l'équipe ou le produit du client.
3. Garde les moments retenus dans `work/<slug>_broll.json` :
   `[{"word": "Lorsque", "occurrence": 1, "until": "euros", "image": "inbox/vitrine.jpg", "mode": "full"}]`
   — calé sur un mot dit (jamais un timecode), jusqu'au mot `until` (ou `"dur": 2.5`). `mode` : `full` (plein écran,
   léger travelling) ou `carte` (photo encadrée ; sur fond flouté elle se place dans la bande du haut, sinon en haut
   de l'écran). Une vidéo (`.mp4`) passe en muet.
4. `build_composition.py` les pose (whoosh discret à l'entrée) ; vérifie sur `snapshot` pendant chaque plan.

### Contrôle avant de montrer
1. `check` : 0 erreur. Les avertissements `line_unread` sur des groupes mot à mot sont attendus en débit rapide.
2. `snapshot` : visage non couvert, texte dans la zone sûre (ni tout en haut ni dans le dernier quart), pas de
   sous-titres déjà incrustés dans la source (sinon `--mode overlays` ou pas de texte), cadrage 9:16 qui garde la
   personne (sinon `visual.focusX` dans `jobs/<job>/config.json`, 0 à 100).
3. Compte rendu court : durée avant / après, îlots jetés et pourquoi, nombre de sous-titres et de punchs, ce que
   l'utilisateur doit écouter. Ne dis jamais « parfait » : c'est lui qui juge. **Pas de rendu final sans accord.**

### Musique
- Banque `sounds/music/` (CC0 / CC-BY, `catalog.json` avec ambiance, BPM, LUFS) : upbeat, chill, inspiring,
  energetic, acoustic, cinematic, funky, ambient. Écoute-la par les chiffres (BPM, durée), propose 2 pistes et
  laisse l'utilisateur choisir à l'oreille.
- Lien YouTube / SoundCloud / Bandcamp (`--url`, via yt-dlp) ou fichier du client (`--file`) : **dis toujours**
  qu'un lien n'est pas une licence ; à n'utiliser que si le client a les droits (sinon son coupé ou vidéo bloquée
  sur Instagram / TikTok). La source part dans `renders/credits.txt` avec « droits à vérifier ».
- Le lit est baissé sous la voix (sidechain) ; `--level` règle son niveau de base (-20 LUFS par défaut).
- Enrichir la banque : `scripts/bank.py sfx|music [--only cat --query "..."]` (Openverse, ~200 recherches/jour).
- `renders/credits.txt` est livré avec la vidéo (obligatoire pour CC-BY : en description du post).

## Sources (imposées)
- Voix off : Gemini TTS (`GEMINI_API_KEY`, gratuit) par défaut ; Fish Audio (`FISH_API_KEY`, payant) pour cloner une
  voix ; un enregistrement du client (`--file`) ; Kokoro local (`ff_siwis`) seulement pour tester ou dépanner.
  Clonage d'une voix : accord écrit de la personne.
- SFX : banque `sounds/` (via `real-sfx` pour un design sonore complet). Jamais de son synthétisé.
- Musique : `openverse-sfx` (CC0 / CC-BY / PDM, `credits.txt` livré).
- Transcription : locale (faster-whisper large-v3-turbo). Groq seulement si l'audio peut sortir de la machine.
  Parakeet (`npx hyperframes transcribe`) est écarté : il bascule en anglais au milieu du français.
- Pas de connexion HeyGen ni de crédits payants sans accord explicite (le skill `media-use` la propose d'office).

## Bibliothèque (la règle qui fait gagner du temps)

`library/` contient les motions **validés** (scènes, styles de sous-titres, transitions, intros/outros, blocs
HyperFrames), chacun avec aperçu vidéo, « quand l'utiliser » et extrait d'utilisation. Galerie : `library/index.html`.

1. **Avant de créer** une scène, un style ou une animation : `python scripts/library.py search "<besoin>"`.
   Réutilise ce qui existe (adapte-le si besoin) ; sinon cherche dans `hyperframes-registry` ; sinon crée.
2. Blocs réglables : scène `{"kind": "block", "block": "<nom>", "text": …, "sub": …, "vars": {…}}` dans le storyboard ;
   `build_scenes.py` copie le bloc de `library/` dans `compositions/` et remplit ses variables depuis la charte.
   Un nouveau bloc = un fichier HyperFrames avec `data-composition-variables`, couleurs et police en `var(--…)`,
   timeline enregistrée sous son id, `src` d'image de repli en data URI (sinon `check` échoue).
3. **Après validation** par l'utilisateur d'une vidéo ou d'un passage, propose en une ligne :
   « Je sauvegarde <ce motion> dans la bibliothèque sous le nom <x> ? ». Si oui :
   `python scripts/library.py save --type <type> --name <x> --title … --desc … --use "<quand>" --tags …
   --job <job> --clip renders/<rendu validé>.mp4 --at <début> --dur <durée> [--file <bloc.html>] --usage '<extrait>'`
   (extrait court : `render --start S --end E` si besoin). Jamais sans validation.

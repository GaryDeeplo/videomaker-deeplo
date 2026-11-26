---
name: videomaker-deeplo
description: >-
  VideoMakerDeeplo (Deeplo Video Maker) : monte une vidéo prête à poster pour une entreprise, un indépendant ou un
  créateur (contenu tech compris), dans HyperFrames, à partir de rushs face caméra, de clips sans paroles (chantier,
  ambiance, plats, événement), de photos, de chiffres, de textes ou d'idées. Accueil en questions-réponses, dérush par
  le texte (meilleures prises, blancs et « euh » coupés), rendu choisi tout seul (écran partagé, explainer papier,
  actu / punch, infographie chiffrée, journal de chantier) avec animations calées sur les mots dits (maquettes
  d'interface, listes « 1 sur 5 », vrais logos d'outils, chiffres), accroches animées en 10 styles, sous-titres mot à
  mot (11 styles), voix off Gemini gratuite ou enregistrement, musique libre de droits, charte du client, formats
  9:16 / 1:1 / 16:9, shorts, traductions, mises à jour. Utiliser dès que l'utilisateur veut « monter une vidéo »,
  « faire un reel », « dérusher », « mettre des sous-titres », « couper les blancs », « faire une vidéo pour <client> »,
  « journal de chantier », « montage de mes clips », « une infographie », ou dépose un rush, ou tape /videomaker-deeplo.
---

# VideoMakerDeeplo (Deeplo Video Maker)

Tout se lance **depuis la racine du projet** : `PYTHONUTF8=1 python .claude/skills/videomaker-deeplo/scripts/<x>.py`
(abrégé `scripts/<x>.py` dans le texte ; chaque script répond en une ligne JSON). HyperFrames se lance toujours dans un
sous-shell, depuis le job : `( cd <job> && npx --yes hyperframes@0.9.71 check )` (`<job>` = le chemin `job`
renvoyé par `new_job.py` ; les scripts acceptent ce chemin ou le nom du dossier dans `jobs/`). Config : `config.default.json`,
écrasée par `brands/<marque>/brand.json` (clé `video`), puis par `jobs/<job>/config.json`. Plan et état : `PLAN.md`.
Les détails de chaque sujet sont dans `references/` (une ligne « Détails : … » renvoie au bon fichier) : lis le
fichier quand le sujet arrive, pas avant.

## Accueil (à chaque chargement du skill)

1. `python .claude/skills/videomaker-deeplo/scripts/onboard.py status` (silencieux, une seconde) : installation, clés,
   marques (`marques_recentes` : les 2 dernières utilisées), projets récents, réglages connus, dernières vidéos /
   photos de Téléchargements. Dès que la marque et le parcours sont connus :
   `onboard.py status --marque <m> --parcours <p>` (parcours : rush, sans-rush, shorts, montage, plusieurs-rushs,
   explainer, punch, infographie, collage, ecran-partage, mots, immobilier, traduction, lot, calendrier, guide,
   vitrine) -> `reglages_connus` de CETTE marque et CE parcours, et `gouts_client` (retours gardés du client, valables
   tout le projet ; la demande du moment gagne toujours).
2. `installe` faux -> propose d'abord l'installation (`INSTALL.md`), rien d'autre. `mise_a_jour.maj` vrai -> une ligne
   (« Une mise à jour du skill est disponible : <2-3 nouveautés> ») et une question à choix « Installer maintenant
   (recommandé) » / « Plus tard » ; si oui : `scripts/update.py install` puis `scripts/check.py` (chartes, projets,
   clés et motions ajoutées ne sont jamais touchés). Une seule fois par session. Hors ligne : rien à dire.
3. **Trois séries de questions au plus** (outil AskUserQuestion : ≤ 4 questions par série, ≤ 4 options par question,
   la recommandée en premier avec « (recommandé) » ; l'outil ajoute « Autre » tout seul). Jamais une question dont la
   réponse est déjà dans la demande, les réglages connus ou la charte.
   - **Demande complète** (quoi + fichiers + pour quoi : « monte ce rush pour un Reel de la boulangerie Martin de 30 s qui pousse le
     parrainage ») -> pas de séries 1 et 2 : complète avec les réglages connus, écris le brief, annonce-le en une
     ligne et lance. **La série 3 se pose toujours**, même alors.
   - **Demande précise sans le pourquoi** (« monte ce rush pour la boulangerie Martin ») -> seulement les questions manquantes de la
     série 2, puis la 3.
   - **Série 1 — quoi et pour qui** (demande vague) : **Quoi ?** (monter une vidéo filmée · vidéo à partir de photos et
     d'un texte · découper une longue vidéo en shorts · reprendre « <projet récent> » s'il y en a un ; plusieurs clips,
     traduire, lot, couverture, planning, guide de tournage passent par « Autre ») · **Pour quelle marque ?** (les 2
     `marques_recentes` · « nouvelle marque » · « sans marque » ; les autres marques de `brands/` via « Autre »).
   - **Nouvelle marque -> entretien de style** (une série, juste après) : **Ce que vous faites, pour qui ?** (« Autre »
     pour l'écrire ; ou « je décris en une phrase plus tard ») · **Couleurs ?** (tirées du logo / du site · je les donne en
     hex · choisis pour moi) · **Rythme des animations ?** (punchy : rebonds courts · doux : entrées longues amorties) ·
     **Jamais ?** (choix multiple : pas d'emoji · pas de musique forte · pas de rouge · rien de spécial ; « Autre » pour le
     reste) ; les montages qu'il aime (créateurs, marques) via « Autre ». Puis, à la série 3, la question des polices.
     Écris la charte EN CHIFFRES (hex, paire de polices, style de sous-titres, vitesse) :
     `scripts/charte.py creer <marque> nom=… accent=#… fond=#… encre=#… polices=<paire> sous_titres=<style>
     vitesse=punchy|doux musique=… ton="…" logo=… interdits="…|…" references="…"` (les interdits deviennent des goûts
     gardés). Évite le look « par défaut » (mot actif coloré + Inter + rebond) sauf si c'est ce qu'il veut.
   - **Série 2 — fichiers et brief** : **Les fichiers ?** (les fichiers récents de Téléchargements en options ; sinon
     un chemin dans « Autre ») · **Où sera-t-elle publiée ?** (Reels / TikTok 9:16 · tous les formats · YouTube 16:9 ·
     LinkedIn) · **Objectif ?** (vendre une offre · faire connaître · informer / conseiller ; recruter, fidéliser via
     « Autre ») · **Durée ?** (15 s · 30 s · 60 s · aussi long que le contenu le mérite). Recommandé : ce que disent
     les réglages de la marque, sinon 30 s pour un Reel et « aussi long que le contenu » pour YouTube.
     Sans rush : « Les fichiers ? » devient **Photos et texte ?** (dossier de photos · « pas de photos : images
     d'ambiance Pixabay » ; le message en une phrase via « Autre ») et, si la voix n'est pas réglée pour la marque,
     **Voix off ?** remplace la durée (« voix de synthèse naturelle (recommandé) » Gemini, gratuit · « j'ai un
     enregistrement » · « pas de voix, musique et textes seulement » ; la durée suit alors le texte). Ni clé Gemini ni
     Fish -> dis-le en une ligne (voix locale de test). Shorts : la durée est 20 à 60 s par short, ne la demande pas.
   - **Ton, public, appel à l'action, langues** ne sont pas des questions : réglages de la marque (`ton`, `public`,
     `cta`, `langues`, `tone` et `contact` de la charte), sinon « choisis pour moi » (déduits du contenu et de
     l'objectif). Promo, date, prix à citer ou sujet à éviter : seulement si l'utilisateur les donne ; le récap
     d'une ligne l'invite à le dire.
   - **Série 3 — look, ouverture, polices, habillage** (toujours, une fois la transcription relue et le dérush décidé,
     ou le storyboard écrit ; 4 questions ensemble, la recommandée en premier dans chacune) :
     **Quel look ?** (choix simple, avec un aperçu texte de la mise en page dans `preview`) : tuto cartes · luxe
     éditorial · écran partagé · classique — reco d'après le contenu et le brief (tuto, tech, liste d'étapes -> tuto
     cartes ; immobilier, hôtellerie, ton haut de gamme -> luxe éditorial ; conseil d'expert, preuves -> écran
     partagé ; témoignage, ton sobre -> classique). Réglages exacts de chaque look : references/looks.md.
     **Quelle ouverture ?** (choix simple) : sujet dessiné (plan, façade, plat… `hook` + `art`) · nom ou mot-clé géant
     derrière la personne (premier mot dynamique, ou `--derriere`) · titre animé (`hook`, style selon le ton) · sans
     (on entre direct sur la personne). Absente si la marque a un réglage `accroche`.
     **Quelles polices ?** (choix simple) : lance d'abord `scripts/polices.py planche <job> --titre "<accroche>"` et
     ouvre `work/polices.png` pour l'utilisateur ; options = « garder la charte » (en premier si la marque a ses
     polices) + 3 paires de `polices.py list` adaptées au look (luxe -> editorial / premium ; tuto -> moderne / net ;
     chaleureux -> chaleureux / creatif ; promo -> punch / ludique). Puis `scripts/polices.py apply <job> <paire>`.
     **Quoi ajouter ?** : une question à **choix multiple** (`multiSelect: true`, 3 ou 4 options). Chaque option
     dit ce qu'on verra et sur quels mots, à partir de ce qui est DIT ou montré — jamais une info en plus :
     lieux et distances -> carte (`map`, pays qui s'allume) + chrono (`clock`) ; prix, fourchettes, chiffres ->
     compteurs (`stat`, bruitage de caisse sur les €), palettes (`flap`), calcul en étapes (`steps`), devis
     (`invoice`) ; avantages, ambiance, comparaison -> pictos qui tombent (`icons`), liste cochée (`check`), titre
     (`title`) ; émotion (« magique », « incroyable ») -> emoji animé (`lottie`, aussi sur un passage `face`), mot en
     escalier (`text.syllabes`) ; outil, appli, site -> vraie capture d'écran (`image` + `fit: contain`) ; ambiance ->
     images libres en carte (toujours présentées comme illustration) ; sujet visuel -> accroche dessinée ; fin ->
     carte `suivre` (vrai compte).
     Quand le look part sur les mots dynamiques (qui coupent les sous-titres), elle propose aussi
     **« sous-titres complets en plus »** (recommandée si la vidéo sera surtout vue sans le son : LinkedIn, public
     pro). Si `pack.py choose` hésite vraiment entre deux packs, ajoute à cette série une question simple « Quel
     rendu ? » avec les deux packs. Puis applique les choix, snapshot, aperçu. Pas de nouvelle série 3 pour une
     deuxième version (Reels courte, traduction) : reprends les mêmes choix.
     Rien n'est tiré au hasard : look, ouverture, polices et ajouts viennent de ces réponses, du brief et du contenu
     dit ; seules la rotation des sons, la piste dans une ambiance et l'ordre des entrées de cartes varient (rejoués à
     l'identique pour une même vidéo).
     Détails : references/looks.md, references/accroches.md, references/mots-dynamiques.md, references/objets.md.
4. **Le brief** (écrit après la série 2 ou la demande complète, complété après la série 3 : la commande fusionne) :
   `scripts/onboard.py brief <job> objectif=… public=… duree=… ton=… cta="…" mentions="…" eviter="…"
   langues=fr,nl accroche=titre|dessin|non habillage="…" look=… ouverture=… polices=…` (`work/brief.json` ; clé inconnue -> avertissement ; seules
   `langues` et `reseaux` sont des listes). **Relis-le à chaque décision** :
   | Brief | Effet sur le montage |
   |---|---|
   | durée | dérush : garde les phrases les plus fortes pour tenir la durée (dis ce que tu as retiré) ; sans rush : nombre de scènes |
   | objectif « vendre » | accroche sur le bénéfice, bloc `bouton-cta` ou `tarif` sur l'offre (vraie), fin sur l'appel à l'action |
   | objectif « recruter » | modèle recrutement, bandeau nom, appel « postulez » ; « informer » : sobre, `etapes` / `points` |
   | public « pros » | vouvoiement dans le post, style `minimal` ou `duo` ; « particuliers » : tutoiement possible si la marque le fait |
   | ton dynamique | musique upbeat / energetic, style `boite` ou `impact`, plans de coupe, emojis, zooms |
   | ton chaleureux | musique acoustic, style `pop`, plans de coupe doux ; « haut de gamme » : cinematic / ambient, `minimal`, pas d'emoji |
   | ton sobre | musique inspiring basse ou aucune, `minimal`, pas d'emoji ni de sticker |
   | cta | outro (`info`), texte du post (`cta`), bloc `bouton-cta` en fin de vidéo |
   | mentions | doivent apparaître à l'écran ET dans le post ; si la vidéo ne les dit pas, demande où les placer |
   | à éviter | jamais à l'écran, dans le post, les plans de coupe ni les suggestions de motion |
   | langues | `translate.py` pour chaque langue en plus, posts traduits |
   | accroche | `titre` : `"hook": {"style": <selon le ton>, "text": <titre court>}` ; `dessin` : en plus le sujet dessiné (`references/accroches-dessin.md`) ; `non` : rien |
   Le brief appartient à CETTE vidéo ; il n'entre dans les réglages de la marque qu'avec l'accord de l'utilisateur
   (`public` et `ton` y sont souvent stables). Valeurs possibles de chaque champ : references/habillage-marque.md.
5. **Le pack (rendu), choisi tout seul** : dès que les fichiers et le brief sont là,
   `scripts/pack.py choose <job> [--slug s] --demande "<la demande>"` conseille un pack d'après les fichiers (rush où
   l'on parle = écran partagé ; clips sans paroles = montage), les chiffres du propos (= infographie), le brief
   (informer / conseiller = explainer ; vendre, annoncer, ≤ 20 s = punch ; ton sobre ou haut de gamme = classique) et
   ce qui est dit. Après `build_text.py` : `scripts/pack.py draft <job> <slug>` écrit le premier jet des temps forts
   (un brouillon : relis-le). L'utilisateur peut toujours dire « plutôt en punch ».
   Détails : references/ecran-partage.md, references/packs.md.
6. **Récap en une ligne puis lancement** (« Reel 9:16 pour la boulangerie Martin, écran partagé, style boîte, musique upbeat, plans
   de coupe : je lance. Une promo ou un sujet à éviter ? dis-le maintenant. »). Ensuite plus de questions de
   réglage : on montre un aperçu et l'utilisateur corrige en français. Les réglages connus ne sont que des valeurs par
   défaut : la demande du moment gagne (« cette fois en 16:9 », « plus sobre ») sans toucher aux réglages.
7. **Garder les réglages** : quand l'utilisateur valide l'aperçu et que ses choix diffèrent des réglages connus (ou
   qu'il n'y en a pas), question à choix « Je garde ces réglages pour les prochaines vidéos <marque> ? » (« Oui, pour
   <marque> » / « Non, juste pour cette vidéo »). Si oui : `scripts/onboard.py profil --marque <m> --parcours <p>
   format=… style=… reseaux=a,b musique=… broll=oui|non sous_titres=oui|non ton=… public=… cta="…"`. Un retour qui vaut
   pour la suite (« jamais de rouge ») : `scripts/gouts.py add <client> "<ses mots>"`, avec son accord. Une demande
   ponctuelle ne s'enregistre jamais. Détails : references/habillage-marque.md.

## Quel parcours ?

| Demande | Parcours | Point de départ | Détails |
|---|---|---|---|
| Le client va filmer lui-même | guide de tournage | `guide.py` (à lui envoyer AVANT) | references/guide-tournage.md |
| Rush face caméra, interview courte | rush -> reel | `transcribe.py` | references/derush.md |
| Rush où l'on parle, rendu « expert » | écran partagé | `--layout split` + `panels.json` | references/ecran-partage.md |
| Rush plein écran, mot géant derrière la personne | mots dynamiques | `build_composition.py --mots` | references/mots-dynamiques.md |
| Bien immobilier, ton luxe | immobilier / luxe | sous-titres `editorial` + blocs en verre | references/immobilier-luxe.md |
| Clips sans paroles (chantier, ambiance, plats, événement, produit, voyage) | montage | `footage.py scan` | references/montage-sans-paroles.md |
| Plusieurs petits clips (téléphone) | plusieurs rushs puis rush -> reel | `multi.py list` | references/derush.md |
| Texte prévu avant de filmer | script écrit | `script.py prompteur` | references/derush.md |
| Expliquer un service / un déroulé, sans rush | explainer papier | `build_explainer.py` | references/packs.md |
| Photos + idée / texte, pas de rush | sans rush | un modèle de `templates/` (promo, boutique, recrutement, témoignage, produit) | references/voix-sans-rush.md |
| Annonce / promo / récap rythmée | actu / punch | `build_punch.py` | references/packs.md |
| Bilan, étude de cas, chiffres clés | infographie | `build_data.py` | references/packs.md |
| Motion design sur musique, sans voix | collage éditorial | `build_collage.py` | references/packs.md |
| Longue vidéo -> plusieurs reels | shorts | `shorts.py sentences` | references/shorts.md |
| Même vidéo dans une autre langue | versions traduites | `translate.py export` | references/traduction-lot.md |
| Plusieurs vidéos × langues × formats | lot | `templates/lot-exemple.json` + `batch.py plan` | references/traduction-lot.md |
| Planning de publication d'un lot | calendrier | `planning.py` | references/traduction-lot.md |
| S'inspirer d'un reel, montrer le skill | référence / vitrine | `reference.py analyse`, `showcase.py` | references/vitrine-reference.md |

Toujours : charte du client dans `brands/` (`new_job.py` répond `charte: "trouvée" | "absente"` ; absente -> choisis
dans `marques` / `proche` ou crée-la depuis `brands/_exemple/`), recherche dans la bibliothèque avant de créer,
`check` + `snapshot` avant de montrer, pas de rendu final sans accord.

## Les règles qui ne se négocient pas

> **Tu n'écris JAMAIS un timestamp.** Le OÙ couper vient des outils (mots horodatés + silences mesurés) ;
> le QUOI garder vient de ton jugement. Dans les JSON, tu n'écris que `keep`, `punch`, `reason`, et tu peux
> corriger l'orthographe d'un mot (`w`), jamais ses temps. Tout ce qui s'affiche se pose sur un **mot dit**.

- Ne jette jamais un îlot que tu n'as pas lu ; `reason` pour chaque îlot jeté ; dans le doute, garde (un tic qui
  porte le sens reste). Détails : references/derush.md.
- **Contenu réel uniquement** : chiffres, avis, prix, dates, classements, noms et fonctions viennent du client ; une
  image de banque illustre (ambiance, gestes) et n'est jamais présentée comme le client, son équipe ou son produit ;
  jamais de faux avis, de faux concurrent nommé, de citation inventée ni d'accroche de marque inventée.
- **Regarde avant de montrer** : `( cd <job> && npx --yes hyperframes@0.9.71 check )` 0 erreur, puis `snapshot`
  (visage non couvert, texte dans la zone sûre), puis `scripts/qa.py <job> <slug>` sur l'aperçu. Ne dis jamais
  « parfait » : c'est l'utilisateur qui juge. **Pas de rendu final sans accord.** Détails : references/controle-qualite.md.
- **Sources imposées** : voix off Gemini TTS (`GEMINI_API_KEY`, gratuit) par défaut, Fish Audio (`FISH_API_KEY`,
  payant) pour cloner une voix (accord écrit de la personne), un enregistrement du client (`--file`), Kokoro local
  (`ff_siwis`) seulement pour tester ou dépanner ; SFX = banque `sounds/` (via `real-sfx`), jamais de son synthétisé ;
  musique = `openverse-sfx` (CC0 / CC-BY / PDM, `credits.txt` livré) ; transcription locale (faster-whisper
  large-v3-turbo), Groq seulement si l'audio peut sortir de la machine ; Parakeet (`npx hyperframes transcribe`)
  écarté : il bascule en anglais au milieu du français. Pas de connexion HeyGen ni de crédits payants sans accord
  explicite (le skill `media-use` la propose d'office).
- **Rien n'est envoyé ni publié par toi** : page de validation, guide de tournage, livraison, planning passent par
  l'utilisateur.
- **Bibliothèque** : avant de créer un motion, `scripts/library.py search "<besoin>"` (couvre aussi le registre
  HyperFrames) ; après validation d'un motion, propose en une ligne de le sauvegarder (`library.py save`), jamais
  sans accord. Détails : references/motions-blocs.md.

## Parcours « rush -> reel sous-titré »

```bash
python .claude/skills/videomaker-deeplo/scripts/new_job.py "<client>" "<sujet>" --brand <dossier> --rush <fichier>   # jobs/<date>-<client>-<sujet>/ ; regarde "charte"
python .claude/skills/videomaker-deeplo/scripts/transcribe.py <job> <rush>                  # local ; --islands si le client se reprend ; --engine groq si accord
#   noms propres (marque, lieux, produits) : un par ligne dans <job>/noms.txt ou brands/<marque>/noms.txt, AVANT de transcrire
python .claude/skills/videomaker-deeplo/scripts/cut_plan.py <job> <slug>                   # îlots de parole, bords dans les silences
#   TU décides : keep / reason dans work/<slug>_plan.json (references/derush.md)
python .claude/skills/videomaker-deeplo/scripts/build_cut.py <job> <slug>                   # assets/<slug>_cut.mp4 + map.json (voix à -16 LUFS)
#   rush de téléphone (HDR, rotation, cadence variable) : REGARDE work/<slug>_controle.jpg (original | importé) au 1er rush
python .claude/skills/videomaker-deeplo/scripts/build_text.py <job> <slug>                  # captions + overlays candidats + punchs proposés
#   TU vérifies : orthographe des captions, keep / punch / reason des overlays (references/sous-titres.md)
python .claude/skills/videomaker-deeplo/scripts/add_music.py <job> <slug> --mood upbeat     # references/son-musique.md
python .claude/skills/videomaker-deeplo/scripts/broll.py moments <job> <slug>               # plans de coupe, facultatif (references/plans-de-coupe.md)
python .claude/skills/videomaker-deeplo/scripts/build_composition.py <job> <slug> --style pop --mode captions   # + --emoji, --zooms, --mots, --layout split|cards
( cd <job> && npx --yes hyperframes@0.9.71 check )                                     # 0 erreur exigée
( cd <job> && npx --yes hyperframes@0.9.71 snapshot --at T1,T2,T3 )                    # REGARDE la planche avant de montrer
( cd <job> && npx --yes hyperframes@0.9.71 preview )                                   # Studio pour l'utilisateur
python .claude/skills/videomaker-deeplo/scripts/brouillon.py <job> "<ce qui change>" --rapide   # aperçu renders/v<N>-….mp4 + work/journal.md
python .claude/skills/videomaker-deeplo/scripts/qa.py <job> <slug>                          # « à revoir » = corriger avant de montrer
python .claude/skills/videomaker-deeplo/scripts/review.py <job> --qa                        # page de validation client (envoyée par l'utilisateur)
python .claude/skills/videomaker-deeplo/scripts/review.py <job> --valide                    # accord du client, puis seulement le rendu final
( cd <job> && npx --yes hyperframes@0.9.71 render -q delivery -w 8 -o renders/<slug>.mp4 )
python .claude/skills/videomaker-deeplo/scripts/finalize.py <job> <slug>.mp4                # master -14 LUFS -> renders/<slug>_final.mp4
```
Styles de sous-titres : pop, karaoke, minimal, boite, impact, duo, mono, bulle, souligne, geant, editorial (`seam`
automatique en écran partagé). Rushs de téléphone, rush filmé en marchant, rush paysage, plusieurs rushs, script écrit :
references/derush.md. Sous-titres qui évitent le visage, style `geant` et cartes sur vidéo floutée :
references/sous-titres.md. Accroche animée, titre derrière la personne, zooms : references/accroches.md,
references/mots-dynamiques.md. Blocs par-dessus le rush (`work/<slug>_motions.json`), suggestions automatiques
(`suggest_motions.py`), emojis animés, piles d'outils, fin « Commente : MOT » : references/motions-blocs.md.
Bruitages automatiques et musique qui s'efface sous la voix : references/son-musique.md.

## Parcours « sans rush » : photos + texte -> vidéo animée

Lis `references/storyboard.md`, écris `work/<slug>_storyboard.json` à partir du brief et des photos (`inbox/`),
montre-le en texte (une ligne par scène : type, texte écran, voix), puis :
```bash
python .claude/skills/videomaker-deeplo/scripts/voice.py <job> <slug>            # Gemini si clé, sinon Fish, sinon voix locale ; ou --file <enregistrement>
python .claude/skills/videomaker-deeplo/scripts/build_text.py <job> <slug>
python .claude/skills/videomaker-deeplo/scripts/add_music.py <job> <slug> --mood <ambiance>
python .claude/skills/videomaker-deeplo/scripts/build_scenes.py <job> <slug>     # scènes hook / photo / points / stat / offer / quote / gallery / cta
( cd <job> && npx --yes hyperframes@0.9.71 check && npx --yes hyperframes@0.9.71 snapshot --at <milieu de chaque scène> )
```
Noms propres : demande la prononciation AVANT de générer la voix (lexique de la marque). En gratuit, Google peut
utiliser les textes envoyés : rien de confidentiel dans la voix off. Pas assez de photos : `broll.py auto <job> <slug>
--storyboard`. Intro / outro de marque : scènes `intro-marque` / `outro-marque`. Détails : references/voix-sans-rush.md,
references/plans-de-coupe.md, references/habillage-marque.md. Explainer, punch, infographie, collage :
references/packs.md. Clips sans paroles : references/montage-sans-paroles.md.

## Parcours « une longue vidéo -> plusieurs shorts »

`transcribe.py <job> <vidéo> --slug <s>` -> `shorts.py sentences <job> <s>` (tu lis TOUTE la liste et écris
`work/<s>_shorts.json` : 3 à 5 passages de 20 à 60 s qui se comprennent seuls, en NUMÉROS de phrases, avec `hook`
≤ 7 mots) -> `shorts.py make <job> <s> [--style <style>] [--mood upbeat]` (un job enfant par short ; la fenêtre 9:16
suit le visage) -> check + snapshot sur chacun -> `deliver.py <job>-<nom> short --formats 9:16`.
Détails : references/shorts.md.

## Livraison (tous les parcours)

1. `scripts/post.py draft <job> <slug>` rassemble la matière (accroche, phrases fortes, brief, mentions, hashtags
   marque / ville / sujets) dans `work/<slug>_post_draft.json` ; réécris-le, puis `post.py check` (longueur de la
   première ligne, hashtags, mentions obligatoires, « à éviter », chiffres absents de la vidéo) et `post.py date`
   (prochain créneau libre de la marque, `renders/publication.ics` à importer ; jours / heure : `"publication"` dans
   brand.json). Écris `work/<slug>_post.json` : `caption` (2-3 phrases dans le ton de la marque, sans promesse
   inventée), `cta`, `hashtags` (5 à 8, locaux + métier), `first_comment` facultatif. Marque-le « brouillon à valider ».
2. **Couverture avec titre** (facultatif, conseillé pour YouTube et les Reels épinglés) :
   `scripts/covers.py <job> <slug> --title "<titre 1>" --title "<titre 2>"` — titres de 6 mots max tirés de la
   promesse DITE dans la vidéo (jamais une promesse inventée). L'outil prend les 3 meilleurs plans du visage (net,
   grand, bien éclairé, yeux ouverts ; vidéo sans rush : photos des scènes) et compose 3 maquettes dans la charte : a « bandeau »,
   b « impact », c « côté », en 9:16, 1:1 et 16:9. Montre `renders/covers/planche.jpg`, puis
   `scripts/covers.py pick <job> <slug> a|b|c` : `deliver.py` livre alors cette couverture pour chaque format (sinon,
   image de la vidéo sans sous-titres). Le titre reste dans les 1080×1440 du centre (ce que montre la grille du profil).
3. Avant de lancer : `--size 1:1` et `--size 16:9` sur le builder + `snapshot` pour vérifier la mise en page
   (explainer, punch et infographie ont une vraie mise en page 16:9 : contenu à gauche, texte à droite ; le 1:1 reste
   tiré du 9:16).
4. `scripts/deliver.py <job> <slug> --formats 9:16,1:1,16:9 --quality delivery` (`--apercu` pour un aperçu ≈ -40 %,
   `--lang nl` pour une version traduite) : pour chaque format, composition à la bonne taille (texte à gauche et image
   à droite en carré / paysage ; rush en format différent = image entière sur fond flouté), rendu, master -14 LUFS,
   couverture, contrôle `qa` et conformité (h264 yuv420p, taille exacte, cadence fixe, AAC 48 kHz stéréo, BT.709) ; puis
   `renders/livraison/` avec `livraison.html` (lecteurs, téléchargements, texte du post à copier, crédits à part :
   jamais dans le post ; `a_citer` = licences BY à mentionner ailleurs), `post.txt`, `credits.txt`. Compter ~3 à 4 min
   de rendu par format pour 30 s de vidéo ; un rendu à la fois (~0,18 s par image, rien ne l'accélère sauf moins
   d'images). La livraison = l'aperçu validé : les options du monteur sont relues dans `work/<slug>_build.json` et
   repassées à chaque format (fichier absent : « avertissement », relancer le monteur puis deliver.py). Cadence = celle
   du cut (24 / 25 / 30 ; 50 -> 25, 60 -> 30) sauf `--fps` ; le 1:1 dérivé est recalculé en lanczos, fond flou en petit.
5. Ouvre `livraison.html` pour l'utilisateur. N'envoie jamais rien au client toi-même.
6. Après validation : propose de garder les réglages (accueil, point 7) et de sauvegarder les motions réussis dans la
   bibliothèque. Variantes d'accroche A/B à tester : references/accroches.md. Traductions, lot, calendrier :
   references/traduction-lot.md.

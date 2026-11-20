# 🎬 Deeplo Video Maker

Des vidéos prêtes à poster pour votre entreprise, montées par Claude à partir de vos rushs, photos et idées.
Tout se passe dans Claude Code, en français : vous décrivez, Claude monte, vous validez.

## Ce que ça fait

| Vous donnez | Vous recevez |
|---|---|
| Plusieurs **petits clips** filmés au téléphone, dans le désordre | Une seule vidéo dans l'ordre du propos, avec la meilleure prise de chaque phrase |
| Un **rush face caméra** (même avec des ratés et des reprises) | Un reel serré : meilleures prises, blancs, « euh » et bégaiements coupés, sous-titres mot à mot, zooms, sons, musique, et vos photos (ou des images et vidéos Pixabay) qui illustrent ce qui est dit |
| Des **photos + une idée** (ou un texte) | Une vidéo animée dans vos couleurs, avec voix off, sous-titres et musique ; pas assez de photos ? des images et vidéos d'ambiance Pixabay |
| Une **longue vidéo** (interview, webinaire, live) | 3 à 5 shorts qui se comprennent seuls, avec un titre d'accroche |
| Une vidéo déjà faite | Sa version **sous-titrée en néerlandais ou en anglais** (accroche et post traduits aussi) |
| Un **lien de musique** ou votre propre fichier | La musique calée sous la voix (droits à vérifier pour un lien) |

À chaque livraison : les formats **9:16** (Reels, TikTok, Stories), **1:1** et **16:9**, une **couverture** (avec titre
au choix parmi 3 maquettes), le
**texte du post** avec hashtags, les **crédits** musique, et une page récap `livraison.html`. Plusieurs vidéos et
langues d'un coup : une seule page pour tout le lot, et un **planning de publication** (jours, heures par réseau,
texte à copier, rappels dans votre agenda).

Toutes les vidéos d'une marque peuvent recevoir le même **habillage** : logo animé en ouverture, bandeau
« Prénom, fonction », fin avec logo et accroche, dans les couleurs et la police de la marque.
15 types de scènes : accroche, photo, liste, chiffre clé, offre, avis client, galerie, étapes, avant/après,
produit détouré, équipe, adresse et horaires, téléphone (capture d'Instagram ou d'une app), navigateur (votre site),
appel à l'action. Transitions : volet, fondu, iris, zoom, flou.

**Motion design** posé sur le mot dit (« 4,8 étoiles », « -30 % », « suivez-nous ») : 17 blocs réglables (compteur,
étoiles, jauge, bouton, compte à rebours, notification, sticker, surligneur, flèche, suivre, confettis, bandeau
défilant, mot qui tourne, barres, frise, machine à écrire, carte tarifaire) et 24 emojis animés. Claude propose
lui-même où les placer à partir de ce qui est dit ; vous gardez ou retirez. Tout est visible dans la galerie
`library/index.html`.

## Comment s'en servir

1. Ouvrez ce dossier dans Claude Code (première fois : « Lis INSTALL.md et installe tout »).
2. Demandez, par exemple :
   - « Monte ce rush pour un reel Instagram : `C:\…\video.mp4` »
   - « Fais une vidéo de 30 s pour présenter la boutique avec ces photos : `C:\…\photos\` »
   - « Même vidéo, en style karaoké et avec la musique chill » (styles : pop, karaoké, minimal, boîte, impact, duo,
     avec ou sans emojis)
   - « Ajoute des plans de coupe avec les photos de la boutique »
   - « Refais la scène 3, le titre est trop long »
   - « Sors 4 shorts de ce webinaire, en français et en néerlandais »
   - « Fais une annonce de recrutement avec ces photos de l'équipe » (modèles prêts dans `.claude/skills/videomaker-deeplo/templates/`)
   - « Ajoute des motions sur les chiffres » · « Mets un compteur sur 1 200 clients et des confettis à la fin »
   - « Fais les 3 vidéos du lot en FR et NL, en 9:16 et 1:1 » (`templates/lot-exemple.json`)
3. Claude montre ce qu'il compte faire (coupes, storyboard), puis un aperçu. Vous corrigez en français.
4. « Livre-la » : les fichiers arrivent dans `jobs/<date>-<client>-<sujet>/renders/livraison/`.

## Conseils de tournage (rush)
Pour un client qui filme lui-même : « Fais le guide de tournage pour <client>, métier restaurant » donne une page
complète à lui envoyer (cadrage, lumière, son, quoi dire, plans à filmer, comment envoyer les fichiers). L'essentiel :
- Téléphone en vertical, à hauteur des yeux, lumière face à vous, micro-cravate si possible.
- Lisez phrase par phrase ; trompez-vous autant que vous voulez, laissez une seconde de silence et reprenez.
  Vous pouvez dire « celle-là est ratée, je la refais » : Claude comprend et garde la bonne prise.

## Bon à savoir
- **Rien n'est inventé** : pas de faux avis, de faux chiffres ni de fausses promotions. Les textes proposés par Claude
  sont des brouillons à valider.
- **Vos fichiers restent sur votre ordinateur** : la transcription est locale. Seuls les textes de la voix off de synthèse partent chez Google (Gemini) ou Fish Audio.
- **Images de banque** (Pixabay, clé gratuite dans `.env`) : ambiance seulement, jamais présentées comme votre
  boutique, votre équipe ou votre produit ; crédits livrés.
- **Hésitations** : les « euh », bégaiements et longs blancs sont retirés ; les « du coup », « en fait »… ne le sont que
  s'ils n'apportent rien. Écoutez les jointures avant de publier.
- **Musique** : la banque fournie est libre de droits (CC0 / CC-BY, crédits livrés). Un lien YouTube ou SoundCloud
  n'est pas une licence : n'utilisez que de la musique dont vous avez les droits.
- **Voix off** : une voix de synthèse naturelle (Gemini, gratuite), ou **votre propre enregistrement** (mémo vocal,
  micro, ou le son d'une vidéo) sur lequel les scènes se calent toutes seules.
- **Voix clonée** : uniquement la vôtre ou celle d'une personne qui a donné son accord écrit.
- Rendu : 3 à 4 minutes par format pour une vidéo de 30 secondes ; un aperçu rapide (15 i/s) prend 40 % de moins.

## Mises à jour (équipe Deeplo)
Le projet est sur un dépôt Git privé. Première fois : `git clone <adresse du dépôt>`, puis
« Lis INSTALL.md et installe tout ».
Ensuite, pour récupérer les nouveautés : « Mets le video maker à jour » (Claude fait `git pull`).
Vos vidéos (`jobs/`) et vos clés (`.env`) ne partent jamais sur GitHub.

## Dossiers
`jobs/` vos vidéos · `brands/` vos chartes · `library/` les animations validées (galerie : `library/index.html`) ·
`sounds/` la banque de sons et musiques · `studio/` le projet HyperFrames de base.

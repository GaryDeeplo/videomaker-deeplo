# Nouveautés

Chaque section « ## <version> » liste ce qui a changé. L'accueil du skill prévient quand une version plus récente est
publiée ; « mets à jour le skill » lance `python .claude/skills/videomaker-deeplo/scripts/update.py install`.

## 2026.11.28
- Catalogue en rafale (« N trucs que… ») : tu énumères face caméra et chaque mot dit allume son élément dans un sommaire numéroté et lance sa démo dans un téléphone (aperçu de la bibliothèque ou ton clip) ; personne décalée pour faire la place, sortie de l'habillage en flou, pas de sous-titres pendant.
- Quatre effets sur la personne, posés sur des mots dits : vertigo (le décor recule, la personne garde sa taille), frame break (l'image rétrécit dans un cadre de Reel, la tête en sort), doodle boil (contour dessiné qui tremble + petits dessins) et zoom-through (zoom à travers l'image sur une coupe) ; nom de l'effet affichable en pastille.
- Le contrôle qualité tient compte du décalage de la personne pendant le catalogue ; la synthèse des références reconnaît ces nouveaux dispositifs.
- Bibliothèque : catalogue et effets, avec aperçus.

## 2026.11.27
- Montage d'images avec voix off : blocs en verre et cartes posés sur les mots (chiffre, recherche, carte du monde…), barre de progression, sous-titres éditorial ; une carte de fin en verre (texte ou logo sur la vidéo floutée) coupe les sous-titres dessous.
- Accroche animée : le titre prend la police de titre choisie (paire de polices) et les jambages (g, p) ne sont plus rognés pendant l'apparition.
- Voix Fish : ton réglable (balise d'émotion, voix naturelle par défaut), modèle gratuit quand le crédit API est épuisé, choix d'une prise à l'écoute.

## 2026.11.26.2
- Accueil : trois nouvelles questions avant l'habillage — « Quel look ? » (tuto cartes, luxe éditorial, écran partagé, classique), « Quelle ouverture ? » (sujet dessiné, nom derrière la personne, titre animé, sans) et « Quelles polices ? » (planche d'aperçu de paires de polices Google libres, ou la charte).
- Nouvelle marque : entretien de style et charte en chiffres (couleurs hex, paire de polices copiée avec sa licence, style de sous-titres, rythme punchy ou doux, interdits gardés comme goûts du client).
- Rushs de téléphone : HDR HLG d'iPhone converti sans tone-mapping (peau naturelle), image de contrôle original / importé, liste de noms propres (`noms.txt`) pour une transcription juste.
- Livraison : zones des applis plus prudentes, couvertures lisibles dans la grille du profil et jamais les yeux fermés, rendu final plus net, brouillons numérotés avec un journal des versions.
- Verre teinté lisible sur un ciel clair ; les sous-titres contournent les blocs posés ; pile d'outils propre en 16:9 ; traductions découpées comme la version d'origine.
- Bibliothèque : blocs en verre, sous-titres éditorial et géant, cartes en verre, avec aperçus.

## 2026.11.26
- Style TikTok « tuto » : sous-titres `geant` (un mot énorme à la fois, mots déjà dits en petit), mot en escalier de syllabes (« IN- / CRO- / YABLE »), cartes au milieu sur vidéo floutée (qui reste nette entre deux cartes), vraie capture d'écran en carte, carte « Suivre » en fin.
- Pack immobilier / luxe : sous-titres `editorial` (petits mots en sans fine, mot fort en serif italique), mots géants dans le décor (serif, ou posés au sol), blocs en verre (recherche qui se tape, carte du lieu avec épingle, cartes photo en 3D, chiffre géant qui compte avec cote fléchée, fin sur le logo), barre de progression.
- Accueil : en 3 séries de questions au plus ; analyse du contenu puis propositions d'habillage en choix multiple (carte et distances, chiffres et calculs, pictos et emojis animés, accroche dessinée…).
- Son : bruitages enfin au bon niveau et calés sur leur pic, nouveaux sons (sub-drop, verre, souffle doux, tap, page), variété d'une vidéo à l'autre, bruitage de caisse sur les prix ; voix travaillée (EQ, de-esser, compresseur) ; musique choisie et calée automatiquement ; master plus propre.
- Image : dérush quasi sans perte, petites sources (WhatsApp) agrandies proprement et sans zoom, couleurs BT.709, HDR sans bandes, cadence 24 / 25 respectée.
- Livraison identique à l'aperçu validé (les options du montage sont reprises pour chaque format) ; crédits jamais dans le texte du post.
- Sous-titres : taille mesurée, ? et ! gardés, nombres et petits mots jamais coupés, encre sombre automatique sur fond clair ; cartes : thème verre, entrées variées, cartes limitées à 4 s ; plusieurs bugs de maquettes corrigés.
- Contrôle `tools/selftest.py` avant chaque version ; SKILL.md allégé (détails dans references/).

## 2026.11.25
- Dérush : aucune coupe ne tombe plus sur des yeux fermés. Si une coupe tombe sur un clignement, elle glisse de quelques images vers des yeux ouverts, sans entrer dans un mot ; le rapport du dérush dit lesquelles ont bougé. Facultatif (MediaPipe, installé par `setup.py install` ; `check.py` dit s'il manque).

## 2026.11.24.3
- Livraison : les crédits ne vont plus jamais dans le texte du post ; ils restent dans `credits.txt` et dans la page de livraison, et les licences BY (mention obligatoire à la publication) sont signalées à part.
- Contrôle qualité : plus d'avis sur les sous-titres quand la vidéo n'en a pas (mots dynamiques).

## 2026.11.24.2
- Page de validation client avant le rendu final (`review.py`) : une image à chaque coupe et à chaque temps fort, avec le texte dit, une remarque possible sous chaque image, « Copier la liste des changements » et « Tout est bon » ; l'accord est noté (`--valide`) avant le rendu final.
- Sous-titres qui évitent le visage (sous le menton, sinon au-dessus de la tête), dans les zones sûres de chaque plateforme ; contrôle « visage couvert » sur les textes, cartes, blocs et mots géants.
- Rushs de téléphone : cadence variable remise à fixe, rotation lue, HDR converti en SDR.
- Conformité de chaque fichier livré (h264, taille exacte, cadence, AAC 48 kHz stéréo, couleurs, poids) avec une pastille dans la page de livraison ; master du son plus fiable.
- Contrôle qualité : micro-coupures, image isolée, première image unie ; reprises cachées repérées au dérush.
- Retours gardés par client (« jamais de rouge », « musique plus douce »), réutilisés aux vidéos suivantes.
- Mots dynamiques : l'accueil demande « Sous-titres sur toute la vidéo ? » au lieu de les couper sans prévenir.
- Registre HyperFrames : 50 blocs et composants de plus avec aperçu (199 au total).

## 2026.11.24
- Mots dynamiques : un mot géant par idée, qui passe derrière la personne quand le cadrage le permet (sinon devant), petits mots autour, carte de verre qui reprend la phrase, compteur en grille d'icônes ou en barre, transition fouettée aux coupes ; couleur tirée de l'image si la charte n'en impose pas.
- Vitrine « Brut / Montage » (le rush d'origine à côté du montage, coupes visibles), démo dans une appli d'agent (objection épinglée, effets cochés, téléchargement) et vitrine portfolio (3 vidéos en quinconce).
- Collage éditorial sans voix, sur la musique : papier crème, serif Didone, objets photo détourés, étiquette dont le mot change, objet qui se fend en morceaux étiquetés, formes d'accent, petites silhouettes.
- Écran partagé : nouvelles maquettes (réglages avec consigne tapée, publication recréée, mur de texte + loupe, tableau à palettes, carte du monde, calendrier, timeline de montage, devis, revenus, horloge), alternance plein écran / écran partagé, pack éditorial (sur-titres, fond papier, fil conducteur, repères de coin).
- Sous-titres : styles « bulle » (message) et « souligne » (éditorial) ; reel sans parole avec bulles posées sur la musique.
- Bloc « scan du visage » ; registre officiel HyperFrames dans la bibliothèque (149 blocs et composants avec aperçu, installables en une commande) ; galerie : nouveautés en premier.

## 2026.11.23.5
- Piles de cartes d'outils : captures des sites prises en local, présentées par 3 sur votre vidéo floutée, au rythme de la musique.
- Fin « Commente : MOT » : le mot s'écrit, un commentaire arrive, puis le message reçu.
- Rush filmé en marchant : les passages qui tremblent sont stabilisés et les passages flous un peu renforcés, sans toucher au son.
- Analyse de références : synthèse de tous les reels analysés (types d'accroche, dispositifs, fins, ce qui manque encore).
- Contrôle qualité : vitesse des sous-titres jugée comme pour des sous-titres calés mot à mot ; zooms jamais sur un petit mot.

## 2026.11.23.4
- Montage depuis un script écrit : prompteur sur téléphone pour le tournage, puis meilleure prise de chaque phrase gardée toute seule, phrases manquantes et passages hors script signalés.
- S'inspirer d'un reel qui marche : son rythme est mesuré (plans, coupes, débit, tempo, place de l'accroche) et appliqué à votre montage, sans rien copier de son contenu.
- Démos : voix Gemini pour le coach et le fleuriste, nouveau showreel, aperçu animé dans le README.

## 2026.11.23.3
- La musique s'efface toute seule quand on parle et sous chaque bruitage, puis remonte dans les silences.
- Titre géant derrière la personne : détourage en local, la tête passe devant les lettres.
- Montage sans paroles : ralenti automatique sur le geste fort (coup de marteau, pâte qui s'étire), léger accéléré des passages calmes.
- Texte du post : premier jet tiré de ce qui est dit et du brief, vérification (mentions obligatoires, chiffres, longueur) et date de publication proposée avec rappel d'agenda.

## 2026.11.23.2
- Vraie mise en page 16:9 pour l'explainer, l'actu / punch et l'infographie (contenu à gauche, texte à droite), pour YouTube et LinkedIn.
- Zooms sur les mots appuyés dans un rush face caméra (coup sec ou glissé), choisis d'après la voix et le texte.
- Sound design automatique : un bruitage discret sur chaque apparition (changement de plan, élément de liste, chiffre, bouton, notification), dans tous les rendus.
- Variantes d'accroche A/B : 2 ou 3 versions des 3 premières secondes sur le même montage, avec une page pour les comparer et suivre les résultats.
- Accroches animées : un titre long passe sur 2 ou 3 lignes au lieu de rapetisser.

## 2026.11.23
- Livraison de tous les rendus (montage, infographie, actu / punch, fiche animée) : le bon monteur est choisi tout seul ; les rendus pensés en vertical sortent aussi en 1:1 et 16:9 sur fond flouté.
- Contrôle qualité automatique avant de montrer une vidéo (`qa.py`) : plans trop courts, images noires ou figées, volume, trous de son, sous-titres trop rapides.
- Coupes calées sur les temps de la musique (montage sans paroles et actu / punch).
- Images sans paroles : stabilisation automatique des passages filmés à main levée, et recadrage vertical posé sur le sujet (visage, ou ce qui bouge et est net) au lieu du milieu.

## 2026.11.22.2
- Accroche avec le sujet dessiné : le plat, la façade ou le produit apparaît dans le style choisi (tracé au trait, rebond, papier qui tombe…).
- À l'accueil, une question « Accroche animée ? » (non / titre animé / avec le sujet dessiné), retenue pour la marque si vous le voulez.
- Vérification de l'installation plus tolérante (la voix locale suffit pour tester) ; l'accroche en scène garde les couleurs de son style.

## 2026.11.22
- Accroches animées de 3 s en 10 styles (papier, plan technique, pâte à modeler, néon, aquarelle, pixel, isométrique, mosaïque, encre, relief 3D).
- Images sans paroles (chantier, ambiance, plats, événement) : meilleurs passages repérés tout seuls, accélérés, « JOUR 12 », avant / après, journal de chantier.
- Maquettes animées : formulaire, chat, classement, recherche, progression, entonnoir, flux « en direct », site annoté, carte de dépôt GitHub, code avant / après.
- Infographie chiffrée (barres, compteur à volets, courbe, pourcentages, foule de pictos) et format liste « 1 sur 5 ».
- Vrais logos d'outils (logo:claude, logo:notion…), sous-titres « mono », thème clair et cartes sur le visage.
- Le pack (rendu) est choisi tout seul et le premier jet des animations est écrit automatiquement.
- Mises à jour : vérification à l'accueil et installation en une commande, sans toucher à vos fichiers.

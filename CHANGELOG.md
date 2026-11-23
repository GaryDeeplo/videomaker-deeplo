# Nouveautés

Chaque section « ## <version> » liste ce qui a changé. L'accueil du skill prévient quand une version plus récente est
publiée ; « mets à jour le skill » lance `python .claude/skills/videomaker-deeplo/scripts/update.py install`.

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

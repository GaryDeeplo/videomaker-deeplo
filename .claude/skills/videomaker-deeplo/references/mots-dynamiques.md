# Mots dynamiques, titre derrière la personne, zooms sur les mots forts

Scripts depuis la racine du projet : `PYTHONUTF8=1 python .claude/skills/videomaker-deeplo/scripts/<x>.py`. Rush face caméra, cadrage plein écran.

## Mots dynamiques (style « dynamic word reels »)
`python .claude/skills/videomaker-deeplo/scripts/build_composition.py <job> <slug> --mots` : un mot géant par idée DERRIÈRE la personne (détourage local,
calculé seulement là où il sert, haut de la tête mesuré par passage), les petits mots de la phrase posés autour, une
carte de verre en bas qui reprend la phrase avec un picto, sortie en traînée de flou, transition fouettée + petite
secousse à chaque coupe du dérush. Un chiffre : `"count": {"to": 50, "icon": "house"}` (grille d'icônes qui
s'allument, ≤ 60) ou `{"to": 365, "unit": "jours"}` (barre + compteur).
**Remplace les sous-titres** (`--mode captions` pour garder les deux) : c'est une option de la série 3 de l'accueil
(« sous-titres complets en plus »), jamais décidé en silence. Par défaut : « non, les mots géants et la carte de verre
suffisent (recommandé) » ; recommande « oui, sous-titres complets en plus » (`--mode captions`) si la vidéo sera surtout
vue sans le son (LinkedIn, public pro). Ne la pose pas si la demande ou les réglages de la marque (`sous_titres=`) y
répondent. Avec les deux, les sous-titres se posent sous le menton et les mots géants restent en haut.
Couleur : `mots.couleur` dans la config > accent de la charte du client > tirée de l'image (teinte dominante du rush ;
scène très colorée -> teinte opposée ; jamais de vert acide), en dégradé clair comme la référence. Proposé dans
`work/<slug>_mots.json` (1er lancement) : relis-le (mot fort, satellites, carte, picto), puis relance.
Plein écran seulement (pas en écran partagé, fond flouté ni suivi du visage). Compter 1 à 4 min de détourage.
Cadrage : le mot ne passe DERRIÈRE la tête que s'il y a de la place au-dessus (plan large, tête sous le haut du cadre,
comme les références filmées en pied) ; en plan serré (tête collée au haut), il se met devant, en haut, sinon le visage
le cache. Rapport : `"place": "derrière" | "devant (cadrage serré)"`. Rush paysage : `visual.fit: "cover"` +
`visual.focusX` (ex. 30) pour centrer la personne, vérifie sur le snapshot.
Variante luxe (serif, mot posé au sol) : `references/immobilier-luxe.md`.

## Titre derrière la personne
`python .claude/skills/videomaker-deeplo/scripts/build_composition.py <job> <slug> --derriere "Montage automatisé" --derriere-mot montage` (ou
`"behind": {"text", "word", "dur"}`). Détourage local (`cutout.py`, rembg, ~30 s pour 2,6 s), titre géant calé sur le
haut de la tête : la tête passe devant les lettres. Une fois par vidéo, sur l'idée principale ; snapshot obligatoire
(le titre doit rester lisible malgré la tête).

## Zooms sur les mots forts
`python .claude/skills/videomaker-deeplo/scripts/build_composition.py <job> <slug> --zooms` (ou `"camera": {"zooms": true}`, `zoomsPerMinute` 8 par défaut).
Mots choisis par les mesures (`python .claude/skills/videomaker-deeplo/scripts/zooms.py <job> <slug>` les liste) : volume de la voix comparé aux 4 s autour,
mot étiré, chiffre ou mot fort ; jamais sur un petit mot ni à moins de 3,5 s du précédent. Coup sec et glissé en
alternance, retour à la fin de la phrase. À proposer d'office pour un ton dynamique.

Autres effets sur la personne détourée (vertigo, frame break, doodle boil, zoom-through) et catalogue en rafale :
`references/catalogue-effets.md`.

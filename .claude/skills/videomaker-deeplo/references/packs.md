# Packs sans visage : explainer papier, actu / punch, infographie chiffrée, collage éditorial

Scripts depuis la racine du projet : `PYTHONUTF8=1 python .claude/skills/videomaker-deeplo/scripts/<x>.py`. `npx` toujours lancé depuis le job :
`( cd <job> && npx --yes hyperframes@0.9.71 check )`.
Le pack est conseillé par `pack.py choose` (voir SKILL.md) ; le premier jet des temps forts vient de `pack.py draft`
(`references/ecran-partage.md`). 16:9 natif : `--size 16:9` sur ces builders (contenu à gauche, texte à droite) ; la
livraison l'utilise, le 1:1 reste tiré du 9:16.

## Explainer papier : vidéo sans rush façon fiche pratique
Pour expliquer un service, un déroulé, une offre : carte papier à ombre franche sur fond à carreaux (couleurs de la
charte), bandeau d'étapes fixe en haut (une puce par chapitre, la courante s'allume) + barre de progression du récit,
temps forts du panneau en thème papier, sous-titres karaoké dans un cadre (mot dit en encre, mot fort dans une boîte).
1. Storyboard : un champ `voice` par phrase (le `kind` n'est pas utilisé ici), avec les vraies infos du client.
   `jobs/<job>/config.json` : `{"text": {"captionMaxWords": 3}}`.
2. `voice.py` (Gemini / Fish / `--file`) -> `build_text.py` -> `add_music.py` (`references/voix-sans-rush.md`).
3. `work/<slug>_panels.json` : mêmes temps forts que l'écran partagé (`title`, `check`, `stat`, `search`, `image`,
   `steps`, maquettes, objets), avec `"chapter"` (2 à 5 chapitres de 1-2 mots : « AVANT », « LE SOIN », « APRÈS »,
   « RÉSERVER »).
4. `python .claude/skills/videomaker-deeplo/scripts/build_explainer.py <job> <slug>` (fin de marque si la charte en a une ; `--no-outro` sinon), puis
   check + snapshot + aperçu. Inspiré des explainers « interface papier » : principes repris, jamais les visuels.

## Actu / punch : annonce, promo, récap d'événement
Images plein cadre coupées vite (léger zoom + éclair à chaque coupe), gros titres condensés (Anton) qui s'empilent en
haut et claquent sur leur mot, objets qui collent aux mots (notification, étiquette prix, étiquette, document qui se
tape, date, chiffre, picto, emoji animé), sous-titres « impact » en bas (`--no-captions` pour s'en passer).
1. Médias dans `inbox/` (vidéos et photos du client, de son site) ; voix : storyboard + `voice.py` (un ton plus
   énergique : `python .claude/skills/videomaker-deeplo/scripts/voice.py <job> <slug> --style "Lis d'une voix énergique, rythmée comme une annonce"`),
   `build_text.py`, `add_music.py --mood upbeat`.
2. `work/<slug>_punch.json` (détails dans `scripts/build_punch.py`) : un temps fort par idée, posé sur un mot ; `media`
   (ou `query` puis `build_punch.py fetch` / `pick` : Pixabay + planche) — une coupe toutes les 1,5 à 3 s ; `title` :
   2-3 lignes de 1 à 3 mots (*mot* en couleur) ; `prop` : un objet par temps fort au plus.
3. `python .claude/skills/videomaker-deeplo/scripts/build_punch.py <job> <slug>` puis check + snapshot. Couleur d'accent : `visual.punchAccent` (une couleur
   de la charte qui se lit sur les images). Coupes calées sur les temps de la musique (0,2 s au plus, les titres restent
   sur leurs mots). Inspiré des formats « actu » courts : principes repris, jamais leurs visuels.
   Une notification est une illustration (contenu vrai), jamais une capture présentée comme réelle.

## Infographie chiffrée : raconter des résultats avec des graphiques
Sans visage, façon page de journal de données : fond papier, rubrique en haut (« VUES PAR REEL · JOUR 03 ») sous un
double filet, un graphique par idée, la phrase dite en bas qui passe du gris à l'encre (chiffres et mot fort en boîte),
frise des jours avec drapeau. Pour un bilan, une étude de cas, une méthode « en 14 jours », des chiffres clés.
1. Storyboard + `voice.py` + `build_text.py` + `add_music.py` (comme une vidéo sans rush).
2. `work/<slug>_data.json` (détails dans `scripts/build_data.py` ; premier jet : `pack.py draft <job> <slug> --pack
   infographie`) : un temps fort par chiffre dit, posé sur un mot ; types `bars` (barres qui poussent + compteurs),
   `grid` (« ×10 » + tuiles), `people` (foule de pictos + étiquette), `flip` (compteur à volets), `line` (courbe, en
   escalier si `steps`, notes « version 2 »), `pct` (pourcentages, le plus fort entouré), `days` (cases cochées +
   tampon), `title`, `end` (nom + lien). `head` et `day` restent acquis. Les maquettes de l'écran partagé marchent aussi.
3. `python .claude/skills/videomaker-deeplo/scripts/build_data.py <job> <slug>` puis check + snapshot. Accent : `visual.dataAccent`.
   **Uniquement des chiffres réels du client.** Un scénario d'exemple doit être dit comme tel à l'oral et à l'écran.

## Collage éditorial (motion design pur, sur musique, sans voix)
`python .claude/skills/videomaker-deeplo/scripts/build_collage.py <job> <slug>` (`work/<slug>_collage.json`, format dans l'en-tête du script ; musique par
add_music.py, les écrans tombent sur ses temps) : papier crème vignetté / crème / noir, titres en serif Didone (Bodoni
Moda, OFL), une couleur d'accent, objets photo détourés en local (`"query"` Pixabay ou `"image"` du client), mots qui
arrivent un par un ou lettres qui tombent (`"anim": "lettres"`), `"titre2"` en accent à mi-écran, étiquette dont le mot
change (`"Certains le [dépensent|gaspillent]"`), objet qui se fend en morceaux étiquetés (`"pieces"`), formes d'accent
(`"forme": "rayon | fleches | bande | disque"`), petites silhouettes (`"gens": 6`), décor (`"deco": ["codebarre",
"trame", "texte"]`). Une idée par écran, 2,5 à 3 s. Regarde le snapshot de chaque écran : si Pixabay donne un objet
à côté du sujet, change la recherche ou `"n": 1` (2e résultat). Crédits Pixabay dans renders/credits.txt.

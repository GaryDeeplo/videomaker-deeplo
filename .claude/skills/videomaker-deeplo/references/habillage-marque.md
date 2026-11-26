# Habillage de marque (intro, outro, bandeau nom) et réglages par marque

Scripts depuis la racine du projet : `PYTHONUTF8=1 python .claude/skills/videomaker-deeplo/scripts/<x>.py`.

## Intro, outro, bandeau nom
Dans `brands/<marque>/brand.json` (clé `video`) ou `jobs/<job>/config.json` :
`"branding": {"intro": "intro-marque", "outro": "outro-marque", "lowerThird": {"name": "Prénom Nom", "role": "Fonction"}}`.
- Rush : `build_composition.py` ajoute l'intro (1,6 s, la vidéo démarre sous son volet de sortie), l'outro (3,4 s,
  accroche et site de la charte) et le bandeau nom à la première prise de parole (après l'accroche d'un short ;
  dans la bande floutée si la source est affichée entière). `--no-branding` pour une version sans. Une accroche animée
  (`hook`) remplace l'intro.
- Sans rush : ajoute toi-même les scènes `{"kind": "block", "block": "intro-marque", "hold": 1.6}` en tête et
  `{"kind": "block", "block": "outro-marque", "hold": 3.4}` en fin du storyboard.
- **Nom et fonction** : uniquement ceux que l'utilisateur donne, avec l'accord de la personne. Jamais deviné.
- **Accroche de marque** : uniquement une accroche officielle du client (`tagline` de la charte) ; jamais inventée.

## Charte
`brands/<marque>/brand.json` (modèle : `brands/_exemple/`) : `name`, `tagline`, `tone`, `contact` (site, adresse,
téléphone), `publication` (jours / heure de publication pour `post.py date`) et `video` (écrase `config.default.json`) :
`visual` (fontFamily + `fonts` [{file, weight, format}], `fontFile`, `titleFont`, bgColor, inkColor, textColor,
accentColor, softColor, logo, `logoBlend: multiply` pour un logo sur fond blanc), `text`, `music`, `voice`
(geminiVoice, geminiStyle, pronunciation, fishVoice), `transcribe.vocabulary`, `branding`, `hook`.
`new_job.py` répond `charte: "trouvée" | "absente"` : absente -> la liste `marques` et la plus `proche` ; corrige
`brand` dans `job.json` ou crée la charte avant de monter (sinon la vidéo sort sans charte). `tools/selftest.py`
vérifie les couleurs et les fichiers de police / logo de chaque charte.

## Réglages connus (profil.json, par marque ET par parcours)
`python .claude/skills/videomaker-deeplo/scripts/onboard.py profil --marque <m> --parcours <p> format=… style=… reseaux=a,b musique=… broll=oui|non sous_titres=oui|non ton=… public=… cta="…" voix=… accroche=… accroche_style=…`
Clés acceptées (liste fermée, une clé inconnue est ignorée avec un avertissement et la plus proche) : format, style,
reseaux, musique, broll, sous_titres, emoji, zooms, accroche, accroche_style, layout, pack, habillage, ton, public,
objectif, cta, duree, langues, voix. Seules `reseaux` et `langues` sont découpées par virgule. Parcours : rush,
sans-rush, shorts, montage, plusieurs-rushs, explainer, punch, infographie, collage, ecran-partage, mots, immobilier,
traduction, lot, calendrier, guide, vitrine.
Ce sont des valeurs par défaut : la demande du moment gagne toujours ; ceux d'un Reel de la boulangerie Martin ne s'appliquent ni à une
autre marque ni à une vidéo sans rush. Enregistrement seulement après accord (question de fin de l'accueil) ; une
demande ponctuelle (« pour Noël », « juste celle-ci ») ne s'enregistre jamais.

## Valeurs du brief (quand l'utilisateur précise, ou pour « choisis pour moi »)
- **Objectif** : vendre un produit ou une offre · faire connaître l'entreprise · recruter · informer / conseiller ·
  fidéliser.
- **Public** : particuliers · professionnels · candidats · clients actuels.
- **Ton** : dynamique · chaleureux · haut de gamme · sobre (sinon le `tone` de la charte).
- **Appel à l'action** : réserver / acheter en ligne · venir en boutique · écrire en message · appeler · suivre le
  compte (lien ou numéro réels : `contact` de la charte ou donnés par l'utilisateur).
- **À ne pas oublier** (`mentions`) : une promo, une date, un prix, un nom ; sinon « rien de spécial ».
- **À éviter** (`eviter`) : prix, concurrents, un sujet sensible ; sinon « rien ».
- **Langues** : FR · FR + NL · FR + EN.
`public` et `ton` sont souvent stables pour une marque : à la fin, propose de les garder dans ses réglages.

## Goûts du client (gouts.json)
`onboard.py status --marque <m>` renvoie `gouts_client` (retours gardés de ce client) : ils valent pour tout le projet ;
la demande du moment gagne toujours. Un retour qui vaut pour les prochaines vidéos (« jamais de rouge », « musique plus
douce ») : propose `python .claude/skills/videomaker-deeplo/scripts/gouts.py add <client> "<ses mots>"` (`--from skill` pour une règle tirée de ses retours),
seulement avec son accord. `gouts.py list|forget|restore|prompt` pour les relire ou les retirer.

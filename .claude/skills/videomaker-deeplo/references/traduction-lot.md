# Versions traduites, lot (vidéos × langues × formats), calendrier de publication

Scripts depuis la racine du projet : `PYTHONUTF8=1 python .claude/skills/videomaker-deeplo/scripts/<x>.py`.

## Versions traduites (FR -> NL / EN / …)
Sous-titres traduits sur la même vidéo, voix d'origine conservée (rush, short ou vidéo sans rush) :
```bash
python .claude/skills/videomaker-deeplo/scripts/translate.py export <job> <slug> --to nl     # phrases + temps -> work/<slug>_tr_nl.json
#   TU remplis chaque "nl" (+ "hook_nl", "post_nl") : traduction naturelle, même sens, longueur proche,
#   registre « je » pour les réseaux (sauf consigne), noms propres et marques inchangés ; jamais les temps.
#   « role_nl » : fonction du bandeau nom (le nom ne se traduit pas). Ré-exporter garde les traductions faites.
python .claude/skills/videomaker-deeplo/scripts/translate.py apply <job> <slug> --to nl
python .claude/skills/videomaker-deeplo/scripts/build_composition.py <job> <slug> --lang nl   # (ou build_scenes.py … --lang nl) ; check + snapshot
python .claude/skills/videomaker-deeplo/scripts/deliver.py <job> <slug> --lang nl             # -> renders/livraison_nl/
```
Brief `langues=fr,nl` : `translate.py` pour chaque langue en plus, posts traduits. Reprends les mêmes choix d'habillage
que la version d'origine (pas de nouvelle question).
Voix dans une autre langue (vidéo sans rush) : copie le storyboard sous un autre slug, traduis `voice` et les textes
à l'écran, puis `voice.py` avec Fish Audio (la voix locale Kokoro n'a pas de néerlandais). Fais relire une
traduction par un locuteur natif avant publication si le client est exigeant sur la langue.

## Lot : plusieurs vidéos × langues × formats
Écris `lot.json` (dans le job parent ou ailleurs ; exemple : `templates/lot-exemple.json`) :
`{"name": "<lot>", "client": "<client>", "items": [{"job": "<job>", "slug": "<slug>"}], "langs": ["fr", "nl"],
"formats": ["9:16", "1:1"], "quality": "delivery", "reuse": true}` puis
`python .claude/skills/videomaker-deeplo/scripts/batch.py plan lot.json` (ce qui manque : traductions, posts ; durée estimée ~5,5 s de rendu par
seconde de vidéo et par format) -> termine ce qui manque -> `python .claude/skills/videomaker-deeplo/scripts/batch.py run lot.json`
-> `jobs/_lots/<lot>/index.html` : une page client avec toutes les vidéos, couvertures et textes par langue.
`reuse: true` garde les livraisons existantes ; mets `false` si la charte, l'habillage ou le montage a changé.

## Calendrier de publication
`python .claude/skills/videomaker-deeplo/scripts/planning.py <lot.json | job:slug,job:slug> --start AAAA-MM-JJ [--days mar,jeu,sam] [--networks instagram,tiktok,facebook,linkedin,youtube] [--langs fr,nl]`
-> à côté de la page du lot (ou dans `renders/`) : `planning.html` (une carte par jour × vidéo × langue : réseaux et
heures, couverture, texte à copier, lien de la vidéo), `planning.ics` (rappels 30 min avant, à importer dans l'agenda
du client) et `planning.csv`. Une vidéo par jour de publication, dans l'ordre du lot ; hashtags réduits par réseau
(TikTok 5, Facebook 3…). Horaires = repères génériques : dis au client de les ajuster selon les statistiques de son
compte. Rien n'est publié.

# Dérush : décider le plan, rushs bruts, téléphone, script écrit, plusieurs rushs

Scripts depuis la racine du projet : `PYTHONUTF8=1 python .claude/skills/videomaker-deeplo/scripts/<x>.py`.
Rappel de la règle : tu n'écris JAMAIS un timestamp ; dans les JSON tu n'écris que `keep`, `punch`, `reason`, et tu
peux corriger l'orthographe d'un mot (`w`), jamais ses temps.

## Décider le dérush (`work/<slug>_plan.json`)
- **Script connu** : aligne les îlots sur le script, garde la meilleure prise de chaque phrase (`script.py match`, plus bas).
- **Script inconnu** : reconstitue le texte voulu, garde la **dernière prise complète** de chaque phrase.
- Fillers du plan : relis les « reformulation » (même idée redite) et les « tic » : remove: true seulement si ça
  n'enlève aucune idée (« des vidéos …, et des photos … » porte une idée : on garde). Les shorts ont aussi leurs fillers.
- Jette : faux départs, phrases interrompues, mots isolés, hésitations seules, consignes dites à la caméra
  (« celle-là est ratée, je la refais »), hors-sujet par rapport au but de la vidéo.
- Ne jette jamais un îlot que tu n'as pas lu. Remplis `reason` pour chaque îlot jeté.
- **Durée du brief** : garde les phrases les plus fortes pour tenir la durée, et dis ce que tu as retiré.
- **Hésitations** (`fillers` du plan, repérées par l'outil dans les îlots gardés ; la transcription est amorcée pour
  écrire les « euh ») : `hesitation` (« euh », « hum ») et `repetition` (« je je ») sont retirées par défaut ;
  `pause` (blanc ≥ 0,6 s au milieu d'une phrase) est resserrée à 0,12 s de chaque côté ; `tic` (« du coup », « en fait »,
  « voilà », « genre », « bon », « quoi »…) reste **par défaut** : passe `remove: true` seulement quand le tic n'apporte
  rien (« Du coup, euh, on a… ») et laisse-le quand il porte le sens (« en fait, c'est gratuit » qui corrige une idée
  reçue, « voilà le résultat »). Dans le doute, garde. Un « euh » gardé n'apparaît jamais dans les sous-titres.
  Écoute les jointures signalées dans le compte rendu (une coupe au milieu d'une phrase peut claquer).
- Réglages : beaucoup de micro-îlots -> `--min-silence 0.6` ou `--noise -25` ; un seul gros îlot (débit continu,
  musique de fond) -> `--min-silence 0.3` ou `--noise -40` (options de `cut_plan.py`). Relancer est instantané.
- Un îlot ne se coupe pas en son milieu : si sa fin déborde (« … Ensuite, »), dis-le dans le compte rendu.
- `build_cut.py` : « clignements » = coupe tombée sur des yeux fermés -> glissée de quelques images, sans entrer dans
  un mot (`blink.py`) ; « restantes » non vide -> regarde ces coupes sur la planche.

## Rush brut face caméra où le client se reprend
`python .claude/skills/videomaker-deeplo/scripts/transcribe.py <job> <rush> --islands` transcrit chaque îlot de parole seul (VAD, pauses ≥ 0,3 s) : les
fausses prises restent écrites au lieu d'être lissées par Whisper (2 à 4x plus lent, local seulement). `cut_plan.py`
repère alors les reprises (fillers `restart`, résumé `restarts`) : sûres -> `remove: true`, on garde la dernière
prise ; possibles -> `remove: false`, à trancher ; un îlot fait de fausse prise -> `keep: false`. Les îlots courts ont
plus de fautes : relis noms et mots coupés avant les sous-titres. Pas de défaut global (config `transcribe.islands`).
Transcription : locale par défaut (~2-3x temps réel), `--engine groq` seulement si l'audio peut sortir de la machine
(accord) ; `--from S --to S` pour une partie seulement.

## Rushs de téléphone, rush filmé en marchant
- `build_cut` remet seul les cadences variables (VFR) à cadence fixe et ramène le HDR (iPhone HLG / Dolby Vision) en
  SDR BT.709 ; la rotation est lue dans la Display Matrix. Regarde `source` dans sa réponse : « ATTENTION » = ffmpeg
  sans zscale (prendre le build « full »). `--denoise` pour le souffle d'un téléphone.
- Petite source (WhatsApp, 480p) : agrandie au dérush (lanczos + netteté douce), sans punch ni zoom de caméra.
- **Rush filmé en marchant** : `build_cut.py` lance `enhance.py` (sauf `--no-enhance`) : chaque morceau qui tremble est
  stabilisé (gardé seulement si ça aide), les morceaux plus flous que le reste du rush reçoivent un léger renfort de
  netteté ; temps et son inchangés (`<slug>_cut_avant_retouche.mp4` gardé). Un flou de bougé ne se rattrape pas : dis-le.
- Rush paysage hors shorts : `python .claude/skills/videomaker-deeplo/scripts/reframe.py <job> <slug>` après `build_cut.py`, puis `build_composition.py`
  (la fenêtre 9:16 suit le visage, voir `references/shorts.md`).

## Avec un script écrit (texte prévu avant de filmer)
```bash
python .claude/skills/videomaker-deeplo/scripts/script.py prompteur <job> [--script texte.txt]   # renders/prompteur.html : prompteur sur téléphone / tablette (espace, vitesse, miroir)
#   … tournage, transcribe.py, cut_plan.py …
python .claude/skills/videomaker-deeplo/scripts/script.py match <job> <slug>                     # meilleure prise de chaque phrase -> keep / reason du plan
```
Le script va dans `work/script.txt`. `match` garde la prise la plus complète de chaque phrase (la dernière à
égalité), écarte les autres prises et signale : îlots « hors script : à relire » (une improvisation peut valoir le
coup : à toi de trancher), phrases manquantes (à refaire ou à retirer), ordre dit différent du script. Relis le
rapport `work/<slug>_script_report.json` avant `build_cut.py`.

## Plusieurs rushs -> une vidéo
Le client a filmé 5 ou 6 clips, dans le désordre, avec des reprises : mets-les tous dans `inbox/`
(`new_job.py … --rush a b c`).
```bash
python .claude/skills/videomaker-deeplo/scripts/multi.py list <job>                       # transcrit chaque clip (une fois) : durée + texte
#   TU lis tout et choisis l'ORDRE DU PROPOS (accroche, explication, preuve, appel à l'action) ; tu laisses de côté
#   les clips en double, ratés ou hors sujet (dis lesquels et pourquoi dans le compte rendu).
python .claude/skills/videomaker-deeplo/scripts/multi.py assemble <job> <slug> --order IMG_2.mp4,IMG_1.mp4,IMG_4.mp4
```
Les clips sont mis bout à bout au format du premier (un clip d'un autre sens sur fond flouté), séparés par un silence ;
les mots sont recalés sans retranscrire. Puis le parcours « rush -> reel » normal à partir de `cut_plan.py` : la
meilleure prise de chaque phrase se choisit tous clips confondus.

## Qualité image du dérush (mise à jour)
- Dérush (build_cut.py) : le cut est un intermédiaire presque sans perte (crf 12, crf 10 si la source est agrandie ; slow, tune film, une image clé par seconde, AAC 320k), couleurs ramenées en BT.709 limité et balisées (source SD sans balise lue en BT.601), HDR tramé (error_diffusion). Taille : celle que la composition affichera ; petite source (WhatsApp, 480p) agrandie dès ×1,0 en lanczos + netteté douce en recadré, jamais en « fill », et alors ni punch, ni zoom, ni dérive de caméra ; source plus large que le format réduite à la hauteur du format, jamais agrandie (reframe.py peut suivre). Rush sans son : piste muette. Voix : voice_chain + loudnorm 2 passes linéaire (voice.py) sur derush.voiceLufs.
- Retouche (enhance.py) : morceaux sans perte, un seul encodage final crf 12 ; pas de netteté en plus sur une source déjà agrandie ; vidstab en zoom adaptatif doux.
- Clignements : une coupe sur des yeux fermés glisse de quelques images sans entrer dans un mot (blink.py, MediaPipe facultatif).
- HDR : PQ / Dolby Vision tone-mappés (hable) ; HLG (iPhone) seulement converti (primaires, matrice), jamais tone-mappé
  (la peau virerait à l'orange). Rush de téléphone : image de contrôle original | importé dans work/<slug>_controle.jpg.
- Noms propres : `noms.txt` (un par ligne) dans le job, son inbox ou brands/<marque>/ ; lus par transcribe.py en amorçage.

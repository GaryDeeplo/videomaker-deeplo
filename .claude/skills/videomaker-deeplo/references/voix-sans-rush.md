# Vidéo sans rush : storyboard, voix off, noms propres, charte

Scripts depuis la racine du projet : `PYTHONUTF8=1 python .claude/skills/videomaker-deeplo/scripts/<x>.py`. Format du storyboard : `references/storyboard.md`.

## D'où vient la voix off
Question de la série 2 de l'accueil (sauf si déjà dit ou réglé pour la marque, `voix=`) : « voix de synthèse naturelle
(recommandé) » (Gemini, gratuit) · « j'ai un enregistrement » (mémo vocal, micro, ou une vidéo dont on garde le son :
chemin via « Autre ») · « pas de voix, musique et textes seulement ». Ni clé Gemini ni Fish -> dis-le en une ligne (voix
locale de test) avant de lancer.

## Voix de synthèse (Gemini TTS)
Voix et ton dans la charte (`video.voice.geminiVoice`, `geminiStyle` en français : « Lis d'une voix calme et douce, débit
naturel ») ou `--voice` / `--style` sur `voice.py`. Le ton du brief se traduit ici. En gratuit, Google peut utiliser les
textes envoyés : rien de confidentiel dans la voix off. `voice.py` prend Gemini si `GEMINI_API_KEY`, sinon Fish, sinon
la voix locale (test) ; `--engine gemini|fish|local` pour forcer.

## Noms propres
Prononciation par marque dans `video.voice.pronunciation` (`{"Lyons-la-Forêt": "Lion-la-Forêt"}`) : seule la voix de synthèse lit la
forme phonétique, sous-titres et post gardent l'orthographe. Orthographe à la transcription :
`video.transcribe.vocabulary` (`["Martin", "Lyons-la-Forêt"]`). Doute sur un nom de lieu, de personne ou de produit :
demande à l'utilisateur comment il se prononce AVANT de générer la voix, et ajoute-le au lexique de la marque.

## Voix enregistrée (`--file`, audio ou vidéo)
Lance d'abord `python .claude/skills/videomaker-deeplo/scripts/voice.py <job> <slug> --file x` SANS storyboard ou avec des scènes sans `voice` -> l'outil
transcrit et écrit `work/<slug>_voice_phrases.txt` ; écris alors le storyboard avec un champ `voice` par scène qui
reprend EXACTEMENT les phrases dites (dans l'ordre ; une scène peut en grouper plusieurs), puis relance : chaque scène
se cale sur sa phrase, l'orthographe vient du storyboard, les blancs du début sont retirés. Les scènes sans voix
(intro, outro) seulement au début ou à la fin. Les ratés et reprises dans l'enregistrement : passe d'abord par le
parcours rush (`cut_plan` / `build_cut`) sur ce fichier, puis `--file` sur la version nettoyée. `--denoise` réduit le
souffle d'un enregistrement au téléphone.

## Charte et contrôle des scènes
Charte : `brands/<marque>/brand.json` (`video.visual` : police + fichiers, bgColor, inkColor, accentColor, logo,
`logoBlend: multiply` pour un logo sur fond blanc). Regarde CHAQUE scène sur la planche : texte lisible sur la photo,
rien sous les sous-titres, pas de grand vide. Scènes de `build_scenes.py` : hook / photo / points / stat / offer /
quote / gallery / cta, plus les blocs (`references/motions-blocs.md`) et les scènes `device` / `browser`.
Pas assez de photos : `broll.py auto … --storyboard` (`references/plans-de-coupe.md`). Voix dans une autre langue :
`references/traduction-lot.md`.

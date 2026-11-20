# Deeplo Video Maker

Skill Claude Code de montage + motion design pour PME. Guide : `README.md` ; installation sur une autre machine : `INSTALL.md`. Workflow : skill `videomaker-deeplo` (`.claude/skills/videomaker-deeplo/SKILL.md`).

- Moteur : HyperFrames (`studio/`). Aperçus `-q draft -w 8`, final `-q delivery`.
- Vérifier le socle : `python .claude/skills/videomaker-deeplo/scripts/check.py`.
- Sources imposées : voix = Gemini TTS (`GEMINI_API_KEY`, gratuit), Fish Audio pour le clonage, ou un enregistrement du client (`voice.py --file`) ; SFX = `real-sfx` (banque `sounds/`) ; musique =
  `openverse-sfx` (CC0/BY/PDM, crédits livrés) ; transcription = locale (faster-whisper large-v3-turbo, `scripts/transcribe.py`) ou Groq ; pas Parakeet (bascule en anglais).
  Pas de connexion HeyGen ni de crédits payants sans accord explicite.
- Montage par le texte : les points de coupe viennent toujours des mots horodatés et des silences mesurés, jamais d'un
  timecode deviné.
- Chaque motion validée : proposer de la sauvegarder dans `library/` (bloc + aperçu + meta.json).
- Un dossier par vidéo : `jobs/<AAAA-MM-JJ>-<client>-<sujet>/{inbox,work,out}`.
- Paquet à partager : `python .claude/skills/videomaker-deeplo/scripts/package.py --pour equipe|client` -> `dist/` (jamais jobs/ ni .env ; « client » retire les chartes et aperçus des autres clients).

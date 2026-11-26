# Musique, bruitages, mixage

Scripts depuis la racine du projet : `PYTHONUTF8=1 python .claude/skills/videomaker-deeplo/scripts/<x>.py`.

## Musique
- Banque `sounds/music/` (CC0 / CC-BY, `catalog.json` avec ambiance, BPM, LUFS) : upbeat, chill, inspiring,
  energetic, acoustic, cinematic, funky, ambient. Écoute-la par les chiffres (BPM, durée), propose 2 pistes et
  laisse l'utilisateur choisir à l'oreille.
- `python .claude/skills/videomaker-deeplo/scripts/add_music.py <job> <slug> --mood upbeat` (ou `--id <piste>`, `--file <fichier client>`,
  `--url <YouTube/SoundCloud/Bandcamp>` via yt-dlp). Pour un lien ou un fichier du client : **dis toujours** qu'un lien
  n'est pas une licence ; à n'utiliser que si le client a les droits (sinon son coupé ou vidéo bloquée sur Instagram /
  TikTok). La source part dans `renders/credits.txt` avec « droits à vérifier ».
- Le lit est baissé sous la voix (sidechain) ; `--level` règle son niveau de base (-20 LUFS par défaut) ; `--start` où
  commencer dans la piste (sinon premier passage énergique).
- Enrichir la banque : `python .claude/skills/videomaker-deeplo/scripts/bank.py sfx|music [--only cat --query "..."]` (Openverse, ~200 recherches/jour).
- `renders/credits.txt` est livré avec la vidéo (obligatoire pour CC-BY : en description du post).
- Ambiance selon le ton du brief : dynamique -> upbeat / energetic ; chaleureux -> acoustic ; haut de gamme ->
  cinematic / ambient ; sobre -> inspiring basse ou aucune.

## Sound design automatique
Chaque monteur termine par `sound_design.auto` (whoosh sur un changement de plan ou de temps fort, pop sur un élément
de liste, impact sur un chiffre, bruitage de caisse sur un prix en €, clic sur un bouton, ding sur une notification…),
instants lus dans la composition, sons de la banque harmonisés et espacés (≥ 0,45 s). Relancer à la main :
`python .claude/skills/videomaker-deeplo/scripts/sound_design.py <job>` ; `--off` les retire ; `"sfx": {"design": false}` pour s'en passer.
La musique n'est pas baissée sous les bruitages : volumes déjà dosés pour passer dessus. SFX : banque `sounds/` (via
`real-sfx` pour un design sonore complet), jamais de son synthétisé.

## Musique qui s'efface (`mix.py`, automatique après le sound design)
La musique descend de 10 dB sous la parole (énergie de la voix, rampes 0,12 s / 0,5 s) et de 4 dB sous chaque
bruitage, puis remonte dans les silences. Piste d'origine intacte (`assets/<slug>_music_bed.wav`, écrit par
add_music) ; `python .claude/skills/videomaker-deeplo/scripts/mix.py <job> --voix -8` pour régler, `--off` pour revenir ; `"music": {"duck": false}` pour
s'en passer.

## Réglages du son (mise à jour)
- Son : bruitages calés sur leur PIC (index real-sfx), mis au même niveau (max momentané : impacts -16, souffles/pops/clics -20, ticks -24), ordre mélangé par job, ±1 demi-ton, pops en cascade en arpège ; couches : riser avant un gros chiffre, boom sous l'accroche (-6 dB), sub-drop sous une révélation, applaudissements sur la fin d'un événement ("sfx": {"applause": true}). Budget : 1 son par changement de plan + 0,5/s, 1,2 s entre deux sons d'une même famille. Les blocs (chiffre-verre, tarif, fin-logo, suivre, accroches…) ont leur son.
- Banque SFX : familles subdrop, glass (notification, tarif luxe), swoosh_soft (bandeau-nom, surligneur, marquee), tap (bouton, suivre), pageflip ; enrichir avec `bank.py sfx --only <famille> [--query "..."]`.
- Musique : piste tirée par job (jamais les 2 dernières posées ailleurs, sounds/music/recent.json), départ au premier passage énergique (--start pour forcer), boucle en fondu enchaîné, niveau mesuré (-20 LUFS). Ducking : -10 dB sous la voix, -2,5 dB sous les seuls bruitages marquants.
- Voix (TTS, enregistrement et rush) : coupe-bas 80 Hz, EQ (-2 dB à 220 Hz, +2,5 dB à 3,2 kHz), de-esser, compresseur 3:1, loudnorm 2 passes linéaire (voice.voice_chain / render_voice) ; --denoise = débruitage doux (afftdn).
- Master (finalize.py) : glue légère + limiteur suréchantillonné, -14 LUFS, crête ≤ -1 dBTP, plage ≤ 9 LU ; « mode linéaire » attendu, « dynamique » = plage > 9 LU resserrée.

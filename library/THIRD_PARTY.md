# Composants tiers

| Élément | Source | Licence |
|---|---|---|
| block/confetti, marquee, mot-tournant, barres, frise, machine-a-ecrire, tarif ; scènes `device` et `browser` ; transitions iris / zoom / flou | Onda — github.com/degueba/onda (réécrits en GSAP) | MIT © 2026 Rodrigo Botelho |
| lottie/* (emojis) | Google Noto Animated Emoji | CC BY 4.0 (crédit automatique dans renders/credits.txt) |
| vendor/dotlottie-web | LottieFiles | MIT |
| Principes de dérush (cut_plan, build_cut) | package reel-cut (Le Club IA) | usage interne ; à réécrire avant redistribution |

## YuNet (détection de visage, recadrage qui suit la personne)
`.claude/skills/videomaker-deeplo/vendor/yunet/face_detection_yunet_2023mar.onnx` — OpenCV Zoo, © 2020 Shiqi Yu, licence MIT
(`vendor/yunet/LICENSE`). Utilisé localement par `scripts/reframe.py` ; aucune image ne quitte la machine.

## Polices du panneau « écran partagé »
`.claude/skills/videomaker-deeplo/vendor/fonts/` : Instrument Serif Italic (© The Instrument Serif Project Authors) et
IBM Plex Mono Medium (© IBM Corp.), licence SIL Open Font License 1.1 (fichiers OFL-*.txt à côté).

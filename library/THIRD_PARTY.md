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

## Pictos Lucide
`.claude/skills/videomaker-deeplo/vendor/lucide/` : icônes Lucide (paquet npm lucide-static), licence ISC
(© Lucide Icons and Contributors, `vendor/lucide/LICENSE`), téléchargées à la demande et intégrées en SVG.

Anton Regular (© The Anton Project Authors), SIL Open Font License 1.1 (`vendor/fonts/OFL-Anton.txt`) : titres du pack « actu / punch ».

## Logos de marques (Simple Icons)
`.claude/skills/videomaker-deeplo/vendor/simple-icons/` : SVG du projet Simple Icons (simpleicons.org), données sous CC0 1.0,
téléchargés à la demande (« logo:<nom> »). Les logos restent des marques de leurs propriétaires : usage informatif seulement
(montrer l'outil dont on parle), jamais pour suggérer un partenariat ou une approbation.

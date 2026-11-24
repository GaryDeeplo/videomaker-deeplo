# Composants tiers

| Élément | Source | Licence |
|---|---|---|
| block/confetti, marquee, mot-tournant, barres, frise, machine-a-ecrire, tarif ; scènes `device` et `browser` ; transitions iris / zoom / flou | Onda — github.com/degueba/onda (réécrits en GSAP) | MIT © 2026 Rodrigo Botelho |
| lottie/* (emojis) | Google Noto Animated Emoji | CC BY 4.0 (crédit automatique dans renders/credits.txt) |
| vendor/dotlottie-web | LottieFiles | MIT |
| Principes de dérush (cut_plan, build_cut) | package reel-cut (Le Club IA) | usage interne ; à réécrire avant redistribution |
| Sous-titres qui évitent le visage et zones sûres par plateforme (`face.py`), reprises cachées (`transcribe.py --islands`), page de validation (`review.py`), retours par client (`gouts.py`) | ghost-editor — github.com/kurbaitaev/ghost-editor (logique portée en Python, aucun asset copié) | MIT © 2026 kurbaitaev |
| Sonde des rushs (VFR, rotation, HDR) et conversion SDR, conformité des livraisons, mode loudnorm et reprise AAC (`finalize.py`), micro-coupures / image isolée / première image (`qa.py`) | ffmpeg-skill — github.com/kajisho5/ffmpeg-skill (idées réécrites dans nos scripts) | MIT © 2026 kajisho5 |

## MediaPipe Face Landmarker (clignements aux coupes)
`.claude/skills/videomaker-deeplo/vendor/mediapipe/face_landmarker.task` — Google, licence Apache 2.0
(`vendor/mediapipe/LICENSE`). Utilisé localement par `scripts/blink.py` (score « yeux fermés » aux points de coupe) ;
aucune image ne quitte la machine. Bibliothèque `mediapipe` (Apache 2.0) installée à part, facultative.

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

# Blocs de motion design, suggestions, Lottie, registre HyperFrames, bibliothèque

Scripts depuis la racine du projet : `PYTHONUTF8=1 python .claude/skills/videomaker-deeplo/scripts/<x>.py`.

## Blocs de `library/block/`
`compteur`, `note-etoiles`, `jauge`, `bouton-cta`, `compte-rebours`, `notification`, `sticker`, `surligneur`, `fleche`,
`suivre`, `confetti`, `marquee`, `mot-tournant`, `barres`, `frise`, `machine-a-ecrire`, `tarif` (+ `intro-marque`,
`outro-marque`, `bandeau-nom`), `commente-mot`, blocs en verre du pack luxe (`references/immobilier-luxe.md`),
accroches `accroche-<style>` (`references/accroches.md`), `scan-visage` (`references/objets.md`). Scènes `device`
(téléphone) et `browser` (navigateur avec barre d'adresse) qui font défiler une vraie capture du site / de l'app.
Transitions de scène : `wipe-up`, `wipe-left`, `fade`, `iris`, `zoom`, `blur`. Confetti, marquee, mot-tournant, barres,
frise, machine-a-ecrire, tarif, device, browser et iris/zoom/flou sont portés depuis Onda (MIT, Rodrigo Botelho).
Chiffres des barres, prix des tarifs, dates des frises : uniquement des données réelles.
Nouveau bloc : l'ajouter dans `scripts/_make_motion_blocks.py`, relancer, tester (`check` + `snapshot`), puis
`library.py save`. Couleurs, police et logo viennent de la charte ; le reste en `vars` (voir l'`usage` de chaque entrée
dans `library/index.html`). Trois façons de s'en servir :
- **Scène plein écran** (sans rush) : `{"kind": "block", "block": "compteur", "vars": {…}, "voice": "…"}` sur le fond de la charte.
- **Par-dessus une scène** (sans rush) : `"motions": [{"block": "note-etoiles", "word": "<mot de la phrase>", "dur": 3, "vars": {…}}]`.
- **Par-dessus un rush** : `work/<slug>_motions.json` = la même liste, puis `build_composition.py` (ignorés en écran
  partagé : leur idée va dans un temps fort ; en mode cartes, posés sur un passage `face`).
Le bloc apparaît quand le **mot** est prononcé (`occurrence` pour la 2e fois qu'il est dit) : jamais de timecode écrit à
la main (les mots élidés comme « l'aventure » sont trouvés par « aventure »). Le rapport `motions` de la sortie dit
quels blocs sont posés ou ignorés. Positions : `top` (%), `left`, `x`/`y` selon le bloc. Durée : libre, le bloc cale ses
animations sur la durée réelle de son montage (scène courte = animations resserrées) ; 2 à 3,5 s conseillées.
En scène plein écran, la carte prend l'encre de la charte (contraste) ; en surimpression, elle reste translucide.
Chiffres, notes, avis et compteurs : uniquement des valeurs réelles du client ; `notification` est une illustration,
pas une vraie commande.

## Suggestion automatique (à trier)
`python .claude/skills/videomaker-deeplo/scripts/suggest_motions.py <job> <slug>` lit ce qui est DIT et propose : montant -> compteur, % -> jauge,
« 4,9 sur 5 » -> étoiles, « plus que 3 jours » -> compte à rebours, « nouveau / offert » -> sticker, « réservez… » ->
bouton, « abonnez-vous » -> suivre, mots-clés -> emoji animé ; variété, espacement, plafond par minute, rien sous
l'accroche. Sortie : `work/<slug>_motions_suggested.json` avec la phrase de chaque proposition. **Tu tries** : garde ce
qui sert le propos (pas d'ancienne valeur qui embrouille, pas deux fois la même idée), écris les légendes avec les mots
de la phrase, complète uniquement avec des infos réelles (nombre d'avis, @compte), puis copie dans
`work/<slug>_motions.json` (rush) ou le champ `motions` des scènes. `--apply` écrit directement, à relire quand même.

## Animations Lottie et emojis animés (`library/lottie/`)
```bash
python .claude/skills/videomaker-deeplo/scripts/lottie.py get emoji 🔥 --name feu              # emoji animé Google Noto (CC BY 4.0, crédit auto)
python .claude/skills/videomaker-deeplo/scripts/lottie.py get url <lien .json|.lottie> --name x --license "Lottie Simple License" --author "…"
python .claude/skills/videomaker-deeplo/scripts/lottie.py render <nom>                         # une fois : WebM transparent + aperçu de galerie
```
Puis dans `motions` : `{"block": "lottie", "name": "feu", "word": "<mot dit>", "dur": 2, "vars": {"x": 50, "y": 24, "size": 30}}`
(centre x/y en %, taille en vmin, rejouée en boucle sur `dur`). Le crédit part dans `renders/credits.txt`.
Sources sûres : LottieFiles gratuit (Lottie Simple License, commercial OK), Noto (CC BY 4.0), Fluent (MIT).
Jamais une animation sans licence connue. Prêtes (24, `lottie.py list`) : valide ✅, coeur ❤️, etoile 🌟, pouce 👍, fusee 🚀,
cadeau 🎁, idee 💡, regard 👀, waouh 🤩, adore 😍, cent 💯, bravo 🙌, applaudir 👏, eclat ✨, cloche 🔔, alarme ⏰,
trophee 🏆, force 💪, reflexion 🤔, rire 😂, doigt 👉, cible 🎯, feu 🔥, fete 🎉. (💰 n'existe pas en animé chez Noto.)
Emoji animé aussi possible sur un passage `face` (cartes) et dans un temps fort (`"lottie": {…}`).

## Piles de cartes d'outils, fin « Commente : MOT »
- **Piles de cartes d'outils** (format « outils à sauvegarder ») : `work/<slug>_outils.json` (`word`, `dur` ou `until`,
  `par_pile`, `outils` [{`nom`, `url`, `logo`, `image`}]), puis `python .claude/skills/videomaker-deeplo/scripts/tools_stack.py capture <job> <slug>`
  (captures locales du haut des pages ; page vide, de chargement ou « vérification anti-robots » écartée — jamais
  contournée — et remplacée par une carte logo + nom ; « image » pour fournir sa capture) ; `build_composition.py` pose
  les piles de 3 sur la vidéo floutée et assombrie, une pile par temps de musique, sous-titres descendus. Regarde les
  captures avant de montrer. Logos : usage informatif, jamais un partenariat.
- **Fin « Commente : MOT »** : bloc `commente-mot` (mot qui s'écrit, commentaire + cœur, message reçu, abonne-toi) ;
  variables `mot`, `pour`, `ressource` (vide = pas de message), `compte`, `abonne`. Ne promets que ce qui sera vraiment
  envoyé (la liste, le lien) : c'est un engagement envers les gens qui commentent.

## Registre HyperFrames (environ 400 blocs et composants officiels, aperçus dans la bibliothèque)
Avant de créer un motion, cherche aussi dans le registre : `python .claude/skills/videomaker-deeplo/scripts/library.py search "…"` couvre
`library/registre/` (type `registre`, aperçu rendu en local depuis la démo de chaque élément ; titres et descriptions en
anglais). Familles utiles : styles de sous-titres (`caption-*`), bandeaux nom (`lt-*`, `lower-third-bild`), curseurs et
démos d'interface (`cursor-*`, `agent-cursor`, `typed-prompt`), échanges IA (`claude-exchange`, `chatgpt-exchange`),
code (`code-*`, `terminal-simulator`), annotations dessinées à la main (`hw-*`, `marker-highlight`), effets de texte
(`scramble-reveal`, `kinetic-type-swap`, `weight-wave`…), transitions (`whip-pan-cut`, `match-cut`, `cinematic-zoom`…),
données (`bar-chart-race`, `chart-story`, `count-up`, `world-map`), réseaux sociaux (`x-post`, `yt-comment-card`,
`instagram-follow`), appareils (`vfx-iphone-device`, `multi-device-splay`).
Installer dans le job : `python .claude/skills/videomaker-deeplo/scripts/library.py use <nom> <job>` (= `npx hyperframes add <nom>` : le fichier arrive dans
`compositions/`), puis monter le bloc comme les autres (motions / scène) en remplissant ses variables (liste dans
l'usage). Les shaders WebGPU du registre (orbes, fonds animés) ne se rendent pas en local : écartés.

## Bibliothèque (`library/`, la règle qui fait gagner du temps)
`library/` contient les motions **validés** (scènes, styles de sous-titres, transitions, intros/outros, blocs
HyperFrames), chacun avec aperçu vidéo, « quand l'utiliser » et extrait d'utilisation. Galerie : `library/index.html`.
1. **Avant de créer** une scène, un style ou une animation : `python .claude/skills/videomaker-deeplo/scripts/library.py search "<besoin>"`.
   Réutilise ce qui existe (adapte-le si besoin) ; sinon cherche dans `hyperframes-registry` ; sinon crée.
2. Blocs réglables : scène `{"kind": "block", "block": "<nom>", "text": …, "sub": …, "vars": {…}}` dans le storyboard ;
   `build_scenes.py` copie le bloc de `library/` dans `compositions/` et remplit ses variables depuis la charte.
   Un nouveau bloc = un fichier HyperFrames avec `data-composition-variables`, couleurs et police en `var(--…)`,
   timeline enregistrée sous son id, `src` d'image de repli en data URI (sinon `check` échoue).
3. **Après validation** par l'utilisateur d'une vidéo ou d'un passage, propose en une ligne :
   « Je sauvegarde <ce motion> dans la bibliothèque sous le nom <x> ? ». Si oui :
   `python .claude/skills/videomaker-deeplo/scripts/library.py save --type <type> --name <x> --title … --desc … --use "<quand>" --tags … --job <job> --clip renders/<rendu validé>.mp4 --at <début> --dur <durée> [--file <bloc.html>] --usage '<extrait>'`
   (extrait court : `render --start S --end E` si besoin). Jamais sans validation.

## Skills d'appui installés
- `gsap-*` (officiels GSAP : SplitText, MorphSVG, DrawSVG gratuits) pour écrire de nouveaux blocs ;
- `remotion-to-hyperframes` pour porter un composant Remotion / Motion Canvas / Lottie / After Effects, vérifié image
  par image (attention à la licence du composant source) ;
- `motion-design` (LottieFiles), `motion-director`, `web-motion-auditor` : principes de timing, de courbes et de
  contrôle qualité. Le « Creator MCP » LottieFiles proposé par `motion-design` n'est pas branché (service en ligne :
  accord requis).

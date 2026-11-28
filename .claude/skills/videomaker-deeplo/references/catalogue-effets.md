# Catalogue « N trucs que X sait faire » et effets sur le rush (vertigo, cadre, contour, traverse)

Scripts depuis la racine du projet : `PYTHONUTF8=1 python .claude/skills/videomaker-deeplo/scripts/<x>.py`. Rush face caméra,
plein écran recadré (`--layout full`, sans fond flouté ni suivi du visage). Tout est posé par `build_composition.py` dès
que le fichier existe dans `work/` ; le rapport `catalogue` / `effets` de sa sortie dit ce qui est posé ou écarté et pourquoi.
Référence d'origine : `jobs/_references/reel-DgPH8lRTKUd` (planche `effets.jpg`).

## Catalogue (vitrine en rafale)
La personne énumère face caméra (« orbit, couch wall, ui world… », ~1 élément par seconde) : chaque mot DIT surligne
l'élément dans le sommaire et lance sa démo dans un téléphone. `work/<slug>_catalogue.json` :
```json
{"titre": "17 effets que Claude sait faire",
 "items": [{"nom": "scan du visage", "mot": "scan", "demo": "library:scan-visage"},
           {"nom": "chiffre en verre", "mot": "chiffre", "demo": "inbox/demo-chiffre.mp4", "depuis": 0.5},
           {"nom": "carte", "mot": "carte"}],
 "fin": "maintenant", "decaler": true}
```
- `mot` : le mot dit qui fait passer à l'élément (`occurrence` pour la 2e fois) ; un élément non dit est ignoré et
  listé dans `non_dits`. Jamais de timecode.
- `demo` : `library:<nom>` (aperçu d'un motion de `library/`, joué à partir de 1 s), une vidéo ou une image du job ;
  absent = carte au nom de l'élément. `depuis` : seconde de la démo où commencer.
- `fin` : le mot où tout l'habillage part en flou (puis l'appel à l'action, sous-titré) ; sans `fin`, juste après le
  dernier élément. `decaler: false` garde la personne au centre.
- Pendant le catalogue : ni sous-titres ni accroche (le titre en tient lieu). Fin conseillée : bloc `commente-mot`
  dans `work/<slug>_motions.json` (references/motions-blocs.md), qui ne promet que ce qui sera vraiment envoyé.
- Snapshot : le téléphone (bas droite) ne doit pas couvrir le visage ; si la personne est décentrée, `visual.focusX`.

## Effets sur le rush
`work/<slug>_effets.json` = une liste, chaque effet posé sur un mot dit :
```json
[{"effet": "vertigo", "mot": "gratuites"},
 {"effet": "cadre", "mot": "Instagram", "compte": "moncompte"},
 {"effet": "contour", "mot": "dessin", "dur": 2.4},
 {"effet": "traverse", "mot": "ensuite"}]
```
| Effet | Ce qu'on voit | Durée par défaut | Réglages |
|---|---|---|---|
| `vertigo` | coup sec avant, puis le décor recule pendant que la personne garde sa taille (dolly zoom) | 1,8 s | `force` (1,28) |
| `cadre` | « frame break » : l'image rétrécit dans un cadre de Reel sur fond flouté, la tête et les épaules en sortent | 2,6 s | `echelle` (0,74), `largeur` (0,6), `compte` (@ affiché) |
| `contour` | « doodle boil » : contour blanc qui tremble autour de la personne + 4 petits dessins qui se tracent | 2,6 s | `dur` |
| `traverse` | « zoom-through cut » : zoom flou à travers l'image, posé sur la coupe du dérush la plus proche (≤ 1,2 s) | 0,5 s | — |

- `vertigo`, `cadre` et `contour` détourent la personne en local (`cutout.py`, ~20 s de calcul par seconde d'effet,
  mis en cache) : un par idée forte, pas plus d'un toutes les 5 s. Rien pendant le catalogue (écarté, dit dans le rapport).
- Un bruitage whoosh part avec `vertigo`, `cadre` et `traverse`.
- `titre` (facultatif) : le nom de l'effet en pastille en haut pendant l'effet (démo, tuto « comment je fais »).
- Regarde le snapshot au milieu de chaque effet : le contour doit suivre la personne, et le cadre doit laisser
  dépasser la tête.

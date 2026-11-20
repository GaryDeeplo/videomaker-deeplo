# Storyboard d'une vidéo sans rush (`work/<slug>_storyboard.json`)

Claude l'écrit à partir du brief (idée, texte, photos, charte). Une scène = une phrase de voix off.
Les temps ne s'écrivent jamais : ils viennent de la voix générée (`voice.py`).

```json
{
 "title": "…", "format": "9:16", "objectif": "ce que la vidéo doit déclencher",
 "scenes": [
  {"kind": "hook", "image": "facade.jpg", "kicker": "Lyon · depuis 1985", "text": "Accroche en 4 à 8 mots", "voice": "…"},
  {"kind": "photo", "image": "x.jpg", "kicker": "Sur mesure", "text": "Titre court sur la photo", "voice": "…"},
  {"kind": "points", "image": "facultatif.jpg", "title": "Titre", "items": ["2 à 4", "items", "courts"], "voice": "…"},
  {"kind": "stat", "kicker": "…", "value": "1895", "from": 1800, "prefix": "", "suffix": "", "label": "…", "voice": "…"},
  {"kind": "offer", "title": "Formule", "old": "6,50 €", "new": "4,90 €", "badge": "Jusqu'au 30/11", "voice": "…"},
  {"kind": "quote", "text": "Avis client réel, mot pour mot", "author": "Prénom, ville", "voice": "…"},
  {"kind": "gallery", "images": ["a.jpg", "b.jpg", "c.jpg"], "text": "Titre", "voice": "…"},
  {"kind": "cta", "text": "Appel à l'action", "sub": "adresse / horaires / site", "voice": "…", "hold": 1.2},
  {"kind": "steps", "title": "Comment ça se passe", "steps": ["2 à 5", "étapes", "courtes"], "voice": "…"},
  {"kind": "beforeafter", "before": "avant.jpg", "after": "apres.jpg", "labels": ["Avant", "Après"], "text": "…", "voice": "… avant, et après."},
  {"kind": "product", "image": "produit.png", "kicker": "Nouveau", "name": "Nom", "features": ["atout 1", "atout 2"], "price": "", "voice": "…"},
  {"kind": "team", "title": "L'équipe", "members": [{"photo": "a.jpg", "name": "Prénom", "role": "Fonction"}], "voice": "…"},
  {"kind": "address", "image": "facade.jpg", "title": "Venez nous voir", "address": "Rue, CP Ville", "hours": ["…"], "voice": "…"},
  {"kind": "device", "image": "capture-mobile.png", "kicker": "En ligne", "title": "…", "screens": 1.5, "transition": "iris", "voice": "…"},
  {"kind": "browser", "image": "capture-desktop.png", "url": "site.be", "kicker": "En ligne", "title": "…", "voice": "…"},
  {"kind": "block", "block": "tarif", "vars": {"tier": "…", "price": "…", "period": "…", "features": "a|b|c", "cta": "…"}, "voice": "…"},
  {"kind": "block", "block": "mot-tournant", "vars": {"before": "Pour les", "words": "restaurants|commerces|artisans"}, "voice": "…"},
  {"kind": "block", "block": "compteur", "vars": {"to": 250, "prefix": "+", "label": "projets"}, "voice": "…"},
  {"kind": "photo", "image": "x.jpg", "text": "…", "voice": "… nos clients …",
   "motions": [{"block": "note-etoiles", "word": "clients", "dur": 3, "vars": {"rating": 4.9, "count": "127 avis Google"}}]},
  {"kind": "block", "block": "outro-marque", "text": "accroche", "sub": "infos", "vars": {}, "hold": 3.6}
 ]
}
```

## Règles d'écriture
- Cherche d'abord dans la bibliothèque (`library.py search`) : une scène ou un bloc validé vaut mieux qu'un neuf.
- 20 à 45 s, 5 à 8 scènes. Une idée par scène ; la voix dit, l'écran résume (jamais la même phrase mot pour mot).
- **Accroche** dans les 2 premières secondes : bénéfice, chiffre ou question.
- Dans `points`, écris les items avec les **mêmes mots que la voix** : chaque item apparaît quand il est prononcé.
  Idem pour `stat.value` et `offer.new` (le prix s'affiche quand il est dit).
- Texte à l'écran : 8 mots maximum par titre, 3 mots par item.
- Termine par `cta` (logo de la charte, action concrète, adresse ou site), avec `hold` 1 à 1,5 s.
- **Jamais de faux** : pas d'avis, de chiffre, de prix ou de promotion inventés. Si le brief n'en donne pas, pas de
  scène `quote` / `offer` / `stat`, ou demande-les.
- Photos : celles du client d'abord (`inbox/`). Une photo par scène `photo` ou `hook`, cadrage portrait-friendly
  (sujet au centre). Les photos très claires vont plutôt en `gallery` ou en bandeau de `points`.
- `steps`, `team.members[].name`, `product.features` : mêmes mots que la voix (ils apparaissent quand ils sont dits).
- `beforeafter` : uniquement de vraies photos avant / après du client ; la voix dit « après » pour lancer le volet.
- `product` : PNG détouré (fond transparent) ; le détourage automatique HyperFrames ne vaut que pour des personnes.
- `team` : vrais noms et photos, avec l'accord des personnes.
- `transition` facultative par scène : `wipe-up`, `wipe-left`, `fade`, `iris`, `zoom`, `blur` (une ou deux par vidéo, pas toutes).

## Chaîne
```bash
python scripts/voice.py <job> <slug> [--engine fish|local] [--voice <reference_id>]   # voix + temps + mots
python scripts/build_text.py <job> <slug>                                             # sous-titres
python scripts/add_music.py <job> <slug> --mood inspiring                             # lit musical
python scripts/build_scenes.py <job> <slug>                                           # composition
cd <job> && npx --yes hyperframes@0.9.71 check && npx --yes hyperframes@0.9.71 snapshot --at …
```
Refaire une phrase : modifie son `voice` puis relance `voice.py` ; les autres phrases viennent du cache.

## Images de banque (Pixabay)
Champ facultatif `"query"` sur une scène sans `image` : 1 à 2 mots anglais concrets (« croissant », « bakery bread »).
`broll.py auto <job> <slug> --storyboard` remplit `image` (vidéo de fond pour `hook` / `photo`, photo sinon) ; crédits
livrés automatiquement. Ambiance seulement : jamais présentée comme le commerce, l'équipe ou le produit du client.

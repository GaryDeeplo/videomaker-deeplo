# Modèles

| Modèle | Pour | Durée |
|---|---|---|
| `promo-offre.json` | offre limitée, soldes, nouveauté à prix spécial | 20-30 s |
| `presentation-boutique.json` | commerce, atelier, cabinet | 30-45 s |
| `recrutement.json` | annonce d'emploi | 25-40 s |
| `temoignage-ecrit.json` | vrai avis client écrit, avec accord | 20-30 s |
| `produit-phare.json` | lancement / relance d'un produit (PNG détouré) | 20-35 s |
| `lot-exemple.json` | plusieurs vidéos × langues × formats (`batch.py`) | — |

Copie le modèle dans `jobs/<job>/work/<slug>_storyboard.json`, remplace chaque `<…>` par le vrai contenu du client,
supprime les scènes sans contenu réel (jamais de chiffre, prix, avis ou nom inventé) et les champs `_quand` / `_musique`.
Les blocs `intro-marque` / `outro-marque` demandent `branding` dans la charte ; sinon, retire-les.

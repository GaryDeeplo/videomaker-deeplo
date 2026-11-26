# Guide de tournage (avant que le client filme)

Scripts depuis la racine du projet : `PYTHONUTF8=1 python .claude/skills/videomaker-deeplo/scripts/<x>.py`.

`python .claude/skills/videomaker-deeplo/scripts/guide.py [--job <job>] --client "<nom>" --metier boutique|artisan|restaurant|service|recrutement|chantier [--brand <marque>] [--envoi "<lien de dépôt>"] [--contact "<qui appeler>"] [--format vertical|horizontal]`
-> `guide-tournage.html` (job : `renders/`, sinon `dist/`) : matériel, cadrage, lumière, son, comment parler et se
tromper sans stress, plan de script du métier à compléter avec SES mots et SES vrais chiffres, plans d'illustration à
filmer, autorisations, envoi des originaux (jamais par WhatsApp). Couleur d'accent de la charte. Lisible sur téléphone,
imprimable en PDF. Tu ne l'envoies pas toi-même : l'utilisateur le transmet.
Chantier (`--metier chantier`) : points fixes, plans de 10 s, accéléré posé, phrase repère.
Avec un texte prévu : prompteur `script.py prompteur` (`references/derush.md`).

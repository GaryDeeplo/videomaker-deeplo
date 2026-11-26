# Une longue vidéo -> plusieurs shorts (interview, webinaire, live) et recadrage qui suit le visage

Scripts depuis la racine du projet : `PYTHONUTF8=1 python .claude/skills/videomaker-deeplo/scripts/<x>.py`.

```bash
python .claude/skills/videomaker-deeplo/scripts/new_job.py "<client>" "<sujet>" --brand <marque>
python .claude/skills/videomaker-deeplo/scripts/transcribe.py <job> <vidéo complète> --slug <s>     # local, ~3x temps réel
python .claude/skills/videomaker-deeplo/scripts/shorts.py sentences <job> <s>                        # phrases numérotées -> work/<s>_sentences.txt
#   TU lis TOUTE la liste, corriges l'orthographe des noms propres dans words.json (champ w, jamais les temps),
#   ignores les phrases hallucinées (« Sous-titrage… »), puis écris work/<s>_shorts.json : 3 à 5 passages de
#   20 à 60 s qui se comprennent seuls (une question ou promesse, une réponse, si possible un chiffre),
#   avec from / to / skip (NUMÉROS de phrases), hook (titre des 3 premières secondes, ≤ 7 mots), why, post.
python .claude/skills/videomaker-deeplo/scripts/shorts.py make <job> <s> [--mode overlays] [--style <style>] [--mood upbeat]
#   --mode overlays si la source a déjà des sous-titres ; --style : tous les styles de build_composition.py
#   -> un job enfant par short (jobs/<job>-<nom>/), puis check + snapshot sur chacun
python .claude/skills/videomaker-deeplo/scripts/deliver.py <job>-<nom> short --formats 9:16
```
Chaque short garde la charte du parent ; ses fillers (« euh », tics, reformulations) sont repérés comme pour un rush :
relis-les (`references/derush.md`).

## Recadrage qui suit le visage
Source paysage avec une personne à l'image : `shorts.py make` lance `reframe.py` et la fenêtre 9:16 **suit le visage**
(détection locale YuNet, caméra posée qui ne glisse que quand la personne sort de la zone centrale ; trajet recalculé
pour chaque format à la livraison). Moins de 40 % d'images avec un visage (diapos, écran partagé) : image entière sur
fond flouté. Forcer : `"visual": {"fit": "fill"}` (image entière) ou `"cover"` (recadrage fixe, `focusX`).
Rush paysage hors shorts : `python .claude/skills/videomaker-deeplo/scripts/reframe.py <job> <slug>` après `build_cut.py`, puis `build_composition.py`.

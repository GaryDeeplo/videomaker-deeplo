# Installation de Deeplo Video Maker

> **Pour l'utilisateur :** ouvre ce dossier dans Claude Code (répertoire de travail = ce dossier) et envoie :
>
> ```
> Lis INSTALL.md et installe tout. Occupe-toi de la partie technique.
> ```
>
> Tu n'as rien à recopier. Claude vérifie ta machine, t'explique ce qui manque en français et attend ton « go ».

---

## Protocole pour l'agent

Ce qui suit t'est destiné. Ne le transforme pas en tutoriel terminal pour l'utilisateur.

**Règles** : une étape à la fois ; tu exécutes, l'utilisateur ne recopie rien ; rien n'est modifié avant son « go » ;
un outil absent n'est pas une erreur, dis-le calmement ; termine par un vrai test, jamais « c'est installé » sans preuve.
Lance les scripts Python avec `PYTHONUTF8=1` (accents sous Windows).

1. **Diagnostic, sans rien modifier** : `python .claude/skills/videomaker-deeplo/scripts/setup.py plan`.
   Résume en 3 lignes maximum : ce qui est prêt, ce qui manque, la durée estimée. Attends « go ».
2. **Outils système** (si `a_installer_par_l_utilisateur_ou_l_agent` n'est pas vide) : propose la commande donnée
   (winget / brew / apt), lance-la après accord, puis vérifie dans un **nouveau** terminal. Node doit être en 22+.
3. **Le reste** : `python .claude/skills/videomaker-deeplo/scripts/setup.py install` (paquets Python, skills HyperFrames,
   skill openverse-sfx, modèle Whisper ~1,6 Go, fichier `.env`). Compter 5 à 15 minutes la première fois.
4. **Clés** : demande à l'utilisateur sa clé **Gemini** gratuite (https://aistudio.google.com/apikey, compte Google)
   pour la voix off et écris-la dans `.env` (`GEMINI_API_KEY=`). Facultatif : **Fish Audio** (`FISH_API_KEY=`, payant)
   pour cloner une voix. Sans clé, la voix française locale (Kokoro) sert de secours pour tester.
   Facultatif : clé **Pixabay** gratuite (https://pixabay.com/api/docs/, affichée une fois connecté) dans `.env`
   (`PIXABAY_API_KEY=`) pour les plans de coupe en photos et vidéos ; sans elle, images libres Openverse.
   Ne montre jamais une clé dans la conversation après l'avoir écrite.
5. **Vérifier** : `python .claude/skills/videomaker-deeplo/scripts/check.py` puis
   `python .claude/skills/videomaker-deeplo/scripts/setup.py test` (crée une vidéo de 4 s, ~2 min). `ok: true` = installé.
6. **Charte du premier client** : propose de créer `brands/<client>/brand.json` (modèle :
   `brands/_exemple/brand.json`) avec son logo, ses couleurs et sa police.
7. Présente le guide `README.md` en 5 lignes et demande quelle vidéo faire en premier.

Ensuite, tout passe par le skill `videomaker-deeplo` (`.claude/skills/videomaker-deeplo/SKILL.md`).

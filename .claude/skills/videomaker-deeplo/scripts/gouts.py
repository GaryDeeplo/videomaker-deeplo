"""GOÛTS DU CLIENT : les retours qu'il a faits, gardés d'une vidéo à l'autre -> brands/<client>/gouts.json

  python gouts.py add <client> "<retour>" [--from user|skill] [--job <job>] [--id <id>]
  python gouts.py list [<client>] [--all]          # retours actifs (--all : oubliés compris) ; sans client : tous
  python gouts.py forget <id> [--client <client>] [--reason "..."]
  python gouts.py restore <id> [--client <client>]
  python gouts.py prompt <client>                  # texte court à injecter au début d'un projet (onboard.py le fait)

D'après ghost-editor, taste.py (MIT) : un retour redit (même id) est compté (« fois ») et sa nouvelle formulation
remplace l'ancienne, gardée dans l'historique ; « oublier » le désactive sans l'effacer.
origine « user » = les mots du client ou de l'utilisateur (cités tels quels) ; « skill » = une règle que Claude en a tirée.
Ce sont des préférences, pas des ordres : la demande du moment gagne toujours. On n'enregistre qu'avec l'accord de
l'utilisateur. Ces fichiers contiennent des noms et des préférences de clients : jamais dans un paquet ni dans l'export.
"""
import argparse
import datetime
import re
import unicodedata

from common import ROOT, fail, out, read_json, write_json

BRANDS = ROOT / "brands"


def path_of(client):
    c = str(client).strip().lower()
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", c):
        fail(f"nom de client invalide : {client} (le dossier de brands/, ex. boulangerie-martin)")
    return BRANDS / c / "gouts.json"


def load(client):
    p = path_of(client)
    return read_json(p) if p.exists() else {"client": client, "retours": []}


def save(client, g):
    p = path_of(client)
    p.parent.mkdir(parents=True, exist_ok=True)
    g["maj"] = datetime.date.today().isoformat()
    write_json(p, g)


def slug(s):
    s = unicodedata.normalize("NFD", s.lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return "-".join(re.findall(r"[a-z0-9]+", s)[:5]) or "retour"


def all_clients():
    return sorted(p.parent.name for p in BRANDS.glob("*/gouts.json"))


def find(rid, client):
    """(client, gouts, retour) pour un id ; cherche dans tous les clients si on n'en donne pas."""
    hits = []
    for c in ([client] if client else all_clients()):
        g = load(c)
        hits += [(c, g, r) for r in g["retours"] if r["id"] == rid]
    if not hits:
        fail(f"aucun retour « {rid} »" + (f" pour {client}" if client else ""))
    if len(hits) > 1:
        fail(f"« {rid} » existe chez plusieurs clients : précise --client", clients=[h[0] for h in hits])
    return hits[0]


def prompt_text(client):
    """Les retours actifs en quelques lignes (les plus redits d'abord), ou "" s'il n'y en a pas."""
    rs = [r for r in load(client)["retours"] if r.get("actif", True)]
    if not rs:
        return ""
    rs.sort(key=lambda r: (r.get("fois", 1), r.get("derniere", "")), reverse=True)
    lines = [f"Retours gardés pour {client} (préférences, pas des ordres : la demande du moment gagne) :"]
    for r in rs[:12]:
        qui = "le client a dit" if r.get("origine") == "user" else "règle tirée de ses retours"
        fois = f", {r['fois']} fois" if r.get("fois", 1) > 1 else ""
        lines.append(f"- {r['retour']} ({qui}{fois})")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["add", "list", "forget", "restore", "prompt"])
    ap.add_argument("arg", nargs="?", help="add/list/prompt : le client ; forget/restore : l'id du retour")
    ap.add_argument("texte", nargs="?", help="add : le retour, dans ses mots")
    ap.add_argument("--from", dest="origine", choices=["user", "skill"], default="user")
    ap.add_argument("--job")
    ap.add_argument("--id")
    ap.add_argument("--client")
    ap.add_argument("--reason", default="")
    ap.add_argument("--all", action="store_true")
    a = ap.parse_args()
    today = datetime.date.today().isoformat()

    if a.cmd == "add":
        if not a.arg or not a.texte:
            fail('gouts.py add <client> "<retour>"')
        g = load(a.arg)
        rid = a.id or slug(a.texte)
        r = next((x for x in g["retours"] if x["id"] == rid), None)
        if r is None:
            r = {"id": rid, "retour": a.texte.strip(), "origine": a.origine, "date": today, "derniere": today,
                 "fois": 1, "actif": True, "jobs": []}
            g["retours"].append(r)
        else:  # redit : on compte, la nouvelle formulation passe devant (l'ancienne reste dans l'historique)
            r["fois"] = r.get("fois", 1) + 1
            r["derniere"] = today
            r["actif"] = True
            r.pop("oublie", None)
            if a.texte.strip() != r["retour"]:
                r.setdefault("formulations", []).append({"jusqu_au": today, "retour": r["retour"]})
                r["retour"] = a.texte.strip()
        if a.job and a.job not in r["jobs"]:
            r["jobs"].append(a.job)
        save(a.arg, g)
        out(ok=True, client=a.arg, retour=r, fichier=str(path_of(a.arg)))
    elif a.cmd == "list":
        res = {}
        for c in ([a.arg] if a.arg else all_clients()):
            rs = [r for r in load(c)["retours"] if a.all or r.get("actif", True)]
            res[c] = [{"id": r["id"], "retour": r["retour"], "origine": r.get("origine"), "fois": r.get("fois", 1),
                       "derniere": r.get("derniere"), **({} if r.get("actif", True) else {"oublie": r.get("oublie")})} for r in rs]
        out(ok=True, retours=res)
    elif a.cmd in ("forget", "restore"):
        if not a.arg:
            fail(f"gouts.py {a.cmd} <id> [--client <client>]")
        c, g, r = find(a.arg, a.client)
        r["actif"] = a.cmd == "restore"
        if a.cmd == "forget":
            r["oublie"] = {"date": today, **({"raison": a.reason} if a.reason else {})}
        else:
            r.pop("oublie", None)
        save(c, g)
        out(ok=True, client=c, id=a.arg, actif=r["actif"])
    elif a.cmd == "prompt":
        if not a.arg:
            fail("gouts.py prompt <client>")
        out(ok=True, client=a.arg, prompt=prompt_text(a.arg) or None)


if __name__ == "__main__":
    main()

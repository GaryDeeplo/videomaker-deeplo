"""CALENDRIER DE PUBLICATION -> planning.html (page à donner au client) + planning.ics (rappels) + planning.csv

  python planning.py <lot.json | job:slug,job:slug…> --start 2026-11-24 [--days mar,jeu,sam]
                     [--networks instagram,tiktok,facebook] [--langs fr,nl] [--out <dossier>]

Une vidéo par jour de publication (dans l'ordre du lot), publiée le même jour sur chaque réseau à son heure. Le texte
vient de work/<slug>_post[_<langue>].json (légende + appel à l'action) ; les hashtags sont réduits selon le réseau.
Vidéos et couvertures : celles de la page du lot (jobs/_lots/<lot>/) sinon de renders/livraison[_<langue>]/ du job.
Les horaires sont des repères génériques, à ajuster avec les statistiques du compte du client (dis-le-lui).
Rien n'est publié : c'est un planning à suivre ou à importer dans l'outil de programmation du client.
"""
import argparse
import csv
import datetime as dt
import html
import os
from pathlib import Path

from common import ROOT, fail, job_dir, out, read_json

NETS = {  # libellé, heure repère, hashtags max, format conseillé
    "instagram": ("Instagram Reels", "18:30", 8, "9x16"),
    "tiktok": ("TikTok", "19:00", 5, "9x16"),
    "facebook": ("Facebook", "12:30", 3, "9x16"),
    "linkedin": ("LinkedIn", "08:30", 3, "1x1"),
    "youtube": ("YouTube Shorts", "17:00", 3, "9x16"),
}
DAYS = {"lun": 0, "mar": 1, "mer": 2, "jeu": 3, "ven": 4, "sam": 5, "dim": 6}
JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]


def esc(s):
    return html.escape(str(s), quote=True)


def ics_text(s):
    return str(s).replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def find_media(job, slug, lang, fmt, lot_dir):
    sfx = f"_{lang}" if lang != "fr" else ""
    names = [f"{slug}_{fmt}{sfx}.mp4", f"{slug}_9x16{sfx}.mp4"]
    dirs = ([lot_dir / f"{job.name}{sfx}"] if lot_dir else []) + [job / "renders" / f"livraison{sfx}"]
    for d in dirs:
        for n in names:
            if (d / n).exists():
                cov = d / n.replace(".mp4", "_cover.jpg")
                return d / n, (cov if cov.exists() else None)
    return None, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source", help="lot.json, ou job:slug séparés par des virgules")
    ap.add_argument("--start", required=True, help="premier jour (AAAA-MM-JJ)")
    ap.add_argument("--days", default="mar,jeu,sam")
    ap.add_argument("--networks", default="instagram,tiktok,facebook")
    ap.add_argument("--langs")
    ap.add_argument("--out")
    a = ap.parse_args()

    lot_dir, client, name = None, "", "planning"
    if a.source.endswith(".json"):
        lot = read_json(Path(a.source))
        items = [(job_dir(i["job"]), i["slug"]) for i in lot["items"]]
        langs = (a.langs or ",".join(lot.get("langs", ["fr"]))).split(",")
        client, name = lot.get("client", ""), lot.get("name", "planning")
        lot_dir = ROOT / "jobs" / "_lots" / name
        lot_dir = lot_dir if lot_dir.exists() else None
    else:
        items = [(job_dir(x.split(":")[0]), x.split(":")[1]) for x in a.source.split(",")]
        langs = (a.langs or "fr").split(",")
    nets = [n for n in a.networks.split(",") if n]
    for n in nets:
        if n not in NETS:
            fail(f"réseau inconnu : {n}", reseaux=list(NETS))
    days = sorted(DAYS[d] for d in a.days.split(","))
    dst = Path(a.out) if a.out else (lot_dir or items[0][0] / "renders")
    dst.mkdir(parents=True, exist_ok=True)

    day, rows = dt.date.fromisoformat(a.start), []
    for job, slug in items:
        while day.weekday() not in days:
            day += dt.timedelta(days=1)
        for lang in langs:
            sfx = f"_{lang}" if lang != "fr" else ""
            pj = job / "work" / f"{slug}_post{sfx}.json"
            post = read_json(pj) if pj.exists() else {}
            hj = job / "work" / f"{slug}_hook{sfx}.json"
            title = read_json(hj)["text"] if hj.exists() else (post.get("caption", "")[:60] or job.name)
            for n in nets:
                label, hour, nh, fmt = NETS[n]
                video, cover = find_media(job, slug, lang, fmt, lot_dir)
                tags = post.get("hashtags", [])[:nh]
                text = "\n\n".join(x for x in (post.get("caption", ""), post.get("cta", ""), " ".join(tags)) if x)
                rows.append({"date": day.isoformat(), "heure": hour, "reseau": label, "net": n, "langue": lang.upper(),
                             "titre": title, "texte": text, "a_valider": not pj.exists(),
                             "video": os.path.relpath(video, dst).replace("\\", "/") if video else "",
                             "couverture": os.path.relpath(cover, dst).replace("\\", "/") if cover else ""})
        day += dt.timedelta(days=1)

    with open(dst / "planning.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["date", "heure", "réseau", "langue", "titre", "vidéo", "couverture", "texte du post"])
        for r in rows:
            w.writerow([r["date"], r["heure"], r["reseau"], r["langue"], r["titre"], r["video"], r["couverture"], r["texte"]])

    stamp = dt.datetime.now().strftime("%Y%m%dT%H%M%S")
    ev = []
    for k, r in enumerate(rows):
        t0 = r["date"].replace("-", "") + "T" + r["heure"].replace(":", "") + "00"
        ev.append("\r\n".join([
            "BEGIN:VEVENT", f"UID:{name}-{k}-{r['date']}@deeplo-video-maker", f"DTSTAMP:{stamp}", f"DTSTART:{t0}",
            "DURATION:PT15M", f"SUMMARY:{ics_text('Publier : ' + r['titre'] + ' (' + r['reseau'] + ', ' + r['langue'] + ')')}",
            f"DESCRIPTION:{ics_text(r['texte'] + (chr(10) * 2 + 'Vidéo : ' + r['video'] if r['video'] else ''))}",
            "BEGIN:VALARM", "ACTION:DISPLAY", "TRIGGER:-PT30M", "DESCRIPTION:Publication dans 30 min", "END:VALARM", "END:VEVENT"]))
    (dst / "planning.ics").write_text("BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//Deeplo//Video Maker//FR\r\nCALSCALE:GREGORIAN\r\n"
                                      + "\r\n".join(ev) + "\r\nEND:VCALENDAR\r\n", encoding="utf-8")

    def fr_date(d):
        dd = dt.date.fromisoformat(d)
        return f"{JOURS[dd.weekday()]} {dd.day} {MOIS[dd.month - 1]}"

    groups = {}  # une carte par jour × vidéo × langue ; les réseaux et leurs heures en liste
    for r in rows:
        groups.setdefault((r["date"], r["titre"], r["langue"]), []).append(r)
    by_day = {}
    for (d, _, _), rs in groups.items():
        by_day.setdefault(d, []).append(rs)
    secs = []
    for d, grs in by_day.items():
        cards = []
        for i, rs in enumerate(grs):
            r = max(rs, key=lambda x: len(x["texte"]))  # le texte le plus complet (tous les hashtags)
            cov = f'<img src="{esc(r["couverture"])}" alt="">' if r["couverture"] else '<div class="nocov">couverture à venir</div>'
            vid = f'<a href="{esc(r["video"])}" download>Télécharger la vidéo</a>' if r["video"] else '<span class="warn">vidéo pas encore livrée</span>'
            val = ' <span class="warn">texte à écrire</span>' if r["a_valider"] else ""
            when = " · ".join(f'<b>{esc(x["heure"])}</b> {esc(x["reseau"])}' for x in sorted(rs, key=lambda x: x["heure"]))
            nh = ", ".join(f'{NETS[x["net"]][0]} : {NETS[x["net"]][2]} premiers' for x in rs if NETS[x["net"]][2] < 8)
            cards.append(f'''<article class="card"><div class="cov">{cov}</div><div class="body">
<div class="meta">{when} · {esc(r["langue"])}{val}</div>
<h3>{esc(r["titre"])}</h3><pre id="t-{d}-{i}">{esc(r["texte"])}</pre>
{f'<p class="note">Hashtags — {esc(nh)}.</p>' if nh else ""}
<div class="act"><button onclick="cp('t-{d}-{i}', this)">Copier le texte</button> {vid}</div></div></article>''')
        head = fr_date(d)
        secs.append(f'<section><h2>{esc(head[0].upper() + head[1:])}</h2>{"".join(cards)}</section>')
    first, last = fr_date(rows[0]["date"]), fr_date(rows[-1]["date"])
    page = f"""<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Planning de publication</title><style>
:root {{ --bg: #f6f5f2; --card: #fff; --ink: #1d1d1f; --mute: #6b6b70; --acc: #2f5bea; --warn: #b4530b; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg: #141416; --card: #1e1e22; --ink: #f2f2f4; --mute: #9a9aa2; --acc: #7a9bff; --warn: #f0a050; }} }}
body {{ margin: 0; background: var(--bg); color: var(--ink); font: 15px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; }}
main {{ max-width: 960px; margin: 0 auto; padding: 28px 16px 60px; }}
h1 {{ margin: 0 0 4px; font-size: 26px; }} .sub {{ color: var(--mute); margin: 0 0 18px; }}
.dl a {{ color: var(--acc); margin-right: 16px; font-weight: 600; }}
h2 {{ margin: 34px 0 12px; font-size: 19px; }}
.card {{ display: flex; gap: 16px; background: var(--card); border-radius: 14px; padding: 14px; margin-bottom: 12px;
        box-shadow: 0 1px 3px rgba(0,0,0,.08); }}
.cov {{ flex: 0 0 120px; }} .cov img {{ width: 120px; border-radius: 8px; display: block; }}
.nocov {{ width: 120px; height: 213px; border-radius: 8px; background: rgba(127,127,127,.15); color: var(--mute); font-size: 12px;
         display: flex; align-items: center; justify-content: center; text-align: center; }}
.body {{ flex: 1; min-width: 0; }} .meta {{ color: var(--mute); font-size: 13px; }} .meta b {{ color: var(--ink); }}
h3 {{ margin: 4px 0 8px; font-size: 16px; }}
.note {{ color: var(--mute); font-size: 13px; margin: -4px 0 10px; }}
pre {{ white-space: pre-wrap; font-family: inherit; font-size: 14px; line-height: 1.5; background: rgba(127,127,127,.08); padding: 10px 12px; border-radius: 8px; margin: 0 0 10px; }}
.act {{ display: flex; flex-wrap: wrap; gap: 12px; align-items: center; }} .act a {{ color: var(--acc); }}
button {{ background: var(--acc); color: #fff; border: 0; padding: 8px 12px; border-radius: 8px; font-weight: 600; cursor: pointer; }}
.warn {{ color: var(--warn); font-weight: 600; }}
@media (max-width: 560px) {{ .card {{ flex-direction: column; }} .cov, .cov img, .nocov {{ width: 100%; max-width: 220px; }} }}
</style></head><body><main>
<h1>Planning de publication{(" · " + esc(client)) if client else ""}</h1>
<p class="sub">{len(items)} vidéo(s) · du {esc(first)} au {esc(last)} · {esc(", ".join(NETS[n][0] for n in nets))}</p>
<p class="dl"><a href="planning.ics" download>Ajouter à mon agenda (.ics)</a><a href="planning.csv" download>Tableau (.csv)</a></p>
<p class="sub">Horaires indicatifs : à ajuster selon les statistiques de votre compte (moments où votre audience est en ligne).</p>
{"".join(secs)}
</main><script>
function cp(id, b) {{ navigator.clipboard.writeText(document.getElementById(id).innerText).then(function () {{
  var t = b.textContent; b.textContent = "Copié"; setTimeout(function () {{ b.textContent = t; }}, 1500); }}); }}
</script></body></html>"""
    (dst / "planning.html").write_text(page, encoding="utf-8")
    out(ok=True, page=str(dst / "planning.html"), publications=len(rows), du=first, au=last,
        textes_a_ecrire=sorted({r["titre"] for r in rows if r["a_valider"]}),
        suite="ouvre planning.html pour l'utilisateur ; rien n'est publié ni envoyé")


if __name__ == "__main__":
    main()

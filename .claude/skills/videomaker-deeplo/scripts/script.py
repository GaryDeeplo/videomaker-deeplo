"""MONTAGE DEPUIS UN SCRIPT ÉCRIT : le texte prévu sert de guide au tournage (prompteur) puis au dérush (meilleure
prise de chaque phrase, phrases manquantes signalées).

  python script.py prompteur <job> [--script texte.txt] [--client "Nom"]   # -> renders/prompteur.html (téléphone / tablette)
  python script.py match <job> <slug> [--script texte.txt]                 # après cut_plan.py : keep / reason dans <slug>_plan.json
                                                                           #   + work/<slug>_script_report.json

Le script : work/script.txt (ou --script) ; une phrase par ligne ou un texte ponctué. Le prompteur défile à la vitesse
choisie (espace = pause, flèches = vitesse, M = miroir pour un prompteur à vitre), une phrase par bloc, avec un repère
« pause » entre les blocs : chaque phrase devient un îlot propre au dérush.
match compare chaque îlot de parole (cut_plan.py) aux phrases du script, mot à mot : pour chaque phrase, la prise la
plus complète est gardée (à égalité, la dernière : c'est souvent la bonne), les autres prises sont écartées avec leur
raison, les îlots hors script sont signalés (« hors script : à relire », gardés si --garder-hors-script), et les
phrases jamais dites en entier sont listées (à refaire ou à retirer du script). Les temps viennent des mots
horodatés : aucun timecode écrit.
"""
import argparse
import html
import json
import re
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

from common import fail, job_dir, out, read_json, write_json

esc = lambda s: html.escape(str(s), quote=True)


def norm(s):
    s = unicodedata.normalize("NFD", s.lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.findall(r"[a-z0-9]+", s.replace("'", " ").replace("’", " "))


def read_script(job, path):
    p = Path(path) if path else job / "work" / "script.txt"
    if not p.is_absolute() and path:
        p = job / path if (job / path).exists() else Path(path)
    if not p.exists():
        fail(f"script introuvable : {p} (colle le texte dans work/script.txt)")
    txt = p.read_text(encoding="utf-8").strip()
    parts = []
    for line in txt.splitlines():
        line = line.strip()
        if not line:
            continue
        parts += [x.strip() for x in re.split(r"(?<=[.!?…])\s+", line) if x.strip()]
    return parts


def coverage(sent, isl):
    """Part des mots de la phrase dits dans l'ordre dans l'îlot, et part de l'îlot qui appartient à la phrase."""
    a, b = norm(sent), norm(isl)
    if not a or not b:
        return 0.0, 0.0
    m = sum(bl.size for bl in SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks())
    return m / len(a), m / len(b)


def match(job, slug, script_path, keep_extra=False):
    pj = job / "work" / f"{slug}_plan.json"
    if not pj.exists():
        fail("lance d'abord cut_plan.py (îlots de parole)")
    plan = read_json(pj)
    sents = read_script(job, script_path)
    isl = plan["islands"]
    # meilleure phrase de chaque îlot (un îlot peut couvrir plusieurs phrases : on garde toutes celles qu'il couvre bien)
    covers = {}
    for it in isl:
        if it.get("reason", "").startswith("hésitation"):
            continue
        for k, s in enumerate(sents):
            c, own = coverage(s, it["text"])
            if c >= 0.5 and own >= 0.3:
                covers.setdefault(k, []).append((c, it["id"]))
    chosen, report = {}, []
    for k, s in enumerate(sents):
        takes = covers.get(k, [])
        if not takes:
            report.append({"phrase": k + 1, "texte": s, "statut": "manquante", "prises": 0})
            continue
        best_c = max(c for c, _ in takes)
        # à couverture presque égale (5 %), la dernière prise
        best = max((c, i) for c, i in takes if c >= best_c - 0.05)[1]
        chosen.setdefault(best, []).append(k)
        report.append({"phrase": k + 1, "texte": s, "statut": "complète" if best_c >= 0.85 else "incomplète",
                       "prise": best, "couverture": round(best_c, 2), "prises": len(takes)})
    used_sent = {k for ks in chosen.values() for k in ks}
    for it in isl:
        if it.get("reason", "").startswith("hésitation"):
            continue
        if it["id"] in chosen:
            it["keep"], it["reason"] = True, "script : phrase " + ", ".join(str(k + 1) for k in chosen[it["id"]])
            continue
        mine = [k for k, takes in covers.items() if any(i == it["id"] for _, i in takes)]
        if mine:
            it["keep"], it["reason"] = False, "autre prise de la phrase " + ", ".join(str(k + 1) for k in mine) + " (moins complète ou plus ancienne)"
        else:
            it["keep"] = bool(keep_extra)
            it["reason"] = "hors script : à relire" + (" (gardé)" if keep_extra else "")
    write_json(pj, plan)
    order = [k for i in sorted(chosen) for k in chosen[i]]
    out_of_order = order != sorted(order)
    rep = {"phrases": len(sents), "completes": sum(r["statut"] == "complète" for r in report),
           "incompletes": [r["phrase"] for r in report if r["statut"] == "incomplète"],
           "manquantes": [r["phrase"] for r in report if r["statut"] == "manquante"],
           "hors_script": [it["id"] for it in isl if it.get("reason", "").startswith("hors script")],
           "ordre_different": out_of_order, "detail": report}
    write_json(job / "work" / f"{slug}_script_report.json", rep)
    out(ok=True, phrases=rep["phrases"], completes=rep["completes"], incompletes=rep["incompletes"], manquantes=rep["manquantes"],
        hors_script=rep["hors_script"], ordre_different=out_of_order,
        suite="relis les îlots « hors script » et les phrases manquantes, puis build_cut.py"
              + (" ; l'ordre dit diffère du script : multi.py / ordre à valider" if out_of_order else ""))


def prompteur(job, script_path, client):
    sents = read_script(job, script_path)
    blocks = "".join(f'<p><span class="n">{k + 1}</span>{esc(s)}</p><div class="pause">· pause ·</div>' for k, s in enumerate(sents))
    doc = f"""<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Prompteur{(' · ' + esc(client)) if client else ''}</title>
<style>
 :root {{ --fs: 44px; }}
 html, body {{ margin: 0; background: #000; color: #fff; font: 600 var(--fs)/1.35 system-ui, -apple-system, sans-serif; }}
 #txt {{ padding: 50vh 7vw 80vh; max-width: 900px; margin: 0 auto; }}
 #txt.miroir {{ transform: scaleX(-1); }}
 p {{ margin: 0 0 .2em; }} .n {{ font-size: .45em; color: #ffd60a; margin-right: .5em; vertical-align: middle; }}
 .pause {{ font-size: .4em; color: #666; text-align: center; margin: .6em 0 1.2em; letter-spacing: .2em; }}
 #ligne {{ position: fixed; left: 0; right: 0; top: 38vh; height: 3px; background: #ffd60a55; pointer-events: none; }}
 #bar {{ position: fixed; left: 0; right: 0; bottom: 0; display: flex; gap: 8px; padding: 10px 12px calc(10px + env(safe-area-inset-bottom));
        background: #111d; font: 500 16px system-ui; align-items: center; flex-wrap: wrap; }}
 button {{ font: 600 16px system-ui; padding: 10px 14px; border-radius: 10px; border: 0; background: #333; color: #fff; }}
 button.go {{ background: #ffd60a; color: #000; }} label {{ display: flex; align-items: center; gap: 6px; }}
 input[type=range] {{ width: 110px; }}
</style></head><body>
<div id="ligne"></div>
<div id="txt">{blocks}<p style="text-align:center;color:#ffd60a">Fin. Coupez.</p></div>
<div id="bar"><button class="go" id="go">▶ Lancer</button><button id="top">⟲ Début</button>
<label>Vitesse <input id="v" type="range" min="10" max="160" value="55"></label>
<label>Taille <input id="t" type="range" min="28" max="80" value="44"></label><button id="mi">Miroir</button></div>
<script>
 let run = false, last = 0, acc = 0;
 const v = document.getElementById("v"), t = document.getElementById("t"), go = document.getElementById("go");
 function step(ts) {{ if (run) {{ acc += (ts - last) / 1000 * v.value; if (acc >= 1) {{ window.scrollBy(0, Math.floor(acc)); acc -= Math.floor(acc); }} }} last = ts; requestAnimationFrame(step); }}
 requestAnimationFrame(step);
 function toggle() {{ run = !run; go.textContent = run ? "❚❚ Pause" : "▶ Lancer"; }}
 go.onclick = toggle; document.getElementById("top").onclick = function () {{ window.scrollTo(0, 0); }};
 document.getElementById("mi").onclick = function () {{ document.getElementById("txt").classList.toggle("miroir"); }};
 t.oninput = function () {{ document.documentElement.style.setProperty("--fs", t.value + "px"); }};
 document.addEventListener("keydown", function (e) {{
   if (e.code === "Space") {{ e.preventDefault(); toggle(); }}
   if (e.key === "ArrowUp") v.value = +v.value + 10; if (e.key === "ArrowDown") v.value = +v.value - 10;
   if (e.key === "m" || e.key === "M") document.getElementById("txt").classList.toggle("miroir"); }});
</script></body></html>"""
    d = job / "renders"
    d.mkdir(exist_ok=True)
    (d / "prompteur.html").write_text(doc, encoding="utf-8")
    out(ok=True, page=str(d / "prompteur.html"), phrases=len(sents),
        conseil="une phrase = une prise ; en cas d'erreur, marquer une pause et reprendre la phrase depuis le début")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["prompteur", "match"])
    ap.add_argument("job")
    ap.add_argument("slug", nargs="?")
    ap.add_argument("--script")
    ap.add_argument("--client")
    ap.add_argument("--garder-hors-script", action="store_true")
    a = ap.parse_args()
    job = job_dir(a.job)
    if a.cmd == "prompteur":
        prompteur(job, a.script, a.client)
    else:
        if not a.slug:
            fail("slug manquant")
        match(job, a.slug, a.script, a.garder_hors_script)


if __name__ == "__main__":
    main()

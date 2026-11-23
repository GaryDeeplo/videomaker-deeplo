"""SOUND DESIGN AUTOMATIQUE : un petit bruitage sur ce qui apparaît à l'écran (whoosh sur un changement de plan, pop sur
un élément de liste, clic sur un bouton, impact sur un chiffre, ding sur une notification…), calé sur l'instant
exact de l'animation, lu dans la composition elle-même. Marche avec tous les monteurs (rush, scènes, explainer,
punch, infographie, montage) ; les monteurs l'appellent d'eux-mêmes (config "sfx": {"design": true}, par défaut).

  python sound_design.py <job> [--off] [--densite 0.45]

- Instants : début de chaque plan / scène / temps fort / bloc (data-start) et chaque entrée animée à l'intérieur
  (tl.fromTo(... opacity: 0 ...)), décalage des timelines imbriquées compris. Jamais un timecode écrit à la main.
- Sons : banque locale sounds/openverse (real-sfx), un fichier différent à chaque fois dans la même famille, volume
  harmonisé une fois pour toutes (loudnorm) puis dosé par famille ; rien sur les sous-titres.
- Retenue : au moins 0,45 s entre deux bruitages (les changements de plan passent en priorité), rien à moins de 0,3 s
  d'un son déjà posé par le monteur (whoosh des punchs, ticks), et au plus 1 son par seconde en moyenne.
Relancer remplace le bloc précédent (balise <!-- sound-design -->).
"""
import argparse
import re
import subprocess
from pathlib import Path

from common import SOUNDS, config, job_dir, out, probe

BANK = SOUNDS / "openverse"
MARK_A, MARK_B = "<!-- sound-design -->", "<!-- /sound-design -->"
VOL = {"whoosh": 0.42, "swoosh": 0.4, "pop": 0.45, "click": 0.5, "tick": 0.32, "ding": 0.38, "hit": 0.45, "sparkle": 0.32,
       "chime": 0.38, "swell": 0.3, "typing": 0.3, "cash": 0.38, "paper": 0.38, "boom": 0.4}
PRIO = {"whoosh": 3, "swoosh": 3, "hit": 2, "boom": 2, "ding": 2, "chime": 2, "cash": 2}
MAXLEN = {"swell": 2.5, "chime": 2.0, "sparkle": 2.0}

# blocs de la bibliothèque (data-composition-src) -> famille
BLOCKS = {"compteur": "tick", "note-etoiles": "sparkle", "sticker": "pop", "notification": "ding", "bouton-cta": "click",
          "confetti": "sparkle", "compte-rebours": "tick", "jauge": "swell", "barres": "swell", "tarif": "cash", "suivre": "click",
          "fleche": "swoosh", "surligneur": "swoosh", "frise": "swoosh", "machine-a-ecrire": "typing", "intro-marque": "whoosh",
          "outro-marque": "chime", "bandeau-nom": "swoosh", "marquee": "swoosh", "mot-tournant": "pop", "lottie": "pop"}
# classes de clip -> famille (None = silence)
CLIPS = [("cap", None), ("hd", None), ("ser", None), ("shade", None), ("lab", "tick"), ("shotv", "whoosh"), ("shot", "whoosh"),
         ("scene", "whoosh"), ("cmp", "swoosh"), ("pwrap", "pop"), ("ttls", "hit"), ("beat", "swoosh"), ("card", "pop"), ("br", "whoosh")]
# classes de l'élément animé à l'intérieur -> famille
INNER = [(r"\b(big|num|stat|price|pct|count|cnt)\b", "hit"), (r"\b(btn|button|cta|cur|cursor|done)\b", "click"),
         (r"\b(notif|msg|bubble|toast)\b", "ding"), (r"\b(stamp|stampx|tag|tagp)\b", "hit"), (r"\b(chart|line|bar|bars|gauge|curve)\b", "swell"),
         (r"\b(pill|chip|item|row|stp|p\d+|r\d+|it\d*|li|card|tile|dbx|x\d+)\b", "pop")]


def files(cat):
    """Sons courts de la famille (les plus longs ne servent pas de ponctuation)."""
    d = BANK / cat
    fs = sorted(d.glob("*.mp3")) + sorted(d.glob("*.wav"))
    res = []
    for f in fs:
        try:
            du = float(probe(f)["duration"])
        except Exception:  # noqa: BLE001
            continue
        if du <= MAXLEN.get(cat, 1.6):
            res.append((f, du))
    return res


def prepared(job, f):
    """Copie harmonisée (même niveau pour tous les sons) dans assets/sfx/ ; renvoie (src relatif, durée)."""
    d = job / "assets" / "sfx"
    d.mkdir(parents=True, exist_ok=True)
    dst = d / f"sd_{f.stem}.wav"
    if not dst.exists():
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(f), "-af", "loudnorm=I=-20:TP=-3:LRA=7", "-ar", "48000", "-ac", "2",
                        str(dst)], check=True)
    return f"assets/sfx/{dst.name}", round(float(probe(dst)["duration"]), 3)


def events(html_):
    """[(t, famille, quoi)] lus dans la composition."""
    ev, kinds = [], {}
    for m in re.finditer(r"<(div|video|img|section)\b([^>]*\bclass=\"clip\b[^\"]*\"[^>]*)>", html_):
        attrs = m.group(2)
        cls = re.search(r'class="([^"]*)"', attrs).group(1).split()
        st = re.search(r'data-start="([\d.]+)"', attrs)
        if not st:
            continue
        t = float(st.group(1))
        idm = re.search(r'\bid="([^"]+)"', attrs)
        src = re.search(r'data-composition-src="[^"]*?([\w-]+)\.html"', attrs)
        if src:
            name = src.group(1)
            fam = "hit" if name.startswith("accroche-") else next((v for k, v in BLOCKS.items() if name.startswith(k)), "pop")
            ev.append((t + (0.15 if name.startswith("accroche-") else 0.05), fam, name))
            if name.startswith("accroche-"):
                du = re.search(r'data-duration="([\d.]+)"', attrs)
                if du:
                    ev.append((t + float(du.group(1)) - 0.45, "whoosh", name + " (sortie)"))
            continue
        fam = "skip"
        for k, v in CLIPS:
            if k in cls or (idm and k == "br" and idm.group(1).startswith("br-")):
                fam = v
                break
        if idm:
            kinds[idm.group(1)] = fam
        if fam not in ("skip", None) and t > 0.05:
            ev.append((t, fam, " ".join(cls[1:]) or (idm.group(1) if idm else "")))
    # décalage des timelines imbriquées (master.add(tl, T0), tl.add(ct, T0))
    off = {}
    for m in re.finditer(r"(\w+)\.add\((\w+),\s*([\d.]+)\)", html_):
        off[m.group(2)] = off.get(m.group(1), 0.0) + float(m.group(3))
    # entrées animées à l'intérieur d'un clip qui fait du bruit (élément de liste, chiffre, bouton…)
    for m in re.finditer(r"(\w+)\.fromTo\(\"#([\w-]+) ([^\"]+)\",\s*\{([^}]*)\}\s*,\s*\{[^}]*\}\s*,\s*([\d.]+)\s*\)", html_):
        var, cid, sel, frm, t = m.groups()
        if "opacity: 0" not in frm or kinds.get(cid) in (None, "skip") and cid in kinds:
            continue
        if cid not in kinds or kinds[cid] in (None,):
            continue
        fam = next((v for pat, v in INNER if re.search(pat, sel)), None)
        if fam:
            ev.append((float(t) + off.get(var, 0.0), fam, f"#{cid} {sel}"))
    return sorted(ev)


def existing(html_):
    """Instants des sons déjà posés par le monteur (hors voix et musique)."""
    res = []
    for m in re.finditer(r"<audio\b([^>]*)>", html_):
        a = m.group(1)
        if 'id="voice"' in a or 'id="music"' in a or "sd-" in a:
            continue
        st = re.search(r'data-start="([\d.]+)"', a)
        if st:
            res.append(float(st.group(1)))
    return res


def apply(job, gap=0.45, off=False):
    p = job / "index.html"
    h = p.read_text(encoding="utf-8")
    h = re.sub(re.escape(MARK_A) + r".*?" + re.escape(MARK_B) + r"\n?", "", h, flags=re.S)
    if off:
        p.write_text(h, encoding="utf-8")
        return {"sons": 0}
    dur_m = re.search(r'data-composition-id="[^"]+"[^>]*data-duration="([\d.]+)"', h)
    total = float(dur_m.group(1)) if dur_m else 1e9
    ev = [e for e in events(h) if 0.1 < e[0] < total - 0.2]
    taken = existing(h)
    # priorité aux changements de plan : on les garde d'abord, puis le reste dans les trous
    kept = []
    for prio in (3, 2, 1):
        for t, fam, what in ev:
            if PRIO.get(fam, 1) != prio:
                continue
            if any(abs(t - x) < 0.3 for x in taken) or any(abs(t - k[0]) < gap for k in kept):
                continue
            kept.append((t, fam, what))
    kept.sort()
    budget = max(3, int(total))  # au plus ~1 son par seconde
    if len(kept) > budget:
        kept = sorted(sorted(kept, key=lambda e: -PRIO.get(e[1], 1))[:budget])
    nodes, used, last = [], {}, {}
    pool = {}
    for i, (t, fam, what) in enumerate(kept):
        if fam not in pool:
            pool[fam] = files(fam)
        fs = pool[fam]
        if not fs:
            continue
        k = used.get(fam, 0)
        f, _ = fs[k % len(fs)]
        used[fam] = k + 1
        src, du = prepared(job, f)
        lead = 0.12 if fam in ("whoosh", "swoosh") else 0.0  # le souffle commence un peu avant la coupe
        st = round(max(0.0, t - lead), 3)
        nodes.append(f'    <audio id="sd-{i}" class="clip" src="{src}" data-start="{st}" data-duration="{round(min(du, total - st), 3)}" '
                     f'data-track-index="{80 + i % 8}" data-volume="{VOL.get(fam, 0.4)}"></audio>')
        last[fam] = t
    block = MARK_A + "\n" + "\n".join(nodes) + "\n    " + MARK_B + "\n"
    # juste avant la fermeture de la racine (dernier </div> avant le premier <script> du corps)
    body = h.index("<body")
    sc = h.index("<script", body)
    cut = h.rindex("</div>", body, sc)
    h = h[:cut] + block + "  " + h[cut:]
    p.write_text(h, encoding="utf-8")
    fams = {}
    for _, fam, _ in kept:
        fams[fam] = fams.get(fam, 0) + 1
    return {"sons": len(nodes), "familles": fams}


def auto(job):
    """Appelé par les monteurs après l'écriture de index.html : bruitages, puis baisse de la musique (mix.py)."""
    c = config(job)
    sf = c.get("sfx", {})
    rep = None
    if sf.get("enabled", True) and sf.get("design", True):
        try:
            rep = apply(job)
        except Exception as e:  # noqa: BLE001  (le bruitage ne doit jamais bloquer un montage)
            rep = {"erreur": str(e)[:200]}
    import mix
    p = job / "index.html"
    h, mrep = mix.auto(job, p.read_text(encoding="utf-8"))
    p.write_text(h, encoding="utf-8")
    return {"bruitages": rep, "musique": mrep}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("job")
    ap.add_argument("--off", action="store_true", help="retire les bruitages posés")
    ap.add_argument("--densite", type=float, default=0.45, help="écart minimal entre deux bruitages (s)")
    a = ap.parse_args()
    r = apply(job_dir(a.job), a.densite, a.off)
    out(ok=True, **r, suite="npx hyperframes check, puis aperçu avec le son")


if __name__ == "__main__":
    main()

"""MONTAGE D'IMAGES SANS PAROLES -> <job>/index.html : journal de chantier, ambiance de restaurant, récap d'événement,
produit sous tous les angles, voyage. Passages mesurés par footage.py, accélérés (time-lapse), étiquettes (« JOUR 12 ·
La cuisine »), avant / après en volet, titre d'ouverture, série (« Épisode 3 · Semaine 4 sur 12 »), voix off et
sous-titres facultatifs, musique, fin de marque.

  python build_footage.py <job> <slug> [--size 9:16] [--style boite] [--no-outro] [--fit cover|blur]

work/<slug>_footage.json (premier jet : footage.py plan) :
  {"title": "On rénove notre futur resto",                      (titre des premières secondes, facultatif)
   "series": {"label": "Journal de chantier", "n": 4, "of": 12, "unit": "Semaine"},   (facultatif)
   "items": [{"clip": "IMG_0412.mp4", "seg": 0, "keep": true, "dur": 2.5, "label": "JOUR 12", "caption": "La cuisine",
              "timelapse": false, "speed": 1, "word": "<mot de la voix off où ce plan commence>"}],
   "compare": [{"before": "IMG_0101.mp4", "after": "IMG_0990.mp4", "label": "Avant / Après", "dur": 3.2, "after_item": 5}]}
seg = n° du passage mesuré (0 = le meilleur) ; timelapse = accéléré du clip entier (caméra posée) ; dur = durée à l'écran.
Voix off : storyboard -> voice.py (Gemini, Fish ou --file) -> build_text.py avec le même slug : les plans changent alors sur
les débuts de phrases (ou sur "word"), la vidéo dure le temps de la voix et les sous-titres s'affichent.
Sans voix : musique (add_music.py) et durées du plan. Le son des clips n'est pas gardé (machines, vent).
"""
import argparse
import hashlib
import html
import json
import shutil
import subprocess
from pathlib import Path

from build_composition import caption_css, caption_js, caption_spans
from footage import camera_jitter, subject_x
import sound_design
from common import ROOT, block_file, brand_info, config, fail, job_dir, mount, music_beats, out, read_json, size_of, snap_beat, word_hit

esc = lambda s: html.escape(str(s), quote=True)
JITTER_MIN = 1.0  # tremblement de la caméra (footage.camera_jitter, px sur 320) au-delà duquel on stabilise ; plans posés : < 0,3


def render_clip(job, src, start, length, speed, W, H, fit, focus=None, stab=False):
    """Extrait [start, start + length] du clip, accéléré, au format W × H (recadré, ou image entière sur fond flouté).
    focus : position du sujet de gauche (0) à droite (1), mesurée par footage.subject_x ; le recadrage le garde dans
    l'image au lieu de couper au milieu. stab : stabilisation en deux passes (vidstab) d'un passage filmé à main levée."""
    key = hashlib.md5(f"{src}|{start:.2f}|{length:.2f}|{speed}|{W}x{H}|{fit}|{focus}|{stab}".encode()).hexdigest()[:10]
    d = job / "assets" / "footage"
    d.mkdir(parents=True, exist_ok=True)
    dst = d / f"{Path(src).stem[:24]}-{key}.mp4"
    mark = dst.with_suffix(".stab")  # présent si la version stabilisée a été gardée
    if dst.exists():
        return dst, mark.exists()
    inp = ["-ss", f"{start:.3f}", "-t", f"{length:.3f}", "-i", str(src)]
    used = False
    if stab:  # passe 1 : mouvements de la caméra ; passe 2 : trajet lissé (les panoramiques voulus restent), léger zoom
        raw, sta = d / f"_raw-{key}.mp4", d / f"_sta-{key}.mp4"
        trf = f"_stab-{key}.trf"  # chemin relatif (dossier de travail = d) : pas de « C: » à échapper dans le filtre
        enc = ["-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "16"]
        subprocess.run(["ffmpeg", "-v", "error", "-y", *inp, *enc, raw.name], check=True, cwd=d)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", raw.name, "-vf", f"vidstabdetect=shakiness=6:accuracy=10:result={trf}",
                        "-f", "null", "-"], check=True, cwd=d)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", raw.name, "-vf",
                        f"vidstabtransform=input={trf}:smoothing=20:optzoom=1:interpol=bicubic,unsharp=5:5:0.5:3:3:0.2", *enc, sta.name],
                       check=True, cwd=d)
        before, after = camera_jitter(raw), camera_jitter(sta)
        used = after < 0.6 * before  # gardée seulement si elle tremble nettement moins (sinon le sujet a trompé l'outil)
        inp = ["-i", str(sta if used else raw)]
    sp = f"setpts=PTS/{speed}," if speed != 1 else ""
    if fit == "blur":
        vf = (f"[0:v]{sp}split[a][b];[a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=30:3,eq=brightness=-0.08[bg];"
              f"[b]scale={W}:{H}:force_original_aspect_ratio=decrease[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2,fps=30,format=yuv420p")
        args = ["-filter_complex", vf]
    else:
        fx = 0.5 if focus is None else min(1.0, max(0.0, float(focus)))
        # x du recadrage : sujet au centre de la fenêtre, sans sortir de l'image (même chose en hauteur si la source est plus haute)
        crop = f"crop={W}:{H}:x='max(0,min(iw-{W},iw*{fx:.3f}-{W}/2))':y='(ih-{H})/2'"
        args = ["-vf", f"{sp}scale={W}:{H}:force_original_aspect_ratio=increase,{crop},fps=30,format=yuv420p"]
    subprocess.run(["ffmpeg", "-v", "error", "-y", *inp, *args, "-an",
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-movflags", "+faststart", str(dst)], check=True, cwd=d)
    if stab:
        for f in (d / f"_raw-{key}.mp4", d / f"_sta-{key}.mp4", d / f"_stab-{key}.trf"):
            f.unlink(missing_ok=True)
        if used:
            mark.write_text(f"tremblement {before} -> {after}", encoding="utf-8")
    return dst, used


def still(job, src, t, W, H):
    d = job / "assets" / "footage"
    d.mkdir(parents=True, exist_ok=True)
    dst = d / f"{Path(src).stem[:24]}-{round(t * 100)}.jpg"
    if not dst.exists():
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", str(src), "-frames:v", "1",
                        "-vf", f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}", "-q:v", "3", str(dst)], check=True)
    return dst


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("job")
    ap.add_argument("slug")
    ap.add_argument("--size")
    ap.add_argument("--style", default="boite")
    ap.add_argument("--fit", choices=["cover", "blur"])
    ap.add_argument("--no-outro", action="store_true")
    ap.add_argument("--lang", help="sous-titres traduits (translate.py apply) : nl, en…")
    ap.add_argument("--no-captions", action="store_true", help="sans sous-titres (couverture)")
    ap.add_argument("--accroche", help="accroche animée de 3 s en ouverture (papier, plan, neon… ; ou plan.hook)")
    a = ap.parse_args()
    job = job_dir(a.job)
    c = config(job)
    vis = c["visual"]
    W, H = size_of(a.size, vis)
    u = W / 1080
    pj, fj = job / "work" / f"{a.slug}_footage.json", job / "work" / "footage.json"
    if not pj.exists() or not fj.exists():
        fail("footage.py scan puis footage.py plan d'abord")
    plan, scan = read_json(pj), {x["clip"]: x for x in read_json(fj)["clips"]}
    items = [it for it in plan.get("items", []) if it.get("keep", True) and it.get("clip") in scan]
    if not items:
        fail("aucun plan gardé")
    fit = a.fit or plan.get("fit") or "cover"
    fam = vis["fontFamily"]
    acc = vis.get("accentColor", "#ffcc00")

    # voix off facultative (même slug) : la vidéo dure le temps de la voix, les plans changent sur les débuts de phrases
    mj, tj = job / "work" / f"{a.slug}_map.json", job / "work" / f"{a.slug}_text.json"
    voice = read_json(mj) if mj.exists() else None
    t = read_json(tj) if (voice and tj.exists()) else {}
    words = [w for g in t.get("captions", []) for w in g["words"]]
    comps = [x for x in plan.get("compare", []) if x.get("before") in scan and x.get("after") in scan]
    seq = []  # (kind, objet)
    for k, it in enumerate(items):
        seq.append(("clip", it))
        for cp in comps:
            if int(cp.get("after_item", len(items) - 1)) == k:
                seq.append(("compare", cp))
    if voice:
        dur = float(voice["out_duration"])
        starts = [0.0]
        anchors = [float(o["start"]) for o in t.get("overlays", []) if o.get("words")] or [w["start"] for w in words[::6]]
        for i in range(1, len(seq)):
            obj = seq[i][1]
            hit = word_hit(words, obj["word"], obj.get("occurrence", 1)) if obj.get("word") else None
            if hit:
                starts.append(max(starts[-1] + 1.2, hit["start"] - 0.1))
                continue
            target = dur * i / len(seq)
            cand = [x for x in anchors if x > starts[-1] + 1.2]
            starts.append(min(cand, key=lambda x: abs(x - target)) if cand and abs(min(cand, key=lambda x: abs(x - target)) - target) < dur / len(seq)
                          else max(starts[-1] + 1.2, target))
        ends = starts[1:] + [dur]
    else:
        lens = [float(o.get("dur", 3.2 if kind == "compare" else (3.5 if o.get("timelapse") else 2.5))) for kind, o in seq]
        starts = [round(sum(lens[:i]), 3) for i in range(len(seq))]
        ends = [round(s + l, 3) for s, l in zip(starts, lens)]
        dur = ends[-1]

    # coupes calées sur les temps de la musique (la musique part de 0, le montage après l'éventuelle accroche)
    hk0 = dict(plan.get("hook") or c.get("hook") or {})
    T0e = (float(hk0.get("dur", 3.0)) - 0.45) if (hk0.get("style") or a.accroche) else 0.0
    beats = [] if plan.get("beat_sync") is False else music_beats(job, a.slug)
    snapped = 0
    if beats and len(starts) > 1:
        tol = 0.3 if voice else 0.26
        new = [starts[0]]
        for s_ in starts[1:]:
            t_ = snap_beat(s_ + T0e, beats, tol, lo=new[-1] + T0e + 1.2) - T0e
            snapped += abs(t_ - s_) > 1e-3
            new.append(round(t_, 3))
        starts = new
        ends = starts[1:] + [ends[-1]]
    vids, labels, js, rep = [], [], [], []
    for i, ((kind, o), s0, s1) in enumerate(zip(seq, starts, ends)):
        d = round(s1 - s0, 3)
        if d < 0.3:
            continue
        if kind == "compare":
            sb, sa = scan[o["before"]], scan[o["after"]]
            tb = sum(sb["segments"][0][x] for x in ("from", "to")) / 2 if sb["segments"] else 0
            ta = sum(sa["segments"][0][x] for x in ("from", "to")) / 2 if sa["segments"] else 0
            ib = still(job, job / "inbox" / o["before"], tb, W, H)
            ia = still(job, job / "inbox" / o["after"], ta, W, H)
            cid = f"cmp{i}"
            vids.append(f'    <div class="clip cmp" id="{cid}" data-start="{round(s0, 3)}" data-duration="{d}" data-track-index="{3 + i % 2}">'
                        f'<img class="ca" src="assets/footage/{ia.name}" alt=""><div class="cbw"><img class="cb" src="assets/footage/{ib.name}" alt=""></div>'
                        f'<i class="cline"></i><span class="ctag l">AVANT</span><span class="ctag r">APRÈS</span>'
                        + (f'<div class="clab">{esc(o["label"])}</div>' if o.get("label") else "") + '</div>')
            wd = round(min(2.2, d * 0.6), 2)  # le volet découvre l'après de droite à gauche
            js.append(f'  tl.fromTo("#{cid} .cbw", {{ clipPath: "inset(0% 0% 0% 0%)" }}, {{ clipPath: "inset(0% 100% 0% 0%)", duration: {wd}, ease: "power2.inOut", immediateRender: false }}, {round(s0 + 0.5, 3)});')
            js.append(f'  tl.fromTo("#{cid} .cline", {{ x: {W} }}, {{ x: 0, duration: {wd}, ease: "power2.inOut", immediateRender: false }}, {round(s0 + 0.5, 3)});')
            rep.append({"type": "avant/après", "a": round(s0, 2), "duree": d})
            continue
        sc = scan[o["clip"]]
        src = job / "inbox" / o["clip"]
        if o.get("timelapse"):
            speed = float(o.get("speed") or max(2.0, sc["duration"] / d))
            need = min(sc["duration"], d * speed)
            st = max(0.0, (sc["duration"] - need) / 2)
        else:
            speed = float(o.get("speed", 1) or 1)
            segs = sc["segments"] or [{"from": 0, "to": sc["duration"]}]
            sg = segs[min(int(o.get("seg", 0)), len(segs) - 1)]
            need = min(sc["duration"], d * speed + 0.1)
            mid = (sg["from"] + sg["to"]) / 2
            st = min(max(0.0, mid - need / 2), max(0.0, sc["duration"] - need))
            if need < d * speed:  # clip trop court pour la durée voulue : on ralentit un peu plutôt que de figer
                speed = max(0.5, need / d)
        # main levée : stabilisé si le passage tremble (mesure du scan) ; recadrage : fenêtre posée sur le sujet mesuré
        if "stab" in o:
            stab = bool(o["stab"])
        else:
            stab = plan.get("stab", "auto") == "auto" and not o.get("timelapse") and camera_jitter(src, st, need) >= JITTER_MIN
        focus = None
        if fit != "blur" and abs(sc["width"] / max(1, sc["height"]) - W / H) > 0.15:
            if isinstance(o.get("focus"), (int, float)):
                focus = float(o["focus"])
            elif o.get("focus", plan.get("focus", "auto")) == "auto":
                focus = subject_x(src, st, need, frac=min(1.0, (W / H) / (sc['width'] / max(1, sc['height']))))
        clip, stab = render_clip(job, src, st, need, round(speed, 3), W, H, fit, focus=focus, stab=stab)
        rep_shot = {"stabilise": stab, "sujet_x": focus if focus not in (None, 0.5) else None}
        vid = f"fv{i}"
        vids.append(f'    <video id="{vid}" class="clip shotv" src="assets/footage/{clip.name}" data-start="{round(s0, 3)}" data-duration="{d}" '
                    f'data-track-index="{5 + i % 2}" muted playsinline></video>')
        js.append(f'  tl.fromTo("#{vid}", {{ scale: 1.0 }}, {{ scale: 1.07, duration: {d}, ease: "none", immediateRender: false }}, {round(s0, 3)});')
        if i:
            js.append(f'  tl.fromTo("#flash", {{ opacity: 0.35 }}, {{ opacity: 0, duration: 0.18, ease: "power2.out", immediateRender: false }}, {round(s0, 3)});')
        if o.get("label") or o.get("caption"):
            lid = f"lb{i}"
            labels.append(f'    <div class="clip lab" id="{lid}" data-start="{round(s0, 3)}" data-duration="{d}" data-track-index="{20 + i % 2}">'
                          + (f'<b>{esc(o["label"])}</b>' if o.get("label") else "") + (f'<span>{esc(o["caption"])}</span>' if o.get("caption") else "")
                          + ('<i class="tl">ACCÉLÉRÉ ×' + f'{speed:.0f}</i>' if o.get("timelapse") else "") + '</div>')
            lt = s0 + 0.1 + (min(3.2, d) - 0.2 if i == 0 and plan.get("title") else 0)  # pas sous le titre d'ouverture
            js.append(f'  tl.set("#{lid} > *", {{ opacity: 0 }}, {round(s0, 3)});')
            js.append(f'  tl.fromTo("#{lid} > *", {{ opacity: 0, x: -24 }}, {{ opacity: 1, x: 0, duration: 0.35, stagger: 0.08, ease: "power3.out", immediateRender: false }}, {round(lt, 3)});')
        rep.append({"type": "accéléré" if o.get("timelapse") else "plan", "clip": o["clip"], "a": round(s0, 2), "duree": d, "vitesse": round(speed, 2), **{k: v for k, v in rep_shot.items() if v}})

    # titre d'ouverture et série
    over = []
    if plan.get("title"):
        tdur = round(min(3.2, ends[0] if len(ends) else 3.0), 3)
        over.append(f'    <div class="clip ttl" id="ttl" data-start="0" data-duration="{tdur}" data-track-index="24"><h1>{esc(plan["title"])}</h1></div>')
        js.append('  tl.fromTo("#ttl h1", { opacity: 0, y: 40 }, { opacity: 1, y: 0, duration: 0.5, ease: "power3.out", immediateRender: false }, 0.1);')
        js.append(f'  tl.to("#ttl", {{ opacity: 0, duration: 0.25 }}, {round(tdur - 0.25, 3)});')
    se = plan.get("series") or {}
    if se:
        top = f'{se.get("unit", "Épisode")} {se.get("n", "")}' + (f' sur {se["of"]}' if se.get("of") else "")
        over.append(f'    <div class="clip ser" id="ser" data-start="0" data-duration="{round(dur, 3)}" data-track-index="25">'
                    f'<span class="sl">{esc(se.get("label", ""))}</span><span class="sn">{esc(top)}</span>'
                    + (f'<i class="sb"><b style="width:{round(100 * float(se["n"]) / float(se["of"]))}%"></b></i>' if se.get("of") and se.get("n") else "")
                    + '</div>')
        js.append('  tl.fromTo("#ser > *", { opacity: 0, y: -14 }, { opacity: 1, y: 0, duration: 0.4, stagger: 0.08, ease: "power2.out", immediateRender: false }, 0.2);')

    # sous-titres de la voix off
    caps, capjs = [], []
    if voice and words and not a.no_captions:
        tl_ = t
        if a.lang and (job / "work" / f"{a.slug}_text_{a.lang}.json").exists():
            tl_ = read_json(job / "work" / f"{a.slug}_text_{a.lang}.json")
        groups = tl_.get("captions", [])
        for gi, g in enumerate(groups):
            stc = round(max(0.05, g["words"][0]["start"] - 0.05), 3)
            nxt = groups[gi + 1]["words"][0]["start"] - 0.05 if gi + 1 < len(groups) else dur
            en = round(min(dur, max(g["end"] + 0.25, stc + 0.4), nxt), 3)
            if en - stc <= 0.1:
                continue
            spans, _, _ = caption_spans(g["words"], a.style, False, stc, -99)
            caps.append(f'    <div class="clip cap" id="cap-{g["id"]}" data-start="{stc}" data-duration="{round(en - stc, 3)}" data-track-index="30">'
                        f'<div class="in">{spans}</div></div>')
            capjs.append(f'  cap("cap-{g["id"]}", {stc}, {en}, {json.dumps([[round(max(stc, w["start"]), 3), round(w["end"], 3)] for w in g["words"]])});')

    audio = []
    if voice:
        audio.append(f'    <audio id="voice" class="clip" src="assets/{esc(Path(voice["cut"]).name)}" data-start="0" data-duration="{round(dur, 3)}" '
                     f'data-track-index="8" data-volume="1"></audio>')
    mu = job / "work" / f"{a.slug}_music.json"
    if mu.exists():
        audio.append(f'    <audio id="music" class="clip" src="{read_json(mu)["file"]}" data-start="0" data-duration="{round(dur, 3)}" '
                     f'data-track-index="9" data-volume="{0.35 if voice else 1}"></audio>')

    # accroche animée par style en ouverture : tout le montage est décalé, il démarre sous son volet de sortie
    hk = dict(plan.get("hook") or c.get("hook") or {})
    if a.accroche:
        hk["style"] = a.accroche
    hook_html, T0 = "", 0.0
    if hk.get("style"):
        hname = f"accroche-{hk['style']}"
        block_file(job, hname)
        hdur = float(hk.get("dur", 3.0))
        hv = {"text": hk.get("text") or plan.get("title", ""), "sub": hk.get("sub", ""), "accent": hk.get("accent") or acc, "font": fam}
        hv.update({k: hk[k] for k in ("bg", "ink") if hk.get(k)})
        if hk.get("art") and (job / hk["art"]).exists():  # dessin du sujet (SVG) : references/accroches-dessin.md
            hv["art"] = (job / hk["art"]).read_text(encoding="utf-8")
        hook_html = mount(hname, "hook-anim", 0, hdur, W, H, 26, hv, z=200)
        T0 = round(hdur - 0.45, 3)
        if hk.get("text"):  # le titre est dans l'accroche : pas deux fois
            over = [o_ for o_ in over if 'id="ttl"' not in o_]
            js = [j for j in js if '"#ttl' not in j]
        import re as _re
        sh = lambda n: _re.sub(r'data-start="([\d.]+)"', lambda mm: f'data-start="{round(float(mm.group(1)) + T0, 3)}"', n)
        vids, labels, over, caps, audio = ([sh(n) for n in grp] for grp in (vids, labels, over, caps, audio))
    total, outro = round(dur + T0, 3), ""
    br = c.get("branding", {})
    if br.get("outro") and not a.no_outro:
        block_file(job, br["outro"])
        od = float(br.get("outroDuration", 3.4))
        brand = brand_info(job)
        logo = ""
        if vis.get("logo"):
            lp = ROOT / vis["logo"]
            (job / "assets" / "img").mkdir(parents=True, exist_ok=True)
            shutil.copy2(lp, job / "assets" / "img" / lp.name)
            logo = f"assets/img/{lp.name}"
        outro = mount(br["outro"], "brand-outro", dur + T0, od, W, H, 22,
                      {"logo": logo, "bg": vis.get("bgColor", "#f6f4f0"), "ink": vis.get("inkColor", "#1a1a1a"), "accent": acc,
                       "font": fam, "blend": vis.get("logoBlend", "normal"), "tagline": brand.get("tagline", ""),
                       "info": (brand.get("contact") or {}).get("site", "")}, z=200)
        total = round(dur + T0 + od, 3)

    content_js = "\n".join([caption_js(a.style)] + capjs + js)
    if T0:  # le contenu dans sa propre timeline, décalée de la durée de l'accroche
        content_js = "  const ct = gsap.timeline();\n" + content_js.replace("tl.", "ct.") + f"\n  tl.add(ct, {T0});"
    faces = []
    for f in vis.get("fonts", []):
        ff = ROOT / f["file"] if not Path(f["file"]).is_absolute() else Path(f["file"])
        (job / "assets" / "fonts").mkdir(parents=True, exist_ok=True)
        shutil.copy2(ff, job / "assets" / "fonts" / ff.name)
        faces.append(f"@font-face {{ font-family: '{fam}'; src: url('assets/fonts/{ff.name}'); font-weight: {f.get('weight', 400)}; }}")
    import panel as pn
    faces.append(pn.fonts(job))
    cap_size = round((84 if a.style not in ("minimal", "mono") else 56) * u)
    G = lambda x: round(x * u)
    on_acc = "#111" if pn._lum(acc) > 150 else "#fff"
    doc = f"""<!doctype html>
<html lang="fr">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width={W}, height={H}" />
<title>{esc(a.slug)}</title>
<script src="https://cdn.jsdelivr.net/npm/gsap@3.15.0/dist/gsap.min.js"></script>
<style>
  {' '.join(faces)}
  html, body {{ margin: 0; padding: 0; width: {W}px; height: {H}px; overflow: hidden; background: #000; }}
  #root {{ position: relative; width: {W}px; height: {H}px; overflow: hidden; font-family: '{fam}', 'Inter', sans-serif; color: #fff; background: #000; }}
  .shot {{ position: absolute; inset: 0; }}
  .shotv {{ position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; z-index: 2; }}
  #flash {{ position: absolute; inset: 0; background: #fff; opacity: 0; z-index: 15; pointer-events: none; }}
  .shade {{ position: absolute; left: 0; right: 0; top: 0; height: 30%; background: linear-gradient(rgba(0,0,0,.45), transparent); z-index: 10; }}
  .shadeb {{ position: absolute; left: 0; right: 0; bottom: 0; height: 40%; background: linear-gradient(transparent, rgba(0,0,0,.55)); z-index: 10; }}
  .lab {{ position: absolute; left: {G(56)}px; top: {G(210)}px; z-index: 20; display: flex; flex-direction: column; align-items: flex-start; gap: {G(12)}px; }}
  .lab b {{ font: 600 {G(34)}px 'IBM Plex Mono', monospace; letter-spacing: .08em; padding: {G(8)}px {G(18)}px; background: {acc}; color: {on_acc}; border-radius: {G(8)}px; }}
  .lab span {{ font-size: {G(64)}px; font-weight: 800; line-height: 1.05; text-shadow: 0 {G(4)}px {G(18)}px rgba(0,0,0,.6); max-width: {G(900)}px; }}
  .lab .tl {{ font: 500 {G(24)}px 'IBM Plex Mono', monospace; font-style: normal; letter-spacing: .1em; padding: {G(6)}px {G(14)}px; border: 2px solid #fff;
             border-radius: 99px; }}
  .ttl {{ position: absolute; inset: 0; z-index: 24; display: flex; align-items: center; justify-content: center; background: rgba(0,0,0,.25); }}
  .ttl h1 {{ margin: 0 {G(70)}px; font-size: {G(110)}px; font-weight: 900; line-height: 1.02; text-align: center; letter-spacing: -.02em;
            text-shadow: 0 {G(6)}px {G(30)}px rgba(0,0,0,.6); text-wrap: balance; }}
  .ser {{ position: absolute; left: {G(56)}px; right: {G(56)}px; top: {G(70)}px; z-index: 25; display: flex; flex-wrap: wrap; align-items: center; gap: {G(16)}px; }}
  .ser .sl {{ font: 600 {G(28)}px 'IBM Plex Mono', monospace; letter-spacing: .12em; text-transform: uppercase; opacity: .9; }}
  .ser .sn {{ font-weight: 800; font-size: {G(30)}px; padding: {G(4)}px {G(14)}px; border-radius: {G(8)}px; background: rgba(0,0,0,.45); }}
  .ser .sb {{ flex-basis: 100%; height: {G(8)}px; border-radius: 99px; background: rgba(255,255,255,.3); overflow: hidden; }}
  .ser .sb b {{ display: block; height: 100%; background: {acc}; }}
  .cmp {{ position: absolute; inset: 0; z-index: 4; overflow: hidden; }}
  .cmp img {{ position: absolute; left: 0; top: 0; width: {W}px; height: {H}px; object-fit: cover; }}
  .cbw {{ position: absolute; left: 0; top: 0; bottom: 0; width: 100%; overflow: hidden; z-index: 2; }}
  .cline {{ position: absolute; left: 0; top: 0; bottom: 0; width: {G(6)}px; margin-left: -{G(3)}px; background: #fff; z-index: 3; box-shadow: 0 0 {G(20)}px rgba(0,0,0,.5); }}
  .ctag {{ position: absolute; top: {G(330)}px; z-index: 4; font: 700 {G(30)}px 'IBM Plex Mono', monospace; letter-spacing: .1em; padding: {G(8)}px {G(16)}px;
          border-radius: {G(8)}px; background: rgba(0,0,0,.6); }}
  .ctag.l {{ left: {G(40)}px; }}
  .ctag.r {{ right: {G(40)}px; background: {acc}; color: {on_acc}; }}
  .clab {{ position: absolute; left: 0; right: 0; top: {round(H * 0.5)}px; z-index: 4; text-align: center; font-size: {G(70)}px; font-weight: 900;
          text-shadow: 0 {G(6)}px {G(24)}px rgba(0,0,0,.7); }}
  .cap {{ position: absolute; left: 0; right: 0; top: {round(H * 0.72)}px; text-align: center; z-index: 40; }}
  .cap .in {{ display: inline-block; max-width: 86%; font-weight: 800; font-size: {cap_size}px; line-height: 1.12; color: #fff;
             text-shadow: 0 {G(4)}px {G(16)}px rgba(0,0,0,.7); }}
  .cap .w {{ display: inline-block; margin: 0 0.07em; {"opacity: 0;" if a.style in ("pop", "duo", "mono") else ""} }}
{caption_css(a.style, acc)}
</style>
</head>
<body>
  <div id="root" data-composition-id="footage" data-start="0" data-width="{W}" data-height="{H}" data-duration="{total}">
{chr(10).join(vids)}
    <div class="shade"></div><div class="shadeb"></div><div id="flash"></div>
{chr(10).join(labels)}
{chr(10).join(over)}
{chr(10).join(caps)}
{chr(10).join(audio)}
{outro}
{hook_html}
  </div>
<script>
  window.__timelines = window.__timelines || {{}};
  const tl = gsap.timeline({{ paused: true }});
  const ACCENT = {json.dumps(acc)}, INK = "#ffffff", BOXINK = {json.dumps(on_acc)};
{content_js}
  window.__timelines["footage"] = tl;
</script>
</body>
</html>
"""
    (job / "index.html").write_text(doc, encoding="utf-8")
    if not getattr(a, "no_sfx", False):  # bruitages sur ce qui apparaît (sound_design.py ; "sfx": {"design": false} pour s'en passer)
        sound_design.auto(job)
    out(ok=True, format=f"{W}x{H}", duree=total, plans=rep, voix=bool(voice), sous_titres=len(caps),
        coupes_sur_la_musique=f"{snapped}/{max(0, len(starts) - 1)}" if beats else "pas de musique analysée",
        suite="npx hyperframes check, puis snapshot pendant quelques plans")


if __name__ == "__main__":
    main()

"""DÉRUSH -> assets/<slug>_cut.mp4 + work/<slug>_map.json   (repris de reel-cut, adapté)

Seul endroit où l'on ré-encode la vidéo. Tout l'habillage suit dans HyperFrames : le cut est un INTERMÉDIAIRE,
encodé presque sans perte (crf 12, crf 10 si la source est agrandie ; slow, tune film, une image clé par seconde).
Taille : celle que la composition affichera. « cover » (recadré) : un rush 4K est réduit (lanczos précis), une petite
source est agrandie dès qu'elle est plus petite que le format (lanczos + netteté, « upscale » dans map.json) ;
« fill » (image entière sur fond flouté) : réduite si besoin, jamais agrandie ; source plus large que le format
(fond flouté ou suivi du visage, reframe.py) : réduite à la hauteur du format, jamais agrandie.
Couleurs ramenées en BT.709 limité (une source SD sans balise est lue en BT.601) et balisées ; rush sans son : piste
muette. Voix : chaîne de voice.py (voice_chain : coupe-bas, débruitage doux si --denoise, EQ, de-esser, compresseur)
puis loudnorm en deux passes linéaires sur derush.voiceLufs (render_voice, durée pile) ; son du cut en AAC 320k.
Rushs de téléphone : cadence variable (VFR) remise à cadence fixe par le filtre fps en fin de chaîne (sinon l'image
glisse jusqu'à ~56 ms derrière le son après les coupes) ; vidéo HDR (HLG / PQ / Dolby Vision, iPhone) ramenée en SDR
BT.709 (zscale + tonemap hable), sans quoi elle sort délavée.
Clignements : une coupe qui tomberait sur des yeux fermés glisse de quelques images, sans entrer dans un mot (blink.py,
MediaPipe facultatif ; derush.blinks: false pour couper).

  python build_cut.py <job> <slug> [--crf 12] [--denoise]
"""
import argparse
import shutil
import tempfile
from pathlib import Path

from common import config, fail, ffmpeg_has, hdr_to_sdr, job_dir, out, probe, read_json, round_fps, sh, write_json


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("job")
    ap.add_argument("slug")
    ap.add_argument("--crf", type=int, help="défaut 12 (10 si la source est agrandie) : intermédiaire, presque sans perte")
    ap.add_argument("--preset", default="slow")
    ap.add_argument("--denoise", action="store_true", help="afftdn : rushs au téléphone, souffle")
    ap.add_argument("--no-enhance", action="store_true", help="sans stabilisation / netteté automatiques (enhance.py)")
    a = ap.parse_args()
    job = job_dir(a.job)
    c = config(job)
    f, lufs = c["derush"]["fade"], c["derush"]["voiceLufs"]
    W, H = c["visual"]["width"], c["visual"]["height"]

    pj = job / "work" / f"{a.slug}_plan.json"
    if not pj.exists():
        fail(f"{pj} absent")
    plan = read_json(pj)
    src = Path(plan["source"])
    keep = [i for i in plan["islands"] if i.get("keep")]
    if not keep:
        fail("aucun îlot gardé")

    holes = sorted((float(x["cut_start"]), float(x["cut_end"])) for x in plan.get("fillers", []) if x.get("remove"))
    segs = []
    for i in keep:
        pieces = [[float(i["cut_start"]), float(i["cut_end"])]]
        for hs, he in holes:  # hésitations, répétitions, blancs : l'îlot est coupé en morceaux
            nxt = []
            for s, e in pieces:
                if he <= s or hs >= e:
                    nxt.append([s, e])
                else:
                    nxt += [p for p in ([s, hs], [he, e]) if p[1] - p[0] > 0.05]
            pieces = nxt
        for s, e in pieces:
            if segs and abs(s - segs[-1][1]) < 1e-3:
                segs[-1][1] = e
            else:
                segs.append([s, e])
    segs = [(s, e) for s, e in segs if e - s > 0.05]
    n_fill = sum(1 for x in plan.get("fillers", []) if x.get("remove"))
    blinks = None
    wj = job / "work" / f"{a.slug}_words.json"
    if c["derush"].get("blinks", True) is not False and wj.exists():
        import blink
        if blink.available():
            try:  # aucune coupe sur des yeux fermés ; ne bloque jamais un dérush
                segs, blinks = blink.adjust(src, segs, read_json(wj)["words"])
            except Exception as e:  # noqa: BLE001
                blinks = {"erreur": str(e)[:200]}
        else:
            blinks = "non vérifiés (pip install --no-deps mediapipe absl-py)"

    info = probe(src)
    sw, sh_ = info["width"], info["height"]
    ratio = (sw / sh_) / (W / H)
    fit = c["visual"].get("fit", "auto")
    # même règle que build_composition : « fill » = image entière sur fond flouté (object-fit: contain)
    fill = fit == "fill" or (fit == "auto" and ratio < 0.75)
    wide = not fill and fit in ("auto", "track") and ratio > 1.33  # fond flouté OU fenêtre qui suit le visage (reframe.py)
    k = min(W / sw, H / sh_) if fill else max(W / sw, H / sh_)  # échelle à laquelle la composition affichera la source
    if wide:
        k = min(k, 1.0)  # réduite à la hauteur du format (le suivi recadre dedans), jamais agrandie (peut finir en fond flouté)
    up = k > 1.0 and not fill and not wide
    flags = "lanczos+accurate_rnd+full_chroma_int"
    scale, vpost, notes = "", [], []
    if k < 1:
        scale = f",scale=-2:{int(round(sh_ * k / 2) * 2)}:flags={flags}"
    elif up:  # petite source (WhatsApp, 480p) : agrandie ici en lanczos + netteté douce, sinon le navigateur l'étire en flou
        scale = f",scale=-2:{int(round(sh_ * k / 2) * 2)}:flags={flags},unsharp=5:5:{0.7 if k > 1.3 else 0.4}:5:5:0"
        notes.append(f"source {sw}×{sh_} agrandie ×{k:.2f} (lanczos + netteté) ; zooms de caméra coupés")
    col = info.get("color") or {}
    if info.get("hdr"):  # après la mise à l'échelle : le tone mapping en flottant coûte cher en 4K
        if ffmpeg_has("zscale"):
            vpost.append(hdr_to_sdr(info))
            notes.append(f"source {info.get('hdr_format')} ramenée en SDR BT.709 (" + ("couleurs converties, sans tone-mapping" if info.get('hdr_format') == 'HLG' else 'tonemap hable') + ")")
        else:
            notes.append(f"ATTENTION : source {info.get('hdr_format')} mais ce ffmpeg n'a pas le filtre zscale : "
                         "couleurs délavées. Installe un ffmpeg complet (build « full » de gyan.dev) puis relance.")
    else:  # matrice et plage de la source -> BT.709 limité (un rush SD sans balise est en BT.601)
        mtx = {"bt709": "bt709", "bt470bg": "bt470", "smpte170m": "smpte170m", "bt2020nc": "bt2020", "bt2020c": "bt2020",
               "fcc": "fcc", "smpte240m": "smpte240m"}.get(col.get("space") or "", "bt601" if sh_ < 720 else "bt709")
        rng = {"pc": "pc", "jpeg": "pc", "tv": "tv", "mpeg": "tv"}.get(col.get("range") or "", "tv")
        vpost.append(f"scale=in_color_matrix={mtx}:in_range={rng}:out_color_matrix=bt709:out_range=tv:flags={flags}")
        if mtx != "bt709" or rng != "tv":
            notes.append(f"couleurs {mtx}{' pleine plage' if rng == 'pc' else ''} ramenées en BT.709 limité")
    venc = ["-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv"]
    if info.get("vfr"):  # filtre fps en dernier, pas seulement -r : chaque image retrouve sa place (d'après ffmpeg-skill, MIT)
        rate = round_fps(info.get("fps"), info.get("fps_nominal"))
        vpost.append(f"fps={rate}")
        venc += ["-r", rate]
        notes.append(f"cadence variable ({info.get('fps')} i/s en moyenne) remise à {rate} i/s fixes")
    crf = a.crf if a.crf is not None else (10 if up and k > 1.1 else 12)  # intermédiaire : HyperFrames ré-encode derrière

    has_a = info["has_audio"]
    vparts, aparts = [], []
    for n, (s, e) in enumerate(segs):
        d = e - s
        af = f"atrim=start={s}:end={e},asetpts=PTS-STARTPTS"
        if d > 2 * f + 0.05:
            af += f",afade=t=in:st=0:d={f},afade=t=out:st={d - f:.3f}:d={f}"
        vparts.append(f"[0:v]trim=start={s}:end={e},setpts=PTS-STARTPTS{scale}[v{n}]")
        aparts.append(f"[0:a]{af}[a{n}]")
    n_ = len(segs)
    total = round(sum(e - s for s, e in segs), 3)
    vtail = f";[vc]{','.join(vpost)}[v]" if vpost else ";[vc]null[v]"
    fc = ";".join(vparts) + ";" + "".join(f"[v{i}]" for i in range(n_)) + f"concat=n={n_}:v=1:a=0[vc]{vtail}"

    dst = job / "assets" / f"{a.slug}_cut.mp4"
    dst.parent.mkdir(exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="vm-cut-"))
    try:
        if has_a:  # voix : chaîne de voice.py (coupe-bas, EQ, de-esser, compresseur) + loudnorm 2 passes linéaire, durée pile
            from voice import render_voice, voice_chain
            wav = tmp / "voix.wav"
            render_voice(["-i", str(src)], ";".join(aparts) + ";" + "".join(f"[a{i}]" for i in range(n_))
                         + f"concat=n={n_}:v=0:a=1,{voice_chain(a.denoise)}[pre]", wav, lufs, total)
            ain = ["-i", str(wav)]
        else:  # rush sans son : piste muette
            ain = ["-f", "lavfi", "-t", f"{total:.3f}", "-i", "anullsrc=r=48000:cl=stereo"]
            notes.append("rush sans son : piste muette ajoutée")
        script = tmp / "graph.txt"
        script.write_text(fc, encoding="utf-8")
        sh(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), *ain, "-filter_complex_script", str(script),
            "-map", "[v]", "-map", "1:a", "-c:v", "libx264", "-crf", str(crf), "-preset", a.preset, "-tune", "film",
            "-g", "30", "-pix_fmt", "yuv420p", *venc, "-c:a", "aac", "-b:a", "320k", "-ar", "48000", "-ac", "2",
            "-movflags", "+faststart", str(dst)], "ffmpeg (dérush)")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    mapping, cur = [], 0.0
    for s, e in segs:
        mapping.append({"src_start": round(s, 3), "src_end": round(e, 3),
                        "out_start": round(cur, 3), "out_end": round(cur + (e - s), 3)})
        cur += e - s
    write_json(job / "work" / f"{a.slug}_map.json",
               {"slug": a.slug, "cut": str(dst), "segments": mapping, "out_duration": round(cur, 3),
                **({"upscale": round(k, 2)} if up else {})})
    controle = None
    if (info.get("hdr") or info.get("vfr") or info.get("rotation") or up) and mapping:  # rush de téléphone ou agrandi : original | importé
        sg = mapping[0]
        dt = min(1.0, (sg["src_end"] - sg["src_start"]) / 2)
        ctl = job / "work" / f"{a.slug}_controle.jpg"
        import subprocess  # une image de contrôle ne doit jamais bloquer le dérush (pas de sh(), qui échoue en JSON)
        r_ = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", str(sg["src_start"] + dt), "-i", str(src), "-ss",
                             str(sg["out_start"] + dt), "-i", str(dst), "-filter_complex",
                             "[0:v]scale=-2:960,setsar=1[l];[1:v]scale=-2:960,setsar=1[r];[l][r]hstack", "-frames:v", "1", str(ctl)],
                            capture_output=True)
        controle = str(ctl) if r_.returncode == 0 and ctl.exists() else None
    enh = None
    if not a.no_enhance and config(job).get("video_enhance", True) is not False:
        try:  # passages filmés en marchant stabilisés, passages flous renforcés ; temps et son inchangés
            from enhance import enhance
            enh = enhance(job, a.slug)
        except Exception as e:  # noqa: BLE001 (la retouche ne doit jamais bloquer un dérush)
            enh = {"erreur": str(e)[:200]}
    out(ok=True, segments=len(segs), avant=round(plan["duration"], 1), apres=round(cur, 1), retouche=enh, clignements=blinks, controle=controle,
        gain_pct=round(100 * (1 - cur / plan["duration"])), jetes=len(plan["islands"]) - len(keep),
        fillers_retires=n_fill, cut=str(dst), source=notes or None)


if __name__ == "__main__":
    main()

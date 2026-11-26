"""MUSIQUE DE FOND -> assets/<slug>_music.wav + work/<slug>_music.json (lu par build_composition.py)

Source, au choix :
  --mood upbeat|chill|inspiring|energetic|acoustic|cinematic|funky|ambient   banque sounds/music (CC0 / CC-BY)
  --id <id du catalogue>                                                     une piste précise de la banque
  --file <fichier audio>                                                     musique fournie par le client
  --url <lien YouTube / SoundCloud / Bandcamp…>                              téléchargée avec yt-dlp

  python add_music.py <job> <slug> (--mood X | --id I | --file F | --url U) [--start S] [--level -20] [--no-duck]

Piste de la banque : tirée d'après le nom du job (relancer le même job redonne la même), en évitant les 2 dernières
pistes posées sur d'autres vidéos (sounds/music/recent.json). Départ automatique au premier passage énergique de la
piste, calé sur une attaque (--start pour l'imposer). Piste trop courte : son corps est bouclé en fondu enchaîné
(1 s, pas de coupe sèche). Fondu d'entrée 0,5 s et de sortie 1,5 s ; niveau MESURÉ sur l'extrait (ebur128) puis gain
fixe + limiteur (-3 dBFS) vers --level LUFS (-20 par défaut) ; puis baissé sous la voix (sidechain sur l'audio du
dérush). La voix reste maîtresse ; le master final se fait avec finalize.py.

⚠ Un lien YouTube / SoundCloud n'est PAS une licence : à n'utiliser que si le client a les droits (sa musique,
une licence achetée, un morceau libre). La source est notée dans les crédits, avec la mention « droits à vérifier ».
"""
import argparse
import hashlib
import math
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import numpy as np

from common import SOUNDS, config, fail, job_dir, out, probe, read_json, sh, write_json

RECENT = SOUNDS / "music" / "recent.json"
XF = 1.0  # fondu enchaîné de la boucle (s)


def from_url(url, dst_dir):
    dst_dir.mkdir(parents=True, exist_ok=True)
    if not shutil.which("yt-dlp"):
        fail("yt-dlp absent (winget install yt-dlp.yt-dlp)")
    r = subprocess.run(["yt-dlp", "--no-playlist", "-x", "--audio-format", "mp3", "--audio-quality", "0",
                        "--no-progress", "--print", "after_move:filepath", "--print", "%(title)s|||%(uploader)s|||%(webpage_url)s",
                        "-o", str(dst_dir / "%(title).80s [%(id)s].%(ext)s"), url],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        fail("yt-dlp a échoué", stderr=r.stderr[-800:])
    lines = [x for x in r.stdout.strip().splitlines() if x.strip()]
    meta = next((x for x in lines if "|||" in x), "||||||")
    title, uploader, page = (meta.split("|||") + ["", "", ""])[:3]
    path = Path(next(x for x in reversed(lines) if "|||" not in x))
    return path, {"title": title, "creator": uploader, "source": page or url, "license": "inconnue",
                  "attribution": f'"{title}" par {uploader} ({page or url}) - droits à vérifier par le client'}


def from_bank(mood=None, sid=None, min_len=0, job_name=""):
    """Piste de la banque : --id, sinon tirée d'après le nom du job sans reprendre les 2 dernières posées ailleurs."""
    cat = SOUNDS / "music" / "catalog.json"
    if not cat.exists():
        fail("banque musique vide : lance bank.py music")
    items = read_json(cat)["items"]
    if sid:
        items = [i for i in items if i["id"] == sid]
    elif mood:
        items = [i for i in items if i["category"] == mood]
    if not items:
        fail(f"aucune piste pour {sid or mood}", ambiances=sorted({i['category'] for i in read_json(cat)['items']}))
    longs = [i for i in items if i.get("duration_s", 0) >= min_len] or items
    recent = read_json(RECENT).get("recent", []) if RECENT.exists() else []
    job_name = hashlib.sha1(job_name.encode()).hexdigest()[:10]  # empreinte : aucun nom de client dans la banque
    mine = next((r["id"] for r in reversed(recent) if r.get("job") == job_name), None)
    if sid:
        i = longs[0]
    elif mine and any(x["id"] == mine for x in longs):  # même job relancé : même piste
        i = next(x for x in longs if x["id"] == mine)
    else:
        last2 = [r["id"] for r in recent if r.get("job") != job_name][-2:]
        pool = [x for x in longs if x["id"] not in last2] or longs
        i = pool[int(hashlib.sha1(job_name.encode()).hexdigest(), 16) % len(pool)]
    recent = [r for r in recent if r.get("job") != job_name] + [{"id": i["id"], "job": job_name}]
    write_json(RECENT, {"recent": recent[-20:]})
    return SOUNDS / i["file"], i


def mono(path, sr=11025):
    p = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-vn", "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"],
                       capture_output=True)
    return np.frombuffer(p.stdout, dtype=np.float32)


def shape(path, sr=11025):
    """(départ du premier passage énergique, fin du corps de la piste), en s."""
    a = mono(path, sr)
    if len(a) < sr * 4:
        return 0.0, len(a) / sr
    hop = sr // 4  # énergie sur 1 s, pas de 0,25 s
    n = (len(a) - sr) // hop + 1
    db = np.array([10 * np.log10(np.mean(a[k * hop:k * hop + sr] ** 2) + 1e-12) for k in range(n)])
    loud = np.percentile(db, 80)
    first = int(np.argmax(db >= loud - 2)) * 0.25
    alive = np.nonzero(db > loud - 6)[0]  # fin du corps : avant le fondu de fin de la piste
    body_end = min(len(a) / sr, (alive[-1] * 0.25 + 1.0) if len(alive) else len(a) / sr)
    first = min(first, body_end * 0.5)
    # calé sur une attaque : plus forte montée d'énergie (trames de 20 ms) à ±0,5 s
    fr = sr // 50
    lo, hi = max(0, int((first - 0.5) * sr)), min(len(a), int((first + 0.5) * sr))
    seg = a[lo:hi]
    m = len(seg) // fr
    if m > 2:
        e = np.sqrt(np.mean(seg[:m * fr].reshape(m, fr) ** 2, axis=1))
        first = (lo + (int(np.argmax(np.diff(e))) + 1) * fr) / sr
    return round(max(0.0, first - 0.05), 3), round(body_end, 3)


def source_graph(start, dur, body_end):
    """[0:a] -> [raw] : dur s depuis start ; corps bouclé en fondu enchaîné si la piste est trop courte."""
    L = body_end - start
    if L >= dur:
        return f"[0:a]atrim=start={start:.3f}:end={start + dur:.3f},asetpts=PTS-STARTPTS[raw]", False
    xf = min(XF, L / 3)
    k = 1 + math.ceil((dur - L) / (L - xf))
    parts = [f"[0:a]asplit={k}" + "".join(f"[a{i}]" for i in range(k))]
    parts += [f"[a{i}]atrim=start={start:.3f}:end={body_end:.3f},asetpts=PTS-STARTPTS[p{i}]" for i in range(k)]
    cur = "p0"
    for i in range(1, k):
        parts.append(f"[{cur}][p{i}]acrossfade=d={xf:.3f}:c1=qsin:c2=qsin[x{i}]")
        cur = f"x{i}"
    parts.append(f"[{cur}]atrim=end={dur:.3f},asetpts=PTS-STARTPTS[raw]")
    return ";".join(parts), True


def integrated(path):
    """Niveau intégré (LUFS) mesuré par ebur128."""
    log = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af", "ebur128", "-f", "null", "-"],
                         capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
    i = re.findall(r"I:\s+(-?[\d.]+) LUFS", log)
    return float(i[-1]) if i else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("job")
    ap.add_argument("slug")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--mood")
    g.add_argument("--id")
    g.add_argument("--file")
    g.add_argument("--url")
    ap.add_argument("--start", type=float, help="où commencer dans la musique (s) ; par défaut : premier passage énergique")
    ap.add_argument("--level", type=float, default=-20.0, help="niveau du lit en LUFS avant ducking")
    ap.add_argument("--no-duck", action="store_true")
    a = ap.parse_args()
    job = job_dir(a.job)
    config(job)
    mj = job / "work" / f"{a.slug}_map.json"
    fpj = job / "work" / f"{a.slug}_footage.json"
    if mj.exists():
        m = read_json(mj)
        dur, cut = float(m["out_duration"]), Path(m["cut"])
    elif fpj.exists():  # montage sans paroles et sans voix off : durée tirée du plan, pas de voix à laisser passer
        fp = read_json(fpj)
        dur = sum(float(i.get("dur", 3.5 if i.get("timelapse") else 2.5)) for i in fp.get("items", []) if i.get("keep", True))
        dur += sum(float(cp.get("dur", 3.2)) for cp in fp.get("compare", []))
        dur += float((fp.get("hook") or {}).get("dur", 3.0)) - 0.45 if (fp.get("hook") or {}).get("style") else 0
        cut, a.no_duck = None, True
    else:
        fail(f"{mj} absent : dérushe d'abord (ou footage.py plan pour un montage sans paroles)")

    if a.url:
        src, meta = from_url(a.url, job / "inbox" / "music")
    elif a.file:
        src = Path(a.file).resolve()
        if not src.exists():
            fail(f"introuvable : {src}")
        meta = {"title": src.stem, "creator": "fourni par le client", "license": "fourni par le client",
                "source": str(src), "attribution": f"{src.name} - fourni par le client"}
    else:
        src, meta = from_bank(a.mood, a.id, dur + (a.start or 0), job.name)

    first, body_end = shape(src)
    # départ au premier passage énergique, s'il reste assez de corps derrière (sinon depuis le début)
    start = a.start if a.start is not None else (first if body_end - first >= min(dur, 20) else 0.0)
    graph, loop = source_graph(start, dur, max(body_end, start + 3.0))
    fade_out = min(1.5, dur / 4)
    dst = job / "assets" / f"{a.slug}_music.wav"
    bed = job / "assets" / f"{a.slug}_music_bed.wav"  # lit sans baisse : mix.py en tire la courbe précise
    with tempfile.TemporaryDirectory() as tmp:
        raw = Path(tmp) / "raw.wav"
        sh(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-filter_complex",
            graph + f";[raw]afade=t=in:st=0:d=0.5,afade=t=out:st={dur - fade_out:.3f}:d={fade_out:.3f},"
            "aresample=48000,aformat=channel_layouts=stereo[out]", "-map", "[out]", "-c:a", "pcm_f32le", str(raw)],
           "ffmpeg (extrait musical)")
        lufs_in = integrated(raw)
        gain = (a.level - lufs_in) if lufs_in is not None and lufs_in > -70 else 0.0
        sh(["ffmpeg", "-y", "-loglevel", "error", "-i", str(raw), "-af",
            f"volume={gain:.2f}dB,alimiter=limit=0.708:level=false:latency=true", "-c:a", "pcm_s16le", str(bed)],
           "ffmpeg (lit musical)")
    if a.no_duck:
        shutil.copy2(bed, dst)
    else:
        sh(["ffmpeg", "-y", "-loglevel", "error", "-i", str(bed), "-i", str(cut), "-filter_complex",
            "[1:a]aresample=48000,aformat=channel_layouts=stereo[sc];"
            "[0:a][sc]sidechaincompress=threshold=0.02:ratio=8:attack=20:release=400:makeup=1[out]",
            "-map", "[out]", "-t", f"{dur:.3f}", "-c:a", "pcm_s16le", str(dst)], "ffmpeg (lit baissé sous la voix)")

    write_json(job / "work" / f"{a.slug}_music.json",
               {**{k: v for k, v in meta.items() if k != "file"}, "file": f"assets/{dst.name}",
                "source_file": str(src), "start": start, "looped": loop, "level_lufs": a.level,
                "measured_lufs": lufs_in, "gain_db": round(gain, 2), "ducked": not a.no_duck})
    credits = job / "renders" / "credits.txt"
    line = f"Musique : {meta.get('attribution')}\n"
    old = credits.read_text(encoding="utf-8").splitlines(keepends=True) if credits.exists() else []
    credits.write_text("".join(x for x in old if not x.startswith("Musique :")) + line, encoding="utf-8")
    out(ok=True, piste=meta.get("title"), licence=meta.get("license"), depart=start, bouclee=loop, duree=round(dur, 1),
        lit=str(dst), credits=str(credits),
        avertissement=("droits à vérifier : lien externe" if a.url else None),
        suite="build_composition.py (ajoute la piste), puis rendu et finalize.py")


if __name__ == "__main__":
    main()

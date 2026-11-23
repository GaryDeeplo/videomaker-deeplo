"""MUSIQUE DE FOND -> assets/<slug>_music.wav + work/<slug>_music.json (lu par build_composition.py)

Source, au choix :
  --mood upbeat|chill|inspiring|energetic|acoustic|cinematic|funky|ambient   banque sounds/music (CC0 / CC-BY)
  --id <id du catalogue>                                                     une piste précise de la banque
  --file <fichier audio>                                                     musique fournie par le client
  --url <lien YouTube / SoundCloud / Bandcamp…>                              téléchargée avec yt-dlp

  python add_music.py <job> <slug> (--mood X | --id I | --file F | --url U) [--start S] [--level -20] [--no-duck]

Le lit est préparé une fois pour toutes : extrait de la bonne longueur (bouclé si la piste est courte), fondu
d'entrée 0,5 s et de sortie 1,5 s, normalisé à --level LUFS (-20 par défaut), puis baissé sous la voix (sidechain
sur l'audio du dérush). La voix reste maîtresse ; le master final se fait avec finalize.py.

⚠ Un lien YouTube / SoundCloud n'est PAS une licence : à n'utiliser que si le client a les droits (sa musique,
une licence achetée, un morceau libre). La source est notée dans les crédits, avec la mention « droits à vérifier ».
"""
import argparse
import shutil
import subprocess
from pathlib import Path

from common import SOUNDS, config, fail, job_dir, out, probe, read_json, sh, write_json


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


def from_bank(mood=None, sid=None, min_len=0):
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
    i = longs[0]
    return SOUNDS / i["file"], i


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("job")
    ap.add_argument("slug")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--mood")
    g.add_argument("--id")
    g.add_argument("--file")
    g.add_argument("--url")
    ap.add_argument("--start", type=float, default=0.0, help="où commencer dans la musique (s)")
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
        src, meta = from_bank(a.mood, a.id, dur + a.start)

    tlen = probe(src)["duration"]
    loop = tlen - a.start < dur
    fade_out = min(1.5, dur / 4)
    dst = job / "assets" / f"{a.slug}_music.wav"
    chain = (f"[0:a]atrim=start={a.start},asetpts=PTS-STARTPTS,"
             f"atrim=end={dur:.3f},afade=t=in:st=0:d=0.5,afade=t=out:st={dur - fade_out:.3f}:d={fade_out:.3f},"
             f"loudnorm=I={a.level}:TP=-3:LRA=11,aresample=48000,aformat=channel_layouts=stereo[bed]")
    cmd = ["ffmpeg", "-y", "-loglevel", "error"] + (["-stream_loop", "-1"] if loop else []) + ["-i", str(src)]
    if a.no_duck:
        fc = chain.replace("[bed]", "[out]")
    else:
        cmd += ["-i", str(cut)]
        fc = (chain + ";[1:a]aresample=48000,aformat=channel_layouts=stereo[sc];"
              "[bed][sc]sidechaincompress=threshold=0.02:ratio=8:attack=20:release=400:makeup=1[out]")
    sh(cmd + ["-filter_complex", fc, "-map", "[out]", "-t", f"{dur:.3f}", "-c:a", "pcm_s16le", str(dst)],
       "ffmpeg (lit musical)")
    # lit sans baisse : mix.py en tire une courbe précise (parole + bruitages) une fois la composition montée
    bed = job / "assets" / f"{a.slug}_music_bed.wav"
    sh(["ffmpeg", "-y", "-loglevel", "error"] + (["-stream_loop", "-1"] if loop else []) + ["-i", str(src), "-filter_complex",
        chain.replace("[bed]", "[out]"), "-map", "[out]", "-t", f"{dur:.3f}", "-c:a", "pcm_s16le", str(bed)], "ffmpeg (lit sans baisse)")

    write_json(job / "work" / f"{a.slug}_music.json",
               {**{k: v for k, v in meta.items() if k != "file"}, "file": f"assets/{dst.name}",
                "source_file": str(src), "start": a.start, "looped": loop, "level_lufs": a.level,
                "ducked": not a.no_duck})
    credits = job / "renders" / "credits.txt"
    line = f"Musique : {meta.get('attribution')}\n"
    old = credits.read_text(encoding="utf-8").splitlines(keepends=True) if credits.exists() else []
    credits.write_text("".join(x for x in old if not x.startswith("Musique :")) + line, encoding="utf-8")
    out(ok=True, piste=meta.get("title"), licence=meta.get("license"), bouclee=loop, duree=round(dur, 1),
        lit=str(dst), credits=str(credits),
        avertissement=("droits à vérifier : lien externe" if a.url else None),
        suite="build_composition.py (ajoute la piste), puis rendu et finalize.py")


if __name__ == "__main__":
    main()

"""Construit et enrichit la banque sounds/ depuis Openverse (CC0 / CC-BY / PDM, Freesound + Jamendo, sans clé).

  python bank.py sfx   [--per 8] [--only whoosh,pop]     # effets -> sounds/openverse/<catégorie>/
  python bank.py music [--per 4] [--only upbeat,chill]   # musiques -> sounds/music/<ambiance>/ (+ BPM, LUFS)
  python bank.py sfx --only boom --query "bass drop"     # autre requête pour une catégorie maigre
  python bank.py list                                    # état de la banque

Une seule recherche par requête (Openverse anonyme : ~200 recherches/jour). Chaque fichier téléchargé est
tracé dans catalog.json et son attribution recopiée telle quelle dans CREDITS.txt (obligatoire pour CC-BY).
Après un ajout de SFX : reconstruire l'index real-sfx (fait automatiquement à la fin).
"""
import argparse
import json
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

from common import SOUNDS, out, read_json, write_json

API = "https://api.openverse.org/v1/audio/"
UA = {"User-Agent": "deeplo-video-maker/1.0 (openverse-sfx)"}
REAL_SFX = Path.home() / ".claude" / "skills" / "real-sfx"

# catégorie -> (requête Openverse, durée min ms, durée max ms)
SFX = {
    "whoosh": ("whoosh", 200, 2500),
    "swoosh": ("swoosh transition", 200, 2500),
    "pop": ("pop bubble", 50, 1200),
    "click": ("mouse click", 30, 800),
    "tick": ("tick", 30, 600),
    "hit": ("impact hit", 100, 3000),
    "boom": ("cinematic boom", 500, 5000),
    "riser": ("riser", 800, 6000),
    "swell": ("reverse swell", 500, 5000),
    "cash": ("cash register", 300, 3000),
    "ding": ("notification ding", 100, 2500),
    "chime": ("success chime", 200, 4000),
    "sparkle": ("magic sparkle", 200, 4000),
    "shutter": ("camera shutter", 100, 1500),
    "typing": ("keyboard typing", 1000, 8000),
    "paper": ("paper page turn", 200, 2500),
    "glitch": ("glitch", 100, 2500),
    "applause": ("applause", 1500, 10000),
}

# ambiance -> requête (pistes de 60 s à 6 min)
MUSIC = {
    "upbeat": "upbeat corporate",
    "chill": "lofi chill",
    "inspiring": "inspiring piano",
    "energetic": "energetic electronic",
    "acoustic": "happy acoustic ukulele",
    "cinematic": "cinematic epic",
    "funky": "funky groove",
    "ambient": "ambient calm",
}


def search(q, min_ms, max_ms, n):
    qs = {"q": q, "license": "cc0,by,pdm", "source": "freesound,jamendo", "page_size": "20"}
    with urllib.request.urlopen(urllib.request.Request(API + "?" + urllib.parse.urlencode(qs), headers=UA),
                                timeout=30) as r:
        data = json.load(r)
    res = [x for x in data.get("results", []) if min_ms <= (x.get("duration") or 0) <= max_ms and x.get("url")]
    return res[:n]


def fetch(url, dst):
    tmp = dst.with_suffix(dst.suffix + ".part")
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90) as r, open(tmp, "wb") as f:
        f.write(r.read())
    if tmp.stat().st_size < 1000:
        tmp.unlink()
        raise OSError("fichier vide")
    tmp.replace(dst)


def ext_of(url):
    e = Path(url.split("?")[0]).suffix
    return e if e in (".mp3", ".wav", ".ogg", ".flac") else ".mp3"


def analyse_music(p):
    """BPM (librosa) + LUFS intégré (ffmpeg ebur128)."""
    info = {}
    try:
        import librosa
        y, sr = librosa.load(str(p), sr=22050, mono=True, duration=90)
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        info["bpm"] = round(float(tempo[0] if hasattr(tempo, "__len__") else tempo), 1)
    except Exception as e:  # noqa: BLE001
        info["bpm_error"] = str(e)[:80]
    log = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(p), "-af", "ebur128", "-f", "null", "-"],
                         capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
    for line in reversed(log.splitlines()):
        if line.strip().startswith("I:"):
            info["lufs"] = float(line.split()[1])
            break
    return info


def run(kind, per, only, query=None):
    base = SOUNDS / ("openverse" if kind == "sfx" else "music")
    base.mkdir(parents=True, exist_ok=True)
    cat_path, credits = base / "catalog.json", base / "CREDITS.txt"
    catalog = read_json(cat_path) if cat_path.exists() else {"items": []}
    have = {i["id"] for i in catalog["items"]}
    have |= {p.stem.split("_")[-1] for p in base.rglob("*") if p.is_file()}
    table = SFX if kind == "sfx" else {k: (v, 60000, 360000) for k, v in MUSIC.items()}
    added, searches = [], 0
    for name, (q, lo, hi) in table.items():
        if only and name not in only:
            continue
        q = query or q
        try:
            res = search(q, lo, hi, per * 2)
            searches += 1
        except Exception as e:  # noqa: BLE001
            print(json.dumps({"warn": f"recherche {q} : {e}"}, ensure_ascii=False), file=sys.stderr)
            continue
        got = 0
        for x in res:
            sid = x["id"].replace("-", "")[:8]
            if sid in have:
                continue
            dst = base / name / f"{name}_{sid}{ext_of(x['url'])}"
            dst.parent.mkdir(exist_ok=True)
            try:
                fetch(x["url"], dst)
            except Exception as e:  # noqa: BLE001
                print(json.dumps({"warn": f"téléchargement {x['url'][:60]} : {e}"}, ensure_ascii=False), file=sys.stderr)
                continue
            item = {"id": sid, "openverse_id": x["id"], "category": name, "file": str(dst.relative_to(SOUNDS)),
                    "title": x.get("title"), "creator": x.get("creator"), "license": x.get("license"),
                    "source": x.get("source"), "duration_s": round((x.get("duration") or 0) / 1000, 2),
                    "landing_url": x.get("foreign_landing_url"), "attribution": x.get("attribution")}
            if kind == "music":
                item.update(analyse_music(dst))
            catalog["items"].append(item)
            with open(credits, "a", encoding="utf-8") as f:
                f.write(f"{dst.name}: {x.get('attribution')}\n")
            have.add(sid)
            added.append(item["file"])
            got += 1
            if got >= per:
                break
        time.sleep(0.5)
    write_json(cat_path, catalog)
    if kind == "sfx" and added and (REAL_SFX / "scripts" / "build_index.py").exists():
        subprocess.run([sys.executable, "scripts/build_index.py"], cwd=REAL_SFX, capture_output=True)
    out(ok=True, kind=kind, recherches=searches, ajoutes=len(added), total=len(catalog["items"]), catalog=str(cat_path))


def listing():
    rows = {}
    for p in SOUNDS.rglob("*"):
        if p.suffix.lower() in (".mp3", ".wav", ".ogg", ".flac"):
            k = str(p.parent.relative_to(SOUNDS))
            rows[k] = rows.get(k, 0) + 1
    out(ok=True, total=sum(rows.values()), par_dossier=dict(sorted(rows.items())))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("kind", choices=["sfx", "music", "list"])
    ap.add_argument("--per", type=int)
    ap.add_argument("--only", default="")
    ap.add_argument("--query", help="autre requête pour UNE catégorie (--only obligatoire)")
    a = ap.parse_args()
    if a.kind == "list":
        return listing()
    only = {x for x in a.only.split(",") if x}
    if a.query and len(only) != 1:
        return out(ok=False, error="--query demande une seule catégorie dans --only")
    run(a.kind, a.per or (8 if a.kind == "sfx" else 4), only, a.query)


if __name__ == "__main__":
    main()

"""VISAGES À L'ÉCRAN : sous-titres qui évitent le visage, et contrôle « visage couvert ».

  python face.py <job> <slug>                                           # visage couvert ? (dernière composition)
  python face.py <job> <slug> --placer [--plateforme tous|reels|tiktok|shorts]   # positions des sous-titres, sans rien écrire

D'après ghost-editor (MIT) : scripts/face_track.py et scripts/lib/safezone.mjs, portés en Python.
- face_samples(video) : boîtes de visage échantillonnées (YuNet, local, même détecteur que reframe.py), en cache dans
  work/<vidéo>_visages.json (reframe.py y dépose aussi ses détections : pas de second passage).
- placer_sous_titres(blocs, visages, geo, plateforme) : chaque groupe de sous-titres va sous le menton s'il y a la
  place dans la zone sûre de la plateforme, sinon au-dessus de la tête, sinon le plus bas possible sur fond sombre ;
  la zone ne change qu'entre deux groupes et les petits écarts sont gardés (hystérésis) : pas de sautillement.
- couverture(job) : à partir de work/<slug>_calques.json (écrit par build_composition.py : où et quand chaque texte,
  carte, plan de coupe ou bloc est posé), liste les moments (~1 image/s) où un calque couvre le visage.
Les temps sont ceux de la vidéo dérushée (= timeline du contenu de la composition, avant l'intro T0).
"""
import argparse
from pathlib import Path

from common import ROOT, job_dir, out, read_json, write_json

MODEL = ROOT / ".claude" / "skills" / "videomaker-deeplo" / "vendor" / "yunet" / "face_detection_yunet_2023mar.onnx"

# Interface des applis à 1080x1920 (px couverts) : d'après ghost-editor (MIT), lib/safezone.mjs.
# right = colonne des boutons (j'aime, commentaire…), qui ne compte que pour la moitié basse.
PLATEFORMES = {
    "reels": {"top": 220, "bottom": 420, "right": 130, "nom": "Instagram Reels"},
    "tiktok": {"top": 160, "bottom": 480, "right": 150, "nom": "TikTok"},
    "shorts": {"top": 140, "bottom": 380, "right": 140, "nom": "YouTube Shorts"},
    "tous": {"top": 220, "bottom": 480, "right": 150, "nom": "Reels + TikTok + Shorts"},
}
ALIAS = {"instagram": "reels", "all": "tous", "youtube": "shorts"}
SEUIL, SEUIL_FORT = 0.12, 0.25  # part du visage couverte : info, puis « à revoir »


# ---------------------------------------------------------------- détection

def detect_boxes(src, fps):
    """YuNet sur fps images/s -> ([[t, x, y, w, h, yeux_y, bouche_y, cx] | [t, None]], largeur, hauteur), pixels source
    (cx : centre en part de la largeur, celui que suit reframe.py). Les petits visages du fond sont ignorés, puis le plus
    grand, puis le plus proche du précédent (pas de va-et-vient)."""
    import cv2
    cap = cv2.VideoCapture(str(src))
    sfps = cap.get(cv2.CAP_PROP_FPS) or 30
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    sw, sh = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    k = 640 / sw
    det = cv2.FaceDetectorYN.create(str(MODEL), "", (640, int(sh * k)), 0.7, 0.3, 50)
    step, res, prev = max(1, round(sfps / fps)), [], None
    for f in range(n):  # lecture continue (un saut par image est beaucoup plus lent) ; on ne décode qu'1 image sur step
        if f % step:
            if not cap.grab():
                break
            continue
        ok, img = cap.read()
        if not ok:
            break
        _, faces = det.detect(cv2.resize(img, (640, int(sh * k))))
        row = [f / sfps, None]
        if faces is not None and len(faces):
            big = max(fc[2] * fc[3] for fc in faces)
            ok_f = [fc for fc in faces if fc[2] * fc[3] >= 0.4 * big]  # ignore les petits visages du fond
            pick = (min(ok_f, key=lambda fc: abs((fc[0] + fc[2] / 2) / 640 - prev)) if prev is not None
                    else max(ok_f, key=lambda fc: fc[2] * fc[3]))
            prev = float((pick[0] + pick[2] / 2) / 640)
            # repères YuNet : œil droit, œil gauche, nez, coin droit, coin gauche de la bouche
            row = [f / sfps] + [float(v) / k for v in (pick[0], pick[1], pick[2], pick[3],
                                                       (pick[5] + pick[7]) / 2, (pick[11] + pick[13]) / 2)] + [prev]
        res.append(row)
    cap.release()
    return res, sw, sh


def _cache(video, work=None):
    video = Path(video)
    if work is None:
        work = video.parent.parent / "work" if (video.parent.parent / "work").is_dir() else video.parent
    return Path(work) / f"{video.stem}_visages.json"


def save_samples(video, samples, sw, sh, fps, work=None):
    """Range les détections en cache (pixels source, arrondis) ; reframe.py l'appelle aussi."""
    video = Path(video)
    data = {"source": video.name, "mtime": round(video.stat().st_mtime, 1), "taille": [sw, sh], "fps": fps,
            "samples": [[round(s[0], 3)] + ([None] if s[1] is None else [round(v, 1) for v in s[1:7]]) for s in samples]}
    try:
        write_json(_cache(video, work), data)
    except OSError:
        pass  # cache facultatif
    return data


def face_samples(video, work=None, fps=4.0):
    """Boîtes de visage dans le temps -> {"taille": [w, h], "fps", "samples": [[t, x, y, w, h, yeux, bouche] | [t, None]]}.
    Le cache (work/<vidéo>_visages.json) sert tant que la vidéo n'a pas changé et qu'il est au moins aussi dense."""
    video = Path(video)
    c = _cache(video, work)
    if c.exists():
        d = read_json(c)
        if d.get("source") == video.name and abs(d.get("mtime", 0) - video.stat().st_mtime) < 1 and d.get("fps", 0) >= fps - 1e-6:
            return d
    if not MODEL.exists():
        return {"taille": None, "fps": fps, "samples": [], "erreur": f"modèle absent : {MODEL}"}
    samples, sw, sh = detect_boxes(video, fps)
    return save_samples(video, samples, sw, sh, fps, work)


def part_visages(visages):
    s = visages.get("samples") or []
    return round(100 * sum(1 for x in s if x[1] is not None) / max(1, len(s)))


def boite(s, large=True):
    """Boîte d'un échantillon (pixels source). large : agrandie aux cheveux et au menton (placement, d'après
    face_track.py) ; sinon le visage lui-même (front -> menton), pour mesurer ce qui le couvre."""
    t, x, y, w, h, ey, my = s[:7]
    if large:
        return {"top": y - 0.35 * h, "bottom": y + 1.12 * h, "left": x - 0.08 * w, "right": x + 1.08 * w, "eyes": ey, "mouth": my}
    return {"top": y - 0.05 * h, "bottom": y + 1.08 * h, "left": x, "right": x + w, "eyes": ey, "mouth": my}


def face_at(samples, t, hold=1.5):
    """Échantillon le plus proche de t (on garde le dernier visage vu sur un court trou), sinon None."""
    best, bd = None, 1e9
    for s in samples:
        if s[1] is None:
            continue
        d = abs(s[0] - t)
        if d < bd:
            best, bd = s, d
        if s[0] > t + hold:
            break
    return best if bd <= hold else None


# ---------------------------------------------------------------- source -> écran

class Projection:
    """Point de la vidéo source -> pixel de la composition, comme build_composition.py la pose : object-fit cover /
    contain (object-position focusX% posY%), ou suivi du visage (vidéo pleine largeur qui glisse en x), dans une zone
    (écran entier, ou bas de l'écran partagé), sous la caméra #cam (drifts, punchs) et #zm (zooms).
    geo : {W, H, src: [w, h], fit, focusX, posY, zone: [x, y, w, h], VW, track: {start, moves}, cam: [...], zooms: [[t, fin, échelle]]}"""

    def __init__(self, geo):
        self.g = geo
        self.W, self.H = geo["W"], geo["H"]
        self.sw, self.sh = geo["src"]
        self.zx, self.zy, self.zw, self.zh = geo.get("zone") or [0, 0, self.W, self.H]
        fx = float(geo.get("focusX", 50))
        self.cam_o = (self.zx + self.zw * fx / 100, self.zy + self.zh * 0.42)
        self.zm_o = (self.zx + self.zw * fx / 100, self.zy + self.zh * 0.38)
        fit = geo.get("fit", "cover")
        if fit == "track":
            self.s = self.zh / self.sh
            self.dy = self.zy
        else:
            self.s = (max if fit == "cover" else min)(self.zw / self.sw, self.zh / self.sh)
            self.dx = self.zx + (self.zw - self.sw * self.s) * fx / 100
            self.dy = self.zy + (self.zh - self.sh * self.s) * float(geo.get("posY", 50)) / 100

    def _dx(self, t):
        if self.g.get("fit") != "track":
            return self.dx
        tr, VW = self.g["track"], self.g["VW"]
        cx = tr["start"]
        for tm, c, d in tr.get("moves", []):
            if t >= tm + d:
                cx = c
            elif t > tm:
                cx = cx + (c - cx) * (t - tm) / d
                break
            else:
                break
        return self.zx + min(0, max(self.zw - VW, self.zw / 2 - cx * VW))

    def scales(self, t):
        c = 1.0
        for e in self.g.get("cam") or []:  # [t, de, à, durée, ease]
            if t >= e[0]:
                c = e[2] if t >= e[0] + e[3] else e[1] + (e[2] - e[1]) * (t - e[0]) / max(e[3], 1e-3)
        z = 1.0
        for a, b, sc in self.g.get("zooms") or []:
            if a <= t < b:
                z = sc
        return c, z

    def point(self, x, y, t):
        c, z = self.scales(t)
        X, Y = self._dx(t) + x * self.s, self.dy + y * self.s
        X, Y = self.cam_o[0] + c * (X - self.cam_o[0]), self.cam_o[1] + c * (Y - self.cam_o[1])
        return self.zm_o[0] + z * (X - self.zm_o[0]), self.zm_o[1] + z * (Y - self.zm_o[1])

    def box(self, b, t):
        l, tp = self.point(b["left"], b["top"], t)
        r, bt = self.point(b["right"], b["bottom"], t)
        _, ey = self.point(0, b["eyes"], t)
        _, my = self.point(0, b["mouth"], t)
        return {"top": tp, "bottom": bt, "left": l, "right": r, "eyes": ey, "mouth": my}


def _geo(fmt, visages):
    if isinstance(fmt, dict):
        return fmt
    W, H = fmt  # simple format (L, H) : source recadrée plein cadre, sans caméra
    return {"W": W, "H": H, "src": visages.get("taille") or [W, H], "fit": "cover", "focusX": 50}


def _masque(t, masques):
    return any(a <= t < b for a, b in masques or [])


def portee(visages, proj, t0, t1, masques=None):
    """Union des boîtes de visage (écran) pendant [t0, t1] ; seen=False si aucun visage (ou visage caché par un plan
    plein écran)."""
    S = [s for s in visages.get("samples") or [] if s[1] is not None]
    r = {"top": 1e9, "bottom": -1e9, "left": 1e9, "right": -1e9, "mouth": -1e9, "eyes": 1e9, "seen": False}
    pts = [s for s in S if t0 - 0.1 <= s[0] <= t1 + 0.1 and not _masque(s[0], masques)]
    if not pts:  # bloc plus court que l'échantillonnage : le visage le plus proche
        m = (t0 + t1) / 2
        f = None if _masque(m, masques) else face_at(S, m, hold=1.5)
        pts = [f] if f else []
    for s in pts:
        f = proj.box(boite(s), min(max(s[0], t0), t1))
        r["seen"] = True
        for k_, fn in (("top", min), ("bottom", max), ("left", min), ("right", max), ("mouth", max), ("eyes", min)):
            r[k_] = fn(r[k_], f[k_])
    return r


# ---------------------------------------------------------------- placement des sous-titres

def plateforme_px(plateforme, W, H):
    P = PLATEFORMES.get(ALIAS.get(plateforme, plateforme)) or PLATEFORMES["tous"]
    return P, round(P["top"] * H / 1920), round(H - P["bottom"] * H / 1920)


def placer_sous_titres(blocs, visages, fmt, plateforme="tous", ideal=None, occupes=None, masques=None):
    """D'après ghost-editor (MIT), lib/safezone.mjs (makePlacer.place).
    blocs : [{"id", "t0", "t1", "h"}] (temps du contenu, h = hauteur du bloc en px) ; visages : face_samples() ;
    fmt : géométrie de la composition (voir Projection) ou (L, H) ; occupes : [{"t0", "t1", "y0", "y1"}] déjà à l'écran
    (cartes, accroche) que le sous-titre contourne ; masques : [(t0, t1)] où un plan plein écran cache le visage.
    -> [{"id", "y", "mode", "fond", "visage"}] ; mode : sous | dessus | bas-fond (gros plan : le plus bas possible,
    sur fond sombre) | sans-visage (hauteur par défaut)."""
    geo = _geo(fmt, visages)
    W, H = geo["W"], geo["H"]
    proj = Projection(geo)
    P, safe_top, safe_bot = plateforme_px(plateforme, W, H)
    ideal = round(H * 0.66) if ideal is None else ideal
    gap, hold = round(36 * H / 1920), round(70 * H / 1920)
    occ = list(occupes or [])
    clash = lambda t0, t1, y, h: next((o for o in occ if t0 < o["t1"] and t1 > o["t0"] and y < o["y1"] and y + h > o["y0"]), None)
    prev, res = None, []
    for b in blocs:
        t0, t1, h = b["t0"], b["t1"], b["h"]
        sp = portee(visages, proj, t0, t1, masques)
        max_y = safe_bot - h
        opts = {}
        if not sp["seen"]:
            # pas de visage : la hauteur par défaut (comportement d'avant), ou celle du bloc précédent pour ne pas sauter
            opts["sans-visage"] = prev["y"] if prev and prev["mode"] in ("sous", "dessus", "sans-visage") else ideal
        else:
            if sp["bottom"] + gap <= max_y:
                opts["sous"] = max(sp["bottom"] + gap, min(ideal, max_y))
            if sp["top"] - gap - h >= safe_top:
                opts["dessus"] = sp["top"] - gap - h
            opts["bas-fond"] = max(safe_top, max_y)  # gros plan : le plus bas possible (torse, mains), fond sombre
        # verrou de zone : on reste dans la zone du bloc précédent tant qu'elle convient (pas de haut / bas / haut)
        mode = (prev["mode"] if prev and prev["mode"] in opts and prev["mode"] != "bas-fond"
                else next(m for m in ("sans-visage", "sous", "dessus", "bas-fond") if m in opts))
        y = opts[mode]
        c = clash(t0, t1, y, h)
        if c:  # une carte au même moment : juste en dessous, sinon l'autre zone
            under = c["y1"] + round(24 * H / 1920)
            if under + h <= max_y and (not sp["seen"] or under >= sp["bottom"] + gap or under + h <= sp["top"] - gap):
                y = under
            else:
                alt = next((m for m in ("sous", "dessus", "bas-fond") if m != mode and m in opts and not clash(t0, t1, opts[m], h)), None)
                if alt:
                    mode, y = alt, opts[alt]
        # hystérésis : un petit déplacement est ignoré si l'ancienne hauteur reste valable (même zone, ou sous le
        # menton <-> gros plan, qui sont toutes deux en bas)
        bas = {"sous", "bas-fond"}
        if prev and (prev["mode"] == mode or {prev["mode"], mode} <= bas) and abs(prev["y"] - y) < hold:
            py = prev["y"]
            ok = {"sous": lambda: sp["bottom"] + gap <= py <= max_y,
                  "dessus": lambda: safe_top <= py and py + h <= sp["top"] - gap,
                  "bas-fond": lambda: sp["mouth"] + gap <= py <= max_y}.get(mode, lambda: safe_top <= py <= max_y)()
            if ok:
                y = py
        y = round(y)
        prev = {"y": y, "mode": mode}
        res.append({"id": b["id"], "y": y, "mode": mode, "fond": mode == "bas-fond",
                    "visage": {k_: round(sp[k_]) for k_ in ("top", "bottom", "eyes", "mouth")} if sp["seen"] else None})
    return res


# ---------------------------------------------------------------- visage couvert

def _calques_file(job, slug=None):
    work = job / "work"
    if slug:
        p = work / f"{slug}_calques.json"
        return p if p.exists() else None
    c = sorted(work.glob("*_calques.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    return c[0] if c else None


def couverture(job, slug=None, pas=1.0):
    """Moments où un calque (texte, carte, plan de coupe en carte, bloc) couvre le visage, ~1 image/s.
    Lit work/<slug>_calques.json (build_composition.py) et les visages en cache (sinon les détecte à 1 image/s).
    -> [(niveau, quoi, détail)] au format de qa.py ; « à revoir » dès 25 % du visage couvert ou sur les yeux / la bouche,
    « info » dès 12 % (toujours « info » pour une position estimée : blocs de motion, bandeau nom). Les sous-titres
    sont regroupés en un seul calque « sous-titres »."""
    job = Path(job)
    f = _calques_file(job, slug)
    if not f:
        return []
    cq = read_json(f)
    geo, T0 = cq.get("geo"), float(cq.get("T0", 0))
    video = job / cq["video"] if cq.get("video") else None
    if not geo or not video or not video.exists():
        return []
    vis = face_samples(video, fps=1.0)
    if part_visages(vis) < 15:
        return []
    proj = Projection(geo)
    S = [s for s in vis["samples"] if s[1] is not None]
    masques = [(c["t0"], c["t1"]) for c in cq["calques"] if c.get("type") == "plein-ecran"]
    hits = {}  # nom -> [(t, part)]
    t = pas / 2
    while t < float(cq["duree"]):
        fs = face_at(S, t, hold=0.6)
        if fs and not _masque(t, masques):
            fb = proj.box(boite(fs, large=False), t)
            area = max(1.0, (fb["right"] - fb["left"]) * (fb["bottom"] - fb["top"]))
            for c in cq["calques"]:
                if c.get("type") == "plein-ecran" or not (c["t0"] <= t < c["t1"]):
                    continue
                x0, y0, x1, y1 = c["box"]
                ix = max(0.0, min(x1, fb["right"]) - max(x0, fb["left"]))
                iy = max(0.0, min(y1, fb["bottom"]) - max(y0, fb["top"]))
                part = ix * iy / area
                if part >= SEUIL:
                    traits = [n_ for n_, ly in (("yeux", fb["eyes"]), ("bouche", fb["mouth"])) if ix > 0 and y0 <= ly <= y1]
                    nom = "sous-titres" if c["type"] == "sous-titre" else c["nom"]
                    hits.setdefault((c["type"], nom, bool(c.get("estime"))), []).append((t, part, traits))
        t += pas
    pts = []
    for (typ, nom, est), hs in hits.items():
        runs = [[hs[0]]]
        for h_ in hs[1:]:
            if h_[0] - runs[-1][-1][0] <= pas * 1.5:
                runs[-1].append(h_)
            else:
                runs.append([h_])
        for r_ in runs:
            mx = max(p for _, p, _ in r_)
            traits = sorted({x for *_, tr in r_ for x in tr})
            a, b = T0 + r_[0][0] - pas / 2, T0 + r_[-1][0] + pas / 2
            lvl = "à revoir" if (mx >= SEUIL_FORT or traits) and not est else "info"
            pts.append((r_[0][0], lvl, "visage couvert",
                        ("sous-titres" if typ == "sous-titre" else f"{typ} « {nom} »") + f" sur {round(100 * mx)} % du visage" + (f" ({' et '.join(traits)})" if traits else "") +
                        f" de {a:.1f} à {b:.1f} s" + (" (position estimée)" if est else "")))
    return [p[1:] for p in sorted(pts)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("job")
    ap.add_argument("slug")
    ap.add_argument("--placer", action="store_true", help="positions des sous-titres de la dernière composition, sans rien écrire")
    ap.add_argument("--plateforme", default="tous", choices=sorted(PLATEFORMES) + sorted(ALIAS))
    a = ap.parse_args()
    job = job_dir(a.job)
    if a.placer:
        f = _calques_file(job, a.slug)
        if not f:
            return out(ok=False, erreur="pas de work/<slug>_calques.json : lance d'abord build_composition.py")
        cq = read_json(f)
        vis = face_samples(job / cq["video"])
        blocs = [{"id": c["nom"], "t0": c["t0"], "t1": c["t1"], "h": c["box"][3] - c["box"][1]} for c in cq["calques"] if c["type"] == "sous-titre"]
        pl = placer_sous_titres(blocs, vis, cq["geo"], a.plateforme, ideal=cq.get("ideal"),
                                masques=[(c["t0"], c["t1"]) for c in cq["calques"] if c["type"] == "plein-ecran"])
        return out(ok=True, visages_pct=part_visages(vis), plateforme=a.plateforme,
                   positions=[f'{p["id"]} : {p["y"]} px ({p["mode"]})' for p in pl])
    if not _calques_file(job, a.slug):
        return out(ok=False, verdict="non vérifié", erreur="pas de work/<slug>_calques.json : lance d'abord build_composition.py")
    pts = couverture(job, a.slug)
    out(ok=True, verdict="OK" if not any(p[0] == "à revoir" for p in pts) else "à revoir",
        points=[f"{lvl} — {q} : {d}" for lvl, q, d in pts])


if __name__ == "__main__":
    main()

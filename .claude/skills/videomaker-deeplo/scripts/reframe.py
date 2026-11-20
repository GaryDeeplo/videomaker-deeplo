"""RECADRAGE QUI SUIT LE VISAGE -> work/<slug>_reframe.json

  python reframe.py <job> <slug> [--size 9:16] [--fps 4] [--zone 0.18]

Pour une source plus large que le format de sortie (interview ou webinaire en 16:9 -> Reel 9:16) : au lieu d'afficher
l'image entière sur fond flouté, la fenêtre suit la personne qui parle. Détection locale (YuNet, OpenCV, MIT : rien ne
quitte la machine) sur 4 images par seconde de la vidéo dérushée, puis un trajet de caméra « posé » : la fenêtre reste
immobile tant que le visage reste dans sa zone centrale et ne glisse (0,7 s, douce) que quand il en sort.
Plusieurs visages : on garde le plus grand, puis celui le plus proche du précédent (pas de va-et-vient).
Moins de 40 % d'images avec un visage : l'outil le dit et build_composition garde le fond flouté.
build_composition.py utilise le fichier tout seul (visual.fit "auto" ou "track" ; "fill" ou "cover" le désactivent).
"""
import argparse
from pathlib import Path

from common import ROOT, config, fail, job_dir, out, read_json, size_of, write_json

MODEL = ROOT / ".claude" / "skills" / "videomaker-deeplo" / "vendor" / "yunet" / "face_detection_yunet_2023mar.onnx"
MOVE, MIN_GAP = 0.7, 1.5  # durée d'un glissement, écart minimal entre deux glissements (s)


def detect(src, fps):
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
        cx = None
        if faces is not None and len(faces):
            big = max(fc[2] * fc[3] for fc in faces)
            ok_f = [fc for fc in faces if fc[2] * fc[3] >= 0.4 * big]  # ignore les petits visages du fond
            pick = (min(ok_f, key=lambda fc: abs((fc[0] + fc[2] / 2) / 640 - prev)) if prev is not None
                    else max(ok_f, key=lambda fc: fc[2] * fc[3]))
            cx = float((pick[0] + pick[2] / 2) / 640)
            prev = cx
        res.append((f / sfps, cx))
    cap.release()
    return res, sw, sh


def camera_path(samples, cw, zone=0.18):
    """Trajet « posé » d'une fenêtre de largeur cw (fraction de la source) sur les centres de visage [(t, cx|None)].
    -> (centre de départ, [[t, centre, durée], …])"""
    found = [x for _, x in samples if x is not None]
    xs, last = [], found[0]
    for _, x in samples:  # trous comblés avec le dernier visage vu (ou le premier)
        last = x if x is not None else last
        xs.append(last)
    sm = [sorted(xs[max(0, i - 2):i + 3])[len(xs[max(0, i - 2):i + 3]) // 2] for i in range(len(xs))]  # médiane sur 5
    clamp = lambda v: min(1 - cw / 2, max(cw / 2, v))
    cam = clamp(sm[0])
    start, moves, t_last = round(cam, 4), [], -99.0
    for (t, _), x in zip(samples, sm):
        target = clamp(x)
        if abs(target - cam) > zone * cw and t - t_last >= MIN_GAP:
            moves.append([round(max(0.0, t - 0.2), 3), round(target, 4), MOVE])
            cam, t_last = target, t
    return start, moves


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("job")
    ap.add_argument("slug")
    ap.add_argument("--size", help="format de sortie (défaut : config)")
    ap.add_argument("--fps", type=float, default=4.0)
    ap.add_argument("--zone", type=float, default=0.18, help="zone centrale (part de la fenêtre) où le visage peut bouger sans que la caméra suive")
    a = ap.parse_args()
    job = job_dir(a.job)
    c = config(job)
    W, H = size_of(a.size, c["visual"])
    m = read_json(job / "work" / f"{a.slug}_map.json")
    src = Path(m["cut"])
    if not MODEL.exists():
        fail(f"modèle de détection absent : {MODEL}")
    samples, sw, sh = detect(src, a.fps)
    cw = (sh * W / H) / sw  # largeur visible de la source, en fraction
    if cw >= 0.98:
        return out(ok=True, utile=False, raison="la source n'est pas plus large que le format : rien à suivre")
    found = [s for s in samples if s[1] is not None]
    pct = round(100 * len(found) / max(1, len(samples)))
    dst = job / "work" / f"{a.slug}_reframe.json"
    if pct < 40:
        dst.unlink(missing_ok=True)
        return out(ok=True, utile=False, visages_pct=pct, raison="trop peu de visages : on garde l'image entière sur fond flouté")
    start, moves = camera_path(samples, cw, a.zone)
    # les centres de visage sont gardés : build_composition recalcule le trajet pour chaque format (9:16, 1:1…)
    write_json(dst, {"source": src.name, "src_size": [sw, sh], "zone": a.zone, "visages_pct": pct,
                     "samples": [[round(t, 3), None if x is None else round(x, 4)] for t, x in samples],
                     "size": [W, H], "start": start, "moves": moves})
    out(ok=True, utile=True, visages_pct=pct, glissements=len(moves), fenetre_pct=round(100 * cw), out=str(dst),
        suite="build_composition.py (suit le visage tout seul) ; snapshot pour vérifier le cadrage")


if __name__ == "__main__":
    main()

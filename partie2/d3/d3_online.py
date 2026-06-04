import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import math
from utils import load_marchandises, print_results

L_WAG, l_WAG, H_WAG = 11.583, 2.294, 2.569
VOL_WAG = L_WAG * l_WAG * H_WAG
EPS = 1e-4


class Marchandise:
    __slots__ = ['id', 'rotations']

    def __init__(self, data: dict):
        self.id = data['id']
        L, l, H = data['longueur'], data['largeur'], data['hauteur']

        if data.get('retournable', 1) == 0:
            rot = [(L, l, H), (l, L, H)]
        else:
            rot = [(L, l, H), (L, H, l), (l, L, H), (l, H, L), (H, L, l), (H, l, L)]

        self.rotations = sorted(set(rot), key=lambda r: r[2])


class Wagon:
    __slots__ = ['boites', 'coins', 'vol_used']

    def __init__(self):
        # boites = (cx, cy, cz, rL, rl, rH, item_id)
        self.boites: list[tuple] = []
        self.coins: set[tuple] = {(0.0, 0.0, 0.0)}
        self.vol_used: float = 0.0

    def intersecte(self, b1: tuple) -> bool:
        for b2 in self.boites:
            if (b1[0] < b2[0] + b2[3] - EPS and b1[0] + b1[3] > b2[0] + EPS and
                    b1[1] < b2[1] + b2[4] - EPS and b1[1] + b1[4] > b2[1] + EPS and
                    b1[2] < b2[2] + b2[5] - EPS and b1[2] + b1[5] > b2[2] + EPS):
                return True
        return False

    def est_supportee(self, xmin: float, xmax: float, ymin: float, ymax: float,
                      zmin: float, seuil: float = 0.55) -> bool:
        if zmin <= EPS:
            return True

        aire_base = (xmax - xmin) * (ymax - ymin)
        aire_support = 0.0

        for bx, by, bz, bL, bl, bH, *_ in self.boites:
            if abs(bz + bH - zmin) <= EPS:
                ox = min(xmax, bx + bL) - max(xmin, bx)
                oy = min(ymax, by + bl) - max(ymin, by)
                if ox > 0 and oy > 0:
                    aire_support += ox * oy

        return (aire_support / aire_base) >= seuil

    def _ajouter_coin(self, x: float, y: float, z: float) -> None:
        if x <= L_WAG and y <= l_WAG and z <= H_WAG:
            self.coins.add((x, y, z))

    def placer(self, coin: tuple, rL: float, rl: float, rH: float, item_id: int = 0) -> None:
        cx, cy, cz = coin
        n_avant = len(self.boites)
        self.boites.append((cx, cy, cz, rL, rl, rH, item_id))
        self.vol_used += rL * rl * rH
        self.coins.discard(coin)

        xf, yf, zf = cx + rL, cy + rl, cz + rH

        # Points standards (3 coins de la nouvelle boîte)
        self._ajouter_coin(xf, cy, cz)
        self._ajouter_coin(cx, yf, cz)
        self._ajouter_coin(cx, cy, zf)

        # Extreme points : cross-projection entre nouvelle boîte et existantes
        for bx, by, bz, bL, bl, bH, *_ in self.boites[:n_avant]:
            bxf, byf, bzf = bx + bL, by + bl, bz + bH
            # x de la nouvelle boîte × y,z de l'existante (et vice-versa)
            for nx in (cx, xf):
                for ey in (by, byf):
                    for ez in (bz, bzf):
                        self._ajouter_coin(nx, ey, ez)
            for ny in (cy, yf):
                for ex in (bx, bxf):
                    for ez in (bz, bzf):
                        self._ajouter_coin(ex, ny, ez)
            for nz in (cz, zf):
                for ex in (bx, bxf):
                    for ey in (by, byf):
                        self._ajouter_coin(ex, ey, nz)

        # Pruning : coins désormais à l'intérieur de la nouvelle boîte
        self.coins -= {
            (px, py, pz) for px, py, pz in self.coins
            if cx + EPS < px < xf - EPS
            and cy + EPS < py < yf - EPS
            and cz + EPS < pz < zf - EPS
        }


def placer_item(item: Marchandise, wagons: list[Wagon]) -> None:
    """First-fit across wagons, best position within wagon (minimise volume restant)."""
    for w in wagons:
        best_local = None  # (remaining, coin, rotation)

        for coin in sorted(w.coins, key=lambda c: (c[2], c[0], c[1])):
            cx, cy, cz = coin
            for rL, rl, rH in item.rotations:
                if cx + rL <= L_WAG + EPS and cy + rl <= l_WAG + EPS and cz + rH <= H_WAG + EPS:
                    if not w.intersecte((cx, cy, cz, rL, rl, rH)):
                        if w.est_supportee(cx, cx + rL, cy, cy + rl, cz):
                            remaining = VOL_WAG - w.vol_used - rL * rl * rH
                            if best_local is None or remaining < best_local[0]:
                                best_local = (remaining, coin, (rL, rl, rH))

        if best_local is not None:
            _, coin, (rL, rl, rH) = best_local
            w.placer(coin, rL, rl, rH, item.id)
            return

    nw = Wagon()
    chosen = None
    for rL, rl, rH in item.rotations:
        if rL <= L_WAG + EPS and rl <= l_WAG + EPS and rH <= H_WAG + EPS:
            chosen = (rL, rl, rH)
            break
    if chosen is None:
        chosen = item.rotations[0]
    rL, rl, rH = chosen
    nw.boites.append((0.0, 0.0, 0.0, rL, rl, rH, item.id))
    nw.vol_used = rL * rl * rH
    nw.coins = {(rL, 0.0, 0.0), (0.0, rl, 0.0), (0.0, 0.0, rH)}
    wagons.append(nw)


def wagons_vers_boites(wagons: list[Wagon]) -> list[list[tuple]]:
    """Converts list of Wagon objects to list of boites lists for visualization."""
    return [list(w.boites) for w in wagons]


if __name__ == "__main__":
    print("=" * 65)
    print("  D3 ONLINE - EXTREME POINTS BEST-FIT LOCAL")
    print("=" * 65)

    marchandises = load_marchandises()
    if not marchandises:
        raise SystemExit("Erreur : Impossible de charger les données.")

    vol_total = sum(m['longueur'] * m['largeur'] * m['hauteur'] for m in marchandises)
    borne_inf = math.ceil(vol_total / VOL_WAG)

    print(f"Chargement : {len(marchandises)} marchandises chargées.")
    print(f"Volume total : {vol_total:.2f} m³ | Borne inférieure théorique : {borne_inf} wagons")
    print("-" * 65)

    items = [Marchandise(m) for m in marchandises]
    wagons: list[Wagon] = []

    t_debut = time.time()
    for item in items:
        placer_item(item, wagons)
    temps_total = time.time() - t_debut

    nb_wagons = len(wagons)
    volume_perdu = nb_wagons * VOL_WAG - vol_total

    print_results("d=3", "Online Extreme-Points Best-Fit Local", nb_wagons, volume_perdu, temps_total)

    # Visualisation
    wagons_boites = wagons_vers_boites(wagons)
    try:
        from d3_visualisation import visualiser_wagons
        output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rendus")
        os.makedirs(output_dir, exist_ok=True)
        visualiser_wagons(wagons_boites, output_dir=output_dir, prefix="online_wagon")
        print(f"Images sauvegardées dans : {output_dir}")
    except ImportError:
        print("d3_visualisation non disponible — visualisation ignorée.")

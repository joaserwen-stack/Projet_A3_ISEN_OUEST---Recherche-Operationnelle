"""
Visualisation 3D des wagons — génère une image PNG par wagon.

Format attendu pour wagons_boites:
    list[list[tuple]] où chaque tuple = (cx, cy, cz, rL, rl, rH, item_id)

Usage:
    from d3_visualisation import visualiser_wagons
    visualiser_wagons(wagons_boites, output_dir="rendus")
"""

import os
import colorsys
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

L_WAG, l_WAG, H_WAG = 11.583, 2.294, 2.569
VOL_WAG = L_WAG * l_WAG * H_WAG


def _couleur(item_id: int) -> tuple:
    """Deterministic HSV color from item ID."""
    golden = 0.618033988749895
    h = (item_id * golden) % 1.0
    r, g, b = colorsys.hsv_to_rgb(h, 0.65, 0.90)
    return (r, g, b)


def _dessiner_boite(ax, cx, cy, cz, rL, rl, rH, couleur, alpha=0.80):
    x, y, z = cx, cy, cz
    dx, dy, dz = rL, rl, rH
    verts = [
        [(x, y, z),       (x+dx, y, z),       (x+dx, y+dy, z),       (x, y+dy, z)],
        [(x, y, z+dz),    (x+dx, y, z+dz),    (x+dx, y+dy, z+dz),    (x, y+dy, z+dz)],
        [(x, y, z),       (x+dx, y, z),        (x+dx, y, z+dz),       (x, y, z+dz)],
        [(x, y+dy, z),    (x+dx, y+dy, z),     (x+dx, y+dy, z+dz),    (x, y+dy, z+dz)],
        [(x, y, z),       (x, y+dy, z),        (x, y+dy, z+dz),       (x, y, z+dz)],
        [(x+dx, y, z),    (x+dx, y+dy, z),     (x+dx, y+dy, z+dz),    (x+dx, y, z+dz)],
    ]
    poly = Poly3DCollection(verts, facecolors=couleur, linewidths=0.4,
                            edgecolors='#222222', alpha=alpha)
    ax.add_collection3d(poly)


def _dessiner_contour_wagon(ax):
    L, l, H = L_WAG, l_WAG, H_WAG
    kw = dict(color='#444444', linewidth=1.2, linestyle='--', alpha=0.6)
    # 4 arêtes basses
    ax.plot([0, L], [0, 0], [0, 0], **kw)
    ax.plot([L, L], [0, l], [0, 0], **kw)
    ax.plot([L, 0], [l, l], [0, 0], **kw)
    ax.plot([0, 0], [l, 0], [0, 0], **kw)
    # 4 arêtes hautes
    ax.plot([0, L], [0, 0], [H, H], **kw)
    ax.plot([L, L], [0, l], [H, H], **kw)
    ax.plot([L, 0], [l, l], [H, H], **kw)
    ax.plot([0, 0], [l, 0], [H, H], **kw)
    # 4 montants verticaux
    for xi, yi in [(0, 0), (L, 0), (L, l), (0, l)]:
        ax.plot([xi, xi], [yi, yi], [0, H], **kw)


def _etiquette_boite(ax, cx, cy, cz, rL, rl, rH, item_id):
    """Affiche l'ID au centre de la boîte si elle est assez grande."""
    if rL * rl * rH < 0.5:
        return
    ax.text(cx + rL / 2, cy + rl / 2, cz + rH / 2,
            str(item_id), fontsize=5, ha='center', va='center',
            color='#111111', fontweight='bold', zorder=10)


def visualiser_wagon(boites: list[tuple], num_wagon: int, nb_total: int,
                     output_path: str) -> None:
    """Génère et sauvegarde l'image 3D d'un wagon."""
    vol_occupe = sum(b[3] * b[4] * b[5] for b in boites)
    taux_remplissage = vol_occupe / VOL_WAG * 100

    fig = plt.figure(figsize=(12, 6))
    ax = fig.add_subplot(111, projection='3d')

    _dessiner_contour_wagon(ax)

    for b in boites:
        cx, cy, cz, rL, rl, rH, item_id = b
        couleur = _couleur(item_id)
        _dessiner_boite(ax, cx, cy, cz, rL, rl, rH, couleur)
        _etiquette_boite(ax, cx, cy, cz, rL, rl, rH, item_id)

    ax.set_xlim(0, L_WAG)
    ax.set_ylim(0, l_WAG)
    ax.set_zlim(0, H_WAG)
    ax.set_xlabel('X — Longueur (m)', fontsize=8, labelpad=6)
    ax.set_ylabel('Y — Largeur (m)', fontsize=8, labelpad=6)
    ax.set_zlabel('Z — Hauteur (m)', fontsize=8, labelpad=6)
    ax.set_box_aspect([L_WAG, l_WAG, H_WAG])
    ax.view_init(elev=22, azim=-50)
    ax.tick_params(labelsize=7)

    titre = (f"Wagon {num_wagon}/{nb_total}  —  "
             f"{len(boites)} colis  —  "
             f"{taux_remplissage:.1f}% plein\n"
             f"({vol_occupe:.2f} m³ / {VOL_WAG:.2f} m³)")
    ax.set_title(titre, fontsize=10, fontweight='bold', pad=10)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close(fig)


def visualiser_wagons(wagons_boites: list[list[tuple]],
                      output_dir: str = ".",
                      prefix: str = "wagon") -> None:
    """Génère une image PNG par wagon dans output_dir."""
    os.makedirs(output_dir, exist_ok=True)
    nb_total = len(wagons_boites)
    print(f"Génération de {nb_total} images...")

    for i, boites in enumerate(wagons_boites, start=1):
        filename = f"{prefix}_{i:02d}.png"
        path = os.path.join(output_dir, filename)
        visualiser_wagon(boites, num_wagon=i, nb_total=nb_total, output_path=path)
        vol_occupe = sum(b[3] * b[4] * b[5] for b in boites)
        taux = vol_occupe / VOL_WAG * 100
        print(f"  [{i:02d}/{nb_total}] {filename}  ({len(boites)} colis, {taux:.1f}% plein)")

    print("Visualisation terminée.")


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    from utils import load_marchandises
    from d3_online import Marchandise, Wagon, placer_item, wagons_vers_boites

    print("Chargement des marchandises et placement online...")
    marchandises = load_marchandises()
    items = [Marchandise(m) for m in marchandises]
    wagons: list[Wagon] = []
    for item in items:
        placer_item(item, wagons)

    wagons_boites = wagons_vers_boites(wagons)

    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rendus")
    visualiser_wagons(wagons_boites, output_dir=output_dir)
    print(f"Images dans : {output_dir}")

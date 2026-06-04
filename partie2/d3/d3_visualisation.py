import os
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

# --- CONSTANTES GÉOMÉTRIQUES DES CONTENEURS ---
# Dimensions des wagons standard de la SNCF données dans le sujet officiel
L_WAG, l_WAG, H_WAG = 11.583, 2.294, 2.569
VOL_WAG = L_WAG * l_WAG * H_WAG

# =====================================================================
# Écrit par : Joas
# =====================================================================


def _couleur(item_id: int) -> str:
    cmap = plt.get_cmap("tab20")
    # L'opérateur % permet de boucler proprement sur les 20 couleurs de la palette si l'ID est grand
    return cmap(item_id % 20)


def _dessiner_boite(ax, cx, cy, cz, rL, rl, rH, couleur, alpha=0.80):
    """
    Construit géométriquement un parallélépipède rectangle en 3D dans le repère Matplotlib.
    Génère les 6 faces de la boîte à partir de ses coordonnées d'origine et de ses dimensions de rotation.
    """
    x, y, z = cx, cy, cz
    dx, dy, dz = rL, rl, rH

    # Définition des coordonnées des sommets pour chacune des 6 faces du cube
    verts = [
        [(x, y, z),       (x+dx, y, z),       (x+dx, y+dy, z),       (x, y+dy, z)],       # Face Inférieure (Sol Zmin)
        [(x, y, z+dz),    (x+dx, y, z+dz),    (x+dx, y+dy, z+dz),    (x, y+dy, z+dz)],    # Face Supérieure (Toit Zmax)
        [(x, y, z),       (x+dx, y, z),        (x+dx, y, z+dz),       (x, y, z+dz)],       # Face Avant (Ymin)
        [(x, y+dy, z),    (x+dx, y+dy, z),     (x+dx, y+dy, z+dz),    (x, y+dy, z+dz)],    # Face Arrière (Ymax)
        [(x, y, z),       (x, y+dy, z),        (x, y+dy, z+dz),       (x, y, z+dz)],       # Face Gauche (Xmin)
        [(x+dx, y, z),    (x+dx, y+dy, z),     (x+dx, y+dy, z+dz),    (x+dx, y, z+dz)],    # Face Droite (Xmax)
    ]

    # Création de la collection 3D avec bordures foncées (#222222) pour détacher les colis les uns des autres
    poly = Poly3DCollection(verts, facecolors=couleur, linewidths=0.4,
                            edgecolors='#222222', alpha=alpha)
    ax.add_collection3d(poly)


def _dessiner_contour_wagon(ax):
    L, l, H = L_WAG, l_WAG, H_WAG
    # Style sobre : gris foncé, lignes fines et pointillés discontinus
    kw = dict(color='#444444', linewidth=1.2, linestyle='--', alpha=0.6)

    # Dessin des 4 arêtes du plancher (Z = 0)
    ax.plot([0, L], [0, 0], [0, 0], **kw)
    ax.plot([L, L], [0, l], [0, 0], **kw)
    ax.plot([L, 0], [l, l], [0, 0], **kw)
    ax.plot([0, 0], [l, 0], [0, 0], **kw)

    # Dessin des 4 arêtes du plafond (Z = H)
    ax.plot([0, L], [0, 0], [H, H], **kw)
    ax.plot([L, L], [0, l], [H, H], **kw)
    ax.plot([L, 0], [l, l], [H, H], **kw)
    ax.plot([0, 0], [l, 0], [H, H], **kw)

    # Dessin des 4 poteaux verticaux aux coins du wagon
    for xi, yi in [(0, 0), (L, 0), (L, l), (0, l)]:
        ax.plot([xi, xi], [yi, yi], [0, H], **kw)


def _etiquette_boite(ax, cx, cy, cz, rL, rl, rH, item_id):
    """
    Calcul topologique pour positionner le texte de l'ID au centre barycentrique du volume.
    Filtre les micro-colis (volume < 0.5 m³) pour éviter de surcharger et rendre le graphique illisible.
    """
    if rL * rl * rH < 0.5:
        return # Objet trop petit, on n'affiche pas l'étiquette pour préserver la clarté

    # Placement du texte aux coordonnées moyennes (milieu de la boîte)
    ax.text(cx + rL / 2, cy + rl / 2, cz + rH / 2,
            str(item_id), fontsize=5, ha='center', va='center',
            color='#111111', fontweight='bold', zorder=10)


def visualiser_wagon(boites: list[tuple], num_wagon: int, nb_total: int,
                     output_path: str) -> None:
    """
    Génère de toutes pièces la scène 3D pour un unique wagon donné.
    Calcule le taux de remplissage volumétrique réel et exporte l'image haute définition (DPI 150).
    """
    # Cumul du volume de tous les colis présents dans ce wagon spécifique
    vol_occupe = sum(b[3] * b[4] * b[5] for b in boites)
    taux_remplissage = vol_occupe / VOL_WAG * 100

    # Initialisation de la figure Matplotlib au format paysage (12x6)
    fig = plt.figure(figsize=(12, 6))
    ax = fig.add_subplot(111, projection='3d')

    # Tracé du cadre du wagon SNCF
    _dessiner_contour_wagon(ax)

    # Rendu individuel de chaque marchandise affectée au wagon
    for b in boites:
        cx, cy, cz, rL, rl, rH, item_id = b
        couleur = _couleur(item_id)
        _dessiner_boite(ax, cx, cy, cz, rL, rl, rH, couleur)
        _etiquette_boite(ax, cx, cy, cz, rL, rl, rH, item_id)

    # Configuration stricte des axes pour calquer le volume réel du wagon
    ax.set_xlim(0, L_WAG)
    ax.set_ylim(0, l_WAG)
    ax.set_zlim(0, H_WAG)

    # Légendes explicites demandées dans le cadre d'un projet d'ingénierie
    ax.set_xlabel('X — Longueur (m)', fontsize=8, labelpad=6)
    ax.set_ylabel('Y — Largeur (m)', fontsize=8, labelpad=6)
    ax.set_zlabel('Z — Hauteur (m)', fontsize=8, labelpad=6)

    # Ajustement des proportions de la boîte de visualisation pour éviter les distorsions d'échelle
    ax.set_box_aspect([L_WAG, l_WAG, H_WAG])

    # Orientation de la caméra de rendu pour une vue isométrique optimale du chargement
    ax.view_init(elev=22, azim=-50)
    ax.tick_params(labelsize=7)

    # Construction du titre dynamique avec statistiques d'occupation pour les diapositives du PowerPoint
    titre = (f"Wagon {num_wagon}/{nb_total}  —  "
             f"{len(boites)} colis  —  "
             f"{taux_remplissage:.1f}% plein\n"
             f"({vol_occupe:.2f} m³ / {VOL_WAG:.2f} m³)")
    ax.set_title(titre, fontsize=10, fontweight='bold', pad=10)

    # Optimisation des marges et sauvegarde physique du fichier image PNG
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close(fig) # Libération immédiate de la mémoire RAM


def visualiser_wagons(wagons_boites: list[list[tuple]],
                      output_dir: str = ".",
                      prefix: str = "wagon") -> None:
    """
    Point d'entrée principal du module.
    Prend la structure de données globale du colisage et boucle pour exporter un PNG par wagon.
    """
    # Création du dossier cible (ex: 'rendus') s'il n'existe pas encore sur le disque
    os.makedirs(output_dir, exist_ok=True)
    nb_total = len(wagons_boites)
    print(f"Génération de {nb_total} images...")

    # Parcours indexé de la flotte de wagons (départ à l'index 1 pour l'affichage humain)
    for i, boites in enumerate(wagons_boites, start=1):
        filename = f"{prefix}_{i:02d}.png" # Formatage propre (ex: wagon_01.png, wagon_02.png)
        path = os.path.join(output_dir, filename)

        # Lancement de la génération du graphique 3D
        visualiser_wagon(boites, num_wagon=i, nb_total=nb_total, output_path=path)

        # Log console en temps réel pour suivre l'avancement de la création des visuels
        vol_occupe = sum(b[3] * b[4] * b[5] for b in boites)
        taux = vol_occupe / VOL_WAG * 100
        print(f"  [{i:02d}/{nb_total}] {filename}  ({len(boites)} colis, {taux:.1f}% plein)")

    print("Visualisation terminée.")
import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import random

def dessiner_colis(ax, x, y, z, dx, dy, dz):
    """Dessine un parallélépipède 3D représentant un colis."""
    # Palette de couleurs pastels pour un rendu "pro"
    couleurs = ['#FF9999', '#66B2FF', '#99FF99', '#FFCC99', '#FF99FF', '#99FFFF', '#FFE5CC']
    couleur = random.choice(couleurs)

    sommets = np.array([
        [x, y, z], [x+dx, y, z], [x+dx, y+dy, z], [x, y+dy, z],
        [x, y, z+dz], [x+dx, y, z+dz], [x+dx, y+dy, z+dz], [x, y+dy, z+dz]
    ])
    
    faces = [
        [sommets[0], sommets[1], sommets[2], sommets[3]], # Bas
        [sommets[4], sommets[5], sommets[6], sommets[7]], # Haut
        [sommets[0], sommets[1], sommets[5], sommets[4]], # Devant
        [sommets[2], sommets[3], sommets[7], sommets[6]], # Derrière
        [sommets[1], sommets[2], sommets[6], sommets[5]], # Droite
        [sommets[0], sommets[3], sommets[7], sommets[4]]  # Gauche
    ]
    
    # Ajout du bloc (alpha=0.9 pour une très légère transparence)
    ax.add_collection3d(Poly3DCollection(faces, facecolors=couleur, linewidths=1.5, edgecolors='black', alpha=0.9))


def generer_simulation_3d_animee(objets_du_wagon):
    """Génère l'animation 3D du wagon se remplissant colis par colis."""
    # On calcule dynamiquement les dimensions de la boîte pour un affichage parfait
    LONGUEUR_WAGON = max(11.583, max([obj['x'] + obj['longueur'] for obj in objets_du_wagon]))
    LARGEUR_WAGON = max(2.294, max([obj['y'] + obj['largeur'] for obj in objets_du_wagon]))
    HAUTEUR_WAGON = 2.569

    plt.ion() # Mode interactif ON
    fig = plt.figure(figsize=(10, 7))
    ax = fig.add_subplot(111, projection='3d')

    # 1. Dessiner le contour du wagon (Boîte transparente)
    ax.plot([0, LONGUEUR_WAGON, LONGUEUR_WAGON, 0, 0], [0, 0, LARGEUR_WAGON, LARGEUR_WAGON, 0], [0, 0, 0, 0, 0], color='black', linewidth=1, linestyle='--')
    ax.plot([0, LONGUEUR_WAGON, LONGUEUR_WAGON, 0, 0], [0, 0, LARGEUR_WAGON, LARGEUR_WAGON, 0], [HAUTEUR_WAGON]*5, color='black', linewidth=1, linestyle='--')
    for i in [0, LONGUEUR_WAGON]:
        for j in [0, LARGEUR_WAGON]:
            ax.plot([i, i], [j, j], [0, HAUTEUR_WAGON], color='black', linewidth=1, linestyle='--')

    ax.set_xlim([0, LONGUEUR_WAGON])
    ax.set_ylim([0, LARGEUR_WAGON])
    ax.set_zlim([0, HAUTEUR_WAGON])
    ax.set_xlabel('Longueur (X)')
    ax.set_ylabel('Largeur (Y)')
    ax.set_zlabel('Hauteur (Z)')
    
    # Angle de vue optimisé pour voir l'intérieur du chargement
    ax.set_box_aspect([LONGUEUR_WAGON, LARGEUR_WAGON, HAUTEUR_WAGON])
    ax.view_init(elev=25, azim=-55)

    # 2. Remplissage animé (Chaque boîte s'ajoute l'une après l'autre)
    for i, obj in enumerate(objets_du_wagon):
        dessiner_colis(ax, obj['x'], obj['y'], obj['z'], obj['longueur'], obj['largeur'], obj['hauteur'])
        ax.set_title(f"Métaheuristique 3D : Placement du colis {i+1}/{len(objets_du_wagon)}\n(Wagon Optimisé n°1)", fontsize=14, fontweight='bold')
        
        plt.pause(0.5) # Pause d'une demi-seconde pour apprécier l'empilement

    plt.ioff() # Mode interactif OFF
    plt.tight_layout()
    plt.savefig("rendu_wagon_3d.png", dpi=300) # Sauvegarde l'image haute qualité
    plt.show() # Garde la fenêtre ouverte à la fin

# ==========================================
# DONNÉES EXACTES DU WAGON 1 (Générées par ton IA)
# ==========================================
if __name__ == "__main__":
    
    donnees_wagon_1 = [
        {'id': 51, 'x': 0.0, 'y': 0.0, 'z': 0.0, 'longueur': 2.2, 'largeur': 6.1, 'hauteur': 2.3},
        {'id': 31, 'x': 2.2, 'y': 0.0, 'z': 0.0, 'longueur': 6.0, 'largeur': 1.9, 'hauteur': 1.6},
        {'id': 73, 'x': 2.2, 'y': 0.0, 'z': 1.6, 'longueur': 5.0, 'largeur': 0.6, 'hauteur': 0.5},
        {'id': 32, 'x': 8.2, 'y': 0.0, 'z': 0.0, 'longueur': 3.0, 'largeur': 2.2, 'hauteur': 2.2},
        {'id': 46, 'x': 2.2, 'y': 0.6, 'z': 1.6, 'longueur': 4.2, 'largeur': 1.5, 'hauteur': 0.8},
    ]
    
    print("Lancement de la modélisation 3D...")
    generer_simulation_3d_animee(donnees_wagon_1)
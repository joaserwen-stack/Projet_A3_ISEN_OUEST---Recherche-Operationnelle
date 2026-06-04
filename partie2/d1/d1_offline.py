import time
from utils import load_marchandises, print_results

# =====================================================================
# Écrit par : Thomas
# =====================================================================

# Longueur maximale utile d'un wagon standard en mètres
WAGON_MAX_LENGTH = 11.583

def first_fit_decreasing(marchandises):
    # Tri préalable des marchandises de la plus grande à la plus petite longueur (principe du mode Offline)
    marchandises_triees = sorted(marchandises, key=lambda x: x['longueur'], reverse=True)
    wagons = [] # Stocke l'espace linéaire restant dans chaque wagon ouvert
    wagons_content = [] # Stocke la liste des objets placés dans chaque wagon

    # Rangement séquentiel des marchandises triées
    for item in marchandises_triees:
        placed = False

        # On cherche le tout premier wagon ouvert possédant assez d'espace libre
        for i in range(len(wagons)):
            if wagons[i] >= item['longueur']:
                wagons[i] -= item['longueur']  # Déduction de la longueur de la marchandise
                wagons_content[i].append(item)
                placed = True
                break

        # Si l'objet ne rentre nulle part, on ouvre un nouveau wagon configuré avec l'espace restant
        if not placed:
            wagons.append(WAGON_MAX_LENGTH - item['longueur'])
            wagons_content.append([item])

    return wagons, wagons_content

def best_fit_decreasing(marchandises):
    # Tri préalable des marchandises par ordre décroissant de longueur
    marchandises_triees = sorted(marchandises, key=lambda x: x['longueur'], reverse=True)
    wagons = []
    wagons_content = []

    for item in marchandises_triees:
        best_idx = -1
        # Initialisation avec une valeur théorique maximale pour la recherche de l'espace minimal restant
        min_remaining_space = WAGON_MAX_LENGTH + 1

        # Best-fit
        # On parcourt tous les wagons ouverts pour trouver celui qui minimisera le vide résiduel après placement
        for i in range(len(wagons)):
            if wagons[i] >= item['longueur']:
                remaining_space_after = wagons[i] - item['longueur']
                # On mémorise l'index du wagon si le trou restant après insertion est le plus petit trouvé
                if remaining_space_after < min_remaining_space:
                    min_remaining_space = remaining_space_after
                    best_idx = i

        # Si un wagon optimal a été identifié, on valide le placement dedans
        if best_idx != -1:
            wagons[best_idx] -= item['longueur']
            wagons_content[best_idx].append(item)
        else:
            # Sinon, ouverture d'un nouveau wagon
            wagons.append(WAGON_MAX_LENGTH - item['longueur'])
            wagons_content.append([item])

    return wagons, wagons_content

if __name__ == "__main__":
    print("d=1 Offline First-fit")

    items = load_marchandises()
    print(f"Nombre de marchandises chargées : {len(items)}")

    if items:
        # --- Évaluation des performances du First-Fit Decreasing ---
        start_time = time.time()
        remains, content = first_fit_decreasing(items)
        temps = time.time() - start_time

        nb_wagons = len(remains)
        total_unused_length = sum(remains)

        print_results(dimension_label="d=1", mode_label="Offline", nb_wagons=nb_wagons, total_unused=total_unused_length, execution_time=temps)

        print("Détails du remplissage des premiers wagons :")
        for idx in range(min(5, nb_wagons)):
            print(f"  Wagon {idx + 1} (Espace restant : {remains[idx]:.3f}m) :")
            for obj in content[idx]:
                print(f"    - ID {obj['id']}: {obj['nom']} (L={obj['longueur']}m)")


        print("\n\nd=1 Offline Best-fit")
        # --- Évaluation des performances du Best-Fit Decreasing ---
        start_time = time.time()
        remains_bf, content_bf = best_fit_decreasing(items)
        temps = time.time() - start_time

        nb_wagons_bf = len(remains_bf)
        total_unused_length_bf = sum(remains_bf)

        print_results(dimension_label="d=1", mode_label="Offline (Best-Fit)", nb_wagons=nb_wagons_bf, total_unused=total_unused_length_bf, execution_time=temps)

        print("Détails du remplissage des premiers wagons (Best-Fit) :")
        for idx in range(min(5, nb_wagons_bf)):
            print(f"  Wagon {idx + 1} (Espace restant : {remains_bf[idx]:.3f}m) :")
            for obj in content_bf[idx]:
                print(f"    - ID {obj['id']}: {obj['nom']} (L={obj['longueur']}m)")
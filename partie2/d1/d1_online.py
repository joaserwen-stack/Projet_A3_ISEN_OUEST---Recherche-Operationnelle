import time
from utils import load_marchandises, print_results

# =====================================================================
# Écrit par : Joas
# =====================================================================


# Longueur maximale utile d'un wagon en mètres
WAGON_MAX_LENGTH = 11.583

def first_fit_online(marchandises):
    wagons = []
    wagons_content = []

    # Traitement des marchandises dans leur ordre strict d'arrivée (contrainte du mode Online)
    for item in marchandises:
        placed = False

        # Recherche du premier wagon ouvert capable d'accueillir la marchandise
        for i in range(len(wagons)):
            if wagons[i] >= item['longueur']:
                wagons[i] -= item['longueur']  # Mise à jour de l'espace résiduel
                wagons_content[i].append(item)
                placed = True
                break

        # Si l'élément ne rentre dans aucun conteneur existant, on en ouvre un nouveau
        if not placed:
            wagons.append(WAGON_MAX_LENGTH - item['longueur'])
            wagons_content.append([item])

    return wagons, wagons_content

def best_fit_online(marchandises):
    wagons = []
    wagons_content = []

    # On traite chaque élément au fil de l'eau sans aucune connaissance des suivants
    for item in marchandises:
        best_idx = -1
        min_remaining_space = WAGON_MAX_LENGTH + 1  # Borne supérieure théorique pour l'optimisation

        # --- Logique Best-Fit ---
        # Parcours de tous les wagons actifs pour dénicher celui qui optimisera le remplissage (espace perdu minimal)
        for i in range(len(wagons)):
            if wagons[i] >= item['longueur']:
                remaining_space_after = wagons[i] - item['longueur']
                # On retient le wagon si l'espace vide restant après insertion est le plus petit constaté
                if remaining_space_after < min_remaining_space:
                    min_remaining_space = remaining_space_after
                    best_idx = i

        # Si un wagon adéquat a été trouvé, on y valide l'insertion
        if best_idx != -1:
            wagons[best_idx] -= item['longueur']
            wagons_content[best_idx].append(item)
        else:
            # Sinon, on crée un nouveau wagon pour y loger l'élément
            wagons.append(WAGON_MAX_LENGTH - item['longueur'])
            wagons_content.append([item])

    return wagons, wagons_content

if __name__ == "__main__":
    print("d=1 Online First-fit")

    items = load_marchandises()
    print(f"Nombre de marchandises chargées : {len(items)}")

    if items:
        # --- Évaluation du First-Fit Online ---
        start_time = time.time()
        remains, content = first_fit_online(items)
        temps = time.time() - start_time

        nb_wagons = len(remains)
        total_unused_length = sum(remains)

        print_results(dimension_label="d=1", mode_label="Online First-fit", nb_wagons=nb_wagons, total_unused=total_unused_length, execution_time=temps)

        print("Détails du remplissage des premiers wagons :")
        for idx in range(min(5, nb_wagons)):
            print(f"  Wagon {idx + 1} (Espace restant : {remains[idx]:.3f}m) :")
            for obj in content[idx]:
                print(f"    - ID {obj['id']}: {obj['nom']} (L={obj['longueur']}m)")


        print("\n\nd=1 Online Best-fit")
        # --- Évaluation du Best-Fit Online ---
        start_time = time.time()
        remains_bf, content_bf = best_fit_online(items)
        temps = time.time() - start_time

        nb_wagons_bf = len(remains_bf)
        total_unused_length_bf = sum(remains_bf)

        print_results(dimension_label="d=1", mode_label="Online Best-fit", nb_wagons=nb_wagons_bf, total_unused=total_unused_length_bf, execution_time=temps)

        print("Détails du remplissage des premiers wagons :")
        for idx in range(min(5, nb_wagons_bf)):
            print(f"  Wagon {idx + 1} (Espace restant : {remains_bf[idx]:.3f}m) :")
            for obj in content_bf[idx]:
                print(f"    - ID {obj['id']}: {obj['nom']} (L={obj['longueur']}m)")
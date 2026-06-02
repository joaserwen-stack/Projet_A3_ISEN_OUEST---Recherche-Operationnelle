import time
from utils import load_marchandises, print_results

WAGON_MAX_LENGTH = 11.583

def first_fit_online(marchandises):
    wagons = []
    wagons_content = []

    # Rangement des marchandises une par une
    for item in marchandises: # On traite les marchandises dans l'ordre d'arrivée (online)
        placed = False 

        # On parcourt les wagons existants pour trouver le premier qui a assez de place
        for i in range(len(wagons)):
            if wagons[i] >= item['longueur']:
                wagons[i] -= item['longueur']  # On met à jour l'espace restant
                wagons_content[i].append(item) # On ajoute l'objet au wagon
                placed = True
                break

        # Si aucun wagon n'a assez de place, on en ouvre un nouveau
        if not placed:
            wagons.append(WAGON_MAX_LENGTH - item['longueur'])
            wagons_content.append([item])

    return wagons, wagons_content

def best_fit_online(marchandises):
    wagons = []
    wagons_content = []

    for item in marchandises:
        best_idx = -1
        min_remaining_space = WAGON_MAX_LENGTH + 1  # Initialisé à une valeur max impossible

        # On parcourt tous les wagons pour trouver celui qui laissera le moins d'espace vide
        for i in range(len(wagons)):
            if wagons[i] >= item['longueur']:
                remaining_space_after = wagons[i] - item['longueur']
                if remaining_space_after < min_remaining_space:
                    min_remaining_space = remaining_space_after
                    best_idx = i

        # Si on a trouvé un wagon optimal, on place la marchandise dedans
        if best_idx != -1:
            wagons[best_idx] -= item['longueur']
            wagons_content[best_idx].append(item)
        else:
            # Sinon on ouvre un nouveau wagon
            wagons.append(WAGON_MAX_LENGTH - item['longueur'])
            wagons_content.append([item])

    return wagons, wagons_content

if __name__ == "__main__":
    print("d=1 Online First-fit")

    items = load_marchandises()
    print(f"Nombre de marchandises chargées : {len(items)}")

    if items:
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
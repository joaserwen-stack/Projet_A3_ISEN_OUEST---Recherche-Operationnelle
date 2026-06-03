import csv
import os

def load_marchandises(csv_filename="Données_marchandises.csv"):
    # Résolution dynamique du chemin pour pointer vers le dossier 'data' à la racine
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    csv_path = os.path.join(project_root, "data", csv_filename)

    marchandises = []

    with open(csv_path, mode='r', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter=',')

        for row in reader:
            if not row:
                continue

            try:
                marchandises.append({
                    'id': int(row[0]),
                    'nom': row[1].strip(),
                    'longueur': float(row[2]),
                    'largeur': float(row[3]),
                    'hauteur': float(row[4]),
                    'retournable': int(row[5]) if len(row) > 5 else 1
                })
            except (ValueError, IndexError) as e:
                continue

    return marchandises

def print_results(dimension_label, mode_label, nb_wagons, total_unused, execution_time):
    avg_unused = total_unused / nb_wagons if nb_wagons > 0 else 0

    print(f"\n{dimension_label} {mode_label}")
    print(f"Nombre de wagons nécessaires : {nb_wagons}")
    print(f"Dimension non occupée totale : {total_unused:.3f} m")
    print(f"Espace vide moyen par wagon : {avg_unused:.3f} m")
    print(f"Temps de calcul : {execution_time:.6f} secondes")
    print("\n")
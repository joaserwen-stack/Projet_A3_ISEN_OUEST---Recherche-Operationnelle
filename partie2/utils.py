import csv
import os
import time
import matplotlib.pyplot as plt

# Dimensions wagon standard (partagées par tous les modules)
WAGON_L = 11.583  # longueur (m)
WAGON_l = 2.294   # largeur (m)
WAGON_H = 2.569   # hauteur (m)

# Paramètres benchmark complexité
TAILLES_N = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
N_TRIALS = 5


def load_marchandises(csv_filename="Données_marchandises.csv"):
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
            except (ValueError, IndexError):
                continue
    return marchandises


def print_results(dimension_label, mode_label, nb_wagons, total_unused, execution_time):
    avg_unused = total_unused / nb_wagons if nb_wagons > 0 else 0
    print(f"\n{dimension_label} {mode_label}")
    print(f"Nombre de wagons nécessaires : {nb_wagons}")
    print(f"Dimension non occupée totale : {total_unused:.3f} m")
    print(f"Espace vide moyen par wagon : {avg_unused:.3f} m")
    print(f"Temps de calcul : {execution_time:.6f} secondes")
    print()


def mesurer(fn, data, n_trials=N_TRIALS):
    """Temps moyen d'exécution de fn(data) sur n_trials itérations."""
    t = 0
    for _ in range(n_trials):
        s = time.perf_counter()
        fn(data)
        t += time.perf_counter() - s
    return t / n_trials


def plot_complexite(tailles, temps_on, temps_off, titre, label_on, label_off, fichier):
    """Génère et sauvegarde la courbe online vs offline."""
    plt.figure(figsize=(10, 6))
    plt.plot(tailles, temps_on, 'o-', label=label_on)
    plt.plot(tailles, temps_off, 's-', label=label_off)
    plt.title(titre)
    plt.xlabel("Nombre de marchandises (n)")
    plt.ylabel("Temps de calcul (s)")
    plt.legend()
    plt.grid(True, linestyle=':', alpha=0.6)
    plt.tight_layout()
    plt.savefig(fichier, dpi=150)
    plt.close()
    print(f"Graphique sauvegardé : {fichier}")

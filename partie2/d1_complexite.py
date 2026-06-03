import time
import matplotlib.pyplot as plt
from utils import load_marchandises

from d1_online import first_fit_online
from d1_offline import first_fit_decreasing

def evaluer_complexite():
    items = load_marchandises()
    if not items:
        return

    # Liste des tailles d'échantillons à tester (N de 10 à 100)
    tailles_n = list(range(10, len(items) + 1, 10))

    temps_online = []
    temps_offline = []

    print("--- Début des mesures de temps ---")
    for n in tailles_n:
        sub_items = items[:n] # On extrait les N premières marchandises

        # Mesure pour le mode Online First-Fit
        start = time.perf_counter()
        first_fit_online(sub_items)
        end = time.perf_counter()
        temps_online.append(end - start)

        # Mesure pour le mode Offline First-Fit
        start = time.perf_counter()
        first_fit_decreasing(sub_items)
        end = time.perf_counter()
        temps_offline.append(end - start)

        print(f"Taille N = {n:3d} | Temps Online: {temps_online[-1]:.6f}s | Temps Offline: {temps_offline[-1]:.6f}s")

    plt.figure(figsize=(10, 6))

    # Tracé des courbes
    plt.plot(tailles_n, temps_online, label="First-Fit Online", marker="o", color='blue')
    plt.plot(tailles_n, temps_offline, label="First-Fit Decreasing (Offline)", marker="o", color='orange')

    # Habillage du graphique
    plt.title("Évolution du temps de calcul en fonction du nombre de marchandises (d=1)")
    plt.xlabel("Nombre de marchandises")
    plt.ylabel("Temps de calcul s")
    plt.grid(True)
    plt.legend()

    plt.savefig("courbe_complexite_d1.png", dpi=300)
    plt.show()

if __name__ == "__main__":
    evaluer_complexite()
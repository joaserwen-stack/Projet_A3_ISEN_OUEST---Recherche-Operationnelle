import time
import copy
import matplotlib.pyplot as plt
from utils import load_marchandises

# On importe les algorithmes depuis tes fichiers 2D
# (Assure-toi que les noms de fichiers "d2_online" et "d2_offline" correspondent bien à tes vrais fichiers)
from d2_online import remplir_wagons as remplir_wagons_online
from d2_offline import remplir_wagons as remplir_wagons_offline

def evaluer_complexite_2d():
    items = load_marchandises()
    if not items:
        return

    # Liste des tailles d'échantillons à tester (N de 10 à 100)
    tailles_n = list(range(10, len(items) + 1, 10))

    temps_online = []
    temps_offline = []

    print("--- Début des mesures de temps (Dimension 2) ---")
    for n in tailles_n:
        # On utilise deepcopy car le MaxRects ajoute des clés ('x', 'y') dans les objets
        # On veut que l'Offline et l'Online démarrent avec des objets vierges
        sub_items_online = copy.deepcopy(items[:n])
        sub_items_offline = copy.deepcopy(items[:n])

        # Mesure pour le mode Online MaxRects
        start = time.perf_counter()
        remplir_wagons_online(sub_items_online)
        end = time.perf_counter()
        temps_online.append(end - start)

        # Mesure pour le mode Offline MaxRects
        start = time.perf_counter()
        remplir_wagons_offline(sub_items_offline)
        end = time.perf_counter()
        temps_offline.append(end - start)

        print(f"Taille N = {n:3d} | Temps Online: {temps_online[-1]:.6f}s | Temps Offline: {temps_offline[-1]:.6f}s")

    plt.figure(figsize=(10, 6))

    # Tracé des courbes
    plt.plot(tailles_n, temps_online, label="MaxRects BLSF (Online)", marker="o", color='blue')
    plt.plot(tailles_n, temps_offline, label="MaxRects BSSF (Offline)", marker="o", color='orange')

    # Habillage du graphique
    plt.title("Évolution du temps de calcul en fonction du nombre de marchandises (d=2)")
    plt.xlabel("Nombre de marchandises")
    plt.ylabel("Temps de calcul s")
    plt.grid(True)
    plt.legend()

    # Sauvegarde automatique
    plt.savefig("courbe_complexite_d2.png", dpi=300)
    plt.show()

if __name__ == "__main__":
    evaluer_complexite_2d()
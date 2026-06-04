import time
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import matplotlib.pyplot as plt
from utils import load_marchandises
from d3_online import Marchandise, Wagon, placer_item
from d3_offline import Marchandise as MarchandiseOffline, evaluer_liste

TAILLES_N = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
N_TRIALS = 5


def run_online(marchandises):
    items = [Marchandise(m) for m in marchandises]
    wagons = []
    for item in items:
        placer_item(item, wagons)
    return wagons


def run_offline(marchandises):
    dict_items = {m['id']: MarchandiseOffline(m) for m in marchandises}
    # Ordre volume décroissant — seed heuristique du GA (sans les 300s d'évolution)
    ids = sorted(dict_items, key=lambda i: dict_items[i].rotations[0][0]
                 * dict_items[i].rotations[0][1]
                 * dict_items[i].rotations[0][2], reverse=True)
    return evaluer_liste(ids, dict_items, float('inf'))


def mesurer(fn, data):
    t = 0
    for _ in range(N_TRIALS):
        s = time.perf_counter()
        fn(data)
        t += time.perf_counter() - s
    return t / N_TRIALS


if __name__ == "__main__":
    marchandises = load_marchandises()
    temps_online, temps_offline = [], []

    print(f"{'n':<6} {'Online (s)':<15} {'Offline (s)':<15}")
    for n in TAILLES_N:
        sample = marchandises[:n]
        t_on = mesurer(run_online, sample)
        t_off = mesurer(run_offline, sample)
        temps_online.append(t_on)
        temps_offline.append(t_off)
        print(f"{n:<6} {t_on:<15.6f} {t_off:<15.6f}")

    plt.figure(figsize=(10, 6))
    plt.plot(TAILLES_N, temps_online, 'o-', label='Online (Extreme Points Best-Fit)')
    plt.plot(TAILLES_N, temps_offline, 's-', label='Offline (Corner Points — seed GA)')
    plt.title("D=3 : Temps d'exécution en fonction du nombre de marchandises")
    plt.xlabel("Nombre de marchandises (n)")
    plt.ylabel("Temps de calcul (s)")
    plt.legend()
    plt.grid(True, linestyle=':', alpha=0.6)
    plt.tight_layout()
    plt.savefig("courbe_complexite_d3.png", dpi=150)
    print("Graphique sauvegardé : courbe_complexite_d3.png")

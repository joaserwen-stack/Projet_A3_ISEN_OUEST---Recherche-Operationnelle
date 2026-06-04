import time
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import matplotlib.pyplot as plt
from utils import load_marchandises
from d1_online import first_fit_online
from d1_offline import first_fit_decreasing

TAILLES_N = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
N_TRIALS = 5


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
        t_on = mesurer(first_fit_online, sample)
        t_off = mesurer(first_fit_decreasing, sample)
        temps_online.append(t_on)
        temps_offline.append(t_off)
        print(f"{n:<6} {t_on:<15.6f} {t_off:<15.6f}")

    plt.figure(figsize=(10, 6))
    plt.plot(TAILLES_N, temps_online, 'o-', label='Online (First-Fit)')
    plt.plot(TAILLES_N, temps_offline, 's-', label='Offline (First-Fit Decreasing)')
    plt.title("D=1 : Temps d'exécution en fonction du nombre de marchandises")
    plt.xlabel("Nombre de marchandises (n)")
    plt.ylabel("Temps de calcul (s)")
    plt.legend()
    plt.grid(True, linestyle=':', alpha=0.6)
    plt.tight_layout()
    plt.savefig("courbe_complexite_d1.png", dpi=150)
    print("Graphique sauvegardé : courbe_complexite_d1.png")

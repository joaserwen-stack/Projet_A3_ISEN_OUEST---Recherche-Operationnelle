import sys
import os
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.dirname(_HERE))

from utils import load_marchandises, mesurer, plot_complexite, TAILLES_N
from d1_online import first_fit_online
from d1_offline import first_fit_decreasing

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

    plot_complexite(
        TAILLES_N, temps_online, temps_offline,
        titre="D=1 : Temps d'exécution en fonction du nombre de marchandises",
        label_on="Online (First-Fit)",
        label_off="Offline (First-Fit Decreasing)",
        fichier="courbe_complexite_d1.png",
    )

import sys
import os
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.dirname(_HERE))

from utils import load_marchandises, mesurer, plot_complexite, TAILLES_N
from d2_online import remplir_wagons as remplir_wagons_online
from d2_offline import remplir_wagons as remplir_wagons_offline

if __name__ == "__main__":
    marchandises = load_marchandises()
    temps_online, temps_offline = [], []

    print(f"{'n':<6} {'Online (s)':<15} {'Offline (s)':<15}")
    for n in TAILLES_N:
        sample = marchandises[:n]
        t_on = mesurer(remplir_wagons_online, sample)
        t_off = mesurer(remplir_wagons_offline, sample)
        temps_online.append(t_on)
        temps_offline.append(t_off)
        print(f"{n:<6} {t_on:<15.6f} {t_off:<15.6f}")

    plot_complexite(
        TAILLES_N, temps_online, temps_offline,
        titre="D=2 : Temps d'exécution en fonction du nombre de marchandises",
        label_on="Online (MaxRects BLSF)",
        label_off="Offline (MaxRects BSSF Décroissant)",
        fichier="courbe_complexite_d2.png",
    )

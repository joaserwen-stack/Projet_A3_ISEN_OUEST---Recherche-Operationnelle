import sys
import os
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.dirname(_HERE))

from utils import load_marchandises, mesurer, plot_complexite, TAILLES_N
from d3_online import Marchandise, Wagon, placer_item
from d3_offline import Marchandise as MarchandiseOffline, evaluer_liste


def run_online(marchandises):
    items = [Marchandise(m) for m in marchandises]
    wagons = []
    for item in items:
        placer_item(item, wagons)
    return wagons


def run_offline(marchandises):
    dict_items = {m['id']: MarchandiseOffline(m) for m in marchandises}
    ids = sorted(dict_items, key=lambda i: dict_items[i].rotations[0][0]
                 * dict_items[i].rotations[0][1]
                 * dict_items[i].rotations[0][2], reverse=True)
    return evaluer_liste(ids, dict_items, float('inf'))


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

    plot_complexite(
        TAILLES_N, temps_online, temps_offline,
        titre="D=3 : Temps d'exécution en fonction du nombre de marchandises",
        label_on="Online (Extreme Points Best-Fit)",
        label_off="Offline (Corner Points — seed GA)",
        fichier="courbe_complexite_d3.png",
    )

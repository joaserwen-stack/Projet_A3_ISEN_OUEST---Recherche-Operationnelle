import time
from data.objets import objets
from partie1.q5_glouton import glouton

C = 0.6
n = [1, 2, 5, 10, 15, 23]

for i in n:
    debut = time.time()
    sac = glouton(objets[:i], i, C)
    fin = time.time()

    T = fin - debut
    print(f"n={i}  temps={T:.10f} secondes")
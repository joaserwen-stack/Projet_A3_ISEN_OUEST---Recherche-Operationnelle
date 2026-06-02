import time
from data.objets import objets
from partie1.q5_glouton import glouton
from partie1.q8_9_Forcebrute import sac_a_dos_exact

C = 0.6
n = [1, 2, 5, 10, 15, 23]

for i in n:
    debut = time.time()
    sac = glouton(objets[:i], i, C)
    fin = time.time()

    T = fin - debut
    print(f"n={i}  temps={T:.10f} secondes")



print("--- 2. Lancement de l'Algorithme Exact (Force Brute) ---")
print("(Attente...)")

debut_force = time.time()
sac_joas, utilite_joas = sac_a_dos_exact(C)
fin_force = time.time()

temps_force = round(fin_force - debut_force, 2)

print(f"Utilité maximale trouvée : {utilite_joas}")
print(f"Temps de calcul        : {temps_force} secondes")
print("Objets embarqués :")
for nom in sac_joas:
    print(f" - {nom}")

print("\n" + "="*60 + "\n")
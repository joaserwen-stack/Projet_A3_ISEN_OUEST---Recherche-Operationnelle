import random
import math
from data.objets import objets
import time

# =====================================================================
# Écrit par : Thomas
# =====================================================================

def evaluer_solution(solution, masses, utilites, C):
    poids, utilite = 0, 0
    # On parcourt le vecteur binaire pour sommer les masses et utilités des objets embarqués
    for s, m, u in zip(solution, masses, utilites):
        if s == 1:
            poids += m
            utilite += u

    # Si le sac déborde, la solution est invalide et reçoit un score de 0 pour être rejetée
    return utilite if poids <= C else 0


def recuit_simule(objets, C, T=100.0, T_min=0.01, alpha=0.99, nb_iter=100):
    n = len(objets)
    masses = [o["masse"] for o in objets]
    utilites = [o["utilite"] for o in objets]

    # Génération d'une solution de départ 100% aléatoire (vecteur de 0 et de 1)
    solution = [random.randint(0, 1) for _ in range(n)]
    score = evaluer_solution(solution, masses, utilites, C)

    meilleure_sol, meilleur_score = solution.copy(), score

    # La boucle principale tourne tant que le système n'a pas refroidi
    while T > T_min:
        # Exploration du voisinage à une température fixe
        for _ in range(nb_iter):
            candidat = solution.copy()
            i = random.randrange(n)
            # Inversion d'un bit au hasard pour créer une solution voisine (on prend ou on pose un objet)
            candidat[i] = 1 - candidat[i]

            score_cand = evaluer_solution(candidat, masses, utilites, C)

            # Si le voisin est meilleur, on l'accepte directement.
            # S'il est moins bon, on calcule une probabilité d'acceptation limite avec math.exp(...) qui donne une valeur entre 0 et 1.
            # random.random() génère alors un nombre aléatoire entre 0 et 1 :
            # - Si ce nombre est inférieur à la limite calculée, on valide l'erreur (on accepte une moins bonne solution).
            # - Plus la température T est haute, plus la limite est proche de 1, et plus random.random() a de chances de valider l'erreur.
            if score_cand > score or random.random() < math.exp((score_cand - score) / T):
                solution, score = candidat, score_cand

                # Sauvegarde en mémoire du meilleur résultat absolu croisé pendant la recherche
                if score > meilleur_score:
                    meilleure_sol, meilleur_score = solution.copy(), score

        # Refroidissement géométrique du système
        # Plus la température baisse, plus la probabilité d'accepter une mauvaise solution diminue
        T *= alpha

    return meilleure_sol, meilleur_score

if __name__ == "__main__":
    # Test de la méta-heuristique sur différentes capacités du sac
    for C in [0.6, 2, 3, 4, 5]:

        debut = time.time()
        solution, score = recuit_simule(objets, C)
        temps_calcul = time.time() - debut

        print(f"\n--- Résultat pour C = {C} ---")
        poids_total = 0
        composition = []

        # Reconstruction de la liste des objets retenus pour l'affichage final
        for s, o in zip(solution, objets):
            if s:
                composition.append(o['nom'])
                poids_total += o["masse"]

        print(f"Composition du sac : {', '.join(composition)}")
        print(f"Poids total embarqué : {poids_total} kg")
        print(f"Utilité totale : {score}")
        print(f"Temps de calcul : {temps_calcul:.6f} secondes")
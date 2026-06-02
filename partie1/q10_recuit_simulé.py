import random
import math
from data.objets import objets
import time

# Thomas

def evaluer_solution(solution, masses, utilites, C):
    poids, utilite = 0, 0
    for s, m, u in zip(solution, masses, utilites):
        if s == 1:
            poids += m
            utilite += u

    # Si la contrainte de capacité est respectée la solution est valide
    # Sinon on retourne 0 pour rejeter cette solution
    return utilite if poids <= C else 0


def recuit_simule(objets, C, T=100.0, T_min=0.01, alpha=0.99, nb_iter=100):
    n = len(objets)
    masses = [o["masse"] for o in objets]
    utilites = [o["utilite"] for o in objets]

    # Solution initiale totalement aléatoire
    solution = [random.randint(0, 1) for _ in range(n)]
    score = evaluer_solution(solution, masses, utilites, C)

    meilleure_sol, meilleur_score = solution.copy(), score

    while T > T_min:
        # Palier de température : on explore le voisinage nb_iter fois
        for _ in range(nb_iter):
            # Générer un voisin
            candidat = solution.copy()
            i = random.randrange(n)
            # On modifie un seul élément au hasard : s'il était à 1 il passe à 0, et inversement
            candidat[i] = 1 - candidat[i]

            score_cand = evaluer_solution(candidat, masses, utilites, C)

            # On accepte si c'est meilleur, ou avec une probabilité liée à la température
            if score_cand > score or random.random() < math.exp((score_cand - score) / T):
                solution, score = candidat, score_cand

                # Mise à jour du meilleur global
                if score > meilleur_score:
                    meilleure_sol, meilleur_score = solution.copy(), score

        # On baisse progressivement la température, l'algo va de moins en moins accepter les erreurs
        T *= alpha

    return meilleure_sol, meilleur_score

if __name__ == "__main__":
    for C in [0.6, 2, 3, 4, 5]:

        debut = time.time()

        solution, score = recuit_simule(objets, C)

        # Arrêt du chronomètre
        temps_calcul = time.time() - debut

        print(f"\n--- Résultat pour C = {C} ---")
        poids_total = 0
        composition = [] # Liste pour stocker le nom des objets pris

        # Parcours de la solution pour récupérer la composition et le poids
        for s, o in zip(solution, objets):
            if s:
                composition.append(o['nom'])
                poids_total += o["masse"]

        # Affichage des résultats demandés
        print(f"Composition du sac : {', '.join(composition)}")
        print(f"Poids total embarqué : {poids_total} kg")
        print(f"Utilité totale : {score}")
        print(f"Temps de calcul : {temps_calcul:.6f} secondes")
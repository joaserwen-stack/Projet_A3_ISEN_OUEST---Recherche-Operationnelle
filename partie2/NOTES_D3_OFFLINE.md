# D3 Offline — Compte rendu

## Problème
3D Bin Packing : 100 marchandises, wagons 11.583 × 2.294 × 2.569 m.  
Volume total : 841.67 m³ | Borne inférieure théorique : **13 wagons** (volume seul).  
Objectif : minimiser le nombre de wagons.

---

## Architecture (V4.1 GA Mémétique)

| Composant | Détail |
|---|---|
| Encodage | Permutation d'IDs de marchandises |
| Décodeur | DBLF + Best-Fit wagon + early-exit si dépasse record |
| DBLF | Tri coins par `(x, z, y)` — remplit avant→arrière, plancher d'abord |
| Best-Fit | Choisit le wagon avec le moins de volume résiduel |
| Corner points | 3 coins par boîte placée : `(cx+L, cy, cz)`, `(cx, cy+l, cz)`, `(cx, cy, cz+H)` |
| Population | 40 individus (4 seeds + 36 aléatoires) |
| Sélection | Élitisme top-20 |
| Croisement | OX (Order Crossover) |
| Mutation | Swap / insertion / 2-opt, taux adaptatif 0.35→0.50→0.65 (seuils 50/100 gens stagnation) |
| Or-opt | Or-opt-dernier-wagon every 50 gens, budget 1.5s, sur `meilleur_individu` |
| Cataclysme | Après 200 gens sans amélioration : top-2 + 16 double-bridges + random jusqu'à 40 |
| Parallélisation | `cpu_count()` workers via `multiprocessing.Pool` |
| Pre-warm | `seeds[0]` évalué avant pool → active early-exit dès gen 1 |

### Seeds heuristiques
Volume desc · Hauteur desc · Aire base desc · Longueur desc

---

## Ce qui a marché ✅

| Amélioration | Impact |
|---|---|
| Or-opt ciblé dernier wagon | **DÉCISIF — percée 15→14 wagons.** O(k×n) vs O(n²), cible directement le goulot |
| Population 20→40 | Moins de convergence prématurée, même ~4000 gens en 300s |
| Double-bridge cataclysme | Irréversible par 2-opt/OX → sort des bassins profonds |
| `Wagon.vol_used` cache | Incrémental au lieu de `sum(...)` sur toutes les boites à chaque placement |
| Décodeur unifié (`avec_assignations`) | Fusionne deux fonctions quasi-identiques, élimine double maintenance |
| Pre-warm | Early-exit actif dès gen 1 |

## Ce qui n'a pas marché ❌

| Tentative | Raison de l'échec |
|---|---|
| EMS (Extreme Maximal Spaces) | 18 wagons — plus lent, positions valides éliminées par dominance |
| 6 coins par boîte | Eval 2× plus lente → moins de gens → résultat pire |
| Look-ahead top-3 coins | ~3× plus lent, même résultat |
| `FREQ_OR_OPT = 25` | ~55% CPU sur or-opt, étouffait le GA |
| Seeds dans cataclysme | Déjà explorées → convergent vers le même optima. 10+ cataclysmes sans effet |
| Or-opt-2 en alternance | Améliorait uniquement le taux de remplissage (%), jamais le nb de wagons |

---

## Résultats

| Run | Meilleur | Temps | Notes |
|---|---|---|---|
| V4.0 baseline | 15 wagons | — | 14 observé 1 fois (stochastique) |
| V4.1 best run | **14 wagons** | gen 4894, ~297s | Or-opt dernier wagon décisif |
| Run récent | 15 wagons, 5.0% fill | gen 1014, ~61s | Stagnation totale ensuite |

---

## Diagnostic stagnation actuelle

Dernier wagon à **5% fill** (1-2 items) atteint à gen 1014. Ensuite blocage total jusqu'à fin du chrono (300s).

**Cause** : `meilleur_individu` gelé depuis gen 1014. Cataclysme génère 16 double-bridges de ce même individu → aucun ne produit < 15 wagons → `meilleur_individu` ne change jamais → or-opt reteste le même individu à chaque fire → même échec → boucle fermée.

Or-opt-last-wagon a 1.5s pour trouver où placer 1-2 items dans 14 wagons. Si la géométrie ne le permet pas en 1.5s, il abandonne et ne retente jamais différemment.

---

## Pistes identifiées (non encore testées)

| Piste | Priorité | Raison |
|---|---|---|
| Budget or-opt adaptatif : si fill < 10% → 8s | **Haute** | 1-2 items à placer, 1.5s trop court |
| Or-opt sur top-5 population (pas seulement `meilleur`) | **Haute** | Casse la boucle fermée, explore voisinages différents |
| ILS post-cataclysme : `double_bridge(meilleur)` → or-opt → garder si meilleur | **Haute** | Exploite le budget cataclysme de façon ciblée |
| Extreme Points (Crainic 2008) | Basse | Alternative aux corner points, plus complet sans overhead EMS |

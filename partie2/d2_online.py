import time
import math
from utils import load_marchandises, print_results

# Constantes définissant les dimensions d'un wagon de train
LONGUEUR_WAGON = 11.583  # en mètres
LARGEUR_WAGON = 2.294    # en mètres

# EPS (Epsilon) est une toute petite valeur pour gérer les erreurs d'arrondi flottant.
# Par exemple, 1.9999999 au lieu de 2.0. On tolère cet écart pour ne pas
# refuser un objet qui rentre en réalité parfaitement dans l'espace disponible.
EPS = 1e-9


def remplir_wagons(objets):
    """
    Algorithme de placement Bin-Packing 2D — mode Online (MaxRects BLSF).
    Mode Online : les objets arrivent dans l'ordre du fichier, sans tri préalable.
    On doit placer chaque objet immédiatement, sans connaître la suite.
    L'objectif est de ranger tous les objets dans un minimum de wagons.
    """
    # Liste qui contiendra tous nos wagons et leur contenu
    wagons = []

    # On prend chaque objet dans l'ordre d'arrivée, sans possibilité de réorganiser
    for objet in objets:
        placer_objet(wagons, objet)

    return wagons


def placer_objet(wagons, objet):
    """
    Cherche la meilleure place possible pour un objet dans les wagons déjà ouverts.
    Stratégie : Best Long Side Fit (BLSF) — on choisit l'espace libre dont le plus
    grand côté résiduel est minimal, ce qui compacte au mieux les objets dans l'espace.
    Si aucune place n'est trouvée, on ouvre un nouveau wagon vide.
    """
    obj_longueur = objet['longueur']
    obj_largeur = objet['largeur']

    # On vérifie si l'objet peut physiquement rentrer dans un wagon.
    # ok_normal : l'objet rentre dans sa position d'origine
    # ok_pivote : l'objet rentre si on le tourne de 90 degrés
    ok_normal = obj_longueur <= LONGUEUR_WAGON and obj_largeur <= LARGEUR_WAGON
    ok_pivote = obj_longueur != obj_largeur and obj_largeur <= LONGUEUR_WAGON and obj_longueur <= LARGEUR_WAGON

    # Si l'objet dépasse les dimensions du wagon dans toutes les orientations, on l'ignore.
    if not ok_normal and not ok_pivote:
        return

    # Variables pour mémoriser le meilleur emplacement trouvé pendant la recherche
    meilleur_score = None
    meilleur_choix = None  # (index_wagon, x, y, longueur_placee, largeur_placee, a_ete_pivote)

    # On parcourt tous les wagons ouverts et tous leurs espaces libres
    for index_wagon, wagon in enumerate(wagons):
        # Chaque wagon maintient la liste de ses rectangles libres
        for espace_x, espace_y, espace_largeur, espace_hauteur in wagon['espaces_libres']:

            # --- Essai 1 : Placer l'objet dans cet espace SANS le tourner ---
            if ok_normal and obj_longueur <= espace_largeur + EPS and obj_largeur <= espace_hauteur + EPS:
                # Score BLSF : on minimise le plus grand côté résiduel.
                # Un résidu minimal signifie que l'objet s'emboite au mieux dans l'espace.
                score = max(espace_largeur - obj_longueur, espace_hauteur - obj_largeur)

                # On note ce choix s'il est meilleur que le précédent
                if meilleur_score is None or score < meilleur_score:
                    meilleur_score = score
                    meilleur_choix = (index_wagon, espace_x, espace_y, obj_longueur, obj_largeur, False)

            # --- Essai 2 : Placer l'objet dans cet espace EN LE TOURNANT ---
            if ok_pivote and obj_largeur <= espace_largeur + EPS and obj_longueur <= espace_hauteur + EPS:
                score = max(espace_largeur - obj_largeur, espace_hauteur - obj_longueur)

                if meilleur_score is None or score < meilleur_score:
                    meilleur_score = score
                    # Attention : en pivotant, la longueur et la largeur sont échangées sur le plan
                    meilleur_choix = (index_wagon, espace_x, espace_y, obj_largeur, obj_longueur, True)

    # Bilan de la recherche
    if meilleur_choix is not None:
        # On a trouvé une place dans un wagon existant
        index_wagon, x_choisi, y_choisi, longueur_placee, largeur_placee, a_ete_pivote = meilleur_choix

        # L'objet occupe une partie d'un espace libre : on redécoupe cet espace
        # pour mettre à jour les zones encore disponibles autour de l'objet
        mettre_a_jour_espaces(wagons[index_wagon], x_choisi, y_choisi, longueur_placee, largeur_placee)

        # On enregistre officiellement l'objet dans ce wagon
        wagons[index_wagon]['objets'].append(
            {**objet, 'rotation': a_ete_pivote, 'placed_l': longueur_placee, 'placed_w': largeur_placee, 'x': x_choisi, 'y': y_choisi}
        )
    else:
        # Aucun espace existant n'est assez grand : on ouvre un tout nouveau wagon
        nouveau_wagon = {
            'espaces_libres': [(0, 0, LONGUEUR_WAGON, LARGEUR_WAGON)],  # Le wagon entier est libre au départ
            'objets': []
        }

        # On choisit l'orientation de l'objet pour ce nouveau wagon
        longueur_placee, largeur_placee, a_ete_pivote = (obj_longueur, obj_largeur, False) if ok_normal else (obj_largeur, obj_longueur, True)

        # On pose l'objet dans le coin en bas à gauche (x=0, y=0)
        mettre_a_jour_espaces(nouveau_wagon, 0, 0, longueur_placee, largeur_placee)

        nouveau_wagon['objets'].append(
            {**objet, 'rotation': a_ete_pivote, 'placed_l': longueur_placee, 'placed_w': largeur_placee, 'x': 0, 'y': 0}
        )
        # On ajoute ce nouveau wagon à la liste
        wagons.append(nouveau_wagon)


def mettre_a_jour_espaces(wagon, obj_x, obj_y, obj_longueur, obj_largeur):
    """
    Quand on pose un objet dans un espace libre, cet espace se divise en plusieurs morceaux.
    Cette fonction recalcule les zones encore libres autour de l'objet qu'on vient de poser.
    """
    nouveaux_espaces = []

    # Coordonnées des bords droit et haut de l'objet placé
    bord_droit_obj = obj_x + obj_longueur
    bord_haut_obj  = obj_y + obj_largeur

    # On examine chaque espace libre existant du wagon
    for espace_x, espace_y, espace_largeur, espace_hauteur in wagon['espaces_libres']: 
        bord_droit_espace = espace_x + espace_largeur # Coordonnées des bords droit et haut de l'espace libre
        bord_haut_espace  = espace_y + espace_hauteur 

        # Si l'objet ne touche pas cet espace, on le conserve tel quel
        if (obj_x >= bord_droit_espace - EPS or bord_droit_obj <= espace_x + EPS or # L'objet est complètement à gauche ou à droite de l'espace
                obj_y >= bord_haut_espace - EPS or bord_haut_obj <= espace_y + EPS): # L'objet est complètement en dessous ou au-dessus de l'espace
            nouveaux_espaces.append((espace_x, espace_y, espace_largeur, espace_hauteur))
            continue

        # L'objet est posé dans cet espace : il le découpe en 4 morceaux au maximum

        # 1. Le morceau restant a GAUCHE de l'objet
        if obj_x > espace_x + EPS:
            nouveaux_espaces.append((espace_x, espace_y, obj_x - espace_x, espace_hauteur))

        # 2. Le morceau restant a DROITE de l'objet
        if bord_droit_obj < bord_droit_espace - EPS:
            nouveaux_espaces.append((bord_droit_obj, espace_y, bord_droit_espace - bord_droit_obj, espace_hauteur))

        # 3. Le morceau restant EN BAS de l'objet
        if obj_y > espace_y + EPS:
            nouveaux_espaces.append((espace_x, espace_y, espace_largeur, obj_y - espace_y))

        # 4. Le morceau restant EN HAUT de l'objet
        if bord_haut_obj < bord_haut_espace - EPS:
            nouveaux_espaces.append((espace_x, bord_haut_obj, espace_largeur, bord_haut_espace - bord_haut_obj))

    # Le découpage génère des espaces qui se chevauchent parfois.
    # On fait le ménage pour ne conserver que les espaces vraiment utiles.
    wagon['espaces_libres'] = nettoyer_espaces_inutiles(nouveaux_espaces)


def nettoyer_espaces_inutiles(espaces):
    """
    Supprime les espaces libres redondants.
    Si un petit espace est entièrement contenu dans un plus grand,
    il est inutile de le mémoriser : on ne garde que le grand.
    """
    # Etape 1 : On écarte les espaces trop étroits pour accueillir quoi que ce soit
    espaces_valides = []
    for x, y, largeur, hauteur in espaces:
        if largeur > EPS and hauteur > EPS:
            espaces_valides.append((x, y, largeur, hauteur))

    nb_espaces = len(espaces_valides)
    espaces_utiles = []

    # Etape 2 : Pour chaque espace, on vérifie s'il est contenu dans un autre
    for i in range(nb_espaces):
        x_courant, y_courant, largeur_courante, hauteur_courante = espaces_valides[i]
        bord_droit_courant = x_courant + largeur_courante
        bord_haut_courant  = y_courant + hauteur_courante

        est_avale_par_un_autre = False

        for j in range(nb_espaces):
            if i == j:  # On ne se compare pas à soi-même
                continue

            x_autre, y_autre, largeur_autre, hauteur_autre = espaces_valides[j]
            bord_droit_autre = x_autre + largeur_autre
            bord_haut_autre  = y_autre + hauteur_autre

            # L'espace courant est-il entièrement à l'intérieur de l'espace autre ?
            if (x_courant >= x_autre - EPS and
                    y_courant >= y_autre - EPS and
                    bord_droit_courant <= bord_droit_autre + EPS and
                    bord_haut_courant  <= bord_haut_autre  + EPS):
                est_avale_par_un_autre = True
                break  # Inutile de continuer, on sait déjà que cet espace est redondant

        # On ne garde que les espaces qui ne sont contenus dans aucun autre
        if not est_avale_par_un_autre:
            espaces_utiles.append(espaces_valides[i])

    return espaces_utiles


# ─── Lancement du programme ────────────────────────────────────

if __name__ == "__main__":
    print("=" * 65)
    print("  Bin-Packing 2D Online — MaxRects BLSF")
    print("=" * 65)

    # Lecture du fichier CSV contenant les marchandises à charger
    objets_a_placer = load_marchandises()
    print(f"Nombre d'objets a charger : {len(objets_a_placer)}")

    if len(objets_a_placer) == 0:
        print("Il n'y a rien a charger.")
        exit(0)

    # On lance le chronometre avant l'algorithme, et on l'arrete juste apres
    debut_chrono = time.time()
    wagons_remplis = remplir_wagons(objets_a_placer)
    temps_ecoule = time.time() - debut_chrono

    # Calculs des métriques de performance
    nb_wagons_utilises        = len(wagons_remplis)
    surface_dun_wagon         = LONGUEUR_WAGON * LARGEUR_WAGON
    surface_totale_disponible = nb_wagons_utilises * surface_dun_wagon
    surface_totale_objets     = sum(obj['longueur'] * obj['largeur'] for obj in objets_a_placer)
    surface_vide_perdue       = surface_totale_disponible - surface_totale_objets

    # La borne inférieure est le nombre minimal de wagons théoriquement nécessaires
    # si l'on pouvait découper et réarranger les objets librement (comme un liquide)
    borne_inferieure_theorique = math.ceil(surface_totale_objets / surface_dun_wagon)

    # Affichage du rapport final
    print("\n" + "=" * 65 + "\n  RÉSULTAT\n" + "=" * 65)
    print_results(
        dimension_label="d=2",
        mode_label="Online (MaxRects BLSF)",
        nb_wagons=nb_wagons_utilises,
        total_unused=surface_vide_perdue,
        execution_time=temps_ecoule
    )

    print(f"  Borne inférieure théorique (les objets sont de l'eau) : {borne_inferieure_theorique} wagons")
    print(f"  Taux d'occupation moyen : {(surface_totale_objets / surface_totale_disponible) * 100:.1f}%")
    print(f"  Ratio par rapport à la perfection : {nb_wagons_utilises}/{borne_inferieure_theorique} ({nb_wagons_utilises / borne_inferieure_theorique:.2f}x plus grand)\n")

    # Aperçu du contenu des 5 premiers wagons pour vérification visuelle
    print("Contenu des 5 premiers wagons :")
    for i, wagon in enumerate(wagons_remplis[:5]):
        print(f"\n  Wagon {i + 1} ({len(wagon['objets'])} objets) :")
        # On trie les objets de gauche à droite, puis de bas en haut
        for obj in sorted(wagon['objets'], key=lambda o: (o['y'], o['x'])):
            symbole_rotation = " (pivote)" if obj['rotation'] else ""
            print(f"    . ID {obj['id']:<2} | Pos: X={obj['x']:05.2f}, Y={obj['y']:05.2f} | "
                  f"Espace occupé: {obj['placed_l']}m x {obj['placed_w']}m{symbole_rotation}")
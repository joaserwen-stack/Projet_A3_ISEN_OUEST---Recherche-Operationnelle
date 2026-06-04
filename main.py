import subprocess
import sys
import os

SCRIPTS = {
    # Partie 1
    "1": ("Partie 1 — Glouton",           "partie1/q5_glouton.py"),
    "2": ("Partie 1 — Force brute",        "partie1/q8_9_Forcebrute.py"),
    "3": ("Partie 1 — Recuit simulé",      "partie1/q10_recuit_simulé.py"),
    # Partie 2 — d=1
    "4": ("Partie 2 d=1 — Online",         "partie2/d1/d1_online.py"),
    "5": ("Partie 2 d=1 — Offline",        "partie2/d1/d1_offline.py"),
    "6": ("Partie 2 d=1 — Complexité",     "partie2/d1/d1_complexite.py"),
    # Partie 2 — d=2
    "7": ("Partie 2 d=2 — Online",         "partie2/d2/d2_online.py"),
    "8": ("Partie 2 d=2 — Offline",        "partie2/d2/d2_offline.py"),
    "9": ("Partie 2 d=2 — Complexité",     "partie2/d2/d2_complexite.py"),
    # Partie 2 — d=3
    "10": ("Partie 2 d=3 — Online",        "partie2/d3/d3_online.py"),
    "11": ("Partie 2 d=3 — Offline",       "partie2/d3/d3_offline.py"),
    "12": ("Partie 2 d=3 — Complexité",    "partie2/d3/d3_complexite.py"),
}

ROOT = os.path.dirname(os.path.abspath(__file__))


def afficher_menu():
    print("\n" + "=" * 50)
    print("  PROJET RO — MENU PRINCIPAL")
    print("=" * 50)
    print("\n  [ Partie 1 ]")
    for k in ("1", "2", "3"):
        label, _ = SCRIPTS[k]
        print(f"  {k:>2}.  {label}")
    print("\n  [ Partie 2 — d=1 ]")
    for k in ("4", "5", "6"):
        label, _ = SCRIPTS[k]
        print(f"  {k:>2}.  {label}")
    print("\n  [ Partie 2 — d=2 ]")
    for k in ("7", "8", "9"):
        label, _ = SCRIPTS[k]
        print(f"  {k:>2}.  {label}")
    print("\n  [ Partie 2 — d=3 ]")
    for k in ("10", "11", "12"):
        label, _ = SCRIPTS[k]
        print(f"  {k:>2}.  {label}")
    print("\n   0.  Quitter")
    print("=" * 50)


def lancer(script_path: str):
    full_path = os.path.join(ROOT, script_path)
    print(f"\nLancement : {script_path}\n" + "-" * 50)
    subprocess.run([sys.executable, full_path], cwd=ROOT)


if __name__ == "__main__":
    while True:
        afficher_menu()
        choix = input("\nChoix : ").strip()
        if choix == "0":
            break
        elif choix in SCRIPTS:
            label, path = SCRIPTS[choix]
            lancer(path)
            input("\n[Entrée pour revenir au menu]")
        else:
            print("Choix invalide.")

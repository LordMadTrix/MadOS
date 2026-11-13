# Kit d'identité visuelle MadOS

MadOS est une version de LiberNT avec sa propre identité visuelle : le thème
« Braise » (sombre, accents rouge braise), son fond d'écran et son logo.
Ce dossier contient les scripts qui génèrent tout ça dans les sources LiberNT.

## Utilisation

Depuis la racine des sources LiberNT (dans Ubuntu/WSL) :

```sh
python3 media/mados/apply_mados.py
cd output-Clang-amd64-debug && ninja liberntvhd
```

Le script repart toujours des fichiers d'origine de LiberNT (versionnés dans
git) : on peut le relancer après avoir changé une couleur ou un dessin.

## Fichiers

| Script | Ce qu'il fait |
|---|---|
| `mados_common.py` | Couleurs, transformation « Braise », dessin du badge et du logotype, formats BMP |
| `make_theme.py` | Recolore le thème par défaut de LiberNT (Win8, installé comme `aero.msstyles`) |
| `make_wallpaper.py` | Génère `modules/wallpapers/MadOS.png` (2560×1440) |
| `make_logos.py` | Logos du démarrage (UEFI et VGA), du LiveCD, du panneau Système, du bouton Démarrer et de l'installateur |
| `apply_mados.py` | Lance tout, règle le fond d'écran par défaut, force la recompilation des ressources puis lance la vérification |
| `verify_mados.py` | Compare chaque fichier généré à l'original LiberNT et contrôle son format (46 contrôles) ; code retour 1 en cas de problème |

Les originaux sont lus depuis la branche amont `origin/main-nt10` (et non
`HEAD`), pour que le kit reste correct après un commit des changements MadOS.
Une autre référence peut être choisie avec la variable `MADOS_UPSTREAM`.

Pour changer la couleur d'accent : `ACCENT` dans `mados_common.py`.

## Image personnelle avec les pilotes de son PC

L'option CMake `MADOS_DRIVERS_DIR` intègre au disque préinstallé (VHD et image
USB) un dossier de pilotes Windows, par exemple ceux exportés depuis le
Windows du même PC (`pnputil /export-driver * <dossier>`, en administrateur).
Ils sont copiés dans `%SystemRoot%\MadOS\Pilotes` et installés à la première
ouverture de session ; le résultat est dans `installation.log`, au même
endroit.

```sh
cd output-Clang-amd64-release
cmake -DMADOS_DRIVERS_DIR=/chemin/vers/pilotes .
ninja liberntimg
```

- Un sous-dossier par paquet (un `.inf` et ses fichiers), **sans espace**
  dans les noms.
- Ne mettre que les pilotes utiles : réseau, Wi-Fi, Bluetooth. Pas les
  pilotes de Microsoft (ACPI, NVMe, USB…), qui remplaceraient ceux de MadOS.
- **Une telle image ne doit jamais être publiée** : les pilotes des
  constructeurs (Intel, Realtek…) ne sont pas redistribuables.
- Avant de compiler une version à publier, vider l'option :
  `cmake -DMADOS_DRIVERS_DIR= .`

## Licence et attribution

MadOS est basé sur LiberNT (GPL-3.0), lui-même basé sur ReactOS
(© 1996-2026 ReactOS Team & Contributors). Les mentions de ces deux projets
sont conservées sur l'écran de démarrage et dans l'installateur.

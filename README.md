<p align="center">
  <img src="media/mados/logo/mados_logo_dark.png" alt="MadOS" width="420">
</p>

<p align="center"><b>Un système d'exploitation NT libre, sobre et respectueux.</b><br>
Basé sur <a href="https://github.com/LiberNT/LiberNT">LiberNT</a>, lui-même basé sur <a href="https://reactos.org">ReactOS</a>.</p>

<p align="center"><img src="media/mados/screenshots/bureau.png" alt="Le bureau de MadOS" width="760"></p>

> **Version expérimentale.** MadOS est un projet jeune : testez-le dans une
> machine virtuelle, pas sur un ordinateur dont vous avez besoin au quotidien.

## Ce qu'est MadOS

MadOS reprend le moteur de LiberNT (noyau NT, pilotes modernes, programmes
Windows en 64 bits) et y ajoute sa propre expérience :

- **Une identité « Braise »** : thème sombre aux accents rouge braise, fond
  d'écran, logo, son de démarrage, écran et menu de démarrage MadOS.
- **Rien n'est envoyé sans votre accord.** LiberNT envoie à chaque démarrage
  un rapport de diagnostic (matériel, identifiants des périphériques…).
  Dans MadOS, c'est coupé par défaut ; vous pouvez l'activer dans le panneau
  Système, avec un texte qui dit exactement ce qui part et où.
- **En français par défaut**, avec le clavier AZERTY (une autre langue reste
  au choix à l'installation).
- **« Bienvenue dans MadOS »** : au premier démarrage, cochez les applications
  que vous voulez (Firefox, VLC, 7-Zip, Notepad++, LibreOffice, Steam). Elles
  sont téléchargées depuis le site officiel de chaque éditeur et **vérifiées
  avant l'installation** (signature numérique de l'éditeur, ou empreinte
  SHA-256). Rien n'est préinstallé de force.
- **Plus rapide à démarrer** : le menu de démarrage ne fait plus attendre
  3 secondes ; appuyez sur une touche (F8…) pendant le démarrage pour l'ouvrir.
- **Plus stable** : correction d'une condition de course dans le chargeur de
  DLL qui faisait planter le démarrage de temps en temps.

| | |
|---|---|
| <img src="media/mados/screenshots/installation.png" alt="Installation en français" width="380"> | <img src="media/mados/screenshots/bienvenue.png" alt="Bienvenue dans MadOS" width="380"> |
| Installation en français | Choix des applications |
| <img src="media/mados/screenshots/menu-demarrer.png" alt="Menu Démarrer" width="380"> | <img src="media/mados/screenshots/menu-demarrage.png" alt="Menu de démarrage" width="380"> |
| Menu Démarrer | Menu de démarrage (sur demande) |

## Essayer MadOS

Téléchargez la dernière version dans
[**Releases**](../../releases) :

- **`MadOS-*-amd64.vhd`** : disque déjà installé. Dans VirtualBox, créez une
  machine « Windows 11 (64 bits) », **EFI activé**, 4 Go de mémoire, et
  utilisez ce fichier comme disque dur.
- **`MadOS-*-amd64.iso`** : installation classique depuis un CD.
- **`MadOS-*-amd64.img.xz`** : pour essayer MadOS sur un vrai PC depuis une
  clé USB (démarrage UEFI ou BIOS). Écrivez-le avec
  [Rufus](https://rufus.ie) ou [balenaEtcher](https://etcher.balena.io),
  qui lisent directement le fichier compressé. **Cela efface toute la clé.**
  Sur un vrai PC, la carte graphique fonctionne en affichage de base
  (pas de pilote Nvidia, AMD ou Intel).

## Mesures (VM 4 cœurs / 4 Go)

| | Valeur |
|---|---|
| Du logo de démarrage au bureau | ~7 s |
| Mémoire au repos | ~270 Mo |
| Taille installée | ~510 Mo |

Applications testées (installation et lancement) : Firefox, VLC, 7-Zip,
Notepad++, LibreOffice, Steam. Discord ne s'installe pas encore (il exige le
.NET Framework 4.5).

## Construire MadOS

MadOS se compile comme LiberNT (voir [README.LiberNT.md](README.LiberNT.md)) :
Linux, macOS, ou Windows via WSL2.

L'identité MadOS est appliquée par un kit de scripts, qui repart toujours des
fichiers de LiberNT et vérifie le résultat :

```sh
python3 media/mados/apply_mados.py      # applique et vérifie l'identité MadOS
cd output-Clang-amd64-debug && ninja liberntvhd
```

Voir [media/mados/README.md](media/mados/README.md) pour le kit et
[media/mados/tests/README.md](media/mados/tests/README.md) pour les tests
automatiques.

## Licence et remerciements

MadOS est distribué sous **GPL-3.0**, comme LiberNT. Il n'existerait pas sans
le travail de l'équipe **LiberNT** et des contributeurs de **ReactOS**
(© 1996-2026 ReactOS Team & Contributors) : merci à eux. Les correctifs
généraux de MadOS (chargeur de DLL, compilation Release…) sont dans des
commits séparés, pour pouvoir être repris par LiberNT.

---

**English.** MadOS is a free NT operating system based on LiberNT and ReactOS,
with its own "Ember" look, diagnostic data off by default, French by default,
a first-run app picker that downloads and verifies applications from their
publishers, and a few fixes (loader race, release build). Experimental: try it
in a virtual machine. GPL-3.0.

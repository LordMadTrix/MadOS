# Tests automatiques MadOS

`mados-test.ps1` teste une image MadOS dans VirtualBox, depuis Windows
(PowerShell 7), avant chaque publication ou après une modification
importante.

```powershell
pwsh -File media\mados\tests\mados-test.ps1 -Vhd D:\chemin\LiberNT.vhd -Runs 3
```

| Contrôle | Comment |
|---|---|
| Kit MadOS | `verify_mados.py` dans Ubuntu/WSL (formats, couleurs, noms, télémétrie…) |
| Le bureau apparaît | captures d'écran : bouton Démarrer MadOS dans la barre des tâches |
| Aucun plantage | aucune « Unhandled exception » dans le journal série (version Debug) |
| Aucune télémétrie | réseau branché, aucune ligne `DIAGDATA: drain` 45 s après le bureau |
| Temps de démarrage | du logo MadOS au bureau, médiane des démarrages |

Chaque démarrage repart d'une copie neuve du disque. Code de sortie 0 si
tout passe, 1 sinon ; détails et captures dans le dossier `-WorkDir`.

Prérequis : VirtualBox, WSL avec la distribution `Ubuntu-24.04` et les
sources dans `~/libernt` (modifiables par `-WslDistro` et `-Tree`).

Mesure : la VM doit être lancée avec sa fenêtre (`--type gui`) ; sans
fenêtre, Windows 11 bride le processus et le système paraît deux fois plus
lent.

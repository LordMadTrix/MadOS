<#
.SYNOPSIS
    MadOS - tests automatiques d'une image (VirtualBox, hote Windows).

.DESCRIPTION
    1. Verificateur du kit (verify_mados.py, dans Ubuntu/WSL)
    2. N demarrages d'une copie neuve du disque, reseau BRANCHE :
       - le bureau doit apparaitre (barre des taches, bouton Demarrer MadOS)
       - aucune exception non geree dans le journal serie (version Debug)
       - aucune donnee de diagnostic envoyee (aucune ligne DIAGDATA)
       - temps du logo de demarrage au bureau (captures d'ecran)
    Code de sortie 0 si tout passe, 1 sinon.

.EXAMPLE
    .\mados-test.ps1 -Vhd D:\DEV\vms\MadOS.vhd -Runs 3
#>
param(
    [Parameter(Mandatory)] [string]$Vhd,
    [int]$Runs = 3,
    [string]$VmName = "MadOS-test",
    [string]$WorkDir = "$env:TEMP\mados-test",
    [string]$WslDistro = "Ubuntu-24.04",
    [string]$Tree = "~/libernt",
    [int]$TimeoutSec = 180,
    [switch]$SkipKit
)

$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Drawing
$vb = "C:\Program Files\Oracle\VirtualBox\VBoxManage.exe"
$results = [System.Collections.Generic.List[object]]::new()
function Add-Result($name, $ok, $detail) {
    $results.Add([pscustomobject]@{ Test = $name; Resultat = $(if ($ok) { "ok" } else { "ECHEC" }); Detail = $detail })
    "{0,-6} {1} {2}" -f $(if ($ok) { "ok" } else { "ECHEC" }), $name, $detail | Write-Host
}

New-Item -ItemType Directory -Force $WorkDir | Out-Null
$disk = Join-Path $WorkDir "disk.vhd"

# --- 1. kit ---------------------------------------------------------------
if (-not $SkipKit) {
    $out = & wsl.exe -d $WslDistro -u root -- bash -c "cd $Tree && python3 media/mados/verify_mados.py"
    $failed = @($out | Where-Object { $_ -match "ECHEC" })
    Add-Result "kit MadOS (verify_mados.py)" ($LASTEXITCODE -eq 0) "$($failed.Count) echec(s)"
}

# --- VM de test -----------------------------------------------------------
$prev = $ErrorActionPreference; $ErrorActionPreference = "Continue"
if (-not ((& $vb list vms) -match "`"$VmName`"")) {
    & $vb createvm --name $VmName --ostype Windows11_64 --basefolder $WorkDir --register | Out-Null
    & $vb modifyvm $VmName --memory 4096 --cpus 4 --vram 128 --graphicscontroller vboxsvga --firmware efi `
        --ioapic on --nic1 nat --audio-enabled off --tpm-type none
    & $vb storagectl $VmName --name SATA --add sata --controller IntelAhci --portcount 2
}

function Count-Red($bmp, $x0, $y0, $x1, $y1) {
    $c = 0
    for ($y = $y0; $y -lt [math]::Min($y1, $bmp.Height); $y += 2) {
        for ($x = $x0; $x -lt [math]::Min($x1, $bmp.Width); $x += 2) {
            $p = $bmp.GetPixel($x, $y)
            if ($p.R -gt 170 -and $p.G -lt 110 -and $p.B -lt 110) { $c++ }
        }
    }
    $c
}
function Read-Shared($path) {
    try { $fs = [IO.FileStream]::new($path, 'Open', 'Read', 'ReadWrite'); $t = [IO.StreamReader]::new($fs).ReadToEnd(); $fs.Dispose(); $t } catch { "" }
}

# --- 2. demarrages --------------------------------------------------------
$times = @()
foreach ($run in 1..$Runs) {
    & $vb controlvm $VmName poweroff 2>&1 | Out-Null; Start-Sleep 4
    & $vb storageattach $VmName --storagectl SATA --port 0 --device 0 --medium none 2>&1 | Out-Null
    & $vb closemedium disk $disk 2>&1 | Out-Null
    Copy-Item $Vhd $disk -Force
    & $vb internalcommands sethduuid $disk | Out-Null
    & $vb storageattach $VmName --storagectl SATA --port 0 --device 0 --type hdd --medium $disk
    $log = Join-Path $WorkDir "serial-$run.log"; Remove-Item $log -ErrorAction SilentlyContinue
    & $vb modifyvm $VmName --uart1 0x3F8 4 --uart-mode1 file $log --cableconnected1 on
    $shot = Join-Path $WorkDir "live.png"
    $logo = $null; $desk = $null
    $sw = [Diagnostics.Stopwatch]::StartNew()
    & $vb startvm $VmName --type gui | Out-Null
    while ($sw.Elapsed.TotalSeconds -lt $TimeoutSec -and -not $desk) {
        $t = $sw.Elapsed.TotalSeconds
        Remove-Item $shot -ErrorAction SilentlyContinue
        & $vb controlvm $VmName screenshotpng $shot 2>$null
        if ($LASTEXITCODE -ne 0 -or -not (Test-Path $shot)) { Start-Sleep -Milliseconds 200; continue }
        try { $ms = [IO.MemoryStream]::new([IO.File]::ReadAllBytes($shot)); $bmp = [Drawing.Bitmap]::new($ms) } catch { continue }
        $w = $bmp.Width; $h = $bmp.Height
        if (-not $logo -and $w -ge 640 -and (Count-Red $bmp ([int]($w * 0.40)) 30 ([int]($w * 0.60)) 140) -gt 30) { $logo = $t }
        if ((Count-Red $bmp 8 ($h - 44) 50 ($h - 4)) -gt 40) { $desk = $t; $bmp.Save((Join-Path $WorkDir "desk-$run.png")) }
        $bmp.Dispose(); $ms.Dispose()
    }
    # le service de diagnostic attend 30 s apres le demarrage avant d'envoyer
    if ($desk) { Start-Sleep 45 }
    $text = Read-Shared $log
    & $vb controlvm $VmName poweroff 2>&1 | Out-Null

    Add-Result "demarrage $run : bureau atteint" ([bool]$desk) $(if ($desk) { "{0:N1} s apres le lancement" -f $desk } else { "pas de bureau en $TimeoutSec s" })
    $exc = ([regex]::Matches($text, "Unhandled exception")).Count
    Add-Result "demarrage $run : aucun plantage" ($exc -eq 0) "$exc exception(s) non geree(s)"
    $diag = ([regex]::Matches($text, "DIAGDATA: drain")).Count
    Add-Result "demarrage $run : aucune telemetrie" ($diag -eq 0) "$diag envoi(s)"
    if ($logo -and $desk) { $times += ($desk - $logo) }
}
$ErrorActionPreference = $prev

# --- bilan ----------------------------------------------------------------
if ($times.Count) {
    $sorted = $times | Sort-Object
    "Temps du logo au bureau : mediane {0:N2} s (min {1:N2}, max {2:N2})" -f $sorted[[int][math]::Floor(($sorted.Count - 1) / 2)], $sorted[0], $sorted[-1] | Write-Host
}
$failures = @($results | Where-Object Resultat -eq "ECHEC").Count
$results | Export-Csv (Join-Path $WorkDir "resultats.csv")
"`n{0} test(s), {1} echec(s). Details : {2}" -f $results.Count, $failures, $WorkDir | Write-Host
exit $(if ($failures) { 1 } else { 0 })

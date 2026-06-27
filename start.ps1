Write-Host "O.R.I.O START"

# ---------------- DOCKER ----------------
Write-Host "`nIniciando Docker..."
docker compose up -d


# ---------------- CLOUDFLARED ----------------
$cloudflaredPath = (Get-Command cloudflared -ErrorAction SilentlyContinue).Source

if (-not $cloudflaredPath) {
    $cloudflaredPath = "C:\Windows\System32\cloudflared.exe"
}

if (-not (Test-Path $cloudflaredPath)) {
    Write-Host "ERROR: cloudflared no encontrado"
    exit 1
}

Write-Host "cloudflared OK -> $cloudflaredPath"


# 🔥 MATAR PROCESO ANTERIOR
Get-Process cloudflared -ErrorAction SilentlyContinue | Stop-Process -Force


# ---------------- LOG (FIX BLOQUEO) ----------------
$logFile = "$PSScriptRoot\cf.log"

# 🔥 IMPORTANTE: cerrar handle antes de limpiar
Start-Sleep -Milliseconds 500

if (Test-Path $logFile) {
    Remove-Item $logFile -Force -ErrorAction SilentlyContinue
}

New-Item $logFile -ItemType File | Out-Null


# ---------------- START CLOUDFLARED (SIN START-PROCESS BUG) ----------------
Write-Host "`nIniciando Cloudflare Tunnel..."

$job = Start-Job -ScriptBlock {
    param($path, $log)

    & $path tunnel --url http://localhost:5000 *>> $log
} -ArgumentList $cloudflaredPath, $logFile


# ---------------- WAIT URL ----------------
Write-Host "`nEsperando URL..."

$publicUrl = $null

for ($i = 0; $i -lt 200; $i++) {

    Start-Sleep -Milliseconds 500

    if (!(Test-Path $logFile)) { continue }

    $text = Get-Content $logFile -Raw

    if ([string]::IsNullOrWhiteSpace($text)) { continue }

    if ($text -match "https://[a-zA-Z0-9\-\.]+\.trycloudflare\.com") {
        $publicUrl = $matches[0]
        break
    }
}

if (-not $publicUrl) {
    Write-Host "ERROR: no se pudo capturar URL"
    Stop-Job $job -ErrorAction SilentlyContinue
    exit 1
}

Write-Host "`nURL GENERADA:"
Write-Host $publicUrl


# ---------------- SAVE URL ----------------
$publicUrl | Out-File "$PSScriptRoot\public_url.txt" -Encoding utf8


# ---------------- UPDATE HTML ----------------
$html = @"
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>O.R.I.O</title>
<meta http-equiv="refresh" content="0; url=$publicUrl">
<script>
window.location.href = "$publicUrl";
</script>
</head>
<body>
<h1>O.R.I.O</h1>
<p>Redirigiendo...</p>
<a href="$publicUrl">Entrar</a>
</body>
</html>
"@

$html | Set-Content "$PSScriptRoot\index.html" -Encoding UTF8

Write-Host "`nOK: HTML actualizado"


# ---------------- FTP (.ENV) ----------------
Write-Host "`nSubiendo a Unaux..."

$envFile = "$PSScriptRoot\.env"

if (!(Test-Path $envFile)) {
    Write-Host "ERROR: .env no encontrado"
    exit 1
}

$ftpPassword = (Get-Content $envFile | Where-Object { $_ -match "^FTP_PASSWORD=" }) `
    -split "=",2 | Select-Object -Last 1

$ftpPassword = $ftpPassword.Trim().Trim('"').Trim("'")

$winscp = "C:\Program Files (x86)\WinSCP\WinSCP.com"

if (!(Test-Path $winscp)) {
    Write-Host "ERROR: WinSCP no encontrado"
    exit 1
}

$ftpScript = @"
open ftp://ezyro_42225335:$ftpPassword@ftpupload.net
cd htdocs
put "$PSScriptRoot\index.html"
exit
"@

$ftpFile = "$PSScriptRoot\ftp.txt"
Set-Content $ftpFile $ftpScript

& $winscp /script=$ftpFile

Write-Host "`nOK: Unaux actualizado -> https://orio.unaux.com"

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


# ---------------- START TUNNEL (SIN START-PROCESS) ----------------
Write-Host "`nIniciando Cloudflare Tunnel..."

$logFile = "$PSScriptRoot\cf.log"
if (Test-Path $logFile) { Remove-Item $logFile -Force }


# Ejecutar cloudflared en segundo plano
Start-Job -ScriptBlock {
    param($path, $log)

    & $path tunnel --url http://localhost:5000 *>> $log
} -ArgumentList $cloudflaredPath, $logFile | Out-Null


# ---------------- WAIT URL ----------------
Write-Host "`nEsperando URL..."

$publicUrl = $null

for ($i = 0; $i -lt 120; $i++) {

    Start-Sleep -Milliseconds 500

    if (Test-Path $logFile) {

        $text = Get-Content $logFile -Raw

        if ($text -match "https://[a-zA-Z0-9\-]+\.trycloudflare\.com") {
            $publicUrl = $matches[0]
            break
        }
    }
}

if (-not $publicUrl) {
    Write-Host "ERROR: no se pudo capturar URL"
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
Write-Host "URL FINAL: $publicUrl"
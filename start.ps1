Write-Host "O.R.I.O START"

# ---------------- DOCKER ----------------
Write-Host "`nIniciando Docker..."

docker compose up -d

if ($LASTEXITCODE -eq 0) {
    Write-Host "`nDocker iniciado correctamente."
    Write-Host "La aplicación debería estar disponible en:"
    Write-Host "http://localhost:5000"
} else {
    Write-Host "`nError al iniciar Docker."
}
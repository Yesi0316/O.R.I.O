$ip = (Get-NetIPConfiguration | Where-Object {$_.IPv4DefaultGateway -ne $null}).IPv4Address.IPAddress

Write-Host ""
Write-Host "====================================="
Write-Host "         SERVIDOR INICIADO"
Write-Host "    Local: http://localhost:5000"
Write-Host "   Red:   http://$ip`:5000"
Write-Host "   Adminer: http://localhost:8081"
Write-Host "====================================="
Write-Host ""

docker compose up

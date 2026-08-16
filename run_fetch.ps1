# 启动专用 Edge（带调试端口）并运行 ScienceDirect 抓取
$ErrorActionPreference = 'Stop'
$dir = $PSScriptRoot
$edge = 'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
$profile = Join-Path $dir 'edge_profile'
$port = 9223

# 1. 检查 CDP 是否就绪
$ready = $false
try { $null = Invoke-RestMethod "http://127.0.0.1:$port/json/version" -TimeoutSec 3; $ready = $true } catch {}

if (-not $ready) {
    Start-Process $edge -ArgumentList "--user-data-dir=`"$profile`"", "--remote-debugging-port=$port", "--remote-allow-origins=*", "--no-first-run"
    for ($i = 0; $i -lt 20; $i++) {
        Start-Sleep -Seconds 2
        try { $null = Invoke-RestMethod "http://127.0.0.1:$port/json/version" -TimeoutSec 3; $ready = $true; break } catch {}
    }
}

if (-not $ready) {
    Write-Output "Edge CDP 启动失败"
    exit 1
}

python (Join-Path $dir 'sciencedirect_fetch.py')
exit $LASTEXITCODE

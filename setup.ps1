# 每日论文猎人 一键安装脚本
$ErrorActionPreference = 'Stop'
$dir = $PSScriptRoot

Write-Host "=== 1) 安装 Python 依赖 ==="
pip install requests playwright

Write-Host "=== 2) 生成 config.json（如不存在）==="
if (-not (Test-Path (Join-Path $dir 'config.json'))) {
    Copy-Item (Join-Path $dir 'config.example.json') (Join-Path $dir 'config.json')
    Write-Host "已从 config.example.json 生成 config.json —— 请编辑填入密钥"
} else {
    Write-Host "config.json 已存在，跳过"
}

Write-Host "=== 3) 注册定时任务（06:00 / 06:30 / 07:00）==="
$py = (Get-Command python).Source
$fetchAction = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$(Join-Path $dir 'run_fetch.ps1')`"" -WorkingDirectory $dir
$reportAction = New-ScheduledTaskAction -Execute $py -Argument "`"$(Join-Path $dir 'report_from_sd.py')`"" -WorkingDirectory $dir
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -WakeToRun -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 40)

Register-ScheduledTask -TaskName 'PaperScout-Fetch1' -Action $fetchAction -Trigger (New-ScheduledTaskTrigger -Daily -At '06:00') -Settings $settings -Force | Out-Null
Register-ScheduledTask -TaskName 'PaperScout-Fetch2' -Action $fetchAction -Trigger (New-ScheduledTaskTrigger -Daily -At '06:30') -Settings $settings -Force | Out-Null
Register-ScheduledTask -TaskName 'PaperScout-Report' -Action $reportAction -Trigger (New-ScheduledTaskTrigger -Daily -At '07:00') -Settings $settings -Force | Out-Null

Write-Host ""
Write-Host "=== 安装完成 ==="
Write-Host "接下来手动两步："
Write-Host "  1) 编辑 config.json 填入 llm.api_key / serverchan.sendkey / output_dir"
Write-Host "  2) 运行 .\run_fetch.ps1 弹出专用 Edge 窗口，登录一次 ScienceDirect（登录态存入 edge_profile/）"
Write-Host ""
Write-Host "验证：.\run_fetch.ps1 抓取一批；python report_from_sd.py 生成报告+摄入+通知"

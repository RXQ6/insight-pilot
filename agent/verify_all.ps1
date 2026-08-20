# InsightPilot 一键验证：起基础设施 -> 启动 Java/Worker -> 评测 -> 压测
# 用法：powershell -ExecutionPolicy Bypass -File agent\verify_all.ps1

$ErrorActionPreference = 'Stop'
$agent = $PSScriptRoot
$root = Split-Path $agent -Parent

Write-Host "[1/6] 起基础设施 (db + redis)..."
docker compose -f "$root\docker-compose.yml" up -d db redis
if ($LASTEXITCODE -ne 0) { throw "docker compose 失败，请先启动 Docker Desktop" }

Write-Host "[2/6] 打包并后台启动 Java..."
Push-Location "$root\java"
mvn -DskipTests package
if ($LASTEXITCODE -ne 0) { Pop-Location; throw "Java 打包失败，请检查 mvn" }
$javaProc = Start-Process java -ArgumentList '-jar', 'target\insight-pilot-control-plane-0.1.0.jar' -PassThru -WindowStyle Hidden
Pop-Location
Write-Host "Java PID: $($javaProc.Id)"

Write-Host "[3/6] 后台启动 Worker..."
Push-Location $agent
$workerProc = Start-Process .venv\Scripts\python -ArgumentList '-m', 'insight_agent.worker' -PassThru -WindowStyle Hidden
Pop-Location
Write-Host "Worker PID: $($workerProc.Id)"

Write-Host "[4/6] 等待 Java 8080 就绪..."
$ready = $false
for ($i = 0; $i -lt 30; $i++) {
    try {
        $r = Invoke-WebRequest 'http://localhost:8080/api/health' -TimeoutSec 2 -UseBasicParsing
        if ($r.StatusCode -eq 200) { $ready = $true; break }
    } catch { }
    Start-Sleep -Seconds 2
}
if (-not $ready) { throw "Java 8080 未就绪，检查 Java 进程日志" }
Write-Host "Java OK"

Write-Host "[5/6] 跑评测（116 条，约 10-20 分钟，确认 74.7% 是否保住）..."
Push-Location $agent
.venv\Scripts\python scripts\run_eval.py
if ($LASTEXITCODE -ne 0) { Write-Warning "评测未正常完成，请查看输出" }

Write-Host "[6/6] 跑压测（10 并发 x 5 请求）..."
.venv\Scripts\python scripts\load_test.py --concurrency 10 --each 5
Pop-Location

Write-Host "`n全部完成。停止后台服务："
Write-Host "  Stop-Process -Id $($javaProc.Id),$($workerProc.Id)"
Write-Host "评测结果在 agent\data\eval_report.json，压测结果见上方输出。"

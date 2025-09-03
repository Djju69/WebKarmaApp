<#
.SYNOPSIS
    Скрипт для запуска нагрузочного тестирования приложения.
.DESCRIPTION
    Запускает серию нагрузочных тестов с разными параметрами
    и генерирует отчеты о производительности.
#>

param (
    [string]$targetHost = "http://localhost:8000",
    [int]$duration = "60",  # Длительность теста в секундах
    [string]$envFile = "..\..\.env"  # Файл с переменными окружения
)

# Установка переменных окружения
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        $name, $value = $_.split('=', 2)
        if ($name -and $value) {
            [Environment]::SetEnvironmentVariable($name.Trim(), $value.Trim(), "Process")
        }
    }
}

# Установка переменной окружения для целевого хоста
[Environment]::SetEnvironmentVariable("TARGET_HOST", $targetHost, "Process")

# Создаем директорию для отчетов
$reportDir = "reports/$(Get-Date -Format 'yyyyMMdd_HHmmss')"
New-Item -ItemType Directory -Force -Path $reportDir | Out-Null

# Функция для запуска теста
function Run-LoadTest {
    param (
        [string]$testName,
        [int]$users,
        [int]$spawnRate,
        [int]$duration
    )
    
    Write-Host "`n🚀 Запуск теста: $testName" -ForegroundColor Cyan
    Write-Host "👥 Пользователи: $users, Скорость: $spawnRate/сек, Длительность: ${duration}с" -ForegroundColor Cyan
    
    $reportPath = "$reportDir/$testName"
    
    # Запуск Locust с указанными параметрами
    $process = Start-Process -NoNewWindow -PassThru -FilePath "locust" -ArgumentList @(
        "-f", "locustfile.py",
        "--headless",
        "--users", $users,
        "--spawn-rate", $spawnRate,
        "--run-time", "${duration}s",
        "--csv", $reportPath,
        "--csv-full-history",
        "--host", $targetHost
    )
    
    $process | Wait-Process
    
    # Генерация отчета
    Write-Host "📊 Генерация отчета для $testName..." -ForegroundColor Green
    python -c "import pandas as pd; df = pd.read_csv('${reportPath}_stats.csv'); print(df[['Name', '# requests', '50%', '95%', '99%', 'Max', 'Total Median Response Time']].to_markdown())" | Out-File "${reportPath}_summary.md"
    
    Write-Host "✅ Тест $testName завершен. Отчет сохранен в ${reportPath}_summary.md" -ForegroundColor Green
}

# Установка зависимостей
Write-Host "🔧 Установка зависимостей..." -ForegroundColor Yellow
pip install -r requirements.txt

# Запуск тестов с разными сценариями
$testScenarios = @(
    @{Name = "smoke"; Users = 10; SpawnRate = 5; Duration = 30},
    @{Name = "normal"; Users = 100; SpawnRate = 10; Duration = 60},
    @{Name = "high"; Users = 500; SpawnRate = 50; Duration = 120},
    @{Name = "spike"; Users = 1000; SpawnRate = 100; Duration = 300}
)

foreach ($test in $testScenarios) {
    Run-LoadTest -testName $test.Name -users $test.Users -spawnRate $test.SpawnRate -duration $test.Duration
}

Write-Host "`n🎉 Все тесты завершены! Отчеты сохранены в директории: $reportDir" -ForegroundColor Green

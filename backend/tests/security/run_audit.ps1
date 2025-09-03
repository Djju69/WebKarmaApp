<#
.SYNOPSIS
    Запуск комплексной проверки безопасности WebKarmaApp
.DESCRIPTION
    Выполняет серию проверок безопасности, включая:
    - Анализ зависимостей на уязвимости
    - Проверку конфигурации
    - Поиск чувствительных данных
    - Проверку заголовков безопасности
#>

param (
    [string]$OutputFormat = "html",
    [string]$OutputDir = "./reports",
    [switch]$InstallDeps
)

# Create output directory if it doesn't exist
$reportDir = "$PSScriptRoot/$OutputDir"
if (-not (Test-Path -Path $reportDir)) {
    New-Item -ItemType Directory -Path $reportDir | Out-Null
}

# Install dependencies if requested
if ($InstallDeps) {
    Write-Host "🔧 Установка зависимостей..." -ForegroundColor Yellow
    pip install -r "$PSScriptRoot/requirements.txt"
    if (-not $?) {
        Write-Host "❌ Ошибка при установке зависимостей" -ForegroundColor Red
        exit 1
    }
}

# Function to run a security tool and capture output
function Invoke-SecurityTool {
    param (
        [string]$Name,
        [string]$Command,
        [string]$OutputFile
    )
    
    Write-Host "🔍 Запуск $Name..." -ForegroundColor Cyan
    try {
        Invoke-Expression $Command | Out-File -FilePath $OutputFile -Encoding utf8
        Write-Host "✅ $Name выполнен успешно" -ForegroundColor Green
        return $true
    } catch {
        Write-Host "❌ Ошибка при выполнении $Name : $_" -ForegroundColor Red
        return $false
    }
}

# 1. Run safety check for Python dependencies
$safetyReport = "$reportDir/safety_report.json"
Invoke-SecurityTool -Name "Dependency Check (safety)" -Command "safety check --json" -OutputFile $safetyReport

# 2. Run bandit for Python code analysis
$banditReport = "$reportDir/bandit_report.json"
Invoke-SecurityTool -Name "Code Analysis (bandit)" -Command "bandit -r $PSScriptRoot/../../../app -f json" -OutputFile $banditReport

# 3. Run custom security audit
$auditReport = "$reportDir/security_audit.json"
$pythonCmd = "python -m tests.security.audit --format json"
Invoke-SecurityTool -Name "Security Audit" -Command $pythonCmd -OutputFile $auditReport

# 4. Generate HTML report
$htmlReport = "$reportDir/security_report.html"
$pythonCmd = @"
import json
from datetime import datetime

def load_json_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        return {'error': str(e)}

# Load all reports
reports = {
    'safety': load_json_file('$safetyReport'),
    'bandit': load_json_file('$banditReport'),
    'audit': load_json_file('$auditReport')
}

# Generate HTML
html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Security Audit Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; margin: 0; padding: 20px; }}
        .header {{ background: #2c3e50; color: white; padding: 20px; margin: -20px -20px 20px -20px; }}
        .section {{ margin-bottom: 30px; }}
        .issue {{ 
            border-left: 4px solid #e74c3c; 
            padding: 10px 15px; 
            margin: 10px 0; 
            background: #f9f9f9;
        }}
        .critical {{ border-left-color: #e74c3c; }}
        .high {{ border-left-color: #e67e22; }}
        .medium {{ border-left-color: #f1c40f; }}
        .low {{ border-left-color: #3498db; }}
        .info {{ border-left-color: #2ecc71; }}
        .severity {{ 
            display: inline-block; 
            padding: 2px 8px; 
            border-radius: 3px; 
            color: white; 
            font-weight: bold; 
            font-size: 0.9em;
        }}
        .severity-critical {{ background: #e74c3c; }}
        .severity-high {{ background: #e67e22; }}
        .severity-medium {{ background: #f1c40f; }}
        .severity-low {{ background: #3498db; }}
        .severity-info {{ background: #2ecc71; }}
        pre {{ 
            background: #f5f5f5; 
            padding: 10px; 
            border-radius: 3px; 
            overflow-x: auto;
        }}
        .summary-card {{
            display: inline-block;
            margin: 10px;
            padding: 15px;
            border-radius: 5px;
            background: white;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            width: 200px;
            text-align: center;
        }}
        .summary-count {{
            font-size: 2em;
            font-weight: bold;
            margin: 5px 0;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Security Audit Report</h1>
        <p>Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>

    <div class="summary">
        <h2>Summary</h2>
        <div class="summary-card">
            <div>Critical Issues</div>
            <div class="summary-count" style="color: #e74c3c;">
                {len([i for i in reports.get('audit', {}).get('issues', []) if i.get('severity') == 'CRITICAL'])}
            </div>
        </div>
        <div class="summary-card">
            <div>High Issues</div>
            <div class="summary-count" style="color: #e67e22;">
                {len([i for i in reports.get('audit', {}).get('issues', []) if i.get('severity') == 'HIGH'])}
            </div>
        </div>
        <div class="summary-card">
            <div>Vulnerable Dependencies</div>
            <div class="summary-count" style="color: #f1c40f;">
                {len(reports.get('safety', {}).get('vulnerabilities', []))}
            </div>
        </div>
    </div>
"""

# Add audit issues
if 'audit' in reports and 'issues' in reports['audit']:
    html += "<div class=\"section\"><h2>Security Audit Results</h2>"
    for issue in reports['audit']['issues']:
        severity = issue.get('severity', 'info').lower()
        html += f"""
        <div class="issue {severity}">
            <div><span class="severity severity-{severity}">{issue.get('severity', 'INFO')}</span> {issue.get('title', 'Untitled')}</div>
            <p><strong>Location:</strong> {issue.get('location', 'N/A')}</p>
            <p><strong>Description:</strong> {issue.get('description', 'No description available')}</p>
            <p><strong>Recommendation:</strong> {issue.get('recommendation', 'No recommendation provided')}</p>
        </div>
        """
    html += "</div>"

# Add safety vulnerabilities
if 'safety' in reports and 'vulnerabilities' in reports['safety'] and reports['safety']['vulnerabilities']:
    html += "<div class=\"section\"><h2>Vulnerable Dependencies</h2>"
    for vuln in reports['safety']['vulnerabilities']:
        html += f"""
        <div class="issue high">
            <div><span class="severity severity-high">HIGH</span> {vuln.get('package_name', 'Unknown')} {vuln.get('vulnerable_spec', '')}</div>
            <p><strong>Affected Version:</strong> {vuln.get('analyzed_version', 'N/A')}</p>
            <p><strong>Fixed Version:</strong> {vuln.get('fixed_versions', 'Not fixed')}</p>
            <p><strong>Description:</strong> {vuln.get('advisory', 'No description available')}</p>
            <p><strong>More Info:</strong> {vuln.get('more_info_url', 'N/A')}</p>
        </div>
        """
    html += "</div>"

# Add bandit findings
if 'bandit' in reports and 'results' in reports['bandit'] and reports['bandit']['results']:
    html += "<div class=\"section\"><h2>Code Analysis Results</h2>"
    for finding in reports['bandit']['results']:
        severity = finding.get('issue_severity', 'medium').lower()
        html += f"""
        <div class="issue {severity}">
            <div><span class="severity severity-{severity}">{finding.get('issue_severity', 'MEDIUM')}</span> {finding.get('issue_text', 'Untitled')}</div>
            <p><strong>File:</strong> {finding.get('filename', 'N/A')} (Line {finding.get('line_number', 'N/A')})</p>
            <p><strong>Confidence:</strong> {finding.get('issue_confidence', 'N/A')}</p>
            <p><strong>More Info:</strong> {finding.get('more_info', 'N/A')}</p>
            <pre><code>{finding.get('code', '')}</code></pre>
        </div>
        """
    html += "</div>"

html += """
</body>
</html>
"""

# Write HTML report
with open('$htmlReport', 'w', encoding='utf-8') as f:
    f.write(html)
"@

# Execute Python code to generate HTML report
$pythonOutput = python -c $pythonCmd
if ($?) {
    Write-Host "✅ Отчет сгенерирован: $htmlReport" -ForegroundColor Green
    # Open the report in default browser
    Start-Process $htmlReport
} else {
    Write-Host "❌ Ошибка при генерации отчета" -ForegroundColor Red
    Write-Host $pythonOutput
}

Write-Host "\n🔍 Аудит безопасности завершен. Проверьте отчет: $htmlReport" -ForegroundColor Cyan

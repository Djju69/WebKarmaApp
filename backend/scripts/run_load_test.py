#!/usr/bin/env python3
"""
Скрипт для запуска нагрузочного тестирования с помощью Locust.
Позволяет запускать различные сценарии нагрузки и генерировать отчеты.
"""
import os
import sys
import subprocess
import time
import json
from datetime import datetime
from pathlib import Path

# Конфигурация тестов
TEST_CONFIGS = {
    "smoke": {
        "users": 10,
        "spawn_rate": 1,
        "duration": "1m",
        "description": "Дымовое тестирование (10 пользователей, 1 минута)"
    },
    "normal": {
        "users": 100,
        "spawn_rate": 10,
        "duration": "5m",
        "description": "Нормальная нагрузка (100 пользователей, 5 минут)"
    },
    "high": {
        "users": 1000,
        "spawn_rate": 50,
        "duration": "10m",
        "description": "Высокая нагрузка (1000 пользователей, 10 минут)"
    },
    "spike": {
        "users": 5000,
        "spawn_rate": 100,
        "duration": "15m",
        "description": "Пиковая нагрузка (5000 пользователей, 15 минут)"
    },
    "soak": {
        "users": 100,
        "spawn_rate": 5,
        "duration": "1h",
        "description": "Длительная нагрузка (100 пользователей, 1 час)"
    }
}

def run_locust_test(test_name, config, host, headless=True):
    """Запускает тест с заданной конфигурацией"""
    print(f"\n🚀 Запуск теста: {config['description']}")
    
    # Создаем директорию для результатов, если ее нет
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_dir = Path("load_test_results") / f"{test_name}_{timestamp}"
    results_dir.mkdir(parents=True, exist_ok=True)
    
    # Формируем команду для запуска Locust
    cmd = [
        "locust",
        "-f", "locustfile.py",
        "--host", host,
        "--users", str(config["users"]),
        "--spawn-rate", str(config["spawn_rate"]),
        "--run-time", config["duration"],
        "--headless",
        "--csv", str(results_dir / "report"),
        "--html", str(results_dir / "report.html"),
        "--loglevel", "WARNING"
    ]
    
    # Запускаем тест
    start_time = time.time()
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"✅ Тест успешно завершен за {time.time() - start_time:.1f} секунд")
        return {
            "status": "success",
            "output": result.stdout,
            "error": result.stderr,
            "report_dir": str(results_dir.absolute())
        }
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка при выполнении теста: {e}")
        return {
            "status": "error",
            "output": e.stdout,
            "error": e.stderr,
            "report_dir": str(results_dir.absolute())
        }

def generate_summary_report(results):
    """Генерирует сводный отчет по всем выполненным тестам"""
    report = "# Отчет по нагрузочному тестированию\n\n"
    report += f"Дата выполнения: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    
    for test_name, result in results.items():
        report += f"## {test_name.upper()}: {result.get('config', {}).get('description', '')}\n"
        report += f"- **Статус:** {result['status']}\n"
        if result['status'] == 'success':
            report += "- **Результаты:** [HTML отчет]"
            report += f"(file://{os.path.abspath(result['report_dir'])}/report.html)\n"
            # Парсим CSV для получения ключевых метрик
            try:
                with open(f"{result['report_dir']}/report_stats.csv") as f:
                    lines = f.readlines()
                    if len(lines) > 1:
                        headers = lines[0].strip().split(',')
                        values = lines[-1].strip().split(',')
                        metrics = dict(zip(headers, values))
                        
                        report += "- **Ключевые метрики:**\n"
                        report += f"  - Всего запросов: {metrics.get('Request Count', 'N/A')}\n"
                        report += f"  - Ошибки: {metrics.get('Failure Count', '0')} "
                        if int(metrics.get('Failure Count', 0)) > 0:
                            report += "⚠️"
                        report += "\n"
                        
                        report += f"  - Среднее время ответа: {metrics.get('Average Response Time', 'N/A')} мс\n"
                        report += f"  - RPS: {metrics.get('Requests/s', 'N/A')}\n"
                        report += f"  - 95-й перцентиль: {metrics.get('95%', 'N/A')} мс\n"
            except Exception as e:
                report += f"- Не удалось проанализировать результаты: {str(e)}\n"
        else:
            report += f"- **Ошибка:** {result.get('error', 'Неизвестная ошибка')}\n"
        report += "\n"
    
    # Сохраняем отчет в файл
    report_path = "load_test_results/summary_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    
    return report_path

def main():
    """Основная функция для запуска тестов"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Запуск нагрузочного тестирования')
    parser.add_argument('--host', type=str, default="http://localhost:8000",
                       help='Базовый URL тестируемого приложения')
    parser.add_argument('--test', type=str, choices=['all'] + list(TEST_CONFIGS.keys()),
                       default='all', help='Название теста для запуска')
    parser.add_argument('--headless', action='store_true',
                       help='Запускать в headless режиме (без веб-интерфейса)')
    
    args = parser.parse_args()
    
    # Определяем, какие тесты запускать
    tests_to_run = [args.test] if args.test != 'all' else TEST_CONFIGS.keys()
    
    print(f"🚀 Начало нагрузочного тестирования {args.host}")
    print(f"📊 Будут запущены тесты: {', '.join(tests_to_run)}\n")
    
    results = {}
    for test_name in tests_to_run:
        if test_name not in TEST_CONFIGS:
            print(f"⚠️ Тест '{test_name}' не найден, пропускаем")
            continue
            
        config = TEST_CONFIGS[test_name]
        results[test_name] = {
            "config": config,
            **run_locust_test(test_name, config, args.host, args.headless)
        }
    
    # Генерируем сводный отчет
    report_path = generate_summary_report(results)
    print(f"\n📊 Нагрузочное тестирование завершено!")
    print(f"📄 Отчет сохранен в: {os.path.abspath(report_path)}")
    
    # Выводим сводку по тестам
    print("\n" + "="*50)
    print("СВОДКА ПО ТЕСТАМ")
    print("="*50)
    for test_name, result in results.items():
        status = "✅ УСПЕХ" if result["status"] == "success" else "❌ ОШИБКА"
        print(f"{test_name.upper():<10} | {status}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

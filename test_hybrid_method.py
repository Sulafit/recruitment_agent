"""
Тестовый скрипт для сравнения методов матчинга:
- embedding (быстрый)
- llm (точный)
- hybrid (оптимальный)
"""

import requests
import time
import json

API_URL = "http://localhost:8000"

# Тестовая вакансия
JOB_TEXT = """
Senior Python Developer

We are looking for an experienced Python developer to join our team.

Requirements:
- 5+ years of Python development experience
- Strong knowledge of FastAPI or Django
- Experience with PostgreSQL and Redis
- Docker and Kubernetes knowledge
- Machine Learning experience is a plus

Tech Stack: Python, FastAPI, PostgreSQL, Redis, Docker, Machine Learning
"""

def test_method(method: str):
    """Тестирует один метод матчинга"""
    print(f"\n{'='*80}")
    print(f"  Тестирование метода: {method.upper()}")
    print(f"{'='*80}")

    start_time = time.time()

    try:
        response = requests.get(
            f"{API_URL}/recommendations",
            params={
                "job_text": JOB_TEXT,
                "method": method,
                "top_k": 5
            },
            timeout=60
        )

        elapsed_time = time.time() - start_time

        if response.status_code == 200:
            data = response.json()
            candidates = data.get('candidates', [])

            print(f"✅ Успешно! Время: {elapsed_time:.2f} сек")
            print(f"📊 Найдено кандидатов: {len(candidates)}\n")

            print("🏆 Топ-5 кандидатов:\n")
            for i, candidate in enumerate(candidates, 1):
                print(f"{i}. {candidate['candidate_name']}")
                print(f"   Score: {candidate['score']:.4f}")
                if candidate.get('matching_skills'):
                    skills = ', '.join(candidate['matching_skills'][:5])
                    print(f"   Skills: {skills}")
                if candidate.get('explanation') and method in ['llm', 'hybrid']:
                    explanation = candidate['explanation'][:150]
                    print(f"   Explanation: {explanation}...")
                print()

            return {
                'method': method,
                'time': elapsed_time,
                'candidates': len(candidates),
                'top_score': candidates[0]['score'] if candidates else 0,
                'success': True
            }
        else:
            print(f"❌ Ошибка: {response.status_code}")
            print(f"   {response.json().get('detail', 'Unknown error')}")
            return {
                'method': method,
                'time': elapsed_time,
                'success': False
            }

    except Exception as e:
        elapsed_time = time.time() - start_time
        print(f"❌ Исключение: {str(e)}")
        return {
            'method': method,
            'time': elapsed_time,
            'success': False,
            'error': str(e)
        }


def main():
    print("\n" + "="*80)
    print("  🧪 ТЕСТИРОВАНИЕ МЕТОДОВ МАТЧИНГА")
    print("="*80)

    print(f"\n📋 Вакансия: Senior Python Developer")
    print(f"📊 База резюме: все доступные")

    # Тестируем все три метода
    methods = ['embedding', 'llm', 'hybrid']
    results = []

    for method in methods:
        result = test_method(method)
        results.append(result)
        time.sleep(1)  # Небольшая пауза между тестами

    # Сравнение результатов
    print("\n" + "="*80)
    print("  📊 СРАВНИТЕЛЬНАЯ ТАБЛИЦА")
    print("="*80)

    print(f"\n{'Метод':<15} {'Время (сек)':<15} {'Кандидатов':<15} {'Топ Score':<15} {'Статус':<10}")
    print("-" * 80)

    for result in results:
        if result['success']:
            print(f"{result['method']:<15} {result['time']:<15.2f} {result['candidates']:<15} {result['top_score']:<15.4f} {'✅':<10}")
        else:
            print(f"{result['method']:<15} {result['time']:<15.2f} {'-':<15} {'-':<15} {'❌':<10}")

    # Выводы
    print("\n" + "="*80)
    print("  📈 ВЫВОДЫ")
    print("="*80)

    successful_results = [r for r in results if r['success']]

    if len(successful_results) >= 2:
        # Сравнение скорости
        fastest = min(successful_results, key=lambda x: x['time'])
        print(f"\n🚀 Самый быстрый: {fastest['method']} ({fastest['time']:.2f} сек)")

        # Сравнение точности (по топ score)
        most_accurate = max(successful_results, key=lambda x: x['top_score'])
        print(f"🎯 Самый точный: {most_accurate['method']} (score: {most_accurate['top_score']:.4f})")

        # Рекомендация
        hybrid_result = next((r for r in successful_results if r['method'] == 'hybrid'), None)
        if hybrid_result:
            print(f"\n💡 Hybrid метод:")
            print(f"   - Время: {hybrid_result['time']:.2f} сек (средняя скорость)")
            print(f"   - Score: {hybrid_result['top_score']:.4f}")
            print(f"   - Объяснения: ✅ (от LLM)")
            print(f"   - Стоимость: Оптимальная (LLM только для топ-20)")

    print("\n" + "="*80)
    print("  ✅ ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
    print("="*80)

    # Сохранение результатов
    with open('test_hybrid_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print("\n💾 Результаты сохранены в: test_hybrid_results.json\n")


if __name__ == "__main__":
    main()

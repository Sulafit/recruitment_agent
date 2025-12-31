"""
Тестовый скрипт для проверки LLM-based парсинга резюме
"""

import sys
import os
import json

# Добавляем путь к модулям
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.resume_parser import ResumeParser


def test_resume_parsing(file_path: str):
    """
    Тестирует парсинг резюме с использованием LLM
    """
    print(f"\n{'='*80}")
    print(f"Тестирование парсинга: {os.path.basename(file_path)}")
    print(f"{'='*80}\n")

    # Создаем парсер с LLM
    parser_llm = ResumeParser(use_llm=True)

    # Парсим резюме
    print("🔄 Парсинг резюме с использованием LLM...")
    result = parser_llm.parse_file(file_path)

    # Выводим результаты
    print("\n📊 Результаты парсинга:\n")

    print(f"👤 Имя: {result.get('name', 'N/A')}")
    print(f"📧 Email: {result.get('email', 'N/A')}")
    print(f"📱 Телефон: {result.get('phone', 'N/A')}")
    print(f"📍 Локация: {result.get('location', 'N/A')}")
    print(f"⏱️  Лет опыта: {result.get('years_of_experience', 'N/A')}")

    print(f"\n📝 Краткое резюме:")
    summary = result.get('summary', 'N/A')
    if summary:
        print(f"   {summary}")

    print(f"\n🔧 Навыки ({len(result.get('skills', []))}):")
    skills = result.get('skills', [])
    if skills:
        for i, skill in enumerate(skills[:20], 1):  # Показываем первые 20
            print(f"   {i}. {skill}")
        if len(skills) > 20:
            print(f"   ... и еще {len(skills) - 20} навыков")

    print(f"\n💼 Опыт работы ({len(result.get('work_experience', []))}):")
    for i, exp in enumerate(result.get('work_experience', []), 1):
        print(f"\n   {i}. {exp.get('position', 'N/A')} в {exp.get('company', 'N/A')}")
        print(f"      Период: {exp.get('start_date', 'N/A')} - {exp.get('end_date', 'N/A')}")
        if exp.get('duration'):
            print(f"      Длительность: {exp.get('duration')}")
        if exp.get('description'):
            print(f"      Описание: {exp.get('description')[:100]}...")
        if exp.get('responsibilities'):
            print(f"      Обязанности:")
            for resp in exp.get('responsibilities', [])[:3]:
                print(f"        - {resp}")

    print(f"\n🎓 Образование ({len(result.get('education_details', []))}):")
    for i, edu in enumerate(result.get('education_details', []), 1):
        print(f"\n   {i}. {edu.get('degree', 'N/A')} - {edu.get('field_of_study', 'N/A')}")
        print(f"      {edu.get('institution', 'N/A')}")
        print(f"      Год окончания: {edu.get('graduation_year', 'N/A')}")

    print(f"\n🌍 Языки ({len(result.get('languages', []))}):")
    for lang in result.get('languages', []):
        print(f"   - {lang}")

    print(f"\n📜 Сертификаты ({len(result.get('certifications', []))}):")
    for cert in result.get('certifications', []):
        print(f"   - {cert}")

    print(f"\n🚀 Проекты ({len(result.get('projects', []))}):")
    for proj in result.get('projects', []):
        print(f"   - {proj[:100]}...")

    # Сохраняем JSON для детального просмотра
    output_file = f"test_output_{os.path.basename(file_path)}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\n💾 Полный результат сохранен в: {output_file}")

    print(f"\n{'='*80}\n")


def compare_llm_vs_regex(file_path: str):
    """
    Сравнивает LLM-based и regex-based парсинг
    """
    print(f"\n{'='*80}")
    print(f"Сравнение LLM vs Regex: {os.path.basename(file_path)}")
    print(f"{'='*80}\n")

    # LLM парсинг
    parser_llm = ResumeParser(use_llm=True)
    result_llm = parser_llm.parse_file(file_path)

    # Regex парсинг
    parser_regex = ResumeParser(use_llm=False)
    result_regex = parser_regex.parse_file(file_path)

    # Сравнение
    print("📊 Сравнение результатов:\n")

    print(f"{'Поле':<25} {'LLM':<30} {'Regex':<30}")
    print("-" * 85)

    fields = ['name', 'email', 'phone']
    for field in fields:
        llm_val = str(result_llm.get(field, 'N/A'))[:28]
        regex_val = str(result_regex.get(field, 'N/A'))[:28]
        print(f"{field:<25} {llm_val:<30} {regex_val:<30}")

    print(f"{'skills (count)':<25} {len(result_llm.get('skills', [])):<30} {len(result_regex.get('skills', [])):<30}")
    print(f"{'work_experience (count)':<25} {len(result_llm.get('work_experience', [])):<30} {len(result_regex.get('work_experience', [])):<30}")
    print(f"{'education_details (count)':<25} {len(result_llm.get('education_details', [])):<30} {len(result_regex.get('education_details', [])):<30}")

    print(f"\n{'='*80}\n")


if __name__ == "__main__":
    # Путь к резюме для тестирования
    resume_dir = "data/resumes"

    # Тестируем все резюме в директории
    resume_files = [
        os.path.join(resume_dir, f)
        for f in os.listdir(resume_dir)
        if f.endswith(('.pdf', '.txt', '.docx', '.doc'))
    ]

    if not resume_files:
        print("❌ Резюме не найдены в директории data/resumes/")
        sys.exit(1)

    print(f"\n🔍 Найдено {len(resume_files)} резюме для тестирования")

    # Тестируем первое резюме детально
    if resume_files:
        test_resume_parsing(resume_files[0])

        # Сравниваем LLM vs Regex
        # compare_llm_vs_regex(resume_files[0])

    print("✅ Тестирование завершено!")

"""
Простой тестовый скрипт для проверки LLM парсинга через API
"""

import requests
import json

# Сначала проверим текущее состояние резюме
print("🔍 Проверка текущих резюме в системе...")
response = requests.get("http://localhost:8000/resumes")

if response.status_code == 200:
    data = response.json()
    resumes = data.get('resumes', [])
    print(f"\n✅ Найдено {len(resumes)} резюме:\n")

    for i, resume in enumerate(resumes, 1):
        print(f"\n{'='*80}")
        print(f"Резюме #{i}: {resume.get('id')}")
        print(f"{'='*80}")
        print(f"👤 Имя: {resume.get('name', 'N/A')}")
        print(f"📧 Email: {resume.get('email', 'N/A')}")
        print(f"📱 Телефон: {resume.get('phone', 'N/A')}")
        print(f"📍 Локация: {resume.get('location', 'N/A')}")
        print(f"⏱️  Лет опыта: {resume.get('years_of_experience', 'N/A')}")

        summary = resume.get('summary')
        if summary:
            print(f"\n📝 Краткое резюме:")
            print(f"   {summary}")

        skills = resume.get('skills', [])
        print(f"\n🔧 Навыки ({len(skills)}):")
        for j, skill in enumerate(skills[:15], 1):
            print(f"   {j}. {skill}")
        if len(skills) > 15:
            print(f"   ... и еще {len(skills) - 15} навыков")

        work_exp = resume.get('work_experience', [])
        print(f"\n💼 Опыт работы ({len(work_exp)}):")
        for j, exp in enumerate(work_exp, 1):
            print(f"   {j}. {exp.get('position', 'N/A')} в {exp.get('company', 'N/A')}")
            print(f"      {exp.get('start_date', 'N/A')} - {exp.get('end_date', 'N/A')}")

        edu_details = resume.get('education_details', [])
        print(f"\n🎓 Образование ({len(edu_details)}):")
        for j, edu in enumerate(edu_details, 1):
            print(f"   {j}. {edu.get('degree', 'N/A')} - {edu.get('institution', 'N/A')}")

        languages = resume.get('languages', [])
        if languages:
            print(f"\n🌍 Языки: {', '.join(languages)}")

        certs = resume.get('certifications', [])
        if certs:
            print(f"\n📜 Сертификаты ({len(certs)}):")
            for cert in certs:
                print(f"   - {cert}")

        print("\n")

    # Сохраняем детали в файл
    with open('test_output_api.json', 'w', encoding='utf-8') as f:
        json.dump(resumes, f, ensure_ascii=False, indent=2)
    print(f"💾 Полные данные сохранены в: test_output_api.json")

else:
    print(f"❌ Ошибка при получении резюме: {response.status_code}")
    print(response.text)

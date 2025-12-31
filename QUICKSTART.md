# Quick Start Guide

## Быстрый запуск с Docker (Рекомендуется)

1. Убедитесь, что в `.env` указаны все ключи API:
```bash
cat .env
```

2. Запустите проект:
```bash
docker-compose up --build
```

3. Откройте в браузере:
- Frontend: http://localhost:8501
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## Локальный запуск (без Docker)

### Требования
- Python 3.10+
- Tesseract OCR

### Установка Tesseract

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr tesseract-ocr-eng tesseract-ocr-rus poppler-utils
```

**macOS:**
```bash
brew install tesseract tesseract-lang poppler
```

### Запуск

Используйте готовый скрипт:
```bash
./run_local.sh
```

Или вручную:

1. Backend:
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

2. Frontend (в новом терминале):
```bash
cd frontend
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Первые шаги

### 1. Добавьте резюме

**Вариант А**: Вручную
```bash
# Поместите файлы резюме в:
cp your_resume.pdf data/resumes/
```

**Вариант Б**: Из email
- Настройте пароль приложения Gmail в `.env`
- В интерфейсе нажмите "Fetch New Resumes"
- Или через API:
```bash
curl -X POST http://localhost:8000/fetch-resumes
```

### 2. Найдите кандидатов

**Через интерфейс:**
1. Откройте http://localhost:8501
2. Выберите вакансию или введите описание
3. Выберите метод (embedding или llm)
4. Нажмите "Find Candidates"

**Через API:**
```bash
# С использованием ID вакансии
curl "http://localhost:8000/recommendations?job_id=job_001&method=embedding&top_k=5"

# С текстом вакансии
curl "http://localhost:8000/recommendations?job_text=Looking%20for%20Python%20developer&method=llm&top_k=3"
```

## Примеры вакансий

В проекте уже есть 2 примера:
- `data/jobs/python_developer.json` - Python разработчик
- `data/jobs/fullstack_developer.json` - Full Stack разработчик

### Добавить свою вакансию

Создайте файл `data/jobs/my_job.json`:
```json
{
  "id": "job_003",
  "title": "Data Scientist",
  "description": "Описание вакансии",
  "requirements": "Требования",
  "tech_stack": ["Python", "TensorFlow", "SQL"]
}
```

## Методы сопоставления

### Embedding (быстрый)
- Время: 2-5 сек на 100 резюме
- Подходит для: первичной фильтрации
- Бесплатный (HuggingFace API)

### LLM (детальный)
- Время: 10-30 сек на 10 резюме
- Подходит для: финального отбора
- Дает объяснения релевантности
- Использует Mistral API (платный)

## Troubleshooting

**Ошибка подключения к email:**
- Используйте App Password для Gmail
- Проверьте IMAP настройки в `.env`

**Tesseract не найден:**
```bash
# Проверьте установку
tesseract --version

# Установите если нужно
sudo apt-get install tesseract-ocr
```

**Ошибка API ключей:**
- Проверьте `.env` файл
- Убедитесь что ключи валидны

## Поддержка

Для подробной документации см. [README.md](README.md)

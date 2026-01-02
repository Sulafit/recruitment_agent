import pytesseract
from pdf2image import convert_from_path
from PIL import Image
import PyPDF2
import docx
import re
import os
from typing import Dict, List
import logging
from .llm_resume_extractor import LLMResumeExtractor
import subprocess
import hashlib
import json
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ResumeParser:
    def __init__(self, use_llm: bool = True, cache_dir: str = "data/resumes_parsed"):
        """
        Инициализация парсера резюме

        Args:
            use_llm: Если True, использует LLM для извлечения данных (рекомендуется).
                    Если False, использует старый regex-based метод.
            cache_dir: Директория для кэширования распарсенных резюме в JSON формате.
        """
        self.use_llm = use_llm
        self.cache_dir = cache_dir

        # Создаем директорию для кэша если её нет
        if cache_dir:
            os.makedirs(cache_dir, exist_ok=True)
            logger.info(f"Resume cache directory: {cache_dir}")

        if use_llm:
            try:
                self.llm_extractor = LLMResumeExtractor()
                logger.info("LLM-based extraction enabled")
            except Exception as e:
                logger.warning(f"Failed to initialize LLM extractor: {e}. Falling back to regex.")
                self.use_llm = False
                self.llm_extractor = None
        else:
            self.llm_extractor = None

        # Оставляем для fallback и обратной совместимости
        self.skills_keywords = [
            # Programming languages
            'python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'ruby', 'go', 'rust',
            'php', 'swift', 'kotlin', 'scala', 'r', 'matlab',
            # Frameworks
            'django', 'flask', 'fastapi', 'react', 'vue', 'angular', 'spring', 'express',
            'nodejs', 'node.js', 'laravel', 'rails',
            # Databases
            'sql', 'mysql', 'postgresql', 'mongodb', 'redis', 'oracle', 'sqlite',
            # DevOps
            'docker', 'kubernetes', 'jenkins', 'gitlab', 'github', 'aws', 'azure', 'gcp',
            'terraform', 'ansible',
            # ML/AI
            'machine learning', 'deep learning', 'tensorflow', 'pytorch', 'keras',
            'scikit-learn', 'nlp', 'computer vision', 'opencv',
            # Other
            'git', 'linux', 'bash', 'api', 'rest', 'graphql', 'microservices'
        ]

    def parse_file(self, file_path: str) -> Dict:
        """
        Parse resume file and extract structured information

        Использует кэш если файл уже был распарсен.
        Использует LLM для извлечения данных (если use_llm=True),
        иначе использует regex-based метод.
        """
        logger.info(f"Parsing file: {file_path}")

        # 1. Проверяем кэш
        if self.cache_dir:
            cached_data = self._load_from_cache(file_path)
            if cached_data:
                logger.info(f"✓ Cache HIT: Loaded from cache in <1ms")
                return cached_data
            else:
                logger.info(f"✗ Cache MISS: Will parse and cache")

        # Extract text based on file type
        text = self._extract_text(file_path)

        if self.use_llm and self.llm_extractor:
            # Используем LLM для извлечения структурированных данных
            logger.info("Using LLM-based extraction")

            # Сначала получаем fallback данные через regex (на случай если LLM не сможет извлечь что-то)
            fallback_data = {
                'skills': self._extract_skills(text),
                'experience': self._extract_experience(text),
                'education': self._extract_education(text),
                'name': self._extract_name(text),
                'email': self._extract_email(text)
            }

            # Извлекаем данные через LLM с fallback
            llm_data = self.llm_extractor.extract_with_fallback(text, fallback_data)

            result = {
                'raw_text': text,
                **llm_data
            }

            logger.info(f"LLM extracted: {len(result.get('skills', []))} skills, "
                       f"{len(result.get('work_experience', []))} work experiences, "
                       f"{len(result.get('education_details', []))} education entries")
        else:
            # Используем старый regex-based метод
            logger.info("Using regex-based extraction (fallback mode)")
            result = {
                'raw_text': text,
                'skills': self._extract_skills(text),
                'experience': self._extract_experience(text),
                'education': self._extract_education(text),
                'name': self._extract_name(text),
                'email': self._extract_email(text),
                # Добавляем пустые значения для новых полей
                'phone': None,
                'location': None,
                'summary': None,
                'years_of_experience': None,
                'work_experience': [],
                'education_details': [],
                'languages': [],
                'certifications': [],
                'projects': []
            }

            logger.info(f"Regex extracted {len(result['skills'])} skills from resume")

        # 2. Сохраняем в кэш
        if self.cache_dir:
            self._save_to_cache(file_path, result)

        return result

    def _extract_text(self, file_path: str) -> str:
        """Extract text from various file formats"""
        extension = os.path.splitext(file_path)[1].lower()

        try:
            if extension == '.pdf':
                return self._extract_from_pdf(file_path)
            elif extension == '.docx':
                return self._extract_from_docx(file_path)
            elif extension == '.doc':
                return self._extract_from_doc(file_path)
            elif extension in ['.png', '.jpg', '.jpeg']:
                return self._extract_from_image(file_path)
            elif extension == '.txt':
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
            else:
                logger.warning(f"Unsupported file format: {extension}")
                return ""
        except Exception as e:
            logger.error(f"Error extracting text from {file_path}: {e}")
            return ""

    def _extract_from_pdf(self, file_path: str) -> str:
        """Extract text from PDF using PyPDF2 and Tesseract OCR"""
        text = ""

        # Try PyPDF2 first (for text-based PDFs)
        try:
            with open(file_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                for page in pdf_reader.pages:
                    text += page.extract_text()
        except Exception as e:
            logger.warning(f"PyPDF2 extraction failed: {e}")

        # If no text extracted, use OCR
        if len(text.strip()) < 100:
            logger.info("Using Tesseract OCR for PDF")
            try:
                images = convert_from_path(file_path)
                for image in images:
                    text += pytesseract.image_to_string(image, lang='eng+rus')
            except Exception as e:
                logger.error(f"Tesseract OCR failed: {e}")

        return text

    def _extract_from_docx(self, file_path: str) -> str:
        """Extract text from DOCX"""
        try:
            doc = docx.Document(file_path)
            return '\n'.join([paragraph.text for paragraph in doc.paragraphs])
        except Exception as e:
            logger.error(f"Error reading DOCX: {e}")
            return ""

    def _extract_from_doc(self, file_path: str) -> str:
        """Extract text from DOC (old Word format) with multiple fallback methods"""
        text = ""

        # Method 1: Try textract (works with many formats)
        try:
            import textract
            logger.info("Attempting textract extraction for .doc file")
            text = textract.process(file_path).decode('utf-8')
            if text.strip():
                logger.info("Successfully extracted text using textract")
                return text
        except ImportError:
            logger.warning("textract not available, trying other methods")
        except Exception as e:
            logger.warning(f"textract extraction failed: {e}")

        # Method 2: Try antiword (command-line tool)
        try:
            logger.info("Attempting antiword extraction for .doc file")
            result = subprocess.run(
                ['antiword', file_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0 and result.stdout.strip():
                logger.info("Successfully extracted text using antiword")
                return result.stdout
        except FileNotFoundError:
            logger.warning("antiword not installed")
        except Exception as e:
            logger.warning(f"antiword extraction failed: {e}")

        # Method 3: Try LibreOffice conversion (if available)
        try:
            logger.info("Attempting LibreOffice conversion for .doc file")
            # Convert to txt using LibreOffice
            output_dir = os.path.dirname(file_path)
            result = subprocess.run(
                ['soffice', '--headless', '--convert-to', 'txt:Text', '--outdir', output_dir, file_path],
                capture_output=True,
                timeout=60
            )
            if result.returncode == 0:
                txt_path = os.path.splitext(file_path)[0] + '.txt'
                if os.path.exists(txt_path):
                    with open(txt_path, 'r', encoding='utf-8') as f:
                        text = f.read()
                    os.remove(txt_path)  # Clean up
                    if text.strip():
                        logger.info("Successfully extracted text using LibreOffice")
                        return text
        except FileNotFoundError:
            logger.warning("LibreOffice not installed")
        except Exception as e:
            logger.warning(f"LibreOffice conversion failed: {e}")

        # Method 4: Last resort - try python-docx anyway (might be .docx with wrong extension)
        try:
            logger.info("Attempting python-docx extraction (might be .docx with .doc extension)")
            doc = docx.Document(file_path)
            text = '\n'.join([paragraph.text for paragraph in doc.paragraphs])
            if text.strip():
                logger.info("Successfully extracted using python-docx (file was likely .docx)")
                return text
        except Exception as e:
            logger.warning(f"python-docx extraction failed: {e}")

        # If all methods failed
        logger.error(f"All extraction methods failed for .doc file: {file_path}")
        logger.info("Please install one of: textract, antiword, or LibreOffice for .doc support")
        return ""

    def _extract_from_image(self, file_path: str) -> str:
        """Extract text from image using Tesseract OCR"""
        try:
            image = Image.open(file_path)
            return pytesseract.image_to_string(image, lang='eng+rus')
        except Exception as e:
            logger.error(f"Tesseract OCR failed: {e}")
            return ""

    def _extract_skills(self, text: str) -> List[str]:
        """Extract skills from text"""
        text_lower = text.lower()
        found_skills = []

        for skill in self.skills_keywords:
            if skill.lower() in text_lower:
                found_skills.append(skill.title())

        # Remove duplicates while preserving order
        return list(dict.fromkeys(found_skills))

    def _extract_experience(self, text: str) -> str:
        """Extract work experience section"""
        patterns = [
            r'(experience|work experience|employment)(.*?)(education|skills|$)',
            r'(опыт работы|опыт)(.*?)(образование|навыки|$)'
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(2).strip()[:500]

        return ""

    def _extract_education(self, text: str) -> str:
        """Extract education section"""
        patterns = [
            r'(education|academic)(.*?)(experience|skills|$)',
            r'(образование)(.*?)(опыт|навыки|$)'
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(2).strip()[:500]

        return ""

    def _extract_name(self, text: str) -> str:
        """Extract candidate name (first line usually)"""
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if len(line) > 3 and len(line) < 50:
                # Simple heuristic: name is usually in first few lines
                return line
        return ""

    def _extract_email(self, text: str) -> str:
        """Extract email address"""
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        match = re.search(email_pattern, text)
        return match.group(0) if match else ""

    # ========== Cache Methods ==========

    def _get_file_hash(self, file_path: str) -> str:
        """
        Получить MD5 хэш файла для проверки изменений

        Args:
            file_path: Путь к файлу резюме

        Returns:
            MD5 хэш файла в виде hex строки
        """
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, 'rb') as f:
                # Читаем файл блоками для эффективности с большими файлами
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            logger.error(f"Error calculating hash for {file_path}: {e}")
            return ""

    def _get_cache_path(self, file_path: str) -> str:
        """
        Получить путь к кэш-файлу для данного резюме

        Args:
            file_path: Путь к исходному файлу резюме

        Returns:
            Путь к JSON файлу кэша
        """
        file_name = os.path.basename(file_path)
        # Убираем расширение и добавляем .json
        cache_name = os.path.splitext(file_name)[0] + '.json'
        return os.path.join(self.cache_dir, cache_name)

    def _load_from_cache(self, file_path: str) -> Dict:
        """
        Загрузить распарсенные данные из кэша если они актуальны

        Args:
            file_path: Путь к исходному файлу резюме

        Returns:
            Словарь с распарсенными данными или None если кэш отсутствует/устарел
        """
        cache_path = self._get_cache_path(file_path)

        # Проверяем существование кэш-файла
        if not os.path.exists(cache_path):
            return None

        try:
            # Загружаем кэш
            with open(cache_path, 'r', encoding='utf-8') as f:
                cached = json.load(f)

            # Проверяем актуальность кэша (сравниваем хэш исходного файла)
            current_hash = self._get_file_hash(file_path)
            cached_hash = cached.get('file_hash', '')

            if current_hash != cached_hash:
                logger.info(f"Cache outdated (file modified): {os.path.basename(file_path)}")
                return None

            # Кэш актуален!
            return cached.get('data')

        except Exception as e:
            logger.warning(f"Error loading cache for {file_path}: {e}")
            return None

    def _save_to_cache(self, file_path: str, parsed_data: Dict) -> None:
        """
        Сохранить распарсенные данные в кэш

        Args:
            file_path: Путь к исходному файлу резюме
            parsed_data: Распарсенные данные для сохранения
        """
        cache_path = self._get_cache_path(file_path)

        try:
            # Получаем хэш файла
            file_hash = self._get_file_hash(file_path)

            # Формируем данные для кэша
            cache_data = {
                'file_hash': file_hash,
                'file_name': os.path.basename(file_path),
                'parsed_at': datetime.now().isoformat(),
                'parser_version': '2.0',  # Версия парсера (для будущей совместимости)
                'data': parsed_data
            }

            # Сохраняем в JSON
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)

            logger.info(f"✓ Saved to cache: {os.path.basename(cache_path)}")

        except Exception as e:
            logger.error(f"Error saving cache for {file_path}: {e}")

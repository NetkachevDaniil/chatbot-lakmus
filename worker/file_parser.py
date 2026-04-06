import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class FileParser:
    """Парсер для различных типов файлов"""
    
    SUPPORTED_FORMATS = {
        "txt": "text/plain",
        "pdf": "application/pdf",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg"
    }
    
    @staticmethod
    def parse_file(file_path: str) -> str:
        """
        Парсит файл и возвращает текстовое содержимое
        
        Args:
            file_path: Путь к файлу
            
        Returns:
            Текстовое содержимое файла
            
        Raises:
            FileParsingError: При ошибке парсинга файла
        """
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Файл не найден: {file_path}")
            
            file_ext = Path(file_path).suffix.lower().lstrip(".")
            
            if file_ext == "txt":
                return FileParser._parse_txt(file_path)
            elif file_ext == "pdf":
                return FileParser._parse_pdf(file_path)
            elif file_ext == "docx":
                return FileParser._parse_docx(file_path)
            elif file_ext in ["png", "jpg", "jpeg"]:
                return FileParser._parse_image(file_path)
            else:
                raise ValueError(f"Неподдерживаемый формат файла: .{file_ext}")
        
        except Exception as e:
            logger.error(f"Ошибка при парсинге файла {file_path}: {e}")
            raise
    
    @staticmethod
    def _parse_txt(file_path: str) -> str:
        """Парсинг текстового файла"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            # Попытка с другой кодировкой
            with open(file_path, 'r', encoding='latin-1') as f:
                return f.read()
    
    @staticmethod
    def _parse_pdf(file_path: str) -> str:
        """Парсинг PDF файла"""
        try:
            import PyPDF2
            text = ""
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                for page_num in range(len(reader.pages)):
                    page = reader.pages[page_num]
                    text += page.extract_text()
            return text
        except ImportError:
            return f"[Требуется PyPDF2 для парсинга PDF файлов. Файл: {file_path}]"
    
    @staticmethod
    def _parse_docx(file_path: str) -> str:
        """Парсинг DOCX файла"""
        try:
            from docx import Document
            doc = Document(file_path)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text
        except ImportError:
            return f"[Требуется python-docx для парсинга DOCX файлов. Файл: {file_path}]"
    
    @staticmethod
    def _parse_image(file_path: str) -> str:
        """Парсинг изображения с помощью OCR"""
        try:
            from PIL import Image
            import pytesseract
            
            image = Image.open(file_path)
            text = pytesseract.image_to_string(image, lang='rus')
            return text if text.strip() else "[Текст в изображении не найден]"
        except ImportError:
            return f"[Требуется Pillow и pytesseract для OCR. Файл: {file_path}]"
    
    @staticmethod
    def validate_file(file_path: str, max_size: int = 50 * 1024 * 1024) -> bool:
        """
        Валидирует файл перед парсингом
        
        Args:
            file_path: Путь к файлу
            max_size: Максимальный размер файла в байтах
            
        Returns:
            True если файл валиден
            
        Raises:
            ValueError: Если файл невалиден
        """
        if not os.path.exists(file_path):
            raise ValueError(f"Файл не существует: {file_path}")
        
        file_size = os.path.getsize(file_path)
        if file_size > max_size:
            raise ValueError(f"Размер файла ({file_size}) превышает максимум ({max_size})")
        
        file_ext = Path(file_path).suffix.lower().lstrip(".")
        if file_ext not in FileParser.SUPPORTED_FORMATS:
            raise ValueError(f"Неподдерживаемый формат файла: .{file_ext}")
        
        return True

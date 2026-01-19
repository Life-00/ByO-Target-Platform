"""
Document Processor
PDF and text document processing utilities
"""

import logging
from typing import List, Dict, Any
from pathlib import Path

import pandas as pd

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """PDF 및 텍스트 문서 처리 도구"""

    @staticmethod
    async def extract_text(file_path: str) -> str:
        """
        PDF 또는 텍스트 파일에서 텍스트 추출

        Args:
            file_path: 파일 경로

        Returns:
            추출된 텍스트
        """
        try:
            path = Path(file_path)

            if not path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")

            if path.suffix.lower() == ".pdf":
                return await DocumentProcessor._extract_pdf_text(file_path)
            elif path.suffix.lower() in [".txt", ".md"]:
                with open(file_path, "r", encoding="utf-8") as f:
                    return f.read()
            else:
                raise ValueError(f"Unsupported file format: {path.suffix}")

        except Exception as e:
            logger.error(f"[DocumentProcessor] Error extracting text: {str(e)}")
            raise

    @staticmethod
    async def _extract_pdf_text(file_path: str) -> str:
        """PyMuPDF로 PDF 텍스트 추출"""
        if fitz is None:
            raise ImportError("PyMuPDF not installed. Install with: pip install PyMuPDF")

        try:
            pdf_document = fitz.open(file_path)
            text_parts = []

            for page_num in range(len(pdf_document)):
                page = pdf_document[page_num]
                text = page.get_text()
                if text.strip():
                    text_parts.append(f"--- Page {page_num + 1} ---\n{text}")

            pdf_document.close()
            return "\n\n".join(text_parts)

        except Exception as e:
            logger.error(f"[DocumentProcessor] PDF extraction error: {str(e)}")
            raise

    @staticmethod
    async def extract_tables(file_path: str) -> List[pd.DataFrame]:
        """
        PDF 또는 문서에서 표 추출

        Args:
            file_path: 파일 경로

        Returns:
            DataFrame 리스트
        """
        try:
            path = Path(file_path)

            if path.suffix.lower() == ".pdf":
                return await DocumentProcessor._extract_pdf_tables(file_path)
            elif path.suffix.lower() in [".xlsx", ".xls"]:
                return await DocumentProcessor._extract_excel_tables(file_path)
            else:
                logger.warning(f"Table extraction not supported for {path.suffix}")
                return []

        except Exception as e:
            logger.error(f"[DocumentProcessor] Error extracting tables: {str(e)}")
            raise

    @staticmethod
    async def _extract_pdf_tables(file_path: str) -> List[pd.DataFrame]:
        """PDF에서 표 추출"""
        try:
            # 간단한 구현: tabula-py 또는 pdfplumber 사용 권장
            # 여기서는 기본 구조만 제공
            logger.info(f"[DocumentProcessor] Extracting tables from PDF: {file_path}")

            # TODO: tabula-py 통합
            # import tabula
            # tables = tabula.read_pdf(file_path, pages='all')
            # return tables

            return []

        except Exception as e:
            logger.error(f"[DocumentProcessor] PDF table extraction error: {str(e)}")
            raise

    @staticmethod
    async def _extract_excel_tables(file_path: str) -> List[pd.DataFrame]:
        """Excel 파일에서 표 추출"""
        try:
            excel_file = pd.ExcelFile(file_path)
            tables = []

            for sheet_name in excel_file.sheet_names:
                df = pd.read_excel(file_path, sheet_name=sheet_name)
                tables.append(df)
                logger.info(f"[DocumentProcessor] Extracted table from sheet: {sheet_name}")

            return tables

        except Exception as e:
            logger.error(f"[DocumentProcessor] Excel extraction error: {str(e)}")
            raise

    @staticmethod
    async def extract_metadata(file_path: str) -> Dict[str, Any]:
        """
        파일 메타데이터 추출 (저자, 연도, 제목 등)

        Args:
            file_path: 파일 경로

        Returns:
            메타데이터 딕셔너리
        """
        try:
            path = Path(file_path)
            metadata = {
                "filename": path.name,
                "file_type": path.suffix,
                "file_size": path.stat().st_size,
            }

            if path.suffix.lower() == ".pdf":
                return await DocumentProcessor._extract_pdf_metadata(file_path, metadata)
            else:
                logger.info(f"[DocumentProcessor] Limited metadata for {path.suffix}")
                return metadata

        except Exception as e:
            logger.error(f"[DocumentProcessor] Error extracting metadata: {str(e)}")
            return {}

    @staticmethod
    async def _extract_pdf_metadata(file_path: str, base_metadata: Dict) -> Dict:
        """PDF 메타데이터 추출"""
        if fitz is None:
            return base_metadata

        try:
            pdf_document = fitz.open(file_path)
            pdf_metadata = pdf_document.metadata

            if pdf_metadata:
                base_metadata.update({
                    "title": pdf_metadata.get("title", "Unknown"),
                    "author": pdf_metadata.get("author", "Unknown"),
                    "subject": pdf_metadata.get("subject", "Unknown"),
                    "creator": pdf_metadata.get("creator", "Unknown"),
                    "pages": len(pdf_document),
                })

            pdf_document.close()
            return base_metadata

        except Exception as e:
            logger.error(f"[DocumentProcessor] PDF metadata extraction error: {str(e)}")
            return base_metadata

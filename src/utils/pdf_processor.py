"""
PDF 텍스트 추출 및 전처리 모듈

이 모듈은 PDF 파일에서 텍스트를 추출하고 전처리하는 기능을 제공합니다.
Grobid를 사용한 고급 파싱과 기본 텍스트 추출 방법을 모두 지원합니다.
"""

import os
import re
import logging
import tempfile
from typing import Dict, List, Any, Optional, Union, Tuple
import requests
from bs4 import BeautifulSoup

# PDF 텍스트 추출을 위한 라이브러리
try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

# PyMuPDF 라이브러리 (fitz)
try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

# Grobid Python 클라이언트 (선택적)
try:
    from grobid_client.grobid_client import GrobidClient
    GROBID_CLIENT_AVAILABLE = True
except ImportError:
    GROBID_CLIENT_AVAILABLE = False

logger = logging.getLogger(__name__)

class PDFProcessor:
    """
    PDF 처리 클래스
    
    PDF 파일에서 텍스트를 추출하고 전처리하는 기능 제공
    """
    
    def __init__(self, 
                 use_grobid: bool = False, 
                 grobid_url: str = "http://localhost:8070",
                 extraction_method: str = "pymupdf",
                 temp_dir: Optional[str] = None):
        """
        PDF 프로세서 초기화
        
        Args:
            use_grobid: Grobid 사용 여부
            grobid_url: Grobid 서버 URL
            extraction_method: 텍스트 추출 방법 ('pymupdf', 'pdfplumber')
            temp_dir: 임시 파일 디렉토리
        """
        self.use_grobid = use_grobid
        self.grobid_url = grobid_url
        self.temp_dir = temp_dir
        self.extraction_method = extraction_method
        
        # 추출 방법 가용성 검사
        if extraction_method == "pymupdf" and not PYMUPDF_AVAILABLE:
            logger.warning("PyMuPDF(fitz)가 설치되지 않았습니다. pdfplumber로 전환합니다.")
            self.extraction_method = "pdfplumber"
        
        if self.extraction_method == "pdfplumber" and not PDFPLUMBER_AVAILABLE:
            logger.warning("pdfplumber가 설치되지 않았습니다. 텍스트 추출이 제한될 수 있습니다.")
        
        # Grobid 초기화 상태
        self.grobid_initialized = False
        
        # Grobid 사용 설정인 경우 초기화 시도
        if use_grobid:
            self.grobid_initialized = self._initialize_grobid()
            if not self.grobid_initialized:
                logger.warning("Grobid 초기화 실패. 기본 텍스트 추출 방식으로 전환합니다.")
                self.use_grobid = False
    
    def _initialize_grobid(self) -> bool:
        """
        Grobid 클라이언트 초기화
        
        Returns:
            초기화 성공 여부
        """
        # grobid-client 라이브러리 사용 시
        if GROBID_CLIENT_AVAILABLE:
            try:
                self.grobid_client = GrobidClient(config_path=None)
                self.grobid_client.base_url = self.grobid_url
                logger.info(f"Grobid 클라이언트 초기화 완료: {self.grobid_url}")
                return True
            except Exception as e:
                logger.error(f"Grobid 클라이언트 초기화 실패: {str(e)}")
                return False
        
        # 라이브러리 없이 REST API 직접 사용
        try:
            # 서버 상태 확인
            response = requests.get(f"{self.grobid_url}/api/isalive")
            if response.status_code == 200 and response.text == "true":
                logger.info(f"Grobid 서버 연결 성공: {self.grobid_url}")
                return True
            else:
                logger.error(f"Grobid 서버 응답 오류: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"Grobid 서버 연결 실패: {str(e)}")
            return False
    
    def process_pdf(self, pdf_path: str) -> str:
        """
        PDF 파일을 처리하여 텍스트 추출 및 전처리
        
        Args:
            pdf_path: PDF 파일 경로
            
        Returns:
            추출 및 전처리된 텍스트
        """
        if not os.path.exists(pdf_path):
            logger.error(f"PDF 파일을 찾을 수 없음: {pdf_path}")
            return ""
        
        logger.info(f"PDF 처리 시작: {pdf_path}")
        
        # Grobid를 사용하는 경우
        if self.use_grobid and self.grobid_initialized:
            text = self._extract_text_with_grobid(pdf_path)
            if text:
                return text
            else:
                logger.warning("Grobid로 텍스트 추출 실패. 기본 방식으로 전환합니다.")
        
        # 기본 PDF 텍스트 추출
        text = self._extract_text_basic(pdf_path)
        
        # 추출된 텍스트 전처리
        text = self._preprocess_text(text)
        
        logger.info(f"PDF 처리 완료: {len(text)} 자")
        return text
    
    def _extract_text_with_grobid(self, pdf_path: str) -> str:
        """
        Grobid를 사용하여 PDF에서 텍스트 추출
        
        Args:
            pdf_path: PDF 파일 경로
            
        Returns:
            추출된 텍스트 (실패 시 빈 문자열)
        """
        logger.info(f"Grobid로 텍스트 추출 시작: {pdf_path}")
        
        try:
            # 파일 존재 확인
            if not os.path.exists(pdf_path):
                logger.error(f"PDF 파일을 찾을 수 없음: {pdf_path}")
                return ""
            
            # grobid-client 라이브러리 사용 시
            if GROBID_CLIENT_AVAILABLE and hasattr(self, 'grobid_client'):
                # 임시 출력 디렉토리 생성
                with tempfile.TemporaryDirectory() as temp_dir:
                    # Grobid 처리
                    self.grobid_client.process_pdf(
                        "processFulltextDocument",
                        input_path=os.path.dirname(pdf_path),
                        output_path=temp_dir,
                        n=1,
                        consolidate_citations=True,
                        force=True
                    )
                    
                    # 결과 파일 경로
                    base_name = os.path.basename(pdf_path)
                    xml_file = os.path.join(temp_dir, f"{os.path.splitext(base_name)[0]}.tei.xml")
                    
                    # XML 파일 파싱
                    if os.path.exists(xml_file):
                        return self._parse_grobid_xml(xml_file)
            
            # REST API 직접 사용 (라이브러리 없을 때)
            with open(pdf_path, 'rb') as pdf_file:
                files = {'input': (os.path.basename(pdf_path), pdf_file, 'application/pdf')}
                response = requests.post(
                    f"{self.grobid_url}/api/processFulltextDocument",
                    files=files
                )
                
                if response.status_code != 200:
                    logger.error(f"Grobid 응답 오류: {response.status_code}")
                    return ""
                
                # XML 문자열에서 텍스트 추출
                return self._parse_grobid_xml_content(response.content)
                
        except Exception as e:
            logger.error(f"Grobid 텍스트 추출 실패: {str(e)}")
            return ""
    
    def _parse_grobid_xml(self, xml_path: str) -> str:
        """
        Grobid XML 파일 파싱
        
        Args:
            xml_path: XML 파일 경로
            
        Returns:
            추출된 텍스트
        """
        try:
            with open(xml_path, 'r', encoding='utf-8') as f:
                xml_content = f.read()
            return self._parse_grobid_xml_content(xml_content)
        except Exception as e:
            logger.error(f"Grobid XML 파일 파싱 실패: {str(e)}")
            return ""
    
    def _parse_grobid_xml_content(self, xml_content: Union[str, bytes]) -> str:
        """
        Grobid XML 콘텐츠 파싱
        
        Args:
            xml_content: XML 콘텐츠 (문자열 또는 바이트)
            
        Returns:
            추출된 텍스트
        """
        try:
            # BeautifulSoup으로 XML 파싱
            soup = BeautifulSoup(xml_content, 'xml')
            if not soup:
                return ""
            
            text_parts = []
            
            # 제목 추출
            title = soup.find('titleStmt')
            if title:
                title_text = title.find('title')
                if title_text:
                    text_parts.append(f"# {title_text.get_text().strip()}")
            
            # 초록 추출
            abstract = soup.find('abstract')
            if abstract:
                text_parts.append("\n## 초록")
                text_parts.append(abstract.get_text().strip())
            
            # 본문 추출
            body = soup.find('body')
            if body:
                # 각 섹션 처리
                for div in body.find_all('div'):
                    # 섹션 헤더 추출
                    head = div.find('head')
                    if head:
                        section_title = head.get_text().strip()
                        if section_title:
                            level = min(len(div.find_parents('div')) + 2, 6)  # 중첩 레벨에 따라 헤딩 레벨 결정
                            text_parts.append(f"\n{'#' * level} {section_title}")
                    
                    # 단락 추출
                    for p in div.find_all('p'):
                        para_text = p.get_text().strip()
                        if para_text:
                            text_parts.append(para_text)
            
            # 참고문헌 추출
            biblio = soup.find('listBibl')
            if biblio:
                text_parts.append("\n## 참고문헌")
                for ref in biblio.find_all('biblStruct'):
                    ref_text = ref.get_text().strip()
                    if ref_text:
                        text_parts.append(f"- {ref_text}")
            
            # 최종 텍스트 조합
            return "\n\n".join(text_parts)
            
        except Exception as e:
            logger.error(f"Grobid XML 콘텐츠 파싱 실패: {str(e)}")
            return ""
    
    def _extract_text_basic(self, pdf_path: str) -> str:
        """
        기본적인 방법으로 PDF에서 텍스트 추출
        
        Args:
            pdf_path: PDF 파일 경로
            
        Returns:
            추출된 텍스트
        """
        logger.info(f"기본 방식으로 텍스트 추출 시작: {pdf_path}, 방법: {self.extraction_method}")
        
        text = ""
        
        try:
            # PyMuPDF 사용
            if self.extraction_method == "pymupdf" and PYMUPDF_AVAILABLE:
                doc = fitz.open(pdf_path)
                text_parts = []
                
                for page_num in range(len(doc)):
                    page = doc.load_page(page_num)
                    text_parts.append(page.get_text())
                
                text = "\n".join(text_parts)
                doc.close()
            
            # pdfplumber 사용
            elif self.extraction_method == "pdfplumber" and PDFPLUMBER_AVAILABLE:
                with pdfplumber.open(pdf_path) as pdf:
                    text_parts = []
                    for page in pdf.pages:
                        text_parts.append(page.extract_text() or "")
                    text = "\n".join(text_parts)
            
            # 추출 실패
            else:
                logger.error(f"텍스트 추출 실패: 지원되는 라이브러리 없음")
                return ""
            
            # 기본 정리
            text = text.strip()
            return text
            
        except Exception as e:
            logger.error(f"기본 텍스트 추출 실패: {str(e)}")
            return ""
    
    def _preprocess_text(self, text: str) -> str:
        """
        추출된 텍스트 전처리
        
        Args:
            text: 원본 텍스트
            
        Returns:
            전처리된 텍스트
        """
        if not text:
            return ""
        
        # 1. 여러 줄 바꿈 정리
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # 2. 불필요한 공백 제거 (줄 시작과 끝)
        text = re.sub(r'^ +| +$', '', text, flags=re.MULTILINE)
        
        # 3. 하이픈으로 나뉜 단어 결합
        text = re.sub(r'(\w)-\n(\w)', r'\1\2', text)
        
        # 4. 잘린 문장 결합 (단, 문단 구분은 유지)
        text = re.sub(r'([^.\n])\n([a-z가-힣])', r'\1 \2', text)
        
        # 5. 페이지 번호 및 헤더/푸터 패턴 제거
        # 일반적인 페이지 번호 패턴
        text = re.sub(r'\n\s*\d+\s*\n', '\n', text)
        
        # 일반적인 헤더/푸터 패턴 (반복되는 짧은 라인)
        lines = text.split('\n')
        filtered_lines = []
        header_footer_pattern = re.compile(r'^[\d\s\-_]{1,20}$|^[^a-zA-Z가-힣0-9]{1,5}$')
        
        for i, line in enumerate(lines):
            # 짧은 줄이고 숫자나 특수 기호만 있는 경우 제외
            if header_footer_pattern.match(line):
                continue
                
            # 상단/하단 5줄 내에서 반복되는 라인 제외
            repeats_in_doc = sum(1 for l in lines if l == line)
            if repeats_in_doc > 3 and len(line) < 50:
                page_positions = [j for j, l in enumerate(lines) if l == line]
                # 첫 페이지와 마지막 페이지에 나타나면 헤더/푸터로 간주
                if page_positions and (page_positions[0] < 5 or (len(lines) - page_positions[-1]) < 5):
                    continue
            
            filtered_lines.append(line)
        
        text = '\n'.join(filtered_lines)
        
        # 6. URL 및 이메일 주소 형식 보존
        # (특별한 처리 없이도 일반적으로 보존됨)
        
        # 7. 텍스트 인코딩 이슈 수정 (특수문자 복원)
        text = text.replace('â', "'")
        text = text.replace('â', '"')
        text = text.replace('â', '"')
        
        # 8. 한글 문장에서 영어, 숫자와 한글 사이에 공백 추가
        text = self._insert_spaces(text)
        
        # 9. 최종 정리 (중복 공백 제거)
        text = re.sub(r' {2,}', ' ', text)
        
        return text.strip()
    
    def _insert_spaces(self, text: str) -> str:
        """
        한글과 영어/숫자 사이에 공백 추가
        
        Args:
            text: 원본 텍스트
            
        Returns:
            공백이 추가된 텍스트
        """
        # 한글 유니코드 범위: [가-힣]
        # 영어: [a-zA-Z]
        # 숫자: [0-9]
        
        # 1. 한글 뒤에 영어/숫자가 오는 경우 공백 추가
        text = re.sub(r'([가-힣])([a-zA-Z0-9])', r'\1 \2', text)
        
        # 2. 영어/숫자 뒤에 한글이 오는 경우 공백 추가
        text = re.sub(r'([a-zA-Z0-9])([가-힣])', r'\1 \2', text)
        
        # 예외 케이스: 괄호, 쉼표, 마침표 등의 문장 부호는 공백을 추가하지 않음
        text = re.sub(r' (?=[.,;:!?)\]}])', '', text)
        text = re.sub(r'(?<=[({[\s]) ', '', text)
        
        return text


def process_pdf(pdf_path: str, use_grobid: bool = False, grobid_url: str = "http://localhost:8070", extraction_method: str = "pymupdf") -> str:
    """
    PDF 파일을 처리하여 텍스트 추출 및 전처리하는 간편 함수
    
    Args:
        pdf_path: PDF 파일 경로
        use_grobid: Grobid 사용 여부
        grobid_url: Grobid 서버 URL
        extraction_method: 텍스트 추출 방법 ('pymupdf', 'pdfplumber')
        
    Returns:
        추출 및 전처리된 텍스트
    """
    processor = PDFProcessor(
        use_grobid=use_grobid,
        grobid_url=grobid_url,
        extraction_method=extraction_method
    )
    return processor.process_pdf(pdf_path) 
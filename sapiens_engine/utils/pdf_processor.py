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
                abstract_text = abstract.get_text().strip()
                if abstract_text:
                    text_parts.append("## 초록")
                    text_parts.append(abstract_text)
            
            # 본문 추출
            body = soup.find('body')
            if body:
                # 섹션별 처리
                for div in body.find_all(['div', 'head']):
                    # 섹션 제목
                    head = div.find('head')
                    if head:
                        head_text = head.get_text().strip()
                        if head_text:
                            text_parts.append(f"## {head_text}")
                    
                    # 문단 추출
                    for p in div.find_all('p'):
                        p_text = p.get_text().strip()
                        if p_text:
                            text_parts.append(p_text)
                
                # 문단 직접 추출 (섹션 구조가 없는 경우)
                if not text_parts or len(text_parts) <= 2:  # 제목과 초록만 있는 경우
                    paragraphs = body.find_all('p')
                    for p in paragraphs:
                        p_text = p.get_text().strip()
                        if p_text:
                            text_parts.append(p_text)
            
            # 표와 그림 캡션 추출
            figures = soup.find_all('figure')
            for fig in figures:
                caption = fig.find('figDesc')
                if caption:
                    fig_text = caption.get_text().strip()
                    if fig_text:
                        text_parts.append(f"[그림: {fig_text}]")
            
            tables = soup.find_all('table')
            for table in tables:
                caption = table.find('head')
                if caption:
                    table_text = caption.get_text().strip()
                    if table_text:
                        text_parts.append(f"[표: {table_text}]")
            
            # 텍스트 조합
            result = "\n\n".join(text_parts)
            return result
            
        except Exception as e:
            logger.error(f"Grobid XML 콘텐츠 파싱 실패: {str(e)}")
            return ""
    
    def _extract_text_basic(self, pdf_path: str) -> str:
        """
        기본 방식으로 PDF에서 텍스트 추출
        
        Args:
            pdf_path: PDF 파일 경로
            
        Returns:
            추출된 텍스트
        """
        logger.info(f"기본 방식으로 텍스트 추출 시작: {pdf_path} (방식: {self.extraction_method})")
        
        # PyMuPDF 방식 사용
        if self.extraction_method == "pymupdf" and PYMUPDF_AVAILABLE:
            try:
                text = ""
                with fitz.open(pdf_path) as doc:
                    for page in doc:
                        # 블록 단위로 텍스트 추출 (레이아웃 보존)
                        blocks = page.get_text("blocks")
                        for block in blocks:
                            # 이미지 블록은 건너뜀 (인덱스 6이 0이 아닌 경우)
                            if block[6] == 0:  # 텍스트 블록
                                block_text = block[4]
                                if block_text.strip():
                                    text += block_text + "\n\n"
                
                # 여러 줄바꿈 정리
                text = re.sub(r'\n{3,}', '\n\n', text)
                return text
                
            except Exception as e:
                logger.error(f"PyMuPDF 텍스트 추출 실패: {str(e)}")
                if PDFPLUMBER_AVAILABLE:
                    logger.info("pdfplumber로 전환합니다.")
                else:
                    return ""
        
        # PDFPlumber 방식 사용
        if PDFPLUMBER_AVAILABLE:
            try:
                text = ""
                with pdfplumber.open(pdf_path) as pdf:
                    for page in pdf.pages:
                        page_text = page.extract_text() or ""
                        text += page_text + "\n\n"
                
                # 여러 줄바꿈 정리
                text = re.sub(r'\n{3,}', '\n\n', text)
                return text
                
            except Exception as e:
                logger.error(f"PDFPlumber 텍스트 추출 실패: {str(e)}")
                return ""
        
        logger.error("적합한 PDF 텍스트 추출 방법이 없습니다.")
        return ""
    
    def _preprocess_text(self, text: str) -> str:
        """
        추출된 텍스트 전처리
        
        Args:
            text: 추출된 원본 텍스트
            
        Returns:
            전처리된 텍스트
        """
        if not text:
            return ""
        
        # 0. 줄바꿈 정리 (문장 중간의 줄바꿈은 공백으로 변환, 문단 구분은 유지)
        # 먼저, 여러 개의 연속된 줄바꿈을 임시 표시자로 변환 (문단 구분으로 유지하기 위함)
        text = re.sub(r'\n{2,}', ' __PARAGRAPH_BREAK__ ', text)
        
        # PDF에서 단어가 줄바꿈으로 하이픈으로 분리된 경우 처리 (예: exam- ple → example)
        # 특히 "- " 패턴 (하이픈 뒤에 공백)이 있는 경우를 처리
        text = re.sub(r'(\w+)-\s+(\w+)', r'\1\2', text)
        
        # 줄바꿈을 공백으로 변환 (문장 중간의 줄바꿈)
        text = re.sub(r'\n', ' ', text)
        
        # 임시 표시자를 두 개의 줄바꿈으로 다시 변환 (문단 구분 복원)
        text = re.sub(r'__PARAGRAPH_BREAK__', '\n\n', text)
        
        # 1. 이메일 주소와 웹사이트 제거
        text = re.sub(r'\S+@\S+\.\S+', '', text)
        text = re.sub(r'emails?\s*:\s*\S+@\S+\.\S+', '', text, flags=re.IGNORECASE)
        text = re.sub(r'https?://\S+|www\.\S+', '', text)
        
        # 2. 학술 논문 특수 패턴 제거
        # DOI 제거
        text = re.sub(r'doi\s*:\s*[\d\.]+\/[\w\.]+', '', text, flags=re.IGNORECASE)
        
        # 2-1. 페이지 번호 패턴 제거 
        text = re.sub(r'Page\s+\d+\s+of\s+\d+', '', text)
        text = re.sub(r'-\s*\d+\s*-', '', text)
        text = re.sub(r'\b\d+\s*[-–]\s*\d+\b', '', text)  # 페이지 범위
        
        # 2-2. 학술지 정보 제거
        journal_patterns = [
            r'©\s*\w+\s*\w+\s*\w+\s*\d{4}',  # © COPYRIGHT INFO
            r'article reuse guidelines\s*:.*$',
            r'journals?\.\s*sagepub\.com.*$',
            r'the linacre quarterly.*$',
            r'\d{4}\s*by\s*\w+\s*\w+\s*association',
        ]
        for pattern in journal_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.MULTILINE)
        
        # 2-3. 저자 정보 및 기관 정보 정리
        # 괄호 안의 기관 정보
        text = re.sub(r'\(\s*university\s+of\s+[\w\s,]+\)', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\(\s*[\w\s]+\s+university[\w\s,]*\)', '', text, flags=re.IGNORECASE)
        text = re.sub(r'corresponding\s+author\s*:.*?\.', '', text, flags=re.IGNORECASE | re.DOTALL)
        
        # 3. 학위 정보 제거
        degree_patterns = [
            r'\b[A-Za-z]{2,5}\s*\(\s*[\w\s,]+\s*\)',  # PhD (Harvard University)
            r'\b[A-Za-z]{2,5}\s+hons\.',  # BSc hons.
        ]
        for pattern in degree_patterns:
            text = re.sub(pattern, '', text)
        
        # 4. 주소 정보 제거
        address_pattern = r'\d+\s*[–-]\s*\d+\s*[\w\s]+,\s*\w+,\s*\w+\s*\d{4,5},\s*\w+'
        text = re.sub(address_pattern, '', text)
        
        # 5. 헤더/푸터로 의심되는 반복 패턴 제거
        lines = text.split('\n')
        filtered_lines = []
        header_footer_candidates = set()
        
        # 반복되는 줄 식별
        for line in lines:
            line = line.strip()
            if line and len(line) > 5:  # 짧은 줄 무시
                if lines.count(line) > 2:  # 3번 이상 반복되면 헤더/푸터로 간주
                    header_footer_candidates.add(line)
        
        # 헤더/푸터가 아닌 줄만 유지
        for line in lines:
            line = line.strip()
            if line and line not in header_footer_candidates:
                filtered_lines.append(line)
        
        # 6. 연속된 공백 정리
        text = '\n'.join(filtered_lines)
        text = re.sub(r' {2,}', ' ', text)
        
        # 7. 단어 사이에 공백이 없는 경우 처리 (뭉개진 단어 탐지 및 수정)
        text = re.sub(r'([a-zA-Z]{15,})', lambda m: self._insert_spaces(m.group(1)), text)
        
        # 8. 하이픈으로 분리된 단어 결합
        # 8.1 줄바꿈과 함께 하이픈으로 분리된 단어 결합
        text = re.sub(r'(\w+)-\n(\w+)', r'\1\2', text)
        
        # 8.2 하이픈과 공백으로 분리된 단어 결합 (예: trans- humanist → transhumanist)
        text = re.sub(r'(\w+)-\s+(\w+)', r'\1\2', text)
        
        # 8.3 하이픈으로 분리된 단어 중 명확한 패턴 결합 (문장 중간에 있는 하이픈으로 분리된 단어)
        # 학술 논문에서 자주 사용되는 복합어 패턴
        compound_patterns = [
            r'(trans|post|pre|non|anti|pro|inter|intra|multi|over|under|sub|super|re|co|de)\s*-\s*([\w]+)',
            r'(human|self|world|mind|body|life|time|space|based|centered|like|related)\s*-\s*([\w]+)',
            r'([\w]+)\s*-\s*(based|like|specific|oriented|centered|driven|related|free)'
        ]
        
        for pattern in compound_patterns:
            text = re.sub(pattern, r'\1\2', text)
        
        # 9. 특수 유니코드 문자 정규화
        special_chars = {
            'ﬁ': 'fi', 'ﬂ': 'fl', 'ﬀ': 'ff', 'ﬃ': 'ffi', 'ﬄ': 'ffl',
            ''': "'", ''': "'", '"': '"', '"': '"', '–': '-', '—': '-',
            '…': '...', '′': "'", '″': '"', '„': '"', '‟': '"', '−': '-',
            '·': '.', '•': '-', '´': "'", '`': "'", '′': "'", '″': '"',
        }
        for char, replacement in special_chars.items():
            text = text.replace(char, replacement)
        
        # 10. 문단 경계 복원 (빈 줄로 구분)
        text = re.sub(r'([.!?])\s+([A-Z])', r'\1\n\n\2', text)
        
        # 11. 참고문헌 섹션 제거
        references_patterns = [
            r'References\s*\n+.*$',
            r'Bibliography\s*\n+.*$',
            r'참고문헌\s*\n+.*$',
            r'REFERENCES\s*\n+.*$',
            r'Works Cited\s*\n+.*$',
        ]
        for pattern in references_patterns:
            if re.search(pattern, text, re.IGNORECASE | re.DOTALL):
                text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.DOTALL)
        
        # 12. 각주 및 미주 번호 정리
        text = re.sub(r'\[\d+\]|\(\d+\)', '', text)
        text = re.sub(r'\b\d+\s*\)', '', text)  # 숫자) 형태 제거
        text = re.sub(r'\b\d+\s*\.', '', text)  # 숫자. 형태 제거 (번호 목록)
        
        # 13. 인용 정보 정리 (핵심 인용은 유지, 부가 정보만 제거)
        # 페이지 번호, 출판사 정보 등 부가 정보는 제거하되 기본 저자-연도 인용은 유지
        text = re.sub(r'\(\s*([\w\s]+\s+\d{4})\s*,\s*\d+(?:\s*[-–]\s*\d+)?\s*\)', r'(\1)', text)  # (Author 2020, 10-15) -> (Author 2020)
        text = re.sub(r'\(\s*(?:cf|see|e\.g\.|i\.e\.|viz)\.\s+([\w\s]+\s+\d{4})\s*\)', r'(\1)', text)  # (cf. Smith 2020) -> (Smith 2020)
        
        # 인용 중복 정리 (같은 문장에 여러 개 인용이 있는 경우)
        text = re.sub(r'\(([\w\s]+\s+\d{4})\)\s*\(([\w\s]+\s+\d{4})\)', r'(\1, \2)', text)  # (Smith 2020)(Jones 2021) -> (Smith 2020, Jones 2021)
        
        # 14. 키워드 섹션에 대한 특별 처리 (Keywords를 별도 문단으로)
        text = re.sub(r'([.!?])\s+Keywords\b', r'\1\n\nKeywords', text, flags=re.IGNORECASE)
        
        # 15. 공백 라인 정리
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # 16. 의미없는 짧은 줄 제거
        lines = text.split('\n')
        meaningful_lines = []
        for line in lines:
            line = line.strip()
            if len(line) > 5 or (line and line[-1] in '.!?'):  # 의미있는 길이이거나 문장 끝인 경우
                meaningful_lines.append(line)
        
        # 17. 학술 용어 두문자어 정리 (예: i . e. -> i.e.)
        text = '\n'.join(meaningful_lines)
        text = re.sub(r'(\b[a-z])\s+\.\s+([a-z])\s+\.', r'\1.\2.', text)
        
        # 18. 키워드 섹션 제거
        text = re.sub(r'keywords\s*:.*?\n\n', '', text, flags=re.IGNORECASE | re.DOTALL)
        
        # 19. 한 번 더 연속된 공백 정리
        text = re.sub(r'\s{2,}', ' ', text)
        
        # 20. 최종 문장 정리 (줄바꿈이 포함된 문장을 일관되게 처리)
        sentences = []
        for paragraph in text.split('\n\n'):
            # 각 문단 내의 문장 결합
            clean_paragraph = re.sub(r'\n', ' ', paragraph)
            # 문단별로 구분하여 추가
            sentences.append(clean_paragraph)
        
        # 문단 구분은 빈 줄로 유지
        text = '\n\n'.join(sentences)
        
        return text.strip()
    
    def _insert_spaces(self, text: str) -> str:
        """
        긴 단어 문자열에 공백 삽입 시도
        
        Args:
            text: 공백 없는 긴 문자열
            
        Returns:
            공백이 삽입된 문자열
        """
        # 대문자로 시작하는 패턴 찾기
        result = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
        
        # 여전히 너무 긴 단어가 있다면 휴리스틱 적용
        words = result.split()
        final_result = []
        
        for word in words:
            if len(word) > 15:  # 여전히 긴 단어
                # 자주 사용되는 접두사 분리
                prefixes = ['trans', 'inter', 'intra', 'super', 'hyper', 'under', 'over', 'anti', 'auto', 'bio', 'geo', 'neo']
                for prefix in prefixes:
                    if word.startswith(prefix) and len(word) > len(prefix) + 3:
                        word = prefix + ' ' + word[len(prefix):]
                        break
                
                # 자주 사용되는 접미사 분리
                suffixes = ['tion', 'sion', 'ment', 'ness', 'ship', 'able', 'ible', 'ance', 'ence', 'ism', 'ist', 'ity', 'ing', 'ology']
                for suffix in suffixes:
                    if word.endswith(suffix) and len(word) > len(suffix) + 3:
                        word = word[:-len(suffix)] + ' ' + suffix
                        break
            
            final_result.append(word)
        
        return ' '.join(final_result)


def process_pdf(pdf_path: str, use_grobid: bool = False, grobid_url: str = "http://localhost:8070", extraction_method: str = "pymupdf") -> str:
    """
    PDF 처리 유틸리티 함수 (간편 사용)
    
    Args:
        pdf_path: PDF 파일 경로
        use_grobid: Grobid 사용 여부
        grobid_url: Grobid 서버 URL
        extraction_method: 텍스트 추출 방법 ('pymupdf', 'pdfplumber')
    
    Returns:
        처리된 텍스트
    """
    processor = PDFProcessor(use_grobid=use_grobid, grobid_url=grobid_url, extraction_method=extraction_method)
    return processor.process_pdf(pdf_path)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="PDF 텍스트 추출 및 전처리")
    parser.add_argument("pdf_path", help="PDF 파일 경로")
    parser.add_argument("--output", "-o", help="출력 파일 경로 (지정하지 않으면 표준 출력)")
    parser.add_argument("--grobid", "-g", action="store_true", help="Grobid 사용")
    parser.add_argument("--grobid-url", default="http://localhost:8070", help="Grobid 서버 URL")
    parser.add_argument("--method", "-m", choices=["pymupdf", "pdfplumber"], default="pymupdf", help="텍스트 추출 방법")
    
    args = parser.parse_args()
    
    # PDF 처리
    processed_text = process_pdf(
        args.pdf_path, 
        use_grobid=args.grobid, 
        grobid_url=args.grobid_url,
        extraction_method=args.method
    )
    
    # 결과 출력
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(processed_text)
        print(f"처리 결과가 {args.output}에 저장되었습니다.")
    else:
        print(processed_text) 
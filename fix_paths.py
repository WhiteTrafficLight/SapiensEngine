#!/usr/bin/env python3
"""
테스트 파일의 결과 저장 경로 및 임포트 경로 자동 수정 스크립트
"""

import os
import re
import glob

# 테스트 디렉토리 경로
TEST_DIRS = ['tests/web', 'tests/rag', 'tests/debate']

# 결과 저장 디렉토리 매핑
RESULT_DIR_MAPPING = {
    'web_search_results': '../../results/web',
    'enhanced_search_results': '../../results/enhancements',
    'query_enhancement_results': '../../results/enhancements',
    'combined_enhancement_results': '../../results/enhancements',
    'real_search_results': '../../results/search',
}

def fix_import_paths(file_path):
    """파일의 임포트 경로 수정"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # sapiens_engine 임포트 수정
    # 상대 경로 -> 절대 경로로 변경
    content = re.sub(
        r'from sapiens_engine\.',
        r'from sapiens_engine.',
        content
    )
    
    # 상대 경로 import 수정
    content = re.sub(
        r'import (.*?) from "(\.\./)+(.*?)"',
        r'import \1 from "../../\3"',
        content
    )
    
    # 테스트 파일 간 상대 참조 수정
    if 'web' in file_path:
        content = re.sub(
            r'from (enhanced_search|query_enhancer|real_query)',
            r'from ../rag/\1',
            content
        )
    
    # sys.path 모듈 경로 수정
    # 현재 디렉토리를 기준으로 상대 경로 조정
    content = re.sub(
        r'sys\.path\.append\(str\(.*?\)\)',
        r'sys.path.append(str(Path(__file__).parent.parent.parent.absolute()))',
        content
    )
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return True

def fix_output_paths(file_path):
    """결과 파일 저장 경로 수정"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # JSON 파일 결과 저장 경로 수정
    for result_prefix, result_dir in RESULT_DIR_MAPPING.items():
        # f"{result_prefix}_{timestamp}.json" 형태의 패턴 찾기
        pattern = rf'({result_prefix}_[^"\']*?\.json)'
        
        # 해당 패턴을 찾아서 경로 수정
        content = re.sub(
            pattern,
            rf'{result_dir}/\1',
            content
        )
    
    # output_file = output_file or "..." 패턴 수정
    for result_prefix, result_dir in RESULT_DIR_MAPPING.items():
        pattern = rf'output_file = output_file or [f]?"([^"]*{result_prefix}[^"]*)"'
        replacement = rf'output_file = output_file or f"{result_dir}/\1"'
        content = re.sub(pattern, replacement, content)
        
        # 작은따옴표 버전도 처리
        pattern = rf"output_file = output_file or [f]?'([^']*{result_prefix}[^']*)'"
        replacement = rf"output_file = output_file or f'{result_dir}/\1'"
        content = re.sub(pattern, replacement, content)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return True

def fix_dotenv_paths(file_path):
    """환경 변수 파일 로드 경로 수정"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # .env.local 파일 로드 코드 확인
    if 'load_dotenv' in content:
        # 경로 설정 코드 추가
        if 'project_root =' not in content:
            # 이미 current_dir 정의가 있는지 확인
            if 'current_dir =' not in content:
                # Path 임포트 확인
                if 'from pathlib import Path' not in content:
                    content = content.replace(
                        'import os', 
                        'import os\nfrom pathlib import Path'
                    )
                
                # 경로 설정 코드 추가
                dotenv_pattern = r'(from\s+dotenv\s+import\s+load_dotenv.*?\n)'
                dotenv_replacement = r'\1\n# 경로 설정\ncurrent_dir = Path(__file__).parent.absolute()\nproject_root = current_dir.parent.parent.absolute()\n'
                content = re.sub(dotenv_pattern, dotenv_replacement, content)
            else:
                # current_dir은 있지만 project_root가 없는 경우
                current_dir_pattern = r'(current_dir\s*=\s*Path.*?\n)'
                project_root_line = r'\1project_root = current_dir.parent.parent.absolute()\n'
                content = re.sub(current_dir_pattern, project_root_line, content)
        
        # .env.local 파일 로드 코드 수정
        content = re.sub(
            r"load_dotenv\(['\"]\.env\.local['\"]\)",
            r"load_dotenv(project_root / '.env.local')",
            content
        )
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return True

def main():
    """모든 테스트 파일 수정"""
    updated_files = 0
    
    for test_dir in TEST_DIRS:
        # 해당 디렉토리의 모든 Python 파일 찾기
        for file_path in glob.glob(f"{test_dir}/*.py"):
            print(f"처리 중: {file_path}")
            
            # 환경 변수 파일 로드 경로 수정
            dotenv_fixed = fix_dotenv_paths(file_path)
            
            # 임포트 경로 수정
            import_fixed = fix_import_paths(file_path)
            
            # 결과 저장 경로 수정
            output_fixed = fix_output_paths(file_path)
            
            if dotenv_fixed or import_fixed or output_fixed:
                updated_files += 1
    
    print(f"\n총 {updated_files}개 파일 업데이트 완료")

if __name__ == "__main__":
    main() 
"""
토론 기본 데이터 사전 생성 스크립트

debate_topics.json의 모든 주제에 대해 
콘텍스트 요약, 찬반 입장, 모더레이터 메시지를 사전 생성하여
JSON 파일로 저장합니다.

사용법:
    python pregenerate_base_data.py
    python pregenerate_base_data.py --category dilemma_challenge
    python pregenerate_base_data.py --output custom_output.json
"""

import asyncio
import json
import time
import logging
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import hashlib
import os
import sys

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from src.new.services.openai_service import OpenAIDebateService
from src.new.models.debate_models import FastDebateRequest, ModeratorStyle, ContextType

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DebateDataPregenrator:
    """토론 데이터 사전 생성기"""
    
    def __init__(self, output_file: str = "pregenerated_debates.json"):
        self.openai_service = OpenAIDebateService(use_fine_tuned=False)
        self.output_file = output_file
        self.debate_topics_file = project_root / "agoramind" / "data" / "debate_topics.json"
        
    def load_debate_topics(self) -> Dict[str, Any]:
        """debate_topics.json 파일 로드"""
        try:
            with open(self.debate_topics_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"Debate topics file not found: {self.debate_topics_file}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in debate topics file: {e}")
            raise
    
    def generate_topic_id(self, category: str, title: str) -> str:
        """주제 ID 생성 (해시 기반)"""
        content = f"{category}:{title}"
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    def detect_context_type(self, context: Dict[str, Any]) -> ContextType:
        """컨텍스트 타입 감지"""
        context_type = context.get("type", "").lower()
        content = context.get("content", "").strip()
        
        if context_type == "url" or content.startswith(('http://', 'https://')):
            return ContextType.URL
        elif context_type == "pdf" or content.lower().endswith('.pdf'):
            return ContextType.PDF
        elif content:
            return ContextType.TEXT
        else:
            return ContextType.EMPTY
    
    async def generate_single_topic(self, 
                                  category: str, 
                                  topic_data: Dict[str, Any]) -> Dict[str, Any]:
        """단일 주제에 대한 데이터 생성"""
        
        title = topic_data["title"]
        context = topic_data.get("context", {})
        pro_philosophers = topic_data.get("pro_philosophers", [])
        con_philosophers = topic_data.get("con_philosophers", [])
        moderator_style = str(topic_data.get("moderator_style", "0"))
        
        topic_id = self.generate_topic_id(category, title)
        
        logger.info(f"🔄 Generating data for: {title}")
        logger.info(f"   Category: {category}")
        logger.info(f"   Context: {context.get('type', 'none')} - {len(context.get('content', ''))}")
        logger.info(f"   PRO: {pro_philosophers}")
        logger.info(f"   CON: {con_philosophers}")
        
        try:
            # FastDebateRequest 생성
            request = FastDebateRequest(
                room_id=f"pregenerated_{topic_id}",
                title=title,
                context=context.get("content", ""),
                context_type=self.detect_context_type(context),
                pro_npcs=pro_philosophers,
                con_npcs=con_philosophers,
                user_ids=[],
                user_side="neutral",
                moderator_style=ModeratorStyle(moderator_style)
            )
            
            # 토론 패키지 생성
            start_time = time.time()
            debate_package = await self.openai_service.generate_complete_debate_package(request)
            generation_time = time.time() - start_time
            
            # 결과 구성
            result = {
                "topic_id": topic_id,
                "category": category,
                "title": title,
                "original_data": {
                    "context": context,
                    "pro_philosophers": pro_philosophers,
                    "con_philosophers": con_philosophers,
                    "moderator_style": moderator_style
                },
                "generated_data": {
                    "stance_statements": {
                        "pro": debate_package.stance_statements.pro,
                        "con": debate_package.stance_statements.con
                    },
                    "context_summary": debate_package.context_summary.model_dump() if debate_package.context_summary else None,
                    "opening_message": debate_package.opening_message,
                    "generation_time": generation_time,
                    "system_version": debate_package.system_version
                },
                "cache_key": f"topic:{title}:base",
                "generated_at": datetime.utcnow().isoformat()
            }
            
            logger.info(f"✅ Generated successfully in {generation_time:.2f}s")
            logger.info(f"   Stance PRO: {result['generated_data']['stance_statements']['pro'][:50]}...")
            logger.info(f"   Stance CON: {result['generated_data']['stance_statements']['con'][:50]}...")
            logger.info(f"   Opening: {result['generated_data']['opening_message'][:50]}...")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to generate data for '{title}': {str(e)}")
            return {
                "topic_id": topic_id,
                "category": category,
                "title": title,
                "error": str(e),
                "generated_at": datetime.utcnow().isoformat()
            }
    
    async def generate_all_topics(self, 
                                target_category: Optional[str] = None) -> Dict[str, Any]:
        """모든 주제 또는 특정 카테고리 주제들 생성"""
        
        # 토론 주제 로드
        topics_data = self.load_debate_topics()
        categories = topics_data.get("categories", {})
        
        if target_category and target_category not in categories:
            raise ValueError(f"Category '{target_category}' not found. Available: {list(categories.keys())}")
        
        # 생성할 주제들 수집
        topics_to_generate = []
        
        if target_category:
            # 특정 카테고리만
            category_data = categories[target_category]
            for topic in category_data.get("topics", []):
                topics_to_generate.append((target_category, topic))
        else:
            # 모든 카테고리
            for category_name, category_data in categories.items():
                for topic in category_data.get("topics", []):
                    topics_to_generate.append((category_name, topic))
        
        logger.info(f"🚀 Starting pregeneration for {len(topics_to_generate)} topics")
        if target_category:
            logger.info(f"   Target category: {target_category}")
        else:
            logger.info(f"   Categories: {list(categories.keys())}")
        
        # 병렬 생성 (제한된 동시 실행)
        semaphore = asyncio.Semaphore(3)  # 최대 3개 동시 실행
        
        async def generate_with_semaphore(category: str, topic_data: Dict[str, Any]):
            async with semaphore:
                return await self.generate_single_topic(category, topic_data)
        
        # 모든 작업 실행
        start_time = time.time()
        results = await asyncio.gather(*[
            generate_with_semaphore(category, topic_data)
            for category, topic_data in topics_to_generate
        ], return_exceptions=True)
        
        total_time = time.time() - start_time
        
        # 결과 정리
        successful_results = []
        failed_results = []
        
        for result in results:
            if isinstance(result, Exception):
                failed_results.append({"error": str(result)})
            elif "error" in result:
                failed_results.append(result)
            else:
                successful_results.append(result)
        
        # 최종 데이터 구성
        output_data = {
            "metadata": {
                "generated_at": datetime.utcnow().isoformat(),
                "total_topics": len(topics_to_generate),
                "successful": len(successful_results),
                "failed": len(failed_results),
                "total_generation_time": total_time,
                "average_time_per_topic": total_time / len(topics_to_generate) if topics_to_generate else 0,
                "target_category": target_category,
                "system_version": "v2_fast_pregenerated"
            },
            "topics": {
                result["topic_id"]: result for result in successful_results
            },
            "failed_topics": failed_results
        }
        
        logger.info(f"🎯 Pregeneration completed!")
        logger.info(f"   Total time: {total_time:.2f}s")
        logger.info(f"   Average per topic: {total_time/len(topics_to_generate):.2f}s")
        logger.info(f"   Successful: {len(successful_results)}")
        logger.info(f"   Failed: {len(failed_results)}")
        
        return output_data
    
    def save_results(self, data: Dict[str, Any]) -> None:
        """결과를 JSON 파일로 저장"""
        output_path = Path(self.output_file)
        
        # 디렉토리 생성
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # JSON 저장
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"💾 Results saved to: {output_path.absolute()}")
        logger.info(f"   File size: {output_path.stat().st_size / 1024:.2f} KB")
    
    def load_existing_results(self) -> Optional[Dict[str, Any]]:
        """기존 결과 파일 로드 (있다면)"""
        output_path = Path(self.output_file)
        
        if output_path.exists():
            try:
                with open(output_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load existing results: {e}")
        
        return None
    
    async def run(self, category: Optional[str] = None, force: bool = False) -> None:
        """메인 실행 함수"""
        
        # 기존 결과 확인
        if not force:
            existing_results = self.load_existing_results()
            if existing_results:
                logger.info(f"📁 Found existing results file: {self.output_file}")
                logger.info(f"   Generated topics: {len(existing_results.get('topics', {}))}")
                logger.info(f"   Generated at: {existing_results.get('metadata', {}).get('generated_at', 'unknown')}")
                
                response = input("Do you want to overwrite? (y/N): ")
                if response.lower() != 'y':
                    logger.info("Pregeneration cancelled.")
                    return
        
        try:
            # 데이터 생성
            results = await self.generate_all_topics(category)
            
            # 결과 저장
            self.save_results(results)
            
            # 요약 출력
            print("\n" + "="*60)
            print("🎉 PREGENERATION SUMMARY")
            print("="*60)
            print(f"Total topics processed: {results['metadata']['total_topics']}")
            print(f"Successful generations: {results['metadata']['successful']}")
            print(f"Failed generations: {results['metadata']['failed']}")
            print(f"Total time: {results['metadata']['total_generation_time']:.2f}s")
            print(f"Average per topic: {results['metadata']['average_time_per_topic']:.2f}s")
            print(f"Output file: {Path(self.output_file).absolute()}")
            print("="*60)
            
        except KeyboardInterrupt:
            logger.info("Pregeneration interrupted by user")
        except Exception as e:
            logger.error(f"Pregeneration failed: {str(e)}")
            raise

def main():
    """CLI 메인 함수"""
    parser = argparse.ArgumentParser(description="Pregenerate debate base data")
    parser.add_argument(
        "--category", 
        type=str, 
        help="Target specific category (dilemma_challenge, self_and_philosophy, global_and_current_affairs, science_and_technology)"
    )
    parser.add_argument(
        "--output", 
        type=str, 
        default="data/pregenerated_debates.json",
        help="Output file path (default: data/pregenerated_debates.json)"
    )
    parser.add_argument(
        "--force", 
        action="store_true",
        help="Force overwrite existing results"
    )
    
    args = parser.parse_args()
    
    # 사전 생성기 실행
    pregenrator = DebateDataPregenrator(output_file=args.output)
    
    # 비동기 실행
    asyncio.run(pregenrator.run(
        category=args.category,
        force=args.force
    ))

if __name__ == "__main__":
    main() 
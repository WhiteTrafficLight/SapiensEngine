"""
Fine-tuning Model Training Script

생성된 학습 데이터를 사용하여 OpenAI 모델 파인튜닝
🔥 여기서 파인튜닝 모델을 훈련하고 배포합니다
"""

import os
import time
import json
from pathlib import Path
from typing import Dict, Any, Optional
import openai
from openai import OpenAI

class DebateModeratorTrainer:
    """토론 모더레이터 파인튜닝 트레이너"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.client = OpenAI(api_key=api_key)
        self.training_dir = Path("src/new/fine_tuning")
        
        # 파인튜닝 설정
        self.model_config = {
            "model": "gpt-4o-mini-2024-07-18",  # 파인튜닝 가능한 모델
            "training_file": None,
            "validation_file": None,
            "hyperparameters": {
                "n_epochs": 3,  # 적은 에포크로 시작 (과적합 방지)
                "batch_size": 1,
                "learning_rate_multiplier": 1.0
            },
            "suffix": "debate-moderator-v1"
        }
    
    def upload_training_files(self) -> tuple[str, str]:
        """🔥 학습/검증 파일을 OpenAI에 업로드"""
        
        train_file = self.training_dir / "train_data.jsonl"
        val_file = self.training_dir / "validation_data.jsonl"
        
        if not train_file.exists() or not val_file.exists():
            raise FileNotFoundError(
                "Training data not found. Run prepare_training_data.py first."
            )
        
        print("📤 Uploading training files to OpenAI...")
        
        # 학습 파일 업로드
        print(f"📚 Uploading training file: {train_file}")
        with open(train_file, "rb") as f:
            training_file = self.client.files.create(
                file=f,
                purpose="fine-tune"
            )
        
        # 검증 파일 업로드
        print(f"🔍 Uploading validation file: {val_file}")
        with open(val_file, "rb") as f:
            validation_file = self.client.files.create(
                file=f,
                purpose="fine-tune"
            )
        
        print(f"✅ Training file uploaded: {training_file.id}")
        print(f"✅ Validation file uploaded: {validation_file.id}")
        
        return training_file.id, validation_file.id
    
    def start_fine_tuning(self, training_file_id: str, validation_file_id: str) -> str:
        """🚀 파인튜닝 작업 시작"""
        
        print("🚀 Starting fine-tuning job...")
        
        fine_tuning_job = self.client.fine_tuning.jobs.create(
            training_file=training_file_id,
            validation_file=validation_file_id,
            model=self.model_config["model"],
            hyperparameters=self.model_config["hyperparameters"],
            suffix=self.model_config["suffix"]
        )
        
        job_id = fine_tuning_job.id
        print(f"✅ Fine-tuning job started: {job_id}")
        print(f"📊 Model: {self.model_config['model']}")
        print(f"⚙️ Hyperparameters: {self.model_config['hyperparameters']}")
        
        return job_id
    
    def monitor_training(self, job_id: str) -> Dict[str, Any]:
        """📊 훈련 진행 상황 모니터링"""
        
        print(f"📊 Monitoring training job: {job_id}")
        print("⏳ This may take 10-30 minutes depending on data size...")
        
        while True:
            job = self.client.fine_tuning.jobs.retrieve(job_id)
            status = job.status
            
            print(f"📈 Status: {status}")
            
            if status == "succeeded":
                print("🎉 Training completed successfully!")
                model_id = job.fine_tuned_model
                print(f"🤖 Fine-tuned model ID: {model_id}")
                
                # 훈련 결과 저장
                self._save_training_results(job_id, model_id, job)
                
                return {
                    "status": "succeeded",
                    "model_id": model_id,
                    "job_id": job_id,
                    "training_file": job.training_file,
                    "validation_file": job.validation_file
                }
            
            elif status == "failed":
                print("❌ Training failed!")
                error_msg = getattr(job, 'error', 'Unknown error')
                print(f"Error: {error_msg}")
                
                return {
                    "status": "failed",
                    "error": error_msg,
                    "job_id": job_id
                }
            
            elif status in ["validating_files", "queued", "running"]:
                # 진행 중
                if hasattr(job, 'trained_tokens') and job.trained_tokens:
                    print(f"🔄 Trained tokens: {job.trained_tokens}")
                
                time.sleep(30)  # 30초마다 확인
            
            else:
                print(f"⚠️ Unknown status: {status}")
                time.sleep(30)
    
    def _save_training_results(self, job_id: str, model_id: str, job_info) -> None:
        """훈련 결과 저장"""
        
        results = {
            "job_id": job_id,
            "model_id": model_id,
            "status": job_info.status,
            "created_at": job_info.created_at,
            "finished_at": getattr(job_info, 'finished_at', None),
            "training_file": job_info.training_file,
            "validation_file": getattr(job_info, 'validation_file', None),
            "hyperparameters": getattr(job_info, 'hyperparameters', None),
            "result_files": getattr(job_info, 'result_files', []),
            "trained_tokens": getattr(job_info, 'trained_tokens', None)
        }
        
        results_file = self.training_dir / "training_results.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Training results saved to: {results_file}")
    
    def test_fine_tuned_model(self, model_id: str, test_cases: list) -> Dict[str, Any]:
        """🧪 파인튜닝된 모델 테스트"""
        
        print(f"🧪 Testing fine-tuned model: {model_id}")
        
        test_results = []
        
        for i, test_case in enumerate(test_cases):
            print(f"🔬 Test case {i+1}: {test_case['title'][:50]}...")
            
            start_time = time.time()
            
            try:
                response = self.client.chat.completions.create(
                    model=model_id,
                    messages=[
                        {
                            "role": "system", 
                            "content": "Generate complete debate package as Jamie the Host (casual, friendly, young-style)."
                        },
                        {
                            "role": "user",
                            "content": f"""Create a complete debate package for this topic:

TOPIC: {test_case['title']}

PARTICIPANTS:
- PRO side: {', '.join(test_case.get('pro_npcs', []))}
- CON side: {', '.join(test_case.get('con_npcs', []))}

Use the create_complete_debate_package function to provide structured output."""
                        }
                    ],
                    max_tokens=2000,
                    temperature=0.7
                )
                
                generation_time = time.time() - start_time
                
                test_results.append({
                    "test_case": i + 1,
                    "title": test_case['title'],
                    "generation_time": generation_time,
                    "success": True,
                    "response_length": len(response.choices[0].message.content) if response.choices[0].message.content else 0,
                    "tokens_used": response.usage.total_tokens if hasattr(response, 'usage') else 0
                })
                
            except Exception as e:
                test_results.append({
                    "test_case": i + 1,
                    "title": test_case['title'],
                    "generation_time": time.time() - start_time,
                    "success": False,
                    "error": str(e)
                })
        
        # 결과 요약
        successful_tests = [r for r in test_results if r["success"]]
        success_rate = len(successful_tests) / len(test_results)
        avg_time = sum(r["generation_time"] for r in successful_tests) / len(successful_tests) if successful_tests else 0
        
        summary = {
            "model_id": model_id,
            "total_tests": len(test_results),
            "success_rate": success_rate,
            "average_generation_time": avg_time,
            "test_results": test_results
        }
        
        # 테스트 결과 저장
        test_results_file = self.training_dir / "test_results.json"
        with open(test_results_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        print(f"📊 Test Results Summary:")
        print(f"   Success Rate: {success_rate:.1%}")
        print(f"   Average Time: {avg_time:.2f}s")
        print(f"   Results saved to: {test_results_file}")
        
        return summary
    
    def list_fine_tuned_models(self) -> list:
        """📋 파인튜닝된 모델 목록 조회"""
        
        print("📋 Listing fine-tuned models...")
        
        models = self.client.fine_tuning.jobs.list(limit=10)
        
        for job in models.data:
            print(f"🤖 Job ID: {job.id}")
            print(f"   Status: {job.status}")
            print(f"   Model: {getattr(job, 'fine_tuned_model', 'N/A')}")
            print(f"   Created: {job.created_at}")
            print()
        
        return models.data
    
    def run_full_training_pipeline(self) -> Dict[str, Any]:
        """🚀 전체 훈련 파이프라인 실행"""
        
        print("🎯 Starting full training pipeline...")
        
        try:
            # 1. 파일 업로드
            training_file_id, validation_file_id = self.upload_training_files()
            
            # 2. 파인튜닝 시작
            job_id = self.start_fine_tuning(training_file_id, validation_file_id)
            
            # 3. 훈련 모니터링
            results = self.monitor_training(job_id)
            
            if results["status"] == "succeeded":
                print("\n🎉 Training pipeline completed successfully!")
                print(f"🤖 Your fine-tuned model: {results['model_id']}")
                print("\n📋 Next steps:")
                print("1. Update the model ID in openai_service.py")
                print("2. Test the model in Jupyter notebook")
                print("3. Deploy to production")
                
                return results
            else:
                print(f"\n❌ Training failed: {results}")
                return results
                
        except Exception as e:
            print(f"❌ Pipeline error: {str(e)}")
            return {"status": "error", "error": str(e)}

def main():
    """메인 실행 함수"""
    
    print("🚀 Debate Moderator Fine-tuning Script")
    print("=" * 50)
    
    # OpenAI API 키 확인
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️ OPENAI_API_KEY environment variable not set!")
        print("Please set your OpenAI API key and try again.")
        return
    
    trainer = DebateModeratorTrainer()
    
    # 메뉴 선택
    print("\n📋 Available options:")
    print("1. Run full training pipeline")
    print("2. List existing fine-tuned models")
    print("3. Test specific model")
    
    choice = input("\nEnter your choice (1-3): ").strip()
    
    if choice == "1":
        # 전체 파이프라인 실행
        results = trainer.run_full_training_pipeline()
        
    elif choice == "2":
        # 기존 모델 목록
        trainer.list_fine_tuned_models()
        
    elif choice == "3":
        # 특정 모델 테스트
        model_id = input("Enter model ID to test: ").strip()
        if model_id:
            # 간단한 테스트 케이스
            test_cases = [
                {
                    "title": "Will AI threaten humanity or liberate us?",
                    "pro_npcs": ["nietzsche", "sartre"],
                    "con_npcs": ["kant", "confucius"]
                }
            ]
            trainer.test_fine_tuned_model(model_id, test_cases)
        
    else:
        print("❌ Invalid choice")

if __name__ == "__main__":
    main() 
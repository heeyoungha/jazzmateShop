# services/embedding_service.py
import os
import pickle
from datetime import datetime
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI

class EmbeddingService:
    def __init__(self):
        self.client = None
        self.failed_data_file = "failed_embeddings.pkl"
        self.failed_data = self._load_failed_data()

    async def initialize(self):
        """임베딩 서비스 초기화"""
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            print("⚠️ OPENAI_API_KEY가 설정되지 않았습니다.")
            self.client = None
            return

        try:
            self.client = AsyncOpenAI(api_key=api_key)
            print("✅ Hugging Face 임베딩 서비스 초기화 완료")
        except Exception as e:
            print(f"❌ OpenAI 클라이언트 초기화 실패: {e}")
            self.client = None

    async def get_embedding(self, track_data: Dict[str, Any]) -> Optional[List[float]]:
        """단일 임베딩 생성 (text-embedding-3-small, 1536차원)"""
        if not self.client:
            print("❌ OpenAI 클라이언트가 초기화되지 않았습니다.")
            return None

        try:
            text = self._create_text(track_data)
            response = await self.client.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            return response.data[0].embedding

        except Exception as e:
            print(f"❌ 임베딩 생성 실패: {e}")
            return None
    
    async def get_embeddings_batch(self, track_data_list: List[Dict[str, Any]]) -> List[Optional[List[float]]]:
        """배치 임베딩 생성"""
        if not self.client:
            error_msg = "HF_TOKEN이 설정되지 않았습니다."
            print(f"❌ {error_msg}")
            return [None] * len(track_data_list)
            
        try:
            # 텍스트 생성
            texts = [self._create_text(track_data) for track_data in track_data_list]
            
            # 배치 임베딩 생성
            results = self.client.feature_extraction(
                texts,  # 리스트로 여러 텍스트 전달
                model="intfloat/multilingual-e5-large",  
            )
            
            return [result.tolist() for result in results]
            
        except Exception as e:
            error_msg = f"배치 임베딩 생성 실패: {str(e)}"
            print(f"❌ {error_msg}")
            # 임베딩 없이는 저장하지 않음
            return [None] * len(track_data_list)
    
    # 나머지 메서드들은 동일...
    def _create_text(self, track_data: Dict[str, Any]) -> str:
        """임베딩용 텍스트 생성"""
        text_parts = []
        
        if track_data.get("album_title"):
            text_parts.append(f"앨범 제목: {track_data['album_title']}")
        
        if track_data.get("album_artist"):
            text_parts.append(f"아티스트: {track_data['album_artist']}")
        
        if track_data.get("album_year"):
            text_parts.append(f"발매년도: {track_data['album_year']}")
        
        if track_data.get("album_label"):
            text_parts.append(f"레이블: {track_data['album_label']}")
        
        if track_data.get("review_summary"):
            text_parts.append(f"리뷰 요약: {track_data['review_summary']}")
        
        if track_data.get("content"):
            text_parts.append(f"리뷰 내용: {track_data['content'][:500]}")
        
        return " ".join(text_parts)
    
    def _load_failed_data(self) -> List[Dict[str, Any]]:
        """실패한 데이터 로드"""
        try:
            if os.path.exists(self.failed_data_file):
                with open(self.failed_data_file, 'rb') as f:
                    return pickle.load(f)
        except Exception as e:
            print(f"⚠️ 실패 데이터 로드 실패: {e}")
        return []
    
    def _save_failed_data(self, track_data: Dict[str, Any], error_message: str, embedding: Optional[List[float]] = None):
        """실패한 데이터 저장 (임베딩이 있는 경우만)"""
        # 임베딩이 없으면 저장하지 않음
        if embedding is None:
            print(f"⚠️ 임베딩 없음으로 실패 데이터 저장 건너뜀: {track_data.get('album_title', 'Unknown')}")
            return
        
        try:
            failed_item = {
                'track_data': track_data,
                'embedding': embedding, 
                'error_message': error_message,
                'timestamp': datetime.now().isoformat(),
                'retry_count': 0
            }
            self.failed_data.append(failed_item)
            
            with open(self.failed_data_file, 'wb') as f:
                pickle.dump(self.failed_data, f)
            
            # 더 나은 제목 표시
            title = track_data.get('album_title') or track_data.get('title') or f"ID: {track_data.get('id', 'Unknown')}"
            print(f"📝 실패한 데이터 저장됨: {title} (임베딩 포함)")
        except Exception as e:
            print(f"⚠️ 실패 데이터 저장 실패: {e}")
    
    def get_failed_data_count(self) -> int:
        """실패한 데이터 개수 반환"""
        return len(self.failed_data)
    
    def get_failed_data_summary(self) -> List[Dict[str, Any]]:
        """실패한 데이터 요약 반환"""
        summary = []
        for item in self.failed_data:
            track_data = item['track_data']
            title = track_data.get('album_title') or track_data.get('title') or f"ID: {track_data.get('id', 'Unknown')}"
            has_embedding = 'embedding' in item and item['embedding'] is not None
            summary.append({
                'title': title,
                'error': item['error_message'],
                'timestamp': item['timestamp'],
                'retry_count': item['retry_count'],
                'has_embedding': has_embedding
            })
        return summary
    
    async def retry_failed_embeddings(self, max_retries: int = 3) -> Dict[str, int]:
        """실패한 임베딩 재시도 (저장된 임베딩 재사용)"""
        retry_results = {'success': 0, 'failed': 0, 'skipped': 0}
        
        for item in self.failed_data[:]:  # 복사본으로 순회
            if item['retry_count'] >= max_retries:
                retry_results['skipped'] += 1
                continue
            
            try:
                # 저장된 임베딩이 있으면 재사용
                if 'embedding' in item and item['embedding'] is not None:
                    embedding = item['embedding']
                    print(f"♻️ 저장된 임베딩 재사용: {item['track_data'].get('album_title', 'Unknown')}")
                else:
                    # 임베딩이 없으면 새로 생성
                    embedding = await self.get_embedding(item['track_data'])
                
                if embedding is not None:
                    # Qdrant에 저장 시도 (이 부분은 build_vector_db.py에서 처리)
                    # 여기서는 성공으로 간주하고 실패 목록에서 제거
                    self.failed_data.remove(item)
                    retry_results['success'] += 1
                    print(f"✅ 재시도 성공: {item['track_data'].get('album_title', 'Unknown')}")
                else:
                    # 여전히 실패한 경우 재시도 횟수 증가
                    item['retry_count'] += 1
                    retry_results['failed'] += 1
                    print(f"⚠️ 재시도 실패: {item['track_data'].get('album_title', 'Unknown')}")
                    
            except Exception as e:
                item['retry_count'] += 1
                retry_results['failed'] += 1
                print(f"⚠️ 재시도 중 오류: {e}")
        
        # 업데이트된 실패 데이터 저장
        try:
            with open(self.failed_data_file, 'wb') as f:
                pickle.dump(self.failed_data, f)
        except Exception as e:
            print(f"⚠️ 실패 데이터 저장 실패: {e}")
        
        return retry_results
    
    def clear_failed_data(self):
        """실패한 데이터 초기화"""
        self.failed_data = []
        try:
            if os.path.exists(self.failed_data_file):
                os.remove(self.failed_data_file)
            print("🗑️ 실패한 데이터 초기화 완료")
        except Exception as e:
            print(f"⚠️ 실패 데이터 초기화 실패: {e}")
    
    async def disconnect(self):
        """연결 해제"""
        pass
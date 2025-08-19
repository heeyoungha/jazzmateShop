import os
import asyncio
from supabase import create_client, Client
from typing import List, Dict, Any, Optional

class SupabaseService:
    def __init__(self):
        self.client: Optional[Client] = None
        self.url = os.getenv("SUPABASE_URL")
        self.key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        
    async def connect_with_service_role(self):
        """서비스 역할로 Supabase 연결"""
        if not self.url or not self.key:
            raise ValueError("SUPABASE_URL과 SUPABASE_SERVICE_ROLE_KEY 환경변수가 필요합니다")
        
        self.client = create_client(self.url, self.key)
        print("✅ Supabase 연결 완료")
    
    async def get_reviews_with_summary(self) -> List[Dict[str, Any]]:
        """review_summary가 있는 리뷰 데이터 조회"""
        if not self.client:
            raise RuntimeError("Supabase에 연결되지 않았습니다")
        
        try:
            response = self.client.table("critics_review").select("*").not_.is_("review_summary", "null").execute()
            return response.data
        except Exception as e:
            print(f"❌ 리뷰 데이터 조회 실패: {e}")
            return []
    
    async def get_albums_with_reviews(self) -> List[Dict[str, Any]]:
        """album과 critics_review를 효율적으로 조인하여 데이터 조회"""
        if not self.client:
            raise RuntimeError("Supabase에 연결되지 않았습니다")
        
        try:
            # 한 번의 쿼리로 조인하여 유효한 데이터만 조회
            response = self.client.table("album").select(
                "*, critics_review!inner(content, review_summary)"
            ).not_.is_("critics_review.content", "null").not_.is_("critics_review.review_summary", "null").execute()
            
            print(f"📊 조인된 유효한 앨범-리뷰 데이터: {len(response.data)}개")
            return response.data
            
        except Exception as e:
            print(f"❌ 데이터 조회 실패: {e}")
            return []
    
    async def check_track_exists(self, track_id: int) -> bool:
        """Track이 존재하는지 확인"""
        if not self.client:
            raise RuntimeError("Supabase에 연결되지 않았습니다")
        
        try:
            response = self.client.table("track").select("id").eq("id", track_id).execute()
            return len(response.data) > 0
        except Exception as e:
            print(f"❌ Track 존재 확인 실패: {e}")
            return False
    
    async def save_recommend_track(self, recommend_data: Dict[str, Any]) -> bool:
        """RecommendTrack 저장"""
        if not self.client:
            raise RuntimeError("Supabase에 연결되지 않았습니다")
        
        try:
            response = self.client.table("recommend_track").insert(recommend_data).execute()
            return len(response.data) > 0
        except Exception as e:
            print(f"❌ RecommendTrack 저장 실패: {e}")
            return False
    
    async def disconnect(self):
        """연결 해제"""
        self.client = None
# process_critics_reviews_streaming.py
import os
import json
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

# backend 폴더의 .env 파일 로드
backend_path = Path(__file__).parent.parent
env_path = backend_path / ".env"
load_dotenv(env_path)

class AlbumDataProcessor:
    def __init__(self):
        self.supabase = None
        
    async def connect(self):
        """Supabase 연결"""
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        
        if not url or not key:
            raise ValueError("SUPABASE_URL과 SUPABASE_SERVICE_ROLE_KEY 환경변수가 필요합니다")
        
        self.supabase = create_client(url, key)
        print("✅ Supabase 연결 완료")
    
    def parse_title_for_artist(self, title: str) -> str:
        """title에서 artist 추출 (: 구분자)"""
        if not title:
            return ""
        
        # : 구분자로 분리하여 앞부분 추출
        parts = title.split(":")
        return parts[0].strip() if parts else ""
    
    def parse_album_info(self, album_info: str) -> dict:
        """album_info에서 title, year, label 추출"""
        result = {
            "title": "",
            "year": None,
            "label": ""
        }
        
        if not album_info:
            return result
        
        try:
            # JSON 형태로 파싱 시도
            if album_info.startswith("{") and album_info.endswith("}"):
                info_data = json.loads(album_info)
                result["title"] = info_data.get("title", "")
                result["year"] = info_data.get("year")
                result["label"] = info_data.get("label", "")
            else:
                # 텍스트 형태인 경우 파싱
                lines = album_info.split("\n")
                for line in lines:
                    line = line.strip()
                    if "title" in line.lower():
                        result["title"] = line.split(":", 1)[1].strip() if ":" in line else ""
                    elif "year" in line.lower():
                        year_str = line.split(":", 1)[1].strip() if ":" in line else ""
                        try:
                            result["year"] = int(year_str) if year_str.isdigit() else None
                        except:
                            result["year"] = None
                    elif "label" in line.lower():
                        result["label"] = line.split(":", 1)[1].strip() if ":" in line else ""
        except Exception as e:
            print(f"⚠️ album_info 파싱 실패: {e}")
        
        return result
    
    def parse_track_listing(self, track_listing: str) -> dict:
        """track_listing을 JSON으로 변환"""
        if not track_listing:
            return {}
        
        try:
            # ; 구분자로 분리
            tracks = [track.strip() for track in track_listing.split(";") if track.strip()]
            
            # 인덱스를 키로 하는 JSON 생성
            result = {}
            for i, track in enumerate(tracks, 1):
                result[str(i)] = track
            
            return result
        except Exception as e:
            print(f"⚠️ track_listing 파싱 실패: {e}")
            return {}
    
    async def process_critics_reviews_streaming(self):
        """스트리밍 처리 (500개씩) - 실제 데이터 수 기반"""
        try:
            # 스트리밍 설정
            data_size = 500  # 한 번에 처리할 데이터 수
            start_index = 0
            processed_count = 0
            
            # 실제 데이터 수 조회
            print("📊 전체 데이터 수 조회 중...")
            count_response = self.supabase.table("critics_review").select("id", count="exact").execute()
            total_count = count_response.count
            total_datas = (total_count + data_size - 1) // data_size  # 올림 계산
            
            print(f"📊 전체 데이터: {total_count}개")
            print(f"📊 총 예상 배치: {total_datas}개 ({data_size}개씩)")
            
            while True:
                try:
                    # 데이터 조회
                    print(f"📖 데이터 조회 중: {start_index + 1}-{start_index + data_size}")
                    response = self.supabase.table("critics_review").select("*").range(start_index, start_index + data_size - 1).execute()
                    reviews = response.data
                    
                    if not reviews:
                        print("✅ 모든 데이터 처리 완료")
                        break
                    
                    print(f"📊 처리 중: {start_index + 1}-{start_index + len(reviews)} / {total_count}")
                    
                    # 배치 처리
                    album_records = []
                    for review in reviews:
                        try:
                            # 데이터 가공
                            album_artist = self.parse_title_for_artist(review.get("title", ""))
                            album_info = self.parse_album_info(review.get("album_info", ""))
                            track_listing = self.parse_track_listing(review.get("track_listing", ""))
                            
                            album_record = {
                                "album_artist": album_artist,
                                "album_title": album_info["title"],
                                "album_year": album_info["year"],
                                "album_label": album_info["label"],
                                "track_listing": track_listing,
                                "critics_review_id": review.get("id")
                            }
                            
                            album_records.append(album_record)
                            
                        except Exception as e:
                            print(f"⚠️ 리뷰 {review.get('id', 'unknown')} 처리 실패: {e}")
                            continue
                    
                    # 배치 삽입
                    if album_records:
                        try:
                            self.supabase.table("album").insert(album_records).execute()
                            processed_count += len(album_records)
                            print(f"✅ 데이터 처리 완료: {processed_count}/{total_count} ({processed_count/total_count*100:.1f}%)")
                        except Exception as e:
                            print(f"❌ 데이터 삽입 실패: {e}")
                            # 실패해도 다음 데이터 계속 처리
                            continue
                    
                    start_index += data_size
                    
                    # 메모리 정리
                    del reviews
                    del album_records
                    
                except Exception as e:
                    print(f"❌ 데이터 처리 실패: {e}")
                    start_index += data_size  # 실패한 데이터는 건너뛰고 계속
                    continue
            
            print(f"✅ Album 테이블 처리 완료: {processed_count}개 레코드")
            return True
            
        except Exception as e:
            print(f"❌ 데이터 처리 실패: {e}")
            return False
    
    async def run(self):
        """전체 프로세스 실행"""
        try:
            # 1. 연결
            await self.connect()
            
            # 2. 데이터 처리
            await self.process_critics_reviews_streaming()
            
        except Exception as e:
            print(f"❌ 실행 실패: {e}")

async def main():
    processor = AlbumDataProcessor()
    await processor.run()

if __name__ == "__main__":
    asyncio.run(main())
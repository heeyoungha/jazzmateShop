#!/usr/bin/env python3
"""
Supabase 데이터를 벡터 DB로 변환하는 스크립트
"""

import os
import sys
import argparse
import asyncio
import json
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv

from services.supabase_service import SupabaseService
from services.qdrant_service import QdrantService
from services.embedding_service import EmbeddingService

# backend 폴더의 .env 파일 로드
env_path = "/Users/heeha/Desktop/coding/JazzmateShop/backend/.env"
print(f"Loading .env from: {env_path}")
load_dotenv(env_path)

class VectorDBBuilder:
    def __init__(self, batch_size: int = 20):
        self.supabase = SupabaseService()
        self.qdrant = QdrantService()
        self.embedding = EmbeddingService()
        self.batch_size = batch_size
    
    def is_valid_json_data(self, album: Dict[str, Any]) -> bool:
        """앨범 데이터가 유효한 JSON 양식인지 검증"""
        try:
            # track_listing이 JSON 형태인지 확인
            track_listing = album.get("track_listing")
            if track_listing:
                if isinstance(track_listing, str):
                    json.loads(track_listing)
                elif not isinstance(track_listing, dict):
                    return False
            
            # critics_review 데이터 확인
            critics_review = album.get("critics_review", {})
            content = critics_review.get("content", "")
            review_summary = critics_review.get("review_summary", "")
            
            # content와 review_summary가 비어있지 않은지 확인
            if not content or not review_summary:
                return False
            
            # content와 review_summary가 유효한 텍스트인지 확인
            if not isinstance(content, str) or not isinstance(review_summary, str):
                return False
            
            return True
            
        except (json.JSONDecodeError, TypeError, ValueError):
            return False
    
    async def build_vector_db(self, limit: int = None):
        """벡터 DB 구축"""
        print("🎵 JazzMate 벡터 DB 구축 시작")
        print("=" * 50)
        
        try:
            # 1. 서비스 연결
            await self.supabase.connect_with_service_role()
            await self.qdrant.initialize()
            await self.embedding.initialize()
            
            # 2. 이미 업로드된 ID 목록 조회
            print("🔍 이미 업로드된 데이터 확인 중...")
            existing_ids = await self.qdrant.get_existing_ids()
            print(f"📊 이미 업로드된 데이터: {len(existing_ids)}개")
            
            # 3. Supabase에서 앨범-리뷰 조인 데이터 조회
            print("📖 앨범-리뷰 조인 데이터 조회 중...")
            all_albums = await self.supabase.get_albums_with_reviews()
            
            if not all_albums:
                print("❌ 앨범 데이터가 없습니다")
                return False
            
            # 4. 유효한 JSON 데이터와 아직 업로드되지 않은 앨범만 필터링
            valid_albums = []
            invalid_albums = []
            
            for album in all_albums:
                if self.is_valid_json_data(album):
                    valid_albums.append(album)
                else:
                    invalid_albums.append(album)
            
            # 기존에 업로드한 앨범은 제외하고 새로 업로드할 앨범만 필터링
            new_albums = [album for album in valid_albums 
                                if str(album.get("id")) not in existing_ids]
            
            print(f"📊 전체 앨범: {len(all_albums)}개")
            print(f"📊 유효한 JSON 데이터: {len(valid_albums)}개")
            print(f"📊 새로 업로드할 앨범: {len(new_albums)}개")
            print(f"📊 이미 업로드된 앨범: {len(valid_albums) - len(new_albums)}개")
            print(f"📊 필터링된 앨범: {len(all_albums) - len(valid_albums)}개")
            
            if not new_albums:
                print("✅ 모든 데이터가 이미 업로드되었습니다!")
                return True
            
            if limit:
                new_albums = new_albums[:limit]
                print(f"📊 제한된 새 데이터: {len(new_albums)}개 앨범")
            
            # 5. 벡터 DB 구축 (동적 배치 처리)
            print(f"🔄 벡터 DB 구축 중... (배치 크기: {self.batch_size})")
            success_count = 0
            error_count = 0

            for i in range(0, len(new_albums), self.batch_size):
                try:
                    batch_albums = new_albums[i:i+self.batch_size]
                    
                    # 배치 데이터 준비
                    batch_track_data = []
                    for album in batch_albums:
                        critics_review = album.get("critics_review", {})
                        track_data = {
                            "id": album.get("id"),
                            "album_artist": album.get("album_artist", ""),
                            "album_title": album.get("album_title", ""),
                            "album_year": album.get("album_year"),
                            "album_label": album.get("album_label", ""),
                            "track_listing": album.get("track_listing", {}),
                            "critics_review_id": album.get("critics_review_id"),
                            "content": critics_review.get("content", ""),
                            "review_summary": critics_review.get("review_summary", "")
                        }
                        batch_track_data.append(track_data)
                    
                    # 배치 임베딩 생성
                    embeddings = await self.embedding.get_embeddings_batch(batch_track_data)
                    
                    # 성공한 임베딩들을 Qdrant에 저장
                    for j, (track_data, embedding) in enumerate(zip(batch_track_data, embeddings)):
                        if embedding is not None:
                            try:
                                await self.qdrant.add_track(track_data, embedding)
                                success_count += 1
                            except ConnectionError as e:
                                # 네트워크 오류 - 재시도 가능 (임베딩 포함)
                                error_msg = f"네트워크 오류: {str(e)}"
                                self.embedding._save_failed_data(track_data, error_msg, embedding)
                                error_count += 1
                            except ValueError as e:
                                # 데이터 형식 오류 - 수정 필요 (임베딩 포함)
                                error_msg = f"데이터 형식 오류: {str(e)}"
                                self.embedding._save_failed_data(track_data, error_msg, embedding)
                                error_count += 1
                            except Exception as e:
                                # 기타 오류 (임베딩 포함)
                                error_msg = f"Qdrant 저장 실패: {str(e)}"
                                self.embedding._save_failed_data(track_data, error_msg, embedding)
                                error_count += 1
                        else:
                            error_count += 1
                            print(f"⚠️ 임베딩 생성 실패로 건너뜀: {track_data.get('id', 'unknown')}")
                    
                    # 진행률 출력
                    processed = min(i + self.batch_size, len(new_albums))
                    print(f"📊 진행률: {processed}/{len(new_albums)} ({processed/len(new_albums)*100:.1f}%)")
                    
                except Exception as e:
                    error_count += len(batch_albums)
                    print(f"⚠️ 배치 처리 실패: {e}")
                    continue
            
            # 6. 결과 출력
            print("\n✅ 벡터 DB 구축 완료!")
            print(f"📊 새로 추가된 데이터: {success_count}개")
            print(f"❌ 실패: {error_count}개")
            print(f"📈 성공률: {success_count/(success_count+error_count)*100:.1f}%")
            
            # 실패한 데이터 정보 출력
            failed_count = self.embedding.get_failed_data_count()
            if failed_count > 0:
                print(f"📝 실패한 데이터: {failed_count}개 (재처리 가능)")
                print("💡 재처리하려면: python build_vector_db.py --retry-failed")
            
            return True
            
        except Exception as e:
            print(f"❌ 벡터 DB 구축 실패: {e}")
            return False
    
    async def retry_failed_embeddings(self, max_retries: int = 3) -> bool:
        """실패한 임베딩 재처리"""
        try:
            print("🔄 실패한 임베딩 재처리 시작...")
            
            # 실패한 데이터 개수 확인
            failed_count = self.embedding.get_failed_data_count()
            if failed_count == 0:
                print("✅ 재처리할 실패한 데이터가 없습니다.")
                return True
            
            print(f"📝 재처리 대상: {failed_count}개")
            
            # 재시도 실행 (저장된 임베딩 재사용)
            retry_results = {'success': 0, 'failed': 0, 'skipped': 0}
            success_count = 0
            
            for item in self.embedding.failed_data[:]:
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
                        embedding = await self.embedding.get_embedding(item['track_data'])
                    
                    if embedding is not None:
                        # Qdrant에 저장 시도
                        await self.qdrant.add_track(item['track_data'], embedding)
                        self.embedding.failed_data.remove(item)
                        retry_results['success'] += 1
                        success_count += 1
                        print(f"✅ 재시도 성공: {item['track_data'].get('album_title', 'Unknown')}")
                    else:
                        item['retry_count'] += 1
                        retry_results['failed'] += 1
                        print(f"⚠️ 재시도 실패: {item['track_data'].get('album_title', 'Unknown')}")
                        
                except Exception as e:
                    item['retry_count'] += 1
                    retry_results['failed'] += 1
                    print(f"⚠️ 재시도 중 오류: {e}")
            
            # 업데이트된 실패 데이터 저장
            try:
                with open(self.embedding.failed_data_file, 'wb') as f:
                    import pickle
                    pickle.dump(self.embedding.failed_data, f)
            except Exception as e:
                print(f"⚠️ 실패 데이터 저장 실패: {e}")
            
            # 결과 출력
            print("\n✅ 재처리 완료!")
            print(f"📊 성공: {retry_results['success']}개")
            print(f"❌ 실패: {retry_results['failed']}개")
            print(f"⏭️ 건너뜀: {retry_results['skipped']}개")
            print(f"💾 Qdrant 저장: {success_count}개")
            
            return True
            
        except Exception as e:
            print(f"❌ 재처리 실패: {e}")
            return False
    
    async def show_failed_data_summary(self):
        """실패한 데이터 요약 출력"""
        try:
            failed_count = self.embedding.get_failed_data_count()
            if failed_count == 0:
                print("✅ 실패한 데이터가 없습니다.")
                return
            
            print(f"\n📝 실패한 데이터 요약 ({failed_count}개):")
            print("-" * 80)
            
            summary = self.embedding.get_failed_data_summary()
            for i, item in enumerate(summary[:10], 1):  # 최대 10개만 표시
                embedding_status = "♻️" if item['has_embedding'] else "❌"
                print(f"{i:2d}. {item['title'][:40]:<40} | {embedding_status} | {item['error'][:20]:<20} | 재시도: {item['retry_count']}")
            
            if len(summary) > 10:
                print(f"... 외 {len(summary) - 10}개 더")
            
            # 임베딩 포함 통계
            with_embedding = sum(1 for item in summary if item['has_embedding'])
            without_embedding = len(summary) - with_embedding
            print(f"\n📊 임베딩 상태: ♻️ {with_embedding}개 (재사용 가능) | ❌ {without_embedding}개 (재생성 필요)")
            
            print("-" * 80)
            
        except Exception as e:
            print(f"❌ 요약 출력 실패: {e}")
        
        finally:
            # 연결 해제
            try:
                await self.supabase.disconnect()
                await self.qdrant.disconnect()
                await self.embedding.disconnect()
            except:
                pass

def main():
    parser = argparse.ArgumentParser(description="Supabase 데이터를 벡터 DB로 변환")
    parser.add_argument("--limit", type=int, help="처리할 리뷰 수 제한 (테스트용)")
    parser.add_argument("--status", action="store_true", help="벡터 DB 상태 확인")
    parser.add_argument("--clear", action="store_true", help="벡터 DB 초기화")
    parser.add_argument("--retry-failed", action="store_true", help="실패한 임베딩 재처리")
    parser.add_argument("--show-failed", action="store_true", help="실패한 데이터 요약 출력")
    parser.add_argument("--clear-failed", action="store_true", help="실패한 데이터 초기화")
    parser.add_argument("--max-retries", type=int, default=3, help="최대 재시도 횟수 (기본값: 3)")
    parser.add_argument("--batch-size", type=int, default=20, help="배치 처리 크기")  # 새로 추가
    
    args = parser.parse_args()
    
    builder = VectorDBBuilder(batch_size=args.batch_size)
    
    if args.status:
        # 상태 확인
        async def check_status():
            try:
                await builder.qdrant.initialize()
                health = await builder.qdrant.health_check()
                print(f"📊 컬렉션 상태: {health}")
                return health['status'] == 'healthy'
            except Exception as e:
                print(f"❌ 상태 확인 실패: {e}")
                return False
        
        success = asyncio.run(check_status())
        sys.exit(0 if success else 1)
    
    elif args.retry_failed:
        # 실패한 임베딩 재처리
        async def retry_failed():
            try:
                await builder.qdrant.initialize()
                await builder.embedding.initialize()
                return await builder.retry_failed_embeddings(args.max_retries)
            except Exception as e:
                print(f"❌ 재처리 실패: {e}")
                return False
        
        success = asyncio.run(retry_failed())
        sys.exit(0 if success else 1)
    
    elif args.show_failed:
        # 실패한 데이터 요약 출력
        async def show_failed():
            try:
                await builder.embedding.initialize()
                await builder.show_failed_data_summary()
                return True
            except Exception as e:
                print(f"❌ 요약 출력 실패: {e}")
                return False
        
        success = asyncio.run(show_failed())
        sys.exit(0 if success else 1)
    
    elif args.clear_failed:
        # 실패한 데이터 초기화
        async def clear_failed():
            try:
                await builder.embedding.initialize()
                builder.embedding.clear_failed_data()
                return True
            except Exception as e:
                print(f"❌ 초기화 실패: {e}")
                return False
        
        success = asyncio.run(clear_failed())
        sys.exit(0 if success else 1)
    
    else:
        # 벡터 DB 구축
        success = asyncio.run(builder.build_vector_db(args.limit))
        sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()





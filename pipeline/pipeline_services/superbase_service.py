import os
import logging
from supabase import create_client, Client
from typing import List, Dict, Any, Optional, Set
from datetime import datetime
from pipeline_services.exceptions import DatabaseError

logger = logging.getLogger(__name__)

class SuperbaseService:

    def get_pending_batch_for_retry(self) -> Optional[Dict[str, Any]]:
            """재시도할 미완료 배치 찾기"""

            try:
                # 1) 가장 오래된 미완료 batch_id 조회 (batch_num 오름차순)
                batch_resp = self.client.table('crawl_jobs')\
                    .select('batch_id, pipeline_batches(batch_num)')\
                    .in_('status', ['pending', 'failed'])\
                    .lt('attempt_count', 3)\
                    .order('pipeline_batches(batch_num)', desc=False)\
                    .limit(1)\
                    .execute()
                
                if not batch_resp.data:
                    return None

                row = batch_resp.data[0]
                batch_num = (row.get('pipeline_batches') or {}).get('batch_num', 0)

                # 2) 조회된 레코드가 있으면, allthatjazz_raw테이블에서 한번더 필터링
                jobs_resp = self.client.table('crawl_jobs')\
                    .select('id, allthatjazz_raw(id)')\
                    .eq('batch_id', row['batch_id'])\
                    .in_('status', ['pending', 'failed'])\
                    .lt('attempt_count', 3)\
                    .execute()
                if not jobs_resp.data:
                    return None

                job_ids = [
                    j['id'] for j in jobs_resp.data
                    if not j.get('allthatjazz_raw') or not j['allthatjazz_raw'].get('id')
                ]
                if not job_ids:
                    return None

                return {
                    'batch_id': row['batch_id'],
                    'batch_num': batch_num,
                    'pending_count': len(job_ids),
                    'job_ids': job_ids,
                }
            except Exception as e:
                logger.error(f"get_pending_batch_for_retry 실패: {e}", exc_info=True)
                raise DatabaseError("미완료 batch 조회 실패") from e
    

    def __init__(self):
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

        if not url or not key:
            raise ValueError("SUPABASE_URL과 SUPABASE_SERVICE_ROLE_KEY 환경변수가 필요합니다")
        
        self.client = create_client(url, key)

    def generate_batch_num(self, airflow_dag_run_id: str) -> Dict[str, Any]:
        #TODO: 동시에 같은 airflow_dag_run_id로 호출되면 여전히 충돌 가능
        
        if not airflow_dag_run_id:
            raise ValueError("airflow_dag_run_id is required")
        
        try:
            # 1. 먼저 기존 batch 확인
            existing = self.client.table('pipeline_batches')\
                .select('id, batch_num')\
                .eq('airflow_dag_run_id', airflow_dag_run_id)\
                .execute()

            if existing.data:
                batch = existing.data[0]
                logger.info(f"♻️ Pipeline batch already exists: batch_num={batch['batch_num']}")
                return {'batch_num': batch['batch_num'], 'batch_id': batch['id']}
            # 2. 없으면 새로 생성
            response = self.client.table('pipeline_batches')\
                .insert({'airflow_dag_run_id': airflow_dag_run_id})\
                .execute()

            if not response.data:
                raise RuntimeError("pipeline_batches insert가 데이터를 반환하지 않았습니다")

            batch = response.data[0]
            logger.info(f"✅ Pipeline batch created: batch_num={batch['batch_num']}")
            return {'batch_num': batch['batch_num'], 'batch_id': batch['id']}

        except Exception as e:
            logger.error(f"❌ Pipeline batch 생성 실패: {e}")
            raise
            

    def get_successful_crawl_target_urls(self, urls: List[str], batch_size: int = 200) -> Set[str]:

        if not urls:
            return set()
        if not self.client:
            raise DatabaseError("Supabase client가 초기화되지 않았습니다")
        if batch_size <= 0:
            raise ValueError("batch_size must be greater than 0")
                
        existing: Set[str] = set()
        for i in range(0, len(urls), batch_size):
            chunk = urls[i : i + batch_size]
            try:
                resp = self.client.table('crawl_targets')\
                    .select('url')\
                    .in_('url', chunk)\
                    .eq('has_successful_crawl', True)\
                    .execute()
                
                if resp.data:
                    existing.update(r['url'] for r in resp.data)

            except Exception as e:
                logger.error(f"crawl_targets 기존 URL 조회 실패: {e}", exc_info=True)
                raise DatabaseError("crawl_targets 기존 URL 조회 실패") from e
        return existing
    
    def register_crawl_jobs(
        self,
        urls: List[str],
        batch_id: str
    ) -> int:

        if not urls or not batch_id:
            return 0
        
        try:
            # TODO: 트랜잭션 롤백 필요
            # TODO: crawl_target.has_successful_crawl이 false인 url 처리 필요 
            # ==========================================
            # crawl_targets 테이블에 저장
            # ==========================================
            # crawl_targets에 URL 존재하는지 확인 (멱등성 보장)
            existing_targets = self.client.table('crawl_targets')\
                .select('id')\
                .eq('url', url)\
                .execute()
            
            existing_urls = {row['url'] for row in existing_targets.data}
            new_urls = [url for url in urls if url not in existing_urls]
            if not new_urls:
                logger.info(f"ℹ️ 모든 URL이 이미 존재함, 등록 스킵 (batch_id={batch_id})")
                return 0
            
            target_inserts = [{'url': url} for url in new_urls]
            target_response = self.client.table('crawl_targets')\
                .insert(target_inserts)\
                .execute()

            # ==========================================
            # crawl_jobs 테이블에 저장
            # ==========================================
            job_inserts = []
            for target_row in target_response.data:
                job_inserts.append({
                    'batch_id': batch_id,
                    'crawl_target_id': target_row['id'],
                    'status': 'pending',
                })

            job_response = self.client.table('crawl_jobs')\
                .insert(job_inserts)\
                .execute()

            registered_count = len(job_response.data)
            logger.info(f"✅ {registered_count}개 작업 등록 완료 (batch_id={batch_id})")
            return registered_count

        except Exception as e:
            logger.error(f"❌ 작업 등록 실패: {e}")
            raise DatabaseError("crawl_jobs 벌크 등록 실패") from e

    def get_pending_jobs(self, batch_id: str) -> List[Dict[str, Any]]:

        try:
            # crawl_jobs에서 batch_id로 수집해야 할 url 리스트 가져오기
            response = self.client.table('crawl_jobs')\
                .select('id, status, attempt_count, crawl_target_id, crawl_targets!inner(url), allthatjazz_raw(id)')\
                .eq('batch_id', batch_id)\
                .in_('status', ['pending', 'failed'])\
                .limit(1000)\
                .execute()
            
            jobs = []
            if response.data:
                for job in response.data:
                    # Supabase는 JOIN 결과를 중첩된 객체로 반환 
                    jobs.append({
                        'id': job['id'],
                        'status': job['status'],
                        'attempt_count': job.get('attempt_count', 0),
                        'crawl_target_id': job['crawl_target_id'],
                        'url': job['crawl_targets']['url'],
                        'has_raw': bool(job.get('allthatjazz_raw')),
                    })
            
            logger.info(f"📋 {len(jobs)}개 미완료 작업 조회 (batch_id={batch_id})")
            return jobs
        
        except Exception as e:
            logger.error(f"❌ 미완료 작업 조회 실패: {e}")
            return []

    def update_crawl_job_status(
            self,
            crawl_job_id: str,
            status: str,
            **kwargs
        ) -> bool:
            
            try:
                update_data = {
                    'status': status,
                    'updated_at': datetime.now().isoformat()
                }
                
                if status == 'running':
                    update_data['started_at'] = datetime.now().isoformat()
                
                elif status in ('success', 'failed', 'skipped'):
                    update_data['completed_at'] = datetime.now().isoformat()
                
                # attempt_count 처리
                attempt_count_param = kwargs.get('attempt_count')
                
                # boolean을 None으로 변환 (자동 증가)
                if isinstance(attempt_count_param, bool):
                    attempt_count_param = None
                
                if attempt_count_param is None:
                    # None이면 자동으로 증가
                    current = self.client.table('crawl_jobs')\
                        .select('attempt_count')\
                        .eq('id', crawl_job_id)\
                        .single()\
                        .execute()
                    if current.data:
                        update_data['attempt_count'] = (current.data.get('attempt_count', 0) or 0) + 1
                elif isinstance(attempt_count_param, int):
                    # 정수인 경우: 직접 값 설정
                    update_data['attempt_count'] = attempt_count_param
                
                response = self.client.table('crawl_jobs')\
                    .update(update_data)\
                    .eq('id', crawl_job_id)\
                    .execute()
                
                success = bool(response.data)
                
                # 중요한 상태 업데이트('success') 실패 시 예외 발생
                if not success and status == 'success':
                    error_msg = f"크롤 작업 상태를 'success'로 업데이트 실패: crawl_job_id={crawl_job_id}"
                    logger.error(error_msg)
                    raise Exception(error_msg)
                
                if not success:
                    logger.warning(f"크롤 작업 상태 업데이트 실패: crawl_job_id={crawl_job_id}, status={status}")
                
                return success
            
            except Exception as e:
                # 'success' 상태 업데이트 실패는 예외 재전파
                if status == 'success':
                    logger.error(f"크롤 작업 상태 업데이트 실패: {e}")
                    raise
                logger.warning(f"크롤 작업 상태 업데이트 실패: {e}")
                return False
            
    def create_batch_metadata_sync(
        self,
        batch_num: int,
        stage: str,
        openai_batch_id: str,
        item_count: int,
        **kwargs
    ) -> Optional[str]:
        
        batch = self.get_pipeline_batch_by_num(batch_num)
        if not batch:
            logger.error(f"❌ Pipeline batch 조회 실패: batch_num={batch_num}")
            return None

        metadata = {
            'batch_id': batch['id'],
            'stage': stage,
            'openai_batch_id': openai_batch_id,
            'status': 'submitted',
            'openai_status': 'submitted',
            'parsing_status': 'pending',
            'item_count': item_count,
            'total_count': item_count,
            **kwargs,
        }

        record_id = self.save_batch_job_metadata_sync(metadata)

        if record_id:
            logger.info(f"✅ Batch metadata created: stage={stage}, openai_batch_id={openai_batch_id}, items={item_count}")
        else:
            logger.error(f"❌ Failed to create batch metadata: stage={stage}")

        return record_id
    

    def save_batch_job_metadata_sync(self, metadata: Dict[str, Any]) -> Optional[str]:


        try:
            # ON CONFLICT DO NOTHING으로 멱등성 보장 (필요한 경우)
            response = self.client.table('processing_jobs').insert(metadata).execute()
            if response.data:
                openai_batch_id = response.data[0].get('openai_batch_id', 'Unknown')
                logger.info(f"✅ processing_jobs 저장 완료: openai_batch_id={openai_batch_id}")
                return response.data[0]['id']
            return None
        except Exception as e:
            logger.error(f"❌ processing_jobs 저장 실패: {e}")
            return None
    
    def get_reviews_for_gpt(self, batch_num: int, batch_id: str) -> List[Dict[str, Any]]:

        try:
            
            # crawl_jobs에서 성공한 작업의 id 조회
            jobs_data = self.client.table('crawl_jobs')\
                .select('id')\
                .eq('batch_id', batch_id)\
                .eq('status', 'success')\
                .limit(2000)\
                .execute().data

            crawl_job_ids = [job['id'] for job in jobs_data] if jobs_data else []

            if not crawl_job_ids:
                logger.warning(f"⚠️ Batch {batch_num}: 성공한 작업 없음")
                return []
                
            logger.info(f"📋 Batch {batch_num}: {len(crawl_job_ids)}개 성공한 작업 조회")
            
            # allthatjazz_raw에서 실제 리뷰 데이터 조회
            reviews_response = self.client.table('allthatjazz_raw')\
                .select('id, title, reviewer, published_date, content, album_info, youtube_info, rating, track_listing, personnel')\
                .in_('crawl_job_id', crawl_job_ids)\
                .execute().data
            
            if not reviews_response:
                logger.warning(f"⚠️ Batch {batch_num}: 리뷰 데이터 조회 실패")
                return []
            
            logger.info(f"✅ Batch {batch_num}: {len(reviews_response)}개 리뷰 데이터 조회 완료")
            return reviews_response
        
        except Exception as e:
            logger.error(f"❌ Batch {batch_num} 리뷰 조회 실패: {e}")
            return []
    
    def get_pipeline_batch_by_num(self, batch_num: int) -> Optional[Dict[str, Any]]:

        try:
            response = self.client.table('pipeline_batches')\
                .select('*')\
                .eq('batch_num', batch_num)\
                .single()\
                .execute()
            return response.data if response.data else None
        except Exception as e:
            logger.error(f"❌ Pipeline batch 조회 실패 (batch_num={batch_num}): {e}")
            return None
    
    def create_batch_metadata_sync(
        self,
        batch_num: int,
        stage: str,
        batch_id: str,
        openai_batch_id: str,
        item_count: int,
        **kwargs
    ) -> Optional[str]:

        metadata = {
            'batch_id': batch_id,
            'stage': stage,
            'openai_batch_id': openai_batch_id,
            'status': 'submitted',
            'openai_status': 'submitted',
            'parsing_status': 'pending',
            'item_count': item_count,
            'total_count': item_count,
            **kwargs,
        }

        try:
            response = self.client.table('processing_jobs').insert(metadata).execute()
            if response.data:
                logger.info(f"✅ Batch metadata created: stage={stage}, openai_batch_id={openai_batch_id}, items={item_count}")
                return response.data[0]['id']
            logger.error(f"❌ Failed to create batch metadata: stage={stage}")
            return None
        except Exception as e:
            logger.error(f"❌ processing_jobs 저장 실패: {e}")
            return None
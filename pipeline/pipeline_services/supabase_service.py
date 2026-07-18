import os
import logging
from supabase import create_client, Client
from typing import List, Dict, Any, Optional
from datetime import datetime
from pipeline_services.exceptions import DatabaseError

logger = logging.getLogger(__name__)

class SupabaseService:

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
                .select('url')\
                .in_('url', urls)\
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
            

    def save_error_history(
        self,
        stage: str,
        batch_id: Optional[str] = None,
        crawl_job_id: Optional[str] = None,
        processing_job_id: Optional[str] = None,
        error_type: str = '',
        error_message: str = '',
        error_details: Optional[Dict[str, Any]] = None,
        http_status_code: Optional[int] = None,
        s3_original_html_path: Optional[str] = None
    ) -> Optional[str]:
        if not self.client:
            logger.warning("Supabase 연결 안됨, error_history 저장 불가")
            return None
        try:
            data: Dict[str, Any] = {
                'stage': stage,
                'error_type': error_type,
                'error_message': error_message,
            }
            if batch_id:
                data['batch_id'] = batch_id
            if crawl_job_id:
                data['crawl_job_id'] = crawl_job_id
            if processing_job_id:
                data['processing_job_id'] = processing_job_id
            if error_details:
                data['error_details'] = error_details
            if http_status_code:
                data['http_status_code'] = http_status_code
            if s3_original_html_path:
                data['s3_original_html_path'] = s3_original_html_path

            response = self.client.table('error_history').insert(data).execute()
            if response.data:
                logger.info(f"✅ Error history saved: stage={stage}, error_type={error_type}")
                return response.data[0]['id']
            return None
        except Exception as e:
            logger.error(f"❌ Error history 저장 실패: {e}")
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
    
    
    def create_batch_metadata_sync(
        self,
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
    
    def update_batch_job_status_sync(
        self,
        openai_batch_id: str,
        status: str,
        **kwargs
    ) -> bool:
        """
        processing_jobs 상태 업데이트 (openai_status + parsing_status 분리)
        """
        if not self.client:
            logger.warning("Supabase 연결 안됨, processing_jobs 업데이트 스킵")
            return False

        update_data = {
            'openai_status': status,
            'status': status,
            'updated_at': datetime.now().isoformat()
        }

        if status in ['success', 'partial_success', 'failed']:
            update_data['completed_at'] = datetime.now().isoformat()

        count = kwargs.get('processed_count')
        if count is not None:
            update_data['processed_count'] = count
            update_data['completed_count'] = count
        if kwargs.get('completed_count') is not None:
            update_data['completed_count'] = kwargs['completed_count']

        if kwargs.get('failed_count') is not None:
            update_data['failed_count'] = kwargs['failed_count']

        if kwargs.get('error_message'):
            update_data['error_message'] = kwargs['error_message']

        if kwargs.get('error_type'):
            update_data['error_type'] = kwargs['error_type']

        if kwargs.get('error_details'):
            update_data['error_details'] = kwargs['error_details']

        if kwargs.get('output_file_id'):
            update_data['output_file_id'] = kwargs['output_file_id']

        if kwargs.get('last_check_time'):
            update_data['last_check_time'] = kwargs['last_check_time'].isoformat() if isinstance(kwargs['last_check_time'], datetime) else kwargs['last_check_time']

        if kwargs.get('metadata'):
            update_data['metadata'] = kwargs['metadata']

        if kwargs.get('success_rate') is not None:
            update_data['success_rate'] = float(kwargs['success_rate'])

        if kwargs.get('parsing_status'):
            update_data['parsing_status'] = kwargs['parsing_status']
        if kwargs.get('parsing_count') is not None:
            update_data['parsing_count'] = kwargs['parsing_count']
        if kwargs.get('parsing_failed') is not None:
            update_data['parsing_failed'] = kwargs['parsing_failed']
        if kwargs.get('parsed_at'):
            pt = kwargs['parsed_at']
            update_data['parsed_at'] = pt.isoformat() if isinstance(pt, datetime) else pt

        try:
            self.client.table('processing_jobs')\
                .update(update_data)\
                .eq('openai_batch_id', openai_batch_id)\
                .execute()
            logger.debug(f"✅ processing_jobs 업데이트: openai_batch_id={openai_batch_id}, openai_status={status}")
            return True
        except Exception as e:
            logger.error(f"❌ processing_jobs 업데이트 실패 (openai_batch_id={openai_batch_id}): {e}")
            return False

    def get_batch_by_id_sync(self, openai_batch_id: str) -> Optional[Dict[str, Any]]:
        """
        openai_batch_id로 processing_jobs 조회 (동기)
        """
        if not self.client:
            return None

        try:
            response = self.client.table('processing_jobs')\
                .select('*')\
                .eq('openai_batch_id', openai_batch_id)\
                .single()\
                .execute()
            return response.data if response.data else None
        except Exception as e:
            logger.error(f"❌ get_batch_by_id_sync 실패: {e}")
            return None

    def save_original_html(self, html_content: str, batch_num: int, crawl_job_id: str) -> Optional[str]:
        """
        원본 HTML 저장 (로컬 파일 시스템 또는 S3)

        Returns:
            str: 저장된 파일 경로 (실패 시 None)
        """
        import os
        from pathlib import Path

        use_s3 = os.getenv('USE_S3', 'false').lower() == 'true'

        if use_s3:
            # TODO: S3 업로드 구현
            logger.warning("S3 업로드는 아직 구현되지 않았습니다")
            return None
        else:
            try:
                base_path = Path(os.getenv('CRAWL_STORAGE_PATH', 'data/crawled_html'))
                file_path = base_path / str(batch_num) / crawl_job_id / 'original.html'
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(html_content, encoding='utf-8')
                logger.debug(f"✅ HTML 저장: {file_path}")
                return str(file_path)
            except Exception as e:
                logger.error(f"❌ HTML 저장 실패: {e}")
                return None

    def get_existing_raw_ids_sync(self, raw_ids: List[str]) -> set:
        if not self.client:
            raise RuntimeError("Supabase에 연결되지 않았습니다")

        if not raw_ids:
            return set()

        try:
            response = self.client.table('processed_summary')\
                .select('raw_id')\
                .in_('raw_id', raw_ids)\
                .execute()
            return {row['raw_id'] for row in response.data}
        except Exception as e:
            logger.error(f"❌ 기존 raw_ids 조회 실패: {e}")
            return set()

    def save_processed_summary_sync(
        self, 
        raw_id: str,  # UUID 문자열
        summary: str, 
        batch_num: int,
        model_id: Optional[str] = None,
        token_usage: Optional[Dict[str, int]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        summary_data: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        processed_summary 저장 및 ID 반환 (동기 버전)
        
        Args:
            raw_id: 원본 데이터 ID (UUID 문자열)
            summary: 요약 텍스트
            batch_num: 배치 번호
            model_id: 모델 ID
            token_usage: 토큰 사용량
            temperature: 온도 설정
            max_tokens: 최대 토큰 수
            summary_data: 전체 요약 데이터 (JSONB로 저장)
            
        Returns:
            str: 생성된 레코드 ID (실패 시 None)
        """
        if not self.client:
            raise RuntimeError("Supabase에 연결되지 않았습니다")
        
        try:
            # summary_data가 제공되지 않으면 기본 구조 생성
            if summary_data is None:
                summary_data = {
                    'summary': summary,
                    'batch_num': batch_num,
                    'token_usage': token_usage,
                    'temperature': temperature,
                    'max_tokens': max_tokens
                }
            else:
                # summary_data에 batch_num 추가 (없는 경우)
                if 'batch_num' not in summary_data:
                    summary_data['batch_num'] = batch_num
            
            data = {
                'raw_id': raw_id,  # UUID 문자열
                'summary_text': summary,
                'summary_data': summary_data
            }
            
            # model_id가 제공되면 추가
            if model_id:
                data['model_id'] = model_id
            
            # token_usage 컬럼에도 저장
            if token_usage:
                data['token_usage'] = token_usage
            
            # 처리 설정 저장
            if temperature is not None:
                data['temperature'] = temperature
            if max_tokens is not None:
                data['max_tokens'] = max_tokens
            
            response = self.client.table('processed_summary')\
                .insert(data)\
                .execute()
            
            if response.data and len(response.data) > 0:
                record_id = response.data[0]['id']
                logger.debug(f"✅ processed_summary 저장 성공: raw_id={raw_id}, id={record_id}")
                return record_id
            else:
                logger.warning(f"⚠️ processed_summary 저장 응답 없음: raw_id={raw_id}")
                return None
        except Exception as e:
            logger.error(f"❌ processed_summary 저장 실패 (raw_id={raw_id}): {e}")
            return None

    def log_api_usage(
        self,
        openai_batch_id: str,
        stage: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> bool:
        """
        API 토큰 사용량 및 비용을 api_usage_logs에 기록.
        단가는 ai_models 테이블에서 직접 조회하여 계산.

        Args:
            openai_batch_id: OpenAI Batch ID
            stage: 'gpt' | 'embedding'
            model: 사용 모델명
            prompt_tokens: input token 수
            completion_tokens: output token 수 (embedding은 0)
        """
        if not self.client:
            logger.warning("Supabase 연결 안됨, api_usage_logs 저장 불가")
            return False

        input_rate, output_rate = self._get_model_rates(model)
        cost_usd = (prompt_tokens / 1000.0) * input_rate + (completion_tokens / 1000.0) * output_rate

        try:
            self.client.table('api_usage_logs').insert({
                'openai_batch_id': openai_batch_id,
                'stage': stage,
                'model': model,
                'prompt_tokens': prompt_tokens,
                'completion_tokens': completion_tokens,
                'total_tokens': prompt_tokens + completion_tokens,
                'cost_usd': cost_usd,
            }).execute()
            logger.info(
                f"💰 API 사용량 기록: {stage}/{model} "
                f"prompt={prompt_tokens}, completion={completion_tokens}, "
                f"cost=${cost_usd:.6f}"
            )
            return True
        except Exception as e:
            logger.error(f"❌ api_usage_logs 저장 실패: {e}")
            return False

    def _get_model_rates(self, model_name: str) -> tuple[float, float]:
        """ai_models 테이블에서 input/output 단가 조회. (cost_per_1k_input, cost_per_1k_output)"""
        try:
            resp = self.client.table('ai_models') \
                .select('cost_per_1k_input, cost_per_1k_output') \
                .eq('model_name', model_name) \
                .single() \
                .execute()
            if resp.data:
                return (resp.data.get('cost_per_1k_input') or 0.0,
                        resp.data.get('cost_per_1k_output') or 0.0)
        except Exception as e:
            logger.warning(f"⚠️ ai_models 단가 조회 실패 ({model_name}): {e}")
        return (0.0, 0.0)
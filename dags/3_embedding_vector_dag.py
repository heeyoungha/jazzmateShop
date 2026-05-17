from datetime import datetime, timedelta
from typing import Dict, Any
import logging

from airflow.decorators import dag, task

logger = logging.getLogger(__name__)

def get_slack_alert():
    """Lazy import for slack_alert callback"""
    from common.slack import slack_alert
    return slack_alert

# 부분 실패 허용 임계값
SUCCESS_RATE_THRESHOLD = 0.8  # 80% 이상 성공 시 completed로 간주


@dag(
    dag_id='3_embedding_vector_dag',
    default_args={
        'owner': 'hee',
        'depends_on_past': False,
        'retries': 2,
        'retry_delay': timedelta(minutes=10),
        'on_failure_callback': get_slack_alert(),
    },
    description='[Sensor 기반] Embedding Batch 완료 대기 → 결과 처리 → VectorDB 저장',
    schedule_interval=None,  # ✅ 수동 트리거 (Sensor가 배치 완료 대기)
    start_date=datetime(2024, 1, 1),
    catchup=False,
)
def embedding_vector_dag():
   
    @task.sensor(
        task_id='wait_for_embedding_completion',
        poke_interval=300,      # 5분마다 체크
        timeout=86400,           # 24시간 타임아웃
        mode='reschedule',       # ✅ Worker 해제!
        execution_timeout=timedelta(hours=24),
    )
    def wait_for_embedding_completion(**context) -> bool:

        from pipeline_services import SupabaseService, OpenAIService
        from datetime import datetime

        # DB 연결 (상태 업데이트용으로 항상 필요)
        db = SupabaseService()

        # DAG Run Config: 정상 워크플로에서는 openai_batch_id 전달 → DB 조회 없이 사용
        dag_run = context.get('dag_run')
        conf = (dag_run.conf or {}) if dag_run else {}
        openai_batch_id = conf.get('openai_batch_id')
        batch_id = conf.get('batch_id')

        logger.info(f"🔍 Waiting for Embedding batch completion: openai_batch_id={openai_batch_id or batch_id}")

        if not openai_batch_id:
            if not batch_id:
                # 부분 재실행: DB에서 최신 진행 중인 배치 조회
                response = db.client.table('processing_jobs')\
                    .select('*')\
                    .eq('stage', 'embedding')\
                    .not_.in_('openai_status', ['success', 'partial_success', 'failed', 'cancelled', 'expired'])\
                    .order('submitted_at', desc=True)\
                    .limit(1)\
                    .execute()
                if not response.data:
                    response = db.client.table('processing_jobs')\
                        .select('*')\
                        .eq('stage', 'embedding')\
                        .in_('openai_status', ['success', 'partial_success', 'failed'])\
                        .order('submitted_at', desc=True)\
                        .limit(1)\
                        .execute()
                    if not response.data:
                        raise Exception("No Embedding batch found (in-progress or completed)")
                openai_batch_id = response.data[0]['openai_batch_id']
            else:
                # batch_id만 넘긴 경우: DB에서 openai_batch_id 조회
                by_batch = db.client.table('processing_jobs')\
                    .select('openai_batch_id')\
                    .eq('stage', 'embedding')\
                    .eq('batch_id', batch_id)\
                    .order('submitted_at', desc=True)\
                    .limit(1)\
                    .execute()
                if by_batch.data:
                    openai_batch_id = by_batch.data[0]['openai_batch_id']
                else:
                    by_id = db.client.table('processing_jobs')\
                        .select('openai_batch_id')\
                        .eq('id', batch_id)\
                        .execute()
                    if by_id.data:
                        openai_batch_id = by_id.data[0]['openai_batch_id']
                    else:
                        openai_batch_id = batch_id  # 문자열이 OpenAI batch id인 경우

        # OpenAI API 상태 확인
        openai = OpenAIService()
        status_info = openai.check_batch_status(openai_batch_id)

        if not status_info:
            logger.warning(f"⚠️ Failed to check batch status: {openai_batch_id}")
            return False

        openai_status = status_info.get('status')
        request_counts = status_info.get('request_counts', {})
        total_requests = request_counts.get('total', 0)
        completed_requests = request_counts.get('completed', 0)
        failed_requests = request_counts.get('failed', 0)

        # OpenAI status를 우리 status로 매핑
        status_mapping = {
            'submitted': 'submitted',
            'validating': 'validating',
            'in_progress': 'running',
            'finalizing': 'finalizing',
            'completed': 'success',  # 임시, 아래에서 세분화
            'failed': 'failed',
            'cancelled': 'cancelled',
            'expired': 'expired'
        }
        db_status = status_mapping.get(openai_status, openai_status)

        # 상태 세분화: completed → success / partial_success
        if openai_status == 'completed':
            # 세분화된 상태 계산
            if total_requests == 0:
                final_status = 'failed'
            elif failed_requests == 0:
                final_status = 'success'
            else:
                success_rate = completed_requests / total_requests if total_requests > 0 else 0.0
                if success_rate >= SUCCESS_RATE_THRESHOLD:
                    final_status = 'partial_success'
                else:
                    final_status = 'failed'
            
            # 세분화된 상태로 바로 저장
            db.update_batch_job_status_sync(
                openai_batch_id=openai_batch_id,
                status=final_status,
                processed_count=completed_requests,
                failed_count=failed_requests,
                success_rate=completed_requests / total_requests if total_requests > 0 else 0.0,
                last_check_time=datetime.now(),
                output_file_id=status_info.get('output_file_id')
            )
            logger.info(f"✅ Embedding batch completed: {final_status} ({completed_requests}/{total_requests})")
            return True
        else:
            # 진행 중인 경우 상태 업데이트
            db.update_batch_job_status_sync(
                openai_batch_id=openai_batch_id,
                status=db_status,
                processed_count=completed_requests,
                failed_count=failed_requests,
                last_check_time=datetime.now(),
                output_file_id=status_info.get('output_file_id')
            )
            logger.info(f"⏳ Embedding batch still in progress: {openai_status} ({completed_requests}/{total_requests})")
            return False

    @task(
        task_id='process_embedding_result',
        execution_timeout=timedelta(minutes=30),
    )
    def process_embedding_result(**context) -> Dict[str, Any]:

        from pipeline_services import SupabaseService, OpenAIService

        conf = (context.get('dag_run').conf or {}) if context.get('dag_run') else {}
        openai_batch_id = conf.get('openai_batch_id')
        batch_id = conf.get('batch_id')

        db = SupabaseService()

        if not openai_batch_id:
            if not batch_id:
                response = db.client.table('processing_jobs')\
                    .select('*')\
                    .eq('stage', 'embedding')\
                    .in_('openai_status', ['success', 'partial_success', 'failed'])\
                    .order('submitted_at', desc=True)\
                    .limit(1)\
                    .execute()
                if not response.data:
                    raise Exception("No completed Embedding batch found")
                batch = response.data[0]
            else:
                by_fk = db.client.table('processing_jobs')\
                    .select('*')\
                    .eq('stage', 'embedding')\
                    .eq('batch_id', batch_id)\
                    .order('submitted_at', desc=True)\
                    .limit(1)\
                    .execute()
                if by_fk.data:
                    batch = by_fk.data[0]
                else:
                    by_id = db.client.table('processing_jobs')\
                        .select('*')\
                        .eq('id', batch_id)\
                        .execute()
                    if not by_id.data:
                        raise Exception(f"Batch not found: {batch_id}")
                    batch = by_id.data[0]
            openai_batch_id = batch['openai_batch_id']
            batch_id_fk = batch['batch_id']
        else:
            # openai_batch_id로 processing_job 조회하여 batch_id_fk, batch_num 얻기
            pj = db.client.table('processing_jobs')\
                .select('batch_id')\
                .eq('stage', 'embedding')\
                .eq('openai_batch_id', openai_batch_id)\
                .limit(1)\
                .execute()
            if not pj.data:
                raise Exception(f"No processing_job found for openai_batch_id={openai_batch_id}")
            batch_id_fk = pj.data[0]['batch_id']

        batch_response = db.client.table('pipeline_batches')\
            .select('batch_num')\
            .eq('id', batch_id_fk)\
            .single()\
            .execute()
        batch_num = batch_response.data['batch_num'] if batch_response.data else None

        logger.info(f"🚀 Processing Embedding result: openai_batch_id={openai_batch_id}, batch_num={batch_num}")

        batch_row = db.get_batch_by_id_sync(openai_batch_id)
        current_status = (batch_row.get('openai_status') or batch_row.get('status') or 'running') if batch_row else 'running'
        db.update_batch_job_status_sync(
            openai_batch_id=openai_batch_id,
            status=current_status,
            parsing_status='running',
        )

        try:
            openai = OpenAIService()
            results_path = openai.download_batch_results(openai_batch_id)
            if not results_path:
                raise Exception(f"Failed to download batch results: {openai_batch_id}")

            parsed = openai.parse_embedding_batch_results(results_path)
            items = parsed.get('items') or []
            success_count = 0
            failed_count = parsed.get('parsing_failed', 0)

            model_id = 'text-embedding-3-small'
            for item in items:
                try:
                    ok = db.save_embedding_metadata(
                        raw_id=item['raw_id'],
                        processed_id=item['processed_id'],
                        vector_id=str(item['processed_id']),
                        dim=len(item['embedding']),
                        embedding=item['embedding'],
                        model_id=model_id,
                    )
                    if ok:
                        success_count += 1
                    else:
                        failed_count += 1
                except Exception as e:
                    logger.warning(f"⚠️ Failed to save embedding: processed_id={item.get('processed_id')}: {e}")
                    failed_count += 1

            logger.info(f"✅ Task 2 completed: success={success_count}, failed={failed_count}")

            db.update_batch_job_status_sync(
                openai_batch_id=openai_batch_id,
                status=current_status,
                parsing_status='done',
                parsing_count=success_count,
                parsing_failed=failed_count,
                parsed_at=datetime.now(),
            )

            # API 사용량 기록
            token_usage = parsed.get('token_usage', {})
            if token_usage.get('total_tokens', 0) > 0:
                db.log_api_usage(
                    openai_batch_id=openai_batch_id,
                    stage='embedding',
                    model='text-embedding-3-small',
                    prompt_tokens=token_usage['prompt_tokens'],
                    completion_tokens=0,
                )

            return {
                'batch_num': batch_num,
                'success_count': success_count,
                'failed_count': failed_count,
            }
        except Exception as e:
            db.update_batch_job_status_sync(
                openai_batch_id=openai_batch_id,
                status=current_status,
                parsing_status='failed',
                error_message=str(e),
                error_type='processing_error',
            )
            raise

    # TODO: 외부 벡터 DB 연동 시 save_to_vectordb task 추가
    # 현재는 process_embedding_result에서 Supabase pgvector에 직접 저장

    # 파이프라인 정의
    wait_result = wait_for_embedding_completion()
    embedding_result = process_embedding_result()

    # 의존성 설정: Sensor 완료 후 Embedding 결과 처리
    wait_result >> embedding_result


# DAG 인스턴스 생성
dag_instance = embedding_vector_dag()

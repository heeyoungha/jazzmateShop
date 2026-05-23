from datetime import datetime, timedelta
from typing import Dict, Any
import logging

from airflow.decorators import dag, task
from airflow.operators.trigger_dagrun import TriggerDagRunOperator
from airflow.exceptions import AirflowFailException, AirflowSkipException

logger = logging.getLogger(__name__)

def get_slack_alert():
    """Lazy import for slack_alert callback"""
    from common.slack import slack_alert
    return slack_alert

# 부분 실패 허용 임계값
SUCCESS_RATE_THRESHOLD = 0.8  # 80% 이상 성공 시 completed로 간주


@dag(
    dag_id='2_summary_dag',
    default_args={
        'owner': 'hee', # DAG 담당자
        'depends_on_past': False, # 이전 DAG 실행이 실패했어도 다음 DAG 실행은 독립적으로 수행가능
        'retries': 2, # Task가 실패했을 때 최대 2번 추가로 재시도 (총 3번)
        'retry_delay': timedelta(minutes=10), # 재시도 간격 10분
        'on_failure_callback': get_slack_alert(),
    },
    description='[Sensor 기반] GPT Batch 완료 대기 → 결과 처리 → Embedding 제출',
    schedule_interval=None,  # ✅ 수동 트리거 (Sensor가 배치 완료 대기)
    start_date=datetime(2024, 1, 1),
    catchup=False,
)
def summary_dag():

    @task.sensor(
        task_id='wait_for_gpt_completion',
        poke_interval=300,      # 5분마다 체크
        timeout=86400,                # 24시간 타임아웃
        mode='reschedule',            # Worker 해제
        execution_timeout=timedelta(hours=2),
    )
    def wait_for_gpt_completion(**context) -> bool:

        from pipeline_services import SupabaseService, OpenAIService, SlackService

        openai_batch_id = None
        batch = None

        db = SupabaseService()

        # batch_id, openai_batch_id 조회 
        conf = (context['dag_run'].conf or {}) if context.get('dag_run') else {}
        openai_batch_id = conf.get('openai_batch_id')
        batch_id = conf.get('batch_id')
        
        # DAG 1에서 트리거된 경우: batch_id, openai_batch_id 둘 다 필수. 하나라도 없으면 fail
        if batch_id or openai_batch_id:
            if not batch_id or not openai_batch_id:
                raise Exception(
                    "DAG 2 was triggered with config but batch_id or openai_batch_id is missing. "
                )
            # 둘 다 있으면 openai_batch_id 그대로 사용 (DB 조회 없음)        
        
        else:
            # 2단계만 따로 실행: Config 없음 → DB에서 최신 진행 중 배치 조회
            db = SupabaseService()
            response = db.client.table('processing_jobs')\
                .select('*')\
                .eq('stage', 'gpt')\
                .not_.in_('openai_status', ['success', 'partial_success', 'failed', 'cancelled', 'expired'])\
                .order('submitted_at', desc=True)\
                .limit(1)\
                .execute()
            if not response.data:
                raise Exception("No in-progress GPT batch found")
            batch = response.data[0]
            openai_batch_id = batch['openai_batch_id']
            batch_id = batch['batch_id'] 

        if not openai_batch_id:
            raise AirflowFailException("openai_batch_id could not be resolved")
        
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
        
        # DB 상태 동기화 (항상)
        db.update_batch_job_status_sync(
            openai_batch_id=openai_batch_id,
            status=db_status,
            processed_count=completed_requests,
            failed_count=failed_requests,
            last_check_time=datetime.now(),
            output_file_id=status_info.get('output_file_id')
        )
        
        # 상태 세분화: completed → success / partial_success
        if openai_status == 'completed':
            if total_requests > 0:
                success_rate = completed_requests / total_requests
            else:
                success_rate = 0.0
            
            logger.info(
                f"📊 Batch {openai_batch_id} completed: "
                f"completed={completed_requests}/{total_requests}, "
                f"success_rate={success_rate:.1%}"
            )
            
            if completed_requests == total_requests:

                final_status = 'success'
                db.update_batch_job_status_sync(
                    openai_batch_id=openai_batch_id,
                    status=final_status,
                    processed_count=completed_requests,
                    failed_count=0,
                    success_rate=success_rate,
                    metadata={'success_rate': success_rate}
                )
                logger.info(f"✅ Batch {openai_batch_id} success (100%)")
                
            elif completed_requests > 0:
                # 성공률이 80% 이상이면 다음 단계 진행
                success_rate_pct = success_rate * 100
                if success_rate >= SUCCESS_RATE_THRESHOLD:
                    final_status = 'partial_success'
                    db.update_batch_job_status_sync(
                        openai_batch_id=openai_batch_id,
                        status=final_status,
                        processed_count=completed_requests,
                        failed_count=failed_requests,
                        success_rate=success_rate,
                        metadata={'success_rate': success_rate}
                    )
                    logger.warning(
                        f"⚠️ Batch {openai_batch_id} partial_success: "
                        f"{success_rate_pct:.1f}% (proceeding)"
                    )
                else:
                    # 성공률 낮음 → 실패 처리
                    final_status = 'failed'
                    db.update_batch_job_status_sync(
                        openai_batch_id=openai_batch_id,
                        status=final_status,
                        processed_count=completed_requests,
                        failed_count=failed_requests,
                        success_rate=success_rate,
                        error_message=f"Low success rate: {success_rate_pct:.1f}%",
                        error_type='low_success_rate',
                        metadata={'success_rate': success_rate}
                    )
                    logger.error(
                        f"❌ Batch {openai_batch_id} failed: "
                        f"{success_rate_pct:.1f}% (below threshold)"
                    )
                    # Slack 알림 전송 
                    slack = SlackService()
                    slack.check_and_send_alert(
                        stage='gpt',
                        success_rate=success_rate,
                        success_count=completed_requests,
                        failed_count=failed_requests,
                        batch_num=batch.get('batch_num') if 'batch' in locals() else None,
                        batch_id=openai_batch_id,
                        error_message=None
                    )
                    # 부분 실패 허용: 실패해도 다음 단계로 진행
                    return True
            
            else:
                # ❌ 완전 실패
                final_status = 'failed'
                db.update_batch_job_status_sync(
                    openai_batch_id=openai_batch_id,
                    status=final_status,
                    processed_count=0,
                    failed_count=total_requests,
                    success_rate=0.0,
                    error_message="Batch completely failed: no successful requests",
                    error_type='complete_failure',
                    metadata={'success_rate': 0.0}
                )
                logger.error(f"❌ Batch {openai_batch_id} failed (0% success)")
                # 부분 실패 허용: 실패해도 다음 단계로 진행
                return True
            
            # 완료 처리 완료
            return True
        
        elif openai_status in ['failed', 'expired', 'cancelled']:
            # ✅ OpenAI API 레벨 실패 → failed로 기록
            db.update_batch_job_status_sync(
                openai_batch_id=openai_batch_id,
                status='failed',
                error_message=f"Batch {openai_status}",
                error_type='batch_api_failed',
                metadata={'openai_status': openai_status}
            )
            logger.error(f"❌ Batch {openai_batch_id} failed (OpenAI status: {openai_status})")
            # 부분 실패 허용: 실패해도 다음 단계로 진행
            return True
        
        # 진행 중
        logger.info(f"⏳ Batch {openai_batch_id} still in progress: {openai_status}")
        return False

    @task(
        task_id='process_gpt_result',
        execution_timeout=timedelta(minutes=30),
    )
    def process_gpt_result(**context) -> Dict[str, Any]:

        from pipeline_services import SupabaseService, OpenAIService, GptResultProcessor

        # DAG Run Config 또는 최신 completed 배치로 조회
        conf = (context.get('dag_run').conf or {}) if context.get('dag_run') else {}
        openai_batch_id_conf = conf.get('openai_batch_id')

        db = SupabaseService()

        if openai_batch_id_conf:
            # DAG 1에서 트리거된 경우: openai_batch_id로 processing_jobs 조회
            batch = db.get_batch_by_id_sync(openai_batch_id_conf)
            if not batch:
                raise Exception(f"Batch not found: openai_batch_id={openai_batch_id_conf}")
            openai_batch_id = openai_batch_id_conf
        else:
            # config 없음: DB에서 최신 completed 배치 조회
            response = db.client.table('processing_jobs')\
                .select('*')\
                .eq('stage', 'gpt')\
                .in_('openai_status', ['success', 'partial_success', 'failed'])\
                .order('completed_at', desc=True)\
                .limit(1)\
                .execute()

            if not response.data:
                raise Exception("No completed GPT batch found")

            batch = response.data[0]
            openai_batch_id = batch['openai_batch_id']
        
        # batch_num 조회 (pipeline_batches에서)
        batch_id_fk = batch['batch_id']  # FK
        if not batch_id_fk:
            raise Exception(f"batch_id is None in processing_jobs: batch={batch}")
        
        batch_response = db.client.table('pipeline_batches')\
            .select('batch_num')\
            .eq('id', batch_id_fk)\
            .single()\
            .execute()

        if not batch_response.data:
            raise Exception(f"No pipeline_batch found for batch_id={batch_id_fk}")

        batch_num = batch_response.data['batch_num'] if batch_response.data else None
        if batch_num is None:
            raise Exception(f"batch_num is None for batch_id={batch_id_fk}")

        batch_status = batch.get('openai_status') or batch.get('status')
        if not batch_status:
            raise Exception(f"batch_status is None for batch_id={batch_id_fk}")     

        # 파싱 시작: parsing_status = running
        db.update_batch_job_status_sync(
            openai_batch_id=openai_batch_id,
            status=batch_status,
            parsing_status='running',
        )
        
        # Service 레이어 호출 (비즈니스 로직 위임)
        openai = OpenAIService()
        processor = GptResultProcessor(db, openai)
        
        try:
            result = processor.process_batch_results(
                batch_id=openai_batch_id,  # OpenAI Batch ID
                batch_num=batch_num,
                batch_status=batch_status
            )
        except Exception as e:
            # DB에 실패 기록
            db.update_batch_job_status_sync(
                openai_batch_id=openai_batch_id,
                status=batch.get('openai_status') or batch.get('status', 'failed'),
                parsing_status='failed',
                error_message=str(e),
                error_type='processing_error',
            )
            # 영구 실패(배치 failed/expired/cancelled): 스킵 → 다음 태스크 실행 안 함
            from pipeline_services.exceptions import BatchFailedError
            if isinstance(e, BatchFailedError):
                logger.warning(f"⏭️ Permanent batch failure, skipping downstream: {e}")
                raise AirflowSkipException(str(e))
            logger.error(f"❌ GPT result processing failed: {e}", exc_info=True)
            raise
        
        # DB 통계 업데이트 (parsing_status=done, parsing_count, parsing_failed, parsed_at)
        existing_status = batch.get('openai_status') or batch.get('status', 'success')
        db.update_batch_job_status_sync(
            openai_batch_id=openai_batch_id,
            status=existing_status,
            processed_count=result['success_count'],
            failed_count=result['failed_count'],
            parsing_status='done',
            parsing_count=result['success_count'],
            parsing_failed=result['failed_count'],
            parsed_at=datetime.now(),
            error_message=result['error_message'],
            error_type='processing_error' if result['failed_count'] > 0 else None,
            error_details=result['error_details']
        )

        # API 사용량 기록
        token_usage = result.get('token_usage', {})
        if token_usage.get('total_tokens', 0) > 0:
            db.log_api_usage(
                openai_batch_id=openai_batch_id,
                stage='gpt',
                model='gpt-4o-mini',
                prompt_tokens=token_usage['prompt_tokens'],
                completion_tokens=token_usage['completion_tokens'],
            )
        
        logger.info(
            f"✅ Task 2 completed: "
            f"saved={result['success_count']}, "
            f"failed={result['failed_count']}, "
            f"skipped={result['skipped_count']}"
        )
        
        return {
            'batch_num': batch_num,
            'success_count': result['success_count'],
            'error_count': result['failed_count']
        }

    @task(
        task_id='submit_embedding_batch',
        execution_timeout=timedelta(minutes=30)
    )
    def submit_embedding_batch(gpt_result: Dict[str, Any]) -> Dict[str, Any]:

        from pipeline_services import SupabaseService, OpenAIService

        batch_num = gpt_result['batch_num']

        logger.info(f"🚀 Submitting Embedding Batch for batch {batch_num}")

        # DB 연결
        db = SupabaseService()

        # batch_num → batch_id → crawl_job_id → raw id (allthatjazz_raw에는 batch_num 컬럼 없음)
        # Step 1: batch_num으로 pipeline_batches.id 조회
        batch_row = db.client.table('pipeline_batches')\
            .select('id')\
            .eq('batch_num', batch_num)\
            .limit(1)\
            .execute()
        if not batch_row.data:
            raise Exception(f"No pipeline_batch found for batch_num {batch_num}")
        batch_id = batch_row.data[0]['id']

        # Step 2: batch_id로 crawl_jobs.id 목록 조회
        crawl_jobs_response = db.client.table('crawl_jobs')\
            .select('id')\
            .eq('batch_id', batch_id)\
            .limit(50000)\
            .execute()
        if not crawl_jobs_response.data:
            raise Exception(f"No crawl_jobs found for batch_num {batch_num}")
        crawl_job_ids = [row['id'] for row in crawl_jobs_response.data]

        # Step 3: crawl_job_id로 allthatjazz_raw.id 조회 (청크 단위, in 쿼리 크기 제한 대비)
        raw_ids = []
        chunk_size = 500
        for i in range(0, len(crawl_job_ids), chunk_size):
            chunk = crawl_job_ids[i:i + chunk_size]
            raw_response = db.client.table('allthatjazz_raw')\
                .select('id')\
                .in_('crawl_job_id', chunk)\
                .execute()
            if raw_response.data:
                raw_ids.extend(row['id'] for row in raw_response.data)

        if not raw_ids:
            raise Exception(f"No raw data found for batch {batch_num}")
        logger.info(f"📋 Found {len(raw_ids)} raw_ids for batch {batch_num}")
        
        # Step 2: raw_ids로 processed_summary 조회
        # 배치 크기 제한을 위해 청크 단위로 조회
        processed_summaries = []
        chunk_size = 1000
        
        for i in range(0, len(raw_ids), chunk_size):
            chunk_raw_ids = raw_ids[i:i + chunk_size]
            response = db.client.table('processed_summary')\
                .select('id, raw_id, summary_text')\
                .in_('raw_id', chunk_raw_ids)\
                .execute()
            
            if response.data:
                processed_summaries.extend(response.data)
        
        if not processed_summaries:
            raise Exception(f"No processed_summary found for batch {batch_num}")
        
        logger.info(f"📋 {len(processed_summaries)}개 요약을 임베딩 배치로 제출")
        
        # OpenAI Embedding Batch API 제출
        openai = OpenAIService()
        
        # Step 1: Batch 요청 생성
        batch_requests = openai.create_embedding_batch_requests(processed_summaries)
        if not batch_requests:
            raise Exception("Failed to create embedding batch requests")
        
        # Step 2: 파일 업로드
        file_id = openai.upload_batch_file(batch_requests, batch_num)

        # Step 3: Batch 작업 제출
        embedding_batch_id = openai.create_embedding_batch_job(file_id)
        if not embedding_batch_id:
            raise Exception("Failed to create embedding batch job")
        
        # processing_jobs에 저장
        db.create_batch_metadata_sync(
            batch_num=batch_num,
            stage='embedding',
            openai_batch_id=embedding_batch_id,  # ✅ 실제 OpenAI batch_id
            item_count=len(processed_summaries),
            file_id=file_id,
            metadata={
                'gpt_completed_at': datetime.now().isoformat(),
                'gpt_success_count': gpt_result['success_count'],
                'gpt_error_count': gpt_result['error_count']
            }
        )

        logger.info(
            f"✅ Task 3 completed: "
            f"batch_id={embedding_batch_id}, "
            f"items={len(processed_summaries)}"
        )

        return {
            'batch_num': batch_num,
            'batch_id': embedding_batch_id,
            'item_count': len(processed_summaries)
        }

    # 파이프라인 정의
    wait_result = wait_for_gpt_completion()
    gpt_result = process_gpt_result()
    embedding_result = submit_embedding_batch(gpt_result)
    
    # 의존성 설정: Sensor 완료 후 GPT 결과 처리
    wait_result >> gpt_result
    
    # DAG 3 자동 트리거 (Sensor 방식 유지하면서 자동화)
    trigger_dag3 = TriggerDagRunOperator(
        task_id='trigger_embedding_vector_dag',
        trigger_dag_id='3_embedding_vector_dag',
        conf={
            'batch_id': '{{ ti.xcom_pull(task_ids="submit_embedding_batch")["batch_id"] }}',
            'openai_batch_id': '{{ ti.xcom_pull(task_ids="submit_embedding_batch")["batch_id"] }}',  # 정상 워크플로: DB 조회 없이 사용
            'batch_num': '{{ ti.xcom_pull(task_ids="submit_embedding_batch")["batch_num"] }}',
        },
        wait_for_completion=False,  # DAG 3은 Sensor가 대기하므로 False
    )
    
    # 의존성 설정: Embedding 배치 제출 후 DAG 3 트리거
    embedding_result >> trigger_dag3


# DAG 인스턴스 생성
dag_instance = summary_dag()

from datetime import datetime, timedelta
from typing import Dict, Any
from common.slack import slack_alert

# airflow 클래스. dag간 데이터 공유, 의존성 관리를 위한 키-값 저장소
from airflow.models import Variable
# Airflow 관련 모듈
from airflow.decorators import dag, task
from airflow.operators.trigger_dagrun import TriggerDagRunOperator
from airflow.exceptions import AirflowSkipException

import logging

logger = logging.getLogger(__name__)

@dag(
    dag_id='1_crawl_dag', 
    max_active_runs=1,
    default_args={ 
        'owner': 'hee', 
        'depends_on_past': False, # 이전 DAG 실행이 실패했어도 다음 DAG 실행은 독립적으로 수행가능
        'retries': 1, 
        'retry_delay': timedelta(minutes=5), 
        'on_failure_callback': slack_alert,
    },
    description='URL 수집 → 크롤링 → GPT Batch 제출',
    schedule_interval=None, 
    # schedule="*/30 * * * *", 
    start_date=datetime(2026, 2, 28), # "언제부터 이 DAG를 실행할 수 있는가"를 판단하는 기준점. 반드시 필요
    catchup=False, # 이전 실행 데이터 무시하고 최신 데이터만 처리. 테스트 중에는 DAG를 자주 껐다 켜기 때문에 catchup=False가 사실상 필수
)
def crawl_dag():

    @task.branch(task_id='check_pending_batch')
    def check_pending_batch() -> str:
        from pipeline_services import SupabaseService
        from airflow.operators.python import get_current_context
        db = SupabaseService()
        pending = db.get_pending_batch_for_retry()
        if pending:
            logger.info(
                f"🔄 미완료 배치 발견: batch_num={pending['batch_num']}, "
                f"pending_count={pending['pending_count']} → URL 수집 스킵"
            )
            # XCom push를 직접 해야 하는 경우 (branch task는 return이 task_id여야 해서)
            context = get_current_context()
            context['ti'].xcom_push(key='pending_batch', value=pending)
            return 'resume_pending_batch'
        return 'create_batch'

    @task(task_id='resume_pending_batch')
    def resume_pending_batch() -> Dict[str, Any]:
        from airflow.operators.python import get_current_context
        context = get_current_context()
        pending = context['ti'].xcom_pull(task_ids='check_pending_batch', key='pending_batch')
        logger.info(
            f"🔄 재실행: batch_num={pending['batch_num']}, url_count={pending['pending_count']}"
        )
        # 건너뛰고 merged ─► crawl_details 시작
        return {
            'batch_num': pending['batch_num'],
            'batch_id': pending['batch_id'],
            'url_count': pending['pending_count'],
            'job_ids': pending['job_ids'],
        }

    @task(task_id='create_batch')
    def create_batch() -> Dict[str, Any]:
        from pipeline_services import SupabaseService
        from airflow.operators.python import get_current_context

        context = get_current_context()
        dag_run = context['dag_run']
        airflow_dag_run_id = dag_run.run_id

        db = SupabaseService()
        batch_info = db.generate_batch_num(airflow_dag_run_id)
        logger.info(f"✅ Batch {batch_info['batch_num']} 생성 (batch_id={batch_info['batch_id']})")
        return batch_info  # {'batch_num': int, 'batch_id': str}

    @task(task_id='collect_and_register_urls', execution_timeout=timedelta(minutes=30))
    def collect_and_register_urls(batch_info: Dict[str, Any], page_count: int = 5) -> Dict[str, Any]:
        from pipeline_services import (
            SupabaseService,
            URLCollectorService,
        )
        from pipeline_services.async_runner import run_async
        from pipeline_services.exceptions import BlockedError, ParseError, NetworkError, TimeoutError

        batch_num = batch_info['batch_num']
        batch_id = batch_info['batch_id']

        # 시작 페이지 계산
        start_page = int(Variable.get("current_start_page", default_var=1))
        if start_page > 3000:
            start_page = 1
        end_page = start_page + page_count - 1
        logger.info(f"📄 Crawling pages {start_page} ~ {end_page}")

        db = SupabaseService()

        # URL 수집
        url_collector = URLCollectorService(db)
        try:
            urls = run_async(url_collector.collect_review_urls(
                start_page=start_page,
                end_page=end_page,
            ))
            logger.info(f"✅ URL 수집 완료: {len(urls)}개")
        except Exception as e:
            logger.error(f"❌ URL 수집 실패: {e}", exc_info=True)
            if isinstance(e, BlockedError):
                error_type, http_status_code = 'blocked_error', 403
            elif isinstance(e, (NetworkError, TimeoutError)):
                error_type, http_status_code = 'network_error', None
            elif isinstance(e, ParseError):
                error_type, http_status_code = 'parse_error', None
            else:
                error_type, http_status_code = 'unknown_error', None

            db.save_error_history(
                stage='crawl',
                batch_id=batch_id,
                error_type=error_type,
                error_message=str(e),
                http_status_code=http_status_code,
                error_details={'task': 'collect_and_register_urls', 'page_count': page_count}
            )
            raise

        # crawl_jobs 등록
        logger.info(f"📋 Registering {len(urls)} URLs to crawl_jobs (batch_id={batch_id})")
        registered_count = db.register_crawl_jobs(urls, batch_id)
        logger.info(f"✅ {registered_count} URLs registered to crawl_jobs")

        if registered_count == 0:
            next_start = (end_page + 1) if (end_page + 1) <= 2000 else 1
            Variable.set("current_start_page", str(next_start))
            logger.info(f"📌 신규 URL 없음 → 다음 시작 페이지 업데이트: {next_start}")
            raise AirflowSkipException("신규 URL 없음, 이후 태스크 스킵")

        logger.info(f"✅ crawl_jobs 등록 완료: {registered_count}개")
        return {
            'batch_num': batch_num,
            'batch_id': batch_id,
            'url_count': registered_count,
            'end_page': end_page,
        }

    @task(task_id='update_page_variable')
    def update_page_variable(collect_result: Dict[str, Any]) -> None:
        end_page = collect_result['end_page']
        next_start = (end_page + 1) if (end_page + 1) <= 2000 else 1
        Variable.set("current_start_page", str(next_start))
        logger.info(f"📌 다음 크롤링 시작 페이지: {next_start}")

    @task(
        task_id='crawl_details',
        execution_timeout=timedelta(hours=1), # 2시간 초과 시 Task 강제 종료
        retries=2,  # Airflow가 재시도
        retry_delay=timedelta(minutes=5), # 재시도 전 5분 대기
    )
    def crawl_details(collect_result: Dict[str, Any]) -> Dict[str, Any]:
        from pipeline_services import (
            SupabaseService,
            CrawlJobManager,
            SlackService,
        )
        from pipeline_services.async_runner import run_async

        batch_num = collect_result['batch_num']
        batch_id = collect_result['batch_id']

        logger.info(f"🚀 Starting detail crawling for batch {batch_num} (batch_id={batch_id})")

        db = SupabaseService()
        start_time = datetime.now()

        job_manager = CrawlJobManager(db)

        result = run_async(job_manager.process_crawl_jobs(
            batch_id=batch_id,
            batch_num=batch_num,
        ))

        duration = (datetime.now() - start_time).total_seconds()

        # 실패 검증: 최소 성공률 80% 미만이면 Task 실패
        total_jobs = result['success_count'] + result['failed_count']
        min_success_rate = 0.8

        if total_jobs > 0:
            success_rate = result['success_count'] / total_jobs

            if success_rate < min_success_rate:
                error_msg = (
                    f"❌ Success rate too low: {success_rate:.1%} < {min_success_rate:.1%} "
                    f"(success={result['success_count']}, failed={result['failed_count']}). "
                    f"Task marked as FAILED."
                )
                logger.error(error_msg)

                slack = SlackService()
                slack.check_and_send_alert(
                    stage='crawl',
                    success_rate=success_rate,
                    success_count=result['success_count'],
                    failed_count=result['failed_count'],
                    batch_num=batch_num,
                    error_message=None
                )

                raise Exception(error_msg)

        logger.info(
            f"✅ Task 2 completed: "
            f"success={result['success_count']}, "
            f"failed={result['failed_count']}, "
            f"duration={duration:.1f}s"
        )

        return {
            'batch_num': batch_num,
            'batch_id': batch_id,
            'success_count': result['success_count'],
            'failed_count': result['failed_count'],
            'duration': duration
        }

    @task(
        task_id='submit_gpt_batch',
        execution_timeout=timedelta(minutes=30),
    )
    def submit_gpt_batch(crawl_result: Dict[str, Any]) -> Dict[str, Any]:
        """GPT Batch API 제출"""
        from airflow.operators.python import get_current_context
        from pipeline_services import SupabaseService, OpenAIService
        from pipeline_services.exceptions import BillingLimitError

        batch_num = crawl_result['batch_num']
        batch_id = crawl_result['batch_id']
        ti = get_current_context()['ti']

        logger.info(f"🚀 Submitting GPT Batch for batch {batch_num}")

        try:
            # DB 연결
            db = SupabaseService()

            # 이전 시도에서 OpenAI 배치는 만들었는데 DB 저장만 실패한 경우 → DB 저장만 재시도
            if ti.try_number > 1:
                openai_batch_result = ti.xcom_pull(key='openai_batch_result')
                if openai_batch_result and openai_batch_result.get('batch_id'):
                    logger.info("🔄 Retry: reusing existing OpenAI batch, retrying DB insert only")
                    result = db.create_batch_metadata_sync(
                        batch_num=batch_num,
                        batch_id=batch_id,
                        stage='gpt',
                        openai_batch_id=openai_batch_result['batch_id'],
                        item_count=openai_batch_result['item_count'],
                        file_id=openai_batch_result.get('file_id'),
                        metadata=openai_batch_result.get('metadata', {}),
                    )
                    if not result:
                        raise Exception(
                            f"Failed to save processing_job for batch_num={batch_num} (DB insert failed on retry)"
                        )
                    logger.info(f"✅ Task 3 completed (retry): batch_id={openai_batch_result['batch_id']}")
                    return {
                        'batch_num': batch_num,
                        'batch_id': openai_batch_result['batch_id'],
                        'item_count': openai_batch_result['item_count'],
                    }

            # 리뷰 데이터 조회
            reviews = db.get_reviews_for_gpt(batch_num, batch_id)

            if not reviews:
                logger.warning(f"⚠️ No reviews found for batch {batch_num}")
                raise AirflowSkipException(
                    f"No reviews found for GPT batch submission: batch_num={batch_num}"
                )

            logger.info(f"📋 {len(reviews)} reviews to process")

            openai = OpenAIService()
            batch_requests = openai.build_batch_requests(reviews) # 개별 리뷰들을 하나의 Batch API 요청으로 변환
            file_id = openai.upload_batch_file(batch_requests, batch_num) # 데이터 파일을 서버에 올려둠
            openai_batch_id = openai.create_batch_job(file_id) # 올려둔 파일로 처리 작업을 시작함

            if not openai_batch_id:
                raise Exception(f"Failed to create batch job for batch {batch_num}")

            metadata_payload = {
                'crawl_completed_at': datetime.now().isoformat(),
                'success_count': crawl_result['success_count'],
                'failed_count': crawl_result['failed_count'],
                'duration': crawl_result['duration'],
            }
            # 재시도 시 OpenAI 중복 생성 방지: DB 저장 전에 XCom에 저장
            ti.xcom_push(
                key='openai_batch_result',
                value={
                    'batch_id': batch_id,
                    'openai_batch_id' : openai_batch_id,
                    'file_id': file_id,
                    'item_count': len(reviews),
                    'metadata': metadata_payload,
                },
            )

            # processing_jobs 테이블에 저장 (실패 시 예외로 재시도 유도)
            result = db.create_batch_metadata_sync(
                batch_num=batch_num,
                stage='gpt',
                batch_id=batch_id,
                openai_batch_id=openai_batch_id,
                item_count=len(reviews),
                file_id=file_id,
                metadata=metadata_payload,
            )
            if not result:
                raise Exception(
                    f"Failed to save processing_job for batch_num={batch_num} (DB insert failed). "
                    "Task will retry without creating a duplicate OpenAI batch."
                )

            logger.info(
                f"✅ Task completed: "
                f"batch_id={batch_id}, "
                f"items={len(reviews)}"
            )

            return {
                'batch_num': batch_num,
                'batch_id': batch_id,
                'item_count': len(reviews)
            }

        except BillingLimitError as e:
            logger.error(f"⛔ OpenAI 결제 한도 도달 - 재시도 없이 스킵: {e}")
            raise AirflowSkipException(f"Billing limit reached: {e}")
        
    # crawl_details: branch 합류 지점. 내부에서 XCom으로 결과를 직접 pull
    @task(
        task_id='merge_collect_result',
        trigger_rule=TriggerRule.NONE_FAILED_MIN_ONE_SUCCESS,
    )
    def merge_collect_result() -> Dict[str, Any]:
        from airflow.operators.python import get_current_context
        context = get_current_context()
        ti = context['ti']
        result = (
            ti.xcom_pull(task_ids='resume_pending_batch')
            or ti.xcom_pull(task_ids='collect_and_register_urls')
        )
        return result

    from airflow.utils.trigger_rule import TriggerRule

    """
    branch
    ├── resumed ────────────────────────────────────┐
    └─► batch_created ─► collected ─► page_updated ─┤
                                                    └──► merged ─► crawl_details ─► 
    """

    # Task 인스턴스 생성
    branch = check_pending_batch()

    resumed = resume_pending_batch()
    batch_created = create_batch()
    collected = collect_and_register_urls(batch_created)
    page_updated = update_page_variable(collected)

    merged = merge_collect_result()
    crawl_result = crawl_details(merged)
    gpt_result = submit_gpt_batch(crawl_result)

    # branch → 두 갈래
    branch >> [resumed, batch_created]
    batch_created >> collected >> page_updated
    [resumed, page_updated] >> merged 

    # DAG 2 자동 트리거 (conf로 batch 정보 전달; run_id는 Airflow가 자동 생성)
    trigger_dag2 = TriggerDagRunOperator(
        task_id='trigger_summary_dag',
        trigger_dag_id='2_summary_dag',
        conf={
            'batch_id': '{{ ti.xcom_pull(task_ids="merge_collect_result")["batch_id"] }}',
            'openai_batch_id': '{{ ti.xcom_pull(task_ids="submit_gpt_batch")["batch_id"] }}',
            'batch_num': '{{ ti.xcom_pull(task_ids="submit_gpt_batch")["batch_num"] }}',
        },
        wait_for_completion=False,
    )

    gpt_result >> trigger_dag2


# DAG 인스턴스 생성
dag_instance = crawl_dag()

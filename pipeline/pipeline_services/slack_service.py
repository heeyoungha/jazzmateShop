import os
import logging
from typing import Optional, Dict, Any
import requests

logger = logging.getLogger(__name__)


class SlackService:
    """Slack 알림 서비스"""

    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url or os.getenv('SLACK_WEBHOOK')
        
        if not self.webhook_url:
            logger.warning("⚠️ SLACK_WEBHOOK 환경변수가 설정되지 않았습니다. Slack 알림이 전송되지 않습니다.")

    def send_alert(
        self,
        stage: str,
        batch_num: Optional[int] = None,
        batch_id: Optional[str] = None,
        failure_rate: float = 0.0,
        success_count: int = 0,
        failed_count: int = 0,
        total_count: int = 0,
        is_critical: bool = False,
        error_message: Optional[str] = None
    ) -> bool:

        if not self.webhook_url:
            logger.debug("Slack Webhook URL이 없어 알림을 전송하지 않습니다.")
            return False

        try:
            # 단계명 한글화
            stage_names = {
                'crawl': '크롤링',
                'gpt': 'GPT 요약',
                'embedding': '임베딩',
                'vectordb': '벡터 저장'
            }
            stage_name = stage_names.get(stage, stage)

            # 알림 레벨 및 색상
            if is_critical:
                level = "🚨 CRITICAL"
                color = "danger"  # 빨간색
            else:
                level = "⚠️ WARNING"
                color = "warning"  # 노란색

            # 메시지 구성
            failure_rate_pct = failure_rate * 100
            success_rate_pct = (1 - failure_rate) * 100

            # 제목
            title = f"{level}: {stage_name} 단계 실패율 경고"

            # 필드 구성
            fields = [
                {
                    "title": "단계",
                    "value": stage_name,
                    "short": True
                },
                {
                    "title": "실패율",
                    "value": f"{failure_rate_pct:.1f}%",
                    "short": True
                },
                {
                    "title": "성공률",
                    "value": f"{success_rate_pct:.1f}%",
                    "short": True
                },
                {
                    "title": "통계",
                    "value": f"성공: {success_count}건 / 실패: {failed_count}건 / 전체: {total_count}건",
                    "short": True
                }
            ]

            if batch_num:
                fields.append({
                    "title": "배치 번호",
                    "value": str(batch_num),
                    "short": True
                })

            if batch_id:
                fields.append({
                    "title": "배치 ID",
                    "value": batch_id[:50] + "..." if len(batch_id) > 50 else batch_id,
                    "short": True
                })

            if error_message:
                fields.append({
                    "title": "에러 메시지",
                    "value": error_message[:500],  # 최대 500자
                    "short": False
                })

            # Slack 메시지 페이로드
            payload = {
                "attachments": [
                    {
                        "color": color,
                        "title": title,
                        "fields": fields,
                        "footer": "Jazz Pipeline Monitor",
                        "ts": int(__import__('time').time())
                    }
                ]
            }

            # HTTP 요청
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=10
            )

            if response.status_code == 200:
                logger.info(f"✅ Slack 알림 전송 성공: {stage_name} (실패율: {failure_rate_pct:.1f}%)")
                return True
            else:
                logger.error(f"❌ Slack 알림 전송 실패: HTTP {response.status_code} - {response.text}")
                return False

        except Exception as e:
            logger.error(f"❌ Slack 알림 전송 중 오류 발생: {e}", exc_info=True)
            return False

    def check_and_send_alert(
        self,
        stage: str,
        success_rate: float,
        success_count: int,
        failed_count: int,
        batch_num: Optional[int] = None,
        batch_id: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> bool:
        
        total_count = success_count + failed_count
        
        if total_count == 0:
            return False

        failure_rate = 1 - success_rate

        # 50% 이상 실패 → Critical 알림
        if failure_rate >= 0.5:
            return self.send_alert(
                stage=stage,
                batch_num=batch_num,
                batch_id=batch_id,
                failure_rate=failure_rate,
                success_count=success_count,
                failed_count=failed_count,
                total_count=total_count,
                is_critical=True,
                error_message=error_message
            )
        # 20% 이상 실패 (성공률 80% 미달) → 경고 알림
        elif failure_rate >= 0.2:
            return self.send_alert(
                stage=stage,
                batch_num=batch_num,
                batch_id=batch_id,
                failure_rate=failure_rate,
                success_count=success_count,
                failed_count=failed_count,
                total_count=total_count,
                is_critical=False,
                error_message=error_message
            )

        return False
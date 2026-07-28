# Playwright Cloudflare 봇 탐지 트러블슈팅

## 증상

Airflow DAG1(`collect_and_register_urls`) 실행 시 page 1은 성공하지만 page 2부터 실패.

```
페이지 1에서 16개 링크 추출 (누적: 16개)
페이지 2 goto 실패: Page.goto: net::ERR_FAILED at https://www.allaboutjazz.com/reviews/?pg=2
```

---

## 원인: headless 모드에서의 TLS fingerprint 차이

Cloudflare Bot Management는 HTTP 헤더뿐만 아니라 **TLS Client Hello 패킷**의 cipher suite 순서, extension 목록 등을 분석해 봇 여부를 판단한다(JA3 fingerprint).

| 클라이언트 | TLS fingerprint | Cloudflare 반응 |
|---|---|---|
| 실제 Chrome 브라우저 | 정상 Chrome fingerprint | 통과 |
| `headless=True` Playwright | 미묘하게 다른 fingerprint | 403 / ERR_FAILED |
| `headless=False` + Xvfb | 실제 Chrome과 동일한 fingerprint | 통과 |

## 해결

`.env`에서 `CRAWLER_HEADLESS=false` 설정, Docker 워커에 Xvfb 가상 디스플레이 구성.

```bash
# .env
CRAWLER_HEADLESS=false
```

```bash
# scripts/entrypoint-xvfb.sh (Airflow 워커 entrypoint)
rm -f /tmp/.X99-lock  # 재시작 시 남은 lock 파일 제거
Xvfb :99 -screen 0 1280x720x24 &
export DISPLAY=:99
exec /entrypoint "$@"
```

---

## 재발 방지

- Xvfb 재시작 시 `/tmp/.X99-lock` 파일이 남으면 Xvfb가 시작되지 않는다. `entrypoint-xvfb.sh`에 `rm -f /tmp/.X99-lock` 추가로 해결.
- Cloudflare 사이트 크롤링은 반드시 `headless=False` + Xvfb 조합을 사용한다.

#!/bin/bash
# Xvfb(가상 디스플레이)를 백그라운드로 시작한 뒤 Airflow worker를 실행한다.
# Playwright Headful 모드 지원을 위해 필요하다.

# 이전 실행에서 남은 lock 파일 제거 (재시작 시 Xvfb 시작 실패 방지)
rm -f /tmp/.X99-lock

Xvfb :99 -screen 0 1280x720x24 &
XVFB_PID=$!

cleanup() {
  kill $XVFB_PID 2>/dev/null
}
trap cleanup EXIT

exec /entrypoint "$@"

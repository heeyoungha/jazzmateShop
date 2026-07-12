import asyncio
import concurrent.futures


def run_async(coro):
    """
    Celery/Airflow Worker 환경에서 안전하게 코루틴 실행.

    asyncio.run()을 항상 새 스레드에서 실행하므로Worker의 이벤트 루프 상태와 완전히 독립된다.
    """
    # 스레드를 1개 생성 후 코루틴(asyncio.run(coro)) 실행
    # .result()로 메인 스레드가 결과를 기다렸다가 반환
    # with를 사용해서 블록이 끝나면 executor.shutdown()이 자동 호출(스레드 풀 정리)
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        # 이벤트 루프 생성 후 coro 실행(코루틴을 스레드 풀에 제출)하고 결과를 반환
        # submit(fn, *args)의 의미: 새 스레드에서 fn(*args)를 실행하라
        return pool.submit(asyncio.run, coro).result()

"""
# asyncio.run()의 내부 동작 (단순화)                                                                                             
def run(coro):                                                                                                                   
    loop = asyncio.new_event_loop()      # 1. 이벤트 루프 생성                                                                 
    asyncio.set_event_loop(loop)                                                                                                 
    try:                                                                                                                       
        return loop.run_until_complete(coro)  # 2. coro 실행 + 3. 결과 반환
    finally:
        loop.close()                      # 4. 이벤트 루프 종료
"""
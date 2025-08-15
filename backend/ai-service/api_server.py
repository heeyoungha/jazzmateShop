from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import os
import sys
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# 현재 디렉토리를 Python 경로에 추가
sys.path.append('/app')

app = FastAPI(title="JazzMate AI Recommendation API", version="1.0.0")

# CORS 설정
# CORS 설정
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3001,http://localhost:3000").split(",")
allowed_origins = [origin.strip() for origin in allowed_origins]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "JazzMate AI Recommendation API", "status": "running"}

@app.post("/recommend/by-review")
async def recommend_by_review(request: dict):
    try:
        review_text = request.get("review_text", "")
        review_id = request.get("review_id")
        limit = request.get("limit", 3)
        
        print(f"📝 추천 요청 받음: review_id={review_id}, limit={limit}")
        print(f"📝 감상문 내용: {review_text[:100]}...")
        
        # recommend_by_review.py 스크립트 실행
        import subprocess
        
        cmd = [
            "python3", 
            "/app/recommend_by_review.py",
            "--review-text", review_text,
            "--review-id", str(review_id),
            "--limit", str(limit)
        ]
        
        print(f"🚀 Python 스크립트 실행: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            print(f"✅ 추천 생성 완료: review_id={review_id}")
            print(f"📤 Python 출력: {result.stdout}")
            
            return {
                "success": True,
                "message": f"추천이 성공적으로 생성되었습니다. (review_id: {review_id})",
                "review_id": review_id
            }
        else:
            print(f"❌ 추천 생성 실패: review_id={review_id}")
            print(f"📤 Python 오류: {result.stderr}")
            
            return {
                "success": False,
                "message": f"추천 생성에 실패했습니다: {result.stderr}",
                "review_id": review_id
            }
        
    except Exception as e:
        print(f"❌ 추천 오류: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "recommendations": []
        }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "JazzMate AI Recommendation API"}

if __name__ == "__main__":
    import uvicorn
    print("🚀 JazzMate AI Recommendation API 서버 시작...")
    print("📍 서버 주소: http://localhost:8000")
    print("📚 API 문서: http://localhost:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import asyncio
import os
import sys
from dotenv import load_dotenv
import pandas as pd
import json
from typing import Optional

# 환경 변수 로드
load_dotenv()

# 현재 디렉토리를 Python 경로에 추가
sys.path.append('/app')

# 추천 함수 import
from recommend_by_review import recommend_by_review

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
async def recommend_by_review_endpoint(request: dict):
    """감상문 기반 추천 API 엔드포인트"""
    try:
        review_text = request.get("review_text", "")
        review_id = request.get("review_id")
        limit = request.get("limit", 3)
        
        print(f"📝 추천 요청 받음: review_id={review_id}, limit={limit}")
        print(f"📝 감상문 내용: {review_text[:100]}...")
        
        print(f"🚀 추천 함수 호출 시작: review_id={review_id}")
        
        # 비동기 함수 직접 호출
        result = await recommend_by_review(
            review_text=review_text,
            review_id=review_id,
            limit=limit
        )
        
        if result.get("success"):
            print(f"✅ 추천 처리 완료: review_id={review_id}, 추천 개수={result.get('count', 0)}")
            return result
        else:
            print(f"❌ 추천 처리 실패: review_id={review_id}, 오류={result.get('error', 'Unknown')}")
            return result
        
    except Exception as e:
        print(f"❌ 추천 오류: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e),
            "recommendations": []
        }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "JazzMate AI Recommendation API"}

@app.get("/admin/failed-recommendation-reasons")
async def get_failed_recommendation_reasons():
    """추천사유 생성 실패 데이터 조회"""
    try:
        from services.recommendation_reason_service import RecommendationReasonService
        
        reason_service = RecommendationReasonService()
        count = reason_service.get_failed_data_count()
        summary = reason_service.get_failed_data_summary()
        
        return {
            "success": True,
            "count": count,
            "data": summary
        }
    except Exception as e:
        print(f"❌ 실패 데이터 조회 오류: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e),
            "count": 0,
            "data": []
        }

@app.post("/admin/retry-failed-recommendation-reasons")
async def retry_failed_recommendation_reasons(request: dict = None):
    """실패한 추천사유 생성 재시도"""
    try:
        from services.recommendation_reason_service import RecommendationReasonService
        
        max_retries = request.get("max_retries", 3) if request else 3
        
        reason_service = RecommendationReasonService()
        results = await reason_service.retry_failed_reason_generation(max_retries=max_retries)
        
        return {
            "success": True,
            "results": results,
            "message": f"재시도 완료: 성공 {results['success']}개, 실패 {results['failed']}개, 건너뜀 {results['skipped']}개"
        }
    except Exception as e:
        print(f"❌ 재시도 오류: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e)
        }

@app.get("/admin/data-quality")
async def get_data_quality():
    """데이터 품질 히스토리 및 현재 상태 조회"""
    try:
        csv_file = '/app/data_quality_history.csv'
        
        # CSV 파일이 없으면 빈 응답
        if not os.path.exists(csv_file):
            return {
                "success": False,
                "message": "데이터 품질 히스토리 파일이 없습니다.",
                "data": None
            }
        
        # CSV 파일 읽기
        df = pd.read_csv(csv_file)
        
        # datetime으로 변환
        df['datetime'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('datetime')
        
        # 최신 분석 결과 (마지막 행)
        latest_row = df.iloc[-1]
        
        # 전체 시계열 데이터 추출
        timeseries_data = {
            "dates": df['datetime'].dt.strftime('%Y-%m-%d %H:%M').tolist(),
            "overall_quality": df['overall_quality'].tolist(),
            "total_records": df['total_records'].tolist(),
            "total_fields": df['total_fields'].tolist() if 'total_fields' in df.columns else []
        }
        
        # 필드별 완성도 데이터 추출
        completeness_fields = [col for col in df.columns if col.endswith('_completeness')]
        field_completeness = {}
        
        for col in completeness_fields:
            field_name = col.replace('_completeness', '')
            # 메타데이터 필드 제외
            if field_name not in ['date', 'timestamp']:
                field_completeness[field_name] = {
                    "history": df[col].tolist(),
                    "latest": float(latest_row[col]),
                    "missing_pct": float(latest_row.get(f'{field_name}_missing_pct', 0))
                }
        
        # 최신 분석 결과 요약
        latest_summary = {
            "date": latest_row['date'],
            "timestamp": latest_row['timestamp'],
            "overall_quality": float(latest_row['overall_quality']),
            "total_records": int(latest_row['total_records']),
            "total_fields": int(latest_row.get('total_fields', 0)),
            "field_completeness": {field: data["latest"] for field, data in field_completeness.items()}
        }
        
        return {
            "success": True,
            "data": {
                "latest": latest_summary,
                "timeseries": timeseries_data,
                "field_completeness": field_completeness
            }
        }
        
    except Exception as e:
        print(f"❌ 데이터 품질 조회 오류: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e),
            "data": None
        }

@app.get("/admin/data-quality/heatmap-image")
async def get_heatmap_image():
    """히트맵 PNG 이미지 제공"""
    try:
        # 히트맵 이미지 파일 경로
        heatmap_path = '/app/data_quality_heatmap.png'
        
        # 이미지가 없으면 생성 시도
        if not os.path.exists(heatmap_path):
            from data_quality_visualizer import DataQualityVisualizer
            
            visualizer = DataQualityVisualizer()
            visualizer.load_data_from_db()
            
            if visualizer.df is None or visualizer.df.empty:
                raise HTTPException(status_code=404, detail="데이터를 로드할 수 없습니다.")
            
            visualizer.analyze_missing_data()
            visualizer.create_missing_data_heatmap()
        
        # 이미지 파일이 존재하면 반환
        if os.path.exists(heatmap_path):
            return FileResponse(
                heatmap_path,
                media_type='image/png',
                filename='data_quality_heatmap.png'
            )
        else:
            raise HTTPException(status_code=404, detail="히트맵 이미지를 생성할 수 없습니다.")
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 히트맵 이미지 조회 오류: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/admin/data-quality/current")
async def get_current_data_quality():
    """현재 데이터베이스의 실시간 데이터 품질 분석"""
    try:
        from data_quality_visualizer import DataQualityVisualizer
        
        visualizer = DataQualityVisualizer()
        visualizer.load_data_from_db()
        
        if visualizer.df is None or visualizer.df.empty:
            return {
                "success": False,
                "message": "데이터를 로드할 수 없습니다.",
                "data": None
            }
        
        # 누락 데이터 분석
        analysis_results = visualizer.analyze_missing_data()
        
        if analysis_results is None:
            return {
                "success": False,
                "message": "분석을 수행할 수 없습니다.",
                "data": None
            }
        
        # 필드별 완성도 데이터
        field_stats = []
        for col in visualizer.df.columns:
            completeness = analysis_results['completeness'][col]
            missing_pct = analysis_results['missing_pct'][col]
            missing_count = analysis_results['missing_stats'][col]
            
            field_stats.append({
                "field": col,
                "completeness": float(completeness),
                "missing_pct": float(missing_pct),
                "missing_count": int(missing_count),
                "total_records": int(analysis_results['total_records'])
            })
        
        # 히트맵 데이터 생성 (샘플링하여 성능 개선)
        # 최대 100개 레코드만 표시 (너무 많으면 성능 문제)
        max_records_for_heatmap = 100
        df_sample = visualizer.df.sample(min(max_records_for_heatmap, len(visualizer.df)))
        
        # 누락 데이터 마스크 생성
        missing_mask = df_sample.isnull().copy()
        for col in df_sample.columns:
            if df_sample[col].dtype == 'object':
                col_str = df_sample[col].astype(str)
                meaningless_mask = (
                    (df_sample[col] == '') |
                    (col_str.str.strip() == '') |
                    (col_str == 'nan') |
                    (col_str.str.lower() == 'null') |
                    (col_str.str.strip() == '{}')
                )
                missing_mask[col] = missing_mask[col] | meaningless_mask
        
        # 히트맵 데이터 생성 (누락=1, 존재=0)
        heatmap_data = []
        field_list = df_sample.columns.tolist()
        
        for idx, (orig_idx, row) in enumerate(missing_mask.iterrows()):
            record_data = []
            for field in field_list:
                # 0=존재, 1=누락
                record_data.append(int(row[field]))
            heatmap_data.append({
                "name": f"Record {idx + 1}",
                "data": record_data
            })
        
        # 품질 등급 결정
        overall_quality = analysis_results['overall_quality']
        if overall_quality >= 90:
            quality_grade = "excellent"
        elif overall_quality >= 70:
            quality_grade = "good"
        elif overall_quality >= 50:
            quality_grade = "poor"
        else:
            quality_grade = "critical"
        
        return {
            "success": True,
            "data": {
                "overall_quality": float(overall_quality),
                "quality_grade": quality_grade,
                "total_records": int(analysis_results['total_records']),
                "total_fields": int(analysis_results['total_fields']),
                "fields": field_stats,
                "heatmap": {
                    "fields": field_list,
                    "data": heatmap_data,
                    "sample_size": len(df_sample),
                    "total_records": len(visualizer.df)
                }
            }
        }
        
    except Exception as e:
        print(f"❌ 실시간 데이터 품질 분석 오류: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e),
            "data": None
        }

if __name__ == "__main__":
    import uvicorn
    print("🚀 JazzMate AI Recommendation API 서버 시작...")
    print("📍 서버 주소: http://localhost:8000")
    print("📚 API 문서: http://localhost:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)

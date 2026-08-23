"""
Jazz Reviews DB 데이터 품질 분석 및 시각화 도구
누락된 데이터 필드를 시각화하여 보충이 필요한 부분을 파악
"""

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
import seaborn as sns
import numpy as np
from supabase import create_client
import os
from dotenv import load_dotenv
from datetime import datetime
# 한글 폰트 설정

plt.rcParams['font.family'] = 'AppleGothic'
plt.rcParams['axes.unicode_minus'] = False

# ── 설정 상수 ────────────────────────────────────────────
# 대상 테이블
TABLE_NAME = 'allthatjazz_raw'

# 출력 파일명
HEATMAP_FILE = 'data_quality_heatmap.png'
TIMESERIES_FILE = 'data_quality_timeseries.png'
HISTORY_CSV = 'data_quality_history.csv'
INGESTION_FILE = 'ingestion_timeline.png'  # 적재 이력(파이프라인 처리) 시각화

# 적재 이력 통합 VIEW (011 마이그레이션에서 생성) — 처리 이력 축, 내용 품질 축과 별개
INGESTION_VIEW = 'ingestion_timeline'

# 파이프라인 v1→v2 경계
PIPELINE_V2_START = '2026-02'

# 완성도(completeness) 등급 임계값 — 높을수록 좋음, "이상(>=)"으로 판정
#   completeness = 100 - missing_pct 이므로 누락률 임계값과 짝을 이룬다
COMPLETENESS_EXCELLENT = 90   # 90% 이상: 우수
COMPLETENESS_GOOD = 70        # 70% 이상: 보통/양호
COMPLETENESS_POOR = 50        # 50% 이상: 개선필요 (미만은 심각)
COMPLETENESS_TOP = 95         # 95% 이상: 최상위(권장사항용)

# 누락률(missing_pct) 우선순위 임계값 — 낮을수록 좋음, "초과(>)"로 판정
MISSING_CRITICAL = 50   # 50% 초과: 즉시 보충
MISSING_HIGH = 20       # 20% 초과: 우선 보충
MISSING_MEDIUM = 10     # 10% 초과: 점진적 개선
# ─────────────────────────────────────────────────────────

class DataQualityVisualizer:
    def __init__(self):
        """데이터 품질 시각화 도구 초기화"""
        load_dotenv()

        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

        # env 검증: 누락된 변수를 모아 한 번에 알려준다 (설정 왕복 최소화)
        if not supabase_url or not supabase_key:
            missing_vars = []
            if not supabase_url:
                missing_vars.append('SUPABASE_URL')
            if not supabase_key:
                missing_vars.append('SUPABASE_SERVICE_ROLE_KEY')
            raise EnvironmentError(
                f"환경 변수 누락: {', '.join(missing_vars)}. .env 파일을 확인하세요."
            )

        # Supabase 연결
        self.supabase = create_client(supabase_url, supabase_key)

        self.df = None
        self.analysis_results = {}

        print("🔧 데이터 품질 시각화 도구 초기화 완료")
    
    def load_data_from_db(self):
        """Supabase DB에서 데이터 로드"""
        print("📡 Supabase DB에서 데이터 로드 중...")
        
        try:
            # 총 레코드 수 확인
            count_response = self.supabase.table(TABLE_NAME)\
                .select('id', count='exact')\
                .execute()
            
            total_count = count_response.count if hasattr(count_response, 'count') else None
            
            # 총 레코드 수에 따라 batch_size 동적 설정
            # Supabase API 기본 limit: 1000개 (최대값)
            if total_count:
                if total_count <= 100:
                    batch_size = 100  # 작은 데이터셋: 100개씩
                elif total_count <= 1000:
                    batch_size = 500  # 중간 크기: 500개씩
                else:
                    batch_size = 1000  # 큰 데이터셋: Supabase API 최대 limit
                
                estimated_pages = (total_count + batch_size - 1) // batch_size
                print(f"  📊 총 레코드 수: {total_count:,}개")
                print(f"  📦 배치 크기: {batch_size:,}개 (예상 API 호출 횟수: {estimated_pages}회)")
                print(f"  💡 참고: Supabase API 최대 limit는 1000개입니다")
            else:
                batch_size = 1000
                print(f"  📦 배치 크기: {batch_size:,}개 (기본값, Supabase API 최대 limit)")
            
            # 모든 데이터 로드 (페이지네이션 고려)
            all_data = []
            offset = 0
            
            while True:
                print(f"  📦 배치 로드 시작: offset={offset}, limit={batch_size}")
                # range(start, end)는 양끝 포함(inclusive)이라 end는 offset+batch_size-1.
                # limit()+offset() 조합보다 널리 지원되는 페이지네이션 API라 호환성이 낫다.
                # order('id') 필수: PostgREST는 정렬 없이 range/offset을 쓰면 페이지 간
                # row 순서를 보장하지 않는다. 크롤러가 동시에 insert 중이면 페이지 경계에서
                # row가 중복되거나 누락될 수 있어, 안정 정렬 키로 id를 지정한다.
                response = self.supabase.table(TABLE_NAME)\
                    .select('*')\
                    .order('id')\
                    .range(offset, offset + batch_size - 1)\
                    .execute()
                
                if not response.data:
                    print(f"  ⚠️ 응답 데이터 없음, 종료")
                    break
                
                loaded_count = len(response.data)
                all_data.extend(response.data)
                print(f"  📦 {offset + 1}~{offset + loaded_count} 레코드 로드 완료 (실제: {loaded_count}개)")
                
                # 로드된 데이터가 배치 사이즈보다 작으면 마지막 배치
                if loaded_count < batch_size:
                    print(f"  ✅ 마지막 배치 도달 (로드된 개수: {loaded_count} < 배치 사이즈: {batch_size})")
                    break
                
                # 다음 배치로 이동
                offset += batch_size
            
            self.df = pd.DataFrame(all_data)
            print(f"✅ 총 {len(self.df)}개 레코드 로드 완료")

            # 로딩 정합성 검증: "품질 분석(결측률)" 이전에 "입력이 온전한가"를 먼저 확인.
            # total_count(count='exact' 결과)와 대조하고 id 유일성을 점검한다.
            self._verify_load_integrity(total_count)

            return self.df

        except Exception as e:
            print(f"❌ 데이터 로드 실패: {e}")
            return None

    def _verify_load_integrity(self, expected_count):
        """로딩 정합성 검증: 결측률 분모(len(self.df))가 오염됐는지 로드 직후 확인한다."""
        print("\n🔍 데이터 로딩 정합성 검증 중...")
        loaded_count = len(self.df)

        # count 대조: None(검증 불가)/부족(페이지 누락)=중단, 초과(insert/읽기 중복)=경고
        if expected_count is None:
            raise ValueError("DB count를 받지 못해 정합성을 검증할 수 없습니다 (count='exact' 실패 의심)")
        elif loaded_count < expected_count:
            raise ValueError(
                f"페이지 누락 의심: DB {expected_count}개 vs 로드 {loaded_count}개"
            )
        elif loaded_count > expected_count:
            print(f"   ℹ️  로드 중 insert/읽기 중복 추정: DB {expected_count}개 < 로드 {loaded_count}개 (계속 진행)")
        else:
            print(f"   ✅ count 일치 ({loaded_count:,}개)")

        # id 유일성 체크: 페이지 경계에서 같은 행을 두 번 읽으면 결측률 분모가 부풀려진다.
        if 'id' in self.df.columns:
            dup_count = int(self.df['id'].duplicated().sum())
            if dup_count > 0:
                dup_ids = self.df.loc[self.df['id'].duplicated(keep=False), 'id'].unique()
                print(f"   ⚠️  id 중복 {dup_count}건 발견 → 페이지네이션 순서 불안정 의심")
                print(f"      중복 id 샘플: {list(dup_ids[:5])}")

                # id는 PK라 DB엔 하나뿐 → 이 중복은 "읽기 중복"이므로 버려도 안전하다.
                before = len(self.df)
                self.df = self.df.drop_duplicates('id').reset_index(drop=True)
                removed = before - len(self.df)
                print(f"   🧹 중복 {removed}건 제거 후 진행 (남은 레코드: {len(self.df):,}개)")
            else:
                print(f"   ✅ id 중복 없음 (unique: {self.df['id'].nunique():,}개)")
        else:
            print("   ℹ️  id 컬럼이 없어 유일성 검증을 건너뜁니다.")

    def _missing_mask(self, series):
        """한 컬럼(Series)에 대해 '결측으로 간주할 값'의 불리언 마스크 반환."""
        # None/NaN 여부에서 출발 (값마다 True/False)
        mask = series.isnull()

        # 문자열 컬럼일 때만 문자열 기반 결측 기준을 OR로 누적.
        # object / str(StringDtype) 양쪽을 모두 잡아야 pandas 버전에 무관하게 동작한다.
        if pd.api.types.is_object_dtype(series) or pd.api.types.is_string_dtype(series):
            col_str = series.astype(str)
            stripped = col_str.str.strip()
            mask |= (stripped == '')                  # 빈 문자열 + 공백만 있는 문자열
            mask |= (col_str == 'nan')                # 'nan' 문자열
            mask |= (col_str.str.lower() == 'null')   # 'null' 문자열
            mask |= (stripped == '{}')                # 빈 JSON

        return mask

    def analyze_missing_data(self):
        """누락 데이터 분석"""
        if self.df is None:
            print("❌ 데이터가 로드되지 않았습니다.")
            return None
        
        print("\n📊 누락 데이터 분석 시작...")
        
        # 기본 통계
        total_records = len(self.df)
        total_fields = len(self.df.columns)
        
        # album_info 필드 디버깅을 위한 샘플 확인
        if 'album_info' in self.df.columns:
            print("\n🔍 album_info 필드 샘플 데이터 확인:")
            non_null_samples = self.df[self.df['album_info'].notna()]['album_info'].head(5)
            print(f"   Null이 아닌 샘플 수: {len(non_null_samples)}")
            for idx, val in non_null_samples.items():
                print(f"   샘플 {idx}: {str(val)[:100]}...")
            
            # 빈 JSON 객체나 의미없는 값 확인
            print(f"\n   album_info 상세 분석:")
            print(f"   - 전체 레코드: {len(self.df)}")
            print(f"   - Null 값: {self.df['album_info'].isnull().sum()}")
            print(f"   - 빈 문자열: {(self.df['album_info'] == '').sum()}")
            
            # 문자열로 변환해서 분석
            album_info_str = self.df['album_info'].astype(str)
            print(f"   - 'nan' 문자열: {(album_info_str == 'nan').sum()}")
            print(f"   - 'null' 문자열: {(album_info_str.str.lower() == 'null').sum()}")
            print(f"   - 빈 JSON '{{}}': {(album_info_str.str.strip() == '{}').sum()}")
            print(f"   - 공백만 있는 값: {(album_info_str.str.strip() == '').sum()}")
            
            # 유효한 데이터가 있는지 확인
            valid_data = album_info_str[
                (album_info_str != 'nan') & 
                (album_info_str.str.strip() != '') & 
                (album_info_str.str.strip() != '{}') &
                (album_info_str.str.lower() != 'null')
            ]
            print(f"   - 유효한 데이터로 보이는 레코드: {len(valid_data)}")
            if len(valid_data) > 0:
                print(f"   - 유효한 데이터 샘플: {valid_data.iloc[0][:100]}...")
        
        # 누락 데이터 계산 — 값마다 결측 여부를 마스크로 판정 후 개수 집계.
        missing_stats = {
            col: self._missing_mask(self.df[col]).sum()
            for col in self.df.columns
        }
        missing_stats = pd.Series(missing_stats)
        missing_pct = (missing_stats / total_records) * 100
        
        # 완성도 계산
        completeness = 100 - missing_pct
        
        # 결과 저장
        self.analysis_results = {
            'total_records': total_records,
            'total_fields': total_fields,
            'missing_stats': missing_stats,
            'missing_pct': missing_pct,
            'completeness': completeness,
            'overall_quality': completeness.mean()
        }
        
        # 콘솔 출력
        print(f"📊 전체 통계:")
        print(f"   총 레코드 수: {total_records:,}개")
        print(f"   총 필드 수: {total_fields}개")
        print(f"   전체 데이터 포인트: {total_records * total_fields:,}개")
        print(f"   전체 데이터 품질: {completeness.mean():.1f}%")
        
        print(f"\n📈 필드별 상세 분석:")
        for col in self.df.columns:
            missing_count = missing_stats[col]
            missing_percent = missing_pct[col]
            completeness_pct = completeness[col]
            
            # 품질 등급 결정
            if completeness_pct >= COMPLETENESS_EXCELLENT:
                quality_grade = "🟢 우수"
            elif completeness_pct >= COMPLETENESS_GOOD:
                quality_grade = "🟡 보통"
            elif completeness_pct >= COMPLETENESS_POOR:
                quality_grade = "🟠 개선필요"
            else:
                quality_grade = "🔴 심각"
            
            print(f"   {col:25} | {missing_count:5}개 누락 ({missing_percent:5.1f}%) | {completeness_pct:5.1f}% 완성 | {quality_grade}")
        
        return self.analysis_results
    
    def create_missing_data_heatmap(self):
        """누락 데이터 히트맵 생성"""
        if self.df is None:
            print("❌ 데이터가 로드되지 않았습니다.")
            return
        
        print("🔥 누락 데이터 히트맵 생성 중...")
        
        plt.figure(figsize=(15, 10))
        
        # 서브플롯 1: 누락 데이터 히트맵
        plt.subplot(2, 2, 1)
        
        # 누락 데이터 마스크 생성 
        missing_mask = pd.DataFrame({
            col: self._missing_mask(self.df[col])
            for col in self.df.columns
        })

        # 이진 데이터에 적합한 컬러맵 사용 (노란색=누락, 보라색=존재)
        colors = ['#8B00FF', '#FFFF00']  # 보라색(존재=0), 노란색(누락=1)
        cmap = ListedColormap(colors)
        
        # 히트맵 생성 (누락=1, 존재=0으로 변환)
        heatmap_data = missing_mask.astype(int)
        
        sns.heatmap(
            heatmap_data,
            cbar=True, 
            yticklabels=False,
            cmap=cmap,
            vmin=0,
            vmax=1,
            cbar_kws={'label': 'Missing Data (0=Present, 1=Missing)', 'ticks': [0, 1]}
        )
        plt.title('Missing Data Heatmap\n(Yellow = Missing, Purple = Present)', fontsize=12, fontweight='bold')
        plt.xlabel('Data Fields')
        plt.ylabel('Records')
        
        # 서브플롯 2: 필드별 누락 비율
        plt.subplot(2, 2, 2)
        missing_pct = self.analysis_results['missing_pct']
        bars = plt.bar(range(len(missing_pct)), missing_pct.values, color='coral', alpha=0.7)
        plt.title('Missing Data Percentage by Field', fontsize=12, fontweight='bold')
        plt.xlabel('Fields')
        plt.ylabel('Missing Percentage (%)')
        plt.xticks(range(len(missing_pct)), missing_pct.index, rotation=45, ha='right')
        
        # 색상으로 심각도 표시
        for bar, pct in zip(bars, missing_pct.values):
            if pct > MISSING_CRITICAL:
                bar.set_color('red')
            elif pct > MISSING_HIGH:
                bar.set_color('orange')
            elif pct > MISSING_MEDIUM:
                bar.set_color('yellow')
            else:
                bar.set_color('green')
        
        # 서브플롯 3: 데이터 완성도
        plt.subplot(2, 2, 3)
        completeness = self.analysis_results['completeness']
        bars = plt.bar(range(len(completeness)), completeness.values, color='lightgreen', alpha=0.7)
        plt.title('Data Completeness by Field', fontsize=12, fontweight='bold')
        plt.xlabel('Fields')
        plt.ylabel('Completeness (%)')
        plt.xticks(range(len(completeness)), completeness.index, rotation=45, ha='right')
        plt.ylim(0, 100)
        
        # 90% 이상은 초록색, 70% 이상은 노란색, 그 외는 빨간색
        for bar, pct in zip(bars, completeness.values):
            if pct >= COMPLETENESS_EXCELLENT:
                bar.set_color('green')
            elif pct >= COMPLETENESS_GOOD:
                bar.set_color('orange')
            else:
                bar.set_color('red')
        
        # 서브플롯 4: 전체 데이터 품질 점수
        plt.subplot(2, 2, 4)
        overall_quality = self.analysis_results['overall_quality']
        
        # 품질 등급별 색상
        if overall_quality >= COMPLETENESS_EXCELLENT:
            color = 'green'
            grade = 'Excellent'
        elif overall_quality >= COMPLETENESS_GOOD:
            color = 'orange'
            grade = 'Good'
        elif overall_quality >= COMPLETENESS_POOR:
            color = 'red'
            grade = 'Poor'
        else:
            color = 'darkred'
            grade = 'Critical'
        
        plt.bar(['Overall Quality'], [overall_quality], color=color, alpha=0.7)
        plt.title(f'Overall Data Quality: {overall_quality:.1f}%\nGrade: {grade}', 
                 fontsize=12, fontweight='bold')
        plt.ylabel('Quality Score (%)')
        plt.ylim(0, 100)
        
        # 품질 등급 텍스트 추가
        plt.text(0, overall_quality + 2, f'{grade}', ha='center', fontweight='bold', fontsize=10)
        
        plt.tight_layout()
        plt.savefig(HEATMAP_FILE, dpi=300, bbox_inches='tight')

        print(f"✅ 히트맵 저장 완료: {HEATMAP_FILE}")
        plt.show()
    
    def generate_recommendations(self):
        """데이터 보충 권장사항 생성"""
        if not self.analysis_results:
            print("❌ 분석 결과가 없습니다.")
            return
        
        print("\n💡 데이터 보충 권장사항:")
        print("=" * 60)
        
        missing_pct = self.analysis_results['missing_pct']
        completeness = self.analysis_results['completeness']
        
        # 우선순위별 분류
        critical_fields = missing_pct[missing_pct > MISSING_CRITICAL].index.tolist()
        high_priority_fields = missing_pct[(missing_pct > MISSING_HIGH) & (missing_pct <= MISSING_CRITICAL)].index.tolist()
        medium_priority_fields = missing_pct[(missing_pct > MISSING_MEDIUM) & (missing_pct <= MISSING_HIGH)].index.tolist()
        
        if critical_fields:
            print("🔴 CRITICAL (50% 이상 누락) - 즉시 보충 필요:")
            for field in critical_fields:
                pct = missing_pct[field]
                print(f"   • {field}: {pct:.1f}% 누락")
        
        if high_priority_fields:
            print("\n🟠 HIGH PRIORITY (20-50% 누락) - 우선 보충 권장:")
            for field in high_priority_fields:
                pct = missing_pct[field]
                print(f"   • {field}: {pct:.1f}% 누락")
        
        if medium_priority_fields:
            print("\n🟡 MEDIUM PRIORITY (10-20% 누락) - 점진적 개선:")
            for field in medium_priority_fields:
                pct = missing_pct[field]
                print(f"   • {field}: {pct:.1f}% 누락")
        
        # 완성도가 높은 필드들
        excellent_fields = completeness[completeness >= COMPLETENESS_TOP].index.tolist()
        if excellent_fields:
            print(f"\n🟢 EXCELLENT ({COMPLETENESS_TOP}% 이상 완성) - 우수한 데이터 품질:")
            for field in excellent_fields:
                pct = completeness[field]
                print(f"   • {field}: {pct:.1f}% 완성")
        
        # 전체 권장사항
        overall_quality = self.analysis_results['overall_quality']
        print(f"\n📊 전체 데이터 품질: {overall_quality:.1f}%")
        
        if overall_quality >= COMPLETENESS_EXCELLENT:
            print("🎉 데이터 품질이 우수합니다! 추가 보충이 필요하지 않습니다.")
        elif overall_quality >= COMPLETENESS_GOOD:
            print("✅ 데이터 품질이 양호합니다. 일부 필드만 보충하면 됩니다.")
        elif overall_quality >= COMPLETENESS_POOR:
            print("⚠️ 데이터 품질이 보통입니다. 우선순위 필드부터 보충하세요.")
        else:
            print("🚨 데이터 품질이 심각합니다! 전체적인 데이터 수집 개선이 필요합니다.")
    
    def save_analysis_report(self):
        """CSV로 시계열 데이터 저장 (변화 추적 용이)"""
        if not self.analysis_results:
            print("❌ 분석 결과가 없습니다.")
            return
        
        # 현재 시간 정보
        now = datetime.now()
        date_str = now.strftime('%Y-%m-%d')
        
        # CSV로 시계열 데이터 저장
        csv_history_file = HISTORY_CSV
        
        # CSV 행 데이터 생성
        csv_row = {
            'date': date_str,
            'timestamp': now.isoformat(),
            'total_records': int(self.analysis_results['total_records']),
            'total_fields': int(self.analysis_results['total_fields']),
            'overall_quality': float(self.analysis_results['overall_quality'])
        }
        
        # 각 필드별 완성도 추가
        for field in self.df.columns:
            csv_row[f'{field}_completeness'] = float(self.analysis_results['completeness'][field])
            csv_row[f'{field}_missing_pct'] = float(self.analysis_results['missing_pct'][field])
        
        # CSV 파일이 없으면 헤더와 함께 생성, 있으면 추가
        csv_exists = os.path.exists(csv_history_file)
        df_csv = pd.DataFrame([csv_row])
        
        if csv_exists:
            # 기존 CSV 읽기
            df_existing = pd.read_csv(csv_history_file)
            # 새 데이터 추가
            df_combined = pd.concat([df_existing, df_csv], ignore_index=True)
            df_combined.to_csv(csv_history_file, index=False, encoding='utf-8')
        else:
            # 새 CSV 파일 생성
            df_csv.to_csv(csv_history_file, index=False, encoding='utf-8')
        
        print(f"✅ 시계열 히스토리 저장 완료: {csv_history_file}")
        
        # 이전 결과와 비교 (이전 리포트가 있는 경우)
        self.compare_with_previous()
    
    def compare_with_previous(self):
        """이전 분석 결과와 비교하여 개선 정도 표시"""
        history_file = HISTORY_CSV
        
        if not os.path.exists(history_file):
            print("📊 이전 분석 결과가 없어 비교를 건너뜁니다.")
            return
        
        try:
            df_history = pd.read_csv(history_file)
            
            if len(df_history) < 2:
                print("📊 비교할 이전 분석 결과가 없습니다.")
                return
            
            # 최근 2개 분석 결과 비교
            latest = df_history.iloc[-1]
            previous = df_history.iloc[-2]
            
            print("\n📈 데이터 품질 변화 추이:")
            print("=" * 60)
            
            # 전체 품질 비교
            quality_change = latest['overall_quality'] - previous['overall_quality']
            quality_change_str = f"{quality_change:+.2f}%" if quality_change != 0 else "변화 없음"
            quality_symbol = "📈" if quality_change > 0 else "📉" if quality_change < 0 else "➡️"
            print(f"{quality_symbol} 전체 데이터 품질:")
            print(f"   이전: {previous['overall_quality']:.2f}%")
            print(f"   현재: {latest['overall_quality']:.2f}%")
            print(f"   변화: {quality_change_str}")
            
            # 레코드 수 비교
            records_change = latest['total_records'] - previous['total_records']
            if records_change != 0:
                print(f"\n📊 총 레코드 수:")
                print(f"   이전: {previous['total_records']:,}개")
                print(f"   현재: {latest['total_records']:,}개")
                print(f"   변화: {records_change:+,}개")
            
            # 필드별 개선도 확인
            print(f"\n🔍 주요 필드별 개선도:")
            field_columns = [col for col in df_history.columns if col.endswith('_completeness')]
            
            improvements = []
            declines = []
            
            for col in field_columns:
                field_name = col.replace('_completeness', '')
                if field_name in ['date', 'timestamp', 'total_records', 'total_fields', 'overall_quality']:
                    continue
                
                current_val = latest[col]
                previous_val = previous[col]
                change = current_val - previous_val
                
                if abs(change) > 0.01:  # 0.01% 이상 변화가 있는 경우만 표시
                    if change > 0:
                        improvements.append((field_name, change, current_val, previous_val))
                    else:
                        declines.append((field_name, change, current_val, previous_val))
            
            if improvements:
                print("\n   ✅ 개선된 필드:")
                for field_name, change, current, prev in sorted(improvements, key=lambda x: x[1], reverse=True)[:5]:
                    print(f"      • {field_name:20} {prev:6.2f}% → {current:6.2f}% ({change:+.2f}%p)")
            
            if declines:
                print("\n   ⚠️  악화된 필드:")
                for field_name, change, current, prev in sorted(declines, key=lambda x: x[1])[:5]:
                    print(f"      • {field_name:20} {prev:6.2f}% → {current:6.2f}% ({change:+.2f}%p)")
            
            if not improvements and not declines:
                print("   변화 없음")
            
            print("\n" + "=" * 60)
            
        except Exception as e:
            print(f"⚠️  비교 분석 중 오류: {e}")
    
    def visualize_timeseries(self):
        """CSV 히스토리 파일을 기반으로 시계열 시각화"""
        history_file = HISTORY_CSV
        
        if not os.path.exists(history_file):
            print("❌ 시계열 히스토리 파일이 없습니다. 먼저 분석을 실행하세요.")
            return
        
        print("📈 시계열 시각화 생성 중...")
        
        try:
            # CSV 파일 읽기
            df_history = pd.read_csv(history_file)
            
            if len(df_history) < 1:
                print("❌ 시계열 데이터가 없습니다.")
                return
            
            # timestamp를 datetime으로 변환
            df_history['datetime'] = pd.to_datetime(df_history['timestamp'])
            df_history = df_history.sort_values('datetime')

            # v1→v2 파이프라인 재구축 경계. 이 그래프는 v1(2025)과 v2(2026~) 측정이 함께 있어,
            # 경계선을 그으면 "품질 도약(76→92%)이 파이프라인 교체와 맞물린다"를 시각적으로 지목한다.
            # tz 유무가 섞이면 axvline 비교가 깨지므로 관측 시각의 tz에 맞춰 경계값을 만든다.
            v2_line = pd.Timestamp(PIPELINE_V2_START + '-01')
            if getattr(df_history['datetime'].dt, 'tz', None) is not None:
                v2_line = v2_line.tz_localize(df_history['datetime'].dt.tz)

            def _mark_v2(label=True):
                """현재 서브플롯에 v2 경계선을 긋는다 (시간축 서브플롯 전용)."""
                plt.axvline(v2_line, color='#C1443C', linestyle='--', linewidth=1.5, alpha=0.7)
                if label:
                    ymax = plt.ylim()[1]
                    plt.text(v2_line, ymax * 0.95, ' v2 재구축', color='#C1443C',
                             fontsize=9, va='top', ha='left')

            # 전체 품질 추이 그래프
            fig = plt.figure(figsize=(20, 12))

            # 서브플롯 1: 전체 데이터 품질 추이
            plt.subplot(2, 2, 1)
            plt.plot(df_history['datetime'], df_history['overall_quality'],
                    marker='o', linewidth=2, markersize=8, color='#2E86AB')
            plt.title('Overall Data Quality Trend', fontsize=14, fontweight='bold')
            plt.xlabel('Date/Time')
            plt.ylabel('Quality Score (%)')
            plt.ylim(0, 100)
            plt.grid(True, alpha=0.3)
            plt.xticks(rotation=45)
            _mark_v2()

            # 레코드 수 추이
            plt.subplot(2, 2, 2)
            plt.plot(df_history['datetime'], df_history['total_records'],
                    marker='s', linewidth=2, markersize=8, color='#A23B72')
            plt.title('Total Records Trend', fontsize=14, fontweight='bold')
            plt.xlabel('Date/Time')
            plt.ylabel('Number of Records')
            plt.grid(True, alpha=0.3)
            plt.xticks(rotation=45)
            _mark_v2()

            # 필드별 completeness 추이 (100%가 아닌 필드들만)
            completeness_cols = [col for col in df_history.columns if col.endswith('_completeness')]
            
            # 모든 필드 수집 (100%인 필드도 포함)
            all_fields = []
            for col in completeness_cols:
                field_name = col.replace('_completeness', '')
                all_fields.append((field_name, col))
            
            # 필드별 개선도 비교 (모든 필드)
            plt.subplot(2, 1, 2)
            if len(df_history) >= 2:
                first_row = df_history.iloc[0]
                last_row = df_history.iloc[-1]
                
                changes = []
                # 모든 필드의 변화율 계산
                for field_name, col in all_fields:
                    change = last_row[col] - first_row[col]
                    changes.append((field_name, change, first_row[col], last_row[col]))
                
                if changes:
                    # 변화량이 큰 순서로 정렬 (절대값 기준)
                    changes.sort(key=lambda x: abs(x[1]), reverse=True)
                    field_names = [x[0] for x in changes]
                    changes_values = [x[1] for x in changes]
                    first_values = [x[2] for x in changes]
                    last_values = [x[3] for x in changes]
                    
                    x_pos = np.arange(len(field_names))
                    colors = ['green' if c > 0.01 else 'red' if c < -0.01 else 'gray' for c in changes_values]
                    
                    plt.barh(x_pos, changes_values, color=colors, alpha=0.7)
                    plt.yticks(x_pos, field_names, fontsize=9)
                    plt.xlabel('Change in Completeness (%)', fontsize=12)
                    plt.title('All Fields Completeness Change Rate\n(First vs Last Analysis)', fontsize=14, fontweight='bold')
                    plt.axvline(x=0, color='black', linestyle='--', linewidth=0.8)
                    plt.grid(True, alpha=0.3, axis='x')
                    
                    # 값 표시 (모든 필드 표시)
                    for i, (change, first, last) in enumerate(zip(changes_values, first_values, last_values)):
                        plt.text(change, i, f' {first:.1f}%→{last:.1f}%', 
                                va='center', fontsize=7)
                else:
                    plt.text(0.5, 0.5, 'No data available for comparison', 
                            ha='center', va='center', transform=plt.gca().transAxes)
            else:
                plt.text(0.5, 0.5, 'Need at least 2 data points for comparison', 
                        ha='center', va='center', transform=plt.gca().transAxes)
                plt.title('All Fields Completeness Change Rate\n(First vs Last Analysis)', fontsize=14, fontweight='bold')
            
            # 완성도가 100%가 아닌 필드들만 필터링 (통계 요약용)
            fields_to_plot = []
            for col in completeness_cols:
                field_name = col.replace('_completeness', '')
                if field_name not in ['id', 'url', 'personnel', 'created_at']:  # 항상 100%인 필드 제외
                    if df_history[col].min() < 100:  # 한 번이라도 100% 미만인 필드만
                        fields_to_plot.append((field_name, col))
            
            # 통계 요약을 별도 위치에 배치
            fig.text(0.5, 0.02, self._generate_summary_text(df_history, fields_to_plot), 
                    ha='center', fontsize=9, family='monospace',
                    bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
            
            plt.tight_layout()
            plt.subplots_adjust(bottom=0.15)  # 통계 요약 공간 확보
            plt.savefig(TIMESERIES_FILE, dpi=300, bbox_inches='tight')
            plt.close()
            print(f"✅ 시계열 시각화 저장 완료: {TIMESERIES_FILE}")
            
        except Exception as e:
            print(f"❌ 시계열 시각화 생성 중 오류: {e}")
            import traceback
            traceback.print_exc()

    def visualize_ingestion_timeline(self):
        """적재 이력(ingestion_timeline VIEW)을 두 관점으로 시각화한다.

        - 왼쪽 = 단계 전환 깔때기(Funnel): crawl→gpt→embedding으로 몇 %가 살아남나.
          "어느 단계에서 새는가"(병목)를 한눈에. CTO/파이프라인 건강도 관점.
        - 오른쪽 = 월별 누적 적재 추세: 각 단계가 시간에 따라 얼마나 쌓였나.
          "요약이 크롤을 따라오나"를 본다. 기획/데이터 볼륨 관점.

        주의: 여기 수치는 '처리 성공량'이지 '내용 결측률'이 아니다.
        내용 품질은 heatmap/timeseries(=self.df, raw 테이블) 쪽 축으로 별개다.
        """
        print("🚚 적재 이력 시각화 생성 중 (ingestion_timeline VIEW)...")

        try:
            # VIEW를 테이블처럼 조회 (raw 테이블 self.df와 독립 — 관심사 분리)
            resp = self.supabase.table(INGESTION_VIEW).select('*').execute()
            rows = resp.data if hasattr(resp, 'data') else None

            if not rows:
                print("   ℹ️  ingestion_timeline VIEW에 데이터가 없어 건너뜁니다.")
                return

            df = pd.DataFrame(rows)

            # 숫자 컬럼 결측(NULL)은 0으로 — 아직 그 단계에 도달 안 한 배치는 처리량 0.
            for col in ['crawl_success', 'gpt_ok', 'emb_ok']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

            crawl_total = int(df['crawl_success'].sum())
            gpt_total = int(df['gpt_ok'].sum())
            emb_total = int(df['emb_ok'].sum())

            fig, (ax_funnel, ax_trend) = plt.subplots(1, 2, figsize=(20, 8))

            # ── 왼쪽: 단계 전환 깔때기 ──────────────────────────────
            stages = ['crawl', 'gpt(summary)', 'embedding']
            values = [crawl_total, gpt_total, emb_total]
            colors = ['#2E86AB', '#A23B72', '#3B7A57']

            y_pos = np.arange(len(stages))[::-1]  # 위→아래로 crawl→embed
            ax_funnel.barh(y_pos, values, color=colors, alpha=0.85)
            ax_funnel.set_yticks(y_pos)
            ax_funnel.set_yticklabels(stages, fontsize=12)
            ax_funnel.set_xlabel('Records processed', fontsize=12)
            ax_funnel.set_title('Pipeline Stage Funnel\n(how many survive each stage)',
                                fontsize=14, fontweight='bold')
            ax_funnel.grid(True, alpha=0.3, axis='x')

            # 각 막대에 건수 + 직전 단계 대비 전환율 표시 (병목 가독성)
            base = crawl_total if crawl_total else 1
            for i, (yp, val) in enumerate(zip(y_pos, values)):
                pct = f"{100.0 * val / base:.1f}%" if i > 0 else "100%"
                ax_funnel.text(val, yp, f'  {val:,} ({pct})',
                               va='center', fontsize=11, fontweight='bold')

            # ── 오른쪽: 월별 누적 적재 추세 ─────────────────────────
            # to_period가 tz를 버리며 경고를 내므로 tz를 먼저 제거한 뒤 월 단위로 변환
            df['month'] = pd.to_datetime(df['batch_created_at'], errors='coerce', utc=True) \
                            .dt.tz_localize(None).dt.to_period('M').astype(str)
            monthly = df.groupby('month')[['crawl_success', 'gpt_ok', 'emb_ok']] \
                        .sum().sort_index()
            # 누적(cumulative): "총 데이터 자산이 시간에 따라 얼마까지 쌓였나".
            # 월별 신규량은 재적재가 있던 달만 튀어 성장 서사를 흐리므로 단조증가 곡선으로 본다.
            cumulative = monthly.cumsum()

            for col, color, label in [
                ('crawl_success', '#2E86AB', 'crawl'),
                ('gpt_ok', '#A23B72', 'gpt(summary)'),
                ('emb_ok', '#3B7A57', 'embedding'),
            ]:
                ax_trend.plot(cumulative.index, cumulative[col], marker='o',
                              linewidth=2, markersize=7, color=color, label=label)
                ax_trend.fill_between(range(len(cumulative)), cumulative[col],
                                      color=color, alpha=0.08)

            # 이 그래프는 전 구간이 v2(신 파이프라인)다. 경계선은 v1이 함께 보이는
            # CSV 시계열(visualize_timeseries)에 표시하고, 여기선 제목으로 정체만 명시한다.
            ax_trend.set_title('Cumulative Ingestion by Stage — v2 pipeline (2026-02~)',
                               fontsize=14, fontweight='bold')
            ax_trend.set_xlabel('Month')
            ax_trend.set_ylabel('Cumulative records')
            ax_trend.grid(True, alpha=0.3)
            ax_trend.legend(loc='center right')
            for tick in ax_trend.get_xticklabels():
                tick.set_rotation(45)

            plt.tight_layout()
            plt.savefig(INGESTION_FILE, dpi=300, bbox_inches='tight')
            plt.close()
            print(f"✅ 적재 이력 시각화 저장 완료: {INGESTION_FILE}")
            print(f"   깔때기: crawl {crawl_total:,} → gpt {gpt_total:,} → embed {emb_total:,}")

        except Exception as e:
            print(f"❌ 적재 이력 시각화 생성 중 오류: {e}")
            import traceback
            traceback.print_exc()

    def _generate_summary_text(self, df_history, fields_to_plot):
        """통계 요약 텍스트 생성"""
        summary_lines = []
        summary_lines.append("Time Series Analysis Summary")
        summary_lines.append("=" * 50)
        summary_lines.append(f"Analysis Period: {df_history['datetime'].min().strftime('%Y-%m-%d %H:%M')} ~ {df_history['datetime'].max().strftime('%Y-%m-%d %H:%M')}")
        summary_lines.append(f"Total Analysis Count: {len(df_history)}")
        
        if len(df_history) >= 2:
            first_quality = df_history.iloc[0]['overall_quality']
            last_quality = df_history.iloc[-1]['overall_quality']
            quality_change = last_quality - first_quality
            summary_lines.append("")
            summary_lines.append(f"Overall Quality Change: {first_quality:.2f}% -> {last_quality:.2f}% ({quality_change:+.2f}%p)")
            
            # 가장 개선된 필드
            improvements = []
            for field_name, col in fields_to_plot:
                first_val = df_history.iloc[0][col]
                last_val = df_history.iloc[-1][col]
                change = last_val - first_val
                if change > 0.01:  # 0.01% 이상 개선
                    improvements.append((field_name, change))
            
            if improvements:
                improvements.sort(key=lambda x: x[1], reverse=True)
                summary_lines.append("")
                summary_lines.append("Top Improved Fields:")
                for field_name, change in improvements[:5]:
                    summary_lines.append(f"  • {field_name}: +{change:.2f}%p")
        
        return '\n'.join(summary_lines)
    
    def run_full_analysis(self):
        """전체 분석 실행"""
        print("🚀 Jazz Reviews DB 데이터 품질 분석 시작")
        print("=" * 60)
        
        # 1. 데이터 로드
        data = self.load_data_from_db()
        if data is None or data.empty:
            return
        
        # 누락 데이터 분석
        self.analyze_missing_data()
        
        # 히트맵 생성
        self.create_missing_data_heatmap()

        # 권장사항 생성
        self.generate_recommendations()
        
        # 리포트 저장
        self.save_analysis_report()
        
        # 시계열 시각화 생성
        self.visualize_timeseries()

        # 적재 이력(파이프라인 처리 이력) 시각화 — 내용 품질과 별개 축
        self.visualize_ingestion_timeline()

        print("\n🎉 데이터 품질 분석 완료!")
        print("\n📁 생성된 파일:")
        print(f"   • {HEATMAP_FILE} (히트맵)")
        print(f"   • {TIMESERIES_FILE} (시계열 추이)")
        print(f"   • {INGESTION_FILE} (적재 이력: 단계 깔때기 + 월별 추세)")
        print(f"   • {HISTORY_CSV} (시계열 히스토리)")

def main():
    """메인 실행 함수"""
    try:
        visualizer = DataQualityVisualizer()
        visualizer.run_full_analysis()
    except Exception as e:
        print(f"❌ 분석 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

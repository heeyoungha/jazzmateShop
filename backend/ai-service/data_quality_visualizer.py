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
import warnings
from datetime import datetime
# 한글 폰트 설정

plt.rcParams['font.family'] = 'AppleGothic'
plt.rcParams['axes.unicode_minus'] = False

class DataQualityVisualizer:
    def __init__(self):
        """데이터 품질 시각화 도구 초기화"""
        load_dotenv()
        
        # Supabase 연결
        self.supabase = create_client(
            os.getenv('SUPABASE_URL'),
            os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        )
        
        self.df = None
        self.analysis_results = {}
        
        print("🔧 데이터 품질 시각화 도구 초기화 완료")
    
    def load_data_from_db(self):
        """Supabase DB에서 데이터 로드"""
        print("📡 Supabase DB에서 데이터 로드 중...")
        
        try:
            # 총 레코드 수 확인
            count_response = self.supabase.table('critics_review')\
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
                response = self.supabase.table('critics_review')\
                    .select('*')\
                    .limit(batch_size)\
                    .offset(offset)\
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
            
            return self.df
            
        except Exception as e:
            print(f"❌ 데이터 로드 실패: {e}")
            return None
    
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
        
        # 누락 데이터 계산 (None + 빈 문자열 + 공백만 있는 문자열 + 의미없는 값)
        missing_stats = {}
        for col in self.df.columns:
            # None 값
            null_count = self.df[col].isnull().sum()
            
            # 문자열 타입인 경우 더 정확한 체크
            if self.df[col].dtype == 'object':
                col_str = self.df[col].astype(str)
                
                # 빈 문자열
                empty_string_count = (self.df[col] == '').sum()
                
                # 공백만 있는 문자열 (strip 후 빈 문자열)
                whitespace_count = (col_str.str.strip() == '').sum() - empty_string_count
                
                # 의미없는 값들 (nan 문자열, null 문자열, 빈 JSON 등)
                meaningless_values = (
                    (col_str == 'nan').sum() +
                    (col_str.str.lower() == 'null').sum() +
                    (col_str.str.strip() == '{}').sum()
                )
                
                missing_stats[col] = null_count + empty_string_count + whitespace_count + meaningless_values
            else:
                empty_string_count = 0
                whitespace_count = 0
                missing_stats[col] = null_count
        
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
            if completeness_pct >= 90:
                quality_grade = "🟢 우수"
            elif completeness_pct >= 70:
                quality_grade = "🟡 보통"
            elif completeness_pct >= 50:
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
        
        # 누락 데이터 마스크 생성 (개선된 로직 사용)
        missing_mask = self.df.isnull().copy()
        for col in self.df.columns:
            if self.df[col].dtype == 'object':
                col_str = self.df[col].astype(str)
                # 빈 문자열, 공백만 있는 문자열, 의미없는 값 모두 체크
                meaningless_mask = (
                    (self.df[col] == '') |
                    (col_str.str.strip() == '') |
                    (col_str == 'nan') |
                    (col_str.str.lower() == 'null') |
                    (col_str.str.strip() == '{}')
                )
                missing_mask[col] = missing_mask[col] | meaningless_mask
        
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
        for i, (bar, pct) in enumerate(zip(bars, missing_pct.values)):
            if pct > 50:
                bar.set_color('red')
            elif pct > 20:
                bar.set_color('orange')
            elif pct > 10:
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
        for i, (bar, pct) in enumerate(zip(bars, completeness.values)):
            if pct >= 90:
                bar.set_color('green')
            elif pct >= 70:
                bar.set_color('orange')
            else:
                bar.set_color('red')
        
        # 서브플롯 4: 전체 데이터 품질 점수
        plt.subplot(2, 2, 4)
        overall_quality = self.analysis_results['overall_quality']
        
        # 품질 등급별 색상
        if overall_quality >= 90:
            color = 'green'
            grade = 'Excellent'
        elif overall_quality >= 70:
            color = 'orange'
            grade = 'Good'
        elif overall_quality >= 50:
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
        plt.savefig('data_quality_heatmap.png', dpi=300, bbox_inches='tight')
        
        print("✅ 히트맵 저장 완료: data_quality_heatmap.png")
        plt.show()
    
    def generate_recommendations(self):
        """데이터 보충 권장사항 생성"""
        if self.analysis_results is None:
            print("❌ 분석 결과가 없습니다.")
            return
        
        print("\n💡 데이터 보충 권장사항:")
        print("=" * 60)
        
        missing_pct = self.analysis_results['missing_pct']
        completeness = self.analysis_results['completeness']
        
        # 우선순위별 분류
        critical_fields = missing_pct[missing_pct > 50].index.tolist()
        high_priority_fields = missing_pct[(missing_pct > 20) & (missing_pct <= 50)].index.tolist()
        medium_priority_fields = missing_pct[(missing_pct > 10) & (missing_pct <= 20)].index.tolist()
        
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
        excellent_fields = completeness[completeness >= 95].index.tolist()
        if excellent_fields:
            print(f"\n🟢 EXCELLENT (95% 이상 완성) - 우수한 데이터 품질:")
            for field in excellent_fields:
                pct = completeness[field]
                print(f"   • {field}: {pct:.1f}% 완성")
        
        # 전체 권장사항
        overall_quality = self.analysis_results['overall_quality']
        print(f"\n📊 전체 데이터 품질: {overall_quality:.1f}%")
        
        if overall_quality >= 90:
            print("🎉 데이터 품질이 우수합니다! 추가 보충이 필요하지 않습니다.")
        elif overall_quality >= 70:
            print("✅ 데이터 품질이 양호합니다. 일부 필드만 보충하면 됩니다.")
        elif overall_quality >= 50:
            print("⚠️ 데이터 품질이 보통입니다. 우선순위 필드부터 보충하세요.")
        else:
            print("🚨 데이터 품질이 심각합니다! 전체적인 데이터 수집 개선이 필요합니다.")
    
    def save_analysis_report(self):
        """CSV로 시계열 데이터 저장 (변화 추적 용이)"""
        if self.analysis_results is None:
            print("❌ 분석 결과가 없습니다.")
            return
        
        # 현재 시간 정보
        now = datetime.now()
        date_str = now.strftime('%Y-%m-%d')
        
        # CSV로 시계열 데이터 저장
        csv_history_file = 'data_quality_history.csv'
        
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
        history_file = 'data_quality_history.csv'
        
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
        history_file = 'data_quality_history.csv'
        
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
            
            # 레코드 수 추이
            plt.subplot(2, 2, 2)
            plt.plot(df_history['datetime'], df_history['total_records'], 
                    marker='s', linewidth=2, markersize=8, color='#A23B72')
            plt.title('Total Records Trend', fontsize=14, fontweight='bold')
            plt.xlabel('Date/Time')
            plt.ylabel('Number of Records')
            plt.grid(True, alpha=0.3)
            plt.xticks(rotation=45)
            
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
            plt.savefig('data_quality_timeseries.png', dpi=300, bbox_inches='tight')
            plt.close()
            print("✅ 시계열 시각화 저장 완료: data_quality_timeseries.png")
            
        except Exception as e:
            print(f"❌ 시계열 시각화 생성 중 오류: {e}")
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
        
        print("\n🎉 데이터 품질 분석 완료!")
        print("\n📁 생성된 파일:")
        print("   • data_quality_heatmap.png (히트맵)")
        print("   • data_quality_timeseries.png (시계열 추이)")
        print("   • data_quality_history.csv (시계열 히스토리)")

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

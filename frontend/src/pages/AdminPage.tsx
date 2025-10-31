import React, { useEffect, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { getAiServiceUrl } from '../lib/api';
import ReactApexChart from 'react-apexcharts';
import { TrendingUp, TrendingDown, Activity, Database, Home } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

interface DataQualityResponse {
  success: boolean;
  data: {
    latest: {
      date: string;
      timestamp: string;
      overall_quality: number;
      total_records: number;
      total_fields: number;
      field_completeness: Record<string, number>;
    };
    timeseries: {
      dates: string[];
      overall_quality: number[];
      total_records: number[];
      total_fields: number[];
    };
    field_completeness: Record<string, {
      history: number[];
      latest: number;
      missing_pct: number;
    }>;
  } | null;
  message?: string;
  error?: string;
}

export default function AdminPage() {
  const navigate = useNavigate();
  const [dataQuality, setDataQuality] = useState<DataQualityResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchDataQuality();
  }, []);

  const fetchDataQuality = async () => {
    try {
      setLoading(true);
      setError(null);
      const aiServiceUrl = getAiServiceUrl();
      const response = await fetch(`${aiServiceUrl}/admin/data-quality`);
      const data: DataQualityResponse = await response.json();
      setDataQuality(data);
    } catch (err) {
      console.error('데이터 품질 조회 실패:', err);
      setError('데이터를 불러오는데 실패했습니다.');
    } finally {
      setLoading(false);
    }
  };


  if (loading) {
    return (
      <div className="container mx-auto p-6">
        <div className="flex items-center justify-center h-64">
          <div className="text-lg">데이터를 불러오는 중...</div>
        </div>
      </div>
    );
  }

  if (error || !dataQuality?.success || !dataQuality.data) {
    return (
      <div className="container mx-auto p-6">
        <Card>
          <CardHeader>
            <CardTitle>데이터 품질 관리</CardTitle>
            <CardDescription>데이터 품질 현황을 확인할 수 있습니다.</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-red-500">
              {error || dataQuality?.message || '데이터를 불러올 수 없습니다.'}
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  const { latest, timeseries, field_completeness } = dataQuality.data;
  const fieldNames = Object.keys(field_completeness);

  // 전체 데이터 품질 추이 차트 옵션
  const overallQualityChartOptions: any = {
    chart: {
      type: 'line',
      toolbar: { show: false },
      zoom: { enabled: true }
    },
    title: {
      text: '전체 데이터 품질 추이',
      style: { fontSize: '16px', fontWeight: 'bold' }
    },
    xaxis: {
      categories: timeseries.dates,
      labels: { rotate: -45, rotateAlways: true }
    },
    yaxis: {
      title: { text: '품질 점수 (%)' },
      min: 0,
      max: 100,
      decimalsInFloat: 0,
      labels: {
        formatter: (val: number) => Math.round(val).toString()
      }
    },
    stroke: {
      width: 2,
      curve: 'smooth'
    },
    markers: {
      size: 4
    },
    colors: ['#2563eb'],
    grid: {
      borderColor: '#e5e7eb'
    }
  };

  const overallQualitySeries = [{
    name: '전체 품질',
    data: timeseries.overall_quality
  }];

  // 레코드 수 추이 차트 옵션
  const recordsChartOptions: any = {
    chart: {
      type: 'line',
      toolbar: { show: false },
      zoom: { enabled: true }
    },
    title: {
      text: '총 레코드 수 추이',
      style: { fontSize: '16px', fontWeight: 'bold' }
    },
    xaxis: {
      categories: timeseries.dates,
      labels: { rotate: -45, rotateAlways: true }
    },
    yaxis: {
      title: { text: '레코드 수' },
      decimalsInFloat: 0,
      labels: {
        formatter: (val: number) => Math.round(val).toString()
      }
    },
    stroke: {
      width: 2,
      curve: 'smooth'
    },
    markers: {
      size: 4
    },
    colors: ['#a855f7'],
    grid: {
      borderColor: '#e5e7eb'
    }
  };

  const recordsSeries = [{
    name: '레코드 수',
    data: timeseries.total_records
  }];

  // 필드별 완성도 바 차트 옵션
  const fieldCompletenessChartOptions: any = {
    chart: {
      type: 'bar',
      toolbar: { show: false }
    },
    title: {
      text: '필드별 데이터 완성도',
      style: { fontSize: '16px', fontWeight: 'bold' }
    },
    xaxis: {
      categories: fieldNames,
      labels: { rotate: -45, rotateAlways: true }
    },
    yaxis: {
      title: { text: '완성도 (%)' },
      min: 0,
      max: 100,
      decimalsInFloat: 0,
      labels: {
        formatter: (val: number) => Math.round(val).toString()
      }
    },
    plotOptions: {
      bar: {
        horizontal: false,
        columnWidth: '70%',
        distributed: false,
        dataLabels: {
          position: 'top'
        }
      }
    },
    dataLabels: {
      enabled: true,
      formatter: (val: number) => `${val.toFixed(1)}%`,
      offsetY: -20,
      style: {
        fontSize: '12px',
        colors: ['#304758']
      }
    },
    colors: fieldNames.map(field => {
      const completeness = field_completeness[field].latest;
      if (completeness >= 90) return '#10b981'; // green
      if (completeness >= 70) return '#f59e0b'; // orange
      if (completeness >= 50) return '#ef4444'; // red
      return '#dc2626'; // dark red
    }),
    grid: {
      borderColor: '#e5e7eb'
    }
  };

  const fieldCompletenessSeries = [{
    name: '완성도',
    data: fieldNames.map(field => field_completeness[field].latest)
  }];

  // 필드별 완성도 히스토리 차트 (최대 5개 필드)
  const topIncompleteFields = fieldNames
    .map(field => ({
      field,
      completeness: field_completeness[field].latest
    }))
    .sort((a, b) => a.completeness - b.completeness)
    .slice(0, 5);

  const fieldHistoryChartOptions: any = {
    chart: {
      type: 'line',
      toolbar: { show: false },
      zoom: { enabled: true }
    },
    title: {
      text: '주요 필드 완성도 추이 (완성도 낮은 상위 5개)',
      style: { fontSize: '16px', fontWeight: 'bold' }
    },
    xaxis: {
      categories: timeseries.dates,
      labels: { rotate: -45, rotateAlways: true }
    },
    yaxis: {
      title: { text: '완성도 (%)' },
      min: 0,
      max: 100,
      decimalsInFloat: 0,
      labels: {
        formatter: (val: number) => Math.round(val).toString()
      }
    },
    stroke: {
      width: 2,
      curve: 'smooth'
    },
    markers: {
      size: 4
    },
    colors: ['#ef4444', '#f59e0b', '#eab308', '#84cc16', '#22c55e'],
    legend: {
      position: 'top'
    },
    grid: {
      borderColor: '#e5e7eb'
    }
  };

  const fieldHistorySeries = topIncompleteFields.map(({ field }) => ({
    name: field,
    data: field_completeness[field].history
  }));

  // 품질 등급 색상
  const getQualityColor = (quality: number) => {
    if (quality >= 90) return 'text-green-600';
    if (quality >= 70) return 'text-orange-600';
    if (quality >= 50) return 'text-red-600';
    return 'text-red-800';
  };

  const getQualityBadge = (quality: number) => {
    if (quality >= 90) return '🟢 우수';
    if (quality >= 70) return '🟡 양호';
    if (quality >= 50) return '🟠 보통';
    return '🔴 심각';
  };

  // 품질 변화 계산
  const getQualityTrend = () => {
    if (timeseries.overall_quality.length < 2) return null;
    const current = timeseries.overall_quality[timeseries.overall_quality.length - 1];
    const previous = timeseries.overall_quality[timeseries.overall_quality.length - 2];
    const change = current - previous;
    return { change, current, previous };
  };

  const qualityTrend = getQualityTrend();

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">데이터 품질 관리</h1>
          <p className="text-muted-foreground mt-2">
            데이터베이스의 데이터 품질 현황을 모니터링합니다.
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => navigate('/')}
            className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors flex items-center gap-2"
          >
            <Home className="h-4 w-4" />
            메인 페이지
          </button>
        </div>
      </div>

      {/* 요약 카드 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">전체 데이터 품질</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              <span className={getQualityColor(latest.overall_quality)}>
                {latest.overall_quality.toFixed(1)}%
              </span>
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              {getQualityBadge(latest.overall_quality)}
            </p>
            {qualityTrend && (
              <div className="flex items-center mt-2 text-xs">
                {qualityTrend.change > 0 ? (
                  <>
                    <TrendingUp className="h-3 w-3 text-green-500 mr-1" />
                    <span className="text-green-500">
                      {qualityTrend.change.toFixed(1)}%p 증가
                    </span>
                  </>
                ) : qualityTrend.change < 0 ? (
                  <>
                    <TrendingDown className="h-3 w-3 text-red-500 mr-1" />
                    <span className="text-red-500">
                      {Math.abs(qualityTrend.change).toFixed(1)}%p 감소
                    </span>
                  </>
                ) : (
                  <span className="text-gray-500">변화 없음</span>
                )}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">총 레코드 수</CardTitle>
            <Database className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{latest.total_records.toLocaleString()}</div>
            <p className="text-xs text-muted-foreground mt-1">
              {latest.total_fields}개 필드
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">분석 일시</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-sm font-medium">{latest.date}</div>
            <p className="text-xs text-muted-foreground mt-1">
              {new Date(latest.timestamp).toLocaleString('ko-KR')}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">추적 기간</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{timeseries.dates.length}</div>
            <p className="text-xs text-muted-foreground mt-1">
              분석 횟수
            </p>
          </CardContent>
        </Card>
      </div>

      {/* 누락 데이터 히트맵 (PNG 이미지) */}
      <Card>
        <CardHeader>
          <CardTitle>누락 데이터 히트맵</CardTitle>
          <CardDescription>
            모든 레코드와 필드별로 데이터 누락 여부를 시각화합니다. 
            보라색 = 데이터 존재, 노란색 = 데이터 누락
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="w-full overflow-auto">
            <img
              src={`${getAiServiceUrl()}/admin/data-quality/heatmap-image`}
              alt="데이터 품질 히트맵"
              className="w-full h-auto border rounded-lg"
              onError={(e) => {
                const target = e.target as HTMLImageElement;
                target.style.display = 'none';
                const errorDiv = document.createElement('div');
                errorDiv.className = 'text-center py-8 text-red-500';
                errorDiv.textContent = '히트맵 이미지를 불러올 수 없습니다. 이미지 생성 중일 수 있습니다.';
                target.parentElement?.appendChild(errorDiv);
              }}
            />
          </div>
        </CardContent>
      </Card>

      {/* 필드별 상세 정보 테이블 */}
      <Card>
        <CardHeader>
          <CardTitle>필드별 상세 정보</CardTitle>
          <CardDescription>각 필드의 완성도 및 누락 비율 정보입니다.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b">
                  <th className="text-left p-2">필드명</th>
                  <th className="text-right p-2">완성도</th>
                  <th className="text-right p-2">누락 비율</th>
                  <th className="text-center p-2">상태</th>
                </tr>
              </thead>
              <tbody>
                {fieldNames
                  .sort((a, b) => field_completeness[b].latest - field_completeness[a].latest)
                  .map((field) => {
                    const completeness = field_completeness[field].latest;
                    const missingPct = field_completeness[field].missing_pct;
                    return (
                      <tr key={field} className="border-b hover:bg-gray-50">
                        <td className="p-2 font-medium">{field}</td>
                        <td className="text-right p-2">
                          <span className={getQualityColor(completeness)}>
                            {completeness.toFixed(2)}%
                          </span>
                        </td>
                        <td className="text-right p-2 text-red-600">
                          {missingPct.toFixed(2)}%
                        </td>
                        <td className="text-center p-2">
                          {completeness >= 90 ? (
                            <span className="text-green-600">🟢 우수</span>
                          ) : completeness >= 70 ? (
                            <span className="text-orange-600">🟡 양호</span>
                          ) : completeness >= 50 ? (
                            <span className="text-red-600">🟠 보통</span>
                          ) : (
                            <span className="text-red-800">🔴 심각</span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* 전체 데이터 품질 추이 */}
      <Card>
        <CardHeader>
          <CardTitle>전체 데이터 품질 추이</CardTitle>
          <CardDescription>시간에 따른 전체 데이터 품질 변화를 보여줍니다.</CardDescription>
        </CardHeader>
        <CardContent>
          <ReactApexChart
            options={overallQualityChartOptions}
            series={overallQualitySeries}
            type="line"
            height={350}
          />
        </CardContent>
      </Card>

      {/* 레코드 수 추이 */}
      <Card>
        <CardHeader>
          <CardTitle>총 레코드 수 추이</CardTitle>
          <CardDescription>시간에 따른 총 레코드 수 변화를 보여줍니다.</CardDescription>
        </CardHeader>
        <CardContent>
          <ReactApexChart
            options={recordsChartOptions}
            series={recordsSeries}
            type="line"
            height={350}
          />
        </CardContent>
      </Card>

      {/* 필드별 완성도 */}
      <Card>
        <CardHeader>
          <CardTitle>필드별 데이터 완성도</CardTitle>
          <CardDescription>각 필드의 현재 완성도를 보여줍니다.</CardDescription>
        </CardHeader>
        <CardContent>
          <ReactApexChart
            options={fieldCompletenessChartOptions}
            series={fieldCompletenessSeries}
            type="bar"
            height={400}
          />
        </CardContent>
      </Card>

      {/* 필드별 완성도 히스토리 */}
      {topIncompleteFields.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>주요 필드 완성도 추이</CardTitle>
            <CardDescription>완성도가 낮은 상위 5개 필드의 변화를 추적합니다.</CardDescription>
          </CardHeader>
          <CardContent>
            <ReactApexChart
              options={fieldHistoryChartOptions}
              series={fieldHistorySeries}
              type="line"
              height={350}
            />
          </CardContent>
        </Card>
      )}
    </div>
  );
}

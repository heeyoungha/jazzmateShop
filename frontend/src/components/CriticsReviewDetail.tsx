import { Calendar, User, ExternalLink } from "lucide-react";

interface CriticsDetail {
  id: string;
  title: string;
  reviewer: string;
  date: string;
  reviewSummary: string;
  content: string;
  url: string;
}

interface CriticsReviewDetailProps {
  review: CriticsDetail;
}

interface ParsedSummary {
  summary: string;
  artistInfo: string;
  albumInfo: string;
  trackInfo: Record<string, string>;
  performanceNote: string;
  culturalContext: string;
  instrumentation: string;
  compositionInfluence: string;
  reviewerOpinion: string;
}

function parseSummary(raw: string): ParsedSummary | null {
  if (!raw?.trim()) return null;
  try {
    const p = JSON.parse(raw);
    // track_info는 { korean: { 트랙명: "설명" }, english: {...} } 구조
    const trackInfoKorean: Record<string, string> =
      p.categories?.track_info?.korean ?? {};
    return {
      summary: p.summary?.korean ?? "",
      artistInfo: p.categories?.artist_info?.korean ?? "",
      albumInfo: p.categories?.album_info?.korean ?? "",
      trackInfo: trackInfoKorean,
      performanceNote: p.categories?.performance_note?.korean ?? "",
      culturalContext: p.categories?.cultural_context?.korean ?? "",
      instrumentation: p.categories?.instrumentation?.korean ?? "",
      compositionInfluence: p.categories?.composition_influence?.korean ?? "",
      reviewerOpinion: p.categories?.reviewer_opinion?.korean ?? "",
    };
  } catch {
    return null;
  }
}

function formatDate(dateString: string) {
  if (!dateString) return "";
  return new Date(dateString).toLocaleDateString("ko-KR", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

function Section({
  emoji,
  title,
  children,
}: {
  emoji: string;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-2">
      <h4 className="font-medium text-gray-900 flex items-center gap-1.5">
        <span>{emoji}</span> {title}
      </h4>
      {children}
    </div>
  );
}

export function CriticsReviewDetail({ review }: CriticsReviewDetailProps) {
  const s = parseSummary(review.reviewSummary);

  return (
    <div className="space-y-8">
      {/* 메타 */}
      <div className="space-y-3">
        <h2 className="text-2xl font-bold text-gray-900 leading-snug">
          {review.title}
        </h2>
        <div className="flex items-center gap-4 text-sm text-gray-500">
          <span className="flex items-center gap-1.5">
            <User className="w-4 h-4" />
            {review.reviewer}
          </span>
          {review.date && (
            <span className="flex items-center gap-1.5">
              <Calendar className="w-4 h-4" />
              {formatDate(review.date)}
            </span>
          )}
        </div>
      </div>

      {s ? (
        <div className="space-y-6">
          {/* 요약 */}
          {s.summary && (
            <div className="bg-blue-50 rounded-xl px-5 py-4">
              <p className="text-sm font-semibold text-blue-700 mb-1">
                📝 요약
              </p>
              <p className="text-gray-700 leading-relaxed">{s.summary}</p>
            </div>
          )}

          {/* 카테고리 섹션들 */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            {s.artistInfo && (
              <Section emoji="🎵" title="아티스트 정보">
                <p className="text-sm text-gray-600 leading-relaxed">
                  {s.artistInfo}
                </p>
              </Section>
            )}
            {s.albumInfo && (
              <Section emoji="💿" title="앨범 정보">
                <p className="text-sm text-gray-600 leading-relaxed">
                  {s.albumInfo}
                </p>
              </Section>
            )}
            {s.performanceNote && (
              <Section emoji="🎺" title="연주 노트">
                <p className="text-sm text-gray-600 leading-relaxed">
                  {s.performanceNote}
                </p>
              </Section>
            )}
            {s.instrumentation && (
              <Section emoji="🎷" title="악기 구성">
                <p className="text-sm text-gray-600 leading-relaxed">
                  {s.instrumentation}
                </p>
              </Section>
            )}
            {s.compositionInfluence && (
              <Section emoji="🎼" title="작곡 영향">
                <p className="text-sm text-gray-600 leading-relaxed">
                  {s.compositionInfluence}
                </p>
              </Section>
            )}
            {s.culturalContext && (
              <Section emoji="🌍" title="문화적 맥락">
                <p className="text-sm text-gray-600 leading-relaxed">
                  {s.culturalContext}
                </p>
              </Section>
            )}
          </div>

          {/* 트랙 정보 */}
          {Object.keys(s.trackInfo).length > 0 && (
            <Section emoji="🎼" title="트랙 정보">
              <div className="space-y-2">
                {Object.entries(s.trackInfo).map(([name, data]) => (
                  <div key={name} className="bg-gray-50 rounded-lg px-4 py-3">
                    <p className="text-sm font-medium text-gray-800 mb-0.5">
                      • {name}
                    </p>
                    <p className="text-sm text-gray-600">{data}</p>
                  </div>
                ))}
              </div>
            </Section>
          )}

          {/* 평론가 의견 */}
          {s.reviewerOpinion && (
            <div className="bg-yellow-50 rounded-xl px-5 py-4">
              <p className="text-sm font-semibold text-yellow-700 mb-1">
                ⭐ 평론가 의견
              </p>
              <p className="text-sm text-gray-700 leading-relaxed">
                {s.reviewerOpinion}
              </p>
            </div>
          )}
        </div>
      ) : (
        /* 요약 없을 때 원문 내용 표시 */
        review.content && (
          <div className="space-y-2">
            <h4 className="font-medium text-gray-900">📖 리뷰 내용</h4>
            <p className="text-gray-700 leading-relaxed whitespace-pre-line">
              {review.content}
            </p>
          </div>
        )
      )}

      {/* 원문 링크 */}
      {review.url && (
        <div className="pt-4 border-t">
          <a
            href={review.url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 text-blue-600 hover:text-blue-800 font-medium text-sm transition-colors"
          >
            원문 보기 <ExternalLink className="w-3.5 h-3.5" />
          </a>
        </div>
      )}
    </div>
  );
}

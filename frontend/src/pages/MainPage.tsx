import { BookOpen, Heart, TrendingUp } from "lucide-react";
import { useNavigate } from "react-router-dom";

export function MainPage() {
  const navigate = useNavigate();

  const features = [
    {
      icon: Heart,
      title: "나만의 감상문 작성",
      description:
        "좋아하는 재즈 곡에 대한 상세한 감상을 기록하세요. 느낌, 무드, 장르까지 세심하게 담아낼 수 있습니다.",
      color: "text-red-500",
      label: "작성하기",
      onClick: () => navigate("/write"),
    },
    {
      icon: TrendingUp,
      title: "AI 맞춤 추천",
      description:
        "당신의 감상문을 분석한 AI가 비슷한 분위기의 재즈 앨범을 추천합니다.",
      color: "text-purple-500",
      label: "추천받기",
      onClick: () => navigate("/recommend"),
    },
    {
      icon: BookOpen,
      title: "전문가 리뷰",
      description: "재즈 전문가들의 최신 앨범 리뷰를 확인하세요.",
      color: "text-blue-500",
      label: "리뷰 보기",
      onClick: () => navigate("/critics"),
    },
  ];

  return (
    <div className="max-w-5xl mx-auto px-4 py-12 space-y-16">
      {/* Hero */}
      <section className="text-center space-y-4">
        <h1 className="text-5xl font-bold text-gray-900">
          당신만의 재즈 이야기를
          <br />
          시작하세요
        </h1>
        <p className="text-xl text-gray-500">
          감상을 기록하고, AI가 추천하는 새로운 음악을 만나보세요.
        </p>
      </section>

      {/* Features */}
      <section className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {features.map((f) => {
          const Icon = f.icon;
          return (
            <div
              key={f.title}
              onClick={f.onClick}
              className="border rounded-xl p-6 cursor-pointer hover:shadow-lg transition-all hover:-translate-y-1 space-y-4"
            >
              <div
                className={`inline-flex p-3 rounded-xl bg-gray-50 ${f.color}`}
              >
                <Icon className="h-7 w-7" />
              </div>
              <h2 className="text-lg font-semibold text-gray-900">{f.title}</h2>
              <p className="text-sm text-gray-500 leading-relaxed">
                {f.description}
              </p>
              <button className="text-sm font-medium border rounded-lg px-4 py-2 hover:bg-gray-50 transition-colors">
                {f.label}
              </button>
            </div>
          );
        })}
      </section>
    </div>
  );
}

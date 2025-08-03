import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import { ImageWithFallback } from "../components/figma/ImageWithFallback";
import { Heart, MapPin, TrendingUp, BookOpen, PenTool, User, Sparkles, Star, Calendar } from "lucide-react";

export default function MainPage() {
  const renderStars = (rating: number) => {
    const fullStars = Math.floor(rating);
    const hasHalfStar = rating % 1 !== 0;
    
    return (
      <div className="flex items-center gap-1">
        {Array.from({ length: 5 }, (_, i) => {
          if (i < fullStars) {
            return <Star key={i} className="h-4 w-4 fill-yellow-400 text-yellow-400" />;
          } else if (i === fullStars && hasHalfStar) {
            return <Star key={i} className="h-4 w-4 fill-yellow-400/50 text-yellow-400" />;
          } else {
            return <Star key={i} className="h-4 w-4 text-gray-300" />;
          }
        })}
        <span className="ml-1 text-sm">{rating.toFixed(1)}</span>
      </div>
    );
  };

  const features = [
    {
      icon: Heart,
      title: "나만의 감상문 작성",
      description: "좋아하는 재즈 곡에 대한 상세한 감상을 기록하고 공유하세요. 보컬, 연주자, 작곡가 정보부터 추천 테마, 느낌까지 세심하게 담아낼 수 있습니다.",
      color: "text-red-500",
      gradient: "from-red-50 to-pink-50 dark:from-red-950/20 dark:to-pink-950/20",
      example: "Kind of Blue를 들으며 느낀 그 깊은 감동을 기록하고 싶어요"
    },
    {
      icon: TrendingUp,
      title: "AI 맞춤 추천",
      description: "당신의 감상 패턴과 취향을 분석한 AI 알고리즘이 매달 새로운 앨범과 트랙을 추천합니다. 당신만을 위한 재즈 발견의 여정을 시작하세요.",
      color: "text-purple-500",
      gradient: "from-purple-50 to-indigo-50 dark:from-purple-950/20 dark:to-indigo-950/20",
      example: "당신이 좋아할 만한 숨겨진 재즈 명반들을 발견해보세요"
    },
    {
      icon: BookOpen,
      title: "최근 전문가 리뷰",
      description: "재즈 전문가들의 최신 앨범 리뷰를 확인해보세요. 클래식의 현대적 해석부터 새로운 발견까지 전문가의 시각을 만나보세요.",
      color: "text-blue-500",
      gradient: "from-blue-50 to-cyan-50 dark:from-blue-950/20 dark:to-cyan-950/20",
      example: "Miles Davis의 Kind of Blue 재해석"
    }
  ];

  return (
    <div className="space-y-16 px-4 max-w-7xl mx-auto">
      {/* Hero Section */}
      <section className="relative -mt-8">
        <div className="relative overflow-hidden rounded-2xl">
          <ImageWithFallback
            src="https://images.unsplash.com/photo-1687589891886-a8578a54ef76?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&q=80&w=1400"
            alt="Jazz musician"
            className="w-full h-[500px] object-cover"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-black via-black/60 to-black/30" />
          <div className="absolute inset-0 flex items-center justify-center text-center">
            <div className="max-w-3xl px-6">
              <Badge className="mb-6 bg-primary/20 text-white border-white/30 backdrop-blur-sm">
                재즈를 사랑하는 당신을 위한 특별한 공간
              </Badge>
              <h1 className="text-5xl mb-6 text-white">
                당신만의 재즈 이야기를<br />시작하세요
              </h1>
              <p className="text-xl text-white/90 mb-8 leading-relaxed">
                감상을 기록하고, 공연을 공유하고, AI가 추천하는 새로운 음악을 만나보세요.<br />
                재즈 팬들의 커뮤니티에서 함께 성장하는 음악 여정이 시작됩니다.
              </p>
              <div className="flex gap-4 justify-center">
                <Button size="lg" className="bg-white text-black hover:bg-white/90 px-8 py-3">
                  <Heart className="mr-2 h-5 w-5" />
                  감상문 시작하기
                </Button>
                <Button size="lg" variant="outline" className="bg-transparent text-white border-white/30 hover:bg-white/10 px-8 py-3">
                  <MapPin className="mr-2 h-5 w-5" />
                  재즈 스팟 둘러보기
                </Button>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Main Features */}
      <section>
        <div className="text-center mb-12">
          <Badge className="mb-4">핵심 기능</Badge>
          <h2 className="mb-4">세 가지 특별한 경험</h2>
          <p className="text-muted-foreground text-lg">
            Jazz Playlist만의 독특한 기능으로 재즈를 더욱 깊이 즐겨보세요
          </p>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {features.map((feature, index) => {
            const Icon = feature.icon;
            return (
              <Card key={index} className="relative overflow-hidden border-2 hover:shadow-xl transition-all duration-300 hover:-translate-y-1">
                <div className={`absolute inset-0 bg-gradient-to-br ${feature.gradient} opacity-50`} />
                <CardHeader className="relative">
                  <div className={`inline-flex p-3 rounded-xl bg-white dark:bg-card mb-4 ${feature.color}`}>
                    <Icon className="h-8 w-8" />
                  </div>
                  <CardTitle>{feature.title}</CardTitle>
                </CardHeader>
                <CardContent className="relative">
                  <p className="text-muted-foreground leading-relaxed mb-4">
                    {feature.description}
                  </p>
                  {feature.example && (
                    <div className="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg mb-4">
                      <p className="text-sm text-gray-700 dark:text-gray-300 italic">
                        "{feature.example}"
                      </p>
                    </div>
                  )}
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <User className="h-4 w-4 text-muted-foreground" />
                      <span className="text-sm text-muted-foreground">
                        {index === 0 ? "개인 감상" : index === 1 ? "AI 분석" : "전문가 리뷰"}
                      </span>
                    </div>
                    <Button variant="outline" size="sm" className="px-4 py-2">
                      {index === 0 ? "작성하기" : index === 1 ? "추천받기" : "리뷰 보기"}
                    </Button>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      </section>
    </div>
  );
}
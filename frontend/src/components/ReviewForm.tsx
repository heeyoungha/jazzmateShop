import { useState } from "react";
import { Music, User, FileText, Star, Zap, Mic, Music2 } from "lucide-react";

export interface ReviewFormData {
  trackName: string;
  artistName: string;
  reviewContent: string;
  rating?: number;
  mood?: string;
  genre?: string;
  energyLevel?: number;
  bpm?: number;
  vocalStyle?: string;
  instrumentation?: string;
  isPublic: boolean;
}

interface ReviewFormProps {
  onSubmit: (data: ReviewFormData) => void;
  submitting?: boolean;
  error?: string;
}

export function ReviewForm({ onSubmit, submitting, error }: ReviewFormProps) {
  const [validationErrors, setValidationErrors] = useState<
    Record<string, string>
  >({});

  function getText(formData: FormData, name: string) {
    return String(formData.get(name) ?? "").trim();
  }

  function getOptionalNumber(formData: FormData, name: string) {
    const value = getText(formData, name);
    if (!value) return undefined;

    const number = Number(value);
    return Number.isFinite(number) ? number : undefined;
  }

  function validate(
    data: Pick<ReviewFormData, "trackName" | "artistName" | "reviewContent">,
  ) {
    const errors: Record<string, string> = {};
    if (!data.trackName) errors.trackName = "곡명은 필수입니다.";
    if (!data.artistName) errors.artistName = "아티스트는 필수입니다.";
    if (!data.reviewContent) errors.reviewContent = "감상문은 필수입니다.";
    return errors;
  }

  function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    const requiredData = {
      trackName: getText(formData, "trackName"),
      artistName: getText(formData, "artistName"),
      reviewContent: getText(formData, "reviewContent"),
    };
    const errors = validate(requiredData);

    if (Object.keys(errors).length > 0) {
      setValidationErrors(errors);
      return;
    }

    setValidationErrors({});

    const rating = getOptionalNumber(formData, "rating");
    const energyLevel = getOptionalNumber(formData, "energyLevel");
    const bpm = getOptionalNumber(formData, "bpm");
    const mood = getText(formData, "mood");
    const genre = getText(formData, "genre");
    const vocalStyle = getText(formData, "vocalStyle");
    const instrumentation = getText(formData, "instrumentation");

    const data: ReviewFormData = {
      ...requiredData,
      isPublic: formData.get("isPublic") === "on",
      ...(rating !== undefined && { rating }),
      ...(mood && { mood }),
      ...(genre && { genre }),
      ...(energyLevel !== undefined && { energyLevel }),
      ...(bpm !== undefined && { bpm }),
      ...(vocalStyle && { vocalStyle }),
      ...(instrumentation && { instrumentation }),
    };

    onSubmit(data);
  }

  const inputClass =
    "w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-900 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition";

  function Field({
    id,
    label,
    icon: Icon,
    error: fieldError,
    children,
  }: {
    id: string;
    label: string;
    icon?: React.ElementType;
    error?: string;
    children: React.ReactNode;
  }) {
    return (
      <div className="space-y-1.5">
        <label
          htmlFor={id}
          className="flex items-center gap-1.5 text-sm font-medium text-gray-700"
        >
          {Icon && <Icon className="w-4 h-4 text-gray-400" />}
          {label}
        </label>
        {children}
        {fieldError && <p className="text-xs text-red-500">{fieldError}</p>}
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-8">
      {/* 필수 항목 */}
      <div className="space-y-4">
        <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-widest">
          필수 정보
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Field
            id="trackName"
            label="곡명"
            icon={Music}
            error={validationErrors.trackName}
          >
            <input
              id="trackName"
              name="trackName"
              placeholder="예) So What"
              className={inputClass}
            />
          </Field>
          <Field
            id="artistName"
            label="아티스트"
            icon={User}
            error={validationErrors.artistName}
          >
            <input
              id="artistName"
              name="artistName"
              placeholder="예) Miles Davis"
              className={inputClass}
            />
          </Field>
        </div>
        <Field
          id="reviewContent"
          label="감상문"
          icon={FileText}
          error={validationErrors.reviewContent}
        >
          <textarea
            id="reviewContent"
            name="reviewContent"
            rows={5}
            placeholder="이 곡을 들으며 느낀 감정, 분위기, 인상적인 부분을 자유롭게 적어보세요."
            className={`${inputClass} resize-none`}
          />
        </Field>
      </div>

      {/* 선택 항목 */}
      <div className="space-y-4">
        <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-widest">
          선택 정보
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          <Field id="rating" label="평점" icon={Star}>
            <input
              id="rating"
              name="rating"
              type="number"
              step="0.1"
              min="0"
              max="5"
              placeholder="0 ~ 5"
              className={inputClass}
            />
          </Field>
          <Field id="mood" label="무드">
            <input
              id="mood"
              name="mood"
              placeholder="예) 차분한, 몽환적"
              className={inputClass}
            />
          </Field>
          <Field id="genre" label="장르">
            <input
              id="genre"
              name="genre"
              placeholder="예) Modal Jazz"
              className={inputClass}
            />
          </Field>
          <Field id="energyLevel" label="에너지" icon={Zap}>
            <input
              id="energyLevel"
              name="energyLevel"
              type="number"
              step="0.1"
              min="0"
              max="10"
              placeholder="0 ~ 10"
              className={inputClass}
            />
          </Field>
          <Field id="bpm" label="BPM">
            <input
              id="bpm"
              name="bpm"
              type="number"
              placeholder="예) 120"
              className={inputClass}
            />
          </Field>
          <Field id="vocalStyle" label="보컬 스타일" icon={Mic}>
            <input
              id="vocalStyle"
              name="vocalStyle"
              placeholder="예) 인스트루멘탈"
              className={inputClass}
            />
          </Field>
        </div>
        <Field id="instrumentation" label="편성" icon={Music2}>
          <input
            id="instrumentation"
            name="instrumentation"
            placeholder="예) 트리오, 빅밴드"
            className={inputClass}
          />
        </Field>
      </div>

      {/* 공개 설정 */}
      <label className="flex items-center gap-3 cursor-pointer select-none">
        <input
          id="isPublic"
          name="isPublic"
          type="checkbox"
          className="w-4 h-4 rounded border-gray-300 accent-gray-900"
        />
        <span className="text-sm text-gray-700">감상문 공개</span>
      </label>

      {error && (
        <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-600">
          {error}
        </div>
      )}

      <button
        type="submit"
        disabled={submitting}
        className="w-full rounded-lg bg-gray-900 text-white py-3 text-sm font-semibold hover:bg-gray-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {submitting ? "저장 중..." : "감상문 저장하기"}
      </button>
    </form>
  );
}

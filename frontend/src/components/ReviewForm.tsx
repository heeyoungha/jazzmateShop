import { useState } from "react";

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

  return (
    <form onSubmit={handleSubmit}>
      <div>
        <label htmlFor="trackName">곡명</label>
        <input id="trackName" name="trackName" />
        {validationErrors.trackName && <p>{validationErrors.trackName}</p>}
      </div>
      <div>
        <label htmlFor="artistName">아티스트</label>
        <input id="artistName" name="artistName" />
        {validationErrors.artistName && <p>{validationErrors.artistName}</p>}
      </div>
      <div>
        <label htmlFor="reviewContent">감상문</label>
        <textarea id="reviewContent" name="reviewContent" />
        {validationErrors.reviewContent && (
          <p>{validationErrors.reviewContent}</p>
        )}
      </div>
      <div>
        <label htmlFor="rating">평점</label>
        <input id="rating" name="rating" type="number" step="0.1" />
      </div>
      <div>
        <label htmlFor="mood">무드</label>
        <input id="mood" name="mood" />
      </div>
      <div>
        <label htmlFor="genre">장르</label>
        <input id="genre" name="genre" />
      </div>
      <div>
        <label htmlFor="energyLevel">에너지</label>
        <input
          id="energyLevel"
          name="energyLevel"
          type="number"
          step="0.1"
        />
      </div>
      <div>
        <label htmlFor="bpm">BPM</label>
        <input id="bpm" name="bpm" type="number" />
      </div>
      <div>
        <label htmlFor="vocalStyle">보컬 스타일</label>
        <input id="vocalStyle" name="vocalStyle" />
      </div>
      <div>
        <label htmlFor="instrumentation">편성</label>
        <input id="instrumentation" name="instrumentation" />
      </div>
      <div>
        <label htmlFor="isPublic">공개</label>
        <input id="isPublic" name="isPublic" type="checkbox" />
      </div>
      {error && <p>{error}</p>}
      <button type="submit" disabled={submitting}>
        {submitting ? "저장 중" : "저장"}
      </button>
    </form>
  );
}

interface CriticsReview {
  id: string;
  title: string;
  reviewer: string;
  date: string;
  reviewSummary: string;
}

interface CriticsReviewCardProps {
  review: CriticsReview;
  onClick: () => void;
}

export function CriticsReviewCard({ review, onClick }: CriticsReviewCardProps) {
  return (
    <button type="button" onClick={onClick}>
      <p>{review.title}</p>
      <p>{review.reviewer}</p>
      <p>{review.date}</p>
      <p>{review.reviewSummary}</p>
    </button>
  );
}

interface Review {
  id: number;
  trackName: string;
  artistName: string;
  rating?: number;
  createdAt: string;
}

interface ReviewCardProps {
  review: Review;
  onClick: () => void;
}

export function ReviewCard({ review, onClick }: ReviewCardProps) {
  return (
    <button type="button" onClick={onClick}>
      <p>{review.trackName}</p>
      <p>{review.artistName}</p>
      {review.rating !== undefined && <p>{review.rating}</p>}
      <p>{review.createdAt}</p>
    </button>
  );
}

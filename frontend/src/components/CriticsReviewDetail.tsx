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

export function CriticsReviewDetail({ review }: CriticsReviewDetailProps) {
  return (
    <div>
      <p>{review.title}</p>
      <p>{review.content}</p>
      <p>{review.reviewSummary}</p>
      <a href={review.url}>원문 보기</a>
    </div>
  );
}

interface RetryButtonProps {
  onRetry: () => void | Promise<void>;
}

export function RetryButton({ onRetry }: RetryButtonProps) {
  return (
    <button type="button" onClick={onRetry}>
      다시 시도
    </button>
  );
}

interface PageCursor {
  number: number;
  last: boolean;
}

export function getNextReviewPage(page: PageCursor): number | null {
  return page.last ? null : page.number + 1;
}

export function getNextCriticsPage(page: PageCursor): number | null {
  return page.last ? null : page.number + 1;
}

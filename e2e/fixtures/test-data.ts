/**
 * Test Data Fixtures for JazzMate E2E Tests
 *
 * Contains reusable test data for users, reviews, albums, and tracks
 */

export const testUsers = {
  defaultUser: {
    userId: 'test-user-001',
    username: '재즈애호가',
  },
  premiumUser: {
    userId: 'test-user-002',
    username: '프리미엄유저',
  },
};

export const testReviews = {
  validReview: {
    reviewContent: 'Miles Davis의 So What은 모달 재즈의 정수입니다. 미니멀한 코드 진행 속에서 자유로운 즉흥 연주가 돋보입니다.',
    rating: 5,
    isPublic: true,
  },
  shortReview: {
    reviewContent: '훌륭한 연주입니다!',
    rating: 4,
    isPublic: true,
  },
  privateReview: {
    reviewContent: '개인적으로 좋아하는 트랙입니다.',
    rating: 4,
    isPublic: false,
  },
};

export const testAlbums = {
  kindOfBlue: {
    albumName: 'Kind of Blue',
    artistName: 'Miles Davis',
  },
  timeOut: {
    albumName: 'Time Out',
    artistName: 'Dave Brubeck',
  },
};

export const testTracks = {
  soWhat: {
    trackName: 'So What',
    albumName: 'Kind of Blue',
    artistName: 'Miles Davis',
  },
  takeFive: {
    trackName: 'Take Five',
    albumName: 'Time Out',
    artistName: 'Dave Brubeck',
  },
};

export const apiEndpoints = {
  albums: '/api/albums',
  albumSearch: '/api/albums/search',
  userReviews: '/api/user-reviews',
  recommendations: '/api/recommendations',
  tracks: '/api/tracks',
};

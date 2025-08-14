package shop.jazzmate.jazzmateshop.album;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import shop.jazzmate.jazzmateshop.album.dto.AlbumSearchResponse;
import shop.jazzmate.jazzmateshop.album.entity.Album;

import java.util.List;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
@Slf4j
public class AlbumService {
    
    private final AlbumRepository albumRepository;
    
    /**
     * 앨범 검색
     */
    public List<AlbumSearchResponse> searchAlbums(String query, int page, int size) {
        try {
            log.info("앨범 검색 시작: query={}", query);
            
            List<Album> albums = albumRepository.findByAlbumTitleContainingIgnoreCaseOrAlbumArtistContainingIgnoreCase(
                query, query
            );
            
            // 페이징 처리
            int start = page * size;
            int end = Math.min(start + size, albums.size());
            
            if (start >= albums.size()) {
                return List.of();
            }
            
            List<AlbumSearchResponse> result = albums.subList(start, end).stream()
                .map(this::convertToSearchResponse)
                .collect(Collectors.toList());
            
            log.info("앨범 검색 완료: {}개 결과", result.size());
            
            return result;
            
        } catch (Exception e) {
            log.error("앨범 검색 오류: ", e);
            throw new RuntimeException("앨범 검색 중 오류가 발생했습니다: " + e.getMessage());
        }
    }
    
    /**
     * 특정 앨범 조회
     */
    public AlbumSearchResponse getAlbum(Integer id) {
        try {
            Album album = albumRepository.findById(id)
                .orElseThrow(() -> new RuntimeException("앨범을 찾을 수 없습니다."));
            
            return convertToSearchResponse(album);
            
        } catch (Exception e) {
            log.error("앨범 조회 오류: ", e);
            throw new RuntimeException("앨범 조회 중 오류가 발생했습니다: " + e.getMessage());
        }
    }
    
    /**
     * Album 엔티티를 AlbumSearchResponse로 변환
     */
    private AlbumSearchResponse convertToSearchResponse(Album album) {
        return AlbumSearchResponse.builder()
            .id(album.getId())
            .albumArtist(album.getAlbumArtist())
            .albumTitle(album.getAlbumTitle())
            .albumYear(album.getAlbumYear())
            .albumLabel(album.getAlbumLabel())
            .trackListing(album.getTrackListing())
            .criticsReviewId(album.getCriticsReviewId())
            .createdAt(album.getCreatedAt())
            .updatedAt(album.getUpdatedAt())
            .build();
    }
}

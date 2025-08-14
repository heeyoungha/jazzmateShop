package shop.jazzmate.jazzmateshop.album;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;
import shop.jazzmate.jazzmateshop.album.entity.Album;

import java.util.List;

@Repository
public interface AlbumRepository extends JpaRepository<Album, Integer> {
    
    /**
     * 앨범 제목 또는 아티스트명으로 검색
     */
    List<Album> findByAlbumTitleContainingIgnoreCaseOrAlbumArtistContainingIgnoreCase(
        String albumTitle, String albumArtist
    );
    
    /**
     * 아티스트별 앨범 목록 조회
     */
    List<Album> findByAlbumArtistOrderByAlbumYearDesc(String albumArtist);
    
    /**
     * 연도별 앨범 목록 조회
     */
    List<Album> findByAlbumYearOrderByAlbumTitleAsc(Integer albumYear);
    
    /**
     * 레이블별 앨범 목록 조회
     */
    List<Album> findByAlbumLabelOrderByAlbumYearDesc(String albumLabel);
    
    /**
     * 최신 앨범 목록 조회
     */
    List<Album> findTop10ByOrderByCreatedAtDesc();
    
    /**
     * 아티스트별 앨범 개수 조회
     */
    long countByAlbumArtist(String albumArtist);
    
    /**
     * 연도별 앨범 개수 조회
     */
    long countByAlbumYear(Integer albumYear);
}

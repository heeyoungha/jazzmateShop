package shop.jazzmate.jazzmateshop.userReview;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;
import shop.jazzmate.jazzmateshop.userReview.entity.Track;

import java.util.List;
import java.util.Optional;

@Repository
public interface TrackRepository extends JpaRepository<Track, Integer> {
    
    /**
     * 아티스트명과 트랙명으로 트랙 검색
     */
    @Query("SELECT t FROM Track t WHERE t.artistName = :artistName AND t.trackTitle = :trackTitle")
    Optional<Track> findByArtistNameAndTrackTitle(@Param("artistName") String artistName, 
                                                  @Param("trackTitle") String trackTitle);
    
    /**
     * 아티스트명으로 트랙 검색
     */
    List<Track> findByArtistNameContainingIgnoreCase(String artistName);
    
    /**
     * 트랙명으로 트랙 검색
     */
    List<Track> findByTrackTitleContainingIgnoreCase(String trackTitle);
}

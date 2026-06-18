package shop.jazzmate.jazzmateshop.musicbrainz;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import shop.jazzmate.jazzmateshop.musicbrainz.entity.MusicBrainzAlbum;

import java.util.List;
import java.util.UUID;

public interface MusicBrainzAlbumRepository extends JpaRepository<MusicBrainzAlbum, UUID> {

    @Query("""
            SELECT a FROM MusicBrainzAlbum a
            WHERE LOWER(a.name) LIKE LOWER(CONCAT('%', :albumName, '%'))
              AND LOWER(a.artistName) LIKE LOWER(CONCAT('%', :artistName, '%'))
            ORDER BY a.firstReleaseYear ASC
            """)
    List<MusicBrainzAlbum> search(@Param("albumName") String albumName,
                                  @Param("artistName") String artistName);
}

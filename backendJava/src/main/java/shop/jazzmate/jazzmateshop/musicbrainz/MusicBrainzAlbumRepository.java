package shop.jazzmate.jazzmateshop.musicbrainz;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import shop.jazzmate.jazzmateshop.musicbrainz.entity.MusicBrainzAlbum;

import java.util.List;
import java.util.UUID;

public interface MusicBrainzAlbumRepository extends JpaRepository<MusicBrainzAlbum, UUID> {

    @Query(value = """
            SELECT * FROM mb_album
            WHERE LOWER(name) LIKE LOWER(CONCAT('%', :albumName, '%'))
              AND (:artistName = '' OR LOWER(artist_name) LIKE LOWER(CONCAT('%', :artistName, '%')))
            ORDER BY first_release_year ASC
            LIMIT 20
            """, nativeQuery = true)
    List<MusicBrainzAlbum> search(@Param("albumName") String albumName,
                                  @Param("artistName") String artistName);
}

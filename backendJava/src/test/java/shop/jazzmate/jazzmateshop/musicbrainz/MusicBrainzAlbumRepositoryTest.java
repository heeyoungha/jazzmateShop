package shop.jazzmate.jazzmateshop.musicbrainz;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.orm.jpa.DataJpaTest;
import shop.jazzmate.jazzmateshop.musicbrainz.entity.MusicBrainzAlbum;
import shop.jazzmate.jazzmateshop.musicbrainz.entity.MusicBrainzArtist;

import java.util.List;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;

@DataJpaTest
class MusicBrainzAlbumRepositoryTest {

    private static final UUID ARTIST_GID =
            UUID.fromString("10000000-0000-0000-0000-000000000001");
    private static final UUID ALBUM_GID =
            UUID.fromString("20000000-0000-0000-0000-000000000001");

    @Autowired
    MusicBrainzAlbumRepository musicBrainzAlbumRepository;

    @Autowired
    MusicBrainzArtistRepository musicBrainzArtistRepository;

    @Test
    @DisplayName("앨범명과 아티스트명으로 MusicBrainz 앨범 후보를 검색한다")
    void searchByAlbumAndArtist_returnsMatches() {
        MusicBrainzArtist artist = musicBrainzArtistRepository.save(
                MusicBrainzArtist.builder()
                        .gid(ARTIST_GID)
                        .name("Miles Davis")
                        .build()
        );
        musicBrainzAlbumRepository.save(
                MusicBrainzAlbum.builder()
                        .gid(ALBUM_GID)
                        .name("Kind of Blue")
                        .artist(artist)
                        .firstReleaseYear(1959)
                        .coverArtUrl("https://cover.example/kind-of-blue")
                        .build()
        );

        List<MusicBrainzAlbum> result =
                musicBrainzAlbumRepository.search("Kind of Blue", "Miles Davis");

        assertThat(result).extracting(MusicBrainzAlbum::getGid)
                .containsExactly(ALBUM_GID);
    }

    @Test
    @DisplayName("일치하는 MusicBrainz 앨범이 없으면 빈 목록을 반환한다")
    void search_noMatch_returnsEmptyList() {
        assertThat(musicBrainzAlbumRepository.search("Unknown Album", "Nobody"))
                .isEmpty();
    }
}

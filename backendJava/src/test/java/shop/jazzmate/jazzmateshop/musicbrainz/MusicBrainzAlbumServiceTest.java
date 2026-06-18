package shop.jazzmate.jazzmateshop.musicbrainz;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import shop.jazzmate.jazzmateshop.musicbrainz.dto.MusicBrainzAlbumSearchResponse;
import shop.jazzmate.jazzmateshop.musicbrainz.entity.MusicBrainzAlbum;

import java.util.List;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.BDDMockito.given;

@ExtendWith(MockitoExtension.class)
class MusicBrainzAlbumServiceTest {

    @Mock
    MusicBrainzAlbumRepository musicBrainzAlbumRepository;

    @InjectMocks
    MusicBrainzAlbumService musicBrainzAlbumService;

    @Test
    @DisplayName("Repository 검색 결과를 화면용 앨범 후보 DTO로 변환한다")
    void search_mapsAlbumsToResponses() {
        UUID gid = UUID.fromString("20000000-0000-0000-0000-000000000001");
        MusicBrainzAlbum album = MusicBrainzAlbum.builder()
                .gid(gid)
                .name("Kind of Blue")
                .artistName("Miles Davis")
                .firstReleaseYear(1959)
                .coverArtUrl("https://cover.example/kind-of-blue")
                .build();
        given(musicBrainzAlbumRepository.search("Kind of Blue", "Miles Davis"))
                .willReturn(List.of(album));

        List<MusicBrainzAlbumSearchResponse> result =
                musicBrainzAlbumService.search("Kind of Blue", "Miles Davis");

        assertThat(result).singleElement().satisfies(response -> {
            assertThat(response.getGid()).isEqualTo(gid);
            assertThat(response.getName()).isEqualTo("Kind of Blue");
            assertThat(response.getArtistName()).isEqualTo("Miles Davis");
            assertThat(response.getFirstReleaseYear()).isEqualTo(1959);
            assertThat(response.getCoverArtUrl())
                    .isEqualTo("https://cover.example/kind-of-blue");
        });
    }
}

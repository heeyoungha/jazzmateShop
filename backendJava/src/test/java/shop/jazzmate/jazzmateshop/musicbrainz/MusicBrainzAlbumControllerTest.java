package shop.jazzmate.jazzmateshop.musicbrainz;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.test.web.servlet.MockMvc;
import shop.jazzmate.jazzmateshop.musicbrainz.dto.MusicBrainzAlbumSearchResponse;

import java.util.List;
import java.util.UUID;

import static org.mockito.BDDMockito.given;
import static org.mockito.Mockito.verify;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(MusicBrainzAlbumController.class)
class MusicBrainzAlbumControllerTest {

    @Autowired
    MockMvc mockMvc;

    @MockBean
    MusicBrainzAlbumService musicBrainzAlbumService;

    @Test
    @DisplayName("GET 앨범 검색 요청의 파라미터를 Service에 위임하고 후보 목록을 반환한다")
    void search_returnsAlbumCandidates() throws Exception {
        UUID gid = UUID.fromString("20000000-0000-0000-0000-000000000001");
        given(musicBrainzAlbumService.search("Kind of Blue", "Miles Davis"))
                .willReturn(List.of(new MusicBrainzAlbumSearchResponse(
                        gid,
                        "Kind of Blue",
                        "Miles Davis",
                        1959,
                        "https://cover.example/kind-of-blue"
                )));

        mockMvc.perform(get("/api/musicbrainz/albums/search")
                        .param("albumName", "Kind of Blue")
                        .param("artistName", "Miles Davis"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[0].gid").value(gid.toString()))
                .andExpect(jsonPath("$[0].name").value("Kind of Blue"))
                .andExpect(jsonPath("$[0].artistName").value("Miles Davis"))
                .andExpect(jsonPath("$[0].firstReleaseYear").value(1959));

        verify(musicBrainzAlbumService).search("Kind of Blue", "Miles Davis");
    }

    @Test
    @DisplayName("검색 결과가 없으면 HTTP 200과 빈 목록을 반환한다")
    void search_noMatch_returnsEmptyList() throws Exception {
        given(musicBrainzAlbumService.search("Unknown Album", "Nobody"))
                .willReturn(List.of());

        mockMvc.perform(get("/api/musicbrainz/albums/search")
                        .param("albumName", "Unknown Album")
                        .param("artistName", "Nobody"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$").isEmpty());
    }
}

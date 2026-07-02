package shop.jazzmate.jazzmateshop.musicbrainz;

import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import io.swagger.v3.oas.annotations.tags.Tag;
import shop.jazzmate.jazzmateshop.musicbrainz.dto.MusicBrainzAlbumSearchResponse;

import java.util.List;

@Tag(name = "musicbrainz", description = "앨범 검색 (MusicBrainz 프록시)")
@RestController
@RequestMapping("/api/musicbrainz/albums")
@RequiredArgsConstructor
public class MusicBrainzAlbumController {

    private final MusicBrainzAlbumService musicBrainzAlbumService;

    @GetMapping("/search")
    public List<MusicBrainzAlbumSearchResponse> search(
            @RequestParam String albumName,
            @RequestParam(required = false, defaultValue = "") String artistName) {
        return musicBrainzAlbumService.search(albumName, artistName);
    }
}

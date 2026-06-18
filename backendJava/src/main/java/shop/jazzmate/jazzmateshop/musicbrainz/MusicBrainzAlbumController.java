package shop.jazzmate.jazzmateshop.musicbrainz;

import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import shop.jazzmate.jazzmateshop.musicbrainz.dto.MusicBrainzAlbumSearchResponse;

import java.util.List;

@RestController
@RequestMapping("/api/musicbrainz/albums")
@RequiredArgsConstructor
public class MusicBrainzAlbumController {

    private final MusicBrainzAlbumService musicBrainzAlbumService;

    @GetMapping("/search")
    public List<MusicBrainzAlbumSearchResponse> search(
            @RequestParam String albumName,
            @RequestParam String artistName) {
        return musicBrainzAlbumService.search(albumName, artistName);
    }
}

package shop.jazzmate.jazzmateshop.musicbrainz;

import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import shop.jazzmate.jazzmateshop.musicbrainz.dto.MusicBrainzAlbumSearchResponse;

import java.util.List;

@Service
@RequiredArgsConstructor
public class MusicBrainzAlbumService {

    private final MusicBrainzAlbumRepository musicBrainzAlbumRepository;

    @Transactional(readOnly = true)
    public List<MusicBrainzAlbumSearchResponse> search(String albumName, String artistName) {
        return musicBrainzAlbumRepository.search(albumName, artistName)
                .stream()
                .map(MusicBrainzAlbumSearchResponse::from)
                .toList();
    }
}

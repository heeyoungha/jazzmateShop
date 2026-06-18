package shop.jazzmate.jazzmateshop.musicbrainz.dto;

import lombok.AllArgsConstructor;
import lombok.Getter;
import shop.jazzmate.jazzmateshop.musicbrainz.entity.MusicBrainzAlbum;

import java.util.UUID;

@Getter
@AllArgsConstructor
public class MusicBrainzAlbumSearchResponse {

    private UUID gid;
    private String name;
    private String artistName;
    private Integer firstReleaseYear;
    private String coverArtUrl;

    public static MusicBrainzAlbumSearchResponse from(MusicBrainzAlbum album) {
        return new MusicBrainzAlbumSearchResponse(
                album.getGid(),
                album.getName(),
                album.getArtistName(),
                album.getFirstReleaseYear(),
                album.getCoverArtUrl()
        );
    }
}

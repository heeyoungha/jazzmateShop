package shop.jazzmate.jazzmateshop.musicbrainz.entity;

import jakarta.persistence.*;
import lombok.*;

import java.util.UUID;

@Entity
@Table(name = "mb_album")
@Getter
@Builder
@NoArgsConstructor(access = AccessLevel.PROTECTED)
@AllArgsConstructor(access = AccessLevel.PRIVATE)
public class MusicBrainzAlbum {

    @Id
    @Column(name = "gid", columnDefinition = "uuid")
    private UUID gid;

    @Column(name = "name", nullable = false)
    private String name;

    @Column(name = "artist_name")
    private String artistName;

    @Column(name = "first_release_year")
    private Integer firstReleaseYear;

    @Column(name = "cover_art_url")
    private String coverArtUrl;
}

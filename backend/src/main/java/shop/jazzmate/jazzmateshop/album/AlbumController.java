package shop.jazzmate.jazzmateshop.album;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import shop.jazzmate.jazzmateshop.album.dto.AlbumSearchResponse;

import java.util.List;

@RestController
@RequestMapping("/api/albums")
@RequiredArgsConstructor
@Slf4j
@CrossOrigin(origins = "*")
public class AlbumController {
    
    private final AlbumService albumService;
    
    /**
     * 앨범 검색
     */
    @GetMapping("/search")
    public ResponseEntity<List<AlbumSearchResponse>> searchAlbums(
            @RequestParam String q,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {
        try {
            log.info("앨범 검색 요청: query={}, page={}, size={}", q, page, size);
            
            List<AlbumSearchResponse> albums = albumService.searchAlbums(q, page, size);
            
            return ResponseEntity.ok(albums);
        } catch (Exception e) {
            log.error("앨범 검색 오류: ", e);
            return ResponseEntity.internalServerError().build();
        }
    }
    
    /**
     * 특정 앨범 조회
     */
    @GetMapping("/{id}")
    public ResponseEntity<AlbumSearchResponse> getAlbum(@PathVariable Integer id) {
        try {
            AlbumSearchResponse album = albumService.getAlbum(id);
            return ResponseEntity.ok(album);
        } catch (Exception e) {
            log.error("앨범 조회 오류: ", e);
            return ResponseEntity.notFound().build();
        }
    }
}

package shop.jazzmate.jazzmateshop.userReview;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import shop.jazzmate.jazzmateshop.userReview.entity.Track;

import java.time.LocalDateTime;
import java.util.Optional;

@RestController
@RequestMapping("/api/tracks")
@RequiredArgsConstructor
@Slf4j
public class TrackController {
    
    private final TrackRepository trackRepository;
    
    /**
     * Track 생성 (Python API에서 호출)
     */
    @PostMapping
    public ResponseEntity<Track> createTrack(@RequestBody Track track) {
        try {
            log.info("Track 생성 요청: {} - {}", track.getArtistName(), track.getTrackTitle());
            
            // 기존 Track 확인
            Optional<Track> existingTrack = trackRepository.findByArtistNameAndTrackTitle(
                track.getArtistName(), track.getTrackTitle()
            );
            
            if (existingTrack.isPresent()) {
                log.info("기존 Track 반환: {}", existingTrack.get().getId());
                return ResponseEntity.ok(existingTrack.get());
            }
            
            // 새 Track 생성
            Track newTrack = Track.builder()
                .trackTitle(track.getTrackTitle())
                .artistName(track.getArtistName())
                .genre(track.getGenre())
                .mood(track.getMood())
                .energy(track.getEnergy())
                .bpm(track.getBpm())
                .vocalStyle(track.getVocalStyle())
                .instrumentation(track.getInstrumentation())
                .createdAt(LocalDateTime.now())
                .updatedAt(LocalDateTime.now())
                .build();
            
            Track savedTrack = trackRepository.save(newTrack);
            log.info("새 Track 생성 완료: {}", savedTrack.getId());
            
            return ResponseEntity.ok(savedTrack);
            
        } catch (Exception e) {
            log.error("Track 생성 오류: ", e);
            return ResponseEntity.internalServerError().build();
        }
    }
    
    /**
     * 특정 Track 조회
     */
    @GetMapping("/{id}")
    public ResponseEntity<Track> getTrack(@PathVariable Integer id) {
        try {
            Optional<Track> track = trackRepository.findById(id);
            if (track.isPresent()) {
                return ResponseEntity.ok(track.get());
            } else {
                return ResponseEntity.notFound().build();
            }
        } catch (Exception e) {
            log.error("Track 조회 오류: ", e);
            return ResponseEntity.internalServerError().build();
        }
    }
}

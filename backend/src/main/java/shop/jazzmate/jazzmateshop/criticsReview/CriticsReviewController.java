package shop.jazzmate.jazzmateshop.criticsReview;

import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.web.bind.annotation.RequestParam;

import java.util.List;

@RestController
@RequiredArgsConstructor
@RequestMapping("/api/critics")
public class CriticsReviewController {

    private final CriticsReviewRepository repository;

    @GetMapping
    public Page<CriticsReview> getAll(
        @RequestParam(defaultValue = "0") int page,
        @RequestParam(defaultValue = "20") int size
    ) {
        Pageable pageable = PageRequest.of(page, size);
        return repository.findByReviewSummaryIsNotNull(pageable);
    }
    @GetMapping("/{id}")
    public CriticsReview getById(@PathVariable Integer id) {
        return repository.findById(id).orElseThrow();
    }
}

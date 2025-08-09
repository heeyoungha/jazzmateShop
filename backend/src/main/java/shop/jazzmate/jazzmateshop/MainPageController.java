package shop.jazzmate.jazzmateshop;

import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.bind.annotation.CrossOrigin;
import org.springframework.http.ResponseEntity;
import java.util.*;

@Controller
@RequestMapping("/")
@CrossOrigin(origins = "http://localhost:3000")
public class MainPageController {

     @GetMapping("/main")
    public String mainPage() {
        // 개발 환경에서는 React 개발 서버로 리다이렉트
        return "redirect:http://localhost:3000";
    }
}

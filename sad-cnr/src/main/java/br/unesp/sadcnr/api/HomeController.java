package br.unesp.sadcnr.api;

import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.GetMapping;

@Controller
public class HomeController {

    @GetMapping("/")
    public String index() {
        return "index";
    }

    @GetMapping("/importacao")
    public String importacao() {
        return "importacao";
    }
}

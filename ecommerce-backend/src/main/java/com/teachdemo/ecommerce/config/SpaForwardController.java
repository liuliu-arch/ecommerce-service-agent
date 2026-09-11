package com.teachdemo.ecommerce.config;

import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.GetMapping;

@Controller
public class SpaForwardController {

    @GetMapping({
        "/",
        "/login",
        "/cart",
        "/checkout",
        "/orders",
        "/balance",
        "/policies",
        "/products/{path:[^\\.]*}",
        "/pay/{path:[^\\.]*}",
        "/orders/{path:[^\\.]*}"
    })
    public String shop() {
        return "forward:/index.html";
    }

    @GetMapping({
        "/admin",
        "/admin/",
        "/admin/login",
        "/admin/products",
        "/admin/promotions",
        "/admin/orders",
        "/admin/after-sales",
        "/admin/users"
    })
    public String admin() {
        return "forward:/admin/index.html";
    }
}

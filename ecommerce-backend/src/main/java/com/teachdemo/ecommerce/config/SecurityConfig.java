package com.teachdemo.ecommerce.config;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.teachdemo.ecommerce.dto.ApiResponse;
import com.teachdemo.ecommerce.security.AgentServiceAuthenticationFilter;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.config.annotation.authentication.configuration.AuthenticationConfiguration;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;

@Configuration
@EnableWebSecurity
public class SecurityConfig {

    @Bean
    public SecurityFilterChain securityFilterChain(HttpSecurity http, ObjectMapper objectMapper,
                                                   AgentServiceAuthenticationFilter agentServiceAuthenticationFilter)
        throws Exception {
        http.csrf(csrf -> csrf.disable())
            .sessionManagement(session -> session.sessionCreationPolicy(SessionCreationPolicy.IF_REQUIRED))
            .formLogin(form -> form.disable())
            .httpBasic(basic -> basic.disable())
            .logout(logout -> logout.logoutUrl("/api/auth/logout")
                .logoutSuccessHandler((request, response, authentication) ->
                    writeJson(response, HttpServletResponse.SC_OK, ApiResponse.success(null), objectMapper)))
            .exceptionHandling(exceptions -> exceptions
                .authenticationEntryPoint((request, response, authException) ->
                    writeJson(response, HttpServletResponse.SC_UNAUTHORIZED,
                        ApiResponse.error("UNAUTHORIZED", "请先登录"), objectMapper))
                .accessDeniedHandler((request, response, accessDeniedException) ->
                    writeJson(response, HttpServletResponse.SC_FORBIDDEN,
                        ApiResponse.error("FORBIDDEN", "当前账号无权访问该资源"), objectMapper)))
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/api/auth/login", "/api/auth/logout").permitAll()
                .requestMatchers("/api/auth/me").authenticated()
                // 该路径仅在 course-debug Profile 下注册，不属于通用业务用户接口。
                .requestMatchers("/api/course-debug/**").permitAll()
                .requestMatchers(HttpMethod.POST, "/api/users/demo").permitAll()
                .requestMatchers("/api/refund/requests/**", "/api/after-sale/requests/**")
                .hasAnyRole("USER", "AGENT_SERVICE")
                // 审批决定必须来自管理员入口；Agent 只能提交申请或读取审批状态。
                .requestMatchers(HttpMethod.POST, "/api/approvals/*/approve", "/api/approvals/*/reject")
                .hasRole("ADMIN")
                .requestMatchers(HttpMethod.POST, "/api/approvals").hasRole("AGENT_SERVICE")
                .requestMatchers(HttpMethod.GET, "/api/approvals/*").hasAnyRole("ADMIN", "AGENT_SERVICE")
                .requestMatchers("/api/orders/**").hasAnyRole("USER", "AGENT_SERVICE")
                .requestMatchers("/api/users/*", "/api/users/*/preferences", "/api/users/*/coupons")
                .hasAnyRole("USER", "AGENT_SERVICE")
                .requestMatchers("/api/shop/**", "/api/customer-service/**").hasRole("USER")
                .requestMatchers("/api/admin/**").hasRole("ADMIN")
                .requestMatchers(
                    "/actuator/health", "/actuator/info",
                    "/v3/api-docs/**", "/swagger-ui/**", "/swagger-ui.html", "/doc.html", "/webjars/**")
                .permitAll()
                .anyRequest().permitAll())
            .addFilterBefore(agentServiceAuthenticationFilter, UsernamePasswordAuthenticationFilter.class);
        return http.build();
    }

    @Bean
    public PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder();
    }

    @Bean
    public AuthenticationManager authenticationManager(AuthenticationConfiguration configuration) throws Exception {
        return configuration.getAuthenticationManager();
    }

    private static void writeJson(HttpServletResponse response, int status, ApiResponse<?> body,
                                  ObjectMapper objectMapper) throws java.io.IOException {
        response.setStatus(status);
        response.setCharacterEncoding("UTF-8");
        response.setContentType(MediaType.APPLICATION_JSON_VALUE);
        objectMapper.writeValue(response.getWriter(), body);
    }
}

package com.crea3.pcapp.security;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;

/** /api/** 仅接受携带正确 X-Auth-Token 的请求（监控端发起的上报与拉配置）。 */
@Component
@Order(Ordered.HIGHEST_PRECEDENCE)
public class ApiTokenFilter extends OncePerRequestFilter {

    private final byte[] expectedToken;

    public ApiTokenFilter(@Value("${app.api-token}") String apiToken) {
        this.expectedToken = apiToken.getBytes(StandardCharsets.UTF_8);
    }

    @Override
    protected boolean shouldNotFilter(HttpServletRequest request) {
        return !request.getRequestURI().startsWith("/api/");
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain chain)
            throws ServletException, IOException {
        String supplied = request.getHeader("X-Auth-Token");
        if (supplied != null
                && MessageDigest.isEqual(supplied.getBytes(StandardCharsets.UTF_8), expectedToken)) {
            chain.doFilter(request, response);
            return;
        }
        response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
        response.setContentType("application/json;charset=UTF-8");
        response.getWriter().write("{\"ok\":false,\"error\":\"unauthorized\"}");
    }
}

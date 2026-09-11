package com.teachdemo.ecommerce.config;

import java.time.Duration;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.web.client.RestClient;

@Configuration
@EnableConfigurationProperties(CustomerServiceAgentProperties.class)
public class CustomerServiceAgentConfig {

    @Bean
    public RestClient customerServiceAgentRestClient(CustomerServiceAgentProperties properties,
                                                    RestClient.Builder builder) {
        SimpleClientHttpRequestFactory requestFactory = new SimpleClientHttpRequestFactory();
        requestFactory.setConnectTimeout(Duration.ofMillis(properties.getConnectTimeoutMs()));
        requestFactory.setReadTimeout(Duration.ofMillis(properties.getReadTimeoutMs()));
        return builder
            .baseUrl(properties.getBaseUrl())
            .requestFactory(requestFactory)
            .build();
    }
}

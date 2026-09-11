package com.teachdemo.ecommerce.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.teachdemo.ecommerce.dto.AgentChatRequest;
import com.teachdemo.ecommerce.dto.AgentResumeRequest;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClient;

@Service
public class RestCustomerServiceAgentClient implements CustomerServiceAgentClient {

    private final RestClient customerServiceAgentRestClient;

    public RestCustomerServiceAgentClient(RestClient customerServiceAgentRestClient) {
        this.customerServiceAgentRestClient = customerServiceAgentRestClient;
    }

    @Override
    public JsonNode chat(AgentChatRequest request) {
        return customerServiceAgentRestClient.post()
            .uri("/chat")
            .body(request)
            .retrieve()
            .body(JsonNode.class);
    }

    @Override
    public JsonNode resume(AgentResumeRequest request) {
        return customerServiceAgentRestClient.post()
            .uri("/chat/resume")
            .body(request)
            .retrieve()
            .body(JsonNode.class);
    }
}

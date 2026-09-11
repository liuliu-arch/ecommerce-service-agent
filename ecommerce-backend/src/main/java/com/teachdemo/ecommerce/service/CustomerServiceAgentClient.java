package com.teachdemo.ecommerce.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.teachdemo.ecommerce.dto.AgentChatRequest;
import com.teachdemo.ecommerce.dto.AgentResumeRequest;

public interface CustomerServiceAgentClient {

    JsonNode chat(AgentChatRequest request);

    JsonNode resume(AgentResumeRequest request);
}

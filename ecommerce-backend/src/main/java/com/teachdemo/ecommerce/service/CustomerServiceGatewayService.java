package com.teachdemo.ecommerce.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.MissingNode;
import com.teachdemo.ecommerce.dto.AgentChatRequest;
import com.teachdemo.ecommerce.dto.AgentResumeRequest;
import com.teachdemo.ecommerce.dto.CustomerServiceActionResponse;
import com.teachdemo.ecommerce.dto.CustomerServiceChatRequest;
import com.teachdemo.ecommerce.dto.CustomerServicePageContextRequest;
import com.teachdemo.ecommerce.dto.CustomerServiceResponse;
import com.teachdemo.ecommerce.dto.CustomerServiceResumeRequest;
import com.teachdemo.ecommerce.dto.RuntimeOrderContextResponse;
import com.teachdemo.ecommerce.entity.AfterSaleRequest;
import com.teachdemo.ecommerce.entity.OrderEntity;
import com.teachdemo.ecommerce.entity.UserProfile;
import com.teachdemo.ecommerce.repository.AfterSaleRequestRepository;
import com.teachdemo.ecommerce.repository.OrderRepository;
import com.teachdemo.ecommerce.repository.ProductRepository;
import com.teachdemo.ecommerce.repository.UserProfileRepository;
import com.teachdemo.ecommerce.security.AccountPrincipal;
import com.teachdemo.ecommerce.session.CustomerServiceSession;
import com.teachdemo.ecommerce.session.CustomerServiceSessionStore;
import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

@Service
public class CustomerServiceGatewayService {

    public static final String FALLBACK_ANSWER = "客服服务暂时繁忙，您可以稍后再试，或联系人工客服继续处理。";

    private static final Set<String> PAGE_TYPES = Set.of(
        "HOME", "PRODUCT_DETAIL", "CART", "ORDER_LIST", "ORDER_DETAIL", "BALANCE", "AFTER_SALE");

    private final CustomerServiceAgentClient agentClient;
    private final CustomerServiceSessionStore sessionStore;
    private final UserProfileRepository userProfileRepository;
    private final OrderRepository orderRepository;
    private final AfterSaleRequestRepository afterSaleRequestRepository;
    private final ProductRepository productRepository;
    private final RuntimeOrderContextService runtimeOrderContextService;

    public CustomerServiceGatewayService(CustomerServiceAgentClient agentClient,
                                         CustomerServiceSessionStore sessionStore,
                                         UserProfileRepository userProfileRepository,
                                         OrderRepository orderRepository,
                                         AfterSaleRequestRepository afterSaleRequestRepository,
                                         ProductRepository productRepository,
                                         RuntimeOrderContextService runtimeOrderContextService) {
        this.agentClient = agentClient;
        this.sessionStore = sessionStore;
        this.userProfileRepository = userProfileRepository;
        this.orderRepository = orderRepository;
        this.afterSaleRequestRepository = afterSaleRequestRepository;
        this.productRepository = productRepository;
        this.runtimeOrderContextService = runtimeOrderContextService;
    }

    public CustomerServiceResponse chat(CustomerServiceChatRequest request, AccountPrincipal principal) {
        UserProfile profile = loadProfile(principal);
        CustomerServicePageContextRequest pageContext = normalizeAndValidatePageContext(request.getPageContext(), profile.getUserId());
        String sessionId = StringUtils.hasText(request.getSessionId())
            ? request.getSessionId().trim()
            : "cs-" + UUID.randomUUID();
        CustomerServiceSession session = sessionStore.getOrCreate(sessionId, profile.getUserId());
        assertSessionOwner(session, profile.getUserId());
        AgentChatRequest agentRequest = new AgentChatRequest(
            sessionId,
            profile.getUserId(),
            profile.getNickname(),
            profile.getMemberLevel(),
            profile.getRiskLevel(),
            buildAgentMessage(request.getMessage(), pageContext, profile.getUserId()),
            buildRuntimeContext(profile, pageContext)
        );
        try {
            JsonNode agentResponse = agentClient.chat(agentRequest);
            return sanitizeChatResponse(agentResponse, session, pageContext);
        } catch (RuntimeException ex) {
            sessionStore.save(session);
            return fallback(sessionId);
        }
    }

    public CustomerServiceResponse resume(CustomerServiceResumeRequest request, AccountPrincipal principal) {
        UserProfile profile = loadProfile(principal);
        CustomerServiceSession session = sessionStore.find(request.getSessionId())
            .orElseThrow(() -> new CustomerServiceException(HttpStatus.NOT_FOUND, "NOT_FOUND", "客服会话不存在"));
        assertSessionOwner(session, profile.getUserId());
        validateResumeSession(session, request);
        validateOrderOwnership(session.getRelatedOrderNo(), profile.getUserId());
        validateAfterSaleOwnership(session.getRelatedAfterSaleNo(), profile.getUserId());

        String decision = request.getDecision().trim().toUpperCase(Locale.ROOT);
        if ("CANCEL_SUBMIT".equals(decision)) {
            session.setHandled(true);
            sessionStore.save(session);
            return new CustomerServiceResponse(
                cancelAnswer(session.getActionType()),
                session.getSessionId(),
                false,
                null,
                null,
                null,
                session.getRelatedOrderNo(),
                session.getRelatedAfterSaleNo(),
                null,
                List.of(),
                false
            );
        }
        if (!"CONFIRM_SUBMIT".equals(decision)) {
            throw new CustomerServiceException(HttpStatus.BAD_REQUEST, "BAD_REQUEST", "decision 只支持 CONFIRM_SUBMIT 或 CANCEL_SUBMIT");
        }

        try {
            JsonNode agentResponse = agentClient.resume(new AgentResumeRequest(
                session.getSessionId(),
                session.getWorkflowId(),
                session.getResumeToken(),
                "approved",
                "用户已在电商公司商城客服入口确认提交申请"
            ));
            session.setHandled(true);
            sessionStore.save(session);
            return sanitizeResumeResponse(agentResponse, session);
        } catch (RuntimeException ex) {
            return fallback(session.getSessionId());
        }
    }

    private UserProfile loadProfile(AccountPrincipal principal) {
        return userProfileRepository.findByUserId(principal.getUserId())
            .orElseThrow(() -> new CustomerServiceException(HttpStatus.NOT_FOUND, "NOT_FOUND", "用户资料不存在"));
    }

    private CustomerServicePageContextRequest normalizeAndValidatePageContext(CustomerServicePageContextRequest pageContext,
                                                                             String userId) {
        if (pageContext == null) {
            return null;
        }
        if (StringUtils.hasText(pageContext.getType())) {
            String type = normalizePageType(pageContext.getType());
            if (!PAGE_TYPES.contains(type)) {
                throw new CustomerServiceException(HttpStatus.BAD_REQUEST, "BAD_REQUEST", "页面上下文类型不合法");
            }
            pageContext.setType(type);
        }
        if (pageContext.getProductId() != null && !productRepository.existsById(pageContext.getProductId())) {
            throw new CustomerServiceException(HttpStatus.NOT_FOUND, "NOT_FOUND", "关联商品不存在");
        }
        validateOrderOwnership(pageContext.getOrderNo(), userId);
        validateAfterSaleOwnership(pageContext.getAfterSaleNo(), userId);
        return pageContext;
    }

    private static String normalizePageType(String type) {
        String normalized = type.trim().toUpperCase(Locale.ROOT);
        return switch (normalized) {
            case "PRODUCT" -> "PRODUCT_DETAIL";
            case "ORDER" -> "ORDER_DETAIL";
            default -> normalized;
        };
    }

    private void validateOrderOwnership(String orderNo, String userId) {
        if (!StringUtils.hasText(orderNo)) {
            return;
        }
        OrderEntity order = orderRepository.findByOrderNo(orderNo.trim())
            .orElseThrow(() -> new CustomerServiceException(HttpStatus.NOT_FOUND, "NOT_FOUND", "关联订单不存在"));
        if (!userId.equals(order.getUserId())) {
            throw new CustomerServiceException(HttpStatus.FORBIDDEN, "FORBIDDEN", "关联订单不属于当前用户");
        }
    }

    private void validateAfterSaleOwnership(String afterSaleNo, String userId) {
        if (!StringUtils.hasText(afterSaleNo)) {
            return;
        }
        AfterSaleRequest afterSale = afterSaleRequestRepository.findByRequestId(afterSaleNo.trim())
            .orElseThrow(() -> new CustomerServiceException(HttpStatus.NOT_FOUND, "NOT_FOUND", "关联售后申请不存在"));
        if (!userId.equals(afterSale.getUserId())) {
            throw new CustomerServiceException(HttpStatus.FORBIDDEN, "FORBIDDEN", "关联售后申请不属于当前用户");
        }
    }

    private Map<String, Object> buildRuntimeContext(UserProfile profile, CustomerServicePageContextRequest pageContext) {
        Map<String, Object> context = new HashMap<>();
        context.put("userId", profile.getUserId());
        context.put("nickname", profile.getNickname());
        context.put("mobile", profile.getMobile());
        context.put("memberLevel", profile.getMemberLevel());
        context.put("riskLevel", profile.getRiskLevel());
        RuntimeOrderContextResponse orderContext =
            runtimeOrderContextService.loadCurrentUserOrders(profile.getUserId(), null, null);
        context.put("currentUserOrders", orderContext.orders());
        context.put("currentUserOrdersTruncated", orderContext.truncated());
        if (pageContext != null) {
            context.put("currentPage", pageContext.getType());
            context.put("relatedProductId", pageContext.getProductId());
            context.put("relatedOrderNo", trimToNull(pageContext.getOrderNo()));
            context.put("relatedAfterSaleNo", trimToNull(pageContext.getAfterSaleNo()));
            List<Map<String, String>> needMoreInfoRequests = needMoreInfoRequests(pageContext, profile.getUserId()).stream()
                .map(request -> {
                    Map<String, String> item = new HashMap<>();
                    item.put("requestId", request.getRequestId());
                    item.put("orderNo", request.getOrderNo());
                    item.put("requestType", request.getRequestType());
                    item.put("status", request.getStatus());
                    item.put("handlingNote", request.getHandlingNote());
                    return item;
                })
                .toList();
            if (!needMoreInfoRequests.isEmpty()) {
                context.put("relatedNeedMoreInfoAfterSales", needMoreInfoRequests);
            }
        }
        return context;
    }

    private String buildAgentMessage(String message, CustomerServicePageContextRequest pageContext, String userId) {
        if (pageContext == null) {
            return message;
        }
        StringBuilder builder = new StringBuilder(message).append("\n\n[电商公司商城页面上下文]");
        if (StringUtils.hasText(pageContext.getType())) {
            builder.append(" 当前页面=").append(pageContext.getType()).append(";");
        }
        if (pageContext.getProductId() != null) {
            builder.append(" 关联商品ID=").append(pageContext.getProductId()).append(";");
        }
        if (StringUtils.hasText(pageContext.getOrderNo())) {
            builder.append(" 关联订单号=").append(pageContext.getOrderNo().trim()).append(";");
        }
        if (StringUtils.hasText(pageContext.getAfterSaleNo())) {
            builder.append(" 关联售后申请号=").append(pageContext.getAfterSaleNo().trim()).append(";");
        }
        List<AfterSaleRequest> needMoreInfoRequests = needMoreInfoRequests(pageContext, userId);
        for (AfterSaleRequest request : needMoreInfoRequests) {
            builder.append(" 该订单存在待客户补充材料的售后申请=")
                .append(request.getRequestId())
                .append("; 处理意见=")
                .append(StringUtils.hasText(request.getHandlingNote()) ? request.getHandlingNote() : "需要补充材料")
                .append(";");
        }
        builder.append(" 以上上下文已由电商后端校验归属。");
        return builder.toString();
    }

    private List<AfterSaleRequest> needMoreInfoRequests(CustomerServicePageContextRequest pageContext, String userId) {
        if (pageContext == null || !StringUtils.hasText(pageContext.getOrderNo())) {
            return List.of();
        }
        return afterSaleRequestRepository.findByOrderNo(pageContext.getOrderNo().trim()).stream()
            .filter(request -> !StringUtils.hasText(userId) || userId.equals(request.getUserId()))
            .filter(request -> "NEED_MORE_INFO".equalsIgnoreCase(request.getStatus()))
            .toList();
    }

    private CustomerServiceResponse sanitizeChatResponse(JsonNode agentResponse, CustomerServiceSession session,
                                                         CustomerServicePageContextRequest pageContext) {
        if (agentResponse == null || !agentResponse.hasNonNull("answer")) {
            return fallback(session.getSessionId());
        }
        JsonNode workflow = workflowNode(agentResponse);
        String answer = text(agentResponse, "answer", FALLBACK_ANSWER);
        if (isApprovalRequired(workflow)) {
            String orderNo = firstText(workflow, "order_no", "orderNo");
            if (!StringUtils.hasText(orderNo) && pageContext != null) {
                orderNo = trimToNull(pageContext.getOrderNo());
            }
            String afterSaleNo = pageContext == null ? null : trimToNull(pageContext.getAfterSaleNo());
            String actionType = actionType(workflow);
            session.setWorkflowId(text(workflow, "workflow_id", null));
            session.setResumeToken(text(workflow, "resume_token", null));
            session.setPendingAction("CONFIRM_SUBMIT");
            session.setActionType(actionType);
            session.setRelatedOrderNo(orderNo);
            session.setRelatedAfterSaleNo(afterSaleNo);
            session.setExpiresAt(LocalDateTime.now().plusMinutes(30));
            session.setHandled(false);
            sessionStore.save(session);
            return new CustomerServiceResponse(
                answer,
                session.getSessionId(),
                true,
                "CONFIRM_SUBMIT",
                confirmationTitle(actionType),
                confirmationSummary(actionType, orderNo, text(workflow, "risk_summary", null)),
                orderNo,
                afterSaleNo,
                session.getResumeToken(),
                confirmationActions(),
                false
            );
        }
        session.setPendingAction(null);
        session.setResumeToken(null);
        session.setWorkflowId(null);
        session.setHandled(false);
        sessionStore.save(session);
        return new CustomerServiceResponse(answer, session.getSessionId(), false, null, null, null,
            pageContext == null ? null : trimToNull(pageContext.getOrderNo()),
            pageContext == null ? null : trimToNull(pageContext.getAfterSaleNo()),
            null, List.of(), false);
    }

    private CustomerServiceResponse sanitizeResumeResponse(JsonNode agentResponse, CustomerServiceSession session) {
        if (agentResponse == null) {
            return fallback(session.getSessionId());
        }
        String answer = firstText(agentResponse, "answer", "message");
        if (!StringUtils.hasText(answer)) {
            answer = "已收到您的确认，申请已继续提交处理。";
        }
        return new CustomerServiceResponse(answer, session.getSessionId(), false, null, null, null,
            session.getRelatedOrderNo(), session.getRelatedAfterSaleNo(), null, List.of(), false);
    }

    private void validateResumeSession(CustomerServiceSession session, CustomerServiceResumeRequest request) {
        if (session.isHandled()) {
            throw new CustomerServiceException(HttpStatus.CONFLICT, "CONFLICT", "本次确认已处理，请勿重复提交");
        }
        if (session.isExpired(LocalDateTime.now())) {
            throw new CustomerServiceException(HttpStatus.CONFLICT, "CONFLICT", "本次确认已过期，请重新发起咨询");
        }
        if (!StringUtils.hasText(session.getResumeToken()) || !session.getResumeToken().equals(request.getResumeToken())) {
            throw new CustomerServiceException(HttpStatus.FORBIDDEN, "FORBIDDEN", "恢复凭证不匹配");
        }
        if (StringUtils.hasText(request.getRelatedOrderNo())
            && StringUtils.hasText(session.getRelatedOrderNo())
            && !session.getRelatedOrderNo().equals(request.getRelatedOrderNo())) {
            throw new CustomerServiceException(HttpStatus.FORBIDDEN, "FORBIDDEN", "关联订单不匹配");
        }
        if (!StringUtils.hasText(session.getWorkflowId())) {
            throw new CustomerServiceException(HttpStatus.CONFLICT, "CONFLICT", "当前会话没有待确认申请");
        }
    }

    private void assertSessionOwner(CustomerServiceSession session, String userId) {
        if (!userId.equals(session.getUserId())) {
            throw new CustomerServiceException(HttpStatus.FORBIDDEN, "FORBIDDEN", "客服会话不属于当前用户");
        }
    }

    private CustomerServiceResponse fallback(String sessionId) {
        return new CustomerServiceResponse(FALLBACK_ANSWER, sessionId, false, null, null, null,
            null, null, null, List.of(), true);
    }

    private static JsonNode workflowNode(JsonNode root) {
        JsonNode sessionState = root.path("session_state");
        if (sessionState.has("workflow")) {
            return sessionState.path("workflow");
        }
        if (root.has("workflow")) {
            return root.path("workflow");
        }
        return MissingNode.getInstance();
    }

    private static boolean isApprovalRequired(JsonNode workflow) {
        return workflow != null
            && "paused".equals(text(workflow, "status", null))
            && "require_approval".equals(text(workflow, "pending_action", null))
            && StringUtils.hasText(text(workflow, "resume_token", null))
            && StringUtils.hasText(text(workflow, "workflow_id", null));
    }

    private static String actionType(JsonNode workflow) {
        String workflowType = text(workflow, "workflow_type", "").toLowerCase(Locale.ROOT);
        if (workflowType.contains("return")) {
            return "RETURN";
        }
        if (workflowType.contains("cancel")) {
            return "CANCEL_ORDER";
        }
        if (workflowType.contains("compensation")) {
            return "COMPENSATION";
        }
        return "REFUND";
    }

    private static String actionLabel(String actionType) {
        return switch (String.valueOf(actionType)) {
            case "RETURN" -> "退货";
            case "CANCEL_ORDER" -> "取消订单";
            case "COMPENSATION" -> "申请补偿";
            default -> "退款";
        };
    }

    private static String confirmationTitle(String actionType) {
        return "确认提交" + actionLabel(actionType) + "申请";
    }

    private static String confirmationSummary(String actionType, String orderNo, String riskSummary) {
        String label = actionLabel(actionType);
        StringBuilder summary = new StringBuilder("申请类型：").append(label);
        if (StringUtils.hasText(orderNo)) {
            summary.append("；关联订单：").append(orderNo);
        }
        if (StringUtils.hasText(riskSummary)) {
            summary.append("；说明：").append(riskSummary);
        }
        summary.append("。确认前不会正式提交申请。");
        return summary.toString();
    }

    private static List<CustomerServiceActionResponse> confirmationActions() {
        return List.of(
            new CustomerServiceActionResponse("CONFIRM_SUBMIT", "确认提交申请"),
            new CustomerServiceActionResponse("CANCEL_SUBMIT", "暂不提交")
        );
    }

    private static String cancelAnswer(String actionType) {
        return "确认您暂时不打算" + actionLabel(actionType) + "，本次不会提交申请。后续需要帮助时可以继续告诉我。";
    }

    private static String text(JsonNode node, String field, String defaultValue) {
        if (node == null || !node.hasNonNull(field)) {
            return defaultValue;
        }
        return node.path(field).asText(defaultValue);
    }

    private static String firstText(JsonNode node, String first, String second) {
        String value = text(node, first, null);
        if (StringUtils.hasText(value)) {
            return value;
        }
        return text(node, second, null);
    }

    private static String trimToNull(String value) {
        if (!StringUtils.hasText(value)) {
            return null;
        }
        return value.trim();
    }
}

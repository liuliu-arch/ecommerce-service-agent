package com.teachdemo.ecommerce.service;

import com.teachdemo.ecommerce.dto.AdminAfterSaleResponse;
import com.teachdemo.ecommerce.dto.AdminAfterSaleReviewRequest;
import com.teachdemo.ecommerce.dto.AdminAfterSaleReviewResponse;
import com.teachdemo.ecommerce.dto.ApprovalRecordResponse;
import com.teachdemo.ecommerce.entity.AfterSaleRequest;
import com.teachdemo.ecommerce.entity.ApprovalRecord;
import com.teachdemo.ecommerce.entity.BalanceAccount;
import com.teachdemo.ecommerce.entity.BalanceTransaction;
import com.teachdemo.ecommerce.entity.OrderEntity;
import com.teachdemo.ecommerce.entity.UserProfile;
import com.teachdemo.ecommerce.repository.AfterSaleRequestRepository;
import com.teachdemo.ecommerce.repository.ApprovalRecordRepository;
import com.teachdemo.ecommerce.repository.BalanceAccountRepository;
import com.teachdemo.ecommerce.repository.BalanceTransactionRepository;
import com.teachdemo.ecommerce.repository.OrderRepository;
import com.teachdemo.ecommerce.repository.UserProfileRepository;
import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.Comparator;
import java.util.List;
import java.util.Locale;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;

@Service
public class AdminAfterSaleService {

    private final AfterSaleRequestRepository afterSaleRequestRepository;
    private final ApprovalRecordRepository approvalRecordRepository;
    private final BalanceAccountRepository balanceAccountRepository;
    private final BalanceTransactionRepository balanceTransactionRepository;
    private final OrderRepository orderRepository;
    private final UserProfileRepository userProfileRepository;

    public AdminAfterSaleService(AfterSaleRequestRepository afterSaleRequestRepository,
                                 ApprovalRecordRepository approvalRecordRepository,
                                 BalanceAccountRepository balanceAccountRepository,
                                 BalanceTransactionRepository balanceTransactionRepository,
                                 OrderRepository orderRepository,
                                 UserProfileRepository userProfileRepository) {
        this.afterSaleRequestRepository = afterSaleRequestRepository;
        this.approvalRecordRepository = approvalRecordRepository;
        this.balanceAccountRepository = balanceAccountRepository;
        this.balanceTransactionRepository = balanceTransactionRepository;
        this.orderRepository = orderRepository;
        this.userProfileRepository = userProfileRepository;
    }

    public List<AdminAfterSaleResponse> list(String requestNo, String orderNo, String userId, String type, String status) {
        return afterSaleRequestRepository.findAll().stream()
            .filter(request -> !StringUtils.hasText(requestNo) || request.getRequestId().contains(requestNo))
            .filter(request -> !StringUtils.hasText(orderNo) || orderNo.equals(request.getOrderNo()))
            .filter(request -> !StringUtils.hasText(userId) || userId.equals(request.getUserId()))
            .filter(request -> !StringUtils.hasText(type) || normalize(type).equals(normalize(request.getRequestType())))
            .filter(request -> !StringUtils.hasText(status) || normalize(status).equals(normalize(request.getStatus())))
            .sorted(Comparator.comparing(AfterSaleRequest::getCreatedAt, Comparator.nullsLast(Comparator.naturalOrder())).reversed())
            .map(this::toResponse)
            .toList();
    }

    public AdminAfterSaleResponse get(String requestNo) {
        return toResponse(findRequest(requestNo));
    }

    @Transactional
    public AdminAfterSaleReviewResponse approve(String requestNo, AdminAfterSaleReviewRequest request,
                                                String reviewerUsername) {
        AfterSaleRequest afterSale = findRequest(requestNo);
        assertReviewable(afterSale);
        LocalDateTime now = LocalDateTime.now();
        BigDecimal amount = approvedAmount(afterSale, request);
        String approvalNo = nextApprovalNo();
        BalanceTransaction transaction = null;
        String transactionType = balanceTransactionType(afterSale.getRequestType());
        if (transactionType != null && amount.compareTo(BigDecimal.ZERO) > 0) {
            transaction = creditBalance(afterSale, transactionType, amount, now);
        }
        ApprovalRecord record = approvalRecordRepository.save(new ApprovalRecord(approvalNo, "AFTER_SALE",
            afterSale.getRequestId(), "APPROVED", reviewerUsername, noteOrDefault(request.getReviewNote(), "审批通过"),
            now, now));
        afterSale.updateReview("APPROVED", record.getApprovalNo(), record.getReviewNote(), now);
        return new AdminAfterSaleReviewResponse(afterSale.getRequestId(), afterSale.getStatus(), record.getApprovalNo(),
            transaction == null ? null : transaction.getTransactionNo(), amount, reviewerUsername, now);
    }

    @Transactional
    public AdminAfterSaleReviewResponse reject(String requestNo, AdminAfterSaleReviewRequest request,
                                               String reviewerUsername) {
        return reviewWithoutBalance(requestNo, request, reviewerUsername, "REJECTED", "审批拒绝");
    }

    @Transactional
    public AdminAfterSaleReviewResponse needMoreInfo(String requestNo, AdminAfterSaleReviewRequest request,
                                                     String reviewerUsername) {
        return reviewWithoutBalance(requestNo, request, reviewerUsername, "NEED_MORE_INFO", "需要补充材料");
    }

    private AdminAfterSaleReviewResponse reviewWithoutBalance(String requestNo, AdminAfterSaleReviewRequest request,
                                                              String reviewerUsername, String status,
                                                              String defaultNote) {
        AfterSaleRequest afterSale = findRequest(requestNo);
        assertReviewable(afterSale);
        LocalDateTime now = LocalDateTime.now();
        ApprovalRecord record = approvalRecordRepository.save(new ApprovalRecord(nextApprovalNo(), "AFTER_SALE",
            afterSale.getRequestId(), status, reviewerUsername, noteOrDefault(request.getReviewNote(), defaultNote),
            now, now));
        afterSale.updateReview(status, record.getApprovalNo(), record.getReviewNote(), now);
        return new AdminAfterSaleReviewResponse(afterSale.getRequestId(), afterSale.getStatus(), record.getApprovalNo(),
            null, BigDecimal.ZERO, reviewerUsername, now);
    }

    private BalanceTransaction creditBalance(AfterSaleRequest afterSale, String type, BigDecimal amount, LocalDateTime now) {
        balanceTransactionRepository.findByAfterSaleNo(afterSale.getRequestId()).ifPresent(transaction -> {
            throw BusinessException.conflict("AFTER_SALE_ALREADY_REVIEWED", "售后申请已入账，不能重复审批");
        });
        BalanceAccount account = balanceAccountRepository.findByUserId(afterSale.getUserId())
            .orElseThrow(() -> BusinessException.notFound("BALANCE_ACCOUNT_NOT_FOUND", "余额账户不存在"));
        BigDecimal before = account.getAvailableBalance();
        BigDecimal after = before.add(amount);
        account.updateBalance(after, now);
        return balanceTransactionRepository.save(new BalanceTransaction("BT-AS-" + afterSale.getRequestId(),
            afterSale.getUserId(), afterSale.getOrderNo(), afterSale.getRequestId(), type, amount, before, after,
            type + " 审批入账：" + afterSale.getRequestId(), now));
    }

    private BigDecimal approvedAmount(AfterSaleRequest afterSale, AdminAfterSaleReviewRequest request) {
        BigDecimal amount = request.getApprovedAmount() != null ? request.getApprovedAmount() : afterSale.getAmount();
        if (amount == null && isCancelOrder(afterSale.getRequestType())) {
            amount = orderRepository.findByOrderNo(afterSale.getOrderNo()).map(OrderEntity::getTotalAmount).orElse(BigDecimal.ZERO);
        }
        if (amount == null) {
            amount = BigDecimal.ZERO;
        }
        if (amount.compareTo(BigDecimal.ZERO) < 0) {
            throw BusinessException.badRequest("AFTER_SALE_AMOUNT_INVALID", "审批金额不能小于 0");
        }
        return amount;
    }

    private String balanceTransactionType(String requestType) {
        String normalized = normalize(requestType);
        if ("REFUND".equals(normalized) || "CANCEL_ORDER".equals(normalized)) {
            return "REFUND";
        }
        if ("COMPENSATION".equals(normalized)) {
            return "COMPENSATION";
        }
        return null;
    }

    private boolean isCancelOrder(String requestType) {
        return "CANCEL_ORDER".equals(normalize(requestType));
    }

    private void assertReviewable(AfterSaleRequest request) {
        String status = normalize(request.getStatus());
        if ("APPROVED".equals(status) || "REJECTED".equals(status) || "CANCELED".equals(status)) {
            throw BusinessException.conflict("AFTER_SALE_ALREADY_REVIEWED", "售后申请已审批，不能重复处理");
        }
    }

    private String nextApprovalNo() {
        return "AR-" + (1000 + approvalRecordRepository.count() + 1);
    }

    private String noteOrDefault(String note, String defaultNote) {
        return StringUtils.hasText(note) ? note : defaultNote;
    }

    private AfterSaleRequest findRequest(String requestNo) {
        return afterSaleRequestRepository.findByRequestId(requestNo)
            .orElseThrow(() -> BusinessException.notFound("AFTER_SALE_NOT_FOUND", "售后申请不存在"));
    }

    private AdminAfterSaleResponse toResponse(AfterSaleRequest request) {
        UserProfile user = userProfileRepository.findByUserId(request.getUserId()).orElse(null);
        List<ApprovalRecordResponse> records = approvalRecordRepository.findByTargetNoOrderByCreatedAtDesc(request.getRequestId()).stream()
            .map(this::toRecordResponse)
            .toList();
        BigDecimal preview = balanceTransactionType(request.getRequestType()) == null
            ? BigDecimal.ZERO : (request.getAmount() == null ? BigDecimal.ZERO : request.getAmount());
        return new AdminAfterSaleResponse(request.getRequestId(), request.getOrderNo(), request.getUserId(),
            user == null ? null : user.getNickname(), request.getRequestType(), request.getStatus(),
            request.getAmount(), request.getReason(), request.getHandlingNote(), records, preview,
            request.getCreatedAt(), request.getUpdatedAt());
    }

    private ApprovalRecordResponse toRecordResponse(ApprovalRecord record) {
        return new ApprovalRecordResponse(record.getApprovalNo(), record.getTargetType(), record.getTargetNo(),
            record.getStatus(), record.getReviewerUsername(), record.getReviewNote(), record.getCreatedAt(),
            record.getReviewedAt());
    }

    private String normalize(String value) {
        return value == null ? "" : value.toUpperCase(Locale.ROOT);
    }
}

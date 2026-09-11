package com.teachdemo.ecommerce.service;

import com.teachdemo.ecommerce.dto.BalanceResponse;
import com.teachdemo.ecommerce.dto.BalanceTransactionResponse;
import com.teachdemo.ecommerce.dto.CartItemRequest;
import com.teachdemo.ecommerce.dto.CartItemResponse;
import com.teachdemo.ecommerce.dto.CartItemUpdateRequest;
import com.teachdemo.ecommerce.dto.CartResponse;
import com.teachdemo.ecommerce.dto.CreateOrderRequest;
import com.teachdemo.ecommerce.dto.PaymentResponse;
import com.teachdemo.ecommerce.dto.ProductPromotionResponse;
import com.teachdemo.ecommerce.dto.ShopAfterSaleCreateRequest;
import com.teachdemo.ecommerce.dto.ShopAfterSaleResponse;
import com.teachdemo.ecommerce.dto.ShopOrderItemResponse;
import com.teachdemo.ecommerce.dto.ShopOrderResponse;
import com.teachdemo.ecommerce.dto.ShopProductResponse;
import com.teachdemo.ecommerce.entity.AfterSaleRequest;
import com.teachdemo.ecommerce.entity.BalanceAccount;
import com.teachdemo.ecommerce.entity.BalanceTransaction;
import com.teachdemo.ecommerce.entity.CartItem;
import com.teachdemo.ecommerce.entity.OrderEntity;
import com.teachdemo.ecommerce.entity.OrderItem;
import com.teachdemo.ecommerce.entity.Product;
import com.teachdemo.ecommerce.entity.ProductPromotion;
import com.teachdemo.ecommerce.entity.UserProfile;
import com.teachdemo.ecommerce.repository.AfterSaleRequestRepository;
import com.teachdemo.ecommerce.repository.BalanceAccountRepository;
import com.teachdemo.ecommerce.repository.BalanceTransactionRepository;
import com.teachdemo.ecommerce.repository.CartItemRepository;
import com.teachdemo.ecommerce.repository.OrderItemRepository;
import com.teachdemo.ecommerce.repository.OrderRepository;
import com.teachdemo.ecommerce.repository.ProductRepository;
import com.teachdemo.ecommerce.repository.ProductPromotionRepository;
import com.teachdemo.ecommerce.repository.UserProfileRepository;
import java.math.BigDecimal;
import java.time.Clock;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.Comparator;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.function.Function;
import java.util.stream.Collectors;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;

@Service
public class ShopService {

    private static final Set<String> AFTER_SALE_TYPES = Set.of("REFUND", "RETURN", "COMPENSATION", "CANCEL_ORDER");

    private final ProductRepository productRepository;
    private final CartItemRepository cartItemRepository;
    private final OrderRepository orderRepository;
    private final OrderItemRepository orderItemRepository;
    private final BalanceAccountRepository balanceAccountRepository;
    private final BalanceTransactionRepository balanceTransactionRepository;
    private final AfterSaleRequestRepository afterSaleRequestRepository;
    private final UserProfileRepository userProfileRepository;
    private final ProductPromotionRepository productPromotionRepository;
    private final Clock clock;

    public ShopService(ProductRepository productRepository,
                       CartItemRepository cartItemRepository,
                       OrderRepository orderRepository,
                       OrderItemRepository orderItemRepository,
                       BalanceAccountRepository balanceAccountRepository,
                       BalanceTransactionRepository balanceTransactionRepository,
                       AfterSaleRequestRepository afterSaleRequestRepository,
                       UserProfileRepository userProfileRepository,
                       ProductPromotionRepository productPromotionRepository,
                       Clock clock) {
        this.productRepository = productRepository;
        this.cartItemRepository = cartItemRepository;
        this.orderRepository = orderRepository;
        this.orderItemRepository = orderItemRepository;
        this.balanceAccountRepository = balanceAccountRepository;
        this.balanceTransactionRepository = balanceTransactionRepository;
        this.afterSaleRequestRepository = afterSaleRequestRepository;
        this.userProfileRepository = userProfileRepository;
        this.productPromotionRepository = productPromotionRepository;
        this.clock = clock;
    }

    public List<ShopProductResponse> listProducts(String keyword, String category) {
        List<Product> products = productRepository.findAll().stream()
            .filter(product -> Boolean.TRUE.equals(product.getActive()))
            .filter(product -> !StringUtils.hasText(keyword)
                || contains(product.getName(), keyword)
                || contains(product.getDescription(), keyword))
            .filter(product -> !StringUtils.hasText(category) || category.equals(product.getCategory()))
            .collect(Collectors.toList());
        Map<Long, ProductPromotion> promotions = activePromotions(products);
        return products.stream()
            .map(product -> toProductResponse(product, promotions.get(product.getId())))
            .collect(Collectors.toList());
    }

    public ShopProductResponse getProduct(Long productId) {
        Product product = findOnSaleProduct(productId);
        ProductPromotion promotion = activePromotions(List.of(product)).get(product.getId());
        return toProductResponse(product, promotion);
    }

    public CartResponse getCart(String userId) {
        List<CartItem> cartItems = cartItemRepository.findByUserId(userId);
        Map<Long, Product> products = productsById(cartItems.stream().map(CartItem::getProductId).collect(Collectors.toList()));
        Map<Long, ProductPromotion> promotions = activePromotions(products.values().stream().toList());
        UserProfile profile = userProfileRepository.findByUserId(userId)
            .orElseThrow(() -> BusinessException.notFound("USER_NOT_FOUND", "用户不存在"));
        List<CartItemResponse> items = cartItems.stream()
            .sorted(Comparator.comparing(CartItem::getId))
            .map(item -> toCartItemResponse(item, products.get(item.getProductId()), promotions.get(item.getProductId()), profile))
            .collect(Collectors.toList());
        BigDecimal selectedTotal = items.stream()
            .filter(item -> Boolean.TRUE.equals(item.selected()) && Boolean.TRUE.equals(item.settlementAvailable()))
            .map(item -> item.unitPrice().multiply(BigDecimal.valueOf(item.quantity())))
            .reduce(BigDecimal.ZERO, BigDecimal::add);
        int selectedCount = items.stream()
            .filter(item -> Boolean.TRUE.equals(item.selected()) && Boolean.TRUE.equals(item.settlementAvailable()))
            .mapToInt(CartItemResponse::quantity)
            .sum();
        return new CartResponse(items, selectedTotal, selectedCount);
    }

    @Transactional
    public CartResponse addCartItem(String userId, CartItemRequest request) {
        Product product = findOnSaleProduct(request.productId());
        int quantity = positiveQuantity(request.quantity());
        CartItem item = cartItemRepository.findByUserIdAndProductId(userId, request.productId())
            .map(existing -> {
                int mergedQuantity = existing.getQuantity() + quantity;
                ensureStock(product, mergedQuantity);
                existing.update(mergedQuantity, request.selected() == null ? existing.getSelected() : request.selected(), LocalDateTime.now());
                return existing;
            })
            .orElseGet(() -> {
                ensureStock(product, quantity);
                return new CartItem(userId, request.productId(), quantity,
                    request.selected() == null || request.selected(), LocalDateTime.now(), LocalDateTime.now());
            });
        cartItemRepository.save(item);
        return getCart(userId);
    }

    @Transactional
    public CartResponse updateCartItem(String userId, Long itemId, CartItemUpdateRequest request) {
        CartItem item = cartItemRepository.findByIdAndUserId(itemId, userId)
            .orElseThrow(() -> BusinessException.notFound("CART_ITEM_NOT_FOUND", "购物车项不存在"));
        Product product = productRepository.findById(item.getProductId())
            .orElseThrow(() -> BusinessException.notFound("PRODUCT_NOT_FOUND", "商品不存在"));
        if (!Boolean.TRUE.equals(product.getActive()) && request.quantity() != null && request.quantity() > item.getQuantity()) {
            throw BusinessException.badRequest("PRODUCT_NOT_ON_SALE", "商品已下架，不能继续增加数量");
        }
        if (request.quantity() != null) {
            ensureStock(product, positiveQuantity(request.quantity()));
        }
        item.update(request.quantity(), request.selected(), LocalDateTime.now());
        cartItemRepository.save(item);
        return getCart(userId);
    }

    @Transactional
    public void deleteCartItem(String userId, Long itemId) {
        cartItemRepository.findByIdAndUserId(itemId, userId).ifPresent(cartItemRepository::delete);
    }

    @Transactional
    public ShopOrderResponse createOrder(String userId, CreateOrderRequest request) {
        List<OrderLineDraft> drafts = buildOrderDrafts(userId, request);
        if (drafts.isEmpty()) {
            throw BusinessException.badRequest("ORDER_EMPTY", "订单商品不能为空");
        }
        drafts.forEach(draft -> {
            ensureOnSale(draft.product());
            ensureStock(draft.product(), draft.quantity());
        });
        UserProfile profile = userProfileRepository.findByUserId(userId)
            .orElseThrow(() -> BusinessException.notFound("USER_NOT_FOUND", "用户不存在"));
        Map<Long, ProductPromotion> promotions = activePromotions(drafts.stream()
            .map(OrderLineDraft::product)
            .collect(Collectors.toList()));

        BigDecimal totalAmount = drafts.stream()
            .map(draft -> currentUnitPrice(draft.product(), promotions.get(draft.product().getId()), profile)
                .multiply(BigDecimal.valueOf(draft.quantity())))
            .reduce(BigDecimal.ZERO, BigDecimal::add);
        LocalDateTime now = LocalDateTime.now(clock);
        OrderEntity order = orderRepository.save(new OrderEntity(
            nextOrderNo(), profile.getNickname(), "PENDING_PAYMENT", "UNPAID",
            totalAmount, now, userId, false, true, request.remark()));
        drafts.forEach(draft -> {
            // 下单扣库存是电商主应用的权威数据源，后续 Agent 只能读取结果，不能绕过这里直接改库存。
            draft.product().decreaseStock(draft.quantity());
            productRepository.save(draft.product());
            BigDecimal unitPrice = currentUnitPrice(draft.product(), promotions.get(draft.product().getId()), profile);
            orderItemRepository.save(new OrderItem(order, draft.product().getId(), draft.product().getName(),
                draft.quantity(), unitPrice));
        });
        if ("CART".equalsIgnoreCase(request.source()) && request.cartItemIds() != null) {
            cartItemRepository.deleteAllById(request.cartItemIds());
        }
        return toOrderResponse(order);
    }

    public List<ShopOrderResponse> listOrders(String userId, String status) {
        List<OrderEntity> orders = StringUtils.hasText(status)
            ? orderRepository.findByUserIdAndStatusOrderByCreatedAtDesc(userId, status)
            : orderRepository.findByUserIdOrderByCreatedAtDesc(userId);
        return orders.stream().map(this::toOrderResponse).collect(Collectors.toList());
    }

    public ShopOrderResponse getOrder(String userId, String orderNo) {
        OrderEntity order = findOwnOrder(userId, orderNo);
        return toOrderResponse(order);
    }

    @Transactional
    public PaymentResponse pay(String userId, String orderNo) {
        OrderEntity order = findOwnOrder(userId, orderNo);
        if ("PAID".equals(order.getPaymentStatus())) {
            throw BusinessException.badRequest("ORDER_ALREADY_PAID", "订单已支付，不能重复支付");
        }
        if (!"PENDING_PAYMENT".equals(order.getStatus())) {
            throw BusinessException.badRequest("ORDER_STATUS_INVALID", "当前订单状态不能支付");
        }
        BalanceAccount account = balanceAccountRepository.findByUserId(userId)
            .orElseThrow(() -> BusinessException.notFound("BALANCE_ACCOUNT_NOT_FOUND", "余额账户不存在"));
        BigDecimal balanceBefore = account.getAvailableBalance();
        BigDecimal paidAmount = order.getTotalAmount();
        if (balanceBefore.compareTo(paidAmount) < 0) {
            throw BusinessException.badRequest("BALANCE_NOT_ENOUGH", "余额不足，无法完成支付");
        }
        BigDecimal balanceAfter = balanceBefore.subtract(paidAmount);
        LocalDateTime now = LocalDateTime.now(clock);
        account.updateBalance(balanceAfter, now);
        order.markPaid(now);
        String transactionNo = nextTransactionNo();
        balanceTransactionRepository.save(new BalanceTransaction(
            transactionNo, userId, orderNo, null, "PAYMENT", paidAmount.negate(),
            balanceBefore, balanceAfter, "模拟余额支付订单 " + orderNo, now));
        return new PaymentResponse(orderNo, order.getStatus(), order.getPaymentStatus(), paidAmount,
            balanceBefore, balanceAfter, transactionNo, now);
    }

    public BalanceResponse getBalance(String userId) {
        BalanceAccount account = balanceAccountRepository.findByUserId(userId)
            .orElseThrow(() -> BusinessException.notFound("BALANCE_ACCOUNT_NOT_FOUND", "余额账户不存在"));
        return new BalanceResponse(userId, account.getAvailableBalance(), account.getUpdatedAt());
    }

    public List<BalanceTransactionResponse> listBalanceTransactions(String userId, String type) {
        List<BalanceTransaction> transactions = StringUtils.hasText(type)
            ? balanceTransactionRepository.findByUserIdAndTypeOrderByCreatedAtDesc(userId, type)
            : balanceTransactionRepository.findByUserIdOrderByCreatedAtDesc(userId);
        return transactions.stream().map(transaction -> new BalanceTransactionResponse(
            transaction.getTransactionNo(), transaction.getType(), transaction.getAmount(),
            transaction.getBalanceBefore(), transaction.getBalanceAfter(), transaction.getOrderNo(),
            transaction.getAfterSaleNo(), transaction.getRemark(), transaction.getCreatedAt()
        )).collect(Collectors.toList());
    }

    @Transactional
    public ShopAfterSaleResponse createAfterSale(String userId, ShopAfterSaleCreateRequest request) {
        OrderEntity order = findOwnOrder(userId, request.orderNo());
        String type = request.type().toUpperCase();
        if (!AFTER_SALE_TYPES.contains(type)) {
            throw BusinessException.badRequest("AFTER_SALE_NOT_ALLOWED", "售后类型不支持");
        }
        validateAfterSale(order, type, request.amount());
        if (afterSaleRequestRepository.existsByOrderNoAndUserIdAndRequestTypeAndStatus(
            request.orderNo(), userId, type, "PENDING_REVIEW")) {
            throw BusinessException.badRequest("AFTER_SALE_DUPLICATED", "同一订单同一类型已有待审批申请");
        }
        LocalDateTime now = LocalDateTime.now();
        AfterSaleRequest entity = new AfterSaleRequest(
            nextAfterSaleNo(), request.orderNo(), userId, type, request.reason(),
            "PENDING_REVIEW", request.amount(), true, now, now, "售后申请已提交，等待电商公司客服审核。");
        afterSaleRequestRepository.save(entity);
        order.markAfterSaleRequested();
        return toAfterSaleResponse(entity);
    }

    public List<ShopAfterSaleResponse> listAfterSales(String userId) {
        return afterSaleRequestRepository.findByUserId(userId).stream()
            .sorted(Comparator.comparing(AfterSaleRequest::getCreatedAt).reversed())
            .map(this::toAfterSaleResponse)
            .collect(Collectors.toList());
    }

    private List<OrderLineDraft> buildOrderDrafts(String userId, CreateOrderRequest request) {
        if ("DIRECT_BUY".equalsIgnoreCase(request.source())) {
            Product product = productRepository.findById(request.productId())
                .orElseThrow(() -> BusinessException.notFound("PRODUCT_NOT_FOUND", "商品不存在"));
            return List.of(new OrderLineDraft(product, positiveQuantity(request.quantity())));
        }
        List<CartItem> cartItems;
        if (request.cartItemIds() == null || request.cartItemIds().isEmpty()) {
            cartItems = cartItemRepository.findByUserId(userId).stream()
                .filter(item -> Boolean.TRUE.equals(item.getSelected()))
                .collect(Collectors.toList());
        } else {
            cartItems = cartItemRepository.findByIdInAndUserId(request.cartItemIds(), userId);
            if (cartItems.size() != new LinkedHashSet<>(request.cartItemIds()).size()) {
                throw BusinessException.notFound("CART_ITEM_NOT_FOUND", "购物车项不存在");
            }
        }
        Map<Long, Product> products = productsById(cartItems.stream().map(CartItem::getProductId).collect(Collectors.toList()));
        return cartItems.stream()
            .map(item -> new OrderLineDraft(products.get(item.getProductId()), item.getQuantity()))
            .collect(Collectors.toList());
    }

    private Map<Long, ProductPromotion> activePromotions(List<Product> products) {
        List<Long> productIds = products.stream().map(Product::getId).collect(Collectors.toList());
        if (productIds.isEmpty()) {
            return Map.of();
        }
        LocalDateTime now = LocalDateTime.now(clock);
        return productPromotionRepository.findByProductIdInAndActiveTrue(productIds).stream()
            .filter(promotion -> promotionEffectiveAt(promotion, now))
            .collect(Collectors.toMap(ProductPromotion::getProductId, Function.identity(),
                (left, right) -> left.getId() > right.getId() ? left : right));
    }

    private boolean promotionEffectiveAt(ProductPromotion promotion, LocalDateTime now) {
        return (promotion.getStartAt() == null || !promotion.getStartAt().isAfter(now))
            && (promotion.getEndAt() == null || !promotion.getEndAt().isBefore(now));
    }

    private ShopProductResponse toProductResponse(Product product, ProductPromotion promotion) {
        return new ShopProductResponse(product.getId(), product.getName(), product.getCategory(), product.getDescription(),
            product.getPrice(), product.getStock(), product.getImageUrl(), product.getReturnable(), product.getAfterSaleLimit(),
            Boolean.TRUE.equals(product.getActive()) && product.getStock() != null && product.getStock() > 0,
            promotion == null ? null : toPromotionResponse(promotion));
    }

    private ProductPromotionResponse toPromotionResponse(ProductPromotion promotion) {
        return new ProductPromotionResponse(
            promotion.getId(),
            promotion.getPromotionName(),
            promotion.getPromotionType(),
            promotion.getDiscountSummary(),
            promotion.getPromotionPrice(),
            promotion.getRequiredMemberLevel(),
            promotion.getConditionSummary(),
            promotion.getStartAt(),
            promotion.getEndAt()
        );
    }

    private CartItemResponse toCartItemResponse(CartItem item, Product product, ProductPromotion promotion, UserProfile profile) {
        if (product == null) {
            return new CartItemResponse(item.getId(), item.getProductId(), "商品不存在", null,
                BigDecimal.ZERO, BigDecimal.ZERO, null, null, false, null,
                item.getQuantity(), item.getSelected(), 0, "NOT_FOUND", false, "商品不存在");
        }
        boolean onSale = Boolean.TRUE.equals(product.getActive());
        boolean stockEnough = product.getStock() != null && product.getStock() >= item.getQuantity();
        String reason = onSale ? (stockEnough ? null : "库存不足") : "商品已下架";
        boolean promotionApplied = promotionEligible(promotion, profile);
        BigDecimal unitPrice = currentUnitPrice(product, promotion, profile);
        return new CartItemResponse(item.getId(), product.getId(), product.getName(), product.getImageUrl(),
            product.getPrice(), unitPrice, promotion == null ? null : promotion.getPromotionPrice(),
            promotion == null ? null : promotion.getPromotionName(), promotionApplied,
            promotion == null ? null : promotionConditionText(promotion, profile, promotionApplied),
            item.getQuantity(), item.getSelected(), product.getStock(), onSale ? "ON_SALE" : "OFF_SALE",
            onSale && stockEnough, reason);
    }

    private BigDecimal currentUnitPrice(Product product, ProductPromotion promotion, UserProfile profile) {
        if (promotion != null && promotion.getPromotionPrice() != null
            && promotion.getPromotionPrice().compareTo(BigDecimal.ZERO) > 0
            && promotionEligible(promotion, profile)) {
            // 促销价属于“当前用户 + 商品 + 活动条件”的实时结算事实，不能只凭商品有活动就直接降价。
            return promotion.getPromotionPrice();
        }
        return product.getPrice();
    }

    private boolean promotionEligible(ProductPromotion promotion, UserProfile profile) {
        if (promotion == null || promotion.getPromotionPrice() == null
            || promotion.getPromotionPrice().compareTo(BigDecimal.ZERO) <= 0) {
            return false;
        }
        if (!StringUtils.hasText(promotion.getRequiredMemberLevel())) {
            return true;
        }
        return memberRank(profile.getMemberLevel()) >= memberRank(promotion.getRequiredMemberLevel());
    }

    private String promotionConditionText(ProductPromotion promotion, UserProfile profile, boolean promotionApplied) {
        String condition = StringUtils.hasText(promotion.getConditionSummary())
            ? promotion.getConditionSummary()
            : "满足活动条件后可用";
        if (promotionApplied) {
            return "已满足：" + condition;
        }
        if (StringUtils.hasText(promotion.getRequiredMemberLevel())) {
            return "未满足：" + condition + "，当前为" + memberLevelLabel(profile.getMemberLevel());
        }
        return condition;
    }

    private int memberRank(String memberLevel) {
        if ("gold".equalsIgnoreCase(memberLevel)) {
            return 3;
        }
        if ("silver".equalsIgnoreCase(memberLevel)) {
            return 2;
        }
        if ("normal".equalsIgnoreCase(memberLevel)) {
            return 1;
        }
        return 0;
    }

    private String memberLevelLabel(String memberLevel) {
        if ("gold".equalsIgnoreCase(memberLevel)) {
            return "金卡会员";
        }
        if ("silver".equalsIgnoreCase(memberLevel)) {
            return "银卡会员";
        }
        if ("normal".equalsIgnoreCase(memberLevel)) {
            return "普通会员";
        }
        return "未识别会员等级";
    }

    private ShopOrderResponse toOrderResponse(OrderEntity order) {
        List<ShopOrderItemResponse> items = orderItemRepository.findByOrderEntity(order).stream()
            .map(item -> new ShopOrderItemResponse(item.getProductId(), item.getProductName(), productImageUrl(item.getProductId()),
                item.getUnitPrice(), item.getQuantity()))
            .collect(Collectors.toList());
        String itemSummary = items.stream()
            .map(item -> item.productName() + " x" + item.quantity())
            .collect(Collectors.joining("，"));
        List<String> afterSaleTypes = availableAfterSaleTypes(order);
        return new ShopOrderResponse(order.getOrderNo(), order.getStatus(), order.getPaymentStatus(),
            order.getFulfillmentStatus(), order.getTotalAmount(), itemSummary, order.getRemark(),
            order.getLogisticsNo(), items, !afterSaleTypes.isEmpty(), afterSaleTypes, order.getCreatedAt(),
            order.getPaidAt(), order.getShippedAt(), order.getDeliveredAt(), null);
    }

    private ShopAfterSaleResponse toAfterSaleResponse(AfterSaleRequest request) {
        return new ShopAfterSaleResponse(request.getRequestId(), request.getOrderNo(), request.getRequestType(),
            request.getStatus(), request.getAmount(), request.getReason(), request.getCreatedAt());
    }

    private Product findOnSaleProduct(Long productId) {
        Product product = productRepository.findById(productId)
            .orElseThrow(() -> BusinessException.notFound("PRODUCT_NOT_FOUND", "商品不存在"));
        ensureOnSale(product);
        return product;
    }

    private OrderEntity findOwnOrder(String userId, String orderNo) {
        return orderRepository.findByOrderNoAndUserId(orderNo, userId)
            .orElseThrow(() -> BusinessException.notFound("ORDER_NOT_FOUND", "订单不存在"));
    }

    private void ensureOnSale(Product product) {
        if (!Boolean.TRUE.equals(product.getActive())) {
            throw BusinessException.notFound("PRODUCT_NOT_ON_SALE", "商品不存在或已下架");
        }
    }

    private void ensureStock(Product product, int quantity) {
        if (product.getStock() == null || product.getStock() < quantity) {
            throw BusinessException.badRequest("STOCK_NOT_ENOUGH", "商品库存不足");
        }
    }

    private int positiveQuantity(Integer quantity) {
        if (quantity == null || quantity <= 0) {
            throw BusinessException.badRequest("QUANTITY_INVALID", "数量必须大于 0");
        }
        return quantity;
    }

    private void validateAfterSale(OrderEntity order, String type, BigDecimal amount) {
        if (amount == null || amount.compareTo(BigDecimal.ZERO) <= 0) {
            throw BusinessException.badRequest("AFTER_SALE_NOT_ALLOWED", "售后金额必须大于 0");
        }
        if ("COMPENSATION".equals(type)) {
            if (!"PAID".equals(order.getPaymentStatus()) || amount.compareTo(new BigDecimal("100.00")) > 0) {
                throw BusinessException.badRequest("AFTER_SALE_NOT_ALLOWED", "当前订单不满足补偿申请条件");
            }
            return;
        }
        if ("CANCEL_ORDER".equals(type)) {
            if (!"PENDING_PAYMENT".equals(order.getStatus()) && !"PAID_PENDING_SHIPMENT".equals(order.getStatus())) {
                throw BusinessException.badRequest("AFTER_SALE_NOT_ALLOWED", "当前订单不能申请取消");
            }
        } else if (!"PAID".equals(order.getPaymentStatus())) {
            throw BusinessException.badRequest("AFTER_SALE_NOT_ALLOWED", "当前订单未支付，不能申请该售后类型");
        }
        if (amount.compareTo(order.getTotalAmount()) > 0) {
            throw BusinessException.badRequest("AFTER_SALE_NOT_ALLOWED", "售后金额不能超过订单金额");
        }
    }

    private List<String> availableAfterSaleTypes(OrderEntity order) {
        if ("PENDING_PAYMENT".equals(order.getStatus())) {
            return List.of("CANCEL_ORDER");
        }
        if (!"PAID".equals(order.getPaymentStatus())) {
            return List.of();
        }
        if ("PAID_PENDING_SHIPMENT".equals(order.getStatus()) || "PENDING_SHIPMENT".equals(order.getStatus())) {
            return List.of("REFUND", "CANCEL_ORDER", "COMPENSATION");
        }
        return List.of("REFUND", "RETURN", "COMPENSATION");
    }

    private String productImageUrl(Long productId) {
        if (productId == null) {
            return null;
        }
        return productRepository.findById(productId)
            .map(Product::getImageUrl)
            .orElse(null);
    }

    private Map<Long, Product> productsById(List<Long> productIds) {
        return productRepository.findAllById(productIds).stream()
            .collect(Collectors.toMap(Product::getId, Function.identity()));
    }

    private boolean contains(String value, String keyword) {
        return value != null && value.toLowerCase().contains(keyword.toLowerCase());
    }

    private String nextOrderNo() {
        return "SO" + LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyyMMddHHmmssSSS"))
            + "-" + randomSuffix();
    }

    private String nextTransactionNo() {
        return "BT-" + LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyyMMddHHmmssSSS"))
            + "-" + randomSuffix();
    }

    private String nextAfterSaleNo() {
        return "AS-" + LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyyMMddHHmmssSSS"))
            + "-" + randomSuffix();
    }

    private String randomSuffix() {
        return UUID.randomUUID().toString().substring(0, 8);
    }

    private record OrderLineDraft(Product product, int quantity) {
    }
}

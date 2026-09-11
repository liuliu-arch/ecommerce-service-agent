export type ApiResponse<T> = {
  success: boolean;
  code: string;
  message: string;
  data: T;
};

export type CurrentAccount = {
  accountId: number;
  username: string;
  role: "USER" | "ADMIN" | string;
  userId: string | null;
  nickname: string | null;
  mobile: string | null;
  memberLevel: string | null;
  redirectPath: string | null;
};

export type ShopProduct = {
  productId: number;
  name: string;
  category: string;
  description: string;
  price: number;
  stockQuantity: number;
  imageUrl: string | null;
  supportsSevenDayReturn: boolean;
  afterSaleNote: string | null;
  purchaseAvailable: boolean;
  promotion: ProductPromotion | null;
};

export type ProductPromotion = {
  id: number;
  promotionName: string;
  promotionType: string;
  discountSummary: string;
  promotionPrice: number;
  requiredMemberLevel: string | null;
  conditionSummary: string | null;
  startAt: string;
  endAt: string;
};

export type AfterSalePolicy = {
  sceneKey: string;
  title: string;
  content: string;
  eligibility: string;
  applicableConditions: string;
  exclusionConditions: string;
  requiredEvidence: string;
  requiresManualReview: boolean;
  suggestedAction: string;
  policyVersion: string;
};

export type FaqEntry = {
  category: string;
  question: string;
  answer: string;
};

export type CartItem = {
  itemId: number;
  productId: number;
  productName: string;
  productImageUrl: string | null;
  originalUnitPrice: number;
  unitPrice: number;
  promotionPrice: number | null;
  promotionName: string | null;
  promotionApplied: boolean;
  promotionCondition: string | null;
  quantity: number;
  selected: boolean;
  stockQuantity: number;
  productStatus: string;
  settlementAvailable: boolean;
  unavailableReason: string | null;
};

export type Cart = {
  items: CartItem[];
  selectedTotalAmount: number;
  selectedItemCount: number;
};

export type ShopOrderItem = {
  productId: number;
  productName: string;
  productImageUrl: string | null;
  unitPrice: number;
  quantity: number;
};

export type ShopOrder = {
  orderNo: string;
  orderStatus: string;
  paymentStatus: string;
  fulfillmentStatus: string | null;
  totalAmount: number;
  itemSummary: string;
  remark: string | null;
  logisticsNo: string | null;
  items: ShopOrderItem[];
  afterSaleAvailable: boolean;
  availableAfterSaleTypes: string[];
  createdAt: string;
  paidAt: string | null;
  shippedAt: string | null;
  signedAt: string | null;
  completedAt: string | null;
};

export type Payment = {
  orderNo: string;
  orderStatus: string;
  paymentStatus: string;
  paidAmount: number;
  balanceBefore: number;
  balanceAfter: number;
  transactionNo: string;
  paidAt: string;
};

export type Balance = {
  userId: string;
  availableBalance: number;
  updatedAt: string;
};

export type BalanceTransaction = {
  transactionNo: string;
  type: string;
  amount: number;
  balanceBefore: number;
  balanceAfter: number;
  orderNo: string | null;
  afterSaleNo: string | null;
  remark: string | null;
  createdAt: string;
};

export type CustomerServicePageContext = {
  type: string;
  productId?: number;
  orderNo?: string;
  afterSaleNo?: string;
};

export type CustomerServiceResponse = {
  answer: string;
  sessionId: string;
  confirmRequired: boolean;
  pendingAction: string | null;
  confirmationTitle: string | null;
  confirmationSummary: string | null;
  relatedOrderNo: string | null;
  relatedAfterSaleNo: string | null;
  resumeToken: string | null;
  actions: { code: string; label: string }[];
  fallback: boolean;
};

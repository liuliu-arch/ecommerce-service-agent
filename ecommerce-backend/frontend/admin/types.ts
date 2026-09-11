export type AccountRole = "ADMIN" | "USER" | string;

export type CurrentAccount = {
  accountId: number;
  username: string;
  role: AccountRole;
  userId: string | null;
  nickname: string | null;
  mobile: string | null;
  memberLevel: string | null;
  redirectPath: string | null;
};

export type AdminProduct = {
  productId: number;
  code: string;
  name: string;
  category: string;
  description: string;
  price: number;
  stockQuantity: number;
  highlights: string | null;
  status: string;
  imageUrl: string | null;
  supportsSevenDayReturn: boolean;
  afterSaleNote: string | null;
  scenarioTags: string | null;
  createdAt: string;
  updatedAt: string;
};

export type AdminProductPayload = {
  code: string;
  name: string;
  category: string;
  description: string;
  price: number;
  stockQuantity: number;
  highlights: string;
  imageUrl: string;
  supportsSevenDayReturn: boolean;
  afterSaleNote: string;
  scenarioTags: string;
  status: string;
};

export type AdminPromotionProduct = {
  productId: number;
  productCode: string;
  productName: string;
  category: string;
  originalPrice: number;
  promotionPrice: number | null;
  participating: boolean;
};

export type AdminPromotion = {
  promotionName: string;
  promotionType: string;
  discountSummary: string;
  requiredMemberLevel: string | null;
  conditionSummary: string | null;
  startAt: string | null;
  endAt: string | null;
  active: boolean;
  productCount: number;
  products: AdminPromotionProduct[];
};

export type AdminPromotionPayload = {
  promotionName: string;
  promotionType: string;
  discountSummary: string;
  requiredMemberLevel: string | null;
  conditionSummary: string;
  startAt: string | null;
  endAt: string | null;
  active: boolean;
  products: Array<{ productId: number; promotionPrice: number }>;
};

export type OrderItem = {
  productId: number;
  productName: string;
  quantity: number;
  unitPrice: number;
};

export type LogisticsEvent = {
  occurredAt: string;
  content: string;
};

export type LinkedAfterSale = {
  requestId: string;
  orderNo: string;
  userId: string;
  requestType: string;
  reason: string;
  status: string;
  approvalId: string | null;
  createdAt: string;
  updatedAt: string;
  handlingNote: string | null;
};

export type AdminOrder = {
  orderNo: string;
  userId: string;
  userNickname: string;
  userMobile: string;
  orderStatus: string;
  paymentStatus: string;
  fulfillmentStatus: string;
  totalAmount: number;
  logisticsNo: string | null;
  remark: string | null;
  createdAt: string;
  paidAt: string | null;
  shippedAt: string | null;
  signedAt: string | null;
  items: OrderItem[];
  logisticsEvents: LogisticsEvent[];
  afterSaleRequests: LinkedAfterSale[];
};

export type AdminOrderUpdatePayload = {
  orderStatus?: string;
  fulfillmentStatus?: string;
  logisticsNo?: string;
  remark?: string;
};

export type ApprovalRecord = {
  approvalNo: string;
  targetType: string;
  targetNo: string;
  status: string;
  reviewerUsername: string | null;
  reviewNote: string | null;
  createdAt: string;
  reviewedAt: string | null;
};

export type AdminAfterSale = {
  requestNo: string;
  orderNo: string;
  userId: string;
  userNickname: string;
  type: string;
  status: string;
  amount: number;
  reason: string;
  handlingNote: string | null;
  approvalRecords: ApprovalRecord[];
  balanceEffectPreview: number | null;
  createdAt: string;
  updatedAt: string;
};

export type ReviewPayload = {
  reviewNote: string;
  approvedAmount?: number;
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

export type AdminUserBalance = {
  userId: string;
  nickname: string;
  mobile: string;
  memberLevel: string;
  riskLevel: string;
  availableBalance: number;
  recentTransactions: BalanceTransaction[];
};

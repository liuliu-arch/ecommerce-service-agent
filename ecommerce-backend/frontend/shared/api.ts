import type {
  Balance,
  BalanceTransaction,
  AfterSalePolicy,
  Cart,
  CurrentAccount,
  CustomerServiceResponse,
  FaqEntry,
  Payment,
  ShopOrder,
  ShopProduct
} from "./types";

export type ApiResponse<T> = {
  success: boolean;
  code: string;
  message: string;
  data: T;
};

export class ApiError extends Error {
  status: number;
  code: string;

  constructor(status: number, code: string, message: string) {
    super(message || "请求失败");
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

type RequestOptions = Omit<RequestInit, "body"> & {
  body?: unknown;
  query?: Record<string, string | number | undefined | null>;
};

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const url = buildUrl(path, options.query);
  const response = await fetch(url, {
    ...options,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(options.headers ?? {})
    },
    body: options.body === undefined ? undefined : JSON.stringify(options.body)
  });

  const payload = await readPayload<T>(response);
  if (!response.ok || !payload.success) {
    throw new ApiError(response.status, payload.code, payload.message);
  }
  return payload.data;
}

function buildUrl(path: string, query?: RequestOptions["query"]) {
  if (!query) {
    return path;
  }
  const search = new URLSearchParams();
  Object.entries(query).forEach(([key, value]) => {
    if (value !== undefined && value !== null && `${value}`.trim() !== "") {
      search.set(key, `${value}`);
    }
  });
  const qs = search.toString();
  return qs ? `${path}?${qs}` : path;
}

async function readPayload<T>(response: Response): Promise<ApiResponse<T>> {
  try {
    return (await response.json()) as ApiResponse<T>;
  } catch {
    return {
      success: false,
      code: response.ok ? "INVALID_RESPONSE" : `HTTP_${response.status}`,
      message: response.ok ? "接口返回格式不正确" : "网络请求失败",
      data: null as T
    };
  }
}

export const api = {
  login: (username: string, password: string) =>
    apiRequest<CurrentAccount>("/api/auth/login", { method: "POST", body: { username, password } }),
  me: () => apiRequest<CurrentAccount>("/api/auth/me"),
  logout: () => apiRequest<null>("/api/auth/logout", { method: "POST" }),
  products: (query: { keyword?: string; category?: string }) =>
    apiRequest<ShopProduct[]>("/api/shop/products", { query }),
  product: (productId: number) =>
    apiRequest<ShopProduct>(`/api/shop/products/${productId}`),
  cart: () => apiRequest<Cart>("/api/shop/cart"),
  addCartItem: (productId: number, quantity: number, selected = true) =>
    apiRequest<Cart>("/api/shop/cart/items", { method: "POST", body: { productId, quantity, selected } }),
  updateCartItem: (itemId: number, body: { quantity?: number; selected?: boolean }) =>
    apiRequest<Cart>(`/api/shop/cart/items/${itemId}`, { method: "PATCH", body }),
  deleteCartItem: (itemId: number) =>
    apiRequest<null>(`/api/shop/cart/items/${itemId}`, { method: "DELETE" }),
  createOrder: (body: { source: "CART" | "DIRECT_BUY"; cartItemIds?: number[]; productId?: number; quantity?: number; remark?: string }) =>
    apiRequest<ShopOrder>("/api/shop/orders", { method: "POST", body }),
  orders: (status?: string) =>
    apiRequest<ShopOrder[]>("/api/shop/orders", { query: { status } }),
  order: (orderNo: string) =>
    apiRequest<ShopOrder>(`/api/shop/orders/${encodeURIComponent(orderNo)}`),
  pay: (orderNo: string) =>
    apiRequest<Payment>(`/api/shop/orders/${encodeURIComponent(orderNo)}/pay`, { method: "POST" }),
  balance: () => apiRequest<Balance>("/api/shop/balance"),
  balanceTransactions: (type?: string) =>
    apiRequest<BalanceTransaction[]>("/api/shop/balance/transactions", { query: { type } }),
  afterSalePolicies: () =>
    apiRequest<AfterSalePolicy[]>("/api/after-sale/policies"),
  faqs: () =>
    apiRequest<FaqEntry[]>("/api/faq"),
  createAfterSale: (body: unknown) =>
    apiRequest("/api/shop/after-sales", { method: "POST", body }),
  afterSales: () => apiRequest("/api/shop/after-sales"),
  chat: (body: unknown) =>
    apiRequest<CustomerServiceResponse>("/api/customer-service/chat", { method: "POST", body }),
  resume: (body: unknown) =>
    apiRequest<CustomerServiceResponse>("/api/customer-service/resume", { method: "POST", body })
};

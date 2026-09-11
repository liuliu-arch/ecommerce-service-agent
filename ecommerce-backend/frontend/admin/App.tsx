import {
  BadgeCheck,
  Boxes,
  ClipboardList,
  LogOut,
  PackagePlus,
  RefreshCw,
  Search,
  ShieldAlert,
  ShoppingBag,
  Users
} from "lucide-react";
import { FormEvent, ReactNode, useEffect, useState } from "react";
import { ApiError } from "../shared/api";
import { adminApi } from "./adminApi";
import type {
  AdminAfterSale,
  AdminOrder,
  AdminProduct,
  AdminProductPayload,
  AdminPromotion,
  AdminPromotionPayload,
  AdminPromotionProduct,
  AdminUserBalance,
  CurrentAccount,
  ReviewPayload
} from "./types";

type PageKey = "products" | "promotions" | "orders" | "after-sales" | "users";
type AuthState = "checking" | "login" | "ready" | "forbidden";
type Notice = { type: "success" | "error" | "info"; text: string } | null;
type PromotionForm = Omit<AdminPromotionPayload, "products"> & { products: AdminPromotionProduct[] };

const promotionTypeOptions = [
  { value: "instant_discount", label: "限时直降" },
  { value: "member_discount", label: "会员专享价" },
  { value: "category_coupon", label: "品类券优惠" },
  { value: "subsidy_discount", label: "补贴优惠" },
  { value: "bundle_discount", label: "组合套装优惠" },
  { value: "official_discount", label: "官方直降" },
  { value: "service_bundle", label: "服务权益包" }
];

const navItems: Array<{ key: PageKey; label: string; icon: typeof Boxes }> = [
  { key: "products", label: "商品管理", icon: Boxes },
  { key: "promotions", label: "活动管理", icon: PackagePlus },
  { key: "orders", label: "订单管理", icon: ClipboardList },
  { key: "after-sales", label: "售后审批", icon: BadgeCheck },
  { key: "users", label: "用户与余额", icon: Users }
];

const emptyProduct: AdminProductPayload = {
  code: "",
  name: "",
  category: "",
  description: "",
  price: 0,
  stockQuantity: 0,
  highlights: "",
  imageUrl: "",
  supportsSevenDayReturn: true,
  afterSaleNote: "",
  scenarioTags: "",
  status: "OFF_SALE"
};

const emptyPromotion: PromotionForm = {
  promotionName: "",
  promotionType: "instant_discount",
  discountSummary: "",
  requiredMemberLevel: null,
  conditionSummary: "",
  startAt: null,
  endAt: null,
  active: true,
  products: []
};

export function App() {
  const [authState, setAuthState] = useState<AuthState>("checking");
  const [account, setAccount] = useState<CurrentAccount | null>(null);
  const [page, setPage] = useState<PageKey>(readPageFromLocation());
  const [notice, setNotice] = useState<Notice>(null);

  useEffect(() => {
    adminApi
      .me()
      .then((me) => {
        if (me.role !== "ADMIN") {
          setAuthState("forbidden");
          return;
        }
        setAccount(me);
        setAuthState("ready");
        normalizeAdminPath(page);
      })
      .catch((error) => {
        setAuthState(error instanceof ApiError && error.status === 403 ? "forbidden" : "login");
      });
  }, []);

  function navigate(next: PageKey) {
    setPage(next);
    window.history.pushState(null, "", `/admin/${next}`);
  }

  async function handleLogout() {
    setNotice({ type: "info", text: "正在退出后台..." });
    try {
      await adminApi.logout();
    } finally {
      setAccount(null);
      setAuthState("login");
      setNotice(null);
      window.history.replaceState(null, "", "/admin/login");
    }
  }

  if (authState === "checking") {
    return <CenteredState title="正在校验后台登录态" text="电商公司管理后台正在确认当前账号权限。" />;
  }

  if (authState === "login") {
    return (
      <LoginPage
        onSuccess={(nextAccount) => {
          setAccount(nextAccount);
          setAuthState("ready");
          setNotice({ type: "success", text: "已进入电商公司管理后台。" });
          normalizeAdminPath(page);
        }}
        onForbidden={() => setAuthState("forbidden")}
      />
    );
  }

  if (authState === "forbidden") {
    return (
      <CenteredState
        title="当前账号无权进入管理后台"
        text="请使用电商公司管理员账号登录。普通用户可以回到电商平台商城。"
        actionLabel="重新登录后台"
        onAction={() => {
          setAuthState("login");
          window.history.replaceState(null, "", "/admin/login");
        }}
        secondaryLabel="前往商城"
        onSecondary={() => {
          window.location.href = "/";
        }}
      />
    );
  }

  return (
    <div className="admin-shell">
      <aside className="sidebar">
        <div className="brand">
          <ShoppingBag size={22} />
          <div>
            <strong>电商公司</strong>
            <span>运营管理后台</span>
          </div>
        </div>
        <nav className="nav-list" aria-label="管理后台导航">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <button key={item.key} className={page === item.key ? "active" : ""} onClick={() => navigate(item.key)}>
                <Icon size={17} />
                {item.label}
              </button>
            );
          })}
        </nav>
        <button className="logout" onClick={handleLogout}>
          <LogOut size={16} />
          退出登录
        </button>
      </aside>
      <main className="workspace">
        <header className="topbar">
          <div>
            <p className="eyebrow">ADMIN CONSOLE</p>
            <h1>{navItems.find((item) => item.key === page)?.label}</h1>
          </div>
          <div className="operator">
            <span>{account?.username}</span>
            <small>管理员</small>
          </div>
        </header>
        {notice && <NoticeBar notice={notice} />}
        {page === "products" && <ProductsPage setNotice={setNotice} />}
        {page === "promotions" && <PromotionsPage setNotice={setNotice} />}
        {page === "orders" && <OrdersPage setNotice={setNotice} />}
        {page === "after-sales" && <AfterSalesPage setNotice={setNotice} />}
        {page === "users" && <UsersPage setNotice={setNotice} />}
      </main>
    </div>
  );
}

function LoginPage({ onSuccess, onForbidden }: { onSuccess: (account: CurrentAccount) => void; onForbidden: () => void }) {
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      await adminApi.login(username.trim(), password);
      const me = await adminApi.me();
      if (me.role !== "ADMIN") {
        onForbidden();
        return;
      }
      onSuccess(me);
    } catch (err) {
      setError(getLoginErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="login-screen">
      <form className="login-panel" onSubmit={submit}>
        <div className="login-title">
          <ShieldAlert size={24} />
          <div>
            <h1>电商公司管理后台</h1>
            <p>仅限内部运营管理员登录</p>
          </div>
        </div>
        <label>
          管理员账号
          <input value={username} onChange={(event) => setUsername(event.target.value)} autoComplete="username" />
        </label>
        <label>
          密码
          <input
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            autoComplete="current-password"
          />
        </label>
        {error && <p className="form-error">{error}</p>}
        <button className="primary" disabled={submitting || !username.trim() || !password}>
          {submitting ? "登录中..." : "登录后台"}
        </button>
      </form>
    </div>
  );
}

function ProductsPage({ setNotice }: { setNotice: (notice: Notice) => void }) {
  const [products, setProducts] = useState<AdminProduct[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [filters, setFilters] = useState({ keyword: "", category: "", status: "" });
  const [editing, setEditing] = useState<AdminProduct | null>(null);
  const [form, setForm] = useState<AdminProductPayload>(emptyProduct);
  const [submitting, setSubmitting] = useState(false);
  const [busyId, setBusyId] = useState<number | null>(null);
  const categories = Array.from(new Set(products.map((product) => product.category).filter(Boolean))).sort();

  useEffect(() => {
    load();
  }, []);

  async function load() {
    setLoading(true);
    setError("");
    try {
      setProducts(await adminApi.products(filters));
    } catch (err) {
      setError(getErrorMessage(err, "商品列表加载失败。"));
    } finally {
      setLoading(false);
    }
  }

  function edit(product: AdminProduct) {
    setEditing(product);
    setForm({
      code: product.code,
      name: product.name,
      category: product.category,
      description: product.description,
      price: Number(product.price),
      stockQuantity: Number(product.stockQuantity),
      highlights: product.highlights ?? "",
      imageUrl: product.imageUrl ?? "",
      supportsSevenDayReturn: product.supportsSevenDayReturn,
      afterSaleNote: product.afterSaleNote ?? "",
      scenarioTags: product.scenarioTags ?? "",
      status: product.status
    });
  }

  async function saveProduct(event: FormEvent) {
    event.preventDefault();
    if (form.price < 0 || form.stockQuantity < 0) {
      setNotice({ type: "error", text: "价格和库存不能小于 0。" });
      return;
    }
    setSubmitting(true);
    try {
      if (editing) {
        await adminApi.updateProduct(editing.productId, form);
      } else {
        await adminApi.createProduct(form);
      }
      setNotice({ type: "success", text: editing ? "商品已保存。" : "商品已新增。" });
      setEditing(null);
      setForm(emptyProduct);
      await load();
    } catch (err) {
      setNotice({ type: "error", text: getErrorMessage(err, "商品保存失败。") });
    } finally {
      setSubmitting(false);
    }
  }

  async function togglePublish(product: AdminProduct) {
    setBusyId(product.productId);
    try {
      if (product.status === "ON_SALE") {
        await adminApi.unpublishProduct(product.productId);
      } else {
        await adminApi.publishProduct(product.productId);
      }
      setNotice({ type: "success", text: product.status === "ON_SALE" ? "商品已下架。" : "商品已上架。" });
      await load();
    } catch (err) {
      setNotice({ type: "error", text: getErrorMessage(err, "上下架操作失败。") });
    } finally {
      setBusyId(null);
    }
  }

  return (
    <section className="content-grid two-col">
      <div className="panel wide">
        <Toolbar title="商品列表" onRefresh={load} loading={loading}>
          <input placeholder="商品名/编码" value={filters.keyword} onChange={(e) => setFilters({ ...filters, keyword: e.target.value })} />
          <input placeholder="分类" value={filters.category} onChange={(e) => setFilters({ ...filters, category: e.target.value })} />
          <select value={filters.status} onChange={(e) => setFilters({ ...filters, status: e.target.value })}>
            <option value="">全部状态</option>
            <option value="ON_SALE">上架销售</option>
            <option value="OFF_SALE">暂不上架</option>
          </select>
          <button onClick={load}>
            <Search size={15} /> 查询
          </button>
        </Toolbar>
        <DataState loading={loading} error={error} empty={!products.length} emptyText="暂无商品或筛选无结果。">
          <table>
            <thead>
              <tr>
                <th>商品</th>
                <th>分类</th>
                <th>价格</th>
                <th>库存</th>
                <th>售后</th>
                <th>状态</th>
                <th>更新时间</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {products.map((product) => (
                <tr key={product.productId}>
                  <td>
                    <strong>{product.name}</strong>
                    <small>{product.code}</small>
                  </td>
                  <td>{product.category}</td>
                  <td>{money(product.price)}</td>
                  <td>{product.stockQuantity}</td>
                  <td>{product.supportsSevenDayReturn ? "七天无理由" : "按规则处理"}</td>
                  <td><StatusBadge value={product.status} /></td>
                  <td>{date(product.updatedAt)}</td>
                  <td className="actions">
                    <button onClick={() => edit(product)}>编辑</button>
                    <button disabled={busyId === product.productId} onClick={() => togglePublish(product)}>
                      {busyId === product.productId ? "处理中" : product.status === "ON_SALE" ? "下架" : "上架"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </DataState>
      </div>
      <form className="panel form-panel" onSubmit={saveProduct}>
        <h2>{editing ? "编辑商品" : "新增商品"}</h2>
        <label>商品编码<input value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value })} required /></label>
        <label>商品名称<input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required /></label>
        <label>分类<select value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} required>
          <option value="">请选择分类</option>
          {categories.map((category) => <option key={category} value={category}>{category}</option>)}
          {form.category && !categories.includes(form.category) && <option value={form.category}>{form.category}</option>}
        </select></label>
        <div className="inline-fields">
          <label>价格<input type="number" min="0" step="0.01" value={form.price} onChange={(e) => setForm({ ...form, price: Number(e.target.value) })} /></label>
          <label>库存<input type="number" min="0" value={form.stockQuantity} onChange={(e) => setForm({ ...form, stockQuantity: Number(e.target.value) })} /></label>
        </div>
        <label>状态<select value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })}><option value="ON_SALE">上架销售</option><option value="OFF_SALE">暂不上架</option></select></label>
        <label>卖点<input value={form.highlights} onChange={(e) => setForm({ ...form, highlights: e.target.value })} /></label>
        <label>图片地址<input value={form.imageUrl} onChange={(e) => setForm({ ...form, imageUrl: e.target.value })} /></label>
        <label>描述<textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} /></label>
        <label>售后说明<textarea value={form.afterSaleNote} onChange={(e) => setForm({ ...form, afterSaleNote: e.target.value })} /></label>
        <label>场景标签<input value={form.scenarioTags} onChange={(e) => setForm({ ...form, scenarioTags: e.target.value })} /></label>
        <label className="check"><input type="checkbox" checked={form.supportsSevenDayReturn} onChange={(e) => setForm({ ...form, supportsSevenDayReturn: e.target.checked })} /> 支持七天无理由</label>
        <div className="form-actions">
          <button className="primary" disabled={submitting}>{submitting ? "保存中..." : "保存商品"}</button>
          {editing && <button type="button" onClick={() => { setEditing(null); setForm(emptyProduct); }}>取消编辑</button>}
        </div>
      </form>
    </section>
  );
}

function PromotionsPage({ setNotice }: { setNotice: (notice: Notice) => void }) {
  const [promotions, setPromotions] = useState<AdminPromotion[]>([]);
  const [selectedName, setSelectedName] = useState<string | null>(null);
  const [filters, setFilters] = useState({ keyword: "" });
  const [form, setForm] = useState<PromotionForm>(emptyPromotion);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    load();
    startCreate();
  }, []);

  async function load() {
    setLoading(true);
    setError("");
    try {
      setPromotions(await adminApi.promotions(filters));
    } catch (err) {
      setError(getErrorMessage(err, "活动列表加载失败。"));
    } finally {
      setLoading(false);
    }
  }

  async function startCreate() {
    try {
      const products = await adminApi.products({});
      setSelectedName(null);
      setForm({
        ...emptyPromotion,
        products: products.map((product) => ({
          productId: product.productId,
          productCode: product.code,
          productName: product.name,
          category: product.category,
          originalPrice: Number(product.price),
          promotionPrice: null,
          participating: false
        }))
      });
    } catch (err) {
      setNotice({ type: "error", text: getErrorMessage(err, "商品列表加载失败。") });
    }
  }

  async function openDetail(promotionName: string) {
    setNotice({ type: "info", text: "正在读取活动详情..." });
    try {
      const detail = await adminApi.promotion(promotionName);
      setSelectedName(detail.promotionName);
      setForm({
        promotionName: detail.promotionName,
        promotionType: detail.promotionType,
        discountSummary: detail.discountSummary,
        requiredMemberLevel: detail.requiredMemberLevel,
        conditionSummary: detail.conditionSummary ?? "",
        startAt: detail.startAt,
        endAt: detail.endAt,
        active: detail.active,
        products: detail.products
      });
      setNotice(null);
    } catch (err) {
      setNotice({ type: "error", text: getErrorMessage(err, "活动详情加载失败。") });
    }
  }

  function updateProductLine(productId: number, patch: Partial<AdminPromotionProduct>) {
    setForm((current) => ({
      ...current,
      products: current.products.map((product) => {
        if (product.productId !== productId) return product;
        const next = { ...product, ...patch };
        if (patch.participating && next.promotionPrice == null) {
          next.promotionPrice = next.originalPrice;
        }
        return next;
      })
    }));
  }

  async function savePromotion(event: FormEvent) {
    event.preventDefault();
    const selectedProducts = form.products.filter((product) => product.participating);
    if (!selectedProducts.length) {
      setNotice({ type: "error", text: "请至少选择一个参与活动的商品。" });
      return;
    }
    const payload: AdminPromotionPayload = {
      promotionName: form.promotionName.trim(),
      promotionType: form.promotionType.trim(),
      discountSummary: form.discountSummary.trim(),
      requiredMemberLevel: form.requiredMemberLevel?.trim() || null,
      conditionSummary: form.conditionSummary.trim(),
      startAt: form.startAt,
      endAt: form.endAt,
      active: form.active,
      products: selectedProducts.map((product) => ({
        productId: product.productId,
        promotionPrice: Number(product.promotionPrice ?? product.originalPrice)
      }))
    };
    setSaving(true);
    try {
      const saved = selectedName
        ? await adminApi.updatePromotion(selectedName, payload)
        : await adminApi.createPromotion(payload);
      setSelectedName(saved.promotionName);
      setNotice({ type: "success", text: selectedName ? "活动已保存。" : "活动已创建。" });
      await load();
      await openDetail(saved.promotionName);
    } catch (err) {
      setNotice({ type: "error", text: getErrorMessage(err, "活动保存失败。") });
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="content-grid detail-layout">
      <div className="panel">
        <Toolbar title="活动列表" onRefresh={load} loading={loading}>
          <input placeholder="活动名/类型/说明" value={filters.keyword} onChange={(e) => setFilters({ keyword: e.target.value })} />
          <button onClick={load}><Search size={15} /> 查询</button>
          <button onClick={startCreate}>新增活动</button>
        </Toolbar>
        <DataState loading={loading} error={error} empty={!promotions.length} emptyText="暂无活动或筛选无结果。">
          <table>
            <thead><tr><th>活动</th><th>类型</th><th>商品数</th><th>状态</th><th>有效期</th></tr></thead>
            <tbody>
              {promotions.map((promotion) => (
                <tr key={promotion.promotionName} onClick={() => openDetail(promotion.promotionName)} className={selectedName === promotion.promotionName ? "selected" : ""}>
                  <td><strong>{promotion.promotionName}</strong><small>{promotion.discountSummary}</small></td>
                  <td>{promotionTypeLabel(promotion.promotionType)}</td>
                  <td>{promotion.productCount}</td>
                  <td><StatusBadge value={promotion.active ? "ACTIVE" : "INACTIVE"} /></td>
                  <td>{date(promotion.startAt)}<small>至 {date(promotion.endAt)}</small></td>
                </tr>
              ))}
            </tbody>
          </table>
        </DataState>
      </div>
      <form className="panel detail-panel promotion-form" onSubmit={savePromotion}>
        <h2>{selectedName ? "编辑活动" : "新增活动"}</h2>
        <label>活动名称<input value={form.promotionName} onChange={(e) => setForm({ ...form, promotionName: e.target.value })} required /></label>
        <label>
          活动类型
          <select value={form.promotionType} onChange={(e) => setForm({ ...form, promotionType: e.target.value })} required>
            {!promotionTypeOptions.some((option) => option.value === form.promotionType) && (
              <option value={form.promotionType}>{promotionTypeLabel(form.promotionType)}</option>
            )}
            {promotionTypeOptions.map((option) => (
              <option key={option.value} value={option.value}>{option.label}</option>
            ))}
          </select>
        </label>
        <label>活动说明<textarea value={form.discountSummary} onChange={(e) => setForm({ ...form, discountSummary: e.target.value })} required /></label>
        <div className="inline-fields">
          <label>开始时间<input type="datetime-local" value={datetimeInputValue(form.startAt)} onChange={(e) => setForm({ ...form, startAt: e.target.value || null })} /></label>
          <label>结束时间<input type="datetime-local" value={datetimeInputValue(form.endAt)} onChange={(e) => setForm({ ...form, endAt: e.target.value || null })} /></label>
        </div>
        <div className="inline-fields">
          <label>会员门槛<input placeholder="gold / silver，可为空" value={form.requiredMemberLevel ?? ""} onChange={(e) => setForm({ ...form, requiredMemberLevel: e.target.value || null })} /></label>
          <label>条件说明<input value={form.conditionSummary} onChange={(e) => setForm({ ...form, conditionSummary: e.target.value })} /></label>
        </div>
        <label className="check"><input type="checkbox" checked={form.active} onChange={(e) => setForm({ ...form, active: e.target.checked })} /> 活动启用</label>
        <div className="product-picker">
          <div className="picker-head"><strong>参与商品</strong><span>{form.products.filter((product) => product.participating).length} 款已选择</span></div>
          {form.products.map((product) => (
            <div className="product-pick-row" key={product.productId}>
              <label className="check">
                <input type="checkbox" checked={product.participating} onChange={(e) => updateProductLine(product.productId, { participating: e.target.checked })} />
                <span><strong>{product.productName}</strong><small>{product.productCode} / {product.category} / 原价 {money(product.originalPrice)}</small></span>
              </label>
              <input
                type="number"
                min="0"
                step="0.01"
                disabled={!product.participating}
                value={product.promotionPrice ?? ""}
                onChange={(e) => updateProductLine(product.productId, { promotionPrice: Number(e.target.value) })}
                placeholder="活动价"
              />
            </div>
          ))}
        </div>
        <div className="form-actions">
          <button className="primary" disabled={saving}>{saving ? "保存中..." : "保存活动"}</button>
          {selectedName && <button type="button" onClick={startCreate}>新建活动</button>}
        </div>
      </form>
    </section>
  );
}

function OrdersPage({ setNotice }: { setNotice: (notice: Notice) => void }) {
  const [orders, setOrders] = useState<AdminOrder[]>([]);
  const [selected, setSelected] = useState<AdminOrder | null>(null);
  const [filters, setFilters] = useState({ orderNo: "", userId: "", orderStatus: "", paymentStatus: "", fulfillmentStatus: "" });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [patch, setPatch] = useState({ orderStatus: "", fulfillmentStatus: "", logisticsNo: "", remark: "" });

  useEffect(() => {
    load();
  }, []);

  async function load() {
    setLoading(true);
    setError("");
    try {
      setOrders(await adminApi.orders(filters));
    } catch (err) {
      setError(getErrorMessage(err, "订单列表加载失败。"));
    } finally {
      setLoading(false);
    }
  }

  async function openDetail(orderNo: string) {
    setNotice({ type: "info", text: "正在读取订单详情..." });
    try {
      const detail = await adminApi.order(orderNo);
      setSelected(detail);
      setPatch({
        orderStatus: detail.orderStatus,
        fulfillmentStatus: detail.fulfillmentStatus,
        logisticsNo: detail.logisticsNo ?? "",
        remark: detail.remark ?? ""
      });
      setNotice(null);
    } catch (err) {
      setNotice({ type: "error", text: getErrorMessage(err, "订单详情加载失败。") });
    }
  }

  async function saveOrder(event: FormEvent) {
    event.preventDefault();
    if (!selected) return;
    setSaving(true);
    try {
      const updated = await adminApi.updateOrder(selected.orderNo, patch);
      setSelected(updated);
      setNotice({ type: "success", text: "订单履约信息已保存。" });
      await load();
    } catch (err) {
      setNotice({ type: "error", text: getErrorMessage(err, "订单保存失败。") });
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="content-grid detail-layout">
      <div className="panel">
        <Toolbar title="订单列表" onRefresh={load} loading={loading}>
          <input placeholder="订单号" value={filters.orderNo} onChange={(e) => setFilters({ ...filters, orderNo: e.target.value })} />
          <input placeholder="用户 ID" value={filters.userId} onChange={(e) => setFilters({ ...filters, userId: e.target.value })} />
          <input placeholder="订单状态" value={filters.orderStatus} onChange={(e) => setFilters({ ...filters, orderStatus: e.target.value })} />
          <button onClick={load}><Search size={15} /> 查询</button>
        </Toolbar>
        <DataState loading={loading} error={error} empty={!orders.length} emptyText="暂无订单或筛选无结果。">
          <table>
            <thead><tr><th>订单号</th><th>用户</th><th>金额</th><th>订单</th><th>支付</th><th>履约</th><th>物流</th><th>创建时间</th></tr></thead>
            <tbody>
              {orders.map((order) => (
                <tr key={order.orderNo} onClick={() => openDetail(order.orderNo)} className={selected?.orderNo === order.orderNo ? "selected" : ""}>
                  <td><strong>{order.orderNo}</strong></td>
                  <td>{order.userNickname}<small>{order.userId}</small></td>
                  <td>{money(order.totalAmount)}</td>
                  <td><StatusBadge value={order.orderStatus} /></td>
                  <td>{order.paymentStatus}</td>
                  <td>{order.fulfillmentStatus}</td>
                  <td>{order.logisticsNo || "-"}</td>
                  <td>{date(order.createdAt)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </DataState>
      </div>
      <aside className="panel detail-panel">
        <h2>订单详情</h2>
        {!selected ? <EmptyText text="选择一笔订单查看明细和可维护字段。" /> : (
          <>
            <div className="kv">
              <span>订单号</span><strong>{selected.orderNo}</strong>
              <span>用户</span><strong>{selected.userNickname} / {selected.userMobile}</strong>
              <span>金额</span><strong>{money(selected.totalAmount)}</strong>
              <span>支付时间</span><strong>{date(selected.paidAt)}</strong>
            </div>
            <form onSubmit={saveOrder} className="compact-form">
              <label>订单状态<input value={patch.orderStatus} onChange={(e) => setPatch({ ...patch, orderStatus: e.target.value })} /></label>
              <label>履约状态<input value={patch.fulfillmentStatus} onChange={(e) => setPatch({ ...patch, fulfillmentStatus: e.target.value })} /></label>
              <label>物流单号<input value={patch.logisticsNo} onChange={(e) => setPatch({ ...patch, logisticsNo: e.target.value })} /></label>
              <label>后台备注<textarea value={patch.remark} onChange={(e) => setPatch({ ...patch, remark: e.target.value })} /></label>
              <button className="primary" disabled={saving}>{saving ? "保存中..." : "保存允许字段"}</button>
            </form>
            <SubList title="商品明细" rows={selected.items.map((item) => `${item.productName} x${item.quantity} / ${money(item.unitPrice)}`)} />
            <SubList title="物流记录" rows={selected.logisticsEvents.map((event) => `${date(event.occurredAt)} ${event.content}`)} empty="暂无物流记录" />
            <SubList title="关联售后" rows={selected.afterSaleRequests.map((item) => `${item.requestId} ${item.requestType} ${item.status}`)} empty="暂无关联售后" />
          </>
        )}
      </aside>
    </section>
  );
}

function AfterSalesPage({ setNotice }: { setNotice: (notice: Notice) => void }) {
  const [items, setItems] = useState<AdminAfterSale[]>([]);
  const [selected, setSelected] = useState<AdminAfterSale | null>(null);
  const [filters, setFilters] = useState({ requestNo: "", orderNo: "", userId: "", type: "", status: "" });
  const [review, setReview] = useState<ReviewPayload>({ reviewNote: "", approvedAmount: undefined });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState("");

  useEffect(() => {
    load();
  }, []);

  async function load() {
    setLoading(true);
    setError("");
    try {
      setItems(await adminApi.afterSales(filters));
    } catch (err) {
      setError(getErrorMessage(err, "售后列表加载失败。"));
    } finally {
      setLoading(false);
    }
  }

  async function openDetail(requestNo: string) {
    try {
      const detail = await adminApi.afterSale(requestNo);
      setSelected(detail);
      setReview({ reviewNote: "", approvedAmount: Number(detail.amount) });
    } catch (err) {
      setNotice({ type: "error", text: getErrorMessage(err, "售后详情加载失败。") });
    }
  }

  async function submitReview(action: "approve" | "reject" | "needMoreInfo") {
    if (!selected) return;
    const actionLabel = action === "approve" ? "通过" : action === "reject" ? "驳回" : "要求补充材料";
    if (!window.confirm(`确认对 ${selected.requestNo} 执行“${actionLabel}”？`)) return;
    setSubmitting(action);
    try {
      if (action === "approve") await adminApi.approveAfterSale(selected.requestNo, review);
      if (action === "reject") await adminApi.rejectAfterSale(selected.requestNo, review);
      if (action === "needMoreInfo") await adminApi.needMoreInfo(selected.requestNo, review);
      setNotice({ type: "success", text: `售后申请已${actionLabel}。` });
      await load();
      await openDetail(selected.requestNo);
    } catch (err) {
      setNotice({ type: "error", text: getErrorMessage(err, "售后审批失败。") });
    } finally {
      setSubmitting("");
    }
  }

  return (
    <section className="content-grid detail-layout">
      <div className="panel">
        <Toolbar title="售后申请" onRefresh={load} loading={loading}>
          <input placeholder="申请号" value={filters.requestNo} onChange={(e) => setFilters({ ...filters, requestNo: e.target.value })} />
          <input placeholder="订单号" value={filters.orderNo} onChange={(e) => setFilters({ ...filters, orderNo: e.target.value })} />
          <input placeholder="用户 ID" value={filters.userId} onChange={(e) => setFilters({ ...filters, userId: e.target.value })} />
          <input placeholder="状态" value={filters.status} onChange={(e) => setFilters({ ...filters, status: e.target.value })} />
          <button onClick={load}><Search size={15} /> 查询</button>
        </Toolbar>
        <DataState loading={loading} error={error} empty={!items.length} emptyText="暂无售后申请或筛选无结果。">
          <table>
            <thead><tr><th>申请号</th><th>订单</th><th>用户</th><th>类型</th><th>金额</th><th>状态</th><th>余额影响</th><th>更新时间</th></tr></thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.requestNo} onClick={() => openDetail(item.requestNo)} className={selected?.requestNo === item.requestNo ? "selected" : ""}>
                  <td><strong>{item.requestNo}</strong></td>
                  <td>{item.orderNo}</td>
                  <td>{item.userNickname}<small>{item.userId}</small></td>
                  <td>{item.type}</td>
                  <td>{money(item.amount)}</td>
                  <td><StatusBadge value={item.status} /></td>
                  <td>{item.balanceEffectPreview == null ? "-" : money(item.balanceEffectPreview)}</td>
                  <td>{date(item.updatedAt)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </DataState>
      </div>
      <aside className="panel detail-panel">
        <h2>审批处理</h2>
        {!selected ? <EmptyText text="选择一条售后申请查看审批记录。" /> : (
          <>
            <div className="kv">
              <span>申请号</span><strong>{selected.requestNo}</strong>
              <span>关联订单</span><strong>{selected.orderNo}</strong>
              <span>申请用户</span><strong>{selected.userNickname} / {selected.userId}</strong>
              <span>申请原因</span><strong>{selected.reason}</strong>
              <span>当前状态</span><strong>{selected.status}</strong>
            </div>
            <div className="compact-form">
              <label>审批金额<input type="number" min="0" step="0.01" value={review.approvedAmount ?? ""} onChange={(e) => setReview({ ...review, approvedAmount: Number(e.target.value) })} /></label>
              <label>审批意见<textarea value={review.reviewNote} onChange={(e) => setReview({ ...review, reviewNote: e.target.value })} /></label>
              <div className="split-actions">
                <button className="primary" disabled={!!submitting} onClick={() => submitReview("approve")}>{submitting === "approve" ? "处理中..." : "通过"}</button>
                <button disabled={!!submitting} onClick={() => submitReview("reject")}>{submitting === "reject" ? "处理中..." : "驳回"}</button>
                <button disabled={!!submitting} onClick={() => submitReview("needMoreInfo")}>{submitting === "needMoreInfo" ? "处理中..." : "补充材料"}</button>
              </div>
            </div>
            <SubList
              title="审批记录"
              rows={selected.approvalRecords.map((record) => `${record.approvalNo} ${record.status} ${record.reviewerUsername ?? "-"} ${record.reviewNote ?? ""}`)}
              empty="暂无审批记录"
            />
          </>
        )}
      </aside>
    </section>
  );
}

function UsersPage({ setNotice }: { setNotice: (notice: Notice) => void }) {
  const [userId, setUserId] = useState("");
  const [data, setData] = useState<AdminUserBalance | null>(null);
  const [loading, setLoading] = useState(false);

  async function search(event: FormEvent) {
    event.preventDefault();
    if (!userId.trim()) return;
    setLoading(true);
    setData(null);
    try {
      setData(await adminApi.userBalance(userId.trim()));
    } catch (err) {
      setNotice({ type: "error", text: getErrorMessage(err, "用户资料加载失败。") });
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="content-grid user-layout">
      <div className="panel form-panel">
        <h2>查询用户</h2>
        <form onSubmit={search} className="compact-form">
          <label>用户 ID<input placeholder="例如 U1001" value={userId} onChange={(e) => setUserId(e.target.value)} /></label>
          <button className="primary" disabled={loading || !userId.trim()}>{loading ? "查询中..." : "查询余额"}</button>
        </form>
      </div>
      <div className="panel">
        <h2>用户资料与余额</h2>
        {!data ? <EmptyText text={loading ? "正在读取用户资料..." : "输入用户 ID 后查看资料、余额和最近流水。"} /> : (
          <>
            <div className="metric-row">
              <Metric label="用户" value={`${data.nickname} / ${data.userId}`} />
              <Metric label="会员等级" value={data.memberLevel} />
              <Metric label="风险等级" value={data.riskLevel} />
              <Metric label="可用余额" value={money(data.availableBalance)} />
            </div>
            <table>
              <thead><tr><th>流水号</th><th>类型</th><th>金额</th><th>变动前</th><th>变动后</th><th>关联单据</th><th>备注</th><th>时间</th></tr></thead>
              <tbody>
                {data.recentTransactions.map((item) => (
                  <tr key={item.transactionNo}>
                    <td><strong>{item.transactionNo}</strong></td>
                    <td>{item.type}</td>
                    <td>{money(item.amount)}</td>
                    <td>{money(item.balanceBefore)}</td>
                    <td>{money(item.balanceAfter)}</td>
                    <td>{item.orderNo || item.afterSaleNo || "-"}</td>
                    <td>{item.remark || "-"}</td>
                    <td>{date(item.createdAt)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!data.recentTransactions.length && <EmptyText text="暂无余额流水。" />}
          </>
        )}
      </div>
    </section>
  );
}

function Toolbar({ title, children, onRefresh, loading }: { title: string; children: ReactNode; onRefresh: () => void; loading: boolean }) {
  return (
    <div className="toolbar">
      <h2>{title}</h2>
      <div className="filters">{children}</div>
      <button className="icon-button" onClick={onRefresh} title="刷新" disabled={loading}>
        <RefreshCw size={16} />
      </button>
    </div>
  );
}

function DataState({ loading, error, empty, emptyText, children }: { loading: boolean; error: string; empty: boolean; emptyText: string; children: ReactNode }) {
  if (loading) return <EmptyText text="数据加载中..." />;
  if (error) return <EmptyText text={error} tone="error" />;
  if (empty) return <EmptyText text={emptyText} />;
  return <>{children}</>;
}

function CenteredState(props: { title: string; text: string; actionLabel?: string; onAction?: () => void; secondaryLabel?: string; onSecondary?: () => void }) {
  return (
    <div className="centered-state">
      <div>
        <PackagePlus size={28} />
        <h1>{props.title}</h1>
        <p>{props.text}</p>
        <div className="split-actions">
          {props.actionLabel && <button className="primary" onClick={props.onAction}>{props.actionLabel}</button>}
          {props.secondaryLabel && <button onClick={props.onSecondary}>{props.secondaryLabel}</button>}
        </div>
      </div>
    </div>
  );
}

function NoticeBar({ notice }: { notice: Exclude<Notice, null> }) {
  return <div className={`notice ${notice.type}`}>{notice.text}</div>;
}

function EmptyText({ text, tone = "muted" }: { text: string; tone?: "muted" | "error" }) {
  return <p className={`empty ${tone}`}>{text}</p>;
}

function StatusBadge({ value }: { value: string }) {
  return <span className={`status ${value.toLowerCase().replaceAll("_", "-")}`}>{statusLabel(value)}</span>;
}

function Metric({ label, value }: { label: string; value: string }) {
  return <div className="metric"><span>{label}</span><strong>{value}</strong></div>;
}

function SubList({ title, rows, empty = "暂无数据" }: { title: string; rows: string[]; empty?: string }) {
  return (
    <div className="sub-list">
      <h3>{title}</h3>
      {rows.length ? rows.map((row) => <p key={row}>{row}</p>) : <EmptyText text={empty} />}
    </div>
  );
}

function readPageFromLocation(): PageKey {
  const part = window.location.pathname.split("/").filter(Boolean)[1];
  return navItems.some((item) => item.key === part) ? (part as PageKey) : "products";
}

function normalizeAdminPath(page: PageKey) {
  if (!window.location.pathname.startsWith("/admin") || window.location.pathname === "/admin/login") {
    window.history.replaceState(null, "", `/admin/${page}`);
  }
}

function getErrorMessage(error: unknown, fallback: string) {
  if (error instanceof ApiError) {
    if (error.status === 401) return "登录已失效，请重新登录。";
    if (error.status === 403) return "当前账号无权执行该操作。";
    return error.message || fallback;
  }
  return fallback;
}

function getLoginErrorMessage(error: unknown) {
  if (error instanceof ApiError) {
    if (error.status === 401) return error.message || "账号或密码不正确。";
    if (error.status === 403) return "当前账号无权进入管理后台。";
  }
  return "登录失败，请检查账号或稍后重试。";
}

function money(value: number | null | undefined) {
  return `¥${Number(value ?? 0).toFixed(2)}`;
}

function datetimeInputValue(value: string | null | undefined) {
  return value ? value.slice(0, 16) : "";
}

function statusLabel(value: string) {
  const labels: Record<string, string> = {
    ON_SALE: "上架销售",
    OFF_SALE: "暂不上架",
    ACTIVE: "启用",
    INACTIVE: "停用"
  };
  return labels[value] ?? value;
}

function promotionTypeLabel(value: string) {
  return promotionTypeOptions.find((option) => option.value === value)?.label ?? value;
}

function date(value: string | null | undefined) {
  if (!value) return "-";
  return value.replace("T", " ").slice(0, 16);
}

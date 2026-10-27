"use client";
import React, { useEffect, useMemo, useState } from "react";
import { fetchGymData, postGymData } from "@/lib/api";
import { Chip, Note, SectionTitle, Stat, Toast } from "@/components/ui";
import type { PosOrderRow, ProductItem } from "@/lib/erp-types";

/* ==========================================================================
   POS — Bán hàng tại quầy Pro-Shop.
   Hỗ trợ bán nguyên hũ hoặc bán lẻ từng muỗng, thanh toán tiền mặt /
   chuyển khoản / trừ ví trả trước. Cảnh báo tồn kho và hạn sử dụng.
   ========================================================================== */

type CartLine = { product: ProductItem; quantity: number; byServing: boolean };

export default function PosPage() {
  const [products, setProducts] = useState<ProductItem[]>([]);
  const [orders, setOrders] = useState<any>(null);
  const [cart, setCart] = useState<CartLine[]>([]);
  const [category, setCategory] = useState("ALL");
  const [memberId, setMemberId] = useState("");
  const [payment, setPayment] = useState("cash");
  const [discount, setDiscount] = useState("0");
  const [toast, setToast] = useState<{ kind: "ok" | "err"; text: string } | null>(null);
  const [tab, setTab] = useState<"sell" | "orders" | "stock">("sell");
  const [lowStock, setLowStock] = useState<any>(null);
  const [busy, setBusy] = useState(false);

  const load = () => {
    fetchGymData("/gym-ops/products").then(setProducts).catch(() => {});
    fetchGymData("/gym-ops/pos/orders?days=14").then(setOrders).catch(() => {});
    fetchGymData("/gym-ops/inventory/low-stock").then(setLowStock).catch(() => {});
  };

  useEffect(() => {
    load();
  }, []);

  const categories = useMemo(
    () => ["ALL", ...Array.from(new Set(products.map((p) => p.category)))],
    [products]
  );

  const visible = products.filter((p) => category === "ALL" || p.category === category);

  const addToCart = (product: ProductItem, byServing: boolean) => {
    setCart((prev) => {
      const idx = prev.findIndex(
        (l) => l.product.id === product.id && l.byServing === byServing
      );
      if (idx >= 0) {
        const next = [...prev];
        next[idx] = { ...next[idx], quantity: next[idx].quantity + 1 };
        return next;
      }
      return [...prev, { product, quantity: 1, byServing }];
    });
  };

  const updateQty = (index: number, qty: number) => {
    setCart((prev) => {
      const next = [...prev];
      if (qty <= 0) next.splice(index, 1);
      else next[index] = { ...next[index], quantity: qty };
      return next;
    });
  };

  const lineTotal = (line: CartLine) =>
    (line.byServing ? line.product.serving_price : line.product.price) * line.quantity;

  const subtotal = cart.reduce((sum, l) => sum + lineTotal(l), 0);
  const discountAmount = Math.min(Number(discount) || 0, subtotal);
  const total = subtotal - discountAmount;

  const checkout = async () => {
    if (cart.length === 0) {
      setToast({ kind: "err", text: "Chưa có mặt hàng nào trong đơn." });
      return;
    }
    setBusy(true);
    try {
      const res = await postGymData("/gym-ops/pos/checkout", {
        items: cart.map((l) => ({
          product_id: l.product.id,
          quantity: l.quantity,
          by_serving: l.byServing,
        })),
        member_id: memberId ? Number(memberId) : null,
        payment_method: payment,
        discount_amount: discountAmount,
        branch_id: 1,
      });
      setToast({ kind: "ok", text: res.message });
      if (res.low_stock_warnings?.length) {
        setTimeout(
          () =>
            setToast({
              kind: "err",
              text: res.low_stock_warnings.join(" | "),
            }),
          1200
        );
      }
      setCart([]);
      setDiscount("0");
      setMemberId("");
      load();
    } catch (err: any) {
      setToast({ kind: "err", text: err.message });
    } finally {
      setBusy(false);
    }
  };

  const catLabel: Record<string, string> = {
    supplement: "Thực phẩm bổ sung",
    drink: "Nước uống",
    accessory: "Phụ kiện",
    service: "Dịch vụ",
  };

  return (
    <div>
      <div className="hg-page-header">
        <div>
          <Chip>POS - PRO-SHOP</Chip>
          <h1>Bán Hàng Tại Quầy</h1>
          <p>
            Bán nguyên hũ hoặc lẻ từng muỗng Whey pha sẵn. Thanh toán tiền mặt, chuyển khoản hoặc
            trừ ví trả trước của hội viên.
          </p>
        </div>
        <div className="hg-flex">
          {orders && <Chip tone="gold">{orders.total_orders} đơn / 14 ngày</Chip>}
          {lowStock?.low_stock_count > 0 && (
            <Chip tone="warn">{lowStock.low_stock_count} mặt hàng sắp hết</Chip>
          )}
        </div>
      </div>

      {toast && <Toast kind={toast.kind}>{toast.text}</Toast>}

      <div className="hg-tabs">
        <button className={`hg-tab ${tab === "sell" ? "active" : ""}`} onClick={() => setTab("sell")}>
          Bán hàng
        </button>
        <button className={`hg-tab ${tab === "orders" ? "active" : ""}`} onClick={() => setTab("orders")}>
          Lịch sử đơn hàng
        </button>
        <button className={`hg-tab ${tab === "stock" ? "active" : ""}`} onClick={() => setTab("stock")}>
          Kho hàng
        </button>
      </div>

      {/* ================= BÁN HÀNG ================= */}
      {tab === "sell" && (
        <div className="hg-grid-2" style={{ gridTemplateColumns: "1.5fr 1fr" }}>
          <div>
            <div className="hg-flex" style={{ marginBottom: "14px" }}>
              {categories.map((c) => (
                <button
                  key={c}
                  className={category === c ? "hg-btn-primary hg-btn-sm" : "hg-btn-ghost hg-btn-sm"}
                  onClick={() => setCategory(c)}
                >
                  {c === "ALL" ? "Tất cả" : catLabel[c] ?? c}
                </button>
              ))}
            </div>

            <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(230px, 1fr))" }}>
              {visible.map((p) => (
                <div key={p.id} className="card" style={{ gap: "8px", padding: "14px" }}>
                  <div className="hg-flex" style={{ justifyContent: "space-between" }}>
                    <span className="hg-exercise-muscle">{p.sku}</span>
                    <Chip tone={p.is_low_stock ? "warn" : "default"}>
                      Tồn {p.stock_quantity} {p.unit}
                    </Chip>
                  </div>

                  <div style={{ fontWeight: 600, fontSize: "13.5px", lineHeight: 1.4 }}>
                    {p.name}
                  </div>

                  {p.brand && <div className="hg-exercise-muscle">{p.brand}</div>}

                  <div
                    className="hg-num-mono"
                    style={{ fontSize: "16px", fontWeight: 600, color: "#0d1f26" }}
                  >
                    {p.price.toLocaleString("vi-VN")}đ
                    <span style={{ fontSize: "11px", color: "#6b8590" }}>/{p.unit}</span>
                  </div>

                  {p.can_sell_by_serving && (
                    <div className="hg-muted">
                      Bán lẻ: {p.serving_price.toLocaleString("vi-VN")}đ/muỗng (
                      {p.servings_per_unit} muỗng/{p.unit})
                    </div>
                  )}

                  {p.expiry_warning && <Note tone="danger">{p.expiry_warning}</Note>}

                  <div className="hg-flex" style={{ marginTop: "auto" }}>
                    <button
                      className="hg-btn-primary hg-btn-sm"
                      onClick={() => addToCart(p, false)}
                      disabled={p.stock_quantity < 1}
                    >
                      + {p.unit}
                    </button>
                    {p.can_sell_by_serving && (
                      <button className="hg-btn-ghost hg-btn-sm" onClick={() => addToCart(p, true)}>
                        + 1 muỗng
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Giỏ hàng */}
          <div className="hg-chart-card" style={{ position: "sticky", top: "76px", alignSelf: "start" }}>
            <div className="hg-chart-title">Đơn hàng</div>

            {cart.length === 0 ? (
              <div className="hg-empty">Chưa có mặt hàng nào.</div>
            ) : (
              <div style={{ marginBottom: "14px" }}>
                {cart.map((line, i) => (
                  <div key={i} style={{ paddingBottom: "10px", borderBottom: "1px solid #d4e0e5", marginBottom: "10px" }}>
                    <div className="hg-flex" style={{ justifyContent: "space-between" }}>
                      <span style={{ fontSize: "13px", fontWeight: 600 }}>
                        {line.product.name}
                      </span>
                      <button className="hg-btn-ghost hg-btn-sm" onClick={() => updateQty(i, 0)}>
                        Xóa
                      </button>
                    </div>
                    <div className="hg-exercise-muscle">
                      {line.byServing
                        ? `Bán lẻ ${line.quantity} muỗng × ${line.product.serving_price.toLocaleString("vi-VN")}đ`
                        : `${line.quantity} ${line.product.unit} × ${line.product.price.toLocaleString("vi-VN")}đ`}
                    </div>
                    <div className="hg-flex" style={{ marginTop: "6px", justifyContent: "space-between" }}>
                      <div className="hg-flex" style={{ gap: "4px" }}>
                        <button className="hg-btn-ghost hg-btn-sm" onClick={() => updateQty(i, line.quantity - 1)}>
                          −
                        </button>
                        <span className="hg-num-mono" style={{ minWidth: "28px", textAlign: "center" }}>
                          {line.quantity}
                        </span>
                        <button className="hg-btn-ghost hg-btn-sm" onClick={() => updateQty(i, line.quantity + 1)}>
                          +
                        </button>
                      </div>
                      <span className="hg-num-mono" style={{ fontWeight: 600 }}>
                        {lineTotal(line).toLocaleString("vi-VN")}đ
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {cart.length > 0 && (
              <>
                <label>Mã hội viên (để tích điểm và trừ ví)</label>
                <input
                  className="input-box"
                  type="number"
                  placeholder="Bỏ trống nếu khách vãng lai"
                  value={memberId}
                  onChange={(e) => setMemberId(e.target.value)}
                />

                <label>Giảm giá (đ)</label>
                <input
                  className="input-box"
                  type="number"
                  value={discount}
                  onChange={(e) => setDiscount(e.target.value)}
                />

                <label>Phương thức thanh toán</label>
                <select
                  className="input-box"
                  value={payment}
                  onChange={(e) => setPayment(e.target.value)}
                >
                  <option value="cash">Tiền mặt</option>
                  <option value="transfer">Chuyển khoản</option>
                  <option value="wallet">Trừ ví trả trước</option>
                  <option value="card">Thẻ ngân hàng</option>
                </select>

                <div className="hg-divider" />
                <div className="hg-kv">
                  <span>Tạm tính</span>
                  <span className="hg-num-mono">{subtotal.toLocaleString("vi-VN")}đ</span>
                </div>
                <div className="hg-kv">
                  <span>Giảm giá</span>
                  <span className="hg-num-mono">−{discountAmount.toLocaleString("vi-VN")}đ</span>
                </div>
                <div className="hg-kv" style={{ borderTop: "2px solid #06303d", paddingTop: "12px" }}>
                  <span style={{ fontWeight: 700, color: "#0d1f26" }}>TỔNG CỘNG</span>
                  <span
                    className="hg-num-mono"
                    style={{ fontWeight: 700, fontSize: "18px", color: "#0d1f26" }}
                  >
                    {total.toLocaleString("vi-VN")}đ
                  </span>
                </div>

                {memberId && (
                  <Note>
                    Hội viên sẽ được tích <strong>{Math.floor(total / 10000)} điểm</strong> thưởng
                    cho đơn hàng này.
                  </Note>
                )}

                <button
                  className="hg-btn-primary"
                  style={{ width: "100%", marginTop: "10px" }}
                  onClick={checkout}
                  disabled={busy}
                >
                  {busy && <span className="hg-spinner" />}
                  Xác nhận thanh toán
                </button>
              </>
            )}
          </div>
        </div>
      )}

      {/* ================= LỊCH SỬ ĐƠN ================= */}
      {tab === "orders" && (
        <div>
          {orders && (
            <div className="stats-bar">
              <Stat label="Số đơn (14 ngày)" value={orders.total_orders} />
              <Stat
                label="Doanh thu"
                value={`${Number(orders.total_revenue).toLocaleString("vi-VN")}đ`}
                gold
              />
              <Stat
                label="Lợi nhuận"
                value={`${Number(orders.total_profit).toLocaleString("vi-VN")}đ`}
              />
              <Stat label="Biên lợi nhuận" value={`${orders.margin_percent}%`} />
            </div>
          )}
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Mã đơn</th>
                  <th>Khách hàng</th>
                  <th>Số mặt hàng</th>
                  <th>Tổng tiền</th>
                  <th>Lợi nhuận</th>
                  <th>Thanh toán</th>
                  <th>Thu ngân</th>
                </tr>
              </thead>
              <tbody>
                {(orders?.orders ?? []).length === 0 ? (
                  <tr>
                    <td colSpan={7} style={{ textAlign: "center" }}>
                      Chưa có đơn hàng nào.
                    </td>
                  </tr>
                ) : (
                  orders.orders.map((o: PosOrderRow) => (
                    <tr key={o.id}>
                      <td className="hg-num-mono">{o.order_code}</td>
                      <td>{o.customer_name}</td>
                      <td className="hg-num">{o.item_count}</td>
                      <td className="hg-num-mono" style={{ fontWeight: 600 }}>
                        {o.total_amount.toLocaleString("vi-VN")}đ
                      </td>
                      <td className="hg-num-mono" style={{ color: "#0f7a52" }}>
                        {o.profit.toLocaleString("vi-VN")}đ
                      </td>
                      <td>
                        <Chip>{o.payment_method}</Chip>
                      </td>
                      <td className="hg-muted">{o.cashier}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ================= KHO HÀNG ================= */}
      {tab === "stock" && (
        <div>
          {lowStock && (
            <>
              <div className="stats-bar">
                <Stat
                  label="Giá trị tồn kho"
                  value={`${Number(lowStock.total_inventory_value).toLocaleString("vi-VN")}đ`}
                  gold
                />
                <Stat label="Mặt hàng sắp hết" value={lowStock.low_stock_count} />
                <Stat label="Sắp hết hạn" value={lowStock.expiring_count} />
              </div>

              {lowStock.advice && <Note tone="gold">{lowStock.advice}</Note>}

              <SectionTitle>Cần nhập thêm hàng</SectionTitle>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>SKU</th>
                      <th>Sản phẩm</th>
                      <th>Tồn hiện tại</th>
                      <th>Ngưỡng cảnh báo</th>
                      <th>Đề xuất nhập</th>
                    </tr>
                  </thead>
                  <tbody>
                    {lowStock.low_stock.length === 0 ? (
                      <tr>
                        <td colSpan={5} style={{ textAlign: "center" }}>
                          Tất cả mặt hàng đều đủ tồn kho.
                        </td>
                      </tr>
                    ) : (
                      lowStock.low_stock.map((p: any) => (
                        <tr key={p.product_id}>
                          <td className="hg-num-mono">{p.sku}</td>
                          <td>
                            <strong>{p.name}</strong>
                          </td>
                          <td className="hg-num" style={{ color: "#b45309", fontWeight: 600 }}>
                            {p.stock_quantity} {p.unit}
                          </td>
                          <td className="hg-num">{p.threshold}</td>
                          <td className="hg-num" style={{ fontWeight: 600 }}>
                            +{p.suggested_order} {p.unit}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>

              {lowStock.expiring_soon.length > 0 && (
                <>
                  <SectionTitle>Sắp hết hạn sử dụng</SectionTitle>
                  <div className="table-wrap">
                    <table>
                      <thead>
                        <tr>
                          <th>Sản phẩm</th>
                          <th>Hạn sử dụng</th>
                          <th>Còn lại</th>
                          <th>Tồn kho</th>
                        </tr>
                      </thead>
                      <tbody>
                        {lowStock.expiring_soon.map((p: any) => (
                          <tr key={p.product_id}>
                            <td>
                              <strong>{p.name}</strong>
                            </td>
                            <td className="hg-num-mono">{p.expiry_date}</td>
                            <td>
                              <Chip tone={p.is_expired ? "danger" : "warn"}>
                                {p.is_expired
                                  ? `Hết hạn ${Math.abs(p.days_to_expiry)} ngày`
                                  : `${p.days_to_expiry} ngày`}
                              </Chip>
                            </td>
                            <td className="hg-num">{p.stock_quantity}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
export function formatCurrency(amount: number): string {
  return new Intl.NumberFormat("vi-VN", {
    style: "currency",
    currency: "VND",
  }).format(amount);
}

export function formatDays(days: number): string {
  if (days % 30 === 0) return `${days / 30} tháng (${days} ngày)`;
  return `${days} ngày`;
}

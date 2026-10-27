const DEFAULT_API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

function getBaseUrls(): string[] {
  const primary = DEFAULT_API_BASE.replace(/\/+$/, "");
  const urls = [primary];
  if (primary.includes("127.0.0.1")) {
    urls.push(primary.replace("127.0.0.1", "localhost"));
  } else if (primary.includes("localhost")) {
    urls.push(primary.replace("localhost", "127.0.0.1"));
  }
  if (typeof window !== "undefined" && window.location.hostname) {
    const host = window.location.hostname;
    const fromHost = `http://${host}:8000`;
    if (!urls.includes(fromHost)) {
      urls.unshift(fromHost);
    }
  }
  return Array.from(new Set(urls));
}

function getAuthHeaders(): Record<string, string> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("hg_token");
    if (token) headers["Authorization"] = `Bearer ${token}`;
  }
  return headers;
}

async function requestWithFallback(
  endpoint: string,
  options: RequestInit = {}
): Promise<any> {
  const cleanEndpoint = endpoint.startsWith("/") ? endpoint : `/${endpoint}`;
  const urls = getBaseUrls();
  let lastError: any = null;

  for (const base of urls) {
    try {
      const fullUrl = `${base}${cleanEndpoint}`;
      const res = await fetch(fullUrl, {
        ...options,
        headers: {
          ...getAuthHeaders(),
          ...(options.headers || {}),
        },
      });

      let data: any = null;
      const text = await res.text();
      try {
        data = text ? JSON.parse(text) : {};
      } catch {
        data = { detail: text || res.statusText };
      }

      if (!res.ok) {
        const errorMsg =
          data?.detail ||
          data?.message ||
          `Máy chủ trả lời lỗi (${res.status}): ${res.statusText || "Không thành công"}`;
        throw new Error(errorMsg);
      }

      return data;
    } catch (err: any) {
      lastError = err;
      // If error is 4xx or 5xx from server, don't retry on other base URL unless it's a connection failure
      if (err.message && !err.message.includes("Failed to fetch") && !err.message.includes("NetworkError")) {
        throw err;
      }
    }
  }

  throw (
    lastError ||
    new Error("Không thể kết nối đến máy chủ API backend HealthyGym (cổng 8000). Vui lòng đảm bảo backend đang chạy.")
  );
}

export async function fetchGymData(endpoint: string) {
  return requestWithFallback(endpoint, {
    method: "GET",
    cache: "no-store",
  });
}

export async function postGymData(endpoint: string, body: unknown = {}) {
  return requestWithFallback(endpoint, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function putGymData(endpoint: string, body: unknown = {}) {
  return requestWithFallback(endpoint, {
    method: "PUT",
    body: JSON.stringify(body),
  });
}

export async function deleteGymData(endpoint: string) {
  return requestWithFallback(endpoint, {
    method: "DELETE",
  });
}

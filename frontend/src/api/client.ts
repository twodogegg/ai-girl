const JSON_HEADERS = { "Content-Type": "application/json" };

export class ApiError extends Error {
  status: number;
  code?: string;
  constructor(message: string, status = 0, code?: string) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

type RequestOptions = {
  method?: string;
  body?: unknown;
  form?: FormData;
  signal?: AbortSignal;
};

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const response = await fetch(path, {
    method: options.method ?? "GET",
    credentials: "same-origin",
    cache: "no-store",
    signal: options.signal,
    headers: options.form ? undefined : options.body !== undefined ? JSON_HEADERS : undefined,
    body: options.form ?? (options.body !== undefined ? JSON.stringify(options.body) : undefined),
  });
  if (response.status === 204) return undefined as T;
  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    const error = payload?.error;
    if (response.status === 401) window.dispatchEvent(new CustomEvent("plot18:unauthorized"));
    throw new ApiError(error?.message || `请求失败（HTTP ${response.status}）`, response.status, error?.code);
  }
  return payload as T;
}

export type UploadResult = { id: string; url: string; width: number; height: number; size: number };

export async function uploadImage(file: Blob, signal?: AbortSignal): Promise<UploadResult> {
  const form = new FormData();
  form.append("file", file, "photo.jpg");
  return request<UploadResult>("/api/files", { method: "POST", form, signal });
}

export function compressImage(file: File, maxSide = 1600, quality = 0.86): Promise<Blob> {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file);
    const image = new Image();
    image.onload = () => {
      const scale = Math.min(1, maxSide / Math.max(image.width, image.height));
      const canvas = document.createElement("canvas");
      canvas.width = Math.max(1, Math.round(image.width * scale));
      canvas.height = Math.max(1, Math.round(image.height * scale));
      const context = canvas.getContext("2d");
      if (!context) {
        URL.revokeObjectURL(url);
        reject(new Error("浏览器无法压缩这张图片。"));
        return;
      }
      context.drawImage(image, 0, 0, canvas.width, canvas.height);
      canvas.toBlob((blob) => {
        URL.revokeObjectURL(url);
        if (blob) resolve(blob);
        else reject(new Error("图片压缩失败。"));
      }, "image/jpeg", quality);
    };
    image.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error("无法读取这张图片。"));
    };
    image.src = url;
  });
}

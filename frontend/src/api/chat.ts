import type { ChatEvent } from "@/types";
import { ApiError } from "./client";

export type SendPayload = {
  personaId: string;
  conversationId?: string | null;
  text: string;
  imageIds?: string[];
  regenerate?: boolean;
};

async function* readLines(body: ReadableStream<Uint8Array>): AsyncGenerator<string> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      let index: number;
      while ((index = buffer.indexOf("\n")) >= 0) {
        const line = buffer.slice(0, index).trim();
        buffer = buffer.slice(index + 1);
        if (line) yield line;
      }
    }
    const tail = buffer.trim();
    if (tail) yield tail;
  } finally {
    reader.releaseLock();
  }
}

export async function streamChat(
  payload: SendPayload,
  onEvent: (event: ChatEvent) => void,
  signal: AbortSignal,
): Promise<void> {
  let response: Response;
  try {
    response = await fetch("/api/chat", {
      method: "POST",
      credentials: "same-origin",
      cache: "no-store",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      signal,
    });
  } catch (error) {
    if (signal.aborted) throw error;
    throw new ApiError("连接不上服务，请检查网络后重试。", 0);
  }
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    if (response.status === 401) window.dispatchEvent(new CustomEvent("plot18:unauthorized"));
    throw new ApiError(body?.error?.message || `发送失败（HTTP ${response.status}）`, response.status, body?.error?.code);
  }
  if (!response.body) throw new ApiError("浏览器不支持流式响应。", 0);
  let finished = false;
  for await (const line of readLines(response.body)) {
    let event: ChatEvent;
    try {
      event = JSON.parse(line) as ChatEvent;
    } catch {
      continue;
    }
    if (event && typeof event.type === "string") {
      if (event.type === "done") finished = true;
      onEvent(event);
    }
  }
  if (!finished && !signal.aborted) {
    throw new ApiError("她的话说到一半就断了，再试一次？", 0);
  }
}

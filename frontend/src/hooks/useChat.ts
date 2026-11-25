import { useCallback, useRef, useState } from "react";
import type { ChatMessage, ChatEvent, Conversation, MessagePart, Persona, RelationshipState } from "@/types";
import { compressImage, uploadImage, ApiError } from "@/api/client";
import { streamChat, type SendPayload } from "@/api/chat";
import { getConversation } from "@/api/personas";

export type ChatInitial = {
  conversation: Conversation;
  persona: Persona;
  messages: ChatMessage[];
};

let localCounter = 0;
const nextLocalId = (prefix: string) => `${prefix}-${Date.now()}-${localCounter++}`;

function assistantDraft(): ChatMessage {
  return {
    id: nextLocalId("assistant"),
    role: "assistant",
    content: "",
    parts: [],
    seq: Number.MAX_SAFE_INTEGER,
    createdAt: new Date().toISOString(),
    streaming: true,
  };
}

function upsertTool(parts: MessagePart[], event: Extract<ChatEvent, { type: "tool" }>): MessagePart[] {
  const next = [...parts];
  const index = next.findIndex((part) => part.type === "tool" && part.id === event.id);
  const part: MessagePart = {
    type: "tool",
    id: event.id,
    name: event.name,
    title: event.title,
    status: event.status,
    summary: event.summary,
  };
  if (event.status === "running") {
    const running = { ...part, summary: "正在处理…" };
    if (index >= 0) next[index] = running;
    else next.push(running);
    return next;
  }
  if (index >= 0) next[index] = part;
  else next.push(part);
  return next;
}

export function useChat(initial: ChatInitial, onChanged?: () => void) {
  const [conversation, setConversation] = useState<Conversation>(initial.conversation);
  const [persona, setPersona] = useState<Persona>(initial.persona);
  const [messages, setMessages] = useState<ChatMessage[]>(initial.messages);
  const [sending, setSending] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [notice, setNotice] = useState("");
  const [demo, setDemo] = useState(false);
  const controller = useRef<AbortController | null>(null);
  const conversationId = useRef(initial.conversation.id);

  const patchAssistant = useCallback((messageId: string, updater: (message: ChatMessage) => ChatMessage) => {
    setMessages((current) => current.map((message) => (message.id === messageId ? updater(message) : message)));
  }, []);

  const handleEvent = useCallback((event: ChatEvent, assistantId: string) => {
    if (event.type === "ping") return;
    if (event.type === "meta") {
      conversationId.current = event.conversationId;
      setDemo(event.demo);
      setConversation((current) => ({ ...current, id: event.conversationId }));
      return;
    }
    if (event.type === "state") {
      setConversation((current) => ({ ...current, state: event.state }));
      setPersona((current) => ({ ...current, relationshipState: event.state }));
      return;
    }
    if (event.type === "text") {
      patchAssistant(assistantId, (message) => ({
        ...message,
        content: message.content + event.text,
        streaming: true,
      }));
      return;
    }
    if (event.type === "tool") {
      patchAssistant(assistantId, (message) => ({ ...message, parts: upsertTool(message.parts, event) }));
      return;
    }
    if (event.type === "image" || event.type === "voice") {
      patchAssistant(assistantId, (message) => {
        if (message.parts.some((part) => (part.type === "image" || part.type === "voice") && part.fileId === event.fileId)) {
          return message;
        }
        if (event.type === "image") {
          return { ...message, parts: [...message.parts, { type: "image", fileId: event.fileId, url: event.url, caption: event.caption }] };
        }
        return { ...message, parts: [...message.parts, { type: "voice", fileId: event.fileId, url: event.url, text: event.text }] };
      });
      return;
    }
    if (event.type === "error") {
      patchAssistant(assistantId, (message) => ({
        ...message,
        streaming: false,
        error: event.error.message,
      }));
      setNotice(event.error.message);
      return;
    }
    if (event.type === "done") {
      setConversation((current) => ({ ...current, state: event.state }));
      setPersona((current) => ({ ...current, relationshipState: event.state }));
      setMessages((current) => current.map((message) => {
        if (message.id !== assistantId) return message;
        return { ...event.message, streaming: false, pending: false, error: event.error?.message || message.error };
      }));
      onChanged?.();
    }
  }, [onChanged, patchAssistant]);

  const send = useCallback(async (text: string, files: File[] = []) => {
    if (sending || uploading) return;
    const trimmed = text.trim();
    if (!trimmed && files.length === 0) return;
    setNotice("");
    setUploading(files.length > 0);
    let imageIds: string[] = [];
    const previewParts: MessagePart[] = [];
    try {
      if (files.length) {
        for (const file of files.slice(0, 4)) {
          const blob = await compressImage(file);
          const uploaded = await uploadImage(blob);
          imageIds.push(uploaded.id);
          previewParts.push({ type: "image", fileId: uploaded.id, url: uploaded.url });
        }
      }
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "照片上传失败。");
      setUploading(false);
      return;
    }
    const userMessage: ChatMessage = {
      id: nextLocalId("user"),
      role: "user",
      content: trimmed,
      parts: previewParts,
      seq: Number.MAX_SAFE_INTEGER - 1,
      createdAt: new Date().toISOString(),
      pending: true,
    };
    const assistant = assistantDraft();
    setMessages((current) => [...current, userMessage, assistant]);
    setSending(true);
    setUploading(false);
    const abort = new AbortController();
    controller.current = abort;
    const payload: SendPayload = {
      personaId: persona.id,
      conversationId: conversationId.current,
      text: trimmed,
      imageIds,
    };
    try {
      await streamChat(payload, (event) => handleEvent(event, assistant.id), abort.signal);
    } catch (error) {
      if (!abort.signal.aborted) {
        const message = error instanceof ApiError ? error.message : "连接断开了，请重试。";
        patchAssistant(assistant.id, (current) => ({ ...current, streaming: false, error: message }));
        setNotice(message);
      }
    } finally {
      setSending(false);
      setMessages((current) => current
        .map((message) => {
          if (message.id === userMessage.id) return { ...message, pending: false };
          if (message.streaming) return { ...message, streaming: false };
          return message;
        })
        .filter((message) => !(message.role === "assistant" && !message.content && message.parts.length === 0 && !message.error)));
      controller.current = null;
    }
  }, [conversationId, handleEvent, patchAssistant, persona.id, sending, uploading]);

  const regenerate = useCallback(async () => {
    if (sending) return;
    const lastUserIndex = [...messages].reverse().findIndex((message) => message.role === "user");
    if (lastUserIndex < 0) return;
    const cut = messages.length - lastUserIndex;
    setMessages((current) => current.slice(0, cut));
    const assistant = assistantDraft();
    setMessages((current) => [...current, assistant]);
    setSending(true);
    setNotice("");
    const abort = new AbortController();
    controller.current = abort;
    try {
      await streamChat({
        personaId: persona.id,
        conversationId: conversationId.current,
        text: "",
        regenerate: true,
      }, (event) => handleEvent(event, assistant.id), abort.signal);
    } catch (error) {
      if (!abort.signal.aborted) {
        const message = error instanceof ApiError ? error.message : "重试失败。";
        patchAssistant(assistant.id, (current) => ({ ...current, streaming: false, error: message }));
        setNotice(message);
      }
    } finally {
      setSending(false);
      setMessages((current) => current
        .map((message) => (message.streaming ? { ...message, streaming: false } : message))
        .filter((message) => !(message.role === "assistant" && !message.content && message.parts.length === 0 && !message.error)));
      controller.current = null;
    }
  }, [handleEvent, messages, patchAssistant, persona.id, sending]);

  const stop = useCallback(() => {
    controller.current?.abort();
    setSending(false);
    setNotice("已经停下来了。");
  }, []);

  const reload = useCallback(async () => {
    if (!conversationId.current) return;
    const data = await getConversation(conversationId.current);
    setConversation(data.conversation);
    setPersona(data.persona);
    setMessages(data.messages);
  }, []);

  const applyState = useCallback((state: RelationshipState) => {
    setConversation((current) => ({ ...current, state }));
    setPersona((current) => ({ ...current, relationshipState: state }));
  }, []);

  const load = useCallback((data: ChatInitial) => {
    conversationId.current = data.conversation.id;
    setConversation(data.conversation);
    setPersona(data.persona);
    setMessages(data.messages);
    setNotice("");
  }, []);

  return {
    conversation, persona, messages, sending, uploading, notice, setNotice, demo,
    send, regenerate, stop, reload, applyState, load,
  };
}

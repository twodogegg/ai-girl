import type { Conversation, Persona } from "@/types";
import { request } from "./client";

export type OpenPersonaResult = {
  conversation: Conversation;
  persona: Persona;
  messages: import("@/types").ChatMessage[];
};

export async function listPersonas(params: { q?: string; tag?: string } = {}): Promise<Persona[]> {
  const query = new URLSearchParams();
  if (params.q) query.set("q", params.q);
  if (params.tag) query.set("tag", params.tag);
  const suffix = query.toString() ? `?${query.toString()}` : "";
  const data = await request<{ personas: Persona[] }>(`/api/personas${suffix}`);
  return data.personas;
}

export async function getPersona(personaId: string): Promise<Persona> {
  const data = await request<{ persona: Persona }>(`/api/personas/${encodeURIComponent(personaId)}`);
  return data.persona;
}

export async function openPersona(personaId: string): Promise<OpenPersonaResult> {
  return request<OpenPersonaResult>(`/api/personas/${encodeURIComponent(personaId)}/open`, { method: "POST" });
}

export async function listConversations(): Promise<Conversation[]> {
  const data = await request<{ conversations: Conversation[] }>("/api/conversations");
  return data.conversations;
}

export async function getConversation(conversationId: string): Promise<OpenPersonaResult> {
  return request<OpenPersonaResult>(`/api/conversations/${encodeURIComponent(conversationId)}`);
}

export async function deleteConversation(conversationId: string): Promise<void> {
  await request(`/api/conversations/${encodeURIComponent(conversationId)}`, { method: "DELETE" });
}

export async function listMemories(conversationId: string) {
  const data = await request<{ memories: Array<{ id: string; content: string; kind: string; created_at: string }> }>(
    `/api/conversations/${encodeURIComponent(conversationId)}/memories`,
  );
  return data.memories;
}

export async function deleteMemory(memoryId: string): Promise<void> {
  await request(`/api/memories/${encodeURIComponent(memoryId)}`, { method: "DELETE" });
}

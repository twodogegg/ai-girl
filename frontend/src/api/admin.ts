import type { AdminPersona, AdminSkill, AdminTool } from "@/types";
import { request } from "./client";

export type Overview = {
  counts: Record<string, number>;
  recent: Array<{ id: string; displayName: string; personaName: string; lastMessageAt: string }>;
};

export async function getOverview(): Promise<Overview> {
  return request<Overview>("/api/admin/overview");
}

export async function getAdminPersonas(): Promise<AdminPersona[]> {
  const data = await request<{ personas: AdminPersona[] }>("/api/admin/personas");
  return data.personas;
}

export async function createPersona(persona: AdminPersona): Promise<AdminPersona> {
  const data = await request<{ persona: AdminPersona }>("/api/admin/personas", { method: "POST", body: persona });
  return data.persona;
}

export async function updatePersona(persona: AdminPersona): Promise<AdminPersona> {
  const data = await request<{ persona: AdminPersona }>(`/api/admin/personas/${encodeURIComponent(persona.id)}`, {
    method: "PUT", body: persona,
  });
  return data.persona;
}

export async function deletePersona(personaId: string): Promise<void> {
  await request(`/api/admin/personas/${encodeURIComponent(personaId)}`, { method: "DELETE" });
}

export async function getAdminSkills(): Promise<AdminSkill[]> {
  const data = await request<{ skills: AdminSkill[] }>("/api/admin/skills");
  return data.skills;
}

export async function saveSkill(skill: AdminSkill): Promise<AdminSkill> {
  const path = `/api/admin/skills${skill.id && skill.id !== "" ? `/${encodeURIComponent(skill.id)}` : ""}`;
  const method = skill.id ? "PUT" : "POST";
  const data = await request<{ skill: AdminSkill }>(path, { method, body: skill });
  return data.skill;
}

export async function deleteSkill(skillId: string): Promise<void> {
  await request(`/api/admin/skills/${encodeURIComponent(skillId)}`, { method: "DELETE" });
}

export async function getTools(): Promise<AdminTool[]> {
  const data = await request<{ tools: AdminTool[] }>("/api/admin/tools");
  return data.tools;
}

export type AdminUser = {
  id: string;
  username: string;
  displayName: string;
  role: string;
  disabled: boolean;
  adultConfirmed: boolean;
  createdAt: string;
};

export async function getUsers(): Promise<AdminUser[]> {
  const data = await request<{ users: AdminUser[] }>("/api/admin/users");
  return data.users;
}

export async function setUserDisabled(userId: string, disabled: boolean): Promise<void> {
  await request(`/api/admin/users/${encodeURIComponent(userId)}/disable`, { method: "POST", body: { disabled } });
}

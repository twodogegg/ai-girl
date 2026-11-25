import type { User } from "@/types";
import { request } from "./client";

export async function getMe(): Promise<User | null> {
  const data = await request<{ user: User | null }>("/api/auth/me");
  return data.user;
}

export async function login(username: string, password: string): Promise<User> {
  const data = await request<{ user: User }>("/api/auth/login", { method: "POST", body: { username, password } });
  return data.user;
}

export async function register(username: string, password: string, displayName: string): Promise<User> {
  const data = await request<{ user: User }>("/api/auth/register", {
    method: "POST",
    body: { username, password, displayName, adultConfirmed: true },
  });
  return data.user;
}

export async function guestLogin(): Promise<User> {
  const data = await request<{ user: User }>("/api/auth/guest", {
    method: "POST",
    body: { adultConfirmed: true },
  });
  return data.user;
}

export async function logout(): Promise<void> {
  await request("/api/auth/logout", { method: "POST" });
}

export async function confirmAdult(): Promise<User> {
  const data = await request<{ user: User }>("/api/auth/adult-confirm", { method: "POST" });
  return data.user;
}

export type User = {
  id: string;
  username: string;
  displayName: string;
  role: "user" | "admin";
  adultConfirmed: boolean;
  createdAt: string;
};

export type RelationshipState = {
  affinity: number;
  stage: "stranger" | "acquaintance" | "close" | "lover";
  mood: string;
  milestones: Array<{ at: string; note: string }>;
  lastSeenAt: string;
  daysKnown: number;
};

export type Persona = {
  id: string;
  name: string;
  nameZh: string;
  age: number;
  city: string;
  occupation: string;
  tagline: string;
  bio: string;
  personality: string;
  speakingStyle: string;
  relationship: string;
  languages: string[];
  tags: string[];
  palette: [string, string];
  greeting: string;
  starters: string[];
  online: boolean;
  published: boolean;
  conversationId?: string;
  relationshipState?: RelationshipState;
};

export type MessagePart =
  | { type: "image"; fileId: string; url?: string; caption?: string }
  | { type: "voice"; fileId: string; url?: string; text?: string }
  | { type: "tool"; id: string; name: string; title: string; status: "running" | "success" | "error" | "unavailable"; summary?: string }
  | { type: "text"; text: string };

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  parts: MessagePart[];
  meta?: Record<string, unknown>;
  seq: number;
  createdAt: string;
  pending?: boolean;
  streaming?: boolean;
  error?: string;
};

export type Conversation = {
  id: string;
  personaId: string;
  createdAt: string;
  updatedAt: string;
  lastMessageAt: string;
  state: RelationshipState;
  persona?: Pick<Persona, "id" | "name" | "nameZh" | "age" | "occupation" | "tagline" | "palette" | "tags">;
  preview?: string;
};

export type ChatEvent =
  | { type: "meta"; conversationId: string; messageId: string; demo: boolean }
  | { type: "state"; state: RelationshipState }
  | { type: "text"; text: string }
  | { type: "tool"; id: string; name: string; title: string; status: "running" | "success" | "error" | "unavailable"; summary?: string }
  | { type: "image"; fileId: string; url: string; caption?: string }
  | { type: "voice"; fileId: string; url: string; text?: string }
  | { type: "error"; error: { code?: string; message: string; retryable?: boolean; detail?: string } }
  | { type: "ping" }
  | { type: "done"; message: ChatMessage; state: RelationshipState; demo?: boolean; error?: { message?: string } };

export type AdminSkill = {
  id: string;
  name: string;
  description: string;
  category: string;
  instructions: string;
  alwaysOn?: boolean;
};

export type AdminPersona = Persona & {
  promptExtra?: string;
  systemPrompt?: string;
  toolIds: string[];
  skillIds: string[];
  temperature?: number;
  sort?: number;
  timezone?: string;
  voice?: string;
  model?: string;
};

export type AdminTool = {
  id: string;
  title: string;
  description: string;
  risk: string;
  available: boolean;
};

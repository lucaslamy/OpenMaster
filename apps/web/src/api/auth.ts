/** Typed same-origin account and session API. */

export interface AuthUser {
  id: string;
  email: string;
  display_name: string;
  role: "user" | "admin";
  status: "pending" | "active" | "rejected";
  created_at?: string;
}

interface ErrorPayload {
  detail?: string;
}

export class AuthApiClient {
  public constructor(private readonly baseUrl = "/api/v1/auth") {}

  public async me(): Promise<AuthUser | null> {
    const response = await fetch(`${this.baseUrl}/me`);
    if (response.status === 401) return null;
    return this.userResponse(response);
  }

  public async login(email: string, password: string): Promise<AuthUser> {
    return this.userResponse(await fetch(`${this.baseUrl}/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    }));
  }

  public async register(
    displayName: string,
    email: string,
    password: string,
  ): Promise<AuthUser> {
    return this.userResponse(await fetch(`${this.baseUrl}/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        display_name: displayName,
        email,
        password,
      }),
    }));
  }

  public async logout(): Promise<void> {
    const response = await fetch(`${this.baseUrl}/logout`, { method: "POST" });
    if (!response.ok && response.status !== 401) {
      throw new Error("Unable to close the session");
    }
  }

  public async listRequests(): Promise<AuthUser[]> {
    const response = await fetch(`${this.baseUrl}/admin/requests`);
    const payload = (await response.json()) as AuthUser[] | ErrorPayload;
    if (!response.ok || !Array.isArray(payload)) {
      throw new Error(!Array.isArray(payload) ? payload.detail ?? "Unable to load requests" : "Unable to load requests");
    }
    return payload;
  }

  public async review(userId: string, decision: "approve" | "reject"): Promise<AuthUser> {
    return this.userResponse(await fetch(
      `${this.baseUrl}/admin/requests/${encodeURIComponent(userId)}/${decision}`,
      { method: "POST" },
    ));
  }

  private async userResponse(response: Response): Promise<AuthUser> {
    const payload = (await response.json()) as AuthUser | ErrorPayload;
    if (!response.ok || !("id" in payload)) {
      throw new Error("detail" in payload ? payload.detail ?? "Account request failed" : "Account request failed");
    }
    return payload;
  }
}

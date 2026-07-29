import { describe, expect, it, vi } from "vitest";

import { AuthApiClient } from "./auth";

describe("AuthApiClient", () => {
  it("returns null when no HttpOnly session exists", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: "Authentication required" }), {
        status: 401,
        headers: { "Content-Type": "application/json" },
      }),
    ));

    await expect(new AuthApiClient("/auth").me()).resolves.toBeNull();
  });

  it("registers without storing or returning a session token", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({
        id: "user-1",
        email: "artist@example.com",
        display_name: "Artist",
        role: "user",
        status: "pending",
      }), { status: 202, headers: { "Content-Type": "application/json" } }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const user = await new AuthApiClient("/auth").register(
      "Artist",
      "artist@example.com",
      "long-password",
    );

    expect(user.display_name).toBe("Artist");
    expect(fetchMock).toHaveBeenCalledWith("/auth/register", expect.objectContaining({
      method: "POST",
      body: JSON.stringify({
        display_name: "Artist",
        email: "artist@example.com",
        password: "long-password",
      }),
    }));
    expect("token" in user).toBe(false);
  });

  it("lists pending requests for the administrator", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(
      new Response(JSON.stringify([{
        id: "pending-1",
        email: "pending@example.com",
        display_name: "Pending",
        role: "user",
        status: "pending",
      }]), { status: 200, headers: { "Content-Type": "application/json" } }),
    ));

    const requests = await new AuthApiClient("/auth").listRequests();

    expect(requests).toHaveLength(1);
    expect(requests[0]?.status).toBe("pending");
  });
});

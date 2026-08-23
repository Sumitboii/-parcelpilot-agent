/**
 * useSSE.test.ts — unit tests for the streamSSE async generator (task 11.2)
 *
 * Uses Vitest with a mocked fetch. Run with: npm test (requires vitest in devDependencies).
 *
 * Install: npm install -D vitest
 * Add to package.json scripts: "test": "vitest run"
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { streamSSE } from "./useSSE";

// ── Helpers ──────────────────────────────────────────────────────────────────

function makeStream(chunks: string[]): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();
  return new ReadableStream({
    start(controller) {
      for (const chunk of chunks) {
        controller.enqueue(encoder.encode(chunk));
      }
      controller.close();
    },
  });
}

function mockFetch(body: string) {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      statusText: "OK",
      body: makeStream([body]),
    })
  );
}

// ── Tests ────────────────────────────────────────────────────────────────────

describe("streamSSE", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("yields tool_chip event before token events", async () => {
    const sse =
      'event: tool_chip\ndata: {"tool":"document_search"}\n\n' +
      'event: token\ndata: {"text":"Yes"}\n\n' +
      'event: done\ndata: {}\n\n';
    mockFetch(sse);

    const events = [];
    for await (const ev of streamSSE("/chat", { message: "test" })) {
      events.push(ev.event);
    }
    expect(events[0]).toBe("tool_chip");
    expect(events).toContain("token");
  });

  it("parses pending_confirmation as a structured object, not a string", async () => {
    const payload = {
      type: "pending_confirmation",
      action: "escalate",
      display: { Action: "Create Escalation", Ticket: "TKT-501" },
      payload: {},
    };
    const sse = `event: pending_confirmation\ndata: ${JSON.stringify(payload)}\n\ndone\ndata: {}\n\n`;
    mockFetch(sse);

    const events = [];
    for await (const ev of streamSSE("/chat", {})) {
      events.push(ev);
    }
    const confEv = events.find((e) => e.event === "pending_confirmation");
    expect(confEv).toBeDefined();
    expect(typeof confEv!.data).toBe("object");
    expect((confEv!.data as typeof payload).type).toBe("pending_confirmation");
  });

  it("terminates after done event", async () => {
    const sse =
      'event: token\ndata: {"text":"Hello"}\n\n' +
      'event: done\ndata: {}\n\n' +
      'event: token\ndata: {"text":"should not appear"}\n\n';
    mockFetch(sse);

    const events = [];
    for await (const ev of streamSSE("/chat", {})) {
      events.push(ev);
    }
    const afterDone = events.slice(events.findIndex((e) => e.event === "done") + 1);
    expect(afterDone).toHaveLength(0);
  });

  it("terminates after error event", async () => {
    const sse =
      'event: error\ndata: {"message":"rate limited"}\n\n' +
      'event: token\ndata: {"text":"should not appear"}\n\n';
    mockFetch(sse);

    const events = [];
    for await (const ev of streamSSE("/chat", {})) {
      events.push(ev);
    }
    expect(events[events.length - 1].event).toBe("error");
    expect(events).toHaveLength(1);
  });

  it("yields an error event on non-OK HTTP response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: false, status: 500, statusText: "Internal Server Error", body: null })
    );

    const events = [];
    for await (const ev of streamSSE("/chat", {})) {
      events.push(ev);
    }
    expect(events[0].event).toBe("error");
  });
});

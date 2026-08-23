/**
 * useSSE.ts — Async generator for POST-based Server-Sent Events.
 *
 * Uses fetch() + ReadableStream, NOT EventSource, because the /chat endpoint
 * is POST (carries the message body). EventSource only supports GET.
 */

export interface SSEEvent {
  event: string;
  data: unknown;
}

/**
 * Stream SSE events from a POST endpoint.
 * Yields parsed {event, data} objects for: tool_chip, token, pending_confirmation, done, error.
 */
export async function* streamSSE(
  url: string,
  body: object
): AsyncGenerator<SSEEvent> {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!response.ok || !response.body) {
    yield {
      event: "error",
      data: { message: `HTTP ${response.status}: ${response.statusText}` },
    };
    return;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    // Parse SSE events from buffer
    // SSE format: "event: X\ndata: {...}\n\n"
    const events = buffer.split("\n\n");
    buffer = events.pop() ?? ""; // last incomplete chunk stays in buffer

    for (const eventBlock of events) {
      if (!eventBlock.trim()) continue;

      let eventType = "message";
      let dataStr = "";

      for (const line of eventBlock.split("\n")) {
        if (line.startsWith("event: ")) {
          eventType = line.slice(7).trim();
        } else if (line.startsWith("data: ")) {
          dataStr = line.slice(6);
        }
      }

      let parsedData: unknown = dataStr;
      try {
        parsedData = JSON.parse(dataStr);
      } catch {
        // leave as string if not JSON
      }

      yield { event: eventType, data: parsedData };

      // Stop after done or error
      if (eventType === "done" || eventType === "error") return;
    }
  }
}

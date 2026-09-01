import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { App } from "./App";

describe("App", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("reports the backend as ready when its health endpoint responds", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        if (input !== "http://localhost:8000/health") {
          throw new Error(`Unexpected request: ${String(input)}`);
        }
        return new Response(JSON.stringify({ status: "ok", service: "backend" }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }),
    );

    render(<App />);

    expect(await screen.findByText("Backend ready")).toBeInTheDocument();
  });
});


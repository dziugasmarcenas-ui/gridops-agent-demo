import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { App } from "./App";

describe("App", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders the question form and demo shortcut buttons", () => {
    render(<App />);

    expect(screen.getByPlaceholderText(/What caused INC-1042/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Flow A/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Flow B/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Flow C/ })).toBeInTheDocument();
  });

  it("shows the agent's answer after asking a question", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(
          JSON.stringify({
            answer: "The available incident data does not contain a confirmed cause.",
            tool_calls: [],
            incidents: [],
            procedures: [],
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      ),
    );

    render(<App />);
    screen.getByRole("button", { name: /Flow C/ }).click();

    expect(await screen.findByText(/does not contain a confirmed cause/)).toBeInTheDocument();
  });
});

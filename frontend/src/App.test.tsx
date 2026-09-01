import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { App } from "./App";

describe("App", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders the Lithuanian question form and demo shortcut buttons", () => {
    render(<App />);

    expect(screen.getByPlaceholderText(/Kokia yra patvirtinta INC-1042 priežastis/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /A: Prioritetai šį rytą/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /B: Eskalavimo juodraštis/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /C: Kas sukėlė INC-1042/ })).toBeInTheDocument();
    expect(screen.getByText(/sintetiniai/)).toBeInTheDocument();
  });

  it("shows the agent's Lithuanian answer after asking the null-cause question", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(
          JSON.stringify({
            answer: "Turimuose incidento duomenyse patvirtinta INC-1042 priežastis nenurodyta.",
            tool_calls: [],
            incidents: [],
            procedures: [],
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      ),
    );

    render(<App />);
    screen.getByRole("button", { name: /C: Kas sukėlė INC-1042/ }).click();

    expect(await screen.findByText(/priežastis nenurodyta/)).toBeInTheDocument();
  });
});

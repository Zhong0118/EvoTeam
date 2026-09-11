import { afterEach, describe, expect, it, vi } from "vitest";
import { locateFlowElement, registerFlowElement } from "./flow-registry";

afterEach(() => {
  document.body.innerHTML = "";
  vi.useRealTimers();
});

describe("flow registry (V3 §22)", () => {
  it("registerFlowElement stamps the stable data-flow-key", () => {
    const el = document.createElement("div");
    document.body.append(el);
    const dispose = registerFlowElement("agent-run:run-1:planner-1", el);
    expect(el.dataset.flowKey).toBe("agent-run:run-1:planner-1");
    dispose();
    expect(el.getAttribute("data-flow-key")).toBeNull();
  });

  it("locate flashes every element sharing a key (Chat row + Graph node)", () => {
    const chat = document.createElement("div");
    const graphNode = document.createElement("div");
    chat.setAttribute("data-flow-key", "tool:call-1");
    graphNode.setAttribute("data-flow-key", "tool:call-1");
    document.body.append(chat, graphNode);
    expect(locateFlowElement("tool:call-1")).toBe(true);
    expect(chat.classList.contains("ws-locate-flash")).toBe(true);
    expect(graphNode.classList.contains("ws-locate-flash")).toBe(true);
  });

  it("missing keys resolve once the element mounts (async render)", async () => {
    expect(locateFlowElement("event:later-1")).toBe(false);
    const late = document.createElement("div");
    late.setAttribute("data-flow-key", "event:later-1");
    document.body.append(late);
    // The MutationObserver callback is a real microtask: wait it out.
    await vi.waitFor(() => {
      expect(late.classList.contains("ws-locate-flash")).toBe(true);
    });
  });

  it("timeouts report unresolvable keys instead of hanging", () => {
    vi.useFakeTimers();
    const onTimeout = vi.fn();
    locateFlowElement("agent-run:ghost", { timeoutMs: 50, onTimeout });
    vi.advanceTimersByTime(60);
    expect(onTimeout).toHaveBeenCalledOnce();
  });
});

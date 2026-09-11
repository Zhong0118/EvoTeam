/* Chat <-> Graph locate registry — V3 §22. Elements mark themselves with a
   stable `data-flow-key`; the same run may be registered twice (a Chat row
   and a Graph node), and locating scrolls + flashes every element of that
   key inside its own scroll container. When nothing is mounted yet (async
   render), a MutationObserver waits for the key, bounded by a timeout — the
   locator pattern studied in DSH Plan Graph's client.body.js. */

const KEY_ATTRIBUTE = "data-flow-key";

export function registerFlowElement(key: string, el: HTMLElement): () => void {
  el.setAttribute(KEY_ATTRIBUTE, key);
  return () => {
    if (el.getAttribute(KEY_ATTRIBUTE) === key)
      el.removeAttribute(KEY_ATTRIBUTE);
  };
}

export function escapeKey(key: string): string {
  return typeof CSS !== "undefined" && CSS.escape
    ? CSS.escape(key)
    : key.replace(/["\\]/g, "\\$&");
}

let clearFlash: (() => void) | null = null;

interface PendingLocate {
  observer: MutationObserver;
  timer: number;
  key: string;
}
let pending: PendingLocate | null = null;

function settle(el: Element | null): boolean {
  if (!(el instanceof HTMLElement)) return false;
  el.scrollIntoView({ behavior: "smooth", block: "center" });
  el.classList.add("ws-locate-flash");
  const id = window.setTimeout(() => {
    document
      .querySelectorAll(".ws-locate-flash")
      .forEach((node) => node.classList.remove("ws-locate-flash"));
    clearFlash = null;
  }, 1400);
  clearFlash = () => window.clearTimeout(id);
  return true;
}

const selector = (key: string) =>
  `[${KEY_ATTRIBUTE}="${escapeKey(key)}"]`;

/** Returns false when the key cannot be resolved even after waiting. */
export function locateFlowElement(
  key: string,
  options: { timeoutMs?: number; onTimeout?: () => void } = {},
): boolean {
  clearFlash?.();
  if (pending) {
    pending.observer.disconnect();
    window.clearTimeout(pending.timer);
    pending = null;
  }
  const found = document.querySelectorAll(selector(key));
  if (found.length) {
    // Scroll every element of this key into view in its own container and
    // flash it: Chat row + Graph node move together.
    found.forEach((el) => {
      if (el instanceof HTMLElement)
        el.scrollIntoView({ behavior: "smooth", block: "center" });
    });
    found.forEach((el) => el.classList.add("ws-locate-flash"));
    window.setTimeout(
      () =>
        document
          .querySelectorAll(".ws-locate-flash")
          .forEach((node) => node.classList.remove("ws-locate-flash")),
      1400,
    );
    return true;
  }
  // A later locate supersedes an unfinished wait: each attempt owns its
  // observer + timer through the `pending` closure, so a stale timeout can
  // never disconnect the current attempt.
  const attempt: { observer: MutationObserver; timer: number; key: string } = {
    observer: null as unknown as MutationObserver,
    timer: 0,
    key,
  };
  attempt.observer = new MutationObserver(() => {
    if (settle(document.querySelector(selector(key)))) {
      attempt.observer.disconnect();
      window.clearTimeout(attempt.timer);
      if (pending === attempt) pending = null;
    }
  });
  attempt.observer.observe(document.body, { childList: true, subtree: true });
  attempt.timer = window.setTimeout(() => {
    if (pending !== attempt) return;
    pending = null;
    attempt.observer.disconnect();
    options.onTimeout?.();
  }, options.timeoutMs ?? 10000);
  pending = attempt;
  return false;
}

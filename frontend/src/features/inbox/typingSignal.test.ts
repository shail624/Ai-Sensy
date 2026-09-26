import { renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const { post } = vi.hoisted(() => ({ post: vi.fn(() => Promise.resolve({ data: { sent: true } })) }));
vi.mock("@/lib/api/client", () => ({ api: { POST: post } }));

import { TYPING_SIGNAL_INTERVAL_MS, useTypingSignal } from "./api";

describe("useTypingSignal", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    post.mockClear();
  });
  afterEach(() => vi.useRealTimers());

  it("sends at most one signal per interval while the agent keeps typing", () => {
    const { result } = renderHook(() => useTypingSignal("c1", true));
    result.current();
    result.current();
    vi.advanceTimersByTime(TYPING_SIGNAL_INTERVAL_MS - 1);
    result.current();
    expect(post).toHaveBeenCalledTimes(1);
    vi.advanceTimersByTime(1);
    result.current();
    expect(post).toHaveBeenCalledTimes(2);
    expect(post).toHaveBeenCalledWith("/api/v1/conversations/{conversation_id}/typing", {
      params: { path: { conversation_id: "c1" } },
    });
  });

  it("sends nothing when disabled", () => {
    const { result } = renderHook(() => useTypingSignal("c1", false));
    result.current();
    expect(post).not.toHaveBeenCalled();
  });
});

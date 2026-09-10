import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it } from "vitest";
import { CopyId, number } from "./common";
it("unknown usage is not represented as zero", () => {
  expect(number(null)).toBe("未提供");
  expect(number(0)).toBe("0");
});
it("copies the full ID rather than its shortened display", async () => {
  const user = userEvent.setup();
  render(<CopyId id="a-long-run-identifier" />);
  await user.click(
    screen.getByRole("button", { name: "复制 a-long-run-identifier" }),
  );
  expect(await navigator.clipboard.readText()).toBe("a-long-run-identifier");
  expect(screen.getByRole("status")).toHaveTextContent("已复制");
});

import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";
import { current, candidate } from "../../fixtures/evidence";
import { StrategyDiff } from "./strategy-diff";
it("identifies changed prompt references without implying improved performance", () => {
  render(<StrategyDiff left={current} right={candidate} />);
  expect(screen.getByText("修改")).toBeVisible();
  expect(screen.getByText("executor.prompt_ref")).toBeVisible();
  expect(screen.queryByText("收益")).not.toBeInTheDocument();
});

import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";
afterEach(cleanup);
// jsdom has no layout engine; locate code calls scrollIntoView on targets.
Element.prototype.scrollIntoView = () => {};

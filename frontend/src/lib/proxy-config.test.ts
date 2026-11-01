// @vitest-environment node
import { expect, test } from "vitest";
import config from "../../vite.config";

test("Vite forwards API requests to the local FastAPI server", () => {
  expect(config.server?.proxy?.["/api"]).toMatchObject({
    target: "http://127.0.0.1:8000",
    changeOrigin: true,
  });
});

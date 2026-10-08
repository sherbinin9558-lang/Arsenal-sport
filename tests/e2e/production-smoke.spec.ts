import { test, expect } from "@playwright/test";

test.describe("production smoke", () => {
  test("loads the application shell without a frontend preload error", async ({ page }) => {
    const consoleErrors: string[] = [];
    page.on("console", (msg) => {
      if (msg.type() === "error") consoleErrors.push(msg.text());
    });

    const failedRequests: string[] = [];
    page.on("requestfailed", (request) => {
      failedRequests.push(
        `${request.method()} ${request.url()} :: ${request.failure()?.errorText ?? "failed"}`
      );
    });

    await page.goto("/", { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(3000);

    const bodyText = await page.locator("body").innerText();
    expect(bodyText).not.toContain("Unexpected Application Error");
    expect(bodyText).not.toContain("Unable to preload CSS");

    const title = await page.title();
    expect(title).not.toBe("");

    const criticalFailures = failedRequests.filter((x) =>
      /\\.(css|js)(\\?|$)/i.test(x) || /preload/i.test(x)
    );
    expect(criticalFailures, criticalFailures.join("\\n")).toEqual([]);

    expect(consoleErrors.filter((x) => /preload|chunk|module|uncaught/i.test(x))).toEqual([]);
  });
});

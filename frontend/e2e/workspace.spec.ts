import { expect, test, type Page } from "@playwright/test";
import { randomUUID } from "node:crypto";

const base = process.env.E2E_BASE_URL || "http://localhost:3000";
const adminEmail = process.env.E2E_ADMIN_EMAIL || "";
const adminPassword = process.env.E2E_ADMIN_PASSWORD || "";
const demoPassword = process.env.E2E_DEMO_PASSWORD || "";
const changed = process.env.E2E_CHANGED_PASSWORD || "";

async function login(page: Page, email: string, password: string, demo = false) {
  await page.goto("/login");
  if (email === adminEmail || email.includes("supervisor@")) await page.getByRole("button", { name: "Supervisor / Admin" }).click();
  else if (email.includes("doctor@")) await page.getByRole("button", { name: "Doctor", exact: true }).click();
  await page.getByLabel("Email address").fill(email);
  await page.locator("#auth-password").fill(password);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page).toHaveURL(/\/workspace$/);
  if (demo) {
    const welcome = page.getByRole("heading", { name: /Welcome,/ });
    const temporary = page.getByRole("heading", { name: "Change your temporary password" });
    await expect(welcome.or(temporary)).toBeVisible();
    if (await temporary.isVisible()) {
      expect(changed, "Set E2E_CHANGED_PASSWORD for temporary accounts").toBeTruthy();
      await page.getByLabel("Current password").fill(password);
      await page.getByLabel("New password").fill(changed);
      await page.getByRole("button", { name: "Change password", exact: true }).click();
      await expect(page).toHaveURL(/\/login$/);
      await login(page, email, changed);
    }
  }
  await expect(page.getByRole("heading", { name: /Welcome,/ })).toBeVisible();
}

test("public homepage fits desktop, tablet and mobile", async ({ page }, info) => {
  for (const width of [1440, 820, 390]) {
    await page.setViewportSize({ width, height: 950 });
    await page.goto("/");
    await expect(page.getByRole("heading", { name: "Care works better together." })).toBeVisible();
    await expect(page.getByRole("img", { name: /Illustrative portrait/ })).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width);
    await page.screenshot({ path: info.outputPath(`home-${width}.png`) });
  }
});

test("BFF rejects a missing token, foreign origin and unlisted route", async ({ request }) => {
  const endpoint = "/api/medora/";
  expect((await request.get(endpoint + "auth/me")).status()).toBe(401);
  expect((await request.post(endpoint + "auth/login", { data: {}, headers: { Origin: base } })).status()).toBe(403);
  const { token } = await (await request.get(endpoint + "csrf")).json();
  expect((await request.post(endpoint + "auth/login", {
    data: {}, headers: { Origin: "https://outside.example", "x-csrf-token": token },
  })).status()).toBe(403);
  expect((await request.post(endpoint + "auth/login", {
    data: {}, headers: { Origin: base, "x-csrf-token": token },
  })).status()).toBe(400);
  expect((await request.get(endpoint + "admin")).status()).toBe(404);
});

test("patient registration, self edit, directory, assistant and logout", async ({ page, context }) => {
  await page.goto("/register");
  await page.getByLabel("Full name").fill("Taylor Test");
  await page.getByLabel("Email address").fill(`patient-${randomUUID()}@medora.example`);
  await page.locator("#auth-password").fill("Synthetic-browser-test-$592f");
  await page.getByRole("button", { name: "Create account", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Welcome, Taylor" })).toBeVisible();
  const cookies = await context.cookies();
  expect(cookies.filter((cookie) => /medora_(access|refresh)/.test(cookie.name)).every((cookie) => cookie.httpOnly)).toBeTruthy();
  const sessions = cookies.filter((cookie) => /medora_(access|refresh)/.test(cookie.name));
  expect(sessions).toHaveLength(2);
  if (process.env.E2E_EXPECT_SECURE === "1") {
    expect(sessions.every((cookie) => cookie.secure && cookie.name.startsWith("__Host-"))).toBeTruthy();
  }
  const nav = page.getByRole("navigation", { name: "Workspace navigation" });
  await nav.getByRole("button", { name: "My profile" }).click();
  await page.getByRole("button", { name: "Edit profile" }).click();
  await page.getByRole("dialog").getByLabel("Phone", { exact: true }).fill("+1 555 012 3456");
  await page.getByRole("button", { name: "Save changes" }).click();
  await expect(page.getByText("+15550123456")).toBeVisible();
  await nav.getByRole("button", { name: "Doctor directory" }).click();
  await expect(page.getByRole("heading", { name: "Doctor directory" })).toBeVisible();
  await page.getByRole("button", { name: "Open workspace assistant" }).click();
  await page.getByRole("button", { name: "How do I find my assigned doctors?" }).click();
  await expect(page.getByText(/Open My care team/)).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("button", { name: "Open workspace assistant" })).toBeFocused();
  await page.locator(".account-menu summary").click();
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await expect(page).toHaveURL(/\/login$/);
  expect((await context.cookies()).filter((cookie) => /medora_(access|refresh)/.test(cookie.name))).toHaveLength(0);
});

test("super admin creates and suspends a supervisor and views audit", async ({ page }, info) => {
  test.skip(!adminEmail || !adminPassword, "Requires a disposable admin account.");
  await login(page, adminEmail, adminPassword);
  await page.screenshot({ path: info.outputPath("admin-overview.png") });
  const nav = page.getByRole("navigation", { name: "Workspace navigation" });
  await nav.getByRole("button", { name: "Supervisors" }).click();
  await page.getByRole("button", { name: "Add supervisor" }).click();
  const email = `sup-${randomUUID()}@medora.example`;
  const dialog = page.getByRole("dialog");
  await dialog.getByLabel("Full name").fill("Avery Test");
  await dialog.getByLabel("Email address").fill(email);
  await dialog.getByLabel("Temporary password").fill("Synthetic-browser-test-$592f");
  await dialog.getByRole("button", { name: "Create account" }).click();
  await page.getByPlaceholder("Name or email").fill(email);
  await page.getByRole("row").filter({ hasText: email }).getByRole("button", { name: "Suspend" }).click();
  await page.getByRole("button", { name: "Confirm", exact: true }).click();
  await expect(page.getByRole("row").filter({ hasText: email }).getByText("Inactive")).toBeVisible();
  await nav.getByRole("button", { name: "Audit log" }).click();
  await expect(page.getByRole("heading", { name: "Audit log" })).toBeVisible();
  await expect(page.getByRole("cell", { name: "Success" }).first()).toBeVisible();
});

test("supervisor can end and reassign a doctor", async ({ page }) => {
  test.skip(!demoPassword, "Requires seeded disposable demo accounts.");
  await login(page, "supervisor@medora.example", demoPassword, true);
  await page.getByRole("navigation").getByRole("button", { name: "Assignments" }).click();
  const current = page.getByRole("row").filter({ hasText: "Jamie Rao" }).getByRole("button", { name: "End assignment" });
  await current.click();
  await page.getByRole("button", { name: "Confirm" }).click();
  await expect(page.getByRole("row").filter({ hasText: "Jamie Rao" }).getByRole("cell", { name: "Ended" }).first()).toBeVisible();
  await page.getByRole("button", { name: "Assign doctor", exact: true }).click();
  const dialog = page.getByRole("dialog");
  await dialog.getByRole("button", { name: "Jamie Rao" }).click();
  await dialog.getByRole("button", { name: "Morgan Iyer" }).click();
  await dialog.getByRole("button", { name: "Assign doctor" }).click();
  await expect(current).toBeVisible();
});

test("doctor sees assigned patient on mobile", async ({ page }, info) => {
  test.skip(!demoPassword, "Requires seeded disposable demo accounts.");
  await page.setViewportSize({ width: 390, height: 844 });
  await login(page, "doctor@medora.example", demoPassword, true);
  await page.getByRole("button", { name: "Toggle navigation" }).click();
  await page.getByRole("navigation").getByRole("button", { name: "Assigned patients" }).click();
  await page.getByRole("row").filter({ hasText: "Jamie Rao" }).getByRole("button", { name: "View" }).click();
  await expect(page.getByRole("dialog").getByText("Medical history")).toBeVisible();
  await expect(page.getByRole("dialog").getByText("Email address")).toHaveCount(0);
  await page.screenshot({ path: info.outputPath("doctor-mobile.png") });
});

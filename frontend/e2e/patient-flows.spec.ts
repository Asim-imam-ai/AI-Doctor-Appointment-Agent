import { expect, test, type Page } from "@playwright/test";

const doctor = {
  id: "doctor-1",
  name: "Dr. Amira Khan",
  specialties: ["Cardiology"],
  clinic_name: "Central Clinic",
  location: "Karachi",
  bio: "Cardiology consultations.",
  consultation_duration: 30,
  is_active: true,
};
const slot = {
  id: "slot-1",
  doctor_id: doctor.id,
  doctor_name: doctor.name,
  specialty: "Cardiology",
  clinic_name: doctor.clinic_name,
  location: doctor.location,
  start_time: "2026-11-20T10:00:00Z",
  end_time: "2026-11-20T10:30:00Z",
  timezone: "UTC",
  status: "AVAILABLE",
};
const appointment = {
  id: "appointment-1",
  doctor_id: doctor.id,
  patient_id: "patient-1",
  start_time: "2026-11-20T10:00:00Z",
  end_time: "2026-11-20T10:30:00Z",
  reason: null,
  status: "CONFIRMED",
  created_at: "2026-11-01T10:00:00Z",
};
const bookingProposal = {
  booking_request_id: "booking-1",
  proposal_version: 1,
  doctor_name: doctor.name,
  start_time: slot.start_time,
  end_time: slot.end_time,
  clinic_name: doctor.clinic_name,
  expires_at: "2026-11-20T09:00:00Z",
  reason: null,
};
const cancellationProposal = {
  cancellation_request_id: "cancel-1",
  proposal_version: 1,
  doctor_name: doctor.name,
  appointment_start: appointment.start_time,
  expires_at: "2026-11-20T09:00:00Z",
};
const reschedulingProposal = {
  reschedule_request_id: "move-1",
  proposal_version: 1,
  doctor_name: doctor.name,
  old_start_time: appointment.start_time,
  new_start_time: "2026-11-21T10:00:00Z",
  expires_at: "2026-11-20T09:00:00Z",
};
const user = {
  id: "8f4714d3-9080-4a0d-aad5-19c584c94c9d",
  email: "patient@example.com",
  app_metadata: {},
  user_metadata: {},
  aud: "authenticated",
  created_at: "2026-11-01T00:00:00Z",
};

async function signedIn(page: Page) {
  await page.addInitScript(
    ({ user }) => {
      localStorage.setItem(
        "sb-e2e-auth-token",
        JSON.stringify({
          access_token: "e2e-token",
          refresh_token: "e2e-refresh",
          token_type: "bearer",
          expires_at: Math.floor(Date.now() / 1000) + 3600,
          expires_in: 3600,
          user,
        }),
      );
    },
    { user },
  );
}

async function mockApi(page: Page) {
  let chatSent = false;
  await page.route("**/api/v1/**", async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    const method = request.method();
    let body: unknown = {};
    if (path === "/api/v1/patients/me")
      body = {
        name: "Test Patient",
        email: user.email,
        phone: null,
        timezone: "UTC",
      };
    else if (path === "/api/v1/appointments" && method === "GET")
      body = [appointment];
    else if (path === "/api/v1/appointments/appointment-1" && method === "GET")
      body = appointment;
    else if (path === "/api/v1/doctors/search")
      body = {
        status: "success",
        message: "Doctor search completed.",
        doctors: [doctor],
      };
    else if (path === "/api/v1/availability/search")
      body = { status: "success", message: "Slots found.", slots: [slot] };
    else if (path === "/api/v1/appointments/prepare")
      body = {
        status: "success",
        message: "Prepared.",
        proposal: bookingProposal,
      };
    else if (path === "/api/v1/appointments/booking-1/approve")
      body = {
        status: "success",
        message: "Booking confirmed.",
        booking_result: { status: "BOOKED", appointment_id: appointment.id },
      };
    else if (path === "/api/v1/appointments/cancel/prepare")
      body = {
        status: "success",
        message: "Prepared.",
        proposal: cancellationProposal,
      };
    else if (path === "/api/v1/appointments/cancel/cancel-1/approve")
      body = {
        status: "success",
        message: "Appointment cancelled.",
        cancellation_result: {
          status: "BOOKED",
          appointment_id: appointment.id,
        },
      };
    else if (path === "/api/v1/appointments/reschedule/prepare")
      body = {
        status: "success",
        message: "Prepared.",
        proposal: reschedulingProposal,
      };
    else if (path === "/api/v1/appointments/reschedule/move-1/approve")
      body = {
        status: "success",
        message: "Appointment rescheduled.",
        rescheduling_result: {
          status: "BOOKED",
          appointment_id: appointment.id,
        },
      };
    else if (path === "/api/v1/conversations" && method === "GET")
      body = { conversations: [] };
    else if (path === "/api/v1/conversations" && method === "POST")
      body = {
        id: "conversation-1",
        title: "New conversation",
        status: "ACTIVE",
        last_message_at: "2026-11-01T10:00:00Z",
        summary: null,
      };
    else if (path === "/api/v1/conversations/conversation-1")
      body = {
        id: "conversation-1",
        title: "New conversation",
        status: "ACTIVE",
        last_message_at: "2026-11-01T10:00:00Z",
        summary: null,
        messages: chatSent
          ? [
              {
                id: "message-1",
                role: "ASSISTANT",
                content: "I can help you find a doctor.",
                created_at: "2026-11-01T10:00:00Z",
              },
            ]
          : [],
      };
    else if (path === "/api/v1/chat") {
      chatSent = true;
      body = {
        session_id: "conversation-1",
        message: "I can help you find a doctor.",
        requires_hitl: false,
        action_type: "doctor_discovery",
      };
    } else if (path === "/api/v1/conversations/memory") body = { memories: [] };
    else if (path === "/api/v1/knowledge/search")
      body = {
        answer: "The policy document does not specify.",
        grounded: false,
        sources: [],
      };
    else return route.fulfill({ status: 404, body: "{}" });
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(body),
    });
  });
}

test("public landing and mobile navigation work", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: /find the right doctor/i }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Open menu" }).click();
  await expect(
    page
      .getByRole("navigation", { name: "Public navigation" })
      .getByRole("link", { name: "Get started" }),
  ).toBeVisible();
});
test("unauthenticated patient is sent to sign in", async ({ page }) => {
  await page.goto("/appointments");
  await expect(page).toHaveURL(/\/login$/);
});
test("patient can sign in and reach the dashboard", async ({ page }) => {
  await mockApi(page);
  await page.route("**/auth/v1/token?grant_type=password", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        access_token: "e2e-token",
        refresh_token: "e2e-refresh",
        token_type: "bearer",
        expires_in: 3600,
        user,
      }),
    }),
  );
  await page.goto("/login");
  await page.getByLabel("Email address").fill(user.email);
  await page.getByLabel("Password").fill("password123");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(
    page.getByRole("heading", { name: "Welcome back" }),
  ).toBeVisible();
});
test("patient can find a doctor and open the profile", async ({ page }) => {
  await signedIn(page);
  await mockApi(page);
  await page.goto("/doctors");
  await page.getByLabel("Search doctors").fill("Amira");
  await page.getByRole("button", { name: "Search" }).click();
  await page.getByRole("link", { name: /view profile/i }).click();
  await expect(page.getByRole("heading", { name: doctor.name })).toBeVisible();
});
test("patient can view live slots and prepare a booking", async ({ page }) => {
  await signedIn(page);
  await mockApi(page);
  await page.goto("/availability/doctor-1");
  await page.getByLabel("Appointment date").fill("2026-11-20");
  await page.getByRole("button", { name: "Check availability" }).click();
  await page.getByRole("button", { name: "Select time" }).click();
  await page.getByRole("button", { name: "Prepare booking request" }).click();
  await expect(page.getByRole("dialog")).toContainText(doctor.name);
  await page.getByRole("button", { name: "Confirm booking" }).click();
  await expect(page.getByRole("dialog")).toContainText("Booking confirmed.");
});
test("cancellation needs explicit review and approval", async ({ page }) => {
  await signedIn(page);
  await mockApi(page);
  await page.goto("/appointments/appointment-1");
  await page.getByRole("button", { name: "Request cancellation" }).click();
  await expect(page.getByRole("dialog")).toContainText("cancellation");
  await page.getByRole("button", { name: "Confirm cancellation" }).click();
  await expect(page.getByRole("dialog")).toContainText(
    "Appointment cancelled.",
  );
});
test("rescheduling shows the original and new time before approval", async ({
  page,
}) => {
  await signedIn(page);
  await mockApi(page);
  await page.goto("/appointments/appointment-1");
  await page.getByLabel("New date").fill("2026-11-21");
  await page.getByRole("button", { name: "Find replacement slots" }).click();
  await page.locator(".slot-choice").first().click();
  await expect(page.locator(".slot-choice").first()).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  await page.getByRole("button", { name: "Review reschedule request" }).click();
  await expect(page.getByRole("dialog")).toContainText("Current time");
  await page.getByRole("button", { name: "Confirm reschedule" }).click();
  await expect(page.getByRole("dialog")).toContainText(
    "Appointment rescheduled.",
  );
});

test("mobile patient navigation moves focus into the menu and restores it on Escape", async ({
  page,
}) => {
  await signedIn(page);
  await mockApi(page);
  await page.setViewportSize({ width: 375, height: 850 });
  await page.goto("/dashboard");
  const navigation = page.getByRole("navigation", {
    name: "Primary navigation",
    includeHidden: true,
  });
  await expect(navigation).toBeHidden();
  const open = page.getByRole("button", { name: "Open navigation" });
  await open.focus();
  await page.keyboard.press("Enter");
  await expect(navigation).toBeVisible();
  await expect(page.locator("#patient-navigation .brand")).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(navigation).toBeHidden();
  await expect(open).toBeFocused();
});

test("a cancellation request without a proposal explains the backend response", async ({
  page,
}) => {
  await signedIn(page);
  await mockApi(page);
  await page.route("**/api/v1/appointments/cancel/prepare", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        status: "success",
        message: "This appointment cannot be cancelled online.",
        proposal: null,
      }),
    }),
  );
  await page.goto("/appointments/appointment-1");
  await page.getByRole("button", { name: "Request cancellation" }).click();
  await expect(page.getByRole("status")).toContainText(
    "This appointment cannot be cancelled online.",
  );
});
test("assistant conversation receives and displays the backend reply", async ({
  page,
}) => {
  await signedIn(page);
  await mockApi(page);
  await page.goto("/chat");
  await page.getByRole("textbox", { name: "Message" }).fill("Find a doctor");
  await page.getByRole("button", { name: "Send" }).click();
  await expect(page.getByText("I can help you find a doctor.")).toBeVisible();
});
test("patient pages fit mobile, tablet, and desktop widths", async ({
  page,
}) => {
  await signedIn(page);
  await mockApi(page);
  for (const width of [375, 768, 1280]) {
    await page.setViewportSize({ width, height: 850 });
    await page.goto("/dashboard");
    await expect(
      page.getByRole("heading", { name: "Welcome back" }),
    ).toBeVisible();
    expect(
      await page.evaluate(() => document.documentElement.scrollWidth),
    ).toBeLessThanOrEqual(width);
    await page.goto("/doctors");
    await expect(
      page.getByRole("heading", { name: "Find a doctor" }),
    ).toBeVisible();
    expect(
      await page.evaluate(() => document.documentElement.scrollWidth),
    ).toBeLessThanOrEqual(width);
  }
});
test("rejecting a booking proposal does not show a booked confirmation", async ({
  page,
}) => {
  await signedIn(page);
  await mockApi(page);
  await page.route("**/api/v1/appointments/booking-1/approve", (route) => {
    expect(JSON.parse(route.request().postData() ?? "{}").decision).toBe(
      "REJECT",
    );
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        status: "success",
        message: "Booking proposal rejected.",
      }),
    });
  });
  await page.goto("/book/doctor-1/slot-1");
  await page.getByRole("button", { name: "Prepare booking request" }).click();
  await page.getByRole("button", { name: "Reject" }).click();
  await expect(page.getByRole("dialog")).toContainText(
    "Booking proposal rejected.",
  );
  await expect(page.getByRole("dialog")).not.toContainText(
    "Booking confirmed.",
  );
  await page.getByRole("button", { name: "Done" }).click();
  await page.getByRole("button", { name: "Prepare booking request" }).click();
  await expect(
    page.getByRole("button", { name: "Confirm booking" }),
  ).toBeVisible();
});

test("a new authenticated patient completes profile setup before entering the portal", async ({
  page,
}) => {
  await signedIn(page);
  await mockApi(page);
  let profileCreated = false;
  await page.route("**/api/v1/patients/me", async (route) => {
    if (route.request().method() === "POST") {
      profileCreated = true;
      await route.fulfill({
        status: 201,
        contentType: "application/json",
        body: JSON.stringify({
          name: "New Patient",
          email: user.email,
          phone: null,
          timezone: "UTC",
        }),
      });
      return;
    }
    await route.fulfill({
      status: profileCreated ? 200 : 403,
      contentType: "application/json",
      body: JSON.stringify(
        profileCreated
          ? {
              name: "New Patient",
              email: user.email,
              phone: null,
              timezone: "UTC",
            }
          : { detail: "No patient profile is linked to this account." },
      ),
    });
  });
  await page.goto("/dashboard");
  await expect(page).toHaveURL(/\/onboarding$/);
  await page.getByLabel("Full name").fill("New Patient");
  await page.getByRole("button", { name: "Complete setup" }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
  await expect(
    page.getByRole("heading", { name: "Welcome back" }),
  ).toBeVisible();
});

test("booking review can be opened and rejected using the keyboard", async ({
  page,
}) => {
  await signedIn(page);
  await mockApi(page);
  await page.route("**/api/v1/appointments/booking-1/approve", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        status: "success",
        message: "Booking proposal rejected.",
      }),
    }),
  );
  await page.goto("/book/doctor-1/slot-1");
  const prepare = page.getByRole("button", { name: "Prepare booking request" });
  for (
    let i = 0;
    i < 30 && !(await prepare.evaluate((el) => el === document.activeElement));
    i++
  )
    await page.keyboard.press("Tab");
  await expect(prepare).toBeFocused();
  await page.keyboard.press("Enter");
  const reject = page.getByRole("button", { name: "Reject" });
  await expect(reject).toBeVisible();
  for (
    let i = 0;
    i < 10 && !(await reject.evaluate((el) => el === document.activeElement));
    i++
  )
    await page.keyboard.press("Tab");
  await expect(reject).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page.getByRole("dialog")).toContainText(
    "Booking proposal rejected.",
  );
});

test("registration validates password confirmation and can show passwords", async ({
  page,
}) => {
  await page.goto("/register");
  await page.getByLabel("Email address").fill("patient@example.com");
  await page.getByLabel("Password", { exact: true }).fill("password123");
  await page.getByLabel("Confirm password").fill("different123");
  await page.getByRole("button", { name: "Show passwords" }).click();
  await expect(page.getByLabel("Password", { exact: true })).toHaveAttribute(
    "type",
    "text",
  );
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page.getByText("Passwords do not match")).toBeVisible();
});

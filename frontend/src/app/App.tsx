import { lazy, Suspense, useState } from "react";
import {
  Link,
  NavLink,
  Navigate,
  Route,
  Routes,
  useNavigate,
} from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useQuery } from "@tanstack/react-query";
import { z } from "zod";
import {
  CalendarDays,
  HeartPulse,
  LayoutDashboard,
  LogOut,
  MessageCircle,
  Search,
  UserRound,
  BookOpen,
  Menu,
  ArrowRight,
} from "lucide-react";
import { supabase, configurationReady } from "../lib/supabase";
import { useAuth } from "../lib/auth";
import { ApiError } from "../lib/api-client";
import { patients } from "../lib/services";
import { ErrorState, LoadingState } from "../components/common";

const LandingPage = lazy(() =>
  import("../features/landing/LandingPage").then((module) => ({
    default: module.LandingPage,
  })),
);
const AuthCallbackPage = lazy(() =>
  import("../features/auth/AuthCallbackPage").then((module) => ({
    default: module.AuthCallbackPage,
  })),
);
const OnboardingPage = lazy(() =>
  import("../features/auth/OnboardingPage").then((module) => ({
    default: module.OnboardingPage,
  })),
);
const Dashboard = lazy(() =>
  import("../features/dashboard/DashboardPage").then((module) => ({
    default: module.Dashboard,
  })),
);
const DoctorsPage = lazy(() =>
  import("../features/doctors/DoctorPages").then((module) => ({
    default: module.DoctorsPage,
  })),
);
const DoctorDetails = lazy(() =>
  import("../features/doctors/DoctorPages").then((module) => ({
    default: module.DoctorDetails,
  })),
);
const AvailabilityPage = lazy(() =>
  import("../features/availability/AvailabilityPage").then((module) => ({
    default: module.AvailabilityPage,
  })),
);
const BookingPage = lazy(() =>
  import("../features/appointments/AppointmentPages").then((module) => ({
    default: module.BookingPage,
  })),
);
const AppointmentsPage = lazy(() =>
  import("../features/appointments/AppointmentPages").then((module) => ({
    default: module.AppointmentsPage,
  })),
);
const AppointmentDetails = lazy(() =>
  import("../features/appointments/AppointmentPages").then((module) => ({
    default: module.AppointmentDetails,
  })),
);
const ChatPage = lazy(() =>
  import("../features/chat/ChatPage").then((module) => ({
    default: module.ChatPage,
  })),
);
const KnowledgePage = lazy(() =>
  import("../features/knowledge/KnowledgePage").then((module) => ({
    default: module.KnowledgePage,
  })),
);
const ProfilePage = lazy(() =>
  import("../features/profile/ProfilePage").then((module) => ({
    default: module.ProfilePage,
  })),
);

const nav = [
  { to: "/dashboard", label: "Overview", icon: LayoutDashboard },
  { to: "/doctors", label: "Find a doctor", icon: Search },
  { to: "/appointments", label: "Appointments", icon: CalendarDays },
  { to: "/chat", label: "AI assistant", icon: MessageCircle },
  { to: "/knowledge", label: "Clinic guide", icon: BookOpen },
  { to: "/profile", label: "My profile", icon: UserRound },
];
function Shell({ children }: { children: React.ReactNode }) {
  const { session, signOut } = useAuth();
  const [menu, setMenu] = useState(false);
  return (
    <div className="shell">
      <aside className={`sidebar ${menu ? "open" : ""}`}>
        <Link to="/dashboard" className="brand" onClick={() => setMenu(false)}>
          <span className="brand-icon">
            <HeartPulse size={23} />
          </span>
          <span>
            CarePath<small>Patient portal</small>
          </span>
        </Link>
        <p className="nav-heading">YOUR SPACE</p>
        <nav aria-label="Primary navigation">
          {nav.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              onClick={() => setMenu(false)}
              className={({ isActive }) =>
                `nav-link ${isActive ? "active" : ""}`
              }
            >
              <item.icon size={19} />
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-footer">
          <div className="care-note">
            <HeartPulse size={20} />
            <strong>Here for your care</strong>
            <span>Appointments made simpler, one step at a time.</span>
          </div>
          <button className="nav-link logout" onClick={() => void signOut()}>
            <LogOut size={18} /> Sign out
          </button>
        </div>
      </aside>
      <div className="main-area">
        <header className="topbar">
          <button
            className="icon-button mobile-menu"
            aria-label="Toggle menu"
            aria-expanded={menu}
            onClick={() => setMenu(!menu)}
          >
            <Menu />
          </button>
          <span className="topbar-title">A simpler way to care</span>
          <span className="account-pill">
            <UserRound size={16} />
            {session?.user.email ?? "Patient"}
          </span>
        </header>
        <main className="content">{children}</main>
        <footer className="footer">
          CarePath helps with appointments and clinic information. For medical
          emergencies, contact local emergency services.
        </footer>
      </div>
      {menu && (
        <button
          className="mobile-overlay"
          aria-label="Close menu"
          onClick={() => setMenu(false)}
        />
      )}
    </div>
  );
}
function Protected({
  children,
  requireProfile = true,
}: {
  children: React.ReactNode;
  requireProfile?: boolean;
}) {
  const { session, loading } = useAuth();
  const profile = useQuery({
    queryKey: ["patient", session?.user.id],
    queryFn: patients.me,
    enabled: Boolean(session) && requireProfile,
  });
  if (loading) return <LoadingState />;
  if (!session) return <Navigate to="/login" replace />;
  if (requireProfile && profile.isLoading) return <LoadingState />;
  if (
    requireProfile &&
    profile.error instanceof ApiError &&
    profile.error.status === 403
  )
    return <Navigate to="/onboarding" replace />;
  if (requireProfile && profile.isError)
    return (
      <ErrorState
        message="Your patient profile could not be loaded."
        retry={() => void profile.refetch()}
      />
    );
  return <Shell>{children}</Shell>;
}
const authSchema = z.object({
  email: z.email(),
  password: z.string().optional(),
  confirmPassword: z.string().optional(),
});
type AuthFields = z.infer<typeof authSchema>;
function AuthPage({ mode }: { mode: "login" | "register" | "reset" }) {
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const navigate = useNavigate();
  const { session } = useAuth();
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<AuthFields>({
    resolver: zodResolver(
      authSchema.superRefine((values, context) => {
        if (mode !== "reset" && !values.password) {
          context.addIssue({
            code: "custom",
            path: ["password"],
            message: "Enter your password",
          });
        } else if (mode === "register" && (values.password?.length ?? 0) < 8) {
          context.addIssue({
            code: "custom",
            path: ["password"],
            message: "Use at least 8 characters",
          });
        }
        if (mode === "register" && values.confirmPassword !== values.password) {
          context.addIssue({
            code: "custom",
            path: ["confirmPassword"],
            message: "Passwords do not match",
          });
        }
      }),
    ),
  });
  if (session) return <Navigate to="/dashboard" replace />;
  async function submit(values: AuthFields) {
    if (!supabase) return;
    setError("");
    setNotice("");
    const credentials = {
      email: values.email,
      password: values.password ?? "",
    };
    const result =
      mode === "login"
        ? await supabase.auth.signInWithPassword(credentials)
        : mode === "register"
          ? await supabase.auth.signUp({
              ...credentials,
              options: { emailRedirectTo: `${location.origin}/auth/callback` },
            })
          : await supabase.auth.resetPasswordForEmail(values.email, {
              redirectTo: `${location.origin}/auth/callback?flow=recovery`,
            });
    if (result.error) setError(result.error.message);
    else if (mode === "login") navigate("/dashboard");
    else
      setNotice(
        mode === "register"
          ? "Check your email to confirm your account."
          : "Password reset instructions have been sent if the account exists.",
      );
  }
  return (
    <div className="auth-page">
      <div className="auth-hero">
        <Link to="/login" className="brand light">
          <span className="brand-icon">
            <HeartPulse />
          </span>
          <span>
            CarePath<small>Patient portal</small>
          </span>
        </Link>
        <div>
          <span className="eyebrow">YOUR HEALTH, YOUR TIME</span>
          <h1>
            Care that fits
            <br />
            your day.
          </h1>
          <p>
            Find the right doctor, choose a time that works, and manage every
            appointment in one calm place.
          </p>
        </div>
        <span className="auth-hero-bottom">A clearer path to better care.</span>
      </div>
      <div className="auth-panel">
        <div className="auth-card">
          <span className="eyebrow">WELCOME TO CAREPATH</span>
          <h2>
            {mode === "login"
              ? "Good to see you again"
              : mode === "register"
                ? "Create your account"
                : "Reset your password"}
          </h2>
          <p>
            {mode === "login"
              ? "Sign in to manage your care."
              : mode === "register"
                ? "Start managing appointments with confidence."
                : "We’ll send a secure reset link to your email."}
          </p>
          {!configurationReady && (
            <div className="notice error" role="alert">
              Set VITE_SUPABASE_URL and VITE_SUPABASE_PUBLISHABLE_KEY to enable
              sign in.
            </div>
          )}
          <form onSubmit={handleSubmit(submit)}>
            <label>
              Email address
              <input
                type="email"
                autoComplete="email"
                placeholder="you@example.com"
                {...register("email")}
              />
            </label>
            {errors.email && (
              <small className="error-text" role="alert">
                {errors.email.message}
              </small>
            )}
            {mode !== "reset" && (
              <>
                <label>
                  Password
                  <input
                    type={showPassword ? "text" : "password"}
                    autoComplete={
                      mode === "register" ? "new-password" : "current-password"
                    }
                    placeholder="At least 8 characters"
                    {...register("password")}
                  />
                </label>
                {errors.password && (
                  <small className="error-text" role="alert">
                    {errors.password.message}
                  </small>
                )}
                {mode === "register" && (
                  <>
                    <label>
                      Confirm password
                      <input
                        type={showPassword ? "text" : "password"}
                        autoComplete="new-password"
                        {...register("confirmPassword")}
                      />
                    </label>
                    {errors.confirmPassword && (
                      <small className="error-text" role="alert">
                        {errors.confirmPassword.message}
                      </small>
                    )}
                  </>
                )}
                <button
                  type="button"
                  className="text-button"
                  onClick={() => setShowPassword(!showPassword)}
                >
                  {showPassword ? "Hide passwords" : "Show passwords"}
                </button>
              </>
            )}
            {error && (
              <p className="error-text" role="alert">
                {error}
              </p>
            )}
            {notice && (
              <p className="notice" role="status">
                {notice}
              </p>
            )}
            <button
              className="button full"
              disabled={isSubmitting || !configurationReady}
            >
              {isSubmitting
                ? "Please wait…"
                : mode === "login"
                  ? "Sign in"
                  : mode === "register"
                    ? "Create account"
                    : "Send reset link"}
              <ArrowRight size={17} />
            </button>
          </form>
          <div className="auth-links">
            {mode === "login" ? (
              <>
                <Link to="/register">Create an account</Link>
                <Link to="/forgot-password">Forgot password?</Link>
              </>
            ) : (
              <Link to="/login">Back to sign in</Link>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
export function App() {
  return (
    <Suspense fallback={<LoadingState />}>
      <Routes>
        <Route path="/login" element={<AuthPage mode="login" />} />
        <Route path="/register" element={<AuthPage mode="register" />} />
        <Route path="/forgot-password" element={<AuthPage mode="reset" />} />
        <Route
          path="/auth/callback"
          element={
            <Suspense fallback={<LoadingState />}>
              <AuthCallbackPage />
            </Suspense>
          }
        />
        <Route
          path="/"
          element={
            <Suspense fallback={<LoadingState />}>
              <LandingPage />
            </Suspense>
          }
        />
        <Route
          path="/onboarding"
          element={
            <Protected requireProfile={false}>
              <Suspense fallback={<LoadingState />}>
                <OnboardingPage />
              </Suspense>
            </Protected>
          }
        />
        <Route
          path="/dashboard"
          element={
            <Protected>
              <Dashboard />
            </Protected>
          }
        />
        <Route
          path="/doctors"
          element={
            <Protected>
              <DoctorsPage />
            </Protected>
          }
        />
        <Route
          path="/doctors/:id"
          element={
            <Protected>
              <DoctorDetails />
            </Protected>
          }
        />
        <Route
          path="/availability/:doctorId"
          element={
            <Protected>
              <AvailabilityPage />
            </Protected>
          }
        />
        <Route
          path="/book/:doctorId/:slotId"
          element={
            <Protected>
              <BookingPage />
            </Protected>
          }
        />
        <Route
          path="/appointments"
          element={
            <Protected>
              <AppointmentsPage />
            </Protected>
          }
        />
        <Route
          path="/appointments/:id"
          element={
            <Protected>
              <AppointmentDetails />
            </Protected>
          }
        />
        <Route
          path="/chat"
          element={
            <Protected>
              <ChatPage />
            </Protected>
          }
        />
        <Route
          path="/knowledge"
          element={
            <Protected>
              <KnowledgePage />
            </Protected>
          }
        />
        <Route
          path="/profile"
          element={
            <Protected>
              <ProfilePage />
            </Protected>
          }
        />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </Suspense>
  );
}

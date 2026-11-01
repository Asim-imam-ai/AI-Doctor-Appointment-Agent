import { useState, type FormEvent } from "react";
import { Link, Navigate, useNavigate, useSearchParams } from "react-router-dom";
import { HeartPulse } from "lucide-react";
import { useAuth } from "../../lib/auth";
import { supabase } from "../../lib/supabase";
import { LoadingState } from "../../components/common";

export function AuthCallbackPage() {
  const { session, loading } = useAuth();
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  if (loading) return <LoadingState />;
  if (!session)
    return (
      <div className="callback-card">
        <HeartPulse />
        <h1>We could not verify this link</h1>
        <p>The link may have expired. Request a new one or sign in again.</p>
        <Link to="/login" className="button">
          Back to sign in
        </Link>
      </div>
    );
  if (params.get("flow") !== "recovery")
    return <Navigate to="/dashboard" replace />;
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (password.length < 8) {
      setError("Use at least 8 characters.");
      return;
    }
    setSaving(true);
    setError("");
    const { error: updateError } = await supabase!.auth.updateUser({
      password,
    });
    setSaving(false);
    if (updateError) setError(updateError.message);
    else navigate("/dashboard", { replace: true });
  }
  return (
    <div className="callback-card">
      <HeartPulse />
      <h1>Choose a new password</h1>
      <p>Use at least eight characters to protect your account.</p>
      <form onSubmit={submit}>
        <label>
          New password
          <input
            type="password"
            autoComplete="new-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />
        </label>
        {error && (
          <p role="alert" className="error-text">
            {error}
          </p>
        )}
        <button className="button full" disabled={saving}>
          {saving ? "Updating…" : "Update password"}
        </button>
      </form>
    </div>
  );
}

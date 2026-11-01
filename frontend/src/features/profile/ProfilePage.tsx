import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "../../lib/auth";
import { conversations, patients } from "../../lib/services";
import { PageHeader, LoadingState, ErrorState } from "../../components/common";

const preferenceLabels: Record<string, string> = {
  preferred_specialty: "Preferred specialty",
  preferred_doctor: "Preferred doctor",
  preferred_time_range: "Preferred time range",
  timezone: "Timezone",
};
export function ProfilePage() {
  const { session } = useAuth();
  const profile = useQuery({
    queryKey: ["patient", session?.user.id],
    queryFn: patients.me,
  });
  const [key, setKey] = useState("");
  const [value, setValue] = useState("");
  const [notice, setNotice] = useState("");
  const qc = useQueryClient();
  const memories = useQuery({
    queryKey: ["memories", session?.user.id],
    queryFn: conversations.memories,
  });
  const save = useMutation({
    mutationFn: () => conversations.addMemory(key, value),
    onSuccess: () => {
      setKey("");
      setValue("");
      setNotice("Preference saved.");
      void qc.invalidateQueries({ queryKey: ["memories"] });
    },
  });
  const remove = useMutation({
    mutationFn: conversations.removeMemory,
    onSuccess: () => {
      setNotice("Preference removed.");
      void qc.invalidateQueries({ queryKey: ["memories"] });
    },
  });
  return (
    <>
      <PageHeader
        eyebrow="YOUR ACCOUNT"
        title="My profile"
        description="Your sign-in details and saved appointment preferences."
      />
      <div className="card details-card">
        <h2>Account</h2>
        {profile.isLoading ? (
          <LoadingState />
        ) : profile.isError ? (
          <ErrorState message={(profile.error as Error).message} />
        ) : (
          <>
            <p>
              <strong>Name</strong>
              <br />
              {profile.data?.name}
            </p>
            <p>
              <strong>Email</strong>
              <br />
              {profile.data?.email}
            </p>
            <p>
              <strong>Phone</strong>
              <br />
              {profile.data?.phone ?? "Not provided"}
            </p>
            <p>
              <strong>Timezone</strong>
              <br />
              {profile.data?.timezone}
            </p>
          </>
        )}
        <p>Profile editing is not available through the current patient API.</p>
      </div>
      <div className="card details-card">
        <h2>Saved preferences</h2>
        {memories.isLoading ? (
          <LoadingState />
        ) : memories.isError ? (
          <ErrorState message="Preferences could not be loaded." />
        ) : memories.data?.length ? (
          <div className="memory-list">
            {memories.data.map((m) => (
              <div key={m.id}>
                <p>
                  <strong>{preferenceLabels[m.key] ?? m.key}</strong>{" "}
                  <span>{m.value}</span>
                </p>
                <button
                  className="text-button"
                  disabled={remove.isPending}
                  aria-label={`Remove preference ${preferenceLabels[m.key] ?? m.key}`}
                  onClick={() => {
                    setNotice("");
                    remove.mutate(m.id);
                  }}
                >
                  Remove
                </button>
              </div>
            ))}
          </div>
        ) : (
          <p>No saved preferences.</p>
        )}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (key.trim() && value.trim()) {
              setNotice("");
              save.mutate();
            }
          }}
          className="preference-form"
        >
          <label>
            Preference
            <select
              value={key}
              onChange={(e) => setKey(e.target.value)}
              required
            >
              <option value="">Select a preference</option>
              {Object.entries(preferenceLabels).map(([optionKey, label]) => (
                <option key={optionKey} value={optionKey}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          <label>
            Preference value
            <input
              value={value}
              maxLength={500}
              onChange={(e) => setValue(e.target.value)}
              required
            />
          </label>
          <button className="button" disabled={save.isPending}>
            Save preference
          </button>
        </form>
        {save.isError && (
          <p role="alert" className="error-text">
            {(save.error as Error).message}
          </p>
        )}
        {remove.isError && (
          <p role="alert" className="error-text">
            {(remove.error as Error).message}
          </p>
        )}
        {notice && <p role="status">{notice}</p>}
      </div>
    </>
  );
}

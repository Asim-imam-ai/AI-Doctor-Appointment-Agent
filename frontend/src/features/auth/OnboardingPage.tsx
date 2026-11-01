import { useMutation, useQueryClient } from "@tanstack/react-query";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { useNavigate } from "react-router-dom";
import { z } from "zod";
import { patients } from "../../lib/services";
import { PageHeader } from "../../components/common";

const setupSchema = z.object({
  name: z.string().trim().min(2, "Enter your name").max(255),
  phone: z.string().max(50).optional(),
});
type SetupFields = z.infer<typeof setupSchema>;

export function OnboardingPage() {
  const navigate = useNavigate();
  const query = useQueryClient();
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<SetupFields>({ resolver: zodResolver(setupSchema) });
  const save = useMutation({
    mutationFn: (values: SetupFields) =>
      patients.setup({
        ...values,
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC",
      }),
    onSuccess: async () => {
      await query.invalidateQueries({ queryKey: ["patient"] });
      await query.invalidateQueries({ queryKey: ["appointments"] });
      navigate("/dashboard", { replace: true });
    },
  });
  return (
    <>
      <PageHeader
        eyebrow="FINISH SETTING UP"
        title="Welcome to CarePath"
        description="Add your name so your appointment requests can be linked to your account."
      />
      <div className="card details-card onboarding-card">
        <form onSubmit={handleSubmit((values) => save.mutate(values))}>
          <label>
            Full name
            <input
              autoComplete="name"
              placeholder="Your full name"
              {...register("name")}
            />
          </label>
          {errors.name && (
            <small role="alert" className="error-text">
              {errors.name.message}
            </small>
          )}
          <label>
            Phone (optional)
            <input
              autoComplete="tel"
              placeholder="Phone number"
              {...register("phone")}
            />
          </label>
          {errors.phone && (
            <small role="alert" className="error-text">
              {errors.phone.message}
            </small>
          )}
          {save.isError && (
            <p role="alert" className="error-text">
              {(save.error as Error).message}
            </p>
          )}
          <button className="button" disabled={save.isPending}>
            {save.isPending ? "Saving…" : "Complete setup"}
          </button>
        </form>
      </div>
    </>
  );
}

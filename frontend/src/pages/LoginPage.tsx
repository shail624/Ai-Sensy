import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { useLocation, useNavigate } from "react-router-dom";
import { z } from "zod";

import { ErrorState } from "@/components/ui";
import { apiErrorMessage } from "@/lib/api/errors";
import { useAuth } from "@/lib/auth";

const FIELD_CLASS =
  "w-full rounded-md border border-border bg-surface px-2 py-1.5 text-sm text-text-primary";

const schema = z.object({
  email: z.string().min(1, "Email is required").email("Enter a valid email address"),
  password: z.string().min(1, "Password is required"),
  // Optional second factor — the contract accepts it on the same request (FR-AUTH-05).
  mfa_code: z.string().optional(),
});

type FormValues = z.infer<typeof schema>;

interface LocationState {
  from?: { pathname?: string };
}

export function LoginPage(): JSX.Element {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [submitError, setSubmitError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  const from = (location.state as LocationState | null)?.from?.pathname ?? "/";

  const onSubmit = handleSubmit(async (values) => {
    setSubmitError(null);
    try {
      await login({
        email: values.email,
        password: values.password,
        mfa_code: values.mfa_code?.trim() ? values.mfa_code.trim() : null,
      });
      navigate(from, { replace: true });
    } catch (error) {
      setSubmitError(apiErrorMessage(error));
    }
  });

  return (
    <div className="flex min-h-screen items-center justify-center bg-canvas p-4">
      <div className="w-full max-w-sm rounded-lg border border-border bg-surface p-6">
        <h1 className="text-lg font-bold text-text-primary">Sign in</h1>
        <p className="mt-1 text-sm text-text-secondary">WhatsApp Business Platform</p>

        <form onSubmit={onSubmit} className="mt-5 space-y-3" noValidate>
          <div>
            <label htmlFor="login-email" className="text-xs font-medium text-text-secondary">
              Email
            </label>
            <input
              id="login-email"
              type="email"
              autoComplete="username"
              autoFocus
              {...register("email")}
              className={FIELD_CLASS}
            />
            {errors.email ? (
              <p className="mt-1 text-xs text-danger">{errors.email.message}</p>
            ) : null}
          </div>

          <div>
            <label htmlFor="login-password" className="text-xs font-medium text-text-secondary">
              Password
            </label>
            <input
              id="login-password"
              type="password"
              autoComplete="current-password"
              {...register("password")}
              className={FIELD_CLASS}
            />
            {errors.password ? (
              <p className="mt-1 text-xs text-danger">{errors.password.message}</p>
            ) : null}
          </div>

          <div>
            <label htmlFor="login-mfa" className="text-xs font-medium text-text-secondary">
              Authentication code (if enabled)
            </label>
            <input
              id="login-mfa"
              inputMode="numeric"
              autoComplete="one-time-code"
              {...register("mfa_code")}
              className={FIELD_CLASS}
            />
          </div>

          {submitError ? <ErrorState message={submitError} /> : null}

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full rounded-md bg-accent px-3 py-1.5 text-sm text-accent-fg disabled:opacity-50"
          >
            {isSubmitting ? "Signing in…" : "Sign in"}
          </button>
        </form>
      </div>
    </div>
  );
}

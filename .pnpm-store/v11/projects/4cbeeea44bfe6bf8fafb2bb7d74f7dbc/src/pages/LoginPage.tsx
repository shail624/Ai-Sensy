import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowRight, CheckCircle2, LockKeyhole, MessageSquareText, ShieldCheck, Sparkles } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { useLocation, useNavigate } from "react-router-dom";
import { z } from "zod";

import { Button, ErrorState } from "@/components/ui";
import { apiErrorMessage } from "@/lib/api/errors";
import { useAuth } from "@/lib/auth";

const FIELD_CLASS = "mt-1.5 h-11 w-full rounded-xl border border-border bg-surface px-3 text-sm text-text-primary shadow-sm transition-colors placeholder:text-text-disabled hover:border-border-strong focus:border-accent focus:outline-none focus:ring-2 focus:ring-focus/25";

const schema = z.object({
  email: z.string().min(1, "Email is required").email("Enter a valid email address"),
  password: z.string().min(1, "Password is required"),
  mfa_code: z.string().optional(),
});

type FormValues = z.infer<typeof schema>;
interface LocationState { from?: { pathname?: string } }

export function LoginPage(): JSX.Element {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [submitError, setSubmitError] = useState<string | null>(null);
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<FormValues>({ resolver: zodResolver(schema) });
  const from = (location.state as LocationState | null)?.from?.pathname ?? "/";

  const onSubmit = handleSubmit(async (values) => {
    setSubmitError(null);
    try {
      await login({ email: values.email, password: values.password, mfa_code: values.mfa_code?.trim() ? values.mfa_code.trim() : null });
      navigate(from, { replace: true });
    } catch (error) {
      setSubmitError(apiErrorMessage(error));
    }
  });

  return (
    <main className="relative flex min-h-screen items-center justify-center overflow-hidden bg-canvas p-4 sm:p-8">
      <div aria-hidden className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,color-mix(in_srgb,var(--color-accent)_14%,transparent),transparent_38%),radial-gradient(circle_at_bottom_right,color-mix(in_srgb,var(--color-info)_10%,transparent),transparent_38%)]" />
      <div className="relative grid w-full max-w-5xl overflow-hidden rounded-3xl border border-border bg-surface shadow-[0_28px_80px_rgba(15,23,42,0.14)] lg:grid-cols-[1.05fr_0.95fr]">
        <section className="relative hidden min-h-[640px] overflow-hidden bg-[linear-gradient(145deg,#17152f_0%,#2f2673_55%,#5745d6_100%)] p-10 text-white lg:flex lg:flex-col">
          <div aria-hidden className="absolute -right-24 -top-24 h-72 w-72 rounded-full border border-white/10 bg-white/5" />
          <div aria-hidden className="absolute -bottom-20 -left-20 h-64 w-64 rounded-full border border-white/10 bg-white/5" />
          <div className="relative flex items-center gap-3">
            <span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-white/15 shadow-inner"><MessageSquareText aria-hidden className="h-5 w-5" /></span>
            <div><p className="text-sm font-bold tracking-wide">Vi Reactivation</p><p className="text-xs text-white/65">Customer engagement suite</p></div>
          </div>
          <div className="relative my-auto max-w-md">
            <span className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/10 px-3 py-1.5 text-xs font-semibold text-white/85"><Sparkles aria-hidden className="h-3.5 w-3.5" /> Enterprise workspace</span>
            <h2 className="mt-6 text-4xl font-bold leading-tight tracking-[-0.035em]">Turn every customer conversation into confident action.</h2>
            <p className="mt-4 text-base leading-relaxed text-white/70">Campaigns, shared inbox, customer context, and operational control in one focused workspace.</p>
            <div className="mt-8 space-y-3">
              {["Official WhatsApp Cloud API workflows", "Permission-aware customer operations", "Auditable, production-grade delivery"].map((item) => <div key={item} className="flex items-center gap-3 text-sm text-white/85"><CheckCircle2 aria-hidden className="h-4 w-4 text-emerald-300" /><span>{item}</span></div>)}
            </div>
          </div>
          <p className="relative text-xs text-white/50">Secure access · Your session is protected by the platform authentication policy</p>
        </section>

        <section className="flex min-h-[600px] items-center px-5 py-10 sm:px-12 lg:px-14">
          <div className="mx-auto w-full max-w-sm">
            <div className="mb-8 lg:hidden">
              <span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-accent text-accent-fg shadow-sm"><MessageSquareText aria-hidden className="h-5 w-5" /></span>
              <p className="mt-3 text-sm font-bold text-text-primary">Vi Reactivation</p>
            </div>
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-accent-soft text-accent"><LockKeyhole aria-hidden className="h-5 w-5" /></div>
            <h1 className="mt-5 text-3xl font-bold tracking-[-0.035em] text-text-primary">Sign in</h1>
            <p className="mt-2 text-sm leading-relaxed text-text-secondary">Sign in to your WhatsApp customer engagement workspace.</p>

            <form onSubmit={onSubmit} className="mt-8 space-y-4" noValidate>
              <div>
                <label htmlFor="login-email" className="text-sm font-semibold text-text-primary">Email</label>
                <input id="login-email" type="email" autoComplete="username" autoFocus {...register("email")} className={FIELD_CLASS} />
                {errors.email ? <p className="mt-1 text-xs text-danger">{errors.email.message}</p> : null}
              </div>
              <div>
                <label htmlFor="login-password" className="text-sm font-semibold text-text-primary">Password</label>
                <input id="login-password" type="password" autoComplete="current-password" {...register("password")} className={FIELD_CLASS} />
                {errors.password ? <p className="mt-1 text-xs text-danger">{errors.password.message}</p> : null}
              </div>
              <div>
                <label htmlFor="login-mfa" className="text-sm font-semibold text-text-primary">Authentication code <span className="font-normal text-text-secondary">(if enabled)</span></label>
                <input id="login-mfa" inputMode="numeric" autoComplete="one-time-code" {...register("mfa_code")} className={FIELD_CLASS} />
              </div>
              {submitError ? <ErrorState message={submitError} /> : null}
              <Button type="submit" size="lg" block loading={isSubmitting} disabled={isSubmitting} rightIcon={<ArrowRight aria-hidden className="h-4 w-4" />}>Sign in</Button>
            </form>

            <div className="mt-7 flex items-start gap-2.5 rounded-xl bg-surface-subtle p-3 text-xs leading-relaxed text-text-secondary"><ShieldCheck aria-hidden className="mt-0.5 h-4 w-4 shrink-0 text-success" /><p>Password recovery is managed by your workspace administrator. Contact them if you cannot sign in.</p></div>
          </div>
        </section>
      </div>
    </main>
  );
}

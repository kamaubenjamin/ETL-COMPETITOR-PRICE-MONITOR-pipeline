import { useState, type FormEvent } from "react";
import { deploymentEnvironmentLabel } from "../config/deploymentEnvironment";
import { useAuth } from "../auth/useAuth";

export function SignInPage() {
  const { signIn } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [diagnosticCode, setDiagnosticCode] = useState<string>();

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setDiagnosticCode(undefined);
    setSubmitting(true);
    const result = await signIn(email, password);
    setSubmitting(false);
    if (!result.success) setDiagnosticCode(result.code);
  };

  return (
    <main className="sign-in-page">
      <section className="sign-in-card" aria-labelledby="sign-in-title">
        <span className="environment-indicator">{deploymentEnvironmentLabel()}</span>
        <p className="eyebrow">FlowSync Document Intelligence</p>
        <h1 id="sign-in-title">Sign in to continue</h1>
        <p>Use the existing UAT account created by the environment owner.</p>
        {diagnosticCode ? (
          <div className="sign-in-error" role="alert">
            Sign-in could not be completed. Check your credentials and try again.
            <small>Diagnostic: {diagnosticCode}</small>
          </div>
        ) : null}
        <form onSubmit={(event) => void submit(event)}>
          <label>Email<input type="email" autoComplete="username" required maxLength={254} value={email} onChange={(event) => setEmail(event.target.value)} /></label>
          <label>Password<input type="password" autoComplete="current-password" required maxLength={256} value={password} onChange={(event) => setPassword(event.target.value)} /></label>
          <button className="primary-button" type="submit" disabled={submitting}>{submitting ? "Signing in…" : "Sign in"}</button>
        </form>
        <small>No public signup or password recovery is available in this technical preview.</small>
      </section>
    </main>
  );
}

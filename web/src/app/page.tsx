"use client";

import { useState, type FormEvent } from "react";
import styles from "./page.module.css";

// This type keeps the sign-up role aligned with the student and professor accounts.
type Role = "student" | "professor";
type AuthMode = "login" | "signup";

// These credentials make it possible to preview both account roles without a backend.
const demoAccounts = [
  { email: "student@unb.ca", password: "Student123!", role: "student" },
  { email: "professor@unb.ca", password: "Professor123!", role: "professor" },
];

// This component contains only the sign-in and sign-up screens; authenticated pages are out of scope.
export default function Home() {
  const [mode, setMode] = useState<AuthMode>("login");
  const [role, setRole] = useState<Role>("student");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  // This handler reports demo authentication results without navigating to a dashboard.
  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setMessage("");

    if (mode === "signup") {
      setMessage(`Sign-up form ready for ${role} account. Face registration is coming next.`);
      return;
    }

    const account = demoAccounts.find(
      (item) =>
        item.email === email.trim().toLowerCase() &&
        item.password === password,
    );
    if (!account) {
      setError("Those demo credentials do not match. Try one of the sample accounts below.");
      return;
    }

    setMessage(`Demo sign-in successful for the ${account.role} account. Dashboards are not included yet.`);
  }

  // This helper switches between the two forms and clears status from the previous form.
  function changeMode(nextMode: AuthMode) {
    setMode(nextMode);
    setError("");
    setMessage("");
  }

  return (
    <main className={styles.page}>
      <header className={styles.header}>
        <a aria-label="Attendwise home" className={styles.brand} href="#">
          <span aria-hidden="true" className={styles.brandMark}>A</span>
          <span>attendwise</span>
        </a>
        <span className={styles.school}>UNIVERSITY OF NEW BRUNSWICK</span>
      </header>

      <section aria-labelledby="form-heading" className={styles.authCard}>
        <div className={styles.cardHeading}>
          <p className={styles.eyebrow}>SECURE ATTENDANCE</p>
          <h1 id="form-heading">
            {mode === "login" ? "Welcome back" : "Create your account"}
          </h1>
          <p>
            {mode === "login"
              ? "Sign in to your university account."
              : "A few details to get you started."}
          </p>
        </div>

        <div aria-label="Account access" className={styles.tabs} role="tablist">
          <button
            aria-selected={mode === "login"}
            className={mode === "login" ? styles.selectedTab : ""}
            onClick={() => changeMode("login")}
            role="tab"
            type="button"
          >
            Log in
          </button>
          <button
            aria-selected={mode === "signup"}
            className={mode === "signup" ? styles.selectedTab : ""}
            onClick={() => changeMode("signup")}
            role="tab"
            type="button"
          >
            Sign up
          </button>
        </div>

        <form className={styles.form} onSubmit={handleSubmit}>
          {mode === "signup" && (
            <>
              <label htmlFor="full-name">Full name</label>
              <input
                autoComplete="name"
                id="full-name"
                onChange={(event) => setFullName(event.target.value)}
                placeholder="Your name"
                required
                value={fullName}
              />

              <label>Account type</label>
              <div aria-label="Account type" className={styles.roleButtons}>
                <button
                  aria-pressed={role === "student"}
                  className={role === "student" ? styles.selectedRole : ""}
                  onClick={() => setRole("student")}
                  type="button"
                >
                  Student
                </button>
                <button
                  aria-pressed={role === "professor"}
                  className={role === "professor" ? styles.selectedRole : ""}
                  onClick={() => setRole("professor")}
                  type="button"
                >
                  Professor
                </button>
              </div>
            </>
          )}

          <label htmlFor="email">University email</label>
          <input
            autoComplete="username"
            id="email"
            onChange={(event) => setEmail(event.target.value)}
            placeholder="you@unb.ca"
            required
            type="email"
            value={email}
          />

          <label htmlFor="password">Password</label>
          <input
            autoComplete={mode === "login" ? "current-password" : "new-password"}
            id="password"
            minLength={8}
            onChange={(event) => setPassword(event.target.value)}
            placeholder={mode === "login" ? "Enter your password" : "At least 8 characters"}
            required
            type="password"
            value={password}
          />

          {error && <p className={styles.error} role="alert">{error}</p>}
          {message && <p className={styles.message} role="status">{message}</p>}

          <button className={styles.submitButton} type="submit">
            {mode === "login" ? "Log in" : "Create account"}
          </button>
        </form>

        {mode === "login" && (
          <aside aria-label="Demo accounts" className={styles.demoBox}>
            <p>Need a test account?</p>
            <span>Student: student@unb.ca / Student123!</span>
            <span>Professor: professor@unb.ca / Professor123!</span>
          </aside>
        )}

        <p className={styles.footerNote}>
          Frontend demo · Account details are not sent to a server
        </p>
      </section>
    </main>
  );
}

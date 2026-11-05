"use client";

import {
  useEffect,
  useRef,
  useState,
  useSyncExternalStore,
  type FormEvent,
} from "react";
import styles from "./page.module.css";

type Role = "student" | "professor";
type AuthMode = "login" | "signup";
type ThemeMode = "light" | "dark";
type Account = { email: string; password: string; role: Role };

// Turn this on when self-service sign-up is ready to be shown again.
const SIGN_UP_ENABLED = false;

// Read the saved preference after hydration so server and browser markup initially agree.
const themeListeners = new Set<() => void>();
let fallbackTheme: ThemeMode = "light";

function getThemeSnapshot(): ThemeMode {
  try {
    const savedTheme = window.localStorage.getItem("attendance-theme");
    fallbackTheme = savedTheme === "dark" ? "dark" : "light";
  } catch (error) {
    console.error("Could not read the theme preference.", error);
  }
  return fallbackTheme;
}

function subscribeToTheme(listener: () => void) {
  themeListeners.add(listener);
  window.addEventListener("storage", listener);
  return () => {
    themeListeners.delete(listener);
    window.removeEventListener("storage", listener);
  };
}

function saveThemePreference(theme: ThemeMode) {
  fallbackTheme = theme;
  try {
    window.localStorage.setItem("attendance-theme", theme);
  } catch (error) {
    console.error("Could not save the theme preference.", error);
  }
  themeListeners.forEach((listener) => listener());
}

const demoAccounts: Account[] = [
  { email: "student@unb.ca", password: "Student123!", role: "student" },
  { email: "professor@unb.ca", password: "Professor123!", role: "professor" },
];

export default function Home() {
  const theme = useSyncExternalStore(
    subscribeToTheme,
    getThemeSnapshot,
    () => "light",
  );
  const [mode, setMode] = useState<AuthMode>("login");
  const [role, setRole] = useState<Role>("student");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [accounts, setAccounts] = useState<Account[]>(demoAccounts);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [cameraStream, setCameraStream] = useState<MediaStream | null>(null);
  const [facePreview, setFacePreview] = useState<string | null>(null);
  const [cameraError, setCameraError] = useState("");
  const [privacyConsent, setPrivacyConsent] = useState(false);
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  function toggleTheme() {
    saveThemePreference(theme === "light" ? "dark" : "light");
  }

  useEffect(() => {
    const video = videoRef.current;
    if (video && cameraStream) {
      video.srcObject = cameraStream;
      void video.play().catch(() => {
        setCameraError("The camera preview could not start. Check your browser permissions.");
      });
    }

    return () => cameraStream?.getTracks().forEach((track) => track.stop());
  }, [cameraStream]);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setMessage("");

    if (mode === "signup") {
      if (!facePreview) {
        setError("Please complete the face registration preview before creating your account.");
        return;
      }
      if (!privacyConsent) {
        setError("Please confirm that you understand how this demo handles your face preview.");
        return;
      }
      if (accounts.some((account) => account.email === email.trim().toLowerCase())) {
        setError("An account with this email already exists in the demo. Log in instead.");
        return;
      }

      setAccounts((current) => [
        ...current,
        { email: email.trim().toLowerCase(), password, role },
      ]);
      setEmail(email.trim().toLowerCase());
      setPassword("");
      setFullName("");
      setFacePreview(null);
      setPrivacyConsent(false);
      changeMode("login");
      setMessage("Demo account created. Sign in with your email and password to continue.");
      return;
    }

    const account = accounts.find(
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

  function changeMode(nextMode: AuthMode) {
    stopCamera();
    setMode(nextMode);
    setError("");
    setMessage("");
    setCameraError("");
    setFacePreview(null);
    setPrivacyConsent(false);
  }

  async function startCamera() {
    setCameraError("");
    setError("");
    if (!navigator.mediaDevices?.getUserMedia) {
      setCameraError("Camera access requires a supported browser on localhost or HTTPS.");
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: false,
        video: { facingMode: "user", width: { ideal: 640 }, height: { ideal: 480 } },
      });
      setCameraStream(stream);
      setFacePreview(null);
    } catch (cameraRequestError) {
      const permissionDenied =
        cameraRequestError instanceof DOMException &&
        cameraRequestError.name === "NotAllowedError";
      setCameraError(
        permissionDenied
          ? "Camera permission was declined. Allow access in your browser settings and try again."
          : "The camera could not be opened. Check that it is available and try again.",
      );
    }
  }

  function captureFacePreview() {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas || video.videoWidth === 0 || video.videoHeight === 0) {
      setCameraError("Wait for the camera preview to load before taking a photo.");
      return;
    }

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const context = canvas.getContext("2d");
    if (!context) {
      setCameraError("Could not prepare the face preview in this browser.");
      return;
    }

    context.drawImage(video, 0, 0, canvas.width, canvas.height);
    setFacePreview(canvas.toDataURL("image/jpeg", 0.85));
    setCameraError("");
    stopCamera();
  }

  function stopCamera() {
    cameraStream?.getTracks().forEach((track) => track.stop());
    setCameraStream(null);
  }

  return (
    <main className={`${styles.page} ${theme === "dark" ? styles.dark : ""}`}>
      {/* Keep the product name and theme control together in the page header. */}
      <header className={styles.header}>
        <a aria-label="Secure University Attendance System home" className={styles.brand} href="#">
          <span aria-hidden="true" className={styles.brandMark}>SA</span>
          <span>Secure Attendance System</span>
        </a>
        <div className={styles.headerActions}>
          <span className={styles.school}>UNB ATTENDANCE PORTAL</span>
          <button
            aria-label={`Switch to ${theme === "light" ? "dark" : "light"} mode`}
            aria-pressed={theme === "dark"}
            className={styles.themeToggle}
            onClick={toggleTheme}
            type="button"
          >
            <span aria-hidden="true" className={styles.themeIcon}>
              {theme === "light" ? "☾" : "☼"}
            </span>
            <span>{theme === "light" ? "Dark" : "Light"} mode</span>
          </button>
        </div>
      </header>

      <div className={styles.mainLayout}>
        <section aria-labelledby="intro-heading" className={styles.intro}>
          <p className={styles.eyebrow}>UNIVERSITY OF NEW BRUNSWICK</p>
          <h1 id="intro-heading">Attendance, made simple.</h1>
          <p className={styles.introCopy}>
            Sign in to manage campus attendance in one place.
          </p>

          {/* This card is a static visual preview; it does not display live class data. */}
          <div aria-label="Attendance portal preview" className={styles.previewCard}>
            <div className={styles.previewTopline}>
              <span>STUDENT & FACULTY ACCESS</span>
            </div>
            <p className={styles.previewTitle}>Campus<br />attendance</p>
            <div className={styles.classCard}>
              <span aria-hidden="true" className={styles.classIcon}>SA</span>
              <span className={styles.classDetails}>
                <strong>Secure Attendance</strong>
                <small>University of New Brunswick</small>
              </span>
            </div>
            <div aria-hidden="true" className={styles.previewAccent} />
          </div>

          <p className={styles.introNote}>
            For students and instructors
          </p>
        </section>

        <section aria-labelledby="form-heading" className={styles.authCard}>
          <div className={styles.cardHeading}>
            <p className={styles.eyebrow}>CAMPUS PORTAL</p>
            <h2 id="form-heading">
              {mode === "login" ? "Welcome back." : "Create your account."}
            </h2>
            <p>
              {mode === "login"
                ? "Sign in with your university account."
                : "A few details to get you started."}
            </p>
          </div>

          <div
            aria-label="Account access"
            className={`${styles.tabs} ${!SIGN_UP_ENABLED ? styles.loginOnlyTabs : ""}`}
            role="tablist"
          >
            <button
              aria-selected={mode === "login"}
              className={mode === "login" ? styles.selectedTab : ""}
              onClick={() => changeMode("login")}
              role="tab"
              type="button"
            >
              Log in
            </button>
            {SIGN_UP_ENABLED && (
              <button
                aria-selected={mode === "signup"}
                className={mode === "signup" ? styles.selectedTab : ""}
                onClick={() => changeMode("signup")}
                role="tab"
                type="button"
              >
                Sign up
              </button>
            )}
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

            {mode === "signup" && (
              /* The sign-up preview stays in the browser and is not uploaded. */
              <div className={styles.faceSection}>
                <div className={styles.faceHeading}>
                  <span>
                    <strong>Face registration</strong>
                    <small>Register one face with your account</small>
                  </span>
                  <span className={styles.required}>REQUIRED</span>
                </div>
                <canvas aria-hidden="true" className={styles.hiddenCanvas} ref={canvasRef} />
                {facePreview ? (
                  <div className={styles.facePreviewRow}>
                    <div
                      aria-label="Temporary face-registration preview"
                      className={styles.facePreview}
                      role="img"
                      style={{ backgroundImage: `url("${facePreview}")` }}
                    />
                    <span><strong>Preview captured</strong><small>Not uploaded or saved</small></span>
                    <button className={styles.retakeButton} onClick={startCamera} type="button">
                      Retake
                    </button>
                  </div>
                ) : (
                  <div className={styles.cameraPreview}>
                    {cameraStream ? (
                      <video autoPlay muted playsInline ref={videoRef} />
                    ) : (
                      <span>Camera preview will appear here</span>
                    )}
                  </div>
                )}
                {cameraError && <p className={styles.error} role="alert">{cameraError}</p>}
                {!facePreview && (
                  <button
                    className={styles.cameraButton}
                    onClick={cameraStream ? captureFacePreview : startCamera}
                    type="button"
                  >
                    {cameraStream ? "Capture face preview" : "Start face registration"}
                  </button>
                )}
                <label className={styles.consent}>
                  <input
                    checked={privacyConsent}
                    onChange={(event) => setPrivacyConsent(event.target.checked)}
                    type="checkbox"
                  />
                  I understand this is a local camera preview.
                </label>
              </div>
            )}

            {error && <p className={styles.error} role="alert">{error}</p>}
            {message && <p className={styles.message} role="status">{message}</p>}

            <button className={styles.submitButton} type="submit">
              {mode === "login" ? "Log in" : "Create account"}
            </button>
          </form>

          <p className={styles.cardFooter}>University of New Brunswick · Campus access</p>
        </section>
      </div>

      <footer className={styles.footer}>
        <span>Secure Attendance System</span>
        <span>Designed for your campus day</span>
      </footer>
    </main>
  );
}

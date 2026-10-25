"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import styles from "./page.module.css";

// This type keeps locally created demo accounts aligned with the available sign-up roles.
type Role = "student" | "professor";
type AuthMode = "login" | "signup";
type Account = { email: string; password: string; role: Role };

// These sample credentials make it possible to preview both account roles without a backend.
const demoAccounts: Account[] = [
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
  const [accounts, setAccounts] = useState<Account[]>(demoAccounts);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [cameraStream, setCameraStream] = useState<MediaStream | null>(null);
  const [facePreview, setFacePreview] = useState<string | null>(null);
  const [cameraError, setCameraError] = useState("");
  const [privacyConsent, setPrivacyConsent] = useState(false);
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  // This effect shows the requested camera stream and releases it when the preview closes.
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

  // This handler validates demo credentials and keeps all form actions on the login screen.
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

  // This helper switches between the two forms and clears status from the previous form.
  function changeMode(nextMode: AuthMode) {
    stopCamera();
    setMode(nextMode);
    setError("");
    setMessage("");
    setCameraError("");
    setFacePreview(null);
    setPrivacyConsent(false);
  }

  // This function requests camera access only after the user starts face registration.
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

  // This function creates a temporary in-memory image preview and immediately stops the camera.
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

  // This helper releases the camera when the preview is captured or the user changes forms.
  function stopCamera() {
    cameraStream?.getTracks().forEach((track) => track.stop());
    setCameraStream(null);
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

          {mode === "signup" && (
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
                  {/* This temporary image stays in memory only and is cleared when the form is reset. */}
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
              <p className={styles.privacyNote}>
                This demo does not recognize, upload, or save face images. Real face verification
                needs a university-approved service.
              </p>
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

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
  const [comparisonOpen, setComparisonOpen] = useState(false);
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
        <a aria-label="Secure University Attendance System home" className={styles.brand} href="#">
          <span aria-hidden="true" className={styles.brandMark}>SA</span>
          <span>Secure Attendance System</span>
        </a>
        <span className={styles.school}>UNIVERSITY OF NEW BRUNSWICK</span>
      </header>

      {comparisonOpen ? <FaceComparison onBack={() => setComparisonOpen(false)} /> : (
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
        <button type="button" className={styles.cameraButton} style={{ marginTop: 16 }}
          onClick={() => { stopCamera(); setComparisonOpen(true); }}>
          Test face verification
        </button>
      </section>
      )}
    </main>
  );
}

type CaptureTarget = "reference" | "selfie";
type FaceResult = { matched: boolean; distance: number; threshold: number };
const API_URL = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:18000").replace(/\/$/, "");

function photoBlob(dataUrl: string): Blob {
  const bytes = Uint8Array.from(atob(dataUrl.split(",")[1]), (char) => char.charCodeAt(0));
  return new Blob([bytes], { type: "image/jpeg" });
}

// This panel calls the real backend; login and signup remain local demos.
function FaceComparison({ onBack }: { onBack: () => void }) {
  const [photos, setPhotos] = useState<Record<CaptureTarget, string | null>>({ reference: null, selfie: null });
  const [target, setTarget] = useState<CaptureTarget>("reference");
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [opening, setOpening] = useState(false);
  const [consent, setConsent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<FaceResult | null>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const cameraRequest = useRef(0);
  const requestRef = useRef<AbortController | null>(null);

  useEffect(() => () => {
    cameraRequest.current += 1;
    streamRef.current?.getTracks().forEach((track) => track.stop());
    requestRef.current?.abort();
  }, []);

  useEffect(() => {
    if (videoRef.current && stream) {
      videoRef.current.srcObject = stream;
      void videoRef.current.play().catch(() => setError("Camera preview could not start. Try again."));
    }
  }, [stream]);

  function stopCamera() {
    cameraRequest.current += 1;
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    setStream(null);
    setOpening(false);
  }

  async function startCamera(nextTarget: CaptureTarget) {
    stopCamera();
    setError("");
    setResult(null);
    setTarget(nextTarget);
    if (!navigator.mediaDevices?.getUserMedia) {
      setError("Camera access requires localhost or HTTPS and a supported browser.");
      return;
    }
    const requestId = cameraRequest.current;
    setOpening(true);
    try {
      const nextStream = await navigator.mediaDevices.getUserMedia({
        audio: false,
        video: { facingMode: "user", width: { ideal: 640 }, height: { ideal: 480 } },
      });
      if (requestId !== cameraRequest.current) {
        nextStream.getTracks().forEach((track) => track.stop());
        return;
      }
      streamRef.current = nextStream;
      setStream(nextStream);
    } catch {
      if (requestId === cameraRequest.current) {
        setError("Could not open the camera. Allow camera access and check that another app is not using it.");
      }
    } finally {
      if (requestId === cameraRequest.current) setOpening(false);
    }
  }

  function capturePhoto() {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas || !video.videoWidth || !video.videoHeight) {
      setError("Wait until the camera preview is ready, then capture again.");
      return;
    }
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const context = canvas.getContext("2d");
    if (!context) {
      setError("Could not capture a photo in this browser.");
      return;
    }
    context.drawImage(video, 0, 0, canvas.width, canvas.height);
    setPhotos((current) => ({ ...current, [target]: canvas.toDataURL("image/jpeg", 0.9) }));
    setError("");
    setResult(null);
    stopCamera();
  }

  async function comparePhotos() {
    if (!photos.reference || !photos.selfie || !consent || busy) return;
    stopCamera();
    setBusy(true);
    setError("");
    setResult(null);
    const controller = new AbortController();
    requestRef.current = controller;
    const timeout = setTimeout(() => controller.abort(), 120000);
    try {
      const body = new FormData();
      body.append("reference", photoBlob(photos.reference), "reference.jpg");
      body.append("selfie", photoBlob(photos.selfie), "selfie.jpg");
      // The browser sets Content-Type, including the multipart boundary.
      const response = await fetch(API_URL + "/face-spike/compare", {
        method: "POST", body, signal: controller.signal,
      });
      const data: unknown = await response.json().catch(() => null);
      if (!response.ok) {
        let detail = "Comparison failed (HTTP " + response.status + "). Check the backend logs.";
        if (data && typeof data === "object" && "detail" in data) {
          if (typeof data.detail === "string") detail = data.detail;
          else if (Array.isArray(data.detail)) {
            detail = data.detail.map((item: unknown) =>
              item && typeof item === "object" && "msg" in item ? String(item.msg) : "Invalid photo upload."
            ).join(" ");
          }
        }
        throw new Error(detail);
      }
      if (!data || typeof data !== "object" || !("matched" in data) ||
          typeof data.matched !== "boolean" || !("distance" in data) ||
          typeof data.distance !== "number" || !Number.isFinite(data.distance) ||
          !("threshold" in data) || typeof data.threshold !== "number" || !Number.isFinite(data.threshold)) {
        throw new Error("The backend returned an unexpected comparison response.");
      }
      setResult({ matched: data.matched, distance: data.distance, threshold: data.threshold });
    } catch (requestError) {
      if (controller.signal.aborted) {
        setError("The request timed out after two minutes. Check the backend logs; the model may still be downloading.");
      } else if (requestError instanceof TypeError) {
        setError("Could not reach the face API. Check Docker, the API address, and CORS permission for http://localhost:3000.");
      } else {
        setError(requestError instanceof Error ? requestError.message : "Face comparison failed.");
      }
    } finally {
      clearTimeout(timeout);
      requestRef.current = null;
      setBusy(false);
    }
  }

  const cannotCompare = busy || !consent || !photos.reference || !photos.selfie || !!stream || opening;
  return (
    <section aria-labelledby="face-test-heading" className={styles.authCard}>
      <div className={styles.cardHeading}>
        <p className={styles.eyebrow}>FACE VERIFICATION TEST</p>
        <h1 id="face-test-heading">Compare two photos</h1>
        <p>Capture a reference and a new selfie. Keep your face visible and evenly lit; you can keep your head covering on.</p>
      </div>
      <div className={styles.faceSection}>
        <label className={styles.consent}>
          <input type="checkbox" checked={consent} disabled={busy || opening || !!stream}
            onChange={(event) => setConsent(event.target.checked)} />
          I agree to send these two photos to the configured backend for this comparison. This test does not enroll a face or create an account.
        </label>
        {(["reference", "selfie"] as const).map((photoTarget) => (
          <div className={styles.facePreviewRow} key={photoTarget}>
            {photos[photoTarget] && <div className={styles.facePreview} role="img"
              aria-label={"Captured " + photoTarget + " photo"}
              style={{ backgroundImage: 'url("' + photos[photoTarget] + '")' }} />}
            <span>
              <strong>{photoTarget === "reference" ? "1. Reference photo" : "2. New selfie"}</strong>
              <small>{photos[photoTarget] ? "Captured" : "Not captured yet"}</small>
            </span>
            <button type="button" className={styles.retakeButton}
              disabled={!consent || busy || opening || !!stream}
              onClick={() => void startCamera(photoTarget)}>
              {photos[photoTarget] ? "Retake" : "Open camera"}
            </button>
          </div>
        ))}
        <canvas ref={canvasRef} className={styles.hiddenCanvas} aria-hidden="true" />
        {(opening || stream) && <>
          <p style={{ margin: 0, fontSize: 12 }}>
            {opening ? "Opening camera…" : "Capturing " + (target === "reference" ? "reference photo" : "new selfie")}
          </p>
          <div className={styles.cameraPreview} style={{ height: "auto", aspectRatio: "4 / 3" }}>
            {stream ? <video ref={videoRef} autoPlay muted playsInline style={{ objectFit: "contain" }} /> : <span>Waiting for camera permission…</span>}
          </div>
          <button type="button" className={styles.cameraButton} disabled={!stream} onClick={capturePhoto}>Capture photo</button>
          <button type="button" className={styles.cameraButton} onClick={stopCamera}>Cancel camera</button>
        </>}
      </div>
      <button type="button" className={styles.submitButton} style={{ width: "100%", opacity: cannotCompare ? 0.55 : 1 }}
        disabled={cannotCompare} onClick={() => void comparePhotos()}>
        {busy ? "Comparing…" : "Compare faces"}
      </button>
      {busy && <p className={styles.message} role="status">Processing photos. The first comparison may take longer while the model loads.</p>}
      {error && <p className={styles.error} role="alert">{error}</p>}
      {result && <div className={result.matched ? styles.message : styles.error} role="status">
        <strong>{result.matched ? "Face matched" : "Face did not match"}</strong>
        <div>Distance: {result.distance.toFixed(6)} · Threshold: {result.threshold}</div>
        <div>Lower distance means greater similarity. This result is not an attendance decision.</div>
      </div>}
      <button type="button" className={styles.cameraButton} style={{ marginTop: 16 }} disabled={busy}
        onClick={onBack}>Back to login / signup</button>
    </section>
  );
}

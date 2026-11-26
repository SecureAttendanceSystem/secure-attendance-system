"use client";

import {
  useEffect,
  useRef,
  useState,
  useSyncExternalStore,
  type FormEvent,
} from "react";
import { isAuthRetryableFetchError } from "@supabase/supabase-js";
import { getSupabase } from "@/lib/supabase";
import styles from "./page.module.css";

type Role = "student" | "professor";
type AuthMode = "login" | "signup";
type ThemeMode = "light" | "dark";
type Profile = { full_name: string; role: string };
type FaceScanResult = { matched: boolean; distance: number };

// Turn this on when self-service sign-up is ready to be shown again.
const SIGN_UP_ENABLED = false;

const API_BASE_URL = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:18000").replace(/\/$/, "");

const NOT_CONFIGURED =
  "Sign-in isn't configured. Set NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY in web/.env.local.";

// Supabase checks the password; the backend owns the profile and rejects accounts without one.
async function fetchProfile(accessToken: string): Promise<Profile> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/auth/me`, {
      headers: { Authorization: `Bearer ${accessToken}` },
    });
  } catch {
    throw new Error("Could not reach the server. Is the backend running?");
  }
  if (response.status === 401 || response.status === 403) {
    throw new Error("This account isn't set up for the portal yet. Contact an administrator.");
  }
  if (!response.ok) {
    throw new Error(`Could not load your profile (HTTP ${response.status}). Try again.`);
  }
  return response.json();
}

function apiError(data: unknown, fallback: string): string {
  if (data && typeof data === "object" && "detail" in data && typeof data.detail === "string") {
    return data.detail;
  }
  return fallback;
}

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
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [profile, setProfile] = useState<Profile | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [cameraStream, setCameraStream] = useState<MediaStream | null>(null);
  const [facePreview, setFacePreview] = useState<string | null>(null);
  const [cameraError, setCameraError] = useState("");
  const [privacyConsent, setPrivacyConsent] = useState(false);
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  // Face scan after login: compares a fresh selfie with the signed-in student's enrolled face.
  const [faceScanStream, setFaceScanStream] = useState<MediaStream | null>(null);
  const [faceScanPhoto, setFaceScanPhoto] = useState<string | null>(null);
  const [faceScanResult, setFaceScanResult] = useState<FaceScanResult | null>(null);
  const [faceScanBusy, setFaceScanBusy] = useState(false);
  const [faceScanError, setFaceScanError] = useState("");
  const faceScanVideoRef = useRef<HTMLVideoElement>(null);
  const faceScanCanvasRef = useRef<HTMLCanvasElement>(null);
  const faceScanCameraRequest = useRef(0);
  const faceScanStreamRef = useRef<MediaStream | null>(null);
  const faceScanRequest = useRef<AbortController | null>(null);

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

  useEffect(() => {
    const video = faceScanVideoRef.current;
    if (video && faceScanStream) {
      video.srcObject = faceScanStream;
      void video.play().catch(() => {
        setFaceScanError("The camera preview could not start. Check your browser permissions.");
      });
    }
  }, [faceScanStream]);

  // Turn the camera off and cancel any face check once the signed-in user goes away.
  useEffect(() => {
    if (!profile) return;
    return () => {
      faceScanCameraRequest.current += 1;
      faceScanStreamRef.current?.getTracks().forEach((track) => track.stop());
      faceScanStreamRef.current = null;
      faceScanRequest.current?.abort();
    };
  }, [profile]);

  // Restore a saved session on load, and drop the profile whenever the session ends.
  useEffect(() => {
    const supabase = getSupabase();
    if (!supabase) return;

    const { data: { subscription } } = supabase.auth.onAuthStateChange((event, session) => {
      if (event === "SIGNED_OUT") {
        setProfile(null);
      } else if (event === "INITIAL_SESSION" && session) {
        // Not awaited: awaiting Supabase calls inside this callback can deadlock.
        fetchProfile(session.access_token)
          .then(setProfile)
          .catch((profileError: Error) => {
            setError(profileError.message);
            void supabase.auth.signOut();
          });
      }
    });
    return () => subscription.unsubscribe();
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
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

      setEmail(email.trim().toLowerCase());
      setPassword("");
      setFullName("");
      setFacePreview(null);
      setPrivacyConsent(false);
      changeMode("login");
      setMessage("No account was created. An administrator sets up portal accounts; sign in once yours is ready.");
      return;
    }

    const supabase = getSupabase();
    if (!supabase) {
      setError(NOT_CONFIGURED);
      return;
    }

    setIsSubmitting(true);
    try {
      const { data, error: signInError } = await supabase.auth.signInWithPassword({
        email: email.trim().toLowerCase(),
        password,
      });
      if (signInError || !data.session) {
        setError(
          isAuthRetryableFetchError(signInError)
            ? "Could not reach the sign-in service. Check your connection and try again."
            : signInError?.message ?? "Could not sign in. Try again.",
        );
        return;
      }

      setPassword("");
      try {
        const signedIn = await fetchProfile(data.session.access_token);
        resetFaceScan();
        setProfile(signedIn);
        if (signedIn.role === "student") void startFaceScan();
      } catch (profileError) {
        setError(profileError instanceof Error ? profileError.message : "Could not load your profile.");
        await supabase.auth.signOut();
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  // Only clear the profile once Supabase has removed the saved session, or a reload would sign back in.
  async function handleSignOut() {
    setError("");
    setMessage("");
    setIsSubmitting(true);
    try {
      const result = await getSupabase()?.auth.signOut();
      if (result?.error) {
        setError("Could not sign out. Check your connection and try again.");
        return;
      }
      resetFaceScan();
      setProfile(null);
    } finally {
      setIsSubmitting(false);
    }
  }

  function resetFaceScan() {
    stopFaceScanCamera();
    faceScanRequest.current?.abort();
    faceScanRequest.current = null;
    setFaceScanBusy(false);
    setFaceScanPhoto(null);
    setFaceScanResult(null);
    setFaceScanError("");
  }

  async function startFaceScan() {
    stopFaceScanCamera();
    const requestId = faceScanCameraRequest.current;
    setFaceScanError("");
    setFaceScanResult(null);
    if (!navigator.mediaDevices?.getUserMedia) {
      setFaceScanError("Camera access requires a supported browser on localhost or HTTPS.");
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: false,
        video: { facingMode: "user", width: { ideal: 640 }, height: { ideal: 480 } },
      });
      if (requestId !== faceScanCameraRequest.current) {
        stream.getTracks().forEach((track) => track.stop());
        return;
      }
      faceScanStreamRef.current = stream;
      setFaceScanStream(stream);
      setFaceScanPhoto(null);
    } catch {
      if (requestId !== faceScanCameraRequest.current) return;
      setFaceScanError("Could not open the camera. Allow access and check that no other app is using it.");
    }
  }

  function stopFaceScanCamera() {
    faceScanCameraRequest.current += 1;
    faceScanStreamRef.current?.getTracks().forEach((track) => track.stop());
    faceScanStreamRef.current = null;
    setFaceScanStream(null);
  }

  function captureFaceScan() {
    const video = faceScanVideoRef.current;
    const canvas = faceScanCanvasRef.current;
    if (!video || !canvas || video.videoWidth === 0 || video.videoHeight === 0) {
      setFaceScanError("Wait for the camera preview to load before capturing.");
      return;
    }
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const context = canvas.getContext("2d");
    if (!context) {
      setFaceScanError("Could not capture a photo in this browser.");
      return;
    }
    context.drawImage(video, 0, 0, canvas.width, canvas.height);
    setFaceScanPhoto(canvas.toDataURL("image/jpeg", 0.9));
    setFaceScanError("");
    stopFaceScanCamera();
  }

  async function submitFaceScan() {
    if (!faceScanPhoto || faceScanRequest.current) return;
    const controller = new AbortController();
    faceScanRequest.current = controller;
    const timeout = setTimeout(() => controller.abort(), 120_000);
    setFaceScanBusy(true);
    setFaceScanError("");
    try {
      // Read the session at send time; Supabase refreshes the access token in the background.
      const session = (await getSupabase()?.auth.getSession())?.data.session;
      if (!session) {
        setFaceScanError("Your session has ended. Sign in again.");
        return;
      }
      const selfieBlob = await (await fetch(faceScanPhoto)).blob();
      const body = new FormData();
      body.append("selfie", selfieBlob, "selfie.jpg");

      const response = await fetch(`${API_BASE_URL}/face/verify`, {
        method: "POST",
        headers: { Authorization: `Bearer ${session.access_token}` },
        body,
        signal: controller.signal,
      });
      const data = await response.json().catch(() => null);
      if (faceScanRequest.current !== controller) return;

      if (!response.ok) {
        setFaceScanError(apiError(data, "Could not verify your face. Try again."));
        return;
      }
      if (typeof data?.matched !== "boolean" || typeof data?.distance !== "number" || !Number.isFinite(data.distance)) {
        setFaceScanError("The server returned an unexpected face verification response.");
        return;
      }
      setFaceScanResult({ matched: data.matched, distance: data.distance });
    } catch {
      if (faceScanRequest.current === controller) {
        setFaceScanError(controller.signal.aborted
          ? "Face verification timed out. Please try again."
          : "Could not reach the server. Is the backend running?");
      }
    } finally {
      clearTimeout(timeout);
      if (faceScanRequest.current === controller) {
        faceScanRequest.current = null;
        setFaceScanBusy(false);
      }
    }
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
              {profile ? "You're signed in." : mode === "login" ? "Welcome back." : "Create your account."}
            </h2>
            <p>
              {profile
                ? `Signed in as ${profile.full_name} (${profile.role}).`
                : mode === "login"
                  ? "Sign in with your university account."
                  : "A few details to get you started."}
            </p>
          </div>

          {profile ? (
            <div className={styles.form}>
              {profile.role === "student" ? (
                <div className={styles.faceSection}>
                  <div className={styles.faceHeading}>
                    <span>
                      <strong>Face scan</strong>
                      <small>Verify it&apos;s really you</small>
                    </span>
                  </div>
                  <canvas aria-hidden="true" className={styles.hiddenCanvas} ref={faceScanCanvasRef} />
                  {faceScanResult ? (
                    <p className={faceScanResult.matched ? styles.message : styles.error} role="status">
                      {faceScanResult.matched ? "Face matched." : "Face did not match."}{" "}
                      (distance {faceScanResult.distance.toFixed(4)})
                    </p>
                  ) : faceScanPhoto ? (
                    <div className={styles.facePreviewRow}>
                      <div
                        aria-label="Captured face scan"
                        className={styles.facePreview}
                        role="img"
                        style={{ backgroundImage: `url("${faceScanPhoto}")` }}
                      />
                      <span><strong>Photo captured</strong><small>Ready to verify</small></span>
                      <button className={styles.retakeButton} disabled={faceScanBusy} onClick={startFaceScan} type="button">
                        Retake
                      </button>
                    </div>
                  ) : (
                    <div className={styles.cameraPreview} style={{ height: "auto", aspectRatio: "4 / 3" }}>
                      {faceScanStream ? (
                        <video autoPlay muted playsInline ref={faceScanVideoRef} style={{ objectFit: "contain" }} />
                      ) : (
                        <span>Camera preview will appear here</span>
                      )}
                    </div>
                  )}
                  {faceScanError && <p className={styles.error} role="alert">{faceScanError}</p>}
                  {faceScanResult && (
                    <button className={styles.cameraButton} onClick={startFaceScan} type="button">
                      Scan again
                    </button>
                  )}
                  {!faceScanPhoto && (
                    <button
                      className={styles.cameraButton}
                      onClick={faceScanStream ? captureFaceScan : startFaceScan}
                      type="button"
                    >
                      {faceScanStream ? "Capture photo" : "Start face scan"}
                    </button>
                  )}
                  {faceScanPhoto && !faceScanResult && (
                    <button
                      className={styles.submitButton}
                      disabled={faceScanBusy}
                      onClick={() => void submitFaceScan()}
                      type="button"
                    >
                      {faceScanBusy ? "Verifying…" : "Verify my face"}
                    </button>
                  )}
                </div>
              ) : (
                <p className={styles.message} role="status">Face scan applies to student accounts.</p>
              )}

              {error && <p className={styles.error} role="alert">{error}</p>}
              <button className={styles.submitButton} disabled={isSubmitting} onClick={handleSignOut} type="button">
                {isSubmitting ? "Signing out…" : "Sign out"}
              </button>
            </div>
          ) : (
            <>
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
                  minLength={mode === "signup" ? 8 : undefined}
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

                <button className={styles.submitButton} disabled={isSubmitting} type="submit">
                  {mode === "login" ? (isSubmitting ? "Signing in…" : "Log in") : "Create account"}
                </button>
              </form>
            </>
          )}

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

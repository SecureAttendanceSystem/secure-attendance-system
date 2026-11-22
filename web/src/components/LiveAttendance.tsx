"use client";

import { useCallback, useEffect, useState } from "react";
import {
  browserSupportsWebAuthn,
  startAuthentication,
  startRegistration,
  WebAuthnError,
} from "@simplewebauthn/browser";
import styles from "@/app/page.module.css";
import { apiFetch } from "@/lib/api";

type Course = { id: string; code: string; title: string; term: string };
type LiveSession = {
  id: string;
  course_id: string;
  status: string;
  started_at: string | null;
  ended_at: string | null;
  checked_in_at: string | null;
};
type AttendanceEntry = {
  student_id: string;
  full_name: string;
  email: string;
  status: "present" | "absent";
  checked_in_at: string | null;
};
type SessionAttendance = {
  session: LiveSession;
  enrolled_count: number;
  present_count: number;
  students: AttendanceEntry[];
};
type Passkey = { id: string; created_at: string | null; last_used_at: string | null };
type CeremonyOptions = { challenge_id: string; options: Record<string, unknown> };

const REFRESH_MS = 4000;

function timeOf(iso: string | null): string {
  return iso ? new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "";
}

// Turn browser WebAuthn failures (cancelled prompt, timeout, unsupported) into a readable message.
function passkeyErrorMessage(error: unknown): string {
  if (error instanceof WebAuthnError && error.code === "ERROR_AUTHENTICATOR_PREVIOUSLY_REGISTERED") {
    return "This device already has a passkey for your account.";
  }
  if (error instanceof Error && (error.name === "NotAllowedError" || error.name === "AbortError")) {
    return "The passkey prompt was cancelled or timed out.";
  }
  return error instanceof Error ? error.message : "Something went wrong with the passkey.";
}

export default function LiveAttendance({ role }: { role: string }) {
  const isProfessor = role === "professor";
  const isStudent = role === "student";

  const [courses, setCourses] = useState<Course[] | null>(null);
  const [liveByCourse, setLiveByCourse] = useState<Record<string, LiveSession | null>>({});
  const [attendance, setAttendance] = useState<Record<string, SessionAttendance>>({});
  const [passkeys, setPasskeys] = useState<Passkey[] | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const refresh = useCallback(async () => {
    const myCourses = await apiFetch<Course[]>("/courses");
    const sessions = await Promise.all(
      myCourses.map((course) =>
        apiFetch<LiveSession | null>(`/courses/${course.id}/sessions/active`),
      ),
    );
    const live: Record<string, LiveSession | null> = {};
    myCourses.forEach((course, index) => (live[course.id] = sessions[index]));

    const rosters: Record<string, SessionAttendance> = {};
    if (isProfessor) {
      await Promise.all(
        sessions
          .filter((session): session is LiveSession => session !== null)
          .map(async (session) => {
            rosters[session.id] = await apiFetch<SessionAttendance>(`/sessions/${session.id}/attendance`);
          }),
      );
    }
    setCourses(myCourses);
    setLiveByCourse(live);
    setAttendance(rosters);
  }, [isProfessor]);

  const loadPasskeys = useCallback(
    () => (isStudent ? apiFetch<Passkey[]>("/passkeys") : Promise.resolve(null)),
    [isStudent],
  );

  // Poll so a student sees a session appear, and a professor sees check-ins arrive, without reloading.
  useEffect(() => {
    let stopped = false;
    const tick = () =>
      refresh()
        .then(() => !stopped && setError(""))
        .catch((loadError: Error) => !stopped && setError(loadError.message));
    void tick();
    loadPasskeys()
      .then((loaded) => !stopped && setPasskeys(loaded))
      .catch((loadError: Error) => !stopped && setError(loadError.message));
    const timer = window.setInterval(tick, REFRESH_MS);
    return () => {
      stopped = true;
      window.clearInterval(timer);
    };
  }, [refresh, loadPasskeys]);

  async function run(key: string, action: () => Promise<string | void>) {
    setBusy(key);
    setError("");
    setNotice("");
    try {
      const done = await action();
      if (done) setNotice(done);
      await refresh();
    } catch (actionError) {
      setError(passkeyErrorMessage(actionError));
    } finally {
      setBusy(null);
    }
  }

  const startSession = (course: Course) =>
    run(course.id, async () => {
      await apiFetch(`/courses/${course.id}/sessions`, { method: "POST" });
      return `Live session started for ${course.code}.`;
    });

  const endSession = (course: Course, session: LiveSession) =>
    run(course.id, async () => {
      await apiFetch(`/sessions/${session.id}/end`, { method: "POST" });
      return `Session for ${course.code} ended.`;
    });

  const registerPasskey = () =>
    run("passkey", async () => {
      const { challenge_id, options } = await apiFetch<CeremonyOptions>("/passkeys/register/options", {
        method: "POST",
      });
      const credential = await startRegistration({
        optionsJSON: options as unknown as Parameters<typeof startRegistration>[0]["optionsJSON"],
      });
      await apiFetch("/passkeys/register", {
        method: "POST",
        body: JSON.stringify({ challenge_id, credential }),
      });
      setPasskeys(await loadPasskeys());
      return "Passkey saved on this device. Only its public key was sent to the server.";
    });

  const checkIn = (course: Course, session: LiveSession) =>
    run(course.id, async () => {
      const { challenge_id, options } = await apiFetch<CeremonyOptions>(
        `/sessions/${session.id}/check-in/options`,
        { method: "POST" },
      );
      const credential = await startAuthentication({
        optionsJSON: options as unknown as Parameters<typeof startAuthentication>[0]["optionsJSON"],
      });
      await apiFetch(`/sessions/${session.id}/check-in`, {
        method: "POST",
        body: JSON.stringify({ challenge_id, credential }),
      });
      return `You're checked in to ${course.code}.`;
    });

  if (!isProfessor && !isStudent) return null;

  const webAuthnSupported = typeof window === "undefined" || browserSupportsWebAuthn();

  return (
    <div className={styles.faceSection}>
      <div className={styles.faceHeading}>
        <span>
          <strong>{isProfessor ? "Live attendance" : "Check in"}</strong>
          <small>
            {isProfessor
              ? "Start a session, then watch students check in."
              : "Verify with your device's passkey. No face data leaves your device."}
          </small>
        </span>
      </div>

      {isStudent && (
        <div className={styles.sessionRow}>
          <span>
            <strong>Passkey</strong>
            <small>
              {passkeys === null
                ? "Checking…"
                : passkeys.length > 0
                  ? `Set up (${passkeys.length} device${passkeys.length === 1 ? "" : "s"})`
                  : "Not set up yet"}
            </small>
          </span>
          <button
            className={styles.retakeButton}
            disabled={busy !== null || !webAuthnSupported}
            onClick={() => void registerPasskey()}
            type="button"
          >
            {busy === "passkey" ? "Waiting…" : passkeys?.length ? "Add this device" : "Set up passkey"}
          </button>
        </div>
      )}
      {!webAuthnSupported && (
        <p className={`${styles.message} ${styles.error}`}>This browser doesn&apos;t support passkeys.</p>
      )}

      {courses === null ? (
        <p className={styles.mutedNote}>Loading your courses…</p>
      ) : courses.length === 0 ? (
        <p className={styles.mutedNote}>
          {isProfessor ? "You aren't assigned to any courses yet." : "You aren't enrolled in any courses yet."}
        </p>
      ) : (
        courses.map((course) => {
          const session = liveByCourse[course.id] ?? null;
          const roster = session ? attendance[session.id] : undefined;
          return (
            <div className={styles.courseBlock} key={course.id}>
              <div className={styles.sessionRow}>
                <span>
                  <strong>
                    {course.code} · {course.title}
                  </strong>
                  <small>
                    {session
                      ? `Live since ${timeOf(session.started_at)}`
                      : "No live session"}
                  </small>
                </span>
                {session && <span className={styles.liveBadge}>LIVE</span>}
                {isProfessor && (
                  <button
                    className={styles.retakeButton}
                    disabled={busy !== null}
                    onClick={() => void (session ? endSession(course, session) : startSession(course))}
                    type="button"
                  >
                    {busy === course.id ? "…" : session ? "End session" : "Start session"}
                  </button>
                )}
                {isStudent && session && !session.checked_in_at && (
                  <button
                    className={styles.retakeButton}
                    disabled={busy !== null || !passkeys?.length}
                    onClick={() => void checkIn(course, session)}
                    title={passkeys?.length ? undefined : "Set up a passkey first"}
                    type="button"
                  >
                    {busy === course.id ? "Waiting…" : "Check in with passkey"}
                  </button>
                )}
                {isStudent && session?.checked_in_at && (
                  <span className={styles.presentBadge}>Present · {timeOf(session.checked_in_at)}</span>
                )}
              </div>

              {roster && (
                <div className={styles.rosterList}>
                  <p className={styles.mutedNote}>
                    {roster.present_count} of {roster.enrolled_count} checked in
                  </p>
                  <ul>
                    {roster.students.map((student) => (
                      <li key={student.student_id}>
                        <span>{student.full_name}</span>
                        <span className={student.status === "present" ? styles.presentBadge : styles.absentBadge}>
                          {student.status === "present" ? `Present · ${timeOf(student.checked_in_at)}` : "Not yet"}
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          );
        })
      )}

      {notice && <p className={styles.message} role="status">{notice}</p>}
      {error && <p className={`${styles.message} ${styles.error}`} role="alert">{error}</p>}
    </div>
  );
}

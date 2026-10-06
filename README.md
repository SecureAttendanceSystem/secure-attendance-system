# Secure University Attendance System

A capstone project for a centralized mobile attendance platform that aims to simplify classroom attendance and reduce proxy attendance through multiple verification checks.

## Overview

University attendance is often recorded through paper sign-in sheets, online forms, or separate course records. These methods can be difficult to manage consistently and can allow one student to mark another student present.

The proposed system brings attendance into one application. It combines university login, registered-device checks, location and proximity checks, and identity confirmation before the backend accepts a check-in.

Read the [project proposal](docs/Smart_Attendance_Proposal.pdf) for the full scope.

## Planned Features

- **University login:** Link attendance to a student's university account and enrolled courses.
- **Device binding:** Associate each student account with one approved phone, with staff approval for device changes.
- **GPS presence checks:** Verify that the student is within the configured classroom or building area.
- **Bluetooth Low Energy (BLE) proximity checks:** Detect a temporary signal from the professor's device or a classroom beacon.
- **Identity confirmation:** Evaluate built-in device authentication, such as Face ID where supported, or app-based facial recognition. The approach has not been finalized.
- **Live attendance:** Let professors start sessions and view accepted check-ins in real time.
- **Absence tickets and exceptions:** Allow students to submit absence requests and professors to review tickets or correct attendance when appropriate.
- **Role-based dashboards:** Provide tools suited to students, professors, and administrators.

## Planned Attendance Flow

1. A professor starts an attendance session, and enrolled students receive a notification.
2. A student signs in with their university account and selects **Attend**.
3. The system checks that the phone is the student's registered device.
4. GPS and BLE checks verify location and classroom proximity.
5. The student completes the required identity confirmation.
6. The backend validates the check-in and records attendance.
7. The professor sees the result in real time.

## User Roles

| Role | Planned capabilities |
| --- | --- |
| Student | View active sessions, attendance history, absence counts, ticket status, and registered-device details; request a device change. |
| Professor | Manage sessions, view live attendance, configure GPS/BLE settings, review tickets, correct attendance, and set absence limits. |
| Administrator | Approve device changes, manage accounts and roles, and review audit logs or unusual verification activity. |

## Repository Structure

```text
.github/workflows/ci.yml             Basic repository checks
backend/                            Placeholder for backend code
docs/Smart_Attendance_Proposal.pdf   Capstone project proposal
frontend/                           Placeholder for application code
CONTRIBUTING.md                     Branching and contribution workflow
README.md                          Project overview
```

## Getting Started

There is no runnable application yet. Installation, configuration, and local development instructions will be added once the technology stack is selected and the application is initialized.

For now, read the [project proposal](docs/Smart_Attendance_Proposal.pdf) and [contribution guide](CONTRIBUTING.md) before starting work.

## Contributing

Create feature, fix, or documentation branches from `sprint` and open pull requests targeting `sprint`. Stable milestones are merged from `sprint` into `main` through a pull request. Do not develop directly on `main`.

See [CONTRIBUTING.md](CONTRIBUTING.md) for branch naming, Git commands, review expectations, and commit message examples.

## CI and Deployment

The [CI workflow](.github/workflows/ci.yml) runs on pushes to `main` and `sprint`, and on pull requests targeting either branch.

The workflow checks that `README.md` and `CONTRIBUTING.md` exist and are not empty. Application tests, builds, and security checks will be added when there is application code to validate.

Continuous deployment is not configured. Deployment workflows will be defined after the application stack and hosting targets are selected.

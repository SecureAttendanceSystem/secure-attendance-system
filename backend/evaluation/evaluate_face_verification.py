"""Measure the accuracy of the Facenet512 face verification spike.

Compares every image in same_person/ and different_people/ against the
student's face embedding stored in the database. It reuses the route's own
embedding function, model, distance metric and DeepFace threshold, so the
results match what /face-spike/verify-test would return.

Writes two CSV files next to this script:
  results.csv - one row per image
  summary.csv - detection rate, FRR, FAR and accuracy
"""

import argparse
import csv
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.services.face_embedding import MODEL, compare_face_embeddings, extract_face_embedding
from app.core.config import get_settings
from app.database.connection import create_database_engine
from app.models.student_face_embedding import StudentFaceEmbedding

HERE = Path(__file__).resolve().parent
IMAGE_TYPES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
FOLDERS = {"same_person": "Yes", "different_people": "No"}

# extract_face_embedding raises this message when one image contains several faces.
# Every other failure there means no usable face was found.
MULTIPLE_FACES = "The photo must contain exactly one face."


def load_reference(student_id: UUID | None) -> tuple[UUID, list[float]]:
    engine = create_database_engine(get_settings())
    with Session(engine) as session:
        if student_id is None:
            rows = session.scalars(select(StudentFaceEmbedding)).all()
            if len(rows) != 1:
                raise SystemExit(
                    f"{len(rows)} enrolled faces found. Pass --student-id."
                )
            saved = rows[0]
        else:
            saved = session.get(StudentFaceEmbedding, student_id)
            if saved is None:
                raise SystemExit(f"No face enrolled for student {student_id}.")

        if saved.model_name != MODEL:
            raise SystemExit(
                f"Stored embedding uses {saved.model_name}, not {MODEL}."
            )
        return saved.student_id, list(saved.embedding)


def evaluate_image(path: Path, expected: str, reference: list[float]) -> dict:
    row = {
        "Image": f"{path.parent.name}/{path.name}",
        "Expected match": expected,
        "Face detected": "No",
        "Actual match": "",
        "Distance": "",
        "Threshold": "",
        "Result": "Error",
        "Error detail": "",
    }

    try:
        with path.open("rb") as file:
            embedding = extract_face_embedding(SimpleNamespace(file=file))
    except HTTPException as error:
        if error.detail == MULTIPLE_FACES:
            row["Face detected"] = "Yes"
        row["Error detail"] = error.detail
        return row

    row["Face detected"] = "Yes"

    try:
        result = compare_face_embeddings(reference, embedding)
    except Exception as error:  # Record it rather than stop the whole run.
        row["Error detail"] = f"Verification failed: {error}"
        return row

    matched = result["matched"]
    row["Actual match"] = "Yes" if matched else "No"
    row["Distance"] = f"{float(result['distance']):.6f}"
    row["Threshold"] = f"{float(result['threshold']):.6f}"

    if expected == "Yes":
        row["Result"] = "TP" if matched else "FN"
    else:
        row["Result"] = "FP" if matched else "TN"
    return row


def percent(part: int, whole: int) -> str:
    return f"{part / whole * 100:.2f}%" if whole else "N/A (no images)"


def summarise(rows: list[dict]) -> list[tuple[str, str]]:
    counts = {key: 0 for key in ("TP", "TN", "FP", "FN", "Error")}
    for row in rows:
        counts[row["Result"]] += 1

    total = len(rows)
    detected = sum(row["Face detected"] == "Yes" for row in rows)
    no_face = total - detected
    other_errors = counts["Error"] - no_face
    tp, tn, fp, fn = counts["TP"], counts["TN"], counts["FP"], counts["FN"]
    verified = tp + tn + fp + fn

    return [
        ("Total images", str(total)),
        ("Same-person images", str(sum(r["Expected match"] == "Yes" for r in rows))),
        ("Different-person images", str(sum(r["Expected match"] == "No" for r in rows))),
        ("Images with a detected face", str(detected)),
        ("Face detection failures (excluded)", str(no_face)),
        ("Other errors after detection (excluded)", str(other_errors)),
        ("Total excluded from verification metrics", str(counts["Error"])),
        ("Images used for verification metrics", str(verified)),
        ("TP", str(tp)),
        ("TN", str(tn)),
        ("FP", str(fp)),
        ("FN", str(fn)),
        ("Face Detection Rate", percent(detected, total)),
        ("False Rejection Rate (FRR)", percent(fn, tp + fn)),
        ("False Acceptance Rate (FAR)", percent(fp, fp + tn)),
        ("Overall Verification Accuracy", percent(tp + tn, verified)),
    ]


def write_csv(path: Path, header: list[str], rows: list) -> None:
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(header)
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--student-id",
        type=UUID,
        help="Enrolled student to compare against (optional if only one is enrolled).",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=HERE,
        help="Folder holding same_person/ and different_people/ (default: this folder).",
    )
    args = parser.parse_args()

    student_id, reference = load_reference(args.student_id)
    print(f"Comparing against enrolled face of student {student_id} ({MODEL})")

    rows = []
    for folder, expected in FOLDERS.items():
        directory = args.data_dir / folder
        if not directory.is_dir():
            raise SystemExit(f"Missing folder: {directory}")
        for path in sorted(directory.iterdir()):
            if path.suffix.lower() in IMAGE_TYPES:
                row = evaluate_image(path, expected, reference)
                rows.append(row)
                print(f"{row['Image']}: {row['Result']} {row['Error detail']}")

    if not rows:
        raise SystemExit("No images found.")

    summary = summarise(rows)

    results_path = args.data_dir / "results.csv"
    summary_path = args.data_dir / "summary.csv"
    write_csv(results_path, list(rows[0]), [list(r.values()) for r in rows])
    write_csv(summary_path, ["Metric", "Value"], summary)

    print()
    for name, value in summary:
        print(f"{name}: {value}")
    print(f"\nWrote {results_path} and {summary_path}")


if __name__ == "__main__":
    main()

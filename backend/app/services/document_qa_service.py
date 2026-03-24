import re
from typing import Any


SUBJECT_ROW_PATTERN = re.compile(
    r"([A-Z]{3,}\d{3,}(?:-\d{2})?)\s+(.+?)\s+(Theory|Practical)\s+(\d+)\s+([A-Z+]+)\s+(\d+)\s+(\d+)"
)


def is_subject_list_question(question: str) -> bool:
    normalized = question.lower()
    return "subject" in normalized and any(token in normalized for token in ["list", "name", "included"])


def is_marks_question(question: str) -> bool:
    normalized = question.lower()
    return "marks" in normalized or "mark" in normalized


def parse_subject_rows(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen_codes: set[str] = set()
    for chunk in chunks:
        for match in SUBJECT_ROW_PATTERN.finditer(chunk["content"]):
            code, subject_name, subject_type, credits, grade, internal_marks, external_marks = match.groups()
            if code in seen_codes:
                continue
            seen_codes.add(code)
            rows.append(
                {
                    "code": code,
                    "name": subject_name.strip(),
                    "type": subject_type,
                    "credits": int(credits),
                    "grade": grade,
                    "internal_marks": int(internal_marks),
                    "external_marks": int(external_marks),
                    "document_id": chunk["document_id"],
                    "document_name": chunk["document_name"],
                    "page_number": chunk.get("page_number"),
                }
            )
    return rows


def answer_subject_list_question(chunks: list[dict[str, Any]]) -> dict[str, Any] | None:
    rows = parse_subject_rows(chunks)
    if not rows:
        return None

    subject_names = [row["name"] for row in rows]
    answer = "Subjects included in the PDF:\n" + "\n".join(f"- {name}" for name in subject_names)
    citations = [
        {
            "source_type": "document",
            "title": rows[0]["document_name"],
            "snippet": ", ".join(subject_names[:6]),
            "document_id": rows[0]["document_id"],
            "document_name": rows[0]["document_name"],
            "page_number": rows[0]["page_number"],
            "url": None,
        }
    ]
    return {"answer": answer, "decision": "correct", "citations": citations}


def answer_marks_question(question: str, chunks: list[dict[str, Any]]) -> dict[str, Any] | None:
    rows = parse_subject_rows(chunks)
    if not rows:
        return None

    normalized_question = question.lower()
    for row in rows:
        if row["name"].lower() in normalized_question:
            total = row["internal_marks"] + row["external_marks"]
            answer = (
                f"{row['name']}: internal {row['internal_marks']}, external {row['external_marks']}, "
                f"total {total}, grade {row['grade']}."
            )
            citations = [
                {
                    "source_type": "document",
                    "title": row["document_name"],
                    "snippet": (
                        f"{row['code']} {row['name']} {row['type']} "
                        f"{row['internal_marks']} {row['external_marks']}"
                    ),
                    "document_id": row["document_id"],
                    "document_name": row["document_name"],
                    "page_number": row["page_number"],
                    "url": None,
                }
            ]
            return {"answer": answer, "decision": "correct", "citations": citations}
    return None


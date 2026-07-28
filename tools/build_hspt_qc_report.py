#!/usr/bin/env python3

from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"

sys.path.insert(0, str(TOOLS))

import import_catholic_exams as ice


REPORT_PATH = (
    ROOT
    / "imports"
    / "reports"
    / "hspt_complete_qc_report.md"
)


def heading(text: str, level: int = 1) -> str:
    return f'{"#" * level} {text}'


def fenced(value: str) -> str:
    value = str(value or "").strip()

    return f"```text\n{value}\n```"


def exact_duplicate_groups(question):
    groups = {}

    for letter in "ABCD":
        value = question.choices.get(letter, "")
        normalized = ice.normalize_option_text(value)

        groups.setdefault(normalized, []).append(letter)

    return [
        letters
        for normalized, letters in groups.items()
        if normalized and len(letters) > 1
    ]


def answer_distribution(questions):
    counts = Counter(
        question.correct
        for question in questions
        if question.correct in "ABCD"
    )

    return ", ".join(
        f"{letter}: {counts.get(letter, 0)}"
        for letter in "ABCD"
    )


def maximum_run(questions):
    maximum = 0
    current = 0
    previous = None
    start_index = 0
    best_start = 0
    best_letter = ""

    valid_questions = [
        question
        for question in questions
        if question.correct in "ABCD"
    ]

    for index, question in enumerate(valid_questions):
        letter = question.correct

        if letter == previous:
            current += 1
        else:
            current = 1
            start_index = index
            previous = letter

        if current > maximum:
            maximum = current
            best_start = start_index
            best_letter = letter

    if not valid_questions or maximum == 0:
        return "None"

    first = valid_questions[best_start].qid
    last = valid_questions[best_start + maximum - 1].qid

    return (
        f"{maximum} consecutive {best_letter} answers, "
        f"from {first} to {last}"
    )


def cycle_details(questions):
    letters = [
        question.correct
        for question in questions
        if question.correct in "ABCD"
    ]

    ids = [
        question.qid
        for question in questions
        if question.correct in "ABCD"
    ]

    patterns = {
        "ABCDABCDABCDABCD",
        "BCDABCDABCDABCDA",
        "CDABCDABCDABCDAB",
        "DABCDABCDABCDABC",
    }

    found = []

    for start in range(max(0, len(letters) - 15)):
        block = "".join(letters[start:start + 16])

        if block in patterns:
            found.append(
                (
                    ids[start],
                    ids[start + 15],
                    block,
                )
            )

    return found


def collect_exam(exam_no: int):
    discovered = ice.discover_sources("hspt")
    parts = discovered.get(exam_no)

    if not parts:
        return None

    questions = []
    stimuli = {}
    parse_warnings = []

    for part in "abcd":
        path = parts.get(part)

        if path is None:
            continue

        part_questions, part_stimuli, warnings = ice.parse_part(path)

        questions.extend(part_questions)
        stimuli.update(part_stimuli)

        parse_warnings.extend(
            f"{path.name}: {warning}"
            for warning in warnings
        )

    override_notes = ice.apply_overrides(questions)

    errors, warnings = ice.validate_exam(
        "hspt",
        exam_no,
        questions,
        stimuli,
        parts,
    )

    warnings = parse_warnings + override_notes + warnings

    return {
        "parts": parts,
        "questions": questions,
        "stimuli": stimuli,
        "errors": errors,
        "warnings": warnings,
    }


def messages_for_qid(messages, qid):
    return [
        message
        for message in messages
        if qid in message
    ]


lines = []

lines.append(heading("HSPT Exams 01–05 — Complete Quality-Control Report"))
lines.append("")
lines.append(
    "This report was generated before final JSON import. "
    "No HSPT JSON file is currently active in the platform data folder."
)
lines.append("")

grand_errors = 0
grand_warnings = 0

for exam_no in range(1, 6):
    result = collect_exam(exam_no)

    lines.append(heading(f"HSPT Exam {exam_no:02d}", 2))
    lines.append("")

    if result is None:
        lines.append("**SOURCE FILES NOT FOUND**")
        lines.append("")
        continue

    questions = result["questions"]
    stimuli = result["stimuli"]
    errors = result["errors"]
    warnings = result["warnings"]

    grand_errors += len(errors)
    grand_warnings += len(warnings)

    lines.append(f"- Questions parsed: **{len(questions)}**")
    lines.append(f"- Stimuli parsed: **{len(stimuli)}**")
    lines.append(f"- Blocking errors: **{len(errors)}**")
    lines.append(f"- Warnings: **{len(warnings)}**")
    lines.append(
        f"- Answer distribution: **{answer_distribution(questions)}**"
    )
    lines.append(f"- Maximum answer run: **{maximum_run(questions)}**")
    lines.append("")

    all_messages = errors + warnings

    item_ids = []

    for message in all_messages:
        match = re.search(
            r"HSPT-[VQRML]\d+-\d{3}",
            message,
        )

        if match:
            qid = match.group(0)

            if qid not in item_ids:
                item_ids.append(qid)

    non_item_errors = [
        message
        for message in errors
        if not re.search(r"HSPT-[VQRML]\d+-\d{3}", message)
    ]

    non_item_warnings = [
        message
        for message in warnings
        if not re.search(r"HSPT-[VQRML]\d+-\d{3}", message)
    ]

    if non_item_errors:
        lines.append(heading("General blocking errors", 3))
        lines.append("")

        for message in non_item_errors:
            lines.append(f"- {message}")

        lines.append("")

    if non_item_warnings:
        lines.append(heading("General warnings", 3))
        lines.append("")

        for message in non_item_warnings:
            lines.append(f"- {message}")

        lines.append("")

    cycles = cycle_details(questions)

    if cycles:
        lines.append(heading("Detected ABCD cycles", 3))
        lines.append("")

        for first, last, sequence in cycles:
            lines.append(
                f"- From `{first}` to `{last}`: `{sequence}`"
            )

        lines.append("")

    by_id = {
        question.qid: question
        for question in questions
    }

    if item_ids:
        lines.append(heading("Flagged questions", 3))
        lines.append("")

    for qid in item_ids:
        question = by_id.get(qid)

        lines.append(heading(qid, 4))
        lines.append("")

        related = messages_for_qid(all_messages, qid)

        lines.append("**Detected issues**")
        lines.append("")

        for message in related:
            lines.append(f"- {message}")

        lines.append("")

        if question is None:
            lines.append(
                "**Question not parsed from the source files.**"
            )
            lines.append("")
            continue

        lines.append(f"- Section: `{question.section}`")
        lines.append(f"- Category: `{question.category}`")
        lines.append(f"- Skill: `{question.skill}`")
        lines.append(f"- Stimulus ID: `{question.stimulus_id}`")
        lines.append("")

        stimulus_id = question.stimulus_id.strip()

        if (
            stimulus_id
            and stimulus_id.lower() != "none"
            and stimulus_id in stimuli
        ):
            stimulus = stimuli[stimulus_id]

            lines.append("**Stimulus type**")
            lines.append("")
            lines.append(fenced(stimulus.stimulus_type))
            lines.append("")

            if stimulus.title:
                lines.append("**Stimulus title**")
                lines.append("")
                lines.append(fenced(stimulus.title))
                lines.append("")

            lines.append("**Stimulus text**")
            lines.append("")
            lines.append(fenced(stimulus.text))
            lines.append("")

        lines.append("**Prompt**")
        lines.append("")
        lines.append(fenced(question.prompt))
        lines.append("")

        lines.append("**Choices**")
        lines.append("")

        for letter in "ABCD":
            value = question.choices.get(letter, "")
            lines.append(f"- **{letter})** {value}")

        lines.append("")
        lines.append(
            f"**Answer-key letter:** `{question.correct or 'MISSING'}`"
        )
        lines.append("")

        actual_option = (
            question.choices.get(question.correct, "")
            if question.correct in "ABCD"
            else ""
        )

        lines.append("**Answer-key text**")
        lines.append("")
        lines.append(
            fenced(
                question.correct_answer
                or "MISSING"
            )
        )
        lines.append("")

        lines.append("**Actual text of the keyed option**")
        lines.append("")
        lines.append(
            fenced(
                actual_option
                or "MISSING"
            )
        )
        lines.append("")

        duplicates = exact_duplicate_groups(question)

        if duplicates:
            lines.append("**Normalized duplicate-option groups**")
            lines.append("")

            for group in duplicates:
                letters = ", ".join(group)
                lines.append(f"- Options: `{letters}`")

            lines.append("")

        lines.append("**Explanation**")
        lines.append("")
        lines.append(
            fenced(
                question.explanation
                or "MISSING"
            )
        )
        lines.append("")

        lines.append("---")
        lines.append("")

lines.append(heading("Overall summary", 2))
lines.append("")
lines.append(f"- Total blocking errors: **{grand_errors}**")
lines.append(f"- Total warnings: **{grand_warnings}**")
lines.append("")
lines.append(
    "No final HSPT import should be performed until every real issue "
    "listed in this report has been reviewed and corrected."
)
lines.append("")

REPORT_PATH.write_text(
    "\n".join(lines),
    encoding="utf-8",
)

print(REPORT_PATH)

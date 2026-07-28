#!/usr/bin/env python3

from __future__ import annotations

import re
import sys
from collections import defaultdict
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import import_catholic_exams as ice


OUTPUT = (
    ROOT
    / "imports"
    / "reports"
    / "hspt_cross_exam_duplicates.md"
)


def normalize(value: str) -> str:
    value = ice.clean_text(value)

    value = re.sub(
        r"^(?:Select the best answer\.|Choose the best response\.)\s*",
        "",
        value,
        flags=re.IGNORECASE,
    )

    value = re.sub(
        r"\nSECTION\s+\d+\s*[-–—]\s*[A-Z &]+\s*$",
        "",
        value,
        flags=re.IGNORECASE,
    )

    value = re.sub(r"\s+", " ", value).strip().casefold()
    return value


def question_signature(question):
    return (
        normalize(question.section),
        normalize(question.prompt),
        tuple(
            normalize(question.choices.get(letter, ""))
            for letter in "ABCD"
        ),
    )


def stimulus_signature(stimulus):
    return (
        normalize(stimulus.title),
        normalize(stimulus.text),
    )


discovered = ice.discover_sources("hspt")

questions_by_exam = {}
stimuli_by_exam = {}

for exam_no in range(1, 6):
    parts = discovered.get(exam_no)

    if not parts:
        raise SystemExit(
            f"ERRORE: file sorgente dell’Exam {exam_no:02d} non trovati."
        )

    missing_parts = sorted(set("abcd") - set(parts))

    if missing_parts:
        raise SystemExit(
            f"ERRORE: Exam {exam_no:02d}, parti mancanti: "
            f"{', '.join(missing_parts).upper()}"
        )

    questions = []
    stimuli = {}

    for part in "abcd":
        part_questions, part_stimuli, warnings = ice.parse_part(parts[part])

        if warnings:
            print(
                f"Exam {exam_no:02d} Part {part.upper()}: "
                f"{len(warnings)} parser warning"
            )

        questions.extend(part_questions)
        stimuli.update(part_stimuli)

    if len(questions) != 298:
        raise SystemExit(
            f"ERRORE: Exam {exam_no:02d} contiene "
            f"{len(questions)} domande invece di 298."
        )

    questions_by_exam[exam_no] = questions
    stimuli_by_exam[exam_no] = stimuli


question_groups = defaultdict(list)

for exam_no, questions in questions_by_exam.items():
    for question in questions:
        question_groups[question_signature(question)].append(
            (exam_no, question.qid)
        )


cross_exam_question_groups = []

for entries in question_groups.values():
    exams = {exam_no for exam_no, _ in entries}

    if len(exams) > 1:
        cross_exam_question_groups.append(entries)


stimulus_groups = defaultdict(list)

for exam_no, stimuli in stimuli_by_exam.items():
    for stimulus_id, stimulus in stimuli.items():
        stimulus_groups[stimulus_signature(stimulus)].append(
            (
                exam_no,
                stimulus_id,
                stimulus.title,
            )
        )


cross_exam_stimulus_groups = []

for entries in stimulus_groups.values():
    exams = {exam_no for exam_no, _, _ in entries}

    if len(exams) > 1:
        cross_exam_stimulus_groups.append(entries)


pair_question_counts = defaultdict(int)

for entries in cross_exam_question_groups:
    exams = sorted({exam_no for exam_no, _ in entries})

    for first, second in combinations(exams, 2):
        pair_question_counts[(first, second)] += 1


pair_stimulus_counts = defaultdict(int)

for entries in cross_exam_stimulus_groups:
    exams = sorted({exam_no for exam_no, _, _ in entries})

    for first, second in combinations(exams, 2):
        pair_stimulus_counts[(first, second)] += 1


exact_duplicate_choices = []

for exam_no, questions in questions_by_exam.items():
    for question in questions:
        groups = defaultdict(list)

        for letter in "ABCD":
            value = re.sub(
                r"\s+",
                " ",
                question.choices.get(letter, "").strip(),
            )

            groups[value].append(letter)

        duplicates = [
            letters
            for value, letters in groups.items()
            if value and len(letters) > 1
        ]

        if duplicates:
            exact_duplicate_choices.append(
                (
                    exam_no,
                    question.qid,
                    duplicates,
                    question.prompt,
                )
            )


lines = [
    "# HSPT Exams 01–05 — Cross-Exam Duplication Audit",
    "",
    "No JSON files were created by this audit.",
    "",
    "## Source totals",
    "",
]

for exam_no in range(1, 6):
    lines.append(
        f"- Exam {exam_no:02d}: "
        f"{len(questions_by_exam[exam_no])} questions, "
        f"{len(stimuli_by_exam[exam_no])} stimuli"
    )

lines.extend(
    [
        "",
        "## Pairwise exact duplicate-question counts",
        "",
    ]
)

for first in range(1, 6):
    for second in range(first + 1, 6):
        count = pair_question_counts.get((first, second), 0)

        lines.append(
            f"- Exam {first:02d} vs Exam {second:02d}: "
            f"**{count} exact duplicated questions**"
        )

lines.extend(
    [
        "",
        "## Pairwise exact duplicate-stimulus counts",
        "",
    ]
)

for first in range(1, 6):
    for second in range(first + 1, 6):
        count = pair_stimulus_counts.get((first, second), 0)

        lines.append(
            f"- Exam {first:02d} vs Exam {second:02d}: "
            f"**{count} exact duplicated stimuli**"
        )

lines.extend(
    [
        "",
        "## Exact duplicated questions across exams",
        "",
    ]
)

if not cross_exam_question_groups:
    lines.append("- None detected.")
else:
    for index, entries in enumerate(
        sorted(
            cross_exam_question_groups,
            key=lambda group: group[0][1],
        ),
        start=1,
    ):
        ids = ", ".join(
            f"`{qid}`"
            for _, qid in entries
        )

        lines.append(f"{index}. {ids}")

lines.extend(
    [
        "",
        "## Exact duplicated stimuli across exams",
        "",
    ]
)

if not cross_exam_stimulus_groups:
    lines.append("- None detected.")
else:
    for index, entries in enumerate(
        cross_exam_stimulus_groups,
        start=1,
    ):
        values = ", ".join(
            f"`{stimulus_id}` ({title or 'Untitled'})"
            for _, stimulus_id, title in entries
        )

        lines.append(f"{index}. {values}")

lines.extend(
    [
        "",
        "## Questions containing genuinely identical answer options",
        "",
    ]
)

if not exact_duplicate_choices:
    lines.append("- None detected.")
else:
    for exam_no, qid, groups, prompt in exact_duplicate_choices:
        duplicate_letters = "; ".join(
            ", ".join(letters)
            for letters in groups
        )

        lines.append(
            f"- `{qid}` — duplicated options: "
            f"**{duplicate_letters}** — {prompt}"
        )

lines.extend(
    [
        "",
        "## Overall totals",
        "",
        (
            "- Cross-exam exact duplicate-question groups: "
            f"**{len(cross_exam_question_groups)}**"
        ),
        (
            "- Cross-exam exact duplicate-stimulus groups: "
            f"**{len(cross_exam_stimulus_groups)}**"
        ),
        (
            "- Questions with genuinely identical options: "
            f"**{len(exact_duplicate_choices)}**"
        ),
        "",
        (
            "Final import must remain blocked until the duplicated items, "
            "incorrect keys, missing explanations, and parser contamination "
            "have all been corrected."
        ),
        "",
    ]
)

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text("\n".join(lines), encoding="utf-8")

print()
print("AUDIT COMPLETATO")
print("Domande analizzate:", sum(map(len, questions_by_exam.values())))
print("Stimuli analizzati:", sum(map(len, stimuli_by_exam.values())))
print(
    "Gruppi di domande duplicate tra esami:",
    len(cross_exam_question_groups),
)
print(
    "Gruppi di stimuli duplicati tra esami:",
    len(cross_exam_stimulus_groups),
)
print(
    "Domande con opzioni realmente identiche:",
    len(exact_duplicate_choices),
)
print("Report:", OUTPUT)

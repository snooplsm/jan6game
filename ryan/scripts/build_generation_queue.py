#!/usr/bin/env python3
"""Create a randomized, mixed generation queue for synthetic people."""

from __future__ import annotations

import argparse
import csv
import random
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PEOPLE_DIR = ROOT / "generated_people_corrected"


def load_manifest(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def mix_key(record: dict[str, str]) -> str:
    target = record["demographic_target"]
    if target != "white":
        return f"{target} | {record.get('habitus_group', '')}"
    return (
        f"{record['background']} | {record.get('skin_tone', '')} | "
        f"{record.get('habitus_group', '')}"
    )


def mixed_shuffle(records: list[dict[str, str]], seed: int) -> list[dict[str, str]]:
    rng = random.Random(seed)
    remaining = records[:]
    rng.shuffle(remaining)
    ordered: list[dict[str, str]] = []

    while remaining:
        if not ordered:
            ordered.append(remaining.pop(0))
            continue

        last_key = mix_key(ordered[-1])
        viable_indexes = [
            idx for idx, record in enumerate(remaining) if mix_key(record) != last_key
        ]
        if viable_indexes:
            idx = rng.choice(viable_indexes)
        else:
            idx = 0
        ordered.append(remaining.pop(idx))

    return ordered


def stratified_queue(records: list[dict[str, str]], seed: int) -> list[dict[str, str]]:
    rng = random.Random(seed)
    majority = [record for record in records if record["demographic_target"] == "white"]
    minority = [record for record in records if record["demographic_target"] != "white"]

    majority = mixed_shuffle(majority, seed=seed + 1)
    rng.shuffle(minority)
    if not minority:
        return majority

    queue: list[dict[str, str] | None] = [None] * len(records)
    slots = [
        round((idx + 0.5) * len(records) / len(minority))
        for idx in range(len(minority))
    ]
    for slot, record in zip(slots, minority, strict=True):
        queue[min(max(slot, 0), len(records) - 1)] = record

    majority_iter = iter(majority)
    return [
        record if record is not None else next(majority_iter)
        for record in queue
    ]


def image_status(record: dict[str, str]) -> dict[str, str]:
    images_dir = PEOPLE_DIR / "images"
    person_id = record["person_id"]
    return {
        "front_done": str((images_dir / f"{person_id}_front.png").exists()).lower(),
        "side_done": str((images_dir / f"{person_id}_side.png").exists()).lower(),
        "back_done": str((images_dir / f"{person_id}_back.png").exists()).lower(),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", default=7404, type=int)
    args = parser.parse_args()

    records = load_manifest(PEOPLE_DIR / "manifest.csv")
    ordered = stratified_queue(records, seed=args.seed)
    out_path = PEOPLE_DIR / "generation_queue.csv"

    fieldnames = [
        "queue_index",
        "person_id",
        "sex",
        "age",
        "age_bucket",
        "demographic_target",
        "background",
        "skin_tone",
        "weathering_note",
        "distinguishing_marks_note",
        "hard_living_note",
        "habitus_note",
        "habitus_group",
        "aesthetic_note",
        "attractiveness_note",
        "mix_key",
        "front_done",
        "side_done",
        "back_done",
    ]
    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for idx, record in enumerate(ordered, start=1):
            writer.writerow(
                {
                    "queue_index": idx,
                    "person_id": record["person_id"],
                    "sex": record["sex"],
                    "age": record["age"],
                    "age_bucket": record["age_bucket"],
                    "demographic_target": record["demographic_target"],
                    "background": record["background"],
                    "skin_tone": record.get("skin_tone", ""),
                    "weathering_note": record.get("weathering_note", ""),
                    "distinguishing_marks_note": record.get("distinguishing_marks_note", ""),
                    "hard_living_note": record.get("hard_living_note", ""),
                    "habitus_note": record.get("habitus_note", ""),
                    "habitus_group": record.get("habitus_group", ""),
                    "aesthetic_note": record.get("aesthetic_note", ""),
                    "attractiveness_note": record.get("attractiveness_note", ""),
                    "mix_key": mix_key(record),
                    **image_status(record),
                }
            )

    next_pending_full_set = next(
        (
            record
            for record in ordered
            if not all(value == "true" for value in image_status(record).values())
        ),
        None,
    )
    next_pending_front = next(
        (
            record
            for record in ordered
            if image_status(record)["front_done"] != "true"
        ),
        None,
    )
    print(f"Wrote {out_path} with seed {args.seed}")
    if next_pending_front:
        print(
            "Next pending front: "
            f"{next_pending_front['person_id']} "
            f"({next_pending_front['demographic_target']}, {next_pending_front['background']})"
        )
    if next_pending_full_set:
        print(
            "Next pending full set: "
            f"{next_pending_full_set['person_id']} "
            f"({next_pending_full_set['demographic_target']}, {next_pending_full_set['background']})"
        )


if __name__ == "__main__":
    main()

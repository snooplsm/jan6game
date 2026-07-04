#!/usr/bin/env python3
"""Build prompts for a 100-person synthetic bald head portrait set."""

from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "generated_people_corrected"


SOURCE_DISTRIBUTION = {
    "white": {"count": 659, "percentage": 92.0},
    "hispanic_latino": {"count": 39, "percentage": 5.4},
    "black": {"count": 10, "percentage": 1.4},
    "asian": {"count": 7, "percentage": 1.0},
    "native_american": {"count": 1, "percentage": 0.1},
}

# Closest whole-person 100-subject sample by largest remainder:
# 92 White, 6 Hispanic/Latino, 1 Black, 1 Asian, 0 Native American.
SCALED_100_COUNTS = {
    "white": 92,
    "hispanic_latino": 6,
    "black": 1,
    "asian": 1,
    "native_american": 0,
}

DEMOGRAPHIC_SEQUENCE = (
    ["black"] * SCALED_100_COUNTS["black"]
    + ["asian"] * SCALED_100_COUNTS["asian"]
    + ["hispanic_latino"] * SCALED_100_COUNTS["hispanic_latino"]
    + ["native_american"] * SCALED_100_COUNTS["native_american"]
    + ["white"] * SCALED_100_COUNTS["white"]
)

WHITE_BACKGROUNDS = [
    "Northern European ancestry",
    "Southern European ancestry",
    "Eastern European ancestry",
    "Western European ancestry",
    "Balkan European ancestry",
    "Northwestern European ancestry",
    "Central European ancestry",
    "Ashkenazi Jewish European ancestry",
    "Irish and British Isles ancestry",
    "Scandinavian ancestry",
    "Baltic European ancestry",
    "mixed Northern and Southern European ancestry",
    "Central Mediterranean ancestry",
    "Caucasus-region ancestry with fair-to-olive complexion",
]

WHITE_COMPLEXIONS = [
    "very fair porcelain skin, Fitzpatrick type I, cool pink undertone, UV freckling, visible redness on nose and cheeks",
    "fair ivory skin, Fitzpatrick type I-II, neutral-pink undertone, sun-mottled cheeks, slight capillary redness",
    "fair beige skin, Fitzpatrick type II, neutral undertone, uneven light tan, sun spots on forehead and temples",
    "light olive skin, Fitzpatrick type III, muted green-gold undertone, outdoor tan, mild hyperpigmentation",
    "warm beige skin, Fitzpatrick type III, golden undertone, moderate farmer's tan, sun-exposed forehead and cheeks",
    "medium olive skin, Fitzpatrick type III-IV, olive undertone, noticeable tan, uneven pigmentation from sun exposure",
    "ruddy fair skin, Fitzpatrick type II, pink-red undertone, weathered sun exposure, broken capillaries",
    "tan white skin, Fitzpatrick type IV, golden-brown summer tan, sun-damaged forehead and cheekbones",
    "pale freckled skin, Fitzpatrick type I, cool undertone, dense natural freckles and solar lentigines",
    "light neutral skin, Fitzpatrick type II-III, blotchy sun damage, coarse pores, uneven weathered texture",
]

COMPLETED_COMPLEXION_OVERRIDES = {
    27: "ruddy fair skin, Fitzpatrick type II, pink-red undertone, weathered sun exposure",
    30: "light olive skin, Fitzpatrick type III, muted green-gold undertone, mild tan",
    83: "ruddy fair skin, Fitzpatrick type II, pink-red undertone, weathered sun exposure",
}

BLACK_BACKGROUNDS = [
    "West African diaspora ancestry",
    "East African ancestry",
    "Central African ancestry",
    "Southern African ancestry",
    "Caribbean Black ancestry",
]

LATINO_BACKGROUNDS = [
    "Mexican ancestry",
    "Central American ancestry",
    "Caribbean Latino ancestry",
    "Andean Latino ancestry",
    "Southern Cone Latino ancestry",
]

ASIAN_BACKGROUNDS = [
    "East Asian ancestry",
    "South Asian ancestry",
    "Southeast Asian ancestry",
    "Central Asian ancestry",
    "mixed East Asian and Southeast Asian ancestry",
]

NATIVE_AMERICAN_BACKGROUNDS = [
    "Native American ancestry",
]

SKULLS = [
    "long narrow skull with a high forehead",
    "broad skull with a low compact forehead",
    "oval skull with balanced forehead height",
    "rounder skull with a soft jaw transition",
    "angular skull with prominent cheekbones",
    "tall skull with a narrow chin",
    "wide skull with a squared jaw",
    "slightly asymmetrical skull with uneven cheek prominence",
]

NOSES = [
    "straight medium-width nose",
    "wide low-bridge nose",
    "high narrow bridge and rounded tip",
    "slightly crooked nose",
    "short nose with broad nostrils",
    "long nose with a defined bridge",
    "soft bulbous tip and medium nostrils",
    "narrow bridge with a downturned tip",
]

MOUTHS = [
    "thin lips and a long philtrum",
    "full lips and a short philtrum",
    "medium lips with a defined cupid bow",
    "narrow mouth with uneven lip corners",
    "wide mouth with balanced lip thickness",
    "small mouth with a fuller lower lip",
]

SKIN_DETAILS = [
    "prominent pores",
    "mild under-eye darkness",
    "small mole on one cheek",
    "faint acne scarring",
    "subtle rosacea",
    "weathered sun texture",
    "mottled sun discoloration",
    "soft forehead wrinkles",
    "crow's feet",
    "under-eye bags",
    "cleft chin",
    "slight facial asymmetry",
    "solar lentigines",
    "broken capillaries around the nose",
    "rough sun-exposed cheek texture",
]

IRISES = ["brown", "dark brown", "hazel", "green", "gray", "blue", "amber"]


BASE_PROMPT = """Use case: photorealistic-natural
Asset type: synthetic fictional head portrait for a project image set
Primary request: Generate portrait ID {person_id}, a unique fictional adult human, front-facing biometric-style studio portrait.

Attributes for this individual: {sex}, age {age}, {background}, {skin_tone}; {skull}; {nose}; {mouth}; {eyes}; {face_fat}; {skin_detail}; {aesthetic_note}; {attractiveness}.

Complexion target: {complexion_note}

Weathering target: {weathering_note}

Body-habitus target visible in the head and neck: {habitus_note}

Aesthetic target: strongly prefer plain, rugged, unpolished, below-average conventional attractiveness. Keep the person realistic and anatomically normal, but avoid beauty-model facial symmetry, perfect skin, glamorous proportions, chiseled hero jaws, polished skin, or repeated handsome/pretty archetypes.

Composition: Head centered perfectly, looking directly into camera, neutral expression, mouth closed, eyes looking directly at viewer. Entire bald head and full neck visible from just above shoulders to top of skull. Plain neutral gray/off-white background, no texture.

Realism: Completely realistic human anatomy with one nose, two eyes, one mouth, anatomically correct neck and posture. Ultra-photorealistic high-resolution studio photography, realistic skin pores, fine skin detail, subtle subsurface scattering, natural skin texture, visible UV exposure, uneven pigmentation, and non-cosmetic skin imperfections.

Strict appearance rules: completely bald, no facial hair, no eyebrows, no visible eyelashes if possible, no body hair visible, no glasses, no hats, no helmets, no hoods, no jewelry, no piercings, no hearing aids, no masks, no headphones, no tattoos, no makeup, no cosmetics, no prosthetics, no accessories. No visible clothing except optional seamless skin-tight neutral material around shoulders.

Lighting: perfectly soft, flat, shadowless, evenly diffused studio lighting. No harsh shadows, rim lighting, reflections, specular highlights, or dramatic light.

Identity: entirely fictional. No resemblance to any real person, celebrity, politician, athlete, influencer, or public figure. Avoid repeated facial archetypes and stylization."""


def background_for(category: str, index: int) -> str:
    if category == "black":
        return BLACK_BACKGROUNDS[index % len(BLACK_BACKGROUNDS)]
    if category == "hispanic_latino":
        return LATINO_BACKGROUNDS[index % len(LATINO_BACKGROUNDS)]
    if category == "asian":
        return ASIAN_BACKGROUNDS[index % len(ASIAN_BACKGROUNDS)]
    if category == "native_american":
        return NATIVE_AMERICAN_BACKGROUNDS[index % len(NATIVE_AMERICAN_BACKGROUNDS)]
    return WHITE_BACKGROUNDS[index % len(WHITE_BACKGROUNDS)]


def age_for(i: int) -> int:
    if i <= 20:
        return 18 + ((i * 3) % 12)
    if i <= 60:
        return 30 + ((i * 5) % 16)
    return 46 + ((i * 7) % 35)


def sex_for(i: int) -> str:
    return "female" if i > 80 else "male"


def skin_tone_for(category: str, i: int) -> str:
    if category == "black":
        tones = ["deep brown skin", "dark brown skin", "rich umber skin", "medium-dark brown skin"]
    elif category == "hispanic_latino":
        tones = ["light olive skin", "medium tan skin", "warm brown skin", "golden beige skin"]
    elif category == "asian":
        tones = ["fair warm skin", "light golden skin", "medium olive skin", "medium brown skin"]
    elif category == "native_american":
        tones = ["medium tan skin", "warm brown skin"]
    else:
        tones = WHITE_COMPLEXIONS
    return COMPLETED_COMPLEXION_OVERRIDES.get(i, tones[i % len(tones)])


def complexion_note_for(category: str, skin_tone: str) -> str:
    if category == "white":
        return (
            f"Render this exact White complexion visibly: {skin_tone}. "
            "Do not collapse this subject into generic light beige skin; preserve the specified tan level, undertone, redness, freckles, or sun exposure."
        )
    return f"Render this exact complexion visibly: {skin_tone}."


def weathering_note_for(age: int, i: int) -> str:
    if age < 30:
        variants = [
            "mild but visible outdoor sun exposure: uneven tan on forehead, nose, and cheekbones, small freckles or dark spots, realistic pores; keep the person their stated young adult age",
            "noticeable sun exposure for a young adult: faint forehead lines, slight redness, a few sun freckles, dry skin texture on nose and cheeks; do not make them look middle-aged",
            "weathered young adult skin from regular outdoor work: mild tan lines, uneven cheek coloration, pores, and subtle under-eye darkness while preserving age-appropriate firmness",
        ]
    elif age <= 45:
        variants = [
            "moderate sun damage: uneven pigmentation, early crow's feet, faint forehead lines, visible pores, and a slightly leathery nose-and-cheek texture",
            "outdoor-working adult skin: sun spots on temples and cheekbones, broken capillaries around the nose, dry patches, and moderate texture variation",
            "clear UV exposure: mottled tan, mild hyperpigmentation, rough cheek texture, early skin laxity, and realistic fine lines around eyes and mouth",
        ]
    else:
        variants = [
            "pronounced age-appropriate sun damage: solar lentigines, mottled pigmentation, deeper crow's feet, forehead wrinkles, coarse pores, and weathered neck texture",
            "heavily weathered older skin: uneven sun spots, broken capillaries, leathery cheek and forehead texture, under-eye bags, and visible skin laxity",
            "long-term UV exposure: blotchy pigmentation, age spots on temples and cheeks, rough dry texture, deep laugh lines, and sun-weathered scalp and neck",
        ]
    return variants[i % len(variants)]


def face_fat_for(i: int) -> str:
    # Bias toward visibly skinny or heavy-set faces, with fewer average records.
    values = [8, 10, 12, 14, 18, 24, 30, 34, 38, 40, 42, 45]
    return f"face fat visually around {values[i % len(values)]}% with natural human fullness"


def habitus_note_for(i: int) -> str:
    variants = [
        "very lean, skinny face with hollow cheeks, visible cheekbone planes, narrow neck, and minimal under-chin fullness",
        "lean face with defined jawline, thin cheeks, taut neck, and little submental fat",
        "slender build visible in the face: narrow cheeks, sharper chin, thin neck, and minimal facial padding",
        "average-light build: modest facial fullness, clear jaw contour, and medium-thin neck",
        "average build: balanced cheek fullness, normal jaw contour, and medium neck thickness",
        "solid build: fuller cheeks, softened jaw corners, thicker neck, and subtle under-chin fullness",
        "heavy-set build: broad full face, soft jawline, thick neck, and visible under-chin fullness",
        "very heavy-set build: round cheeks, reduced jaw definition, broad neck, and pronounced submental fullness",
        "large heavy face with soft cheek pads, wide lower face, thick neck, and natural folds at the base of the neck",
        "stocky build: dense neck, broad lower face, softened chin transition, and moderate facial fat",
        "obese facial build: very full cheeks, heavy lower face, thick neck, and strong under-chin fullness while remaining anatomically realistic",
        "gaunt-skinny build: hollow cheeks, narrow temples, prominent facial bones, thin neck, and dry weathered texture",
    ]
    return variants[i % len(variants)]


def habitus_group_for(habitus_note: str) -> str:
    if any(word in habitus_note for word in ["lean", "skinny", "slender", "gaunt"]):
        return "lean"
    if any(word in habitus_note for word in ["heavy", "stocky", "obese", "large"]):
        return "heavy"
    return "mid"


UNPOLISHED_FEATURES = [
    "uneven eye height, tired under-eye area, and slightly lopsided mouth corners",
    "broad blunt nose, small narrow mouth, and softened lower-face definition",
    "receded chin, heavy upper eyelids, and coarse visible pores",
    "long philtrum, thin uneven lips, and asymmetrical cheek fullness",
    "puffy under-eyes, weak jaw transition, and mottled complexion",
    "bulbous nose tip, broad nostrils, and rough sun-textured cheeks",
    "narrow skull, prominent ears, and shallow cheeks",
    "low compact forehead, crowded facial proportions, and uneven smile-line depth",
    "soft sagging lower face, under-chin fullness, and flattened cheek contours",
    "gaunt temples, hollow cheeks, and dry weathered scalp skin",
]


def aesthetic_note_for(i: int) -> str:
    return UNPOLISHED_FEATURES[(i * 7) % len(UNPOLISHED_FEATURES)]


def attractiveness_for(i: int) -> str:
    labels = [
        "noticeably plain and not photogenic",
        "below-average conventional attractiveness while remaining realistic",
        "rugged, tired, asymmetrical everyday face",
        "unpolished ordinary face with imperfect proportions",
        "distinctive, awkward facial balance",
        "average-at-best attractiveness with no model-like symmetry",
        "weathered and rough-looking, not conventionally attractive",
        "plain face with uneven features and tired skin",
        "homely but realistic adult face",
        "ordinary face with asymmetry, large pores, and uneven complexion",
    ]
    return labels[i % len(labels)]


def record_for(i: int) -> dict[str, str | int]:
    category = DEMOGRAPHIC_SEQUENCE[i - 1]
    age = age_for(i)
    sex = sex_for(i)
    person_id = f"person_{i:03d}"
    skin_tone = skin_tone_for(category, i)
    weathering_note = weathering_note_for(age, i)
    habitus_note = habitus_note_for(i)
    habitus_group = habitus_group_for(habitus_note)
    aesthetic_note = aesthetic_note_for(i)
    attractiveness_note = attractiveness_for(i)
    prompt = BASE_PROMPT.format(
        person_id=person_id,
        sex=sex,
        age=age,
        background=background_for(category, i),
        skin_tone=skin_tone,
        complexion_note=complexion_note_for(category, skin_tone),
        weathering_note=weathering_note,
        habitus_note=habitus_note,
        skull=SKULLS[i % len(SKULLS)],
        nose=NOSES[(i * 2) % len(NOSES)],
        mouth=MOUTHS[(i * 3) % len(MOUTHS)],
        eyes=f"{IRISES[(i * 5) % len(IRISES)]} irises with varied eyelid shape and natural sclera",
        face_fat=face_fat_for(i),
        skin_detail=SKIN_DETAILS[(i * 7) % len(SKIN_DETAILS)],
        aesthetic_note=aesthetic_note,
        attractiveness=attractiveness_note,
    )
    if i <= 20 and sex != "male":
        raise AssertionError("The first 20 records must be young men.")
    return {
        "person_id": person_id,
        "sex": sex,
        "age": age,
        "age_bucket": "18-29 young men" if i <= 20 else "30-45" if i <= 60 else "46-80",
        "demographic_target": category,
        "background": background_for(category, i),
        "skin_tone": skin_tone,
        "weathering_note": weathering_note,
        "habitus_note": habitus_note,
        "habitus_group": habitus_group,
        "aesthetic_note": aesthetic_note,
        "attractiveness_note": attractiveness_note,
        "prompt": prompt,
        "front_image_path": f"images/{person_id}_front.png",
        "side_image_path": f"images/{person_id}_side.png",
        "back_image_path": f"images/{person_id}_back.png",
    }


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if len(DEMOGRAPHIC_SEQUENCE) != 100:
        raise AssertionError("Scaled demographic sequence must contain exactly 100 records.")
    records = [record_for(i) for i in range(1, 101)]

    jsonl_path = OUT_DIR / "prompts.jsonl"
    with jsonl_path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=True) + "\n")

    csv_path = OUT_DIR / "manifest.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "person_id",
                "sex",
                "age",
                "age_bucket",
                "demographic_target",
                "background",
                "skin_tone",
                "weathering_note",
                "habitus_note",
                "habitus_group",
                "aesthetic_note",
                "attractiveness_note",
                "front_image_path",
                "side_image_path",
                "back_image_path",
            ],
        )
        writer.writeheader()
        for record in records:
            writer.writerow({key: record[key] for key in writer.fieldnames})

    print(f"Wrote {csv_path}")
    print(f"Wrote {jsonl_path}")

    notes_path = OUT_DIR / "distribution_notes.md"
    notes_path.write_text(
        "\n".join(
            [
                "# Corrected Race/Ethnicity Distribution",
                "",
                "Source table:",
                "",
                "| Race/Ethnicity | Number | Percentage |",
                "| --- | ---: | ---: |",
                *[
                    f"| {key.replace('_', ' ').title()} | {value['count']} | {value['percentage']}% |"
                    for key, value in SOURCE_DISTRIBUTION.items()
                ],
                "",
                "Scaled 100-person generation target:",
                "",
                "| Race/Ethnicity | People |",
                "| --- | ---: |",
                *[
                    f"| {key.replace('_', ' ').title()} | {value} |"
                    for key, value in SCALED_100_COUNTS.items()
                ],
                "",
                "Native American rounds to 0 in a 100-person sample. Use the full 716-person source count for exact representation, or intentionally overrepresent it as 1/100 if needed.",
                "",
                "Aesthetic bias:",
                "",
                "- Future prompts intentionally lean toward plain, rugged, unpolished, below-average conventional attractiveness.",
                "- Avoid model-like symmetry, perfect skin, glamor, and heroic/chiseled faces.",
                "- Keep anatomy realistic and normal; variation should come from natural asymmetry, weathering, pores, facial fullness, gauntness, and ordinary proportions.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"Wrote {notes_path}")


if __name__ == "__main__":
    main()

"""Extensive unit tests for the Quest Safety & Validation Engine.

Covers:
  ValidationResult types:
    - Severity enum values
    - ValidationIssue immutability
    - ValidationReport helpers (has_hard_blocks, is_blocking, merge, to_dict)

  QuestSafetyValidator — clean quests:
    - typical safe quests pass with no issues

  QuestSafetyValidator — adversarial inputs (one per category):
    - trespassing
    - breaking and entering
    - theft / shoplifting
    - vandalism
    - private property
    - restricted area / construction site
    - dangerous road crossing
    - dangerous animals
    - climbing dangerous structures
    - harassment / stalking / following
    - self-harm
    - intoxication / alcohol / drugs
    - weapons
    - stranger vehicle / accepting from strangers
    - sensitive personal information
    - spending money

  QuestSafetyValidator — edge cases:
    - violation in title field
    - violation in objectives field
    - violation in safety_notes field
    - multiple simultaneous violations all reported
    - deduplication: same rule matched in multiple fields counted once
    - all findings are HARD_BLOCK severity
    - pipeline stops on HARD_BLOCK (quality/business not run)

  QuestQualityValidator:
    - clean quest passes
    - generic title flagged SOFT_BLOCK
    - single-word non-generic title flagged WARNING
    - brief too short flagged SOFT_BLOCK
    - brief identical to title flagged SOFT_BLOCK
    - vague objective ("do something") flagged SOFT_BLOCK
    - trailing ellipsis in objective flagged SOFT_BLOCK
    - objective instruction < 4 words flagged SOFT_BLOCK
    - duplicate objectives flagged SOFT_BLOCK
    - too many objectives flagged WARNING (>8)
    - duration too short for objective count flagged SOFT_BLOCK
    - impossible requirement (weather dependency) flagged SOFT_BLOCK
    - impossible requirement (requires a car) flagged SOFT_BLOCK
    - impossible requirement (requires a friend) flagged SOFT_BLOCK
    - XP rate too low flagged WARNING
    - XP rate too high flagged WARNING
    - missing safety notes for explorer difficulty flagged WARNING
    - missing safety notes for chaos difficulty flagged WARNING
    - chill difficulty without safety notes passes (no warning)

  QuestBusinessValidator:
    - valid quest passes clean
    - invalid difficulty flagged SOFT_BLOCK
    - duration below minimum flagged SOFT_BLOCK
    - duration above maximum flagged SOFT_BLOCK
    - duration mismatch beyond tolerance flagged SOFT_BLOCK
    - duration within tolerance passes
    - XP below range for difficulty flagged SOFT_BLOCK
    - XP above range for difficulty flagged SOFT_BLOCK
    - XP at boundary values passes
    - objective count below minimum flagged SOFT_BLOCK
    - no requested_duration skips mismatch check

  ValidationPipeline:
    - clean quest passes all stages
    - HARD_BLOCK stops pipeline (quality/business not run)
    - SOFT_BLOCK from safety_notes triggers quality+business still run
    - multiple soft blocks accumulate in merged report
    - warnings don't block persistence
    - report.to_dict contains all expected keys
"""

import pytest

from app.ai.schemas.quest_output import GeneratedObjective, GeneratedQuestOutput
from app.ai.validators import (
    QuestBusinessValidator,
    QuestQualityValidator,
    QuestSafetyValidator,
    Severity,
    ValidationIssue,
    ValidationPipeline,
    ValidationReport,
)

# ---------------------------------------------------------------------------
# Quest builder helpers
# ---------------------------------------------------------------------------


def _quest(
    title: str = "The Colour Hunt",
    brief: str = (
        "Walk through the park and find five distinct natural colours. "
        "Look closely at leaves, flowers, bark, and stones."
    ),
    duration_minutes: int = 20,
    difficulty: str = "chill",
    objectives: list[dict] | None = None,
    xp_reward: int = 75,
    evidence_required: bool = True,
    safety_notes: str = "Stay on public paths and be aware of your surroundings.",
) -> GeneratedQuestOutput:
    """Build a valid GeneratedQuestOutput with sensible defaults."""
    if objectives is None:
        objectives = [
            {
                "id": "obj-1",
                "instruction": "Find five distinct natural colours in the park",
                "optional": False,
            },
            {
                "id": "obj-2",
                "instruction": "Photograph the most interesting colour you find",
                "optional": True,
            },
        ]
    parsed_objectives = [GeneratedObjective(**o) for o in objectives]
    return GeneratedQuestOutput(
        title=title,
        brief=brief,
        duration_minutes=duration_minutes,
        difficulty=difficulty,
        objectives=parsed_objectives,
        xp_reward=xp_reward,
        evidence_required=evidence_required,
        safety_notes=safety_notes,
    )


def _quest_unchecked(**overrides) -> GeneratedQuestOutput:
    """Build a GeneratedQuestOutput bypassing Pydantic validation.

    Use ONLY for quality-validator tests that need to probe edge-case values
    (e.g. briefs shorter than 20 chars) that Pydantic's schema would normally
    reject.  Never use this for safety tests — those must use valid quests.
    """
    defaults = {
        "title": "The Colour Hunt",
        "brief": "Walk through the park and find five distinct natural colours.",
        "duration_minutes": 20,
        "difficulty": "chill",
        "objectives": [
            GeneratedObjective(
                id="obj-1",
                instruction="Find five distinct natural colours in the park",
                optional=False,
            )
        ],
        "xp_reward": 75,
        "evidence_required": True,
        "safety_notes": "Stay on public paths.",
    }
    defaults.update(overrides)
    # Ensure objectives are GeneratedObjective instances
    if (
        isinstance(defaults["objectives"], list)
        and defaults["objectives"]
        and isinstance(defaults["objectives"][0], dict)
    ):
        defaults["objectives"] = [GeneratedObjective(**o) for o in defaults["objectives"]]
    return GeneratedQuestOutput.model_construct(**defaults)


def _obj(instruction: str, optional: bool = False, id: str = "obj-1") -> dict:
    return {"id": id, "instruction": instruction, "optional": optional}


# ===========================================================================
# ValidationResult types
# ===========================================================================


class TestValidationResultTypes:
    def test_severity_enum_values(self):
        assert Severity.HARD_BLOCK == "HARD_BLOCK"
        assert Severity.SOFT_BLOCK == "SOFT_BLOCK"
        assert Severity.WARNING == "WARNING"

    def test_validation_issue_is_immutable(self):
        issue = ValidationIssue(
            severity=Severity.HARD_BLOCK,
            code="TEST_CODE",
            field="brief",
            message="Test message",
        )
        with pytest.raises((AttributeError, TypeError)):
            issue.code = "OTHER"  # type: ignore[misc]

    def test_issue_is_blocking_for_hard_block(self):
        issue = ValidationIssue(Severity.HARD_BLOCK, "C", "f", "m")
        assert issue.is_blocking() is True

    def test_issue_is_blocking_for_soft_block(self):
        issue = ValidationIssue(Severity.SOFT_BLOCK, "C", "f", "m")
        assert issue.is_blocking() is True

    def test_issue_not_blocking_for_warning(self):
        issue = ValidationIssue(Severity.WARNING, "C", "f", "m")
        assert issue.is_blocking() is False

    def test_report_has_hard_blocks(self):
        report = ValidationReport()
        report.add(ValidationIssue(Severity.HARD_BLOCK, "C", "f", "m"))
        assert report.has_hard_blocks is True
        assert report.is_blocking is True

    def test_report_has_soft_blocks(self):
        report = ValidationReport()
        report.add(ValidationIssue(Severity.SOFT_BLOCK, "C", "f", "m"))
        assert report.has_soft_blocks is True
        assert report.is_blocking is True

    def test_report_warning_not_blocking(self):
        report = ValidationReport()
        report.add(ValidationIssue(Severity.WARNING, "C", "f", "m"))
        assert report.has_hard_blocks is False
        assert report.is_blocking is False

    def test_empty_report_not_blocking(self):
        report = ValidationReport()
        assert report.is_blocking is False
        assert not report.issues

    def test_report_merge(self):
        r1 = ValidationReport()
        r1.add(ValidationIssue(Severity.HARD_BLOCK, "A", "f", "m"))
        r2 = ValidationReport()
        r2.add(ValidationIssue(Severity.WARNING, "B", "f", "m"))
        merged = r1.merge(r2)
        assert len(merged.issues) == 2
        assert merged.has_hard_blocks
        assert len(merged.warnings) == 1

    def test_merge_does_not_mutate_originals(self):
        r1 = ValidationReport()
        r1.add(ValidationIssue(Severity.HARD_BLOCK, "A", "f", "m"))
        r2 = ValidationReport()
        _ = r1.merge(r2)
        assert len(r1.issues) == 1

    def test_report_to_dict_structure(self):
        report = ValidationReport()
        report.add(ValidationIssue(Severity.HARD_BLOCK, "CODE", "brief", "msg"))
        d = report.to_dict()
        assert d["blocking"] is True
        assert d["hard_block_count"] == 1
        assert d["soft_block_count"] == 0
        assert d["warning_count"] == 0
        assert len(d["issues"]) == 1
        assert d["issues"][0]["code"] == "CODE"
        assert d["issues"][0]["severity"] == "HARD_BLOCK"


# ===========================================================================
# QuestSafetyValidator — clean quests
# ===========================================================================


class TestSafetyValidatorClean:
    def test_clean_quest_passes(self):
        report = QuestSafetyValidator().validate(_quest())
        assert not report.has_hard_blocks, f"Unexpected blocks: {report.issues}"

    def test_various_clean_environments(self):
        for env_brief in [
            "Walk through the campus and count different types of trees.",
            "Explore the neighborhood and find three red front doors.",
            "Sit in the park and listen for bird calls for five minutes.",
        ]:
            report = QuestSafetyValidator().validate(_quest(brief=env_brief))
            assert not report.has_hard_blocks, f"Blocked clean quest: {env_brief!r}"


# ===========================================================================
# QuestSafetyValidator — adversarial inputs
# ===========================================================================


class TestSafetyValidatorAdversarial:
    """One adversarial test per safety category from docs/13_AI_SAFETY.md."""

    def _assert_blocked(self, quest: GeneratedQuestOutput, expected_code: str) -> None:
        report = QuestSafetyValidator().validate(quest)
        assert report.has_hard_blocks, (
            f"Expected HARD_BLOCK for {expected_code} but got no blocks. Issues: {report.issues}"
        )
        codes = {i.code for i in report.hard_blocks}
        assert expected_code in codes, f"Expected code {expected_code} not found. Got: {codes}"

    # ---- 1. Trespassing -----------------------------------------------
    def test_trespassing_in_brief(self):
        self._assert_blocked(
            _quest(brief="You must trespass onto the old factory grounds to complete this quest."),
            "SAFETY_TRESPASSING",
        )

    def test_breaking_and_entering(self):
        self._assert_blocked(
            _quest(brief="Break into the abandoned building to find the hidden message."),
            "SAFETY_BREAKING_ENTERING",
        )

    def test_theft(self):
        self._assert_blocked(
            _quest(objectives=[_obj("Steal a flower from someone's garden")]),
            "SAFETY_THEFT",
        )

    def test_shoplifting(self):
        self._assert_blocked(
            _quest(brief="Shoplift a snack from the convenience store to prove your skills."),
            "SAFETY_THEFT",
        )

    def test_vandalism(self):
        self._assert_blocked(
            _quest(objectives=[_obj("Spray-paint your quest symbol on the underpass wall")]),
            "SAFETY_VANDALISM",
        )

    # ---- 2. Private property ------------------------------------------
    def test_private_property_access(self):
        self._assert_blocked(
            _quest(brief="Enter the private property behind the school to find the bench."),
            "SAFETY_PRIVATE_PROPERTY",
        )

    def test_restricted_area(self):
        self._assert_blocked(
            _quest(brief="Explore the restricted area near the old power station."),
            "SAFETY_RESTRICTED_AREA",
        )

    def test_construction_site(self):
        self._assert_blocked(
            _quest(
                objectives=[
                    _obj("Walk through the construction site on Fifth Street to count cranes")
                ]
            ),
            "SAFETY_CONSTRUCTION_SITE",
        )

    # ---- 3. Dangerous roads -------------------------------------------
    def test_highway_crossing(self):
        self._assert_blocked(
            _quest(brief="Cross the highway on foot to reach the other side of the trail."),
            "SAFETY_DANGEROUS_ROAD",
        )

    def test_motorway_crossing(self):
        self._assert_blocked(
            _quest(objectives=[_obj("Cross the motorway at the unmarked point near the junction")]),
            "SAFETY_DANGEROUS_ROAD",
        )

    # ---- 4. Dangerous animals -----------------------------------------
    def test_dangerous_animal_interaction(self):
        self._assert_blocked(
            _quest(brief="Approach the wildlife in the deer enclosure and feed them by hand."),
            "SAFETY_DANGEROUS_ANIMALS",
        )

    def test_provoking_animals(self):
        # "Provoke a stray dog" is broad enough to match SAFETY_DANGEROUS_ANIMALS
        # (the dangerous-animals rule covers provocation of strays)
        report = QuestSafetyValidator().validate(
            _quest(objectives=[_obj("Provoke a stray dog to test your courage near the park gate")])
        )
        assert report.has_hard_blocks
        codes = {i.code for i in report.hard_blocks}
        assert codes & {"SAFETY_DANGEROUS_ANIMALS", "SAFETY_ANIMAL_PROVOCATION"}, (
            f"Expected an animal-related safety code, got: {codes}"
        )

    # ---- 5. Dangerous structures / climbing ---------------------------
    def test_climbing_rooftop(self):
        self._assert_blocked(
            _quest(brief="Climb to the rooftop of the community centre to photograph the skyline."),
            "SAFETY_DANGEROUS_CLIMBING",
        )

    def test_climbing_building(self):
        self._assert_blocked(
            _quest(objectives=[_obj("Climb the clock tower building and touch the bell")]),
            "SAFETY_DANGEROUS_CLIMBING",
        )

    def test_jumping_from_height(self):
        self._assert_blocked(
            _quest(objectives=[_obj("Jump from the bridge wall into the river below")]),
            "SAFETY_DANGEROUS_JUMP",
        )

    # ---- 6. Harassment ------------------------------------------------
    def test_harassment(self):
        self._assert_blocked(
            _quest(brief="Follow someone around the park and harass them until they leave."),
            "SAFETY_HARASSMENT",
        )

    def test_following_stranger(self):
        self._assert_blocked(
            _quest(objectives=[_obj("Follow a stranger home to discover where they live")]),
            "SAFETY_FOLLOWING_STRANGERS",
        )

    def test_stalking(self):
        self._assert_blocked(
            _quest(brief="Stalk your target for 30 minutes without being seen."),
            "SAFETY_HARASSMENT",
        )

    def test_surveillance_of_individual(self):
        self._assert_blocked(
            _quest(objectives=[_obj("Spy on a person in the café window for 10 minutes")]),
            "SAFETY_SURVEILLANCE",
        )

    # ---- 7. Self-harm ------------------------------------------------
    def test_self_harm_reference(self):
        self._assert_blocked(
            _quest(brief="This mission requires pushing yourself to the point of self-harm."),
            "SAFETY_SELF_HARM",
        )

    def test_suicide_reference(self):
        self._assert_blocked(
            _quest(brief="Walk to the suicide bridge and stand on the edge for one minute."),
            "SAFETY_SELF_HARM",
        )

    # ---- 8. Intoxication / substances ---------------------------------
    def test_alcohol(self):
        self._assert_blocked(
            _quest(
                brief="Visit three bars and drink a beer at each one to complete your pub crawl."
            ),
            "SAFETY_ALCOHOL",
        )

    def test_controlled_substances(self):
        self._assert_blocked(
            _quest(brief="Find the drug dealer at the corner and complete the transaction."),
            "SAFETY_CONTROLLED_SUBSTANCES",
        )

    def test_cannabis(self):
        self._assert_blocked(
            _quest(
                objectives=[
                    _obj("Locate and photograph the cannabis plants growing behind the warehouse")
                ]
            ),
            "SAFETY_CONTROLLED_SUBSTANCES",
        )

    # ---- 9. Weapons --------------------------------------------------
    def test_weapons_reference(self):
        self._assert_blocked(
            _quest(objectives=[_obj("Find the hidden knife cache behind the park bench")]),
            "SAFETY_WEAPONS",
        )

    def test_firearm_reference(self):
        self._assert_blocked(
            _quest(brief="Locate the gun shop and photograph the display through the window."),
            "SAFETY_WEAPONS",
        )

    # ---- 10. Stranger interaction ------------------------------------
    def test_approach_strangers(self):
        self._assert_blocked(
            _quest(
                objectives=[_obj("Approach a stranger on the street and ask for their address")]
            ),
            "SAFETY_APPROACH_STRANGERS",
        )

    def test_accept_from_stranger(self):
        self._assert_blocked(
            _quest(objectives=[_obj("Accept a ride from a stranger to reach the location faster")]),
            "SAFETY_ACCEPT_FROM_STRANGER",
        )

    # ---- 11. Personal information ------------------------------------
    def test_reveal_personal_info(self):
        self._assert_blocked(
            _quest(
                objectives=[_obj("Reveal your personal information to the clerk to get the prize")]
            ),
            "SAFETY_PERSONAL_INFO",
        )

    def test_credentials_reference(self):
        self._assert_blocked(
            _quest(
                objectives=[
                    _obj(
                        "Find the ATM and photograph your bank account balance displayed on screen"
                    )
                ]
            ),
            "SAFETY_CREDENTIALS",
        )

    # ---- 12. Spending money ------------------------------------------
    def test_purchase_required(self):
        self._assert_blocked(
            _quest(objectives=[_obj("Purchase a coffee from the café at the start of your walk")]),
            "SAFETY_SPENDING_MONEY",
        )

    def test_buy_required(self):
        self._assert_blocked(
            _quest(brief="Buy a flower from the market stall and give it to a passerby."),
            "SAFETY_SPENDING_MONEY",
        )

    # ---- Violation in specific fields --------------------------------
    def test_violation_in_title(self):
        report = QuestSafetyValidator().validate(_quest(title="Trespass into the Old Mill"))
        assert report.has_hard_blocks
        matching = [i for i in report.hard_blocks if i.field == "title"]
        assert matching, "Expected field='title' on violation but got: " + str(report.issues)

    def test_violation_in_objectives_field(self):
        report = QuestSafetyValidator().validate(
            _quest(objectives=[_obj("Steal a badge from the security guard's desk")])
        )
        assert report.has_hard_blocks
        matching = [i for i in report.hard_blocks if i.field == "objectives"]
        assert matching

    def test_violation_in_safety_notes(self):
        report = QuestSafetyValidator().validate(
            _quest(safety_notes="You may need to trespass briefly to complete this objective.")
        )
        assert report.has_hard_blocks

    # ---- Multiple violations all reported ----------------------------
    def test_multiple_violations_all_reported(self):
        quest = _quest(
            brief="Trespass onto private property and steal an object.",
            objectives=[_obj("Buy supplies, then vandalize the fence")],
        )
        report = QuestSafetyValidator().validate(quest)
        assert report.has_hard_blocks
        assert len(report.hard_blocks) >= 3, (
            f"Expected at least 3 violations, got {len(report.hard_blocks)}: "
            f"{[i.code for i in report.hard_blocks]}"
        )

    # ---- Deduplication -----------------------------------------------
    def test_same_rule_not_reported_twice(self):
        """If trespass appears in both brief and objectives it should only produce one issue."""
        quest = _quest(
            brief="You must trespass onto the grounds.",
            objectives=[_obj("Trespass through the side gate to reach the target")],
        )
        report = QuestSafetyValidator().validate(quest)
        trespass_issues = [i for i in report.hard_blocks if i.code == "SAFETY_TRESPASSING"]
        assert len(trespass_issues) == 1, (
            f"Expected 1 deduped trespass issue, got {len(trespass_issues)}"
        )

    # ---- All findings are HARD_BLOCK ---------------------------------
    def test_all_safety_findings_are_hard_block(self):
        quest = _quest(brief="Trespass onto private property and steal things.")
        report = QuestSafetyValidator().validate(quest)
        for issue in report.issues:
            assert issue.severity == Severity.HARD_BLOCK, (
                f"Expected HARD_BLOCK but got {issue.severity} for {issue.code}"
            )


# ===========================================================================
# QuestQualityValidator
# ===========================================================================


class TestQualityValidator:
    def test_clean_quest_passes(self):
        report = QuestQualityValidator().validate(_quest())
        blocking = [i for i in report.issues if i.is_blocking()]
        assert not blocking, f"Unexpected blocking: {blocking}"

    def test_generic_title_quest_flagged(self):
        report = QuestQualityValidator().validate(_quest(title="quest"))
        codes = {i.code for i in report.issues}
        assert "QUALITY_GENERIC_TITLE" in codes

    def test_generic_title_is_soft_block(self):
        report = QuestQualityValidator().validate(_quest(title="mission"))
        issue = next(i for i in report.issues if i.code == "QUALITY_GENERIC_TITLE")
        assert issue.severity == Severity.SOFT_BLOCK

    def test_single_word_non_generic_title_is_warning(self):
        report = QuestQualityValidator().validate(_quest(title="Nightwatch"))
        codes = {i.code for i in report.issues}
        assert "QUALITY_TITLE_TOO_SHORT" in codes
        issue = next(i for i in report.issues if i.code == "QUALITY_TITLE_TOO_SHORT")
        assert issue.severity == Severity.WARNING

    def test_brief_too_short_flagged(self):
        # Use model_construct to bypass Pydantic's min_length=20 constraint
        # so the QuestQualityValidator itself can detect the short brief
        report = QuestQualityValidator().validate(_quest_unchecked(brief="Go walk."))
        codes = {i.code for i in report.issues}
        assert "QUALITY_BRIEF_TOO_SHORT" in codes

    def test_brief_identical_to_title_flagged(self):
        # Title is 15 chars — below Pydantic's min_length=20 for brief,
        # so use model_construct to test the quality validator directly
        report = QuestQualityValidator().validate(
            _quest_unchecked(title="The Colour Hunt", brief="The Colour Hunt")
        )
        codes = {i.code for i in report.issues}
        assert "QUALITY_BRIEF_SAME_AS_TITLE" in codes

    def test_vague_objective_do_something(self):
        report = QuestQualityValidator().validate(_quest(objectives=[_obj("do something")]))
        codes = {i.code for i in report.issues}
        assert "QUALITY_VAGUE_OBJECTIVE" in codes

    def test_vague_objective_trailing_ellipsis(self):
        report = QuestQualityValidator().validate(
            _quest(objectives=[_obj("Find something interesting in the park...")])
        )
        codes = {i.code for i in report.issues}
        assert "QUALITY_VAGUE_OBJECTIVE" in codes

    def test_objective_too_short(self):
        report = QuestQualityValidator().validate(
            _quest(objectives=[_obj("Go walk.")])  # 2 words
        )
        codes = {i.code for i in report.issues}
        assert "QUALITY_OBJECTIVE_TOO_SHORT" in codes

    def test_duplicate_objectives_flagged(self):
        report = QuestQualityValidator().validate(
            _quest(
                objectives=[
                    _obj("Find a red leaf in the park", id="obj-1"),
                    _obj("Find a red leaf in the park", id="obj-2"),
                ]
            )
        )
        codes = {i.code for i in report.issues}
        assert "QUALITY_DUPLICATE_OBJECTIVE" in codes

    def test_too_many_objectives_warning(self):
        objectives = [
            _obj(f"Find item number {i} somewhere in the park area", id=f"obj-{i}")
            for i in range(1, 10)  # 9 objectives
        ]
        report = QuestQualityValidator().validate(_quest(objectives=objectives))
        codes = {i.code for i in report.issues}
        assert "QUALITY_TOO_MANY_OBJECTIVES" in codes
        # Should be WARNING not SOFT_BLOCK
        issue = next(i for i in report.issues if i.code == "QUALITY_TOO_MANY_OBJECTIVES")
        assert issue.severity == Severity.WARNING

    def test_duration_too_short_for_objectives(self):
        # 6 required objectives × 3 min = 18 min needed; give only 5 min
        objectives = [
            _obj(f"Complete task number {i} in the given area", id=f"obj-{i}") for i in range(1, 7)
        ]
        report = QuestQualityValidator().validate(_quest(duration_minutes=5, objectives=objectives))
        codes = {i.code for i in report.issues}
        assert "QUALITY_DURATION_TOO_SHORT_FOR_OBJECTIVES" in codes

    def test_impossible_weather_requirement(self):
        report = QuestQualityValidator().validate(
            _quest(objectives=[_obj("Complete this only if it must be raining outside today")])
        )
        codes = {i.code for i in report.issues}
        assert "QUALITY_IMPOSSIBLE_REQUIREMENT" in codes

    def test_impossible_car_requirement(self):
        report = QuestQualityValidator().validate(
            _quest(objectives=[_obj("This requires a car to drive between the waypoints")])
        )
        codes = {i.code for i in report.issues}
        assert "QUALITY_IMPOSSIBLE_REQUIREMENT" in codes

    def test_impossible_friend_requirement(self):
        report = QuestQualityValidator().validate(
            _quest(brief="This quest requires a friend to help you complete it successfully.")
        )
        codes = {i.code for i in report.issues}
        assert "QUALITY_IMPOSSIBLE_REQUIREMENT" in codes

    def test_xp_rate_too_low_warning(self):
        # 10 XP for 20 min = 0.5 XP/min → too low
        report = QuestQualityValidator().validate(_quest(xp_reward=10, duration_minutes=20))
        codes = {i.code for i in report.issues}
        assert "QUALITY_XP_RATE_TOO_LOW" in codes
        issue = next(i for i in report.issues if i.code == "QUALITY_XP_RATE_TOO_LOW")
        assert issue.severity == Severity.WARNING

    def test_xp_rate_too_high_warning(self):
        # 400 XP for 5 min = 80 XP/min → too high
        report = QuestQualityValidator().validate(_quest(xp_reward=400, duration_minutes=5))
        codes = {i.code for i in report.issues}
        assert "QUALITY_XP_RATE_TOO_HIGH" in codes

    def test_missing_safety_notes_explorer_flagged(self):
        report = QuestQualityValidator().validate(
            _quest(difficulty="explorer", safety_notes="", xp_reward=150)
        )
        codes = {i.code for i in report.issues}
        assert "QUALITY_MISSING_SAFETY_NOTES" in codes
        issue = next(i for i in report.issues if i.code == "QUALITY_MISSING_SAFETY_NOTES")
        assert issue.severity == Severity.WARNING

    def test_missing_safety_notes_chaos_flagged(self):
        report = QuestQualityValidator().validate(
            _quest(difficulty="chaos", safety_notes="", xp_reward=150)
        )
        codes = {i.code for i in report.issues}
        assert "QUALITY_MISSING_SAFETY_NOTES" in codes

    def test_chill_difficulty_without_safety_notes_passes(self):
        report = QuestQualityValidator().validate(_quest(difficulty="chill", safety_notes=""))
        safety_note_issues = [i for i in report.issues if i.code == "QUALITY_MISSING_SAFETY_NOTES"]
        assert not safety_note_issues


# ===========================================================================
# QuestBusinessValidator
# ===========================================================================


class TestBusinessValidator:
    def test_valid_quest_passes(self):
        report = QuestBusinessValidator().validate(_quest(), requested_duration=20)
        assert not report.is_blocking, f"Unexpected issues: {report.issues}"

    def test_invalid_difficulty_flagged(self):
        # Bypass Pydantic validation to inject invalid value for testing
        quest = _quest()
        object.__setattr__(quest, "difficulty", "ultra")  # bypass frozen
        report = QuestBusinessValidator().validate(quest)
        codes = {i.code for i in report.issues}
        assert "BUSINESS_INVALID_DIFFICULTY" in codes

    def test_duration_below_minimum(self):
        quest = _quest()
        object.__setattr__(quest, "duration_minutes", 3)
        report = QuestBusinessValidator().validate(quest)
        codes = {i.code for i in report.issues}
        assert "BUSINESS_DURATION_TOO_SHORT" in codes

    def test_duration_above_maximum(self):
        quest = _quest()
        object.__setattr__(quest, "duration_minutes", 200)
        report = QuestBusinessValidator().validate(quest)
        codes = {i.code for i in report.issues}
        assert "BUSINESS_DURATION_TOO_LONG" in codes

    def test_duration_mismatch_beyond_tolerance(self):
        # Quest says 20 min, player requested 45 → delta 25 > tolerance 5
        report = QuestBusinessValidator().validate(
            _quest(duration_minutes=20), requested_duration=45
        )
        codes = {i.code for i in report.issues}
        assert "BUSINESS_DURATION_MISMATCH" in codes

    def test_duration_within_tolerance_passes(self):
        # Quest says 22 min, player requested 20 → delta 2 ≤ tolerance 5
        report = QuestBusinessValidator().validate(
            _quest(duration_minutes=22), requested_duration=20
        )
        assert not report.is_blocking

    def test_xp_below_range_chill(self):
        # chill range: 50-125; 10 is too low
        report = QuestBusinessValidator().validate(_quest(xp_reward=10), requested_duration=20)
        codes = {i.code for i in report.issues}
        assert "BUSINESS_XP_OUT_OF_RANGE" in codes

    def test_xp_above_range_chill(self):
        # chill range: 50-125; 200 is too high
        report = QuestBusinessValidator().validate(_quest(xp_reward=200), requested_duration=20)
        codes = {i.code for i in report.issues}
        assert "BUSINESS_XP_OUT_OF_RANGE" in codes

    def test_xp_at_lower_boundary_passes(self):
        report = QuestBusinessValidator().validate(_quest(xp_reward=50), requested_duration=20)
        assert not report.is_blocking

    def test_xp_at_upper_boundary_passes(self):
        report = QuestBusinessValidator().validate(_quest(xp_reward=125), requested_duration=20)
        assert not report.is_blocking

    def test_xp_bounds_explorer(self):
        # explorer range: 100-200
        report = QuestBusinessValidator().validate(
            _quest(difficulty="explorer", xp_reward=150, safety_notes="Stay safe."),
            requested_duration=20,
        )
        assert not report.is_blocking

    def test_xp_below_explorer_range(self):
        report = QuestBusinessValidator().validate(
            _quest(difficulty="explorer", xp_reward=50, safety_notes="Stay safe."),
            requested_duration=20,
        )
        codes = {i.code for i in report.issues}
        assert "BUSINESS_XP_OUT_OF_RANGE" in codes

    def test_no_requested_duration_skips_mismatch_check(self):
        # Large duration delta but no requested_duration provided → no MISMATCH issue
        report = QuestBusinessValidator().validate(
            _quest(duration_minutes=10), requested_duration=None
        )
        codes = {i.code for i in report.issues}
        assert "BUSINESS_DURATION_MISMATCH" not in codes

    def test_all_business_findings_are_soft_block(self):
        quest = _quest(xp_reward=10)
        report = QuestBusinessValidator().validate(quest, requested_duration=20)
        for issue in report.issues:
            assert issue.severity == Severity.SOFT_BLOCK, (
                f"Expected SOFT_BLOCK but got {issue.severity} for {issue.code}"
            )


# ===========================================================================
# ValidationPipeline
# ===========================================================================


class TestValidationPipeline:
    def test_clean_quest_passes_all_stages(self):
        report = ValidationPipeline().run(_quest(), requested_duration=20)
        assert not report.is_blocking
        assert not report.has_hard_blocks
        assert not report.has_soft_blocks

    def test_hard_block_stops_pipeline(self):
        """Safety HARD_BLOCK must halt pipeline; quality/business issues not added."""
        quest = _quest(brief="You must trespass onto private property.")
        report = ValidationPipeline().run(quest, requested_duration=20)

        assert report.has_hard_blocks
        # Quality/business validators should not have run — report only has safety issues
        non_safety_codes = [i.code for i in report.issues if not i.code.startswith("SAFETY_")]
        assert not non_safety_codes, (
            f"Pipeline should stop after safety HARD_BLOCK but got: {non_safety_codes}"
        )

    def test_soft_block_runs_all_stages(self):
        """Soft blocks (quality) should still allow business validator to run."""
        # Generic title → quality SOFT_BLOCK, but safety passes so pipeline continues
        report = ValidationPipeline().run(
            _quest(title="quest", xp_reward=10),  # quality + business both have issues
            requested_duration=20,
        )
        codes = {i.code for i in report.issues}
        assert "QUALITY_GENERIC_TITLE" in codes
        assert "BUSINESS_XP_OUT_OF_RANGE" in codes

    def test_warnings_do_not_block(self):
        # Single-word non-generic title → WARNING only
        report = ValidationPipeline().run(_quest(title="Nightwatch"), requested_duration=20)
        assert report.warnings
        assert not report.is_blocking

    def test_report_to_dict_from_pipeline(self):
        report = ValidationPipeline().run(_quest(), requested_duration=20)
        d = report.to_dict()
        assert "blocking" in d
        assert "issues" in d
        assert d["blocking"] is False

    def test_multiple_soft_blocks_accumulate(self):
        # Generic title + too-short brief → multiple SOFT_BLOCKs
        # Use model_construct to bypass Pydantic min_length=20 on brief
        report = ValidationPipeline().run(
            _quest_unchecked(title="task", brief="Go do."),
            requested_duration=20,
        )
        soft = report.soft_blocks
        assert len(soft) >= 2, f"Expected ≥2 soft blocks, got {[i.code for i in soft]}"

    def test_safety_issue_code_prefix(self):
        """All safety issues must have SAFETY_ prefix."""
        quest = _quest(brief="Trespass onto restricted area for this mission.")
        report = ValidationPipeline().run(quest)
        for issue in report.hard_blocks:
            assert issue.code.startswith("SAFETY_"), (
                f"Safety issue code lacks SAFETY_ prefix: {issue.code}"
            )

    def test_quest_with_only_warnings_can_be_persisted(self):
        """A quest with only WARNINGs must not be considered blocking."""
        report = ValidationPipeline().run(
            _quest(title="Nightwatch"),  # WARNING for single-word title
            requested_duration=20,
        )
        # Simulate the orchestrator's decision gate
        may_persist = not report.is_blocking
        assert may_persist is True

import json
import config
import asyncio
from typing import Tuple, cast
from library import Skill, SkillFile
from providers import ChatMessage, ChatResponse
from .convention import (
    BEGIN_BLOCK, CLOSE_BLOCK,
    IDENTITY_PREFIX,
    KEYWORD_PROMPT, SUBJECT_PROMPT, LEVEL_PROMPT, SUBJECT_LEVEL_PROMPT,
)

TEMPERATURE = 0

class BookkeeperError(Exception):
    def __init__(self, message: str) -> None:
        self.message = message

    @staticmethod
    def missing_begin():
        return BookkeeperError("Bookkeeper did not respond with a begin block.")

    @staticmethod
    def missing_close():
        return BookkeeperError("Bookkeeper did not respond with a close block.")

    @staticmethod
    def invalid_parse():
        return BookkeeperError("Bookkeeper did not respond with valid json.")

    @staticmethod
    def invalid_format():
        return BookkeeperError("Bookkeeper responded with unexpected data.")

    @staticmethod
    def bookkeeper_missing():
        return BookkeeperError("Bookkeeper was not able to generate a response.")

def _build_identity() -> str:
    return (IDENTITY_PREFIX.strip()
            .replace("[start]", BEGIN_BLOCK)
            .replace("[end]", CLOSE_BLOCK))

def _render(template: str,
            name: str,
            filename: str,
            content: str,
            level: float | None = None,
            subject: str | None = None) -> Tuple[str, str]:
    rendered = (template.strip()
                .replace("{{SKILL_NAME}}", name)
                .replace("{{SKILL_FILENAME}}", filename)
                .replace("{{SKILL_LEVEL}}", str(level) if level is not None else "N/A.")
                .replace("{{SKILL_SUBJECT}}", subject if subject else "N/A.")
                .replace("{{SKILL_CONTENT}}", content))
    return _build_identity(), rendered


def _render_for_file(template: str, skill_file: SkillFile) -> Tuple[str, str]:
    return _render(
        template,
        skill_file.parent.name,
        skill_file.name,
        skill_file.content_guaranteed(),
        skill_file.level,
        skill_file.subject,
    )


def _call(identity: str, message: str) -> dict[str, object]:
    provider = config.load_primary_provider()
    response = asyncio.run(provider.chat(
        [ChatMessage('system', identity), ChatMessage('user', message)],
        temperature=TEMPERATURE,
    ))
    return process_response(response)


def _call_skill(template: str, skill: Skill) -> dict[str, object]:
    combined = '\n\n'.join(
        f'Skill File "{f.name}":\n{f.content_guaranteed()}' for f in skill.files
    )
    identity, message = _render(template, skill.name, "None", combined)
    return _call(identity, message)


def _call_file(template: str, skill_file: SkillFile) -> dict[str, object]:
    identity, message = _render_for_file(template, skill_file)
    return _call(identity, message)

def process_response(response: ChatResponse) -> dict[str, object]:
    content = response.content

    if BEGIN_BLOCK not in content:
        raise BookkeeperError.missing_begin()
    if CLOSE_BLOCK not in content:
        raise BookkeeperError.missing_close()

    begin_parts = content.split(BEGIN_BLOCK)
    if len(begin_parts) > 2:
        raise BookkeeperError.invalid_format()

    close_parts = begin_parts[1].split(CLOSE_BLOCK)
    if len(close_parts) > 2:
        raise BookkeeperError.invalid_format()

    try:
        return json.loads(close_parts[0])
    except Exception:
        raise BookkeeperError.invalid_parse()


def _expect(parsed: dict, key: str, typ: type) -> object:
    """Assert a single-key response with the expected key and type."""
    if len(parsed) != 1 or key not in parsed:
        print(parsed)
        raise BookkeeperError.invalid_format()
    if not isinstance(parsed[key], typ):
        print(parsed)
        raise BookkeeperError.invalid_format()
    return parsed[key]


def generate_keywords(skill: Skill) -> list[str]:
    parsed = _call_skill(KEYWORD_PROMPT, skill)
    return cast(list[str], _expect(parsed, "keywords", list))


def analyze_subject(skill_file: SkillFile) -> str:
    parsed = _call_file(SUBJECT_PROMPT, skill_file)
    return cast(str, _expect(parsed, "subject", str))


def calculate_level(skill_file: SkillFile) -> float:
    parsed = _call_file(LEVEL_PROMPT, skill_file)
    return cast(float, _expect(parsed, "level", float))


def analyze_subject_and_level(skill_file: SkillFile) -> tuple[str, float]:
    parsed = _call_file(SUBJECT_LEVEL_PROMPT, skill_file)

    if len(parsed) != 2 or "subject" not in parsed or "level" not in parsed:
        print(parsed)
        raise BookkeeperError.invalid_format()
    if not isinstance(parsed["subject"], str) or not isinstance(parsed["level"], float):
        print(parsed)
        raise BookkeeperError.invalid_format()

    return cast(str, parsed["subject"]), cast(float, parsed["level"])


def update_skill_metadata(skill: Skill) -> None:
    skill.keywords = generate_keywords(skill)
    for f in skill.files:
        f.subject, f.level = analyze_subject_and_level(f)

    skill.save_meta()


__all__ = [
    "generate_keywords",
    "analyze_subject",
    "calculate_level",
    "update_skill_metadata",
]
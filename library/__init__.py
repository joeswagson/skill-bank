"""
Library module - Skill discovery, parsing, and management.

Skills are stored in ./skills/[skill-name]/ directory:
    - SKILL.md         (main skill descriptor)
    - skill.meta.json  (metadata with variables, files list)

Usage:
    from library import Library
    lib = Library()
    frontend = lib.get("frontend-design")
    print(frontend.content())  # Variable-substituted content
"""
from .skill import Skill, SkillFile, Library, SKILL_ENTRY, META_ENTRY

__all__ = [
    "Skill",
    "SkillFile",
    "Library",
    "SKILL_ENTRY",
    "META_ENTRY",
]
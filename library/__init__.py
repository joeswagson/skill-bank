"""
Library module - Skill discovery, parsing, and management.

Skills are stored in ./skills/[skill-name]/ directory:
    - SKILL.md         (main skill descriptor)
    - skill.meta.json  (metadata with variables, files list)

Usage:
    from library import Library, create_skill_template

    lib = Library()
    skills = lib.discover()

    frontend = skills.get("frontend-design")
    print(frontend.content)  # Variable-substituted content
"""

from .skill import Skill, Library, create_skill_template, SKILL_TEMPLATE

__all__ = [
    "Skill",
    "Library",
    "create_skill_template",
    "SKILL_TEMPLATE"
]
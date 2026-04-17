"""
Skill parsing and library management.
"""

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

# Default skill template content
SKILL_TEMPLATE = """---
Title: {{SKILL_NAME}}
Description: {{SKILL_DESCRIPTION}}
Tags: {{SKILL_TAGS}}
---

# {{SKILL_NAME}} Skill

## Overview
{{SKILL_OVERVIEW}}

## Capabilities
{{SKILL_CAPABILITIES}}

## Guidelines
{{SKILL_GUIDELINES}}

## Examples
{{SKILL_EXAMPLES}}
"""


@dataclass
class SkillFile:
    """Represents a file within a skill."""
    name: str  # Filename relative to skill directory (e.g., "SKILL.md")
    subject: str = ""  # Subject/category this file addresses
    level: float = 0.0  # Complexity/deepness (0.0 - 1.0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "subject": self.subject,
            "level": self.level
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SkillFile":
        return cls(
            name=data.get("name", ""),
            subject=data.get("subject", ""),
            level=float(data.get("level", 0.0))
        )


@dataclass
class Skill:
    """Represents a single skill with its metadata and content."""

    name: str  # Skill identifier (folder name)
    path: Path  # Path to skill directory

    # Metadata fields
    keywords: List[str] = field(default_factory=list)
    files: List[SkillFile] = field(default_factory=list)
    variables: Dict[str, Any] = field(default_factory=dict)

    # Computed/loaded fields
    _raw_content_cache: Dict[str, str] = field(default_factory=dict, repr=False)
    _substituted_content_cache: Dict[str, str] = field(default_factory=dict, repr=False)

    def __post_init__(self):
        """Load metadata from skill.meta.json if exists."""
        meta_path = self.path / "skill.meta.json"
        if meta_path.exists():
            try:
                data = json.loads(meta_path.read_text())

                if "keywords" in data:
                    self.keywords = data["keywords"]

                if "files" in data:
                    # Validate files are within skill directory (prevent traversal)
                    for file_data in data.get("files", []):
                        file_name = file_data.get("name", "")
                        # Security check: reject any path with .. or absolute paths
                        if ".." not in file_name and not Path(file_name).is_absolute():
                            self.files.append(SkillFile.from_dict(file_data))

                if "variables" in data:
                    self.variables.update(data["variables"])

            except (json.JSONDecodeError, Exception) as e:
                print(f"Warning: Error loading meta for skill '{self.name}': {e}")

    @property
    def files_path(self) -> Path:
        """Path to the skill.meta.json file."""
        return self.path / "skill.meta.json"

    @property
    def is_valid(self) -> bool:
        """Check if skill has required SKILL.md and valid metadata."""
        return (self.path / "SKILL.md").exists() or any(f.name == "SKILL.md" for f in self.files)

    def get_raw_content(self, file_name: str = "SKILL.md") -> Optional[str]:
        """
        Get raw content of a skill file without variable substitution.

        Args:
            file_name: Filename relative to skill directory

        Returns:
            Raw file content or None if not found
        """
        # Check cache first
        if file_name in self._raw_content_cache:
            return self._raw_content_cache[file_name]

        file_path = self.path / file_name

        # Security: ensure path is within skill directory
        try:
            resolved = file_path.resolve()
            skill_root = self.path.resolve()

            # Check if resolved path starts with skill root (prevents .. traversal)
            if not str(resolved).startswith(str(skill_root)):
                print(f"Security warning: File '{file_name}' would escape skill directory")
                return None

            content = file_path.read_text(encoding="utf-8")

        except FileNotFoundError:
            return None
        except Exception as e:
            print(f"Error reading file {file_name}: {e}")
            return None

        # Cache the result
        self._raw_content_cache[file_name] = content or ""
        return self._raw_content_cache.get(file_name)

    def get_substituted_content(self, file_name: str = "SKILL.md") -> Optional[str]:
        """
        Get skill content with variables substituted.

        Replaces {{VARIABLE_NAME}} with values from skill.variables

        Args:
            file_name: Filename relative to skill directory

        Returns:
            Content with variables substituted, or None if not found
        """
        # Check cache first
        if file_name in self._substituted_content_cache:
            return self._substituted_content_cache[file_name]

        raw = self.get_raw_content(file_name)
        if raw is None:
            return None

        content = self._substitute_variables(raw)
        self._substituted_content_cache[file_name] = content
        return content

    def _substitute_variables(self, text: str) -> str:
        """Replace {{VARIABLE_NAME}} patterns with values from variables dict."""

        # Find all variable references
        pattern = r'\{\{(\w+)\}\}'

        def replace_var(match):
            var_name = match.group(1)
            return str(self.variables.get(var_name, f"{{{{{var_name}}}}}"))  # Keep original if not found

        return re.sub(pattern, replace_var, text)

    @property
    def content(self) -> Optional[str]:
        """Shorthand for getting substituted SKILL.md content."""
        return self.get_substituted_content("SKILL.md")

    def save_metadata(self) -> None:
        """Save current metadata back to skill.meta.json"""
        data = {
            "keywords": self.keywords,
            "files": [f.to_dict() for f in self.files],
            "variables": self.variables
        }

        meta_path = self.path / "skill.meta.json"
        with open(meta_path, 'w') as f:
            json.dump(data, f, indent=2)


class Library:
    """Skill library - discovers and manages all skills."""

    def __init__(self, skills_dir: str | Path = "./skills"):
        self.skills_dir = Path(skills_dir).resolve()
        self._skills_cache: Dict[str, Skill] = {}

    @property
    def is_valid(self) -> bool:
        """Check if skills directory exists."""
        return self.skills_dir.exists() and self.skills_dir.is_dir()

    def discover(self) -> "Library":
        """
        Discover all skill directories in the library.

        Looks for subdirectories containing either SKILL.md or skill.meta.json

        Returns:
            Self (for chaining)
        """
        self._skills_cache.clear()

        if not self.is_valid:
            print(f"Skills directory not found: {self.skills_dir}")
            return self

        # Find all subdirectories
        for item in sorted(self.skills_dir.iterdir()):
            if item.is_dir():
                # Check if it looks like a skill (has SKILL.md or meta)
                has_skill_md = (item / "SKILL.md").exists()
                has_meta = (item / "skill.meta.json").exists()

                if has_skill_md or has_meta:
                    skill_name = item.name
                    self._skills_cache[skill_name] = Skill(
                        name=skill_name,
                        path=item
                    )

        return self

    def get(self, name: str) -> Optional[Skill]:
        """Get a skill by name."""
        if not self._skills_cache:
            self.discover()
        return self._skills_cache.get(name)

    def all(self) -> List[Skill]:
        """Get all discovered skills as a list."""
        if not self._skills_cache:
            self.discover()
        return list(self._skills_cache.values())

    def search_keywords(self, keywords: List[str]) -> List[Skill]:
        """Search for skills matching any of the given keywords."""
        results = []

        for skill in self.all():
            for kw in keywords:
                if any([kw.lower() == k.lower() for k in skill.keywords]):
                    results.append(skill)

        return results

    def add_skill(self, name: str, content: str = "") -> Skill:
        """Create a new skill directory with basic files."""
        skill_path = self.skills_dir / name

        # Create directory if needed
        skill_path.mkdir(parents=True, exist_ok=True)

        # Create empty SKILL.md if it doesn't exist
        skill_md = skill_path / "SKILL.md"
        if not skill_md.exists() and content:
            skill_md.write_text(content, encoding="utf-8")

        # Return new Skill object (will load/create meta in __post_init__)
        return Skill(name=name, path=skill_path)


def create_skill_template(
        name: str,
        description: str = "",
        tags: List[str] = None,
        overview: str = "",
        capabilities: str = "",
        guidelines: str = "",
        examples: str = ""
) -> str:
    """
    Create a skill template with variables.

    Args:
        name: Skill name/title
        description: Brief description
        tags: List of tags/keywords
        overview: Overview section content
        capabilities: Capabilities section content
        guidelines: Guidelines section content
        examples: Examples section content

    Returns:
        Template string with {{VARIABLE}} placeholders filled in
    """
    tags_str = ", ".join(tags) if tags else ""

    return SKILL_TEMPLATE.replace("{{SKILL_NAME}}", name).replace(
        "{{SKILL_DESCRIPTION}}", description
    ).replace("{{SKILL_TAGS}}", tags_str).replace(
        "{{SKILL_OVERVIEW}}", overview or "[Add overview here]"
    ).replace("{{SKILL_CAPABILITIES}}", capabilities or "[List capabilities]").replace(
        "{{SKILL_GUIDELINES}}", guidelines or "[Add guidelines]"
    ).replace("{{SKILL_EXAMPLES}}", examples or "[Add examples]")


def create_skill_directory(
        library: Library,
        name: str,
        template_content: Optional[str] = None
) -> Skill:
    """
    Create a new skill with SKILL.md and default metadata.

    Args:
        library: Library instance to add skill to
        name: Skill identifier (folder name)
        template_content: Custom content or uses create_skill_template

    Returns:
        The created Skill object
    """
    # Create the skill directory
    skill = library.add_skill(name, template_content or "")

    # If no content provided, generate a basic template
    if not (skill.path / "SKILL.md").exists():
        content = create_skill_template(
            name=name,
            description="A new skill",
            tags=["placeholder"],
            overview="Skill overview goes here.",
            capabilities="- Capability one\n- Capability two"
        )
        (skill.path / "SKILL.md").write_text(content, encoding="utf-8")

    # Create default metadata if doesn't exist
    meta_path = skill.path / "skill.meta.json"
    if not meta_path.exists():
        meta_data = {
            "keywords": [],  # Will be populated by bookkeeper later
            "files": [
                {
                    "name": "SKILL.md",
                    "subject": "main",
                    "level": 0.1
                }
            ],
            "variables": {}
        }
        with open(meta_path, 'w') as f:
            json.dump(meta_data, f, indent=2)

    # Reload skill to pick up new metadata
    return Skill(name=name, path=skill.path)


if __name__ == "__main__":
    import pprint

    # Demo usage
    lib = Library("./skills")

    # Create a test skill if directory doesn't exist
    test_dir = Path("./skills/test-skill")
    if not test_dir.exists():
        create_skill_directory(lib, "test-skill", template_content=None)

    # Discover skills
    lib.discover()
    print(f"Found {len(lib.all())} skill(s)")

    # Get the test skill
    test = lib.get("test-skill")
    if test:
        print("\nTest skill content:")
        print(test.content[:500] + "...")
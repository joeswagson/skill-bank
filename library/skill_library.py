"""
Skill parsing and library management.
"""

import json
import re
from dataclasses import dataclass, field
from enum import nonmember
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest import skip

SKILL_ENTRY = "SKILL.md"
META_ENTRY  = "skill.meta.json"

VAR_PATTERN = re.compile(r"\{\{(\w+)}}")


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class SkillFile:
    """A file declared in a skill's metadata."""
    parent: Skill            # Parent skill
    name: str               # Filename relative to the skill directory
    subject: str = ""       # Logical subject/category (filled by bookkeeper)
    level: float = 0.0      # Specialisation depth, 0.0–1.0 (filled by bookkeeper)

    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "subject": self.subject, "level": self.level}

    @classmethod
    def from_dict(cls, parent_skill:Skill, data: Dict[str, Any]) -> "SkillFile":
        return cls(
            parent  = parent_skill,
            name    = str(data.get("name", "")),
            subject = str(data.get("subject", "")),
            level   = float(data.get("level", 0.0)),
        )

    def content(self) -> str | None:
        return self.parent.content(self.name)

    def content_guaranteed(self) -> str:
        content = self.parent.content(self.name)
        if content is None:
            raise FileNotFoundError("Skill could not be loaded")

        return content

class SecurityViolation(Exception):
    def __init__(self,
                 bad_path:str   | None = None,
                 offender:Skill | None = None):

        path = bad_path if bad_path else "N/A"
        offender_name = offender.name if offender else "N/A"

        self.offender = offender
        self.bad_path = bad_path
        self.message = f"Skill {offender_name} attempted potential directory traversal (Path: {path})."

@dataclass
class Skill:
    """
    A single skill: its directory, metadata, and content.

    Variable substitution uses {{VARIABLE_NAME}} syntax; values are drawn
    from the ``variables`` mapping in skill.meta.json.
    SKILL.md is always treated as the primary descriptor and is loaded
    regardless of whether it appears in the files list.
    """

    name: str   # Folder name / skill identifier
    path: Path  # Absolute path to the skill directory

    # Metadata (populated from skill.meta.json on construction)
    keywords:  List[str]           = field(default_factory=list)
    files:     List[SkillFile]     = field(default_factory=list)
    variables: Dict[str, Any]      = field(default_factory=dict)

    # Internal read caches (not part of the public interface)
    _raw_cache: Dict[str, str]  = field(default_factory=dict, repr=False)
    _sub_cache: Dict[str, str]  = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        self.path = self.path.resolve()
        meta_path = self.path / META_ENTRY
        if meta_path.exists():
            self._load_meta(meta_path)

    def tool_repr(self):
        return {
            "name": self.name,
            "keywords": self.keywords,
            "extra_skills": [file.to_dict() for file in self.files]
        }

    # ------------------------------------------------------------------
    # Meta loading / saving
    # ------------------------------------------------------------------

    def _load_meta(self, meta_path: Path) -> None:
        try:
            data = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"Warning: could not parse meta for skill '{self.name}': {e}")
            return

        self.keywords = list(data.get("keywords", []))
        self.variables = dict(data.get("variables", {}))

        for entry in data.get("files", []):
            file_name = entry.get("name", "")
            # Security: reject absolute paths and directory traversal
            if not file_name or Path(file_name).is_absolute() or ".." in Path(file_name).parts:
                print(f"Warning: skipping unsafe file entry '{file_name}' in skill '{self.name}'")
                raise SecurityViolation(str(file_name), self)
                # continue
            # Confirm the resolved path is still inside the skill directory
            resolved = (self.path / file_name).resolve()
            if not str(resolved).startswith(str(self.path)):
                print(f"Warning: file '{file_name}' escapes skill directory — skipped")
                raise SecurityViolation(str(file_name), self)
                # continue
            self.files.append(SkillFile.from_dict(self, entry))

    def save_meta(self) -> None:
        """Persist current metadata back to skill.meta.json."""
        data = {
            "keywords":  self.keywords,
            "files":     [f.to_dict() for f in self.files],
            "variables": self.variables,
        }
        (self.path / META_ENTRY).write_text(
            json.dumps(data, indent=2), encoding="utf-8"
        )

    # ------------------------------------------------------------------
    # Validity
    # ------------------------------------------------------------------

    @property
    def is_valid(self) -> bool:
        """True when the primary SKILL.md descriptor exists on disk."""
        return (self.path / SKILL_ENTRY).exists()

    # ------------------------------------------------------------------
    # Content access
    # ------------------------------------------------------------------

    def _safe_read(self, file_name: str) -> Optional[str]:
        """
        Read a file relative to the skill directory with traversal guard.
        Returns raw text or None on any failure.
        """
        if not file_name or Path(file_name).is_absolute() or ".." in Path(file_name).parts:
            raise SecurityViolation(str(file_name), self)

        target = (self.path / file_name).resolve()
        if not str(target).startswith(str(self.path)):
            print(f"Security: '{file_name}' would escape skill directory")
            raise SecurityViolation(str(target), self)
            # return None
        try:
            return target.read_text(encoding="utf-8")
        except FileNotFoundError:
            return None
        except Exception as e:
            print(f"Error reading '{file_name}' in skill '{self.name}': {e}")
            return None

    def raw(self, file_name: str = SKILL_ENTRY) -> Optional[str]:
        """Return raw (unsubstituted) content of a skill file."""
        if file_name not in self._raw_cache:
            text = self._safe_read(file_name)
            if text is None:
                return None
            self._raw_cache[file_name] = text
        return self._raw_cache[file_name]

    def content(self, file_name: str = SKILL_ENTRY) -> Optional[str]:
        """
        Return content of a skill file with {{VARIABLE_NAME}} substitution
        applied using the skill's variables mapping.
        """
        if file_name not in self._sub_cache:
            text = self.raw(file_name)
            if text is None:
                return None
            self._sub_cache[file_name] = VAR_PATTERN.sub(
                lambda m: str(self.variables.get(m.group(1), m.group(0))),
                text,
            )
        return self._sub_cache[file_name]

    def invalidate_cache(self, file_name: Optional[str] = None) -> None:
        """Clear cached content. Pass a filename to clear just one entry."""
        if file_name:
            self._raw_cache.pop(file_name, None)
            self._sub_cache.pop(file_name, None)
        else:
            self._raw_cache.clear()
            self._sub_cache.clear()

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    def extra_files(self) -> List[SkillFile]:
        """Return declared files that are not SKILL.md."""
        return [f for f in self.files if f.name != SKILL_ENTRY]

    def __repr__(self) -> str:
        return f"Skill(name={self.name!r}, sub_skills={len(self.files)}, keywords={self.keywords})"


# ---------------------------------------------------------------------------
# Library
# ---------------------------------------------------------------------------

class Library:
    """
    Discovers and manages the skill library rooted at ``skills_dir``.

    A valid skill directory must contain at least one of SKILL.md or
    skill.meta.json at its top level.
    """

    def __init__(self, skills_dir: str | Path = "./skills") -> None:
        self.skills_dir = Path(skills_dir).resolve()
        self._cache: Dict[str, Skill] = {}
        self._discovered = False

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    @property
    def exists(self) -> bool:
        return self.skills_dir.is_dir()

    def discover(self) -> "Library":
        """Scan the skills directory and populate the internal cache."""
        self._cache.clear()
        self._discovered = True

        if not self.exists:
            print(f"Skills directory not found: {self.skills_dir}")
            return self

        for item in sorted(self.skills_dir.iterdir()):
            if not item.is_dir():
                continue
            if (item / SKILL_ENTRY).exists() or (item / META_ENTRY).exists():
                skill = Skill(name=item.name, path=item)
                self._cache[item.name] = skill

        return self

    def _ensure_discovered(self) -> None:
        if not self._discovered:
            self.discover()

    # ------------------------------------------------------------------
    # Access
    # ------------------------------------------------------------------

    def get(self, name: str) -> Optional[Skill]:
        """Return a skill by its folder name, or None."""
        self._ensure_discovered()
        return self._cache.get(name)

    def all(self) -> List[Skill]:
        """Return all discovered skills."""
        self._ensure_discovered()
        return list(self._cache.values())

    def valid(self) -> List[Skill]:
        """Return only skills that have a SKILL.md on disk."""
        return [s for s in self.all() if s.is_valid]

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search(self, *keywords: str) -> List[Skill]:
        """
        Return skills whose keyword list contains any of the given keywords
        (case-insensitive).
        """
        lower = [k.lower() for k in keywords]
        return [
            s for s in self.all()
            if any(k in lower for k in (kw.lower() for kw in s.keywords))
        ]

    # ------------------------------------------------------------------
    # Scaffolding
    # ------------------------------------------------------------------

    def scaffold(self, name: str, skill_md: str = "") -> Skill:
        """
        Create a new skill directory with a SKILL.md and default
        skill.meta.json.  If the directory already exists it is left
        intact; only missing files are created.

        Args:
            name:     Folder name for the new skill.
            skill_md: Initial content for SKILL.md.  If empty a minimal
                      placeholder is written instead.

        Returns:
            A freshly loaded Skill instance.
        """
        skill_path = self.skills_dir / name
        skill_path.mkdir(parents=True, exist_ok=True)

        # Write SKILL.md if absent
        md_path = skill_path / SKILL_ENTRY
        if not md_path.exists():
            md_path.write_text(
                skill_md or f"# {name}\n\n> Add skill description here.\n",
                encoding="utf-8",
            )

        # Write skill.meta.json if absent
        meta_path = skill_path / META_ENTRY
        if not meta_path.exists():
            default_meta: Dict[str, Any] = {
                "keywords": [],
                "files": [
                    {"name": SKILL_ENTRY, "subject": "main", "level": 0.0}
                ],
                "variables": {},
            }
            meta_path.write_text(json.dumps(default_meta, indent=2), encoding="utf-8")

        skill = Skill(name=name, path=skill_path)
        self._cache[name] = skill
        self._discovered = True
        return skill

    def __repr__(self) -> str:
        status = f"{len(self._cache)} skills" if self._discovered else "not yet discovered"
        return f"Library(skills_dir={str(self.skills_dir)!r}, {status})"
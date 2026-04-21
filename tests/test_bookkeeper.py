import unittest
from pathlib import Path
from library import Skill, SkillFile, Library
from library import bookkeeper

SKILL_NAME = "frontend-design"
SKILLS_DIR = Path(__file__).parent.parent / "skills"


def sample_skill() -> Skill:
    s = Library(SKILLS_DIR).get(SKILL_NAME)
    if s is None:
        raise RuntimeError(f"Skill '{SKILL_NAME}' not found in {SKILLS_DIR}")
    return s


def sample_skill_file(skill: Skill) -> SkillFile:
    if not skill.files:
        raise RuntimeError(f"Skill '{skill.name}' has no declared files")
    return skill.files[0]


class TestBookkeeper(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.skill = sample_skill()
        cls.skill_file = sample_skill_file(cls.skill)

    # ------------------------------------------------------------------
    # generate_keywords
    # ------------------------------------------------------------------

    def test_keywords_returns_list(self):
        result = bookkeeper.generate_keywords(self.skill)
        print(f"\n  keywords → {result}")
        self.assertIsInstance(result, list)

    def test_keywords_non_empty(self):
        result = bookkeeper.generate_keywords(self.skill)
        self.assertGreater(len(result), 0, f"Got empty list: {result!r}")

    def test_keywords_all_strings(self):
        result = bookkeeper.generate_keywords(self.skill)
        for kw in result:
            self.assertIsInstance(kw, str)
            self.assertTrue(kw.strip(), f"Blank keyword in result: {result!r}")

    # ------------------------------------------------------------------
    # analyze_subject
    # ------------------------------------------------------------------

    def test_subject_returns_string(self):
        result = bookkeeper.analyze_subject(self.skill_file)
        print(f"\n  subject → {result!r}")
        self.assertIsInstance(result, str)

    def test_subject_non_empty(self):
        result = bookkeeper.analyze_subject(self.skill_file)
        self.assertTrue(result.strip(), "Subject must not be blank")

    # ------------------------------------------------------------------
    # calculate_level
    # ------------------------------------------------------------------

    def test_level_returns_float(self):
        result = bookkeeper.calculate_level(self.skill_file)
        print(f"\n  level → {result}")
        self.assertIsInstance(result, float)

    def test_level_in_range(self):
        result = bookkeeper.calculate_level(self.skill_file)
        self.assertGreaterEqual(result, 0.0)
        self.assertLessEqual(result, 1.0)


    # ------------------------------------------------------------------
    # oneshot
    # ------------------------------------------------------------------

    def test_all(self):
        self.test_keywords_returns_list()
        subject, level = bookkeeper.analyze_subject_and_level(self.skill_file)

        print(f"\n  subject → {subject!r}")
        print(f"\n  level   → {level}") # the ai arrows are killing me lmao

        self.assertIsInstance(subject, str)
        self.assertIsInstance(level, float)

    def test_subject_level_oneshot(self):
        subject, level = bookkeeper.analyze_subject_and_level(self.skill_file)

        print(f"\n  subject → {subject!r}")
        print(f"\n  level   → {level}") # the ai arrows are killing me lmao

        self.assertIsInstance(subject, str)
        self.assertIsInstance(level, float)

    # ------------------------------------------------------------------
    # update_skill_metadata  (integration)
    # ------------------------------------------------------------------

    def test_skill_metadata(self):
        self.test_update_writes_keywords()
        self.test_update_writes_file_metadata()

    def test_update_writes_keywords(self):
        bookkeeper.update_skill_metadata(self.skill)
        print(f"\n  keywords (post-update) → {self.skill.keywords}")
        self.assertIsInstance(self.skill.keywords, list)
        self.assertGreater(len(self.skill.keywords), 0)

    def test_update_writes_file_metadata(self):
        bookkeeper.update_skill_metadata(self.skill)
        for f in self.skill.files:
            print(f"\n  [{f.name}] subject={f.subject!r}  level={f.level}")
            with self.subTest(file=f.name):
                self.assertIsInstance(f.subject, str)
                self.assertTrue(f.subject.strip())
                self.assertIsInstance(f.level, float)
                self.assertGreaterEqual(f.level, 0.0)
                self.assertLessEqual(f.level, 1.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
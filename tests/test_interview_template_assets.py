import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class InterviewTemplateAssetTests(unittest.TestCase):
    def test_seeker_interview_page_loads_dialog_javascript(self) -> None:
        template = (
            PROJECT_ROOT / "src" / "templates" / "seeker_interviews.html"
        ).read_text()

        self.assertIn("{% block extra_js %}", template)
        self.assertIn("js/interviews.js", template)
        self.assertIn("data-open-dialog", template)

    def test_interview_javascript_opens_and_closes_reason_dialog(self) -> None:
        script = (PROJECT_ROOT / "src" / "static" / "js" / "interviews.js").read_text()

        self.assertIn("[data-open-dialog]", script)
        self.assertIn("showModal", script)
        self.assertIn("[data-close-dialog]", script)

    def test_interview_reason_dialog_is_centred_in_viewport(self) -> None:
        stylesheet = (
            PROJECT_ROOT / "src" / "static" / "css" / "interviews.css"
        ).read_text()

        self.assertIn(".interview-reason-dialog[open]", stylesheet)
        self.assertIn("inset: 50% auto auto 50%;", stylesheet)
        self.assertIn("transform: translate(-50%, -50%);", stylesheet)


if __name__ == "__main__":
    unittest.main()

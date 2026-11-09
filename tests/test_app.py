import html
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from llm_client import GenerationError

APP = Path(__file__).parents[1] / "app.py"
QUESTIONS = ["What is a Python generator?", "How would you debug a slow API?", "How do you respond to feedback?"]


class AppFlowTests(unittest.TestCase):
    def setUp(self):
        environment = patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key", "INTERVIEW_API_ENABLED": "1"})
        environment.start()
        self.addCleanup(environment.stop)

    def test_input_guard_prevents_api_call(self):
        with patch("llm_client.generate_questions") as generate:
            app = AppTest.from_file(str(APP)).run(timeout=10)
            app.button[0].click().run()
            self.assertEqual(len(app.warning), 1)
            self.assertEqual(len(app.exception), 0)
            generate.assert_not_called()

    def test_generation_requires_submit_and_failure_preserves_previous_result(self):
        with patch("llm_client.generate_questions", return_value=QUESTIONS) as generate:
            app = AppTest.from_file(str(APP)).run(timeout=10)
            app.text_input[0].set_value("Python Developer")
            app.number_input[0].set_value(100)
            generate.assert_not_called()
            app.button[0].click().run()
            self.assertEqual(len(app.get("html")), 3)
            generate.assert_called_once_with("Python Developer", 100)
            self.assertTrue(any("Generated for Python Developer" in caption.value for caption in app.caption))
            app.text_area[0].set_value("My draft answer.").run()
            app.run()
            generate.assert_called_once()
            for action in ("questions", "hint", "feedback"):
                app.session_state[f"last_attempt_{action}"] = float("-inf")
            generate.side_effect = GenerationError("The connection failed. Please try again.")
            app.button[0].click().run()
            self.assertEqual(len(app.error), 1)
            self.assertEqual(len(app.get("html")), 3)
            self.assertEqual(len(app.text_area), 3)
            self.assertEqual(app.text_area[0].value, "My draft answer.")
            self.assertEqual(app.text_input[0].value, "Python Developer")
            self.assertEqual(len(app.exception), 0)

    def test_repeated_submit_is_limited(self):
        with patch("llm_client.generate_questions", return_value=QUESTIONS) as generate:
            app = AppTest.from_file(str(APP)).run(timeout=10)
            app.text_input[0].set_value("Python Developer")
            app.button[0].click().run()
            app.button[0].click().run()
            generate.assert_called_once()
            self.assertIn("3 seconds", app.warning[0].value)

    def test_hint_is_cached_keeps_drafts_and_uses_generated_context(self):
        hint = "Start with the problem that lazy iteration solves."
        with patch("llm_client.generate_questions", return_value=QUESTIONS) as generate, \
                patch("llm_client.generate_hint", return_value=hint) as get_hint:
            app = AppTest.from_file(str(APP)).run(timeout=10)
            app.text_input[0].set_value("Python Developer")
            app.button[0].click().run()
            self.assertEqual(len(app.button), 7)
            get_hint.assert_not_called()
            app.text_area[0].set_value("My private draft.").run()
            app.text_input[0].set_value("Data Analyst")
            for action in ("questions", "hint", "feedback"):
                app.session_state[f"last_attempt_{action}"] = float("-inf")
            app.button(key="hint_button_1").click().run()
            get_hint.assert_called_once_with("Python Developer", 0, QUESTIONS[0])
            self.assertEqual(app.text_area[0].value, "My private draft.")
            self.assertTrue(app.button(key="hint_button_1").disabled)
            self.assertIn(hint, [html.unescape(item.proto.body.split(">", 1)[1].rsplit("</div>", 1)[0]) for item in app.get("html")])
            app.text_area[1].set_value("Another draft.").run()
            get_hint.assert_called_once()
            generate.assert_called_once()
            for action in ("questions", "hint", "feedback"):
                app.session_state[f"last_attempt_{action}"] = float("-inf")
            app.button[0].click().run()
            self.assertNotIn("hint_1", app.session_state)
            self.assertFalse(app.button(key="hint_button_1").disabled)
            self.assertEqual(app.text_area[0].value, "")
            self.assertEqual(len(app.exception), 0)

    def test_hint_failure_preserves_questions_drafts_and_can_be_retried(self):
        with patch("llm_client.generate_questions", return_value=QUESTIONS), \
                patch("llm_client.generate_hint", side_effect=[GenerationError("Please try again later."), "Choose one real example."]) as get_hint:
            app = AppTest.from_file(str(APP)).run(timeout=10)
            app.text_input[0].set_value("Python Developer")
            app.button[0].click().run()
            app.text_area[2].set_value("A private experience.").run()
            for action in ("questions", "hint", "feedback"):
                app.session_state[f"last_attempt_{action}"] = float("-inf")
            app.button(key="hint_button_3").click().run()
            self.assertEqual(len(app.warning), 1)
            self.assertEqual(app.text_area[2].value, "A private experience.")
            self.assertEqual(len(app.get("html")), 3)
            self.assertNotIn("hint_3", app.session_state)
            app.button(key="hint_button_3").click().run()
            get_hint.assert_called_once()
            self.assertIn("3 seconds", app.warning[0].value)
            for action in ("questions", "hint", "feedback"):
                app.session_state[f"last_attempt_{action}"] = float("-inf")
            app.button(key="hint_button_3").click().run()
            self.assertEqual(get_hint.call_count, 2)
            self.assertEqual(app.text_area[2].value, "A private experience.")
            self.assertEqual(len(app.exception), 0)

    def test_question_cooldown_allows_immediate_hint(self):
        with patch("llm_client.generate_questions", return_value=QUESTIONS), \
                patch("llm_client.generate_hint", return_value="Consider one relevant example from your work or studies.") as get_hint:
            app = AppTest.from_file(str(APP)).run(timeout=10)
            app.text_input[0].set_value("Python Developer")
            app.button[0].click().run()
            app.button(key="hint_button_2").click().run()
            get_hint.assert_called_once_with("Python Developer", 0, QUESTIONS[1])
            self.assertEqual(len(app.warning), 0)

    def test_answers_are_optional_and_edits_preserve_drafts_without_extra_api_calls(self):
        with patch("llm_client.generate_questions", return_value=QUESTIONS) as generate:
            app = AppTest.from_file(str(APP)).run(timeout=10)
            app.text_input[0].set_value("Python Developer")
            app.button[0].click().run()
            self.assertEqual(len(app.text_area), 3)
            self.assertTrue(all(answer.value == "" for answer in app.text_area))
            app.text_area[0].set_value("A generator yields values lazily.").run()
            app.text_area[1].set_value("I would measure latency first.").run()
            app.run()
            self.assertEqual(app.text_area[0].value, "A generator yields values lazily.")
            self.assertEqual(app.text_area[1].value, "I would measure latency first.")
            self.assertEqual(app.text_area[2].value, "")
            self.assertEqual(len(app.exception), 0)
            generate.assert_called_once_with("Python Developer", 0)

    def test_new_questions_reset_old_answers_but_rejected_requests_preserve_them(self):
        new_questions = ["What is a SQL join?", "How would you check a report?", "How did you resolve a data issue?"]
        with patch("llm_client.generate_questions", side_effect=[QUESTIONS, new_questions]) as generate:
            app = AppTest.from_file(str(APP)).run(timeout=10)
            app.text_input[0].set_value("Python Developer")
            app.button[0].click().run()
            app.text_area[0].set_value("Old Python answer.").run()
            app.button[0].click().run()
            self.assertIn("3 seconds", app.warning[0].value)
            self.assertEqual(app.text_area[0].value, "Old Python answer.")
            app.text_input[0].set_value("")
            app.button[0].click().run()
            self.assertEqual(app.text_area[0].value, "Old Python answer.")
            generate.assert_called_once()
            for action in ("questions", "hint", "feedback"):
                app.session_state[f"last_attempt_{action}"] = float("-inf")
            app.text_input[0].set_value("Data Analyst")
            app.button[0].click().run()
            self.assertEqual([answer.value for answer in app.text_area], ["", "", ""])
            self.assertIn("What is a SQL join?", app.get("html")[0].proto.body)
            self.assertTrue(any("Generated for Data Analyst" in caption.value for caption in app.caption))
            self.assertEqual(generate.call_count, 2)
            self.assertEqual(len(app.exception), 0)

    def test_feedback_is_explicit_cached_and_invalidated_when_answer_changes(self):
        feedback = "Your example is relevant. Explain the result more clearly."
        with patch("llm_client.generate_questions", return_value=QUESTIONS), \
                patch("llm_client.generate_feedback", return_value=feedback) as review:
            app = AppTest.from_file(str(APP)).run(timeout=10)
            app.text_input[0].set_value("Python Developer")
            app.button[0].click().run()
            self.assertTrue(app.button(key="feedback_button_1").disabled)
            app.text_area[0].set_value("My first answer.").run()
            app.text_area[1].set_value("Another private draft.").run()
            review.assert_not_called()
            for action in ("questions", "hint", "feedback"):
                app.session_state[f"last_attempt_{action}"] = float("-inf")
            app.button(key="feedback_button_1").click().run()
            review.assert_called_once_with("Python Developer", 0, QUESTIONS[0], "My first answer.")
            self.assertIn(feedback, [html.unescape(item.proto.body.split(">", 1)[1].rsplit("</div>", 1)[0]) for item in app.get("html")])
            self.assertTrue(app.button(key="feedback_button_1").disabled)
            app.text_area[1].set_value("Edited other answer.").run()
            self.assertIn(feedback, [html.unescape(item.proto.body.split(">", 1)[1].rsplit("</div>", 1)[0]) for item in app.get("html")])
            review.assert_called_once()
            app.text_area[0].set_value("My revised answer.").run()
            self.assertNotIn(feedback, [html.unescape(item.proto.body.split(">", 1)[1].rsplit("</div>", 1)[0]) for item in app.get("html")])
            self.assertFalse(app.button(key="feedback_button_1").disabled)
            self.assertEqual(app.text_area[1].value, "Edited other answer.")
            self.assertEqual(len(app.exception), 0)

    def test_feedback_failure_and_cooldown_keep_all_drafts_and_allow_retry(self):
        with patch("llm_client.generate_questions", return_value=QUESTIONS), \
                patch("llm_client.generate_feedback", side_effect=[GenerationError("Please try again later."), "Good example. Explain the result."]) as review:
            app = AppTest.from_file(str(APP)).run(timeout=10)
            app.text_input[0].set_value("Python Developer")
            app.button[0].click().run()
            app.text_area[0].set_value("My answer.").run()
            app.button(key="feedback_button_1").click().run()
            review.assert_called_once()
            app.button(key="feedback_button_1").click().run()
            review.assert_called_once()
            self.assertIn("3 seconds", app.warning[0].value)
            self.assertEqual(app.text_area[0].value, "My answer.")
            self.assertEqual(len(app.get("html")), 3)
            self.assertFalse(app.button(key="feedback_button_1").disabled)
            for action in ("questions", "hint", "feedback"):
                app.session_state[f"last_attempt_{action}"] = float("-inf")
            app.button(key="feedback_button_1").click().run()
            self.assertEqual(review.call_count, 2)
            self.assertIn("feedback_1", app.session_state)
            for action in ("questions", "hint", "feedback"):
                app.session_state[f"last_attempt_{action}"] = float("-inf")
            app.button[0].click().run()
            self.assertNotIn("feedback_1", app.session_state)
            self.assertEqual(app.text_area[0].value, "")
            self.assertEqual(len(app.exception), 0)

    def test_generated_html_and_links_render_as_inert_text(self):
        question = '<script>alert(1)</script> [link](https://example.com)'
        with patch("llm_client.generate_questions", return_value=[question, QUESTIONS[1], QUESTIONS[2]]):
            app = AppTest.from_file(str(APP)).run(timeout=10)
            app.text_input[0].set_value("Python Developer")
            app.button[0].click().run()
            body = app.get("html")[0].proto.body
            self.assertIn("&lt;script&gt;", body)
            self.assertNotIn("<script>", body)
            self.assertNotIn("<a ", body)
            self.assertIn("[link](https://example.com)", body)

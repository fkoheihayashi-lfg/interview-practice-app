import html
import os
import time

import streamlit as st

from guards import InputError, validate_input
from llm_client import GenerationError, generate_feedback, generate_hint, generate_questions

COOLDOWN_SECONDS = 3


def display_text(text: str) -> None:
    # Escape generated content and prevent Markdown interpretation or active links.
    safe_text = html.escape(text).replace("\n", "<br>")
    st.html(f'<div style="white-space: pre-wrap; overflow-wrap: anywhere">{safe_text}</div>')


def main():
    st.set_page_config(page_title="Interview Practice", page_icon="💬")
    st.title("Interview Practice")
    st.write("Get 3 interview questions tailored to your target role and relevant experience.")

    ready = bool(os.environ.get("OPENROUTER_API_KEY", "").strip()) and os.environ.get(
        "INTERVIEW_API_ENABLED", ""
    ) == "1"
    if not ready:
        st.info("Question generation is not available yet. You can still enter your practice details.")

    with st.form("practice_details"):
        st.subheader("1. Set your target")
        job_title = st.text_input("Job title", placeholder="e.g., Python Developer", max_chars=120)
        years = st.number_input(
            "Years of relevant experience", min_value=0, value=0, step=1,
            help="Use 0 for your first role in this field. There is no app-defined upper limit; check for typing mistakes before generating questions.",
        )
        st.caption("Generating a new set replaces your current questions, hints, feedback and answer drafts.")
        submitted = st.form_submit_button("Generate 3 questions", type="primary")

    if submitted:
        try:
            role, experience = validate_input(job_title, years)
        except InputError as error:
            st.warning(str(error))
        else:
            elapsed = time.monotonic() - st.session_state.get("last_attempt_questions", float("-inf"))
            if not ready:
                st.info("Generation is not set up yet. Your practice details have been kept.")
            elif elapsed < COOLDOWN_SECONDS:
                st.warning("Please wait 3 seconds before repeating this action, then try again.")
            else:
                st.session_state["last_attempt_questions"] = time.monotonic()
                try:
                    with st.spinner("Creating your practice questions…"):
                        questions = generate_questions(role, experience)
                except (GenerationError, InputError) as error:
                    st.error(str(error))
                else:
                    for number in range(1, 4):
                        st.session_state.pop(f"answer_{number}", None)
                        st.session_state.pop(f"hint_{number}", None)
                        st.session_state.pop(f"feedback_{number}", None)
                    st.session_state["practice_result"] = (role, experience, questions)

    result = st.session_state.get("practice_result")
    if result:
        role, experience, questions = result
        st.divider()
        st.subheader("2. Practise your answers")
        st.caption(f"Generated for {role} · {experience} year(s) of relevant experience")
        st.write("Answer aloud or write a draft. Use a hint if you need a starting point.")
        with st.expander("How hints, feedback and drafts work"):
            st.write("Answers are optional session drafts and are cleared when this session ends. Only Get feedback sends the selected answer to AI; typing and hint requests do not. Feedback is practice guidance, not a grade.")
            st.write("Each action has its own 3-second wait before repeating it. You can move straight from questions to a hint or feedback. Retrieved hints stay with their question. Editing an answer clears its old feedback; a new question set clears all drafts, hints and feedback.")
        for number, question in enumerate(questions, start=1):
            with st.container(border=True):
                st.subheader(f"Question {number} of {len(questions)}")
                display_text(question)
                hint_key = f"hint_{number}"
                if st.button(
                    "Hint received" if hint_key in st.session_state else "Get a hint",
                    key=f"hint_button_{number}",
                    type="secondary" if hint_key in st.session_state else "primary",
                    disabled=not ready or hint_key in st.session_state,
                ):
                    elapsed = time.monotonic() - st.session_state.get("last_attempt_hint", float("-inf"))
                    if elapsed < COOLDOWN_SECONDS:
                        st.warning("Please wait 3 seconds before repeating this action, then try again.")
                    else:
                        st.session_state["last_attempt_hint"] = time.monotonic()
                        try:
                            with st.spinner("Getting a short hint…"):
                                st.session_state[hint_key] = generate_hint(role, experience, question)
                        except (GenerationError, InputError) as error:
                            st.warning(str(error))
                        else:
                            st.rerun()
                if hint_key in st.session_state:
                    with st.container(border=True):
                        st.markdown("**Hint**")
                        display_text(st.session_state[hint_key])
                answer = st.text_area(
                    f"Your answer {number} (optional)",
                    key=f"answer_{number}",
                    placeholder="Write your answer here, or practise aloud.",
                    height=150,
                    max_chars=4000,
                )
                feedback_key = f"feedback_{number}"
                saved_feedback = st.session_state.get(feedback_key)
                if saved_feedback and saved_feedback[0] != answer.strip():
                    st.session_state.pop(feedback_key, None)
                    saved_feedback = None
                st.caption("Get feedback sends this answer to AI. Avoid personal or confidential information.")
                if st.button(
                    "Feedback received" if saved_feedback else "Get feedback",
                    key=f"feedback_button_{number}",
                    type="secondary" if saved_feedback else "primary",
                    disabled=not ready or not answer.strip() or bool(saved_feedback),
                ):
                    elapsed = time.monotonic() - st.session_state.get("last_attempt_feedback", float("-inf"))
                    if elapsed < COOLDOWN_SECONDS:
                        st.warning("Please wait 3 seconds before repeating this action, then try again.")
                    else:
                        st.session_state["last_attempt_feedback"] = time.monotonic()
                        try:
                            with st.spinner("Reviewing your answer…"):
                                feedback = generate_feedback(role, experience, question, answer)
                        except (GenerationError, InputError) as error:
                            st.warning(str(error))
                        else:
                            st.session_state[feedback_key] = (answer.strip(), feedback)
                            st.rerun()
                if saved_feedback:
                    with st.container(border=True):
                        st.markdown("**Feedback**")
                        display_text(saved_feedback[1])

        st.caption("Ready for another round? Update your target above and generate a new set.")


if __name__ == "__main__":
    main()

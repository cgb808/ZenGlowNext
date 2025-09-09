from app.central.control import UserProfile, SessionState, build_tutor_prompt


def test_build_tutor_prompt_basic():
    user = UserProfile(name="Jane Doe", goals="Improve algebra grade", learning_style="Prefers step-by-step examples")
    session = SessionState(
        last_interaction_minutes=25,
        last_agent="TutoringAgent_Math",
        last_topic_summary="Discussing how to solve quadratic equations.",
        last_ai_response="So, the next step is to use the quadratic formula to solve for x.",
    )
    insights = [
        "Jane previously struggled with factoring polynomials, which is a related concept.",
        "Successfully solved a similar problem two days ago (mission_id: 456).",
    ]
    prompt = build_tutor_prompt(
        user_prompt="Hey, I'm back. Can you remind me of the formula?",
        user=user,
        session=session,
        insights=insights,
        system_instructions="YOU ARE A HELPFUL AI TUTOR",
    )
    assert "--- USER CHEAT SHEET (BRIEFING DOCUMENT) ---" in prompt
    assert "Jane Doe" in prompt
    assert "quadratic equations" in prompt
    assert "[USER'S NEW PROMPT]" in prompt
    assert "step-by-step" in prompt
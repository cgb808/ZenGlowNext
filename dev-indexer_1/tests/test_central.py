from app.central.control import UserProfile, SessionState, build_cheat_sheet


def test_build_cheat_sheet_basic():
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

    cheat = build_cheat_sheet(user=user, session=session, insights=insights)

    assert "--- SYSTEM INSTRUCTIONS:" in cheat
    assert "--- USER CHEAT SHEET" in cheat
    assert "User: Jane Doe" in cheat
    assert "Known Goals: Improve algebra grade" in cheat
    assert "Learning Style: Prefers step-by-step examples" in cheat
    assert "Time Since Last Interaction: 25 minutes" in cheat
    assert "Last Topic: Discussing how to solve quadratic equations." in cheat
    assert "Your Last Response: \"So, the next step is to use the quadratic formula to solve for x.\"" in cheat
    assert "Insight: Jane previously struggled with factoring polynomials" in cheat
    assert "Insight: Successfully solved a similar problem" in cheat

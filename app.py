import os
from flask import Flask, render_template, request, jsonify
from database import init_db, save_conversation, get_history, save_advisor_setting
from advisors import get_advisors, get_advisor_response, get_ceo_decision, get_all_advisor_configs

app = Flask(__name__)


@app.route("/")
def home():
    """Render main page with chat history."""
    history = get_history(limit=10)
    return render_template("index.html", history=history)


@app.route("/ask", methods=["POST"])
def ask_board():
    """Process question through all advisors then CEO."""
    question = request.json.get("question")

    if not question:
        return jsonify({"error": "No question provided"}), 400

    try:
        # Get responses from all advisors (now loads from DB with fallback)
        advisors = get_advisors()
        advisor_responses = []
        for advisor in advisors:
            response = get_advisor_response(advisor, question)
            advisor_responses.append({
                "name": advisor["name"],
                "role": advisor["role"],
                "model": advisor["model"],
                "response": response
            })

        # Get CEO's final decision
        ceo_decision = get_ceo_decision(advisor_responses, question)

        # Save to database
        conversation_id = save_conversation(question, advisor_responses, ceo_decision)

        return jsonify({
            "conversation_id": conversation_id,
            "question": question,
            "advisors": advisor_responses,
            "ceo_decision": ceo_decision
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/history")
def history():
    """Get conversation history."""
    conversations = get_history(limit=20)
    return jsonify(conversations)


@app.route("/settings", methods=["GET"])
def get_settings():
    """Get all advisor configurations."""
    configs = get_all_advisor_configs()
    return jsonify(configs)


@app.route("/settings/<advisor_key>", methods=["POST"])
def update_setting(advisor_key):
    """Update a single advisor's configuration."""
    if advisor_key not in ["cfo", "cto", "cmo", "ceo"]:
        return jsonify({"error": "Invalid advisor key"}), 400

    data = request.json
    name = data.get("name")
    role = data.get("role")
    model = data.get("model")
    system_prompt = data.get("system_prompt")

    if not all([name, role, model, system_prompt]):
        return jsonify({"error": "Missing required fields"}), 400

    save_advisor_setting(advisor_key, name, role, model, system_prompt)

    return jsonify({"success": True, "message": f"{advisor_key.upper()} settings updated"})


if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)

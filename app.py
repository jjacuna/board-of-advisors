import os
from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
from database import (
    init_db, save_conversation, get_history, save_advisor_setting,
    save_document, update_document_status, get_documents, delete_document
)
from advisors import get_advisors, get_advisor_response, get_ceo_decision, get_all_advisor_configs
from knowledge import process_document, delete_document_vectors, get_context_for_query, check_knowledge_base_configured

app = Flask(__name__)

# File upload configuration
UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"pdf", "txt", "md", "docx"}
MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10MB max file size

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH

# Ensure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


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
        # Get RAG context if knowledge base is configured
        context = ""
        if check_knowledge_base_configured():
            try:
                context = get_context_for_query(question)
            except Exception as e:
                print(f"RAG context retrieval failed: {e}")

        # Get responses from all advisors (now loads from DB with fallback)
        advisors = get_advisors()
        advisor_responses = []
        for advisor in advisors:
            response = get_advisor_response(advisor, question, context)
            advisor_responses.append({
                "name": advisor["name"],
                "role": advisor["role"],
                "model": advisor["model"],
                "response": response
            })

        # Get CEO's final decision
        ceo_decision = get_ceo_decision(advisor_responses, question, context)

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


@app.route("/documents", methods=["GET"])
def list_documents():
    """Get all uploaded documents."""
    documents = get_documents()
    return jsonify(documents)


@app.route("/documents/upload", methods=["POST"])
def upload_document():
    """Upload and process a document for the knowledge base."""
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]

    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": f"File type not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"}), 400

    try:
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(file_path)

        file_size = os.path.getsize(file_path)
        file_type = filename.rsplit(".", 1)[1].lower()

        # Save document metadata
        doc_id = save_document(filename, file_type, file_size)

        # Process document (extract text, chunk, embed, store in Pinecone)
        chunk_count = process_document(doc_id, file_path, filename)

        # Update status to ready
        update_document_status(doc_id, "ready", chunk_count)

        # Clean up uploaded file
        os.remove(file_path)

        return jsonify({
            "success": True,
            "document_id": doc_id,
            "filename": filename,
            "chunk_count": chunk_count,
            "message": f"Document processed successfully with {chunk_count} chunks"
        })

    except Exception as e:
        # Update status to failed if we have a doc_id
        if "doc_id" in locals():
            update_document_status(doc_id, "failed")
        return jsonify({"error": str(e)}), 500


@app.route("/documents/<int:doc_id>", methods=["DELETE"])
def remove_document(doc_id):
    """Delete a document from the knowledge base."""
    try:
        # Delete vectors from Pinecone
        delete_document_vectors(doc_id)

        # Delete from database
        deleted = delete_document(doc_id)

        if not deleted:
            return jsonify({"error": "Document not found"}), 404

        return jsonify({"success": True, "message": "Document deleted"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)

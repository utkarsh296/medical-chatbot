from flask import Flask, render_template, jsonify, request, redirect, url_for
from flask_cors import CORS
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage, AIMessage
import os
import requests

# Initialize Flask
app = Flask(__name__)
CORS(app)

# Load environment variables
load_dotenv()

# Clerk keys
CLERK_FRONTEND_API = os.getenv("CLERK_FRONTEND_API")
CLERK_API_KEY = os.getenv("CLERK_API_KEY")
CLERK_PUBLISHABLE_KEY = os.getenv("CLERK_PUBLISHABLE_KEY")

# OpenAI setup
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
llm = ChatOpenAI(openai_api_key=OPENAI_API_KEY, model="gpt-3.5-turbo")

# --------- Clerk Authentication Helper --------- #
def verify_clerk_token(token):
    """Verify a Clerk session token."""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        res = requests.get("https://api.clerk.dev/v1/me", headers=headers)
        return res.status_code == 200
    except Exception as e:
        print("❌ Clerk verification error:", e)
        return False

# --------- Routes --------- #
@app.route("/")
def home():
    return redirect(url_for("chat_page"))

@app.route("/chat")
def chat_page():
    return render_template("chat.html", clerk_publishable_key=CLERK_PUBLISHABLE_KEY)

@app.route("/api/chat", methods=["POST"])
def chat():
    try:
        # Verify Clerk token
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"reply": "Unauthorized — missing Clerk token."}), 401

        token = auth_header.split(" ")[1]
        if not verify_clerk_token(token):
            return jsonify({"reply": "Invalid or expired Clerk token."}), 403

        # Get message
        data = request.get_json()
        user_message = data.get("message", "").strip()

        if not user_message:
            return jsonify({"reply": "Please enter a valid question."})

        # Create prompt
        messages = [
            SystemMessage(content=(
                "You are MedAssist, a trusted medical assistant chatbot. "
                "Provide accurate, safe, non-diagnostic medical information, "
                "and suggest seeing a doctor when appropriate."
            )),
            HumanMessage(content=user_message)
        ]

        # Get response from OpenAI
        ai_response = llm.invoke(messages)

        # Safely extract reply text
        reply_text = getattr(ai_response, "content", None)
        if not reply_text:
            reply_text = getattr(ai_response, "text", None)
        if not reply_text:
            reply_text = str(ai_response)

        print(f"✅ AI Reply: {reply_text}")  # Debugging output

        return jsonify({"reply": reply_text})

    except Exception as e:
        print("❌ Error in /api/chat:", str(e))
        return jsonify({"reply": f"Internal Server Error: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)

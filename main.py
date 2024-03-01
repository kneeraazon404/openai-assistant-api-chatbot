import logging
from datetime import datetime
from functools import wraps
from zoneinfo import ZoneInfo
import openai
from flask import (
    Flask,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
import json
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

from utils import get_response

api_key = "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"
assistant_id = "asst_Z7lAA5mIhUcOSOWzSaycOdAK"


# Initialize the OpenAI client with your API key.
client = openai.OpenAI(api_key=api_key)
app = Flask(__name__)
app.secret_key = "fo4MLbFiPoL09nByPvQjT3BlbkFJVk2GyRwrNZihOKFKAtxF"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///users.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)


# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    threads = db.relationship("ChatThread", backref="user", lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class ChatThread(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    thread_id = db.Column(db.String(255), nullable=True)  # Store OpenAI's thread ID
    messages = db.relationship("ChatMessage", backref="thread", lazy=True)


class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    sender = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    thread_id = db.Column(db.Integer, db.ForeignKey("chat_thread.id"), nullable=False)


with app.app_context():
    db.create_all()
logging.info("Database and tables created.")


# Helper functions
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "logged_in" not in session:
            return redirect(url_for("login", next=request.url))
        return f(*args, **kwargs)

    return decorated_function


# def start_new_chat_thread(
#     user_id,
#     user_name,
#     part_of_day,
#     query,
# ):
#     # Check if a thread for this user already exists
#     existing_thread = ChatThread.query.filter_by(
#         user_id=user_id,
#     ).first()

#     if not existing_thread:
#         # Only create a new thread with OpenAI if no existing thread is found for this user
#         # Assuming `create_thread` interacts with OpenAI API and returns an OpenAI thread ID
#         thread_id = create_thread(
#             user_name,
#             part_of_day,
#             query,
#         )

#         # Create a new ChatThread instance in your database with the OpenAI thread ID
#         new_thread = ChatThread(
#             user_id=user_id,
#             thread_id=thread_id,
#         )
#         db.session.add(new_thread)
#         db.session.commit()

#         # Return the internal database ID of the new thread
#         return new_thread.thread_id
#     else:
#         # If an existing thread is found, return its internal database ID
#         return existing_thread.thread_id


def save_chat_message(thread_id, text, sender):
    # Ensure text is a single string
    if isinstance(text, list):
        text = " ".join(text)  # Join list elements into a single string
    message = ChatMessage(
        thread_id=thread_id,
        text=text,
        sender=sender,
    )
    db.session.add(message)
    db.session.commit()


def save_or_update_assistant_message(thread_id, text):
    # Convert list to string if `text` is a list
    if isinstance(text, list):
        # Join the list elements into a single string. You can adjust the separator as needed.
        text = " ".join(text)

    # Try to find the last assistant message in the thread
    last_assistant_message = (
        ChatMessage.query.filter_by(thread_id=thread_id, sender="assistant")
        .order_by(ChatMessage.created_at.desc())
        .first()
    )

    if last_assistant_message:
        # If an existing message is found, update it with the new text
        last_assistant_message.text = text
        last_assistant_message.created_at = datetime.utcnow()
    else:
        # If no previous message from the assistant exists, create a new entry
        new_message = ChatMessage(
            thread_id=thread_id,
            text=text,
            sender="assistant",
            created_at=datetime.utcnow(),
        )
        db.session.add(new_message)

    db.session.commit()


# Ensure the database and the tables are created.
with app.app_context():
    db.create_all()
logging.info("Database and tables created.")


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "logged_in" not in session:
            return redirect(url_for("login", next=request.url))
        return f(*args, **kwargs)

    return decorated_function


@app.route("/")
def home():
    return render_template("index.html", user_logged_in="logged_in" in session)


#  Endpoint for login
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        login = request.form["login"]
        password = request.form["password"]
        # Check if login is an email or username
        user = User.query.filter(
            (User.username == login) | (User.email == login)
        ).first()

        if user and user.check_password(password):
            session["logged_in"] = True
            session["username"] = user.username  # Store the username in the session
            return redirect(url_for("home"))
        else:
            flash("Invalid login credentials")
    return render_template("login.html")


#  Endpoing for signup
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        email = request.form["email"]
        username = request.form["username"]
        password = request.form["password"]
        first_name = request.form["first_name"]
        last_name = request.form["last_name"]

        existing_user = User.query.filter(
            (User.username == username) | (User.email == email)
        ).first()
        if existing_user is None:
            new_user = User(
                email=email,
                username=username,
                first_name=first_name,
                last_name=last_name,
            )
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()
            flash("Registration successful. Please log in.")
            return redirect(url_for("login"))
        else:
            flash("Username or email already exists")
    return render_template("signup.html")


# Endpoint for profile
@app.route("/profile")
@login_required
def profile():
    user = User.query.filter_by(username=session["username"]).first()
    if user:
        return render_template(
            "profile.html",
            email=user.email,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            user_logged_in="logged_in" in session,
        )
    else:
        flash("User not found.")
        return redirect(url_for("login"))


# Endpoint for logout
@app.route("/logout")
def logout():
    session.pop("logged_in", None)
    session.pop("username", None)  # Clear the username from the session
    return redirect(url_for("home"))


def get_or_create_thread(user_id):
    thread = ChatThread.query.filter_by(user_id=user_id).first()
    if thread is None:
        thread = ChatThread(user_id=user_id)
        db.session.add(thread)
        db.session.commit()
    return thread.id


def get_chat_history_concatenated(thread_id):
    # Fetch messages ordered by sender or creation time
    messages_query = (
        ChatMessage.query.filter_by(thread_id=thread_id)
        .order_by(ChatMessage.sender, ChatMessage.created_at.asc())
        .all()
    )

    # Initialize a dictionary to hold concatenated messages for each sender
    messages_per_sender = {}

    # Iterate through messages to concatenate them by sender
    for message in messages_query:
        # If the sender is not already in the dictionary, add them with the current message
        if message.sender not in messages_per_sender:
            messages_per_sender[message.sender] = message.text
        else:
            # If the sender is already in the dictionary, append the current message
            messages_per_sender[message.sender] += (
                "\n" + message.text
            )  # Adding a newline for separation

    # Optionally, convert the dictionary to a list of tuples if needed
    concatenated_messages = [
        (sender, messages) for sender, messages in messages_per_sender.items()
    ]

    return concatenated_messages


@app.route("/chat", methods=["GET", "POST"])
@app.route("/chat", methods=["GET", "POST"])
@login_required
def chat_with_assistant():
    if request.method == "POST":
        query = request.form.get("user_query", "")
        current_user = User.query.filter_by(username=session["username"]).first()
        thread_id = get_or_create_thread(current_user.id)
        name = current_user.first_name + " " + current_user.last_name
        email = current_user.email

        # Fetch the chat history for the thread
        chat_history = get_chat_history_concatenated(thread_id)
        print(chat_history)
        # Adjust get_response to include chat_history
        ass_response = get_response(
            question=query,
            name=name,
            email=email,
            thread_id=thread_id,
            chat_history=chat_history,  # Pass the correctly formatted chat history
        )

        # Save query and response in ChatMessage associated with the thread
        save_chat_message(thread_id, query, "user")
        save_chat_message(thread_id, ass_response, "assistant")
        res = json.loads(ass_response)
        assistant_response = res["answer"]

        return jsonify(
            {"user_message": query, "assistant_response": assistant_response}
        )

    else:
        # For GET requests, render the chat page normally
        return render_template("chat.html", user_logged_in="logged_in" in session)


if __name__ == "__main__":
    app.run(debug=True)

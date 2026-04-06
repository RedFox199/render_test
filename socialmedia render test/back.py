from flask import Flask, request, jsonify, render_template, redirect, url_for, session
import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)

# ✅ Secret key from environment
app.secret_key = os.environ.get("SECRET_KEY", "dev-key")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_name = os.path.join(BASE_DIR, "socialSQL.sqlite")

UPLOAD_FOLDER = "static/images"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# ✅ Ensure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def get_db_connection():
    conn = sqlite3.connect(DB_name)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        password TEXT NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS profile (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL UNIQUE,
        name TEXT NOT NULL,
        imgpath TEXT,
        description TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS posts(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        content TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS friend_request(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        friend_id INTEGER NOT NULL,
        status TEXT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS friends(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user1 INTEGER NOT NULL,
        user2 INTEGER NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS notifications(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        message TEXT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS messages(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender_id INTEGER NOT NULL,
        receiver_id INTEGER NOT NULL,
        content TEXT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()


@app.route("/")
def home():
    return render_template("sign-log.html")


@app.route("/signup")
def signup():
    return render_template("signup.html")


@app.route("/add", methods=["POST"])
def add_user():
    conn = get_db_connection()
    data = request.get_json()

    defaultimg = "default-profile-picture-avatar-photo-placeholder-vector-illustration-default-profile-picture-avatar-photo-placeholder-vector-189495158.webp"
    addname = data.get("addname")
    addpassword = data.get("addpassword")

    hashed_password = generate_password_hash(addpassword)

    cur = conn.cursor()
    cur.execute("INSERT INTO users (name,password) VALUES (?,?)", (addname, hashed_password))
    user_id = cur.lastrowid

    cur.execute("INSERT INTO profile (user_id,name,imgpath,description) VALUES (?,?,?,?)",
                (user_id, addname, defaultimg, ""))

    conn.commit()
    conn.close()

    return jsonify({"message": "saved successfully"})


@app.route("/login", methods=["POST"])
def login():
    conn = get_db_connection()
    data = request.get_json()

    name = data.get("name")
    password = data.get("password")

    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE name = ?", (name,))
    user = cur.fetchone()

    conn.close()

    if user and check_password_hash(user["password"], password):
        session["user_id"] = user["id"]
        return jsonify({"message": "login successfull"})
    return jsonify({"message": "invalid"})


@app.route("/uploadimg", methods=["POST"])
def uploadimg():
    if "file" not in request.files:
        return jsonify({"error": "no file found"})

    file = request.files["file"]

    if file.filename == "":
        return jsonify({"error": "no uploaded file"})

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)

        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(filepath)

        user_id = session.get("user_id")
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("UPDATE profile SET imgpath = ? WHERE user_id = ?", (filename, user_id))

        conn.commit()
        conn.close()

        return jsonify({"message": "image updated"})

    return jsonify({"error": "file type not allowed"})


@app.route("/posts", methods=["POST"])
def posts():
    user_id = session.get("user_id")

    data = request.get_json()
    post = data.get("content")

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("INSERT INTO posts (user_id,content) VALUES (?,?)", (user_id, post))

    conn.commit()
    conn.close()

    return jsonify({"message": "posted successfully"})


@app.route("/chat/<int:friend_id>")
def chat(friend_id):
    user_id = session.get("user_id")

    conn = get_db_connection()
    cur = conn.cursor()

    messages = cur.execute("""
        SELECT messages.*, profile.name, profile.imgpath
        FROM messages
        JOIN profile ON messages.sender_id = profile.user_id
        WHERE (sender_id = ? AND receiver_id = ?)
        OR (sender_id = ? AND receiver_id = ?)
    """, (user_id, friend_id, friend_id, user_id)).fetchall()

    conn.close()

    return render_template("chat.html", messages=messages, friend_id=friend_id)


@app.route("/send_request", methods=["POST"])
def send_request():
    data = request.get_json()
    user_id = session.get("user_id")
    friend_id = data["friend_id"]

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("INSERT INTO friend_request (user_id, friend_id, status) VALUES (?,?,?)",
                (user_id, friend_id, "pending"))

    cur.execute("INSERT INTO notifications(user_id,message) VALUES (?,?)",
                (friend_id, f"you have friend request from {user_id}"))

    conn.commit()
    conn.close()

    return jsonify({"message": "request sent"})


# ✅ IMPORTANT FOR RENDER
if __name__== "__main__":
    init_db()
    app.run(debug=True)
from flask import Flask, request,jsonify, render_template, redirect, url_for, session
import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-key")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # folder of back.py
DB_name = os.path.join(BASE_DIR, "socialSQL.sqlite")
UPLOAD_FOLDER= "static/images"
ALLOWED_EXTENSIONS = {"png","jpg","jpeg","gif", "webp"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
\
def allowed_file(filename):
     return "." in filename and filename.rsplit(".",1)[1].lower() in ALLOWED_EXTENSIONS

def get_db_connection():
    conn = sqlite3.connect(DB_name)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
    create table if not exists users (id integer primary key autoincrement,
            name text not null,
                password text not null    )
                """)
    
    cur.execute("""
                create table if not exists profile (id integer primary key autoincrement,
                user_id integer not null unique,
                name text not null,
                imgpath text,
                description text,
                foreign key (user_id) references users(id))
                """)
    
    cur.execute("""
     create table if not exists posts(id integer primary key autoincrement,
                user_id integer not null,
                content text,
                created_at datetime default current_timestamp,
                foreign key(user_id) references users(id))
                """)
    cur.execute("""
     create table if not exists friend_request(id integer primary key autoincrement,
                user_id integer not null,
                friend_id integer not null,
                status text not null,
                created_at datetime default current_timestamp
                )
                """)
    cur.execute("""
     create table if not exists friends(id integer primary key autoincrement,
                user1 integer not null,
                user2 integer not null)
                """)
    cur.execute("""
     create table if not exists notifications(id integer primary key autoincrement,
                user_id integer not null,
                message text not null,
                created_at datetime default current_timestamp)
                """)
    cur.execute("""
     create table if not exists messages(id integer primary key autoincrement,
                sender_id integer not null,
                receiver_id integer not null,
                content text not null,
                created_at datetime default current_timestamp)
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
        if not data:
             return jsonify({"error": "no JSON data"}), 400
        defaultimg = "default-profile-picture-avatar-photo-placeholder-vector-illustration-default-profile-picture-avatar-photo-placeholder-vector-189495158.webp"
        defaultdesc = ""
        addname = data.get("addname")
        addpassword = data.get("addpassword")
        hashed_password = generate_password_hash(addpassword)
        cur = conn.cursor()
        cur.execute("insert into users (name,password) values (?,?)",(addname,hashed_password))
        user_id = cur.lastrowid
        cur.execute("insert into profile (user_id,name,imgpath,description) values (?,?,?,?)",(user_id,addname,defaultimg,defaultdesc))
        conn.commit()
        conn.close()
        return jsonify ({"message": "saved successfully"})
    
@app.route("/login", methods = ["POST"])
def login():
        conn = get_db_connection()
        data = request.get_json()
        if not data:
              return jsonify({"error": "no json data"})
        name = data.get("name")
        password = data.get("password")
        if not name or not password:
            return jsonify({"error": "name and password required"}), 400
        cur = conn.cursor()
        cur.execute("select * from users where name = ?",(name,))
        user = cur.fetchone()
        conn.close()
        if user and check_password_hash(user["password"], password) :
              session["user_id"]=user["id"]
              return jsonify({"message":"login successfull"})
        else:
              return jsonify({"message":"invalid"})

@app.route("/profile")
def profile():
     user_id = session.get("user_id")
     if not user_id:
          return redirect(url_for("home"))
     conn = get_db_connection()
     cur = conn.cursor()
     cur.execute("""
        select users.name, profile.imgpath, profile.description from users
                 join profile on users.id = profile.user_id
                 where users.id = ?
                 """, (user_id,))
     user = cur.fetchone()
     conn.close()

     if not user:
          return redirect(url_for("home"))  # Redirect if user not found

     return render_template("profile.html", user=user)

@app.route("/descupdate", methods = ["POST"])
def descupdate():
    user_id = session.get("user_id")
    if not user_id:
         return jsonify({"error": "Not logged in"}), 401
    data = request.get_json()
    if not data or "desc" not in data:
        return jsonify({"error": "no description provided"}), 400
    newdesc = data.get("desc")
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("update profile set description = ? where user_id = ?",(newdesc,user_id))
    conn.commit()
    conn.close()
    return jsonify({"message": "description updated"})

@app.route("/editnamepage")
def editnamepage():
     user_id = session.get("user_id")
     if not user_id:
          return redirect(url_for("home"))
     conn = get_db_connection()
     cur = conn.cursor()
     cur.execute("select name from users where id = ?", (user_id,))
     user = cur.fetchone()
     conn.close()
     return render_template("editname.html", user=user)

@app.route("/editname", methods = ["POST"])
def editname():
     user_id = session.get("user_id")
     if not user_id:
          return redirect(url_for("home"))
     data = request.get_json()
     new_name = data.get("newname")
     conn = get_db_connection()
     cur = conn.cursor()
     cur.execute("update users set name = ? where id = ?",(new_name,user_id))
     cur.execute("update profile set name = ? where user_id = ?",(new_name,user_id))
     conn.commit()
     conn.close()
     return jsonify ({"message": "updated successfully"})

@app.route("/uploadimg", methods = ["POST"])
def uploadimg():
     if "file" not in request.files:
          return jsonify({"error": "no file found"})
     file = request.files["file"]
     if file.filename == "":
          return jsonify({"error":"no uplaoded file"})
     if file and allowed_file(file.filename):
          filename = secure_filename(file.filename)
          file.save(os.path.join(app.config["UPLOAD_FOLDER"],filename))

          user_id = session.get("user_id")
          if not user_id:
               return jsonify({"message":"not logged in"})
          conn = get_db_connection()
          cur = conn.cursor()
          cur.execute("update profile set imgpath = ? where user_id = ?",(filename,user_id))
          conn.commit()
          conn.close()
          return jsonify({"message":"image updated"})
     return jsonify({"error":"file type not allowed"})

@app.route("/posts", methods=["POST"])
def posts():
     user_id = session.get("user_id")
     if not user_id:
          return redirect(url_for("home"))
     data = request.get_json()
     if not data or "content" not in data:
        return jsonify({"error": "no content"}), 400
     post = data.get("content")
     conn = get_db_connection()
     cur = conn.cursor()
     cur.execute("insert into posts (user_id,content) values (?,?)",(user_id,post))
     conn.commit()
     conn.close()
     return jsonify({"message":"posted successfully"})

@app.route("/showposts")
def showposts():
     user_id = session.get("user_id")
     if not user_id:
          return redirect(url_for("home"))
     conn = get_db_connection()
     cur = conn.cursor()
     cur.execute("select name from users where id = ?",(user_id,))
     user = cur.fetchone()
     username = user["name"]
     
     cur.execute("select users.name, posts.content, posts.created_at from posts join users on posts.user_id=users.id order by posts.created_at desc")
     posts = cur.fetchall()
     conn.close()
     return render_template("home.html", posts=posts , name=username)

@app.route("/searchbar")
def searchbar():
     q = request.args.get("who","")
     conn = get_db_connection()
     cur = conn.cursor()
     users = cur.execute("SELECT user_id, name, imgpath FROM profile WHERE name LIKE ?", (f"%{q}%",)).fetchall()
     conn.close()
     return jsonify([dict(u) for u in users])

@app.route("/send_request", methods=["POST"])
def send_request():
     data = request.get_json()
     user_id = session.get("user_id")
     if not user_id:
          return redirect(url_for("home"))
     friend_id = data["friend_id"]
     conn = get_db_connection()
     cur = conn.cursor()
     cur.execute("insert into friend_request (user_id , friend_id, status) values (?,?,?)", (user_id,friend_id,"pending"))
     cur.execute("insert into notifications(user_id,message) values (?,?)",(friend_id,"you have friend request from {user_id}"))
     conn.commit()
     conn.close()
     return jsonify({"message":"request sent"})

@app.route("/accept_request", methods=["POST"])
def accept_request():
     data = request.get_json()
     user_id = session.get("user_id")
     friend_id = data["friend_id"]
     conn = get_db_connection()
     cur = conn.cursor()
     req = cur.execute("select * from friend_request where friend_id = ?",(friend_id,)).fetchone()
     cur.execute("insert into friends (user1,user2) values (?,?)",(req["user_id"],req["friend_id"]))
     cur.execute("update friend_request set status ='accepted' where user_id = ?, friend_id = ?",(user_id,friend_id))
     conn.commit()
     conn.close()
     return jsonify({"message":"request accepted"})

@app.route("/show_friends")
def show_friends():
     user_id = session.get("user_id")
     if not user_id:
          return redirect(url_for("home"))
     conn = get_db_connection()
     cur = conn.cursor()
     req = cur.execute("select friends.user1 , friends.user2 , users.name from friends join users on friends.user2 = users.id where user1 = ?",(user_id,)).fetchall()
     friends = [row["name"] for row in req]
     conn.close()
     return render_template("friends.html", friends=friends)

@app.route("/show_notification")
def show_notifications():
     user_id = session.get("user_id")
     if not user_id:
          return redirect(url_for("home"))
     conn = get_db_connection()
     cur = conn.cursor()
     notifications = cur.execute("select message from notifications where user_id = ?",(user_id,)).fetchall()
     conn.close()
     return render_template("home.html", notifications = notifications)

@app.route("/messages", methods = ["POST"])
def messages():
     user_id = session.get("user_id")
     if not user_id:
          return redirect("home")
     data = request.get_json()
     content = data.get("content")
     receiver_id = data.get("receiver_id")
     if not receiver_id or not content:
        return jsonify({"error": "missing data"}), 400
     conn = get_db_connection()
     cur = conn.cursor()
     cur.execute("insert into messages (sender_id,receiver_id,content) values(?,?,?)",(user_id,receiver_id,content))
     conn.commit()
     conn.close()
     return jsonify({"message":"message sent"})

@app.route("/chat/<int:friend_id>")
def chat(friend_id):
     user_id = session.get("user_id")
     if not user_id:
          return redirect(url_for("home"))
     conn = get_db_connection()
     cur = conn.cursor()
     cur.execute("select messages.*,profile.name,profile.imgpath from messages join profile on messages.sender_id = profile.user_id where (sender_id = ? and receiver_id = ?) or (sender_id = ? and receiver_id = ?)",(user_id,friend_id , friend_id , user_id)).fetchall()
     conn.close()
     return render_template("chat.html", messages = messages , friend_id=friend_id)
     
@app.route("/unfriend/<int:friend_id>", methods = ["POST"])
def unfriend(friend_id):
     user_id = session.get("user_id")
     if not user_id:
          return redirect(url_for("home"))
     conn = get_db_connection()
     cur = conn.cursor()
     cur.execute("delete from friends where (user1 = ? and user2 = ?) or (user1 = ? and user2 = ?)",(user_id,friend_id,friend_id,user_id))
     conn.commit()
     conn.close()
     return jsonify({"message":"unfriended successfully"})

@app.route("/deletenotif/<int:notification_id>", methods = ["POST"])
def deletenotif(notification_id):
     user_id = session.get("user_id")
     if not user_id:
          return redirect(url_for("home"))
     conn = get_db_connection()
     cur = conn.cursor()
     cur.execute("delete from notifications where id = ? and user_id = ?",(notification_id,user_id))
     conn.commit()
     conn.close()
     return jsonify({"message":"deleted successfully"})

     
@app.route("/db")
def view_db():
    conn = get_db_connection()
    cur = conn.cursor()

    users = cur.execute("SELECT * FROM users").fetchall()
    profiles = cur.execute("SELECT * FROM profile").fetchall()
    posts = cur.execute("SELECT * FROM posts").fetchall()

    conn.close()

    return render_template("dbview.html", users=users, profiles=profiles, posts=posts)

@app.route("/db")
def db():
    conn = get_db_connection()
    cur = conn.cursor()

    users = cur.execute("SELECT * FROM users").fetchall()
    profiles = cur.execute("SELECT * FROM profile").fetchall()
    posts = cur.execute("SELECT * FROM posts").fetchall()

    conn.close()

    return render_template("dbview.html", users=users, profiles=profiles, posts=posts)


if __name__== "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

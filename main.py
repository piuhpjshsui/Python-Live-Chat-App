from flask import Flask, render_template, request, session, redirect, url_for
from flask_socketio import join_room, leave_room, send, SocketIO, emit

app = Flask(__name__)
app.config["SECRET_KEY"] = "hjhjsdahhds"
socketio = SocketIO(app)

ROOM = "public_room"

users = {}  # To store connected users
registered_users = {}  # To store registered usernames

@app.route("/", methods=["POST", "GET"])
def home():
    session.clear()
    if request.method == "POST":
        name = request.form.get("name")

        if not name:
            return render_template("home.html", error="Please enter a name.", name=name)
        
        if name in registered_users:
            # Existing user, log them in
            session["name"] = name
            return redirect(url_for("room"))
        else:
            # Register new user
            registered_users[name] = True
            session["name"] = name
            return redirect(url_for("room"))

    return render_template("home.html")

@app.route("/room")
def room():
    if session.get("name") is None:
        return redirect(url_for("home"))

    return render_template("room.html", messages=[], users=users.keys())

@socketio.on("message")
def handle_message(data):
    name = session.get("name")
    message_type = data.get("type")
    message_content = data.get("data")
    recipient = data.get("recipient")

    if message_type == "public":
        # Public message to all users in the room
        content = {"name": name, "message": message_content}
        send(content, to=ROOM)
    
    elif message_type == "private":
        # Private message to a specific user
        if recipient in users:
            # Notify the recipient
            recipient_sid = users[recipient]
            emit("message", {"name": f"Private from {name}", "message": message_content}, to=recipient_sid)
            
            # Notify the sender
            sender_sid = users[name]
            emit("message", {"name": f"Private to {recipient}", "message": message_content}, to=sender_sid)
        else:
            # If recipient is not found, send an error to the sender
            emit("message", {"name": "System", "message": f"{recipient} is not available."}, to=users[name])

@socketio.on("connect")
def connect():
    name = session.get("name")
    if not name:
        return redirect(url_for("home"))
    
    users[name] = request.sid  # Map username to socket ID
    join_room(ROOM)
    send({"name": name, "message": "has entered the room"}, to=ROOM)
    # Emit the updated user list to all clients
    emit("update_users", list(users.keys()), to=ROOM)

@socketio.on("disconnect")
def disconnect():
    name = session.get("name")
    if name in users:
        del users[name]
    leave_room(ROOM)
    send({"name": name, "message": "has left the room"}, to=ROOM)
    # Emit the updated user list to all clients
    emit("update_users", list(users.keys()), to=ROOM)

if __name__ == "__main__":
    socketio.run(app, debug=True)

import requests
import threading
import json
import pika

from math import ceil
from time import time
from tkinter import *
from tkinter import messagebox
from tkinter.ttk import Notebook

# Update this address to match the server
HOST_ADDRESS = "http://127.0.0.1:5000"

# Static resources
API_ADDRESS = HOST_ADDRESS + "/api/"
GAMETYPES_ADDRESS = None
USERS_ADDRESS = None
GAMES_ADDRESS = None

RANDOM_TTT_ADDRESS = None
RANDOM_CHK_ADDRESS = None

# Global session for communication
session = requests.Session()
session.headers["Content-Type"] = "application/json"

# Window size in pixels, board does not adjust to changes
win_size = (700, 450)

# Create application window
root = Tk()
root.title("Online Boardgame")

# Image files, paths sensitive to run context
# Tic-tac-toe images, size 128x128
BLANK_IMAGE = PhotoImage(file="client/resources/blank_128x128.png")
X_IMAGE = PhotoImage(file="client/resources/X_image.png")
O_IMAGE = PhotoImage(file="client/resources/O_image.png")

# Checkers images, size 43x43
SMALL_BLANK_IMAGE = PhotoImage(file="client/resources/blank_43x43.png")
B_CHECKER_IMAGE = PhotoImage(file="client/resources/black_checker.png")
W_CHECKER_IMAGE = PhotoImage(file="client/resources/white_checker.png")
BK_CHECKER_IMAGE = PhotoImage(file="client/resources/black_king.png")
WK_CHECKER_IMAGE = PhotoImage(file="client/resources/white_king.png")

# Adjust window size and location. Format: WIDTHxHEIGHT+x_coord+y_coord, anchor point is upper left corner
root.geometry(f"{win_size[0]}x{win_size[1]}+200+120")
root.resizable(False, False)

# Create tab controller
tabControl = Notebook(root, height=win_size[1])

#--------------------------------------------------------------
#-- Client state ----------------------------------------------
#--------------------------------------------------------------
# Boards
tic_board: dict[int, Button] = {}
chk_board: dict[int, Button] = {}
spec_board: dict[int, Button] = {}
board_state = ""
chk_selected_piece = None

# Addresses for current game and its moves resource
game_address = None
moves_address = None

# User
username = None
password = None

# Settings
settings = {
    "autojoin": BooleanVar()
}

# Variables
turn_start = 0
current_tab = "profile"
notification_ids = {"checkers": None, "tictactoe": None,
                    "profile": None, "spectate": None}
spec_thread = None
spec_connection = None
spec_game_dict = None

#--------------------------------------------------------------
#-- Profile tab -----------------------------------------------
#--------------------------------------------------------------
prof_frame = Frame(tabControl)
prof_frame.grid(sticky="sewn")

def updateUserInfo():
    # Get user statistics
    resp = session.get(USERS_ADDRESS + username)
    if resp.status_code != 200: return
    
    # Display user info
    data = resp.json()
    uinfo_name.config(text=username)
    uinfo_turncount.config(text="Turns played: " + str(data["turnsPlayed"]))
    uinfo_gametime.config(text="Playtime: " + str(data["totalTime"]))

# Login frame
Label(prof_frame, text="Change user:", font=("", 25)).grid(row=0, column=0, columnspan=2, sticky="nw")
Label(prof_frame, text="Username:", font=("", 15)).grid(row=1, column=0, sticky="w")
Label(prof_frame, text="Password:", font=("", 15)).grid(row=2, column=0, sticky="w")

# Username and password fields
name_entry = Entry(prof_frame)
name_entry.grid(row=1, column=1, sticky="w")
pass_entry = Entry(prof_frame)
pass_entry.grid(row=2, column=1, sticky="w")

# User information
uinfo_frame = Frame(prof_frame, bg="lightgrey", width=300, height=win_size[1])
uinfo_frame.place(x=win_size[0], y=0, anchor="ne")

uinfo_name = Label(prof_frame, bg="lightgrey", text="", font=("", 25))
uinfo_name.place(in_=uinfo_frame, relx=0.5, y=30, anchor="center")

uinfo_turncount = Label(prof_frame, bg="lightgrey", text="", font=("", 15))
uinfo_turncount.place(in_=uinfo_frame, relx=0.5, y=100, anchor="center")

uinfo_gametime = Label(prof_frame, bg="lightgrey", text="", font=("", 15))
uinfo_gametime.place(in_=uinfo_frame, relx=0.5, y=140, anchor="center")

# Login function
def checkLogin():
    name = name_entry.get()
    pwd = pass_entry.get()
    if len(name) == 0 or len(pwd) == 0: return
    
    # Set credentials
    session.headers["username"] = name
    session.headers["password"] = pwd
    
    resp = session.get(USERS_ADDRESS + name)
    global username, password
    if resp.status_code == 200:
        # Credentials are valid, login
        username = name
        password = pwd
        updateUserInfo()
        notify("Logged in.")
        # Show user management buttons
        logout_button.place(x=70, y=350, anchor="center")
        delete_user_button.place(x=220, y=350, anchor="center")
    elif resp.status_code == 404:
        # Username not found, register new user
        data = json.dumps({"name": name, "password": pwd})
        register_resp = session.post(USERS_ADDRESS, data)
        if register_resp.status_code == 201:
            # New user created
            username = name
            password = pwd
            updateUserInfo()
            notify("Created new user.")
            logout_button.place(x=70, y=350, anchor="center")
            delete_user_button.place(x=220, y=350, anchor="center")
            return
        # Failed to create new user
        notify("Username already exists.\n Unable to create new user.")
    elif resp.status_code == 403:
        notify("Incorrect password.")

# Logout fucntion
def logout():
    # Local
    global username, password
    username = None
    password = None
    
    # Session credentials
    session.headers.pop("username")
    session.headers.pop("password")
    
    # Visuals
    uinfo_name.config(text="")
    uinfo_gametime.config(text="")
    uinfo_turncount.config(text="")
    logout_button.place_forget()
    delete_user_button.place_forget()
    notify("Logged out.")

# Delete user, user is asked to confirm
def deleteUser():
    if username is None or password is None:
        return
    
    # Show confirmation window
    popup = Toplevel(root)
    popup.geometry("300x100+400+300")
    popup.grab_set()
    
    Label(popup, text="Delete user?\nThis action is permanent!", font=("", 15)
    ).place(x=150, y=30, anchor="center")
    
    # Confirm function
    def confirmDelete():
        delete_resp = session.delete(USERS_ADDRESS + username)
        if delete_resp.status_code == 200:
            logout()
            notify("Deleted user.")
        else:
            notify("Failed to delete user.")
        popup.destroy()
    
    # Confirm/cancel buttons
    Button(popup, bg="darkgrey", text="Confirm", font=("", 13), command=confirmDelete
    ).place(x=220, y=75, anchor="center")
    Button(popup, bg="darkgrey", text="Cancel", font=("", 13), command=popup.destroy
    ).place(x=80, y=75, anchor="center")

# Login/Register button
Button(prof_frame, text="Login/Register", command=checkLogin, font=("", 13)).grid(row=3, column=0)

# Buttons for logging out and deleting user
logout_button = Button(
    uinfo_frame, bg="darkgray", text="Logout", font=("", 15), command=logout)
delete_user_button = Button(
    uinfo_frame, bg="darkgray", text="Delete user", font=("", 15), command=deleteUser)

checkbox_autojoin = Checkbutton(
    prof_frame, text="Auto-Join after move", variable=settings["autojoin"], font=("", 15),
    onvalue=True, offvalue=False
)
checkbox_autojoin.place(x=10, y=420, anchor="sw")

# Notification is drawn last so it appears on top of other elements
prof_note = Label(prof_frame, bg="lightgrey", text="", font=("", 15))
prof_note.place(x=690, y=425, anchor="se")

#--------------------------------------------------------------
#-- Tic-tac-toe tab -------------------------------------------
#--------------------------------------------------------------
tic_frame = Frame(tabControl)
tic_frame.grid(sticky="sewn")

# Draw tic-tac-toe game info and controls
Label(tic_frame, text="Tic-tac-toe", font=("", 30)).grid(row=0, column=4, sticky="n", padx=40)

tic_note = Label(tic_frame, text="", font=("", 15))
tic_note.place(x=690, y=425, anchor="se")

tic_team_label = Label(tic_frame, text="", font=("", 15))
tic_team_label.place(x=560, y=60, anchor="center")

tic_gameid_label = Label(tic_frame, text="", font=("", 10))
tic_gameid_label.place(x=560, y=200, anchor="center")

Button(
    tic_frame, background="grey", bd=6,
    text="New Game", font=("", 17),
    command= lambda: joinRandomGame()
).place(x=560, y=120, anchor="center")

#--------------------------------------------------------------
#-- Checkers tab ----------------------------------------------
#--------------------------------------------------------------
chk_frame = Frame(tabControl)
chk_frame.grid(sticky="sewn")

Label(chk_frame, text="Checkers", font=("", 30)).grid(row=0, column=8, sticky="n", padx=45)

chk_note = Label(chk_frame, text="", font=("", 15))
chk_note.place(x=690, y=425, anchor="se")

chk_team_label = Label(chk_frame, text="", font=("", 15))
chk_team_label.place(x=560, y=60, anchor="center")

chk_gameid_label = Label(chk_frame, text="", font=("", 10))
chk_gameid_label.place(x=560, y=200, anchor="center")

Button(
    chk_frame, background="grey", bd=6,
    text="New Game", font=("", 17),
    command= lambda: joinRandomGame()
).place(x=560, y=120, anchor="center")

#--------------------------------------------------------------
#-- Spectate tab ----------------------------------------------
#--------------------------------------------------------------
spec_frame = Frame(tabControl)
spec_frame.grid(sticky="sewn")

#padx needs to probably be fixed after button command works
Label(spec_frame, text="Spectate", font=("", 30)).grid(sticky="n", padx=480)

spec_game_id_entry = Entry(spec_frame)
spec_game_id_entry.place(x=560, y=80, anchor="center")

spec_note = Label(spec_frame, text="", font=("", 15))
spec_note.place(x=560, y=400, anchor="center")

# Needs the command for spectateGame() when function completed
Button(
    spec_frame, background="grey", bd=6,
    text="Spectate Game", font=("", 17),
    command= lambda: spectateGame()
).place(x=560, y=120, anchor="center")

gameLabel = Label(spec_frame, text="", font=("", 16))
gameLabel.place(x=560, y=180, anchor="center")
playerLabel = Label(spec_frame, text="", font=("", 16))
playerLabel.place(x=560, y=220, anchor="center")

stopButton = None

#Frame where the game to be spectated would be drawn, might need to be removed
#to just use spec_frame instead
game_frame = Frame(spec_frame, bg="#FFFFFF", bd=2, relief="solid", width=423, height=423)
game_frame.place(x=0, y=0)

#--------------------------------------------------------------
#-- Draw tabs -------------------------------------------------
#--------------------------------------------------------------
tabControl.add(prof_frame, text="Profile")
tabControl.add(tic_frame, text="Tic-tac-toe")
tabControl.add(chk_frame, text="Checkers")
tabControl.add(spec_frame, text="Spectate")
tabControl.pack(fill="both")

#--------------------------------------------------------------
#-- Functions -------------------------------------------------
#--------------------------------------------------------------
def updateCurrentTab(_):
    global current_tab
    current_tab = tabControl.tab(tabControl.select(), "text").lower().replace("-", "")
    leaveCurrentGame()
    if current_tab == "profile" and username is not None and password is not None:
        updateUserInfo()
tabControl.bind("<<NotebookTabChanged>>", updateCurrentTab)

def leaveCurrentGame():
    global game_address, moves_address
    
    # If not in game, return
    if game_address is None: return

    # Make an empty move to leave the game
    data = json.dumps({"move": "", "moveTime": 0})
    session.post(moves_address, data)
    
    # Forget previous game addresses
    game_address = None
    moves_address = None
    
    # Update visuals
    notify("Left game.")
    tic_team_label.config(text="")
    chk_team_label.config(text="")
    tic_gameid_label.config(text="")
    chk_gameid_label.config(text="")

def boardInput(board_index):
    if game_address is None:
        notify("Join game before playing.")
        return
    elif username is None or password is None:
        notify("Login before playing.")
        return
    
    # Extract users move from variables
    global chk_selected_piece
    if current_tab == "tictactoe":
        move = board_index
    elif chk_selected_piece is None:
        # Select checkers piece to move
        chk_selected_piece = board_index
        chk_board[board_index].config(bg="grey")
        return
    elif chk_selected_piece == board_index:
        # Forget previous selection when clicking it again
        chk_selected_piece = None
        chk_board[board_index].config(bg="lightgrey")
        return
    else:
        # Move previously selected piece to new position
        move = (chk_selected_piece, board_index)
    
    turn_duration = time() - turn_start
    data = json.dumps({"move": move, "moveTime": ceil(turn_duration)})
    
    resp = session.post(moves_address, data)
    if resp.status_code == 200:
        notify("Move successful.")
        drawMoveLocally(move)
        
        # Hide team label to avoid confusion
        tic_team_label.config(text="")
        chk_team_label.config(text="")
        
        # Join new game if autojoin is enabled
        if settings["autojoin"].get():
            root.after(400, joinRandomGame)
        
def notify(text: str):
    # Select notification label of the current tab
    if current_tab == "tictactoe":
        label = tic_note
    elif current_tab == "checkers":
        label = chk_note
    elif current_tab == "profile":
        label = prof_note
    elif current_tab == "spectate":
        label = spec_note
    else: return
    
    # Display the notification
    label.config(text=text)
    
    # Reset notification text after 2 seconds
    global notification_ids
    if notification_ids[current_tab] is not None:
        label.after_cancel(notification_ids[current_tab])
    notification_ids[current_tab] = label.after(2000, label.config, {"text":""})

def drawMoveLocally(move: int | tuple[int, int]):
    if current_tab == "tictactoe":
        if board_state[0] == "1":
            image = X_IMAGE
        else:
            image = O_IMAGE
        tic_board[move].config(image=image)
    elif current_tab == "checkers":
        # Stop highlighting
        chk_board[move[0]].config(bg="lightgrey")
        
        # Move the mark
        mark = chk_board[move[0]].cget("image")
        chk_board[move[1]].config(image=mark)
        chk_board[move[0]].config(image=SMALL_BLANK_IMAGE)
        
        # If jumped over a mark, remove it
        if (move[0] - move[1]) % 14 == 0 or (move[0] - move[1]) % 18 == 0:
            chk_board[(move[0] + move[1]) / 2].config(image=SMALL_BLANK_IMAGE)
        
def updateBoard():
    # Updates corresponding board with new state
    # Also marks current team
    global board_state
    state = board_state[1:]
    if current_tab == "tictactoe":
        tic_team_label.config(text="Playing on team " + str(board_state[0]))
        for i in range(9):
            match state[i]:
                case "-":
                    image = BLANK_IMAGE
                case "X":
                    image = X_IMAGE
                case "O":
                    image = O_IMAGE
            tic_board[i].config(image=image)
    elif current_tab == "checkers":
        chk_team_label.config(text="Playing on team " + str(board_state[0]))
        for i in range(64):
            match state[i]:
                case "-":
                    image = SMALL_BLANK_IMAGE
                case "b":
                    image = B_CHECKER_IMAGE
                case "B":
                    image = BK_CHECKER_IMAGE
                case "w":
                    image = W_CHECKER_IMAGE
                case "W":
                    image = WK_CHECKER_IMAGE
            chk_board[i].config(image=image)



def joinRandomGame():
    if username is None or password is None:
        notify("Login before playing.")
        return
    leaveCurrentGame()
    
    # If a checker piece was selected, deselect it before new game
    global chk_selected_piece
    if chk_selected_piece is not None:
        chk_board[chk_selected_piece].config(bg="lightgrey")
        chk_selected_piece = None
    
    # Get random game, gametype detected from tab name
    if current_tab == "tictactoe":
        address = RANDOM_TTT_ADDRESS
    else:
        address = RANDOM_CHK_ADDRESS
    getrandom_resp = session.get(address)
    if getrandom_resp.status_code != 200: return
    
    # Join the received game
    join_href = getrandom_resp.json()["@controls"]["boardgame:join-game"]["href"]
    join_resp = session.post(HOST_ADDRESS + join_href)
    if join_resp.status_code != 200: return
    notify("Game joined.")
    
    # Save game- and moves address
    global game_address, moves_address
    game_address = HOST_ADDRESS + join_resp.headers["Location"]
    moves_address = HOST_ADDRESS + join_resp.json()["@controls"]["boardgame:make-move"]["href"]
    
    # Show game id to user
    game_id = game_address.split("/")[-1]
    if current_tab == "tictactoe":
        tic_gameid_label.config(text="Game id:\n" + game_id)
    else:
        chk_gameid_label.config(text="Game id:\n" + game_id)
    
    # Get board state
    game_resp = session.get(game_address)
    if game_resp.status_code != 200: return
    
    # Save and draw board state
    global board_state, turn_start
    board_state = game_resp.json()["state"]
    updateBoard()
    turn_start = time()

def fetchResourceAddresses():
    global HOST_ADDRESS, API_ADDRESS, USERS_ADDRESS, GAMETYPES_ADDRESS, GAMES_ADDRESS
    global RANDOM_CHK_ADDRESS, RANDOM_TTT_ADDRESS
    
    # Get API entrypoint, exit application if server unreachable or response is invalid
    try:
        init_resp = session.get(API_ADDRESS)
        if init_resp.status_code != 200: raise Exception
        notify("Connected.")
    except Exception:
        notify("Failed to connect to server.")
        root.after(2000, notify, "Exiting...")
        root.after(4000, root.destroy)
        return
    
    USERS_ADDRESS = HOST_ADDRESS + init_resp.json()["@controls"]["boardgame:users-all"]["href"]
    GAMETYPES_ADDRESS = HOST_ADDRESS + init_resp.json()["@controls"]["boardgame:gametypes-all"]["href"]
    GAMES_ADDRESS = HOST_ADDRESS + init_resp.json()["@controls"]["boardgame:games-all"]["href"]
    
    # Get gametypes
    gametypes_resp = session.get(GAMETYPES_ADDRESS)
    if gametypes_resp.status_code != 200:
        notify("Could not get gametypes.")
        root.after(2000, root.destroy)
        return
    
    # Get random-game route for each gametype
    for gtype in gametypes_resp.json()["items"]:
        self_resp = session.get(HOST_ADDRESS + gtype["@controls"]["self"]["href"])
        if self_resp.status_code != 200:
            notify("Could not get gametype " + gtype["name"] + ".")
            root.after(2000, root.destroy)
            return
        
        if gtype["name"] == "tictactoe":
            RANDOM_TTT_ADDRESS = HOST_ADDRESS + self_resp.json()["@controls"]["boardgame:get-random"]["href"]
        elif gtype["name"] == "checkers":
            RANDOM_CHK_ADDRESS = HOST_ADDRESS + self_resp.json()["@controls"]["boardgame:get-random"]["href"]


def updateSpectatorBoard():
    for bt in spec_board.values():
        bt.destroy()
    spec_board.clear()
    state = spec_game_dict["state"][1:]
    if spec_game_dict["type"] == "tictactoe":
        for x in range(3):
            for y in range(3):
                i = x + y * 3
                image = BLANK_IMAGE
                match state[i]:
                    case "X":
                        image = X_IMAGE
                    case "O":
                        image = O_IMAGE
                bt = Button(
                    game_frame, background="lightgrey", image=image, bd=6
                )
                bt.grid(column=x, row=y, sticky="sewn")
                spec_board[i] = bt

    elif spec_game_dict["type"] == "checkers":
        for x in range(8):
            for y in range(8):
                i = x + y * 8
                image = SMALL_BLANK_IMAGE
                match state[i]:
                    case "b":
                        image = B_CHECKER_IMAGE
                    case "B":
                        image = BK_CHECKER_IMAGE
                    case "w":
                        image = W_CHECKER_IMAGE
                    case "W":
                        image = WK_CHECKER_IMAGE
                bt = Button(
                    game_frame, background="lightgrey", image=image, bd=4
                )
                bt.grid(column=x, row=y, sticky="sewn")
                spec_board[i] = bt

### function for handling labels
# Updates the labels with information about the current match the player is spectating
def updateSpectatorInfo():
    global stopButton

    if spec_game_dict["currentPlayer"] is not None:
        playerLabelText = spec_game_dict["currentPlayer"]
    else:
        playerLabelText = "No player"

    gameLabel.config(text=spec_game_dict["type"])
    playerLabel.config(text=playerLabelText)
    
    if stopButton is None:
        stopButton = Button(
                            spec_frame, background="lightgrey", bd=6,
                            text="Stop spectating", font=("", 17), command=lambda: stopSpectating()
                        )
        stopButton.place(x=560, y=300, anchor="center")
    updateSpectatorBoard()



def stopSpectating():
    # Stop the spectator connection and thread and then clear the spectating screen
    global spec_connection, spec_thread
    clearSpectatorInfo()
    if spec_connection is not None:
        if spec_connection.is_open:
            spec_connection.close()
        spec_connection = None
    if spec_thread is not None:
        spec_thread.join()
        spec_thread = None
    print("Stopped spectating")

# Clear the information about the match provided to the spectator
def clearSpectatorInfo():
    global stopButton
    gameLabel.config(text="")
    playerLabel.config(text="")
    if stopButton is not None:
        stopButton.destroy()
        stopButton = None
    for bt in spec_board.values():
        bt.destroy()
    spec_board.clear()

def spectateGame():
    global spec_thread, spec_game_dict

    def notification_handler(ch, method, properties, body):
        global spec_game_dict
        spec_game_dict = json.loads(body)
        updateSpectatorInfo()

    def spectator_thread(exchange, broker_url):
        global spec_connection

        print(exchange)
        print(broker_url)

        print("create connection")
        spec_connection = pika.BlockingConnection(
            pika.URLParameters(broker_url))
        channel = spec_connection.channel()
        channel.exchange_declare(
            exchange=exchange,
            exchange_type="fanout"
        )
        result = channel.queue_declare(queue="", exclusive=True, auto_delete=True)
        channel.queue_bind(
            exchange=exchange,
            queue=result.method.queue
        )
        channel.basic_consume(
            queue=result.method.queue,
            on_message_callback=notification_handler,
            auto_ack=True
        )
        print("start consuming")
        channel.start_consuming()

    if spec_connection is not None or spec_thread is not None:
        stopSpectating()

    # Check for a login required
    if username is None or password is None:
        notify("Login before spectating required.")
        return
    
    # Get random game
    session.headers["username"] = str(username)
    session.headers["password"] = str(password)
    resp = session.get(GAMES_ADDRESS + spec_game_id_entry.get())

    if resp.status_code == 404:
        notify("Game not found.")
        return
    elif resp.status_code != 200:
        notify("Could not get game information.")
        return

    spec_game_dict = resp.json()
    updateSpectatorInfo()
    resp = session.get(
        spec_game_dict["@controls"]["boardgame:spectate"]["href"])

    exchange = resp.json()["exchange"]
    broker_url = resp.json()["@controls"]["amqp-url"]

    spec_thread = threading.Thread(target=spectator_thread, args=(exchange, broker_url))
    spec_thread.start()

# Draw tic-tac-toe board
for x in range(3):
    for y in range(3):
        image = BLANK_IMAGE
        bt = Button(
            tic_frame, background="lightgrey", image=image, bd=6,
            command=lambda idx=x+y*3: boardInput(idx)
        )
        bt.grid(column=x, row=y, sticky="sewn")
        tic_board[x+y*3] = bt

# Draw checkers board
for x in range(8):
    for y in range(8):
        image = SMALL_BLANK_IMAGE
        bt = Button(
            chk_frame, background="lightgrey", image=image, bd=4,
            command=lambda idx=x+y*8: boardInput(idx)
        )
        bt.grid(column=x, row=y, sticky="sewn")
        chk_board[x+y*8] = bt

root.after(10, notify, "Connecting to server...")
root.after(100, fetchResourceAddresses)
root.mainloop()
leaveCurrentGame()
if spec_connection is not None:
    if spec_connection.is_open:
        spec_connection.close()
    spec_connection = None
if spec_thread is not None:
    spec_thread.join()
    spec_thread = None
session.close()

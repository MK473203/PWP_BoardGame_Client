import requests
import json

from tkinter import *
from tkinter.ttk import Notebook

# Update static IP for remote access
API_ROUTE = "http://127.0.0.1:5000"

# Height is selected so that it has room for 3 images, window top bar, and tab bar
win_size = (700, 128*3 + 65)

# Create application window
root = Tk()
root.title("Online Boardgame")

# Tic-tac-toe images, size 128x128
BLANK_IMAGE = PhotoImage(file="resources/blank_128x128.png")
X_IMAGE = PhotoImage(file="resources/X_image.png")
O_IMAGE = PhotoImage(file="resources/O_image.png")

# Checkers images, size 43x43
SMALL_BLANK_IMAGE = PhotoImage(file="resources/blank_43x43.png")
B_CHECKER_IMAGE = PhotoImage(file="resources/black_checker.png")
W_CHECKER_IMAGE = PhotoImage(file="resources/white_checker.png")
BK_CHECKER_IMAGE = PhotoImage(file="resources/black_king.png")
WK_CHECKER_IMAGE = PhotoImage(file="resources/white_king.png")

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
board_state = ""
chk_selected_piece = None

# User
username = 123
password = 123

# Variables
current_tab = "profile"
game_id = None
notification_ids = {"checkers": None, "tictactoe": None, "profile": None}

#--------------------------------------------------------------
#-- Profile tab -----------------------------------------------
#--------------------------------------------------------------
prof_frame = Frame(tabControl)
prof_frame.grid(sticky="sewn")

prof_note = Label(prof_frame, text="", font=("", 15))
prof_note.place(x=560, y=400, anchor="center")

def checkLogin():
    name = name_entry.get()
    pwd = pass_entry.get()
    with requests.Session() as ses:
        ses.headers["username"] = str(name)
        ses.headers["password"] = str(pwd)
        if len(name) == 0 or len(pwd) == 0:
            return
        resp = ses.get(API_ROUTE + "/api/users/" + name)
        global username, password
        if resp.status_code == 200:
            username = name
            password = pwd
            notify("Logged in")
        elif resp.status_code == 404:
            data = json.dumps({"name": name, "password": pwd})
            headers = {"Content-Type": "application/json"}
            register_resp = ses.post(API_ROUTE + "/api/users/", data, headers=headers)
            if register_resp.status_code == 201:
                username = name
                password = pwd
                notify("Created new user")
                return
            notify("Username does not exist\n Unable to create new user")
        elif resp.status_code == 403:
            notify("Incorrect password")

# Login frame
Label(prof_frame, text="Login", font=("", 25)).grid(row=0, column=0, sticky="nw")
Label(prof_frame, text="Username:", font=("", 15)).grid(row=1, column=0, sticky="w")
Label(prof_frame, text="Password:", font=("", 15)).grid(row=2, column=0, sticky="w")

name_entry = Entry(prof_frame)
name_entry.grid(row=1, column=1, sticky="w")
pass_entry = Entry(prof_frame)
pass_entry.grid(row=2, column=1, sticky="w")

Button(prof_frame, text="test", command=checkLogin).grid(row=3, column=0, sticky="w")

#--------------------------------------------------------------
#-- Tic-tac-toe tab -------------------------------------------
#--------------------------------------------------------------
tic_frame = Frame(tabControl)
tic_frame.grid(sticky="sewn")

# Draw tic-tac-toe game info and controls
Label(tic_frame, text="Tic-tac-toe", font=("", 30)).grid(row=0, column=4, sticky="n", padx=40)

tic_note = Label(tic_frame, text="", font=("", 15))
tic_note.place(x=560, y=400, anchor="center")

tic_team_note = Label(tic_frame, text="", font=("", 15))
tic_team_note.place(x=560, y=60, anchor="center")

Button(
    tic_frame, background="grey", bd=6,
    text="New Game", font=("", 17),
    command= lambda: getNewGame()
).place(x=560, y=120, anchor="center")

#--------------------------------------------------------------
#-- Checkers tab ----------------------------------------------
#--------------------------------------------------------------
# Create checkers container
chk_frame = Frame(tabControl)
chk_frame.grid(sticky="sewn")

# Draw checkers game info and controls
Label(chk_frame, text="Checkers", font=("", 30)).grid(row=0, column=8, sticky="n", padx=45)

chk_note = Label(chk_frame, text="", font=("", 15))
chk_note.place(x=560, y=400, anchor="center")

chk_team_note = Label(chk_frame, text="", font=("", 15))
chk_team_note.place(x=560, y=60, anchor="center")

Button(
    chk_frame, background="grey", bd=6,
    text="New Game", font=("", 17),
    command= lambda: getNewGame()
).place(x=560, y=120, anchor="center")

# Prepare and show tabs
tabControl.add(prof_frame, text="Profile")
tabControl.add(tic_frame, text="Tic-tac-toe")
tabControl.add(chk_frame, text="Checkers")
tabControl.pack(fill="both")

#--------------------------------------------------------------
#-- Functions -------------------------------------------------
#--------------------------------------------------------------
def updateCurrentTab(_):
    global current_tab
    current_tab = tabControl.tab(tabControl.select(), "text").lower().replace("-", "")
tabControl.bind("<<NotebookTabChanged>>", updateCurrentTab)

def boardInput(board_index):
    if game_id is None:
        notify("Join game before playing")
        return
    elif username is None or password is None:
        notify("Login before playing")
        return
    
    # Extract users move from variables
    global chk_selected_piece
    if current_tab == "tictactoe":
        move = board_index
    elif chk_selected_piece is None:
        # Select piece to move
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
    
    print(move)
    
    with requests.Session() as ses:
        ses.headers["username"] = str(username)
        ses.headers["password"] = str(password)
        ses.headers["Content-Type"] = "application/json"
        data = json.dumps({"move": move, "moveTime": 1})
        print(data)
        
        resp = ses.post(API_ROUTE + "/api/games/" + game_id + "/moves", data)
        if resp.status_code == 200:
            notify("Move successful")
            drawMoveLocally(move)
        else:
            print(resp.status_code)
        
def notify(text: str):
    # Select notification label of the current tab
    if current_tab == "tictactoe":
        label = tic_note
    elif current_tab == "checkers":
        label = chk_note
    elif current_tab == "profile":
        label = prof_note
    else: return
    
    # Display the notification
    label.config(text=text)
    
    # Reset notification text after 2 seconds
    global notification_ids
    if notification_ids[current_tab] is not None:
        root.after_cancel(notification_ids[current_tab])
    notification_ids[current_tab] = root.after(2000, label.config, {"text":""})

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
        

def updateBoard():
    # Updates corresponding board with new state
    # Also marks current team
    global board_state
    state = board_state[1:]
    if current_tab == "tictactoe":
        tic_team_note.config(text="Team" + str(board_state[0]))
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
        chk_team_note.config(text="Team" + str(board_state[0]))
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

def getNewGame():
    global game_id
    if username is None or password is None:
        notify("Login before playing")
        return
    with requests.session() as ses:
        # Leave previous game
        if game_id is not None:
            data = json.dumps({"move": "", "moveTime": 0})
            ses.post(API_ROUTE + "/api/games/" + game_id + "/moves", data)
            game_id = None
        
        # If a checker piece was selected, deselect it before new game
        global chk_selected_piece
        if chk_selected_piece is not None:
            chk_board[chk_selected_piece].config(bg="lightgrey")
            chk_selected_piece = None
        
        # Get random game, gametype detected from tab name
        ses.headers["username"] = str(username)
        ses.headers["password"] = str(password)
        resp = ses.get(API_ROUTE + "/api/games/random/" + current_tab)
        if resp.status_code != 200: return
        
        # Join the received game
        join_href = resp.json()["@controls"]["boardgame:join-game"]["href"]
        join_resp = ses.post(API_ROUTE + join_href)
        if join_resp.status_code != 200: return
        notify("Game joined")
        
        # Save game id and get board state
        game_id = join_href.split("/")[-2]
        game_resp = ses.get(API_ROUTE + "/api/games/" + game_id)
        if game_resp.status_code != 200: return
        
        # Save and draw board state
        global board_state
        board_state = game_resp.json()["state"]
        updateBoard()
        
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

# Start GUI loop
root.mainloop()
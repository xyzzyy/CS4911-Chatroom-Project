import time, pickle, os
from socket import *
from threading import Thread, Barrier, Condition

serverIP = 'localhost'
serverPort = 12000
line_count = 27
commands_list = ['clear',   'exit', 'quit',   'whoami', 'identitycrisis',   'seen',   'userlist', 'amialone',   'help', '?', 'commands']
local_commands_list = ['clear', 'exit', 'quit', 'help', '?', 'commands']
loggedmessages = []
bar = Barrier(2)
con = Condition()

def clear():
    # windows
    if os.name == 'nt':
        _ = os.system('cls')

    # mac and linux
    else:
        _ = os.system('clear')

def timestamp():
    now = time.gmtime()
    year = now.tm_year
    month = now.tm_mon
    day = now.tm_mday
    hour = now.tm_hour
    minute = now.tm_min
    second = now.tm_sec
    #hour += timezone
    if 3 < month < 11:
        hour += 1
    elif month == 3 and day >= 11:
        hour += 1
    elif month == 11 and day <= 4:
        hour += 1
    return time.strftime('[{}:{}:{} UTC] '.format(str(hour).zfill(2), str(minute).zfill(2), str(second).zfill(2)))

def recv_data():
    try:
        data = pickle.loads(clientSocket.recv(1024)) # ['data type', data]
    except Exception as e:
        data = None
        con.acquire()
        clear()
        print('Connection lost. Please close this window and relaunch to attempt to reconnect.')
        input()
        exit()

    return data

def send_message(user, user_hash, message):
    global serverIP, serverPort
    data = pickle.dumps(['MSG', user, user_hash, message])
    clientSocket.sendto(data, (serverIP, serverPort))
    #data = pickle.loads(clientSocket.recv(1024)) # ['MSG', message to add]
    #loggedmessages.append(timestamp()+data[1])
    #refresh()

def process_command(user, user_hash, message):
    global loggedmessages, serverIP, serverPort
    loggedmessages.append(timestamp()+user+': '+message)
    command = message[1:].split()
    refresh()
    if command[0] not in commands_list:
        loggedmessages.append(timestamp()+'Command does not exist. Type /help for a list of commands.') # send a message to just this client saying the command doesn't exist
        refresh()
        return
    if command[0] == local_commands_list[0]:
        loggedmessages = [] # clears the messages on the client
        refresh()
    elif command[0] in local_commands_list[1:2]:
        exit() # exit client
    elif command[0] in local_commands_list[3:]:
        loggedmessages.append(timestamp()+'Available commands:')
        loggedmessages.append(timestamp()+'/help or /commands: shows this message.')
        loggedmessages.append(timestamp()+'/exit or /quit: disconnects from the chat room.')
        loggedmessages.append(timestamp()+'/whoami: returns what user you are logged in as.')
        loggedmessages.append(timestamp()+'/seen {username}: returns when a user was last online.')
        loggedmessages.append(timestamp()+'/userlist: returns a list of users currently in the room.')
        refresh()
    else:
        data = pickle.dumps(['CMD', user, user_hash, command])
        clientSocket.sendto(data, (serverIP, serverPort))

def send_login_info(user, password, new_user):
    global serverIP, serverPort

    if new_user == None:
        data = pickle.dumps(['UNC', user, password, None])
    elif new_user == True:
        data = pickle.dumps(['REG', user, password, None])
    elif new_user == False:
        data = pickle.dumps(['LGN', user, password, None])

    clientSocket.sendto(data, (serverIP, serverPort))

def refresh():
    global loggedmessages
    if len(loggedmessages) > line_count:
        loggedmessages = loggedmessages[len(loggedmessages)-line_count:]
    print('===================================================== Chat Room 1 =====================================================')
    for i in loggedmessages:
        print(i)
    for i in range(line_count-len(loggedmessages)):
        print('')
    print('-----------------------------------------------------------------------------------------------------------------------')

def foreground_thread():
    refresh()
    while True:
        time.sleep(0.1)
        message = input('->')
        con.acquire()

        if message == '':
            refresh()
        elif (message[0] == '/'):
            # message is a command
            process_command(user, user_hash, message)
        else:
            # message is a message
            send_message(user, user_hash, message)

        con.release()

def background_thread():
    while True:
        data = recv_data() # ['MSG', message to add]
        con.acquire()
        loggedmessages.append(timestamp()+data[1])
        refresh()
        con.release()

# connect to server
try:
    clientSocket = socket(AF_INET, SOCK_STREAM)
    clientSocket.connect((serverIP, serverPort))
except Exception as e:
    print("Unable to connect to server. The server may currently be offline.")
    input("Please hit the enter key to end the program. \n")
    exit()

data = ['',None]
user_hash = None
while data[1] == None:
    user = input("Enter your username: ")
    send_login_info(user, None, None)
    data = recv_data()
    if data[1] == None:
        print("Username invalid. Username must be 16 characters or less, alphanumeric, and not contain any illegal words.")
        print("Please try again.")
    elif data[1] == 'ACTIVE':
        print("This account is already logged in.")
        print("Please log into a different account.")
        data[1] = None

if data[1] == False: # username check returns false
    password = input("Enter a new password: ")
    send_login_info(user, password, True) # add user and edit pass to new pass
    user_hash = recv_data()[1] # returns user hash if user was added, None if user already existed
else:
    while user_hash == None:
        password = input("Enter your password: ")
        send_login_info(user, password, False)
        user_hash = recv_data()[1]

        if (user_hash != None):
            print("you are in")
        else:
            print("no. try again.")

print('Connection established! Welcome {}!'.format(user))
time.sleep(1)

back = Thread(target=background_thread)
back.start()
fore = Thread(target=foreground_thread)
fore.start()

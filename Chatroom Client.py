import time, pickle
from socket import *
from threading import Thread, Barrier, Condition

serverIP = 'localhost'
serverPort = 12000
line_count = 27
commands_list = ['clear', 'exit', 'quit', 'whoami', 'identitycrisis', 'seen', 'userlist', 'amialone']
local_commands_list = ['clear', 'exit', 'quit']
loggedmessages = []
bar = Barrier(2)
con = Condition()

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
    command = message[1:]
    refresh()
    if command not in commands_list:
        # send a message to just this client saying the command doesn't exist
        return
    if command == local_commands_list[0]:
        loggedmessages = [] # clears the messages on the client
        refresh()
    elif command in local_commands_list[1:]:
        exit() # exit client
    else:
        data = pickle.dumps(['CMD', user, user_hash, message])
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
        loggedmessages = loggedmessages[1:]
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
        data = pickle.loads(clientSocket.recv(1024)) # ['MSG', message to add]
        con.acquire()
        loggedmessages.append(timestamp()+data[1])
        refresh()
        con.release()

# connect to server
clientSocket = socket(AF_INET, SOCK_STREAM)
clientSocket.connect((serverIP, serverPort))

# send username
user = input("Enter your username: ")
send_login_info(user, None, None)

# await user existence response
data = pickle.loads(clientSocket.recv(1024))
user_hash = None  

if data[1] == False: # username check returns false
    password = input("Enter a new password: ")
    send_login_info(user, password, True) # add user and edit pass to new pass
    user_hash = pickle.loads(clientSocket.recv(1024))[1] # returns user hash if user was added, None if user already existed
else:
    while user_hash == None:
        password = input("Enter your password: ")
        send_login_info(user, password, False)
        user_hash = pickle.loads(clientSocket.recv(1024))[1]
        if (user_hash != None):
            print("you are in")
        else:
            print("no. try again.")

print('Connection established! Welcome {}!'.format(user))
time.sleep(1)

Thread(target=background_thread).start()
Thread(target=foreground_thread).start()

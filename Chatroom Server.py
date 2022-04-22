import time, json, pickle
from socket import *
from random import randint
from hashlib import sha256
from threading import Thread

PORT = 12000
MAX_INTEGER = 2147483647
ILLEGAL_NAMES = ['template', 'server', 'admin', 'Robert\'); DROP TABLE Students;--', ''] # if i continue on this project, there will be a list of swear words added here
LEGAL_CHARACTERS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890'
connections = []
user_list = []

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

def load_users():
    global login_data
    file = open('logins.json', 'r')
    file = file.read()
    login_data = json.loads(file)

def add_user(user):
    if user in login_data: return False
    login_data[user] = login_data["template"].copy()
    login_data[user]["Username"] = user
    file = open('logins.json', 'w')
    json.dump(login_data, file, indent=4)
    return True

def edit_pass(user, password):
    global MAX_INTEGER
    salt = sha256(str(randint(0,MAX_INTEGER)).encode('utf-8')).hexdigest()
    hashed_pass = sha256((password+salt).encode('utf-8')).hexdigest()
    login_data[user]["Salt"] = salt
    login_data[user]["Hash"] = hashed_pass
    file = open('logins.json', 'w')
    json.dump(login_data, file, indent=4)
    return hashed_pass

def attempt_login(user, password):
    salt = login_data[user]["Salt"]
    hashed_pass = sha256((password+salt).encode('utf-8')).hexdigest()
    return ([login_data[user]["Hash"] == hashed_pass, hashed_pass]) # return [success or not, resulting hash]

def process_command(connectionSocket, user, data):
    command = data[3]
    if command[0] in ['whoami', 'identitycrisis']:
        data = pickle.dumps(['CMD', 'You are currently logged in as \'{}\' '.format(user)])
    elif command[0] == 'seen':
        if len(command) == 1:
            data = pickle.dumps(['CMD', 'Command form: /seen {username}. Please include a user to check.']) # include a name pls
        elif command[1] in ILLEGAL_NAMES:
            data = pickle.dumps(['CMD', '{} is not a user that exists.'.format(command[1])])
        elif command[1] in user_list:
            data = pickle.dumps(['CMD', '{} is currently online.'.format(command[1])])
        else:
            try:
                last = time.strftime("%A, %B %d %Y at %H:%M:%S UTC", time.gmtime(login_data[command[1]]["Last Seen"]))
                data = pickle.dumps(['CMD', '{} was last seen on {}.'.format(command[1], last)])
            except KeyError as e:
                data = pickle.dumps(['CMD', '{} is not a user that exists.'.format(command[1])])
    elif command[0] in ['userlist', 'amialone']:
        data = pickle.dumps(['CMD', 'Users currently in this room: ' + str(user_list)[1:-1]])
    else:
        pass # ignore the command. This should never occur as the client stops commands that don't exist.

    connectionSocket.sendto(data, (client_addr, client_port))

def connection_thread(connectionSocket, client):
    global connections
    global user_list
    user = None
    user_hash = None
    client_addr, client_port = client
    connections.append(connectionSocket)

    while True:
        try:
            bytes, clientrecv = connectionSocket.recvfrom(1024)
            data = pickle.loads(bytes) # [data type, username, hash or password, data]
        except Exception as e: #disconnect
            if user_hash == None:
                print(timestamp()+'DISCNCT || {} <no login> disconnected from the server.'.format(str(client_addr)+':'+str(client_port)))
            else:
                print(timestamp()+'DISCNCT || {} ({}) disconnected from the server.'.format(str(client_addr)+':'+str(client_port),user))
                user_list.remove(user)
                login_data[user]["Last Seen"] = time.time()

            connections.remove(connectionSocket)
            break

        if (data[0] == 'UNC'):
            name_is_illegal = False
            if len(data[1]) > 16:
                name_is_illegal = True
            elif data[1] in ILLEGAL_NAMES:
                name_is_illegal = True
            else:
                for char in data[1]:
                    if char not in LEGAL_CHARACTERS: name_is_illegal = True

            if name_is_illegal:
                data = pickle.dumps(['UNC', None]) # send back that user is illegal
            elif data[1] in user_list:
                data = pickle.dumps(['UNC', 'ACTIVE']) # send back that user is active
            elif data[1] in login_data:
                data = pickle.dumps(['UNC', True]) # send back that user exists
            else:
                data = pickle.dumps(['UNC', False]) # send back that user does not exist
            connectionSocket.sendto(data, (client_addr, client_port))
        elif (data[0] == 'REG'):
            if (add_user(data[1])): # added user to system, returns user's hash
                user = data[1]
                user_list.append(user)
                login_data[user]["Last Seen"] = time.time()
                user_hash = edit_pass(user, data[2])
                print(timestamp()+'USR_REG || {} successfully registered as {}.'.format(str(client_addr)+':'+str(client_port),user))
                data = pickle.dumps(['REG', user_hash])
            else:                   # user already existed, None returned
                data = pickle.dumps(['REG', None])
            connectionSocket.sendto(data, (client_addr, client_port))
        elif (data[0] == 'LGN'):
            result = attempt_login(data[1], data[2])
            if user in user_list: result[0] = False # do not let people get around the active user check
            if (result[0]): # if login successfull, return hash
                user = data[1]
                user_list.append(user)
                login_data[user]["Last Seen"] = time.time()
                user_hash = result[1]
                print(timestamp()+'LGNPASS || {} successfully logged in as {}.'.format(str(client_addr)+':'+str(client_port),user))
                data = pickle.dumps(['LGN', user_hash])
            else: # if not, return None
                print(timestamp()+'LGNFAIL || {} failed to log in as user {}.'.format(str(client_addr)+':'+str(client_port),data[1]))
                data = pickle.dumps(['LGN', None])
            connectionSocket.sendto(data, (client_addr, client_port))
        elif (data[0] == 'MSG'):
            if (login_data[data[1]]["Hash"] == data[2]):
                print(timestamp()+'MSG_RCV || '+data[1]+": "+data[3])
                data = pickle.dumps(['MSG', data[1]+": "+data[3]])
                for sock in connections:
                    sock.send(data)
        elif (data[0] == 'CMD'):
            process_command(connectionSocket, user, data)
        else:
            print('something has gone terribly wrong...') # this should never execute.

# Listen for TCP datagrams on port# PORT
# SO_REUSEADDR eliminates "port already in use" errors
recvSocket = socket(AF_INET, SOCK_STREAM)
recvSocket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
recvSocket.bind(('', PORT))
recvSocket.listen()
load_users()
print(timestamp()+'SVREADY || Server is Ready.')

while True:
    connectionSocket, client = recvSocket.accept()
    client_addr, client_port = client
    print(timestamp()+'CONNECT || Connection received from {} // Awaiting login.'.format(str(client_addr)+':'+str(client_port)))
    Thread(target=connection_thread, args=[connectionSocket, client]).start()

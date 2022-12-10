from PainTrigger import *

HOST = "127.0.0.1"
PORT = 60000

is_MRI = True

if __name__ == "__main__":
    SocketConnection(HOST, PORT).connect(is_MRI)

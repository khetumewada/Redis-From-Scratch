import socket
import threading

class RedisServer:
    def __init__(self, host='127.0.0.1', port=6380):
        self.host = host
        self.port = port
        self.running = False


    def start(self):
        if not self.running:
            self.running = True
            self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server.bind((self.host, self.port))
            self.server.listen(1)

            print(f"Redis server ready on  {self.host}:{self.port}")
            self.thread = threading.Thread(target=self.run)
            self.thread.start()


    def run(self):
        while self.running:
            try:
                conn, addr = self.server.accept()
                print(f"Connected at {addr}")
                self.handle_client(conn)

            except OSError:
                break

    def stop(self):
        self.running = False
        if hasattr(self, "server"):
            self.server.close()
        if hasattr(self, "thread"):
            self.thread.join()


    def handle_client(self, conn):
        while True:
            data = conn.recv(1024)
            if not data:
                break
            message = data.decode().strip()
            print(f"Received: {message}")

            parts = message.split()
            cmd = parts[0].upper()

            if cmd == "PING":
                conn.send(b"+PONG\r\n")

            elif cmd == "QUIT":
                conn.send(b"+OK\r\n")
                break

            elif cmd == "ECHO" and len(parts) > 1:
                response = " ".join(parts[1:])
                conn.send(f"${len(response)} {response}\r\n".encode())

            else:
                conn.send(b"-ERR unknown command\r\n")

        conn.close()

if __name__ == "__main__":
    server = RedisServer()
    server.start()

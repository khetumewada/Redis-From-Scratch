import socket
import threading
import time

from core.commands import CommandHandler
from core.resp import RESPParser


class RedisServer:
    def __init__(self, host='127.0.0.1', port=6380):
        self.host = host
        self.port = port
        self.running = False
        self.thread = None
        self.server = None
        self.parser = RESPParser()
        self.handler = CommandHandler()


    def start(self):
        if self.running:
            return

        self.running = True
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind((self.host, self.port))
        self.server.listen(5)

        print(f"Redis server ready on {self.host}:{self.port}")

        self.thread = threading.Thread(target=self.accept_connections, daemon=True)
        self.thread.start()


    def accept_connections(self):
        while self.running:
            try:
                conn, addr = self.server.accept()
                print(f"Connected by {addr}")
                client_thread = threading.Thread(
                    target=self.handle_client,
                    args=(conn, addr),
                    daemon=True
                )
                client_thread.start()

            except OSError:
                break

    def handle_client(self, conn, addr):
        print("Conn: ", conn)
        parser = RESPParser()
        try:
            while True:
                data = conn.recv(1024)
                if not data:
                    break

                parser.feed(data)
                commands = parser.parse_all()

                # print("commands: ", commands)

                for parts in commands:
                    if not parts:
                        continue

                    response = self.handler.handle(parts)
                    conn.sendall(response)

                    if parts[0].upper() == "QUIT":
                        return
        finally:
            conn.close()


    def stop(self):
        self.running = False

        if self.server:
            try:
                self.server.close()
            except OSError:
                pass

        if self.thread:
            self.thread.join(timeout=1)

        print("Server stopped")


if __name__ == "__main__":
    server = RedisServer()
    server.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        server.stop()
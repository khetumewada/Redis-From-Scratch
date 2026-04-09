import socket
import os


class RedisCLI:

    def __init__(self, host='127.0.0.1', port=6380):
        self.host = host
        self.port = port
        self.sock = None

    def connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(10)
        try:
            self.sock.connect((self.host, self.port))
            # print(self.sock.getsockname())
            return True
        except ConnectionRefusedError:
            print(f"Could not connect to Redis at {self.host}:{self.port}")
            print("Make sure the server is running: python server.py")
            return False

    def run(self):
        if not self.connect():
            return

        print(f"Connected to Redis at {self.host}:{self.port}")
        print("Type 'help' for commands, 'quit' to exit\n")

        while True:
            try:
                prompt = f"{self.host}:{self.port} > "
                command = input(prompt).strip()

                if command.lower() in ('quit', 'exit'):
                    print("Goodbye!")
                    break
                if command.lower() == "clear":
                    os.system("clear")
                    continue
                elif command.lower() == "help":
                    self.print_help()
                else:
                    self.send_command(command)
            except KeyboardInterrupt:
                print("\nUse 'quit' to exit")
            except EOFError:
                print("\nGoodbye!")
                break

    def send_command(self, command):
        try:
            self.sock.sendall((command + '\r\n').encode())
            response = self.sock.recv(1024).decode().strip()
            print(response)

        except Exception as e:
            print(f"Error sending command: {e}")

    def print_help(self):
        print("""
        Available commands:
        help - Show this help message
        quit - Exit the CLI
        clear - Clear the screen
        PING - Ping the server
        """)


if __name__ == "__main__":
    cli = RedisCLI()
    cli.run()
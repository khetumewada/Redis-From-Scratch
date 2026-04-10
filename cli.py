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

    def send_command(self, *args):
        if not args:
            return None

        # print("args: ", args)
        cmd = f"*{len(args)}\r\n"
        for arg in args:
            arg_bytes = str(arg).encode("utf-8")
            cmd += f"${len(arg_bytes)}\r\n{arg}\r\n"
        # print("after parse: ", cmd)

        try:
            # print("sending command: ", cmd.encode('utf-8'))
            self.sock.sendall(cmd.encode('utf-8'))
            response = self.sock.recv(1024)
            return response.decode("utf-8", errors="replace").strip()
            # response = self._receive_response()
            # print(response)
        except (BrokenPipeError, ConnectionResetError):
            print("Connection lost. Reconnecting...")
            if self.connect():
                self.sock.sendall(cmd.encode('utf-8'))
                response = self.sock.recv(1024)
                return response.decode("utf-8", errors="replace").strip()
            return None

    def run(self):
        if not self.connect():
            return

        print(f"Connected to Redis at {self.host}:{self.port}")
        print("Type 'help' for commands, 'quit' to exit\n")

        while True:
            try:
                prompt = f"{self.host}:{self.port} > "
                command = input(prompt).strip()

                if not command:
                    continue
                if command.lower() in ('quit', 'exit'):
                    print("Goodbye!")
                    break
                if command.lower() == "clear":
                    os.system("clear")
                    continue
                elif command.lower() == "help":
                    self.print_help()
                    continue

                parts = self._parse_command(command)
                print(parts)
                if not parts:
                    continue

                response = self.send_command(*parts)

                print(response)

            except KeyboardInterrupt:
                print("\nUse 'quit' to exit")
            except EOFError:
                print("\nGoodbye!")
                break

    def _parse_command(self, command):
        return command.split()

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
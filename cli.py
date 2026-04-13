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
            return self._read_response()

        except (BrokenPipeError, ConnectionResetError):
            print("Connection lost. Reconnecting...")
            if self.connect():
                self.sock.sendall(cmd.encode('utf-8'))
                return self._read_response()
            return None

    def _read_response(self):
        data = b""
        self.sock.settimeout(5.0)
        while True:
            try:
                chunk = self.sock.recv(4096)
                if not chunk:
                    break
                data += chunk
                parsed, _ = self._try_parse(data)
                if parsed is not None:
                    break
            except socket.timeout:
                break
        return self._parse_full(data)

    @staticmethod
    def _try_parse(data):
        """Try to parse, return (result, remaining) or (None, data)"""
        if not data:
            return None, data
        prefix = chr(data[0])
        if prefix in ('+', '-', ':'):
            if b'\r\n' in data:
                return True, b''
        elif prefix == '$':
            idx = data.find(b'\r\n')
            if idx == -1:
                return None, data
            length = int(data[1:idx])
            if length == -1:
                return True, b''
            if len(data) >= idx + 2 + length + 2:
                return True, b''
        elif prefix == '*':
            return True, b''
        return None, data

    @staticmethod
    def _parse_full(data):
        """Parse the full response"""
        if not data:
            return None
        prefix = chr(data[0])
        if prefix == '+':
            return 'simple', data[1:data.find(b'\r\n')].decode()
        elif prefix == '-':
            return 'error', data[1:data.find(b'\r\n')].decode()
        elif prefix == ':':
            return 'integer', int(data[1:data.find(b'\r\n')])
        elif prefix == '$':
            idx = data.find(b'\r\n')
            length = int(data[1:idx])
            if length == -1:
                return 'nil', None
            return 'bulk', data[idx + 2:idx + 2 + length].decode('utf-8', errors='replace')
        return "Unknown", data.decode('utf-8', errors='replace')

    @staticmethod
    def _format_response(response, indent=0):
        """Format a response for display"""
        prefix = '  ' * indent
        if response is None:
            return f'{prefix}(nil)'

        resp_type, value = response

        if resp_type == 'simple':
            return f'{prefix}"{value}"'
        elif resp_type == 'error':
            return f'{prefix}(error) {value}'
        elif resp_type == 'integer':
            return f'{prefix}(integer) {value}'
        elif resp_type == 'nil':
            return f'{prefix}(nil)'
        elif resp_type == 'bulk':
            return f'{prefix}"{value}"'
        elif resp_type == 'array':
            if value is None:
                return f'{prefix}(empty array)'
            if not value:
                return f'{prefix}(empty array)'
            lines = []
            for i, item in enumerate(value, 1):
                if isinstance(item, list):
                    lines.append(f'{prefix}{i})')
                    for j, subitem in enumerate(item, 1):
                        if subitem is None:
                            lines.append(f'{prefix}   {j}) (nil)')
                        else:
                            lines.append(f'{prefix}   {j}) "{subitem}"')
                elif item is None:
                    lines.append(f'{prefix}{i}) (nil)')
                elif isinstance(item, int):
                    lines.append(f'{prefix}{i}) (integer) {item}')
                else:
                    lines.append(f'{prefix}{i}) "{item}"')
            return '\n'.join(lines)
        elif resp_type == 'unknown':
            return f'{prefix}{value}'
        return f'{prefix}{value}'


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

                if command.lower() == "clear":
                    os.system("clear")
                    continue

                elif command.lower() == "help":
                    self.print_help()
                    continue

                parts = self._parse_line(command)
                # print("Parsed line: ", parts)

                if not parts:
                    continue

                response = self.send_command(*parts)
                print(self._format_response(response))

                if parts[0].lower() in ("quit", "exit"):
                    print("Goodbye!")
                    break

            except KeyboardInterrupt:
                print("\nUse 'quit to exit")
            except EOFError:
                print("\nGoodbye!")
                break

    @staticmethod
    def _parse_line(line):
        """Parse a command line, respecting quoted strings"""
        parts = []
        current = []
        in_quote = False
        quote_char = None

        for char in line:
            if in_quote:
                if char == quote_char:
                    in_quote = False
                else:
                    current.append(char)
            elif char in ('"', "'"):
                in_quote = True
                quote_char = char
            elif char == ' ':
                if current:
                    parts.append(''.join(current))
                    current = []
            else:
                current.append(char)

        if current:
            parts.append("".join(current))
        return parts

    @staticmethod
    def print_help():
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

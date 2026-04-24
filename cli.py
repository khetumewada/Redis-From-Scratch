import socket
import os
from unicodedata import lookup

from core.logger import setup_logger
from logging import DEBUG

logger = setup_logger(name="cli", level=DEBUG, console=False, log_file="cli.log")

class RedisCLI:

    def __init__(self, host='127.0.0.1', port=6380):
        self.host = host
        self.port = port
        self.db = 0
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

        logger.debug(f"Sending command: {args}")
        cmd = f"*{len(args)}\r\n"
        for arg in args:
            arg_bytes = str(arg).encode("utf-8")
            cmd += f"${len(arg_bytes)}\r\n{arg}\r\n"
        logger.debug(f"Parsed command: {cmd}")

        try:
            logger.debug(f"Sending command to Redis {cmd.encode('utf-8')}")
            self.sock.sendall(cmd.encode('utf-8'))
            logger.debug("Command sent")
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
                logger.debug(f"Received chunk of data: {chunk}")
                if not chunk:
                    break
                data += chunk
                logger.debug(f"Current data: {data}")
                parsed, _ = self._try_parse(data)
                logger.debug(f"Try Parsed: {parsed}")
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

        def parse_value(chunk):
            if not chunk:
                return None, chunk

            prefix = chr(chunk[0])
            line_end = chunk.find(b'\r\n')
            if line_end == -1:
                return None, chunk

            if prefix == '+':
                return chunk[1:line_end].decode(), chunk[line_end + 2:]

            if prefix == '-':
                return chunk[1:line_end].decode(), chunk[line_end + 2:]

            if prefix == ':':
                return int(chunk[1:line_end]), chunk[line_end + 2:]

            if prefix == '$':
                length = int(chunk[1:line_end])
                if length == -1:
                    return None, chunk[line_end + 2:]

                start = line_end + 2
                end = start + length
                if len(chunk) < end + 2:
                    return None, chunk

                value = chunk[start:end].decode('utf-8', errors='replace')
                return value, chunk[end + 2:]

            if prefix == '*':
                count = int(chunk[1:line_end])
                if count == -1:
                    return None, chunk[line_end + 2:]

                items = []
                remaining = chunk[line_end + 2:]

                for _ in range(count):
                    item, remaining = parse_value(remaining)
                    if remaining is None:
                        return None, chunk
                    items.append(item)

                return items, remaining

            return chunk.decode('utf-8', errors='replace'), b''

        value, _ = parse_value(data)
        prefix = chr(data[0])

        if prefix == '+':
            return 'simple', value
        elif prefix == '-':
            return 'error', value
        elif prefix == ':':
            return 'integer', value
        elif prefix == '$':
            if value is None:
                return 'nil', None
            return 'bulk', value
        elif prefix == '*':
            if value is None:
                return 'nil', None
            return 'array', value

        return "Unknown", data.decode('utf-8', errors='replace')


    @staticmethod
    def _format_response(response, indent=1):
        """Format a response for display"""
        prefix = ' ' * indent
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
            if value is None or not value:
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
                prompt = f"{self.host}:{self.port}[{self.db}]> "
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

                if not parts:
                    continue

                if parts[0].lower() == "select":
                    if len(parts) != 2 or not parts[1].isdigit():
                        print("Usage: select <db_index>")
                        continue
                    self.db = int(parts[1])
                    print(f"Switched to database {self.db}")

                response = self.send_command(*parts)
                logger.debug(f"Response: {response}")
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

class RESPParser:
    def __init__(self):
        self.buffer = b""

    def feed(self, data: bytes):
        self.buffer += data

    def parse_all(self):
        "Parse all available RESP commands from the buffer. Returns a list of command parts (list of strings)."
        commands = []

        while True:
            if not self.buffer:
                break

            if self.buffer[:1] != b"*":
                line_end = self.buffer.find(b"\r\n")
                if line_end == -1:
                    break

                line = self.buffer[:line_end].decode()
                self.buffer = self.buffer[line_end + 2:]
                parts = line.strip().split()
                if parts:
                    commands.append(parts)
                continue

            line_end = self.buffer.find(b"\r\n")
            if line_end == -1:
                break

            try:
                num_args = int(self.buffer[1:line_end])
            except ValueError:
                self.buffer = b""
                break

            pos = line_end + 2
            parts = []

            for _ in range(num_args):
                if pos >= len(self.buffer) or self.buffer[pos:pos + 1] != b"$":
                    return commands

                bulk_len_end = self.buffer.find(b"\r\n", pos)
                if bulk_len_end == -1:
                    return commands

                try:
                    bulk_len = int(self.buffer[pos + 1:bulk_len_end])
                except ValueError:
                    self.buffer = b""
                    return commands

                start = bulk_len_end + 2
                end = start + bulk_len

                if len(self.buffer) < end + 2:
                    return commands

                parts.append(self.buffer[start:end].decode())
                pos = end + 2

            self.buffer = self.buffer[pos:]
            if parts:
                commands.append(parts)

        return commands

class RESPError(Exception):
    pass

class RESPEncoder:
    # Encode a command (list of strings) into RESP format

    @staticmethod
    def encode(value: list) -> bytes:
        if value is None:
            return b"$-1\r\n"

        elif isinstance(value, str):
            return RESPEncoder.encode_bulk_string(value)

        elif isinstance(value, int):
            return RESPEncoder.encode_error(str(value))

        elif isinstance(value, list):
            return RESPEncoder.encode_array(value)

        elif isinstance(value, RESPError):
            return RESPEncoder.encode_error(str(value))


        elif isinstance(value, SimpleString):
            return RESPEncoder.encode_simple_string(str(value))

        else:
            return RESPEncoder.encode_bulk_string(str(value))


    @staticmethod
    def encode_bulk_string(value: str) -> bytes:
        encoded = value.encode("utf-8")
        return f'${len(encoded)}\r\n'.encode() + encoded + b'\r\n'

    @staticmethod
    def encode_integer(value: int) -> bytes:
        return f":{value}\r\n".encode()

    @staticmethod
    def encode_array(value: list) -> bytes:
        encoded = f"*{len(value)}\r\n".encode()
        for item in value:
            encoded += RESPEncoder.encode(item)
        return encoded

    # Encode an error message
    @staticmethod
    def encode_error(value: str) -> bytes:
        return f"-{value}\r\n".encode()

    @staticmethod
    def encode_simple_string(value: str) -> bytes:
        return f"+{value}\r\n".encode()

    @staticmethod
    def ok() -> bytes:
        return b'+OK\r\n'


class SimpleString:
    def __init__(self, value: str):
        self.value = value



# obj = RESPParser()
# obj.feed(b'*3\r\n$3\r\nSET\r\n$4\r\nname\r\n$5\r\nKhetu\r\n')
# print(obj.parse_all())
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


# obj = RESPParser()
# obj.feed(b'*3\r\n$3\r\nSET\r\n$4\r\nname\r\n$5\r\nKhetu\r\n')
# print(obj.parse_all())
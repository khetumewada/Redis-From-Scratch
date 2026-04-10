

class CommandHandler:

    def handle(self, parts):
        # print("Command parts: ", parts)
        cmd = parts[0].upper()

        if cmd == "PING":
            return b"+PONG\r\n"

        if cmd == "QUIT":
            return b"+OK\r\n"

        if cmd == "ECHO":
            if len(parts) < 2:
                return b"-ERR echo requires a message\r\n"
            message = " ".join(parts[1:])
            return f"${len(message)}\r\n{message}\r\n".encode()

        return b"-ERR unknown command\r\n"

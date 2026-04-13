from core.resp import RESPEncoder

class CommandHandler:
    def __init__(self):
        self.commands = {
                # Connection
                'ping': self._ping,
                'echo': self._echo,
                'quit': self._quit,

                # future commands here, for now just ping and quit
                # # Server
                # 'info': self._info,
                # 'dbsize': self._dbsize,
                # 'flushdb': self._flushdb,
                # 'time': self._time,
                #
                # # Keys
                # 'keys': self._keys,
                # 'exists': self._exists,
                # 'del': self._del,
                # 'type': self._type,
                # 'expire': self._expire,
                # 'ttl': self._ttl,
                #
                # # Strings
                # 'set': self._set,
                # 'get': self._get,
                # 'incr': self._incr,
                # 'decr': self._decr,
                # 'append': self._append,
                # 'strlen': self._strlen,
                #
                # # Lists
                # 'lpush': self._lpush,
                # 'rpush': self._rpush,
                # 'lpop': self._lpop,
                # 'lrange': self._lrange,
                # 'llen': self._llen
        }

    def handle(self, commands: list):
        if not commands:
            return RESPEncoder.encode_error("ERR empty command")

        if not isinstance(commands[0], str):
            return RESPEncoder.encode_error("ERR invalid command")

        cmd = commands[0].lower()
        args = commands[1:]
        # print(f"Received command: {cmd} {args}")

        handler = self.commands.get(cmd)
        # print(f"Handler: {handler}")
        if handler is None:
            return RESPEncoder.encode_error(
                f"ERR unknown command '{cmd}', with args beginning with: {' '.join(repr(a) for a in args[:3])}")

        try:
            result = handler(args)
            return result
        except Exception as e:
            return RESPEncoder.encode_error(str(e))

    @staticmethod
    def _ping(args) -> bytes:
        if len(args) > 1:
            return RESPEncoder.encode_error("ERR wrong number of arguments for 'ping' command")
        if args:
            return RESPEncoder.encode_bulk_string(args[0])
        return b"+PONG\r\n"

    @staticmethod
    def _echo(args):
        if not args or len(args) > 1:
            return RESPEncoder.encode_error("ERR wrong number of arguments for 'echo' command")
        return RESPEncoder.encode_bulk_string(args[0])

    @staticmethod
    def _quit(args):
        return RESPEncoder.ok()

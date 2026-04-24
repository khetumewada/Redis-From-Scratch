from core.datastore import DataStore
from core.resp import RESPEncoder


class CommandHandler:
    def __init__(self):
        self.store = DataStore()
        self.commands = {
            # Connection
            'ping': self._ping,
            'echo': self._echo,
            'quit': self._quit,

            # future commands here, for now just ping and quit
            # # Server
            'select': self._select,
            # 'info': self._info,
            # 'dbsize': self._dbsize,
            # 'flushdb': self._flushdb,
            # 'time': self._time,
            #
            # # Keys
            'keys': self._keys,
            # 'exists': self._exists,
            # 'del': self._del,
            # 'type': self._type,
            'expire': self._expire,
            'ttl': self._ttl,
            #
            # # Strings
            'set': self._set,
            'get': self._get,
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

    def handle(self, commands: list, client_state) -> bytes:
        if not commands:
            return RESPEncoder.encode_error("ERR empty command")

        if not isinstance(commands[0], str):
            return RESPEncoder.encode_error("ERR invalid command")

        cmd = commands[0].lower()
        args = commands[1:]
        print(f"Received command: {cmd} {args}")

        handler = self.commands.get(cmd)
        # print(f"Handler: {handler}")
        if handler is None:
            return RESPEncoder.encode_error(
                f"ERR unknown command '{cmd}', with args beginning with: {' '.join(repr(a) for a in args[:3])}")

        try:
            result = handler(args, client_state)
            return result
        except Exception as e:
            return RESPEncoder.encode_error(str(e))

    @staticmethod
    def _ping(args, cs) -> bytes:
        if len(args) > 1:
            return RESPEncoder.encode_error("ERR wrong number of arguments for 'PING' command")
        if args:
            return RESPEncoder.encode_bulk_string(args[0])
        return b"+PONG\r\n"

    @staticmethod
    def _echo(args, cs):
        if not args or len(args) > 1:
            return RESPEncoder.encode_error("ERR wrong number of arguments for 'ECHO' command")
        return RESPEncoder.encode_bulk_string(args[0])

    @staticmethod
    def _quit(args, cs):
        return RESPEncoder.ok()

    def _select(self, args, cs):
        if len(args) != 1:
            return RESPEncoder.encode_error("ERR wrong number of arguments for 'SELECT'")

        try:
            db_index = int(args[0])
        except ValueError:
            return RESPEncoder.encode_error("ERR invalid DB index")

        if db_index < 0 or db_index >= len(self.store.databases):
            return RESPEncoder.encode_error("ERR DB index out of range")

        cs["db"] = db_index
        return RESPEncoder.ok()

    def _keys(self, args, cs) -> bytes:
        if not args or len(args) != 1:
            return RESPEncoder.encode_error("ERR wrong number of arguments for 'KEYS'")
        pattern = args[0]
        print(f"Pattern: {pattern}")
        db = cs["db"]
        result = self.store.keys(pattern, db=db)
        return RESPEncoder.encode_array(result)

    def _expire(self, args, cs):
        if len(args) < 2:
            return RESPEncoder.encode_error("ERR wrong number of arguments for 'EXPIRE'")
        try:
            seconds = int(args[1])
        except ValueError:
            return RESPEncoder.encode_error("ERR invalid expire time")
        result = self.store.expire(cs["db"], args[0], seconds * 1000)
        return RESPEncoder.encode_integer(1 if result else 0)

    def _ttl(self, args, cs):
        if len(args) != 1:
            return RESPEncoder.encode_error("ERR wrong number of arguments for 'TTL'")
        result = self.store.ttl(cs["db"], args[0])
        return RESPEncoder.encode_integer(result)

    def _set(self, args, cs):
        if len(args) < 2:
            return RESPEncoder.encode_error("ERR wrong number of arguments for 'SET'")
        key, value = args[0], args[1]
        ex, px = None, None
        get = False
        i = 2
        while i < len(args):
            if args[i].upper() == "EX" and i + 1 < len(args):
                try:
                    ex = int(args[i + 1]) * 1000
                except ValueError:
                    return RESPEncoder.encode_error("ERR invalid EX value")
                i += 2
            elif args[i].upper() == "PX" and i + 1 < len(args):
                try:
                    px = int(args[i + 1])
                except ValueError:
                    return RESPEncoder.encode_error("ERR invalid PX value")
                i += 2
            elif args[i].upper() == "GET":
                get = True
                i += 1
            else:
                return RESPEncoder.encode_error("ERR syntax error")

        result = self.store.set(cs["db"], key, value, ex, px, get)
        print(f"Set result: {result}")
        if get:
            return RESPEncoder.encode(result)
        if result is True:
            return RESPEncoder.ok()
        return RESPEncoder.null()

    def _get(self, args, cs):
        if len(args) != 1:
            return RESPEncoder.encode_error("ERR wrong number of arguments for 'GET'")
        key = args[0]
        db = cs["db"]
        return self.store.get(key, db)

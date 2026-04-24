from typing import List
import time

from core.resp import RESPEncoder

class RedisDataType:
    STRING = 'string'

class DataStore:
    def __init__(self, db_count=16):
        self.databases = [{} for _ in range(db_count)]
        self.expiry = [{} for _ in range(db_count)]
        self.db_count = db_count

    def _db (self, db_index):
        return self.databases[db_index]

    def _expiry (self, db_index: int):
        return self.expiry[db_index]

    def _check_expiry(self, db_index: int, key: str) -> bool:
        exp = self._expiry(db_index)
        if key in exp:
            if time.time() * 1000 > exp[key]:
                db = self._db(db_index)
                del exp[key]
                del db[key]
                return False
        return key in self._db(db_index)

    # Keys command with pattern support (only '*' for now)
    def keys(self, pattern: str, db=0) -> List[str]:
        database, expiry = self._db(db), self._expiry(db)
        if pattern == "*":
            return list(database.keys())
        if pattern in database:
            return [pattern]
        else:
            # For simplicity, only support '*' pattern for now
            return []

    def expire(self, db_index: int, key: str, expiry: int):
        database, expiry_db = self._db(db_index), self._expiry(db_index)
        if not self._check_expiry(db_index, key):
            return False
        expiry_db[key] = time.time() * 1000 + expiry
        return True

    def ttl(self, db_index: int, key: str):
        database, expiry_db = self._db(db_index), self._expiry(db_index)
        if not self._check_expiry(db_index, key):
            return -2  # Key does not exist
        if key not in expiry_db:
            return -1  # Key exists but has no expiry
        ttl_ms = expiry_db[key] - time.time() * 1000
        return int(ttl_ms / 1000) if ttl_ms > 0 else -2

    def set(self, db_index: int, key: str, value: str, ex, px, get: bool):
        database, expiry = self._db(db_index), self._expiry(db_index)
        existing = None
        if get:
            existing = self.get(key, db_index)

        print(f"Existing value: {existing}")
        database[key] = (RedisDataType.STRING, value)

        if ex is not None:
            expiry[key] = (time.time() * 1000) + ex
        elif px is not None:
            expiry[key] = (time.time() * 1000) + px

        if get and existing is not None:
            return existing
        return True

    def get(self, key, db_index):
        database, expiry = self._db(db_index), self._expiry(db_index)
        if not self._check_expiry(db_index, key):
            return None
        if key not in database:
            return RESPEncoder.null()
        dtype, value = database[key]
        if dtype != RedisDataType.STRING:
            return RESPEncoder.encode_error("WRONGTYPE Operation against a key holding the wrong kind of value")
        return RESPEncoder.encode_bulk_string(value)
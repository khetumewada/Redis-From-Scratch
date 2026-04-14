import asyncio
from logging import DEBUG, INFO

from core.commands import CommandHandler
from core.resp import RESPParser
from core.logger import setup_logger

logger = setup_logger(name="server", level=INFO, log_file="server.log")

class RedisServer:
    def __init__(self, host='127.0.0.1', port=6380):
        self.host = host
        self.port = port
        self.server = None
        self.parser = RESPParser()
        self.handler = CommandHandler()

    async def start(self):
        if self.server is not None:
            return

        self.server = await asyncio.start_server(
            self.handle_client,
            self.host,
            self.port
        )

        addr = ", ".join(str(sock.getsockname()) for sock in self.server.sockets or [])
        logger.info(f"Redis server ready on {addr}")

        async with self.server:
            await self.server.serve_forever()

    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        addr = writer.get_extra_info('peername')
        logger.info(f"Connected by {addr}")

        parser = RESPParser()
        try:
            while True:
                data = await reader.read(1024)
                logger.debug(f"Received data: {data}")
                if not data:
                    break

                parser.feed(data)
                commands = parser.parse_all()
                logger.debug(f"Raw data: {data}")
                logger.debug(f"Parsed commands: {commands}")
                for parts in commands:
                    if not parts:
                        continue

                    response = self.handler.handle(parts)
                    writer.write(response)
                    await writer.drain()

                    if parts[0].lower() in ("quit", "exit"):
                        writer.close()
                        await writer.wait_closed()
                        return

        except Exception as e:
            logger.error(f"Error with {addr}: {e}")

        finally:
            writer.close()
            await writer.wait_closed()

    async def stop(self):
        if self.server is not None:
            self.server.close()
            await self.server.wait_closed()
            self.server = None

            logger.info("Server stopped")


async def main():
    server = RedisServer()
    try:
        await server.start()
    except (asyncio.CancelledError, KeyboardInterrupt):
        logger.info("Shutting down Redis server...")
        await server.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass

import asyncio
import aioping

async def main():
    print(await aioping.ping("8.8.8.8"))

asyncio.run(main())
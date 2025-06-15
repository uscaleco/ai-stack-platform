import asyncpg
import os

class Postgres:
    def __init__(self):
        self._pool = None

    async def get_pool(self):
        if not self._pool:
            self._pool = await asyncpg.create_pool(os.getenv("DATABASE_URL"))
        return self._pool

    async def fetch(self, sql, *args):
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            return await conn.fetch(sql, *args)

    async def execute(self, sql, *args):
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            return await conn.execute(sql, *args)

    async def fetchrow(self, sql, *args):
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            return await conn.fetchrow(sql, *args)

postgres = Postgres() 
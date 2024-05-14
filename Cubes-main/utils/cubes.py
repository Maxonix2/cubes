import random
from utils.core import logger
from pyrogram import Client
from pyrogram.raw.functions.messages import RequestWebView
import asyncio
from urllib.parse import unquote
from data import config
import aiohttp
from aiohttp_proxy import ProxyConnector
from better_proxy import Proxy
from pyrogram.errors import Unauthorized, UserDeactivated, AuthKeyUnregistered

# HTTP request headers
headers = {
    'Accept': '*/*',
    'Accept-Language': 'ru,en;q=0.9,en-GB;q=0.8,en-US;q=0.7',
    'Connection': 'keep-alive',
    'Origin': 'https://server.questioncube.xyz/game',
    'Referer': 'https://server.questioncube.xyz/game',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'same-site',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0',
    'sec-ch-ua': '"Microsoft Edge";v="123", "Not:A-Brand";v="8", "Chromium";v="123", "Microsoft Edge WebView2";v="123"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
}

# Class for Pyrogram client
class Start:
    def __init__(self, tg_client: Client):
        self.session_name = tg_client.name
        self.tg_client = tg_client

    async def main(self, proxy: str | None):
        async with aiohttp.ClientSession(headers=headers) as http_client:
            await self.tg_client.start()  # Start client session before usage
            while True:
                try:
                    await asyncio.sleep(random.uniform(4, 12))

                    tg_web_data = await self.get_tg_web_data(proxy=proxy)
                    balance, energy = await self.login(tg_web_data, http_client=http_client)

                    while True:
                        if energy > 150:
                            balance, energy, boxes, block = await self.mining(http_client=http_client)

                            logger.success(f"Thread {self} | Block broken. Balance: {balance}; Energy: {energy}; Boxes: {boxes}")
                            await asyncio.sleep(random.uniform(4, 12))

                        elif energy <= 150 and balance >= 50:
                            balance, energy, energy_buy = await self.buy_energy(balance, http_client=http_client)
                            logger.success(f"Thread {self} | Bought {energy_buy} energy.")

                        else:
                            logger.warning(f"Thread {self} | Energy is less than 150, thread sleeps.")
                            await asyncio.sleep(random.uniform(4, 12))
                            balance, energy = await self.login(tg_web_data, http_client=http_client)

                except Exception as e:
                    logger.error(f"Thread {self} | Error: {e}")

    async def get_tg_web_data(self, proxy: str | None) -> str:
        if proxy:
            proxy = Proxy.from_str(proxy)
            proxy_dict = dict(
                scheme=proxy.protocol,
                hostname=proxy.host,
                port=proxy.port,
                username=proxy.login,
                password=proxy.password
            )
        else:
            proxy_dict = None

        self.tg_client.proxy = proxy_dict

        web_view = await self.tg_client.invoke(RequestWebView(
            peer=await self.tg_client.resolve_peer('cubesonthewater_bot'),
            bot=await self.tg_client.resolve_peer('cubesonthewater_bot'),
            platform='android',
            from_bot_menu=False,
            url='https://www.thecubes.xyz'
        ))
        auth_url = web_view.url
        return unquote(string=unquote(string=auth_url.split('tgWebAppData=')[1].split('&tgWebAppVersion')[0]))

    async def login(self, tg_web_data, http_client: aiohttp.ClientSession):
        json_data = {"initData": tg_web_data}
        async with http_client.post("https://server.questioncube.xyz/auth", json=json_data) as resp:
            resp_json = await resp.json()
            self.token = resp_json.get("token")
            return int(resp_json.get("drops_amount")), int(resp_json.get("energy"))

    async def mining(self, http_client: aiohttp.ClientSession):
        while True:
            async with http_client.post("https://server.questioncube.xyz/game/mined", json={"token": self.token}) as resp:
                try:
                    resp_json = await resp.json()
                    return int(resp_json.get("drops_amount")), int(resp_json.get("energy")), int(resp_json.get("boxes_amount")), int(resp_json.get("mined_count"))
                except:
                    await asyncio.sleep(random.uniform(4, 12))

    async def buy_energy(self, balance: int, http_client: aiohttp.ClientSession):
        if balance >= 250:
            proposal_id = 3
            energy_buy = 500
        elif 250 > balance >= 125:
            proposal_id = 2
            energy_buy = 250
        elif 125 > balance >= 50:
            proposal_id = 1
            energy_buy = 100

        json_data = {"proposal_id": proposal_id, "token": self.token}
        async with http_client.post("https://server.questioncube.xyz/game/rest-proposal/buy", json=json_data) as resp:
            resp_json = await resp.json()
            return int(resp_json.get("drops_amount")), int(resp_json.get("energy")), energy_buy

async def run_claimer(tg_client: Client, proxy: str | None):
    await Start(tg_client=tg_client).main(proxy=proxy)

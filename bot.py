import asyncio
import pyppeteer
import base64
import openai
import time

from twitchio.ext import commands


openai_key = open(".openai-key").read().strip()
openapi_client = openai.AsyncOpenAI(api_key=openai_key)


TWITCH_ACCESS_TOKEN = open(".twitch-access-token").read().strip()
GOOGLE_CHROME_SHIM = "/usr/bin/google-chrome-unstable"
TWITCH_URL = "https://www.twitch.tv/sumcademy"


class Bot(commands.Bot):
    def __init__(self):
        super().__init__(
            token=TWITCH_ACCESS_TOKEN,
            prefix="!",
            initial_channels=["sumcademy"],
        )

    async def screenshot_loop(self):
        while True:
            ss_b64 = await self.page.screenshot(type="png", encoding="base64")
            messages.append(
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "What's the streamer up to now?"},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{ss_b64}"},
                        },
                    ],
                }
            )
            response = await send_messages()
            content = response.choices[0].message.content
            messages.append(
                {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "text",
                            "text": content,
                        }
                    ],
                }
            )
            await self.get_channel("sumcademy").send(content[:500])
            await asyncio.sleep(2.5 * 60)

    async def event_ready(self):
        print(f"Logged in as | {self.nick}")
        print(f"User id is | {self.user_id}")

        print("launching browser")
        self.browser = await pyppeteer.launch(
            {
                "headless": True,
                "dumpio": True,
                "executablePath": GOOGLE_CHROME_SHIM,
                "defaultViewport": {
                    "width": 1920,
                    "height": 1080,
                    "deviceScaleFactor": 2,
                },
            }
        )
        self.page = await self.browser.newPage()
        await self.page.goto(TWITCH_URL, waitUntil="networkidle0")
        # wait 10 seconds for everything to get loaded and then create the task
        await asyncio.sleep(10)
        asyncio.create_task(self.screenshot_loop())

    async def event_message(self, message):
        if message.echo:
            return

        # Print the contents of our message to console...
        msg = f"<{message.author.name}> {message.content}"
        messages.append(
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": msg,
                    }
                ],
            }
        )

        response = await send_messages()
        content = response.choices[0].message.content
        messages.append(
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": content,
                    }
                ],
            }
        )

        if content != ".":
            await message.channel.send(content)


TOPIC = "Training a GPT using the Fountainhead | Python, Rust"

messages = [
    {
        "role": "system",
        "content": [
            {
                "type": "text",
                "text": "You're an assistant for sumcademy, a coding Twitch streamer. Every 2.5 minutes, you will be "
                "given a new screenshot of the stream. You're going to keep us updated on what's going on in the "
                "stream, specifically regarding the project that the streamer is working on, or rather what the "
                "streamer is doing, or to be more general, what is going on on the stream.\n\n"
                f"The topic of today's stream is {TOPIC}\n\n"
                "However, I'd like you to look deeply into the image, specifically the streamer's cursor position, and "
                "the differences between the old code / what's going on, and what's going on now.\n\n"
                "Your messages will be directly relayed into the Twitch chat, so make sure your responses follow a logical progression."
                "The messages shouldn't be very long, just a couple of sentences summary.\n\n"
                "Additionally, messages from the Twitch chat will be streamed in using `<author> message` format. "
                "If there's anything to respond to, give the response, otherwise just respond with . as the entire message string."
                "Tend to NOT respond to things people say unless it's obviously a QUESTION that you can answer.",
            }
        ],
    },
]


async def send_messages():
    return await async_retry(
        lambda: openapi_client.chat.completions.create(
            model="gpt-4-vision-preview",
            messages=messages,
            max_tokens=500,
        )
    )


async def async_retry(f):
    for i in range(6):
        try:
            if i > 0:
                await asyncio.sleep((2**i) * 0.5)
            return await f()
        except Exception as e:
            print(f"re-trying after exception: {e}", flush=True)
    raise Exception("re-try count exhausted")


bot = Bot()
bot.run()

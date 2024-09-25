import discord
from discord.ext import tasks
from discord import app_commands
import json
import os
import time
from PIL import Image, ImageDraw, ImageFont
import sys
from colorama import init, Fore, Style
from termcolor import cprint
from pyfiglet import figlet_format
from datetime import datetime, timedelta
import numpy as np

#-------------Configuration-------------#

debug = False  # Please if you're gonna host one disable this, it will flood the console

canvas_size = (100, 100)
pixel_size = 10

event_duration = timedelta(days=7)
event_start_time = datetime(2024, 8, 25, 20, 0)
delay_time = timedelta(seconds=30)

db_file = "database.json"

#---------------------------------------#


init(autoreset=True)

cprint(figlet_format('D/PLACE'), 'yellow', attrs=['bold'])

print(f"{Fore.GREEN}Loading bot...{canvas_size} {Style.RESET_ALL}")

canvas_size = (canvas_size[0] + 1, canvas_size[1] + 1)
if debug:
    print("")
    print(f"{Fore.GREEN}Canvas size: {canvas_size} {Style.RESET_ALL}")

with open('token.json') as token_file:
    tkn = json.load(token_file)
TOKEN = tkn['token']

if not TOKEN:
    cprint(figlet_format('ERROR'), 'red', attrs=['bold'])
    print(f"{Fore.RED}The token is empty! Please put your bot token in token.json")
    time.sleep(5)
    exit()

if os.path.exists(db_file):
    with open(db_file, 'r') as f:
        data = json.load(f)
        canvas = data['canvas']
        start_time = datetime.fromisoformat(data['start_time'])
        participants = data.get('participants', {})
        last_pixel_time = {int(k): datetime.fromisoformat(v) for k, v in data.get('last_pixel_time', {}).items()}
else:
    canvas = [[(255, 255, 255) for _ in range(canvas_size[0])] for _ in range(canvas_size[1])]
    start_time = event_start_time
    participants = {}
    last_pixel_time = {}

end_time = start_time + event_duration

def save_state():
    with open(db_file, 'w') as f:
        json.dump({
            'canvas': canvas,
            'start_time': start_time.isoformat(),
            'participants': participants,
            'last_pixel_time': {k: v.isoformat() for k, v in last_pixel_time.items()}
        }, f)

def generate_canvas_image():
    gridColor = (200, 200, 200)
    image_width = canvas_size[0] * pixel_size + pixel_size
    image_height = canvas_size[1] * pixel_size + pixel_size

    # Using NumPy array for better performance in canvas operations
    image_array = np.ones((image_height, image_width, 3), dtype=np.uint8) * 255  # Start with a white background

    # Draw the canvas pixels
    for y in range(canvas_size[1]):
        for x in range(canvas_size[0]):
            color = canvas[y][x]
            if isinstance(color, list) and len(color) == 3:
                color = tuple(color)
            x_start = pixel_size + x * pixel_size
            y_start = pixel_size + y * pixel_size
            x_end = x_start + pixel_size
            y_end = y_start + pixel_size
            image_array[y_start:y_end, x_start:x_end] = color

    # Draw grid lines
    for i in range(0, canvas_size[0] + 1):
        x_line = pixel_size + i * pixel_size
        image_array[:, x_line:x_line + 1] = gridColor

    for i in range(0, canvas_size[1] + 1):
        y_line = pixel_size + i * pixel_size
        image_array[y_line:y_line + 1, :] = gridColor

    # Create Image from array
    image = Image.fromarray(image_array, 'RGB')
    draw = ImageDraw.Draw(image)

    # Draw coordinates
    font = ImageFont.load_default()
    for i in range(canvas_size[0]):
        text = str(i)
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        draw.text((pixel_size + i * pixel_size + (pixel_size - text_width) / 2, 0), text, fill=(0, 0, 0), font=font)

    for i in range(canvas_size[1]):
        text = str(i)
        bbox = draw.textbbox((0, 0), text, font=font)
        text_height = bbox[3] - bbox[1]
        draw.text((0, pixel_size + i * pixel_size + (pixel_size - text_height) / 2), text, fill=(0, 0, 0), font=font)

    return image

def get_leaderboard():
    leaderboard = sorted(participants.items(), key=lambda item: item[1], reverse=True)
    return "\n".join([f"{user.name}: {count} pixels" for user_id, count in leaderboard])

colorsRgb = {
    'red': (255, 0, 0),
    'green': (0, 255, 0),
    'blue': (0, 0, 255),
    'yellow': (255, 255, 0),
    'cyan': (0, 255, 255),
    'magenta': (255, 0, 255),
    'white': (255, 255, 255),
    'black': (0, 0, 0),
    'orange': (255, 165, 0),
    'purple': (128, 0, 128),
    'pink': (255, 192, 203),
    'gray': (128, 128, 128),
    'gold': (255, 215, 0)
}

class RPlaceBot(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()

bot = RPlaceBot(intents=discord.Intents.default())

@bot.event
async def on_ready():
    cprint(figlet_format(f'Bot running as {bot.user}'), 'blue')
    check_event_end.start()

@bot.tree.command(name="info", description="See info about d/place")
async def info(interaction: discord.Interaction):
    now = datetime.now()

    if now < event_start_time:
        remaining_start_time = event_start_time - now
        days, seconds = remaining_start_time.days, remaining_start_time.seconds
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        seconds = seconds % 60

        info_message = (
            f"The event hasn't started yet! It will start in: {days}d {hours}h {minutes}m {seconds}s\n\n"
            f"Leaderboard will be available once the event starts."
        )
        await interaction.response.send_message(info_message)
        return

    remaining_time = end_time - now
    days, seconds = remaining_time.days, remaining_time.seconds
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60

    leaderboard = []
    for user_id, count in sorted(participants.items(), key=lambda item: item[1], reverse=True):
        user = await bot.fetch_user(int(user_id))
        leaderboard.append(f"{user.name}: {count} pixels")

    leaderboard_text = "\n".join(leaderboard)

    with open("leaderboard.txt", "w") as file:
        file.write(leaderboard_text)

    info_message = (
        f"Time left: {days}d {hours}h {minutes}m {seconds}s\n\n"
        f"Leaderboard will be sent on the next message"
    )

    await interaction.response.send_message(info_message)

    with open("leaderboard.txt", "rb") as file:
        await interaction.followup.send(file=discord.File(file, "leaderboard.txt"))


@bot.tree.command(name="canvas", description="Shows the current canvas")
async def info(interaction: discord.Interaction):
    image = generate_canvas_image()
    image.save("canvas.png")

    with open("canvas.png", "rb") as f:
        await interaction.response.send_message(file=discord.File(f, "canvas.png"))

@bot.tree.command(name="dplace", description="Place a pixel on the canvas")
@app_commands.describe(x="X coordinate", y="Y coordinate", color="hex color (eg, FF0000), rgb color (eg, 255,0,0), or just type the color name")
async def dplace(interaction: discord.Interaction, x: int, y: int, color: str):
    now = datetime.now()

    if now < event_start_time:
        remaining_start_time = event_start_time - now
        days, seconds = remaining_start_time.days, remaining_start_time.seconds
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        seconds = seconds % 60
        await interaction.response.send_message(
            f"The event hasn't started yet! It will start in: {days}d {hours}h {minutes}m {seconds}s"
        )
        return

    if datetime.now() > end_time:
        await interaction.response.send_message(f"The event has ended! Thanks to everyone who participated :) do /info to see the leaderboard or /canvas to see the final canvas")
        return

    if not (0 <= x < canvas_size[0] and 0 <= y < canvas_size[1]):
        if debug:
            print("Invalid coordinates: x: ", x, " | y: ", y, " | canvas size: ", canvas_size)
        await interaction.response.send_message("Invalid coordinates! Must be in the canvas!")
        return

    user_id = interaction.user.id
    now = datetime.now()

    if user_id in last_pixel_time and now - last_pixel_time[user_id] < delay_time:
        remaining_cooldown = delay_time - (now - last_pixel_time[user_id])
        await interaction.response.send_message(f"You must wait {remaining_cooldown.seconds} seconds before placing another pixel!")
        return

    color = color.lower()
    if color.startswith('#') and len(color) == 7:
        try:
            r, g, b = tuple(int(color[i:i+2], 16) for i in (1, 3, 5))
        except ValueError:
            await interaction.response.send_message("Invalid hex color!")
            return
    elif color.count(',') == 2:
        try:
            r, g, b = tuple(int(c) for c in color.split(','))
            if not all(0 <= value <= 255 for value in (r, g, b)):
                raise ValueError
        except ValueError:
            await interaction.response.send_message("Invalid RGB color format! Use 'r,g,b' format with values between 0 and 255.")
            return
    elif color in colorsRgb:
        r, g, b = colorsRgb[color]
    else:
        await interaction.response.send_message("Invalid color format or name!")
        return

    canvas[y][x] = (r, g, b)
    last_pixel_time[user_id] = now

    if user_id in participants:
        participants[user_id] += 1
    else:
        participants[user_id] = 1

    save_state()

    image = generate_canvas_image()
    image.save("canvas.png")

    with open("canvas.png", "rb") as f:
        await interaction.response.send_message(file=discord.File(f, "canvas.png"))

@tasks.loop(seconds=60)
async def check_event_end():
    if datetime.now() > end_time:
        check_event_end.stop()

bot.run(TOKEN)

import requests

# Replace with your actual bot token from BotFather
BOT_TOKEN = "7093436536:AAFX-2X9W_DNO6-1lsCrnExFLhsxGWyU1lg"

# Telegram API endpoint for setting a profile photo
url = f"https://api.telegram.org/bot{BOT_TOKEN}/setUserProfilePhotos"

# Open the profile photo file
with open("gigiP2bot_userphoto.png", "rb") as photo:
    files = {"photo": photo}
    response = requests.post(url, files=files)

# Print the response from Telegram
print(response.json())

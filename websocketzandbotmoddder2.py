import websockets
import asyncio
import json
import requests
import sys
import uuid
import re
from datetime import datetime, timezone
import time
import requests, logging
from datetime import datetime
from dataclasses import dataclass, asdict
from ProntoBackend.pronto import *
from ProntoBackend.readjson import *
from ProntoBackend.systemcheck import *
auth_path, chats_path, bubbles_path, loginTokenJSONPath, authTokenJSONPath, verificationCodeResponseJSONPath, settings_path, encryption_path, logs_path, settingsJSONPath, keysJSONPath, bubbleOverviewJSONPath, users_path = createappfolders()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
class BackendError(Exception):
    pass
# API Base URL and Credentials
api_base_url = "https://stanfordohs.pronto.io/"
accesstoken = ""
user_id = "5301889"
int_user_id = 5301889
main_bubble_ID = "4209040"
log_channel_ID = "4251207"
global media
media = []
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {accesstoken}",
}
global warning_count
warning_count = []
settings = [1, 1, 1, 1, 1]
global flagsetting
flagsetting = 3
global ratelimitseconds
ratelimitseconds = 5
global message_max_length
global orgID
orgID = 2245
message_max_length = 750
global is_bot_on
is_bot_on = 0
global warning_threshold
warning_threshold = 3
stored_messages = []
warning_message = ""
log_message = ""
last_message_id = ""
global adminrules
adminrules = ""
global rules
rules = ""

# Bad Words List URL
URL = "https://raw.githubusercontent.com/MrSpots1/MrSpots1.github.io/main/words%20%5BMConverter.eu%5D.txt"

# Download Bad Words List
def download_wordlist(url):
    response = requests.get(url)
    if response.status_code == 200:
        words = response.text.split("\n")
        return set(word.strip().lower() for word in words if word.strip())
    else:
        print("Failed to download word list.")
        return set()

BAD_WORDS = download_wordlist(URL)
BAD_WORDS_REGEX = re.compile(r"\b(" + "|".join(re.escape(word) for word in BAD_WORDS) + r")\b", re.IGNORECASE)

# WebSocket and API Functions
def chat_auth(bubble_id, bubble_sid, socket_id):
    url = f"{api_base_url}api/v1/pusher.auth"
    data = {
        "socket_id": socket_id,
        "channel_name": f"private-bubble.{bubble_id}.{bubble_sid}"
    }
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    bubble_auth = response.json().get("auth")
    print("Bubble Connection Established.")
    return bubble_auth

async def connect_and_listen(bubble_id, bubble_sid):
    uri = "wss://ws-mt1.pusher.com/app/f44139496d9b75f37d27?protocol=7&client=js&version=8.3.0&flash=false"
    async with websockets.connect(uri) as websocket:
        response = await websocket.recv()
        print(f"Received: {response}")

        data = json.loads(response)
        if "data" in data:
            inner_data = json.loads(data["data"])
            socket_id = inner_data.get("socket_id", None)

            data = {
                "event": "pusher:subscribe",
                "data": {
                    "channel": f"private-bubble.{bubble_id}.{bubble_sid}",
                    "auth": chat_auth(bubble_id, bubble_sid, socket_id)
                }
            }
            await websocket.send(json.dumps(data))

            if socket_id:
                print(f"Socket ID: {socket_id}")
            else:
                print("Socket ID not found in response")

        # Listen for incoming messages
        async for message in websocket:
            if message == "ping":
                await websocket.send("pong")
            else:
                msg_data = json.loads(message)
                event_name = msg_data.get("event", "")
                if event_name == "App\\Events\\MessageAdded":
                    msg_content = json.loads(msg_data.get("data", "{}"))
                    msg_text = msg_content.get("message", {}).get("message", "")
                    msg_user = msg_content.get("message", {}).get("user", {})
                    user_firstname = msg_user.get("firstname", "Unknown")
                    user_lastname = msg_user.get("lastname", "User")
                    user_id_websocket = msg_user.get("id", "User")
                    timestamp = msg_content.get("message", {}).get("created_at", "Unknown timestamp")
                    timestamp = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
                    msg_media = msg_content.get("message", {}).get("messagemedia", [])
                    

                    process_message(msg_text, user_firstname, user_lastname, timestamp, msg_media, user_id_websocket)



async def main(bubble_id, bubble_sid):
    '"send_message("Warning: The Moderation Bot is now active and watching for criminals...", main_bubble_ID, media)"'
    await connect_and_listen(bubble_id, bubble_sid)


# Mod Bot Logic for Processing Messages
def process_message(msg_text, user_firstname, user_lastname, timestamp, msg_media, user_id_websocket):
    matches = list(filter(lambda row: row[0] == user_id_websocket, warning_count))
    if matches.__len__() == 0:
        warning_count.append([user_id_websocket, 0])
    msg_text_lower = msg_text.lower()
    msg_id = str(uuid.uuid4())  # Simulate unique message ID
    sent_user_id = user_id_websocket  # This would be the actual user ID for the message sender
    # Check for Commands in the message
    check_for_commands(msg_text_lower, sent_user_id)
    if (is_bot_on == 1):
        if settings[1] == 1:
            # Log the message
            log(msg_text, sent_user_id, msg_media)
        
        # Preform moderation checks
        moderate_message(msg_text_lower, sent_user_id, matches, timestamp)

# Check for any commands in the message
def check_for_commands(msg_text, user_sender_id):
    """Check for any commands in the message."""
    if msg_text.startswith("!rules"):
        if rules == "":
            send_message("Warning: No rules have been set.", main_bubble_ID, media)
        else:
            send_message(f"Warning: The rules are: {rules}", main_bubble_ID, media)
    elif msg_text.startswith("!adminrules"):
        if adminrules == "":
            send_message("Warning: No admin rules have been set.", main_bubble_ID, media)
        else:
            send_message(f"Warning: The admin rules are: {adminrules}", main_bubble_ID, media)
    elif msg_text.startswith("!credits"):
        send_message("This bot was created by:\nTaylan Derstadt (co29) (Lead Dev)\nVajra Vanukuri (co29) (Secondary Dev)\nJimbo Miller (co28) (Secondary Dev)\nAdditional thanks to Greyson Wyler (co29, websocket help) and Paul Estrada (co27, pronto api help)", main_bubble_ID, media)
    if msg_text.startswith("!moderationbot"):
        command = msg_text[1:].split()
        
        if user_sender_id not in bubble_owners:
            send_message("Warning: You do not have permission to use this command.", main_bubble_ID, media)
        else:
            
            if (len(command) == 2):
                global is_bot_on
                if command[1] == "start":
                    
                    is_bot_on = 1
                    send_message("Warning: The Moderation Bot is now active and watching for criminals...", main_bubble_ID, media)
                    print("Bot is now active.")
                    
                elif command[1] == "stop":
                    is_bot_on = 0
                    send_message("Warning: The Moderation Bot is now inactive and will not moderate messages.", main_bubble_ID, media)
                    print("Bot is now inactive.")
                else:
                    send_message(f"Unknown command: '{msg_text}'", main_bubble_ID, media)
            elif len(command) == 4:
                if command[1] == "settings":
                    if command[2] == "badwords":
                        settings[0] = int(command[3])
                        send_message(f"Bad words setting changed to {settings[0]}.", main_bubble_ID, media)
                    elif command[2] == "logging":
                        settings[1] = int(command[3])
                        send_message(f"Logging setting changed to {settings[1]}.", main_bubble_ID, media)
                    elif command[2] == "repeat":
                        settings[2] = int(command[3])
                        send_message(f"Repeat check setting changed to {settings[2]}.", main_bubble_ID, media)
                    elif command[2] == "length":
                        settings[3] = int(command[3])
                        send_message(f"Length check setting changed to {settings[3]}.", main_bubble_ID, media)
                    elif command[2] == "ratelimit":
                        settings[4] = int(command[3])
                        send_message(f"Rate limit setting changed to {settings[4]}.", main_bubble_ID, media)
                    elif command[2] == "flagsetting":
                        flagsetting = int(command[3])
                        send_message(f"Flag setting changed to {flagsetting}.", main_bubble_ID, media)
                    elif command[2] == "rateseconds":
                        ratelimitseconds = int(command[3])
                        send_message(f"Rate limit setting changed to {ratelimitseconds}.", main_bubble_ID, media)
                    elif command[2] == "characterlimit":
                        message_max_length = int(command[3])
                        send_message(f"Character limit setting changed to {message_max_length}.", main_bubble_ID, media)
                    elif command[2] == "warningthreshold":
                        warning_threshold = int(command[3])
                        send_message(f"Warning threshold setting changed to {warning_threshold}.", main_bubble_ID, media)
                    elif (command[2] == "logchat"):
                        log_channel_ID = command[3]
                        send_message(f"Log channel ID changed to {log_channel_ID}.", main_bubble_ID, media)
                    elif (command[2] == "rules"):
                        rules = command[3]
                        send_message(f"Rules changed to {rules}.", main_bubble_ID, media)
                    elif (command[2] == "adminrules"):
                        adminrules = command[3]
                        send_message(f"Admin rules changed to {adminrules}.", main_bubble_ID, media)
                    else:
                        send_message(f"Unknown command: '{msg_text}'", main_bubble_ID, media)
            elif len(command) == 5:
                if command[1] == "warnings":
                    targetuser = re.search(r"<@\[(\d{7})\]>", command[3])
                    targetuserint = int(targetuser.group(1))
                    warning_number = int(command[4])
                    if command[2] == "decrease":
                        decrease_warning_count(targetuserint, warning_number)
                    elif command[2] == "increase":
                        increase_warning_count(targetuserint, warning_number)
                    else:
                        send_message(f"Unknown command: '{msg_text}'", main_bubble_ID, media)
                else:
                    send_message(f"Unknown command: '{msg_text}'", main_bubble_ID, media)
            else:
                send_message(f"Unknown command: '{msg_text}'", main_bubble_ID, media)


# Main function that runs the different moderation checks on the message and increases warnings accourdingly.
def moderate_message(msg_text, sent_user_id, matches_warnings, timestamp):
    # Declare variables
    warnings_in_message = 0
    bad_section_flag = 0
    found_stored_messages = False
    index = warning_count.index(matches_warnings[0])
    previous_warnings = warning_count[index][1]
    # Log the message and it's data.
    matches_messages = list(filter(lambda row: row[0] == sent_user_id, stored_messages))
    if matches_messages.__len__() == 0:
        stored_messages.append([sent_user_id, "", 0, "", 0, msg_text, bad_section_flag, datetime.min, datetime.min , timestamp])
    else:
        index = stored_messages.index(matches_messages[0])
        stored_messages[index][1] = stored_messages[index][3]
        stored_messages[index][2] = stored_messages[index][4]
        stored_messages[index][3] = stored_messages[index][5]
        stored_messages[index][4] = stored_messages[index][6]
        stored_messages[index][7] = stored_messages[index][8]
        stored_messages[index][8] = stored_messages[index][9]
        stored_messages[index][9] = timestamp
        stored_messages[index][5] = msg_text
        stored_messages[index][6] = bad_section_flag
        found_stored_messages = True

    # Check if the message contains any flagged words.
    if (settings[0] == 1 and flagsetting == 1):
        if bool(BAD_WORDS_REGEX.search(msg_text)):
            countflags = BAD_WORDS_REGEX.findall(msg_text)
            warnings_in_message += 1
            warning_message = f"Warning: <@{sent_user_id}> sent a flagged message with {len(countflags)} flagged section(s)! This is their {previous_warnings + warnings_in_message} warning."
            print(warning_message)
            send_message(warning_message, main_bubble_ID, media)
            bad_section_flag = len(countflags)

    
    if found_stored_messages:
        # Check for repeated messages
        if settings[2] == 1:
            if stored_messages[index][1] == stored_messages[index][3] and stored_messages[index][3] == stored_messages[index][5]:
                warnings_in_message += 1
                warning_message = f"Warning: <@{sent_user_id}> sent a repeated message! This is their {previous_warnings + warnings_in_message} warning."
                print(warning_message)
                stored_messages[index][5] = " "
                stored_messages[index][3] = ""
                stored_messages[index][1] = ""
                send_message(warning_message, main_bubble_ID, media)
        
        # Check if the user has exceeded the flag limit
        if settings[0] == 1 and flagsetting > 1:
            totalcount = stored_messages[index][6] + stored_messages[index][4] + stored_messages[index][2]
            if totalcount >= flagsetting:
                warnings_in_message += 1
                warning_message = f"Warning: <@{sent_user_id}> has had {totalcount} flagged sections in the last 3 messages! This is their {previous_warnings + warnings_in_message} warning."
                send_message(warning_message, main_bubble_ID, media)
                print(warning_message)
                stored_messages[index][6] = 0
                stored_messages[index][4] = 0
                stored_messages[index][2] = 0
        
        # Check if the user has exceeded the rate limit
        if settings[4] == 1:
            if (stored_messages[index][9] - stored_messages[index][7]).total_seconds() < ratelimitseconds:
                stored_messages[index][7] = datetime.min 
                stored_messages[index][8] = datetime.min 
                stored_messages[index][9] = datetime.min 
                warnings_in_message += 1
                warning_message = f"Warning: <@{sent_user_id}> has exceded the rate limits! This is their {previous_warnings + warnings_in_message} warning."
                send_message(warning_message, main_bubble_ID, media)
                print(warning_message)

    # Check if the message exceeds a set length
    if settings[3] == 1:
        if len(msg_text) > message_max_length:
            warnings_in_message += 1
            warning_message = f"Warning: <@{sent_user_id}> sent a message that is {len(msg_text)} characters long! This is their {previous_warnings + warnings_in_message} warning."
            send_message(warning_message, main_bubble_ID, media)
            print(warning_message)

    # Increase the warning count if there are any warnings
    if (warnings_in_message > 0):
        increase_warning_count(sent_user_id, warnings_in_message)
    

# Log message details to another channel
def log(msg_text, sent_user_id, msg_media):
    log_message = f"Message sent by <@{sent_user_id}>: {msg_text}"
    send_message(log_message, log_channel_ID, msg_media)
    print(log_message)


# Increase the warning count for a user
def increase_warning_count(sent_user_id, number):
    matches = list(filter(lambda row: row[0] == sent_user_id, warning_count))
    index = warning_count.index(matches[0])
    warning_count[index][1] += number
    if (warning_count[index][1] >= warning_threshold):
        warning_message = f"Warning: <@{sent_user_id}> has reached the warning threshold of {warning_threshold} and has been removed!"
        send_message(warning_message, main_bubble_ID, media)
        kickUserFromBubble(accesstoken, main_bubble_ID, [sent_user_id])
        print(warning_message)
    return warning_count[index][1]


# Decrease the warning count for a user
def decrease_warning_count(sent_user_id, number):
    matches = list(filter(lambda row: row[0] == sent_user_id, warning_count))
    index = warning_count.index(matches[0])
    if (warning_count[index][1] == 0):
        send_message(f"Warning: <@{sent_user_id}> has no warnings to decrease.", main_bubble_ID, media)
        return
    if (warning_count[index][1] < number):
        send_message(f"Warning: <@{sent_user_id}> has only {warning_count[index][1]} warnings to decrease, unable to remove.", main_bubble_ID, media)
        return
    warning_count[index][1] -= 1
    send_message(f"Warning: <@{sent_user_id}>'s warning count has been decreased to {warning_count[index][1]}.", main_bubble_ID, media)


# Send a message to the API
def send_message(message, bubble, send_media):
    unique_uuid = str(uuid.uuid4())
    messageCreatedat = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    data = {
        "id": "Null",
        "uuid": unique_uuid,
        "bubble_id": bubble,
        "message": message,
        "created_at": messageCreatedat,
        "user_id": user_id,
        "messagemedia": send_media
    }
    url = f"{api_base_url}api/v1/message.create"
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()


#startup stuff
main_bubble_ID = input("Ender bubble id: ")
log_channel_ID = input("Enter log channel id: ")
bubble_id = main_bubble_ID
bubble_info = get_bubble_info(accesstoken, bubble_id)
bubble_owners = [row["user_id"] for row in bubble_info["bubble"]["memberships"] if row["role"] == "owner"]
bubbles = getUsersBubbles(accesstoken)
dms = get_dms(bubbleOverviewJSONPath)
bubble_sid = bubble_info["bubble"]["channelcode"]
print(bubble_sid)
asyncio.run(main(bubble_id, bubble_sid))

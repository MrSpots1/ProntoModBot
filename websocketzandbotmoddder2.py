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
#Function to create DM
def createDM(access_token, id, orgID):
    url = f"{API_BASE_URL}api/v1/dm.create"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
    }
    request_payload = {
        "organization_id": orgID,
        "user_id": id,
    }
    try:
        response = requests.post(url, headers=headers, json=request_payload)
        response.raise_for_status()
        response_json = response.json()
        return response_json
    except requests.exceptions.HTTPError as http_err:
        logger.error(f"HTTP error occurred: {http_err} - Response: {response.text}")
        if response.status_code == 401:
            raise BackendError(f"HTTP error occurred: {http_err}")
        else:
            raise BackendError(f"HTTP error occurred: {http_err}")
    except requests.exceptions.RequestException as req_err:
        logger.error(f"Request exception occurred: {req_err}")
        raise BackendError(f"Request exception occurred: {req_err}")
    except Exception as err:
        logger.error(f"An unexpected error occurred: {err}")
        raise BackendError(f"An unexpected error occurred: {err}")
def getUsersBubbles(access_token):
    url = f"{api_base_url}api/v3/bubble.list"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",  # Ensure 'Bearer' is included
    }

    try:
        response = requests.post(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as http_err:
        logger.error(f"HTTP error occurred: {http_err} - Response: {response.text}")
        if response.status_code == 401:
            raise BackendError(f"HTTP error occurred: {http_err}")
        else:
            raise BackendError(f"HTTP error occurred: {http_err}")
    except requests.exceptions.RequestException as req_err:
        logger.error(f"Request exception occurred: {req_err}")
        raise BackendError(f"Request exception occurred: {req_err}")
    except Exception as err:
        logger.error(f"An unexpected error occurred: {err}")
        raise BackendError(f"An unexpected error occurred: {err}")
def get_bubble_info(access_token, bubbleID):
    url = f"{api_base_url}api/v2/bubble.info"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
    }
    request_payload = {
        "bubble_id": bubbleID,
    }
    try:
        response = requests.post(url, headers=headers, json=request_payload)
        response.raise_for_status()
        response_json = response.json()
        return response_json
    except requests.exceptions.HTTPError as http_err:
        logger.error(f"HTTP error occurred: {http_err} - Response: {response.text}")
        if response.status_code == 401:
            raise BackendError(f"HTTP error occurred: {http_err}")
        else:
            raise BackendError(f"HTTP error occurred: {http_err}")
    except requests.exceptions.RequestException as req_err:
        logger.error(f"Request exception occurred: {req_err}")
        raise BackendError(f"Request exception occurred: {req_err}")
    except Exception as err:
        logger.error(f"An unexpected error occurred: {err}")
        raise BackendError(f"An unexpected error occurred: {err}")
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
#Function to add a member to a bubble
#invitations is a list of user IDs, in the form of [{user_id: 5302519}, {user_id: 5302367}]
def addMemberToBubble(access_token, bubbleID, invitations, sendemails, sendsms):
    url = f"{api_base_url}api/v1/bubble.invite"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
    }
    request_payload = {
        "bubbleID": bubbleID,
        "invitations": invitations,
        "sendemails": sendemails,
        "sendsms": sendsms,
    }
    try:
        response = requests.post(url, headers=headers, json=request_payload)
        response.raise_for_status()
        response_json = response.json()
        return response_json
    except requests.exceptions.HTTPError as http_err:
        logger.error(f"HTTP error occurred: {http_err} - Response: {response.text}")
        if response.status_code == 401:
            raise BackendError(f"HTTP error occurred: {http_err}")
        else:
            raise BackendError(f"HTTP error occurred: {http_err}")
    except requests.exceptions.RequestException as req_err:
        logger.error(f"Request exception occurred: {req_err}")
        raise BackendError(f"Request exception occurred: {req_err}")
    except Exception as err:
        logger.error(f"An unexpected error occurred: {err}")
        raise BackendError(f"An unexpected error occurred: {err}")

#Function to kick user from a bubble
#users is a list of user IDs, in the form of [5302519]
def kickUserFromBubble(access_token, bubbleID, users):
    url = f"{api_base_url}api/v1/bubble.kick"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
    }
    request_payload = {
        "bubble_id": bubbleID,
        users: users,
    }
    try:
        response = requests.post(url, headers=headers, json=request_payload)
        response.raise_for_status()
        response_json = response.json()
        return response_json
    except requests.exceptions.HTTPError as http_err:
        logger.error(f"HTTP error occurred: {http_err} - Response: {response.text}")
        if response.status_code == 401:
            raise BackendError(f"HTTP error occurred: {http_err}")
        else:
            raise BackendError(f"HTTP error occurred: {http_err}")
    except requests.exceptions.RequestException as req_err:
        logger.error(f"Request exception occurred: {req_err}")
        raise BackendError(f"Request exception occurred: {req_err}")
    except Exception as err:
        logger.error(f"An unexpected error occurred: {err}")
        raise BackendError(f"An unexpected error occurred: {err}")
async def main(bubble_id, bubble_sid):
    '"send_message("Warning: The Moderation Bot is now active and watching for criminals...", main_bubble_ID, media)"'
    await connect_and_listen(bubble_id, bubble_sid)

# Mod Bot Logic for Processing Messages
def process_message(msg_text, user_firstname, user_lastname, timestamp, msg_media, user_id_websocket):
    msg_text_lower = msg_text.lower()
    msg_id = str(uuid.uuid4())  # Simulate unique message ID
    sent_user_id = user_id_websocket  # This would be the actual user ID for the message sender
    check_for_commands(msg_text_lower, sent_user_id)
    if (is_bot_on == 1):
        
        
        count = 0
        if settings[1] == 1:
            log(msg_text, sent_user_id, msg_media)
        
        if (sent_user_id != int_user_id) or ((sent_user_id == int_user_id) and (msg_text[:8] != "Warning:")):
            # Bad Word Check
            if settings[0] == 1:
                count = check_bad_words(msg_text_lower, sent_user_id)
            
            # Logging
            

            
            repeat_check(msg_text_lower, sent_user_id, count, timestamp)
            
            # Message Length Check
            if settings[3] == 1:
                check_length(msg_text_lower, sent_user_id)
def check_for_commands(msg_text, user_sender_id):
    """Check for any commands in the message."""
    if msg_text.startswith("!moderationbot"):
        
        
        if user_sender_id not in bubble_owners:
            send_message("Warning: You do not have permission to use this command.", main_bubble_ID, media)
        else:
            command = msg_text[1:].split()
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
                    else:
                        send_message(f"Unknown command: '{msg_text}'", main_bubble_ID, media)
                elif command[1] == "warnings":
                    usernumber = re.search(r"<@\[(\d{7})\]>", msg_text)
                    number = int(usernumber.group(1))
                    if command[2] == "decrease":
                        decrease_warning_count(number)
                    elif command[2] == "increase":
                        increase_warning_count(number)
                    else:
                        send_message(f"Unknown command: '{msg_text}'", main_bubble_ID, media)
                else:
                    send_message(f"Unknown command: '{msg_text}'", main_bubble_ID, media)
            else:
                send_message(f"Unknown command: '{msg_text}'", main_bubble_ID, media)
def check_bad_words(msg_text, sent_user_id):
    """Check if the message contains any flagged words."""
    if bool(BAD_WORDS_REGEX.search(msg_text)):
        countflags = BAD_WORDS_REGEX.findall(msg_text)
        warning_message = f"Warning: <@{sent_user_id}> sent a flagged message with {len(countflags)} flagged section(s)!"
        print(warning_message)
        send_message(warning_message, main_bubble_ID, media)
        increase_warning_count(sent_user_id)
        return len(countflags)
        
    return 0

def log(msg_text, sent_user_id, msg_media):
    """Log message details to another channel."""
    log_message = f"Message sent by <@{sent_user_id}>: {msg_text}"
    send_message(log_message, log_channel_ID, msg_media)
    print(log_message)

def check_length(msg_text, sent_user_id):
    """Check if the message exceeds a set length."""
    if len(msg_text) > message_max_length:
        warning_message = f"Warning: <@{sent_user_id}> sent a message that is {len(msg_text)} characters long!"
        increase_warning_count(sent_user_id)
        send_message(warning_message, main_bubble_ID, media)
        print(warning_message)

def repeat_check(msg_text, sent_user_id, flagcount, timestamp):
    matches = list(filter(lambda row: row[0] == sent_user_id, stored_messages))
    if matches.__len__() == 0:
        stored_messages.append([sent_user_id, "", 0, "", 0, msg_text, flagcount, datetime.min, datetime.min , timestamp])
    else:
        index = stored_messages.index(matches[0])
        
        
        stored_messages[index][1] = stored_messages[index][3]
        stored_messages[index][2] = stored_messages[index][4]
        stored_messages[index][3] = stored_messages[index][5]
        stored_messages[index][4] = stored_messages[index][6]
        stored_messages[index][7] = stored_messages[index][8]
        stored_messages[index][8] = stored_messages[index][9]
        stored_messages[index][9] = timestamp
        stored_messages[index][5] = msg_text
        stored_messages[index][6] = flagcount
        if settings[2] == 1:
            if stored_messages[index][1] == stored_messages[index][3] and stored_messages[index][3] == stored_messages[index][5]:
                warning_message = f"Warning: <@{sent_user_id}> sent a repeated message!"
                increase_warning_count(sent_user_id)
                print(warning_message)
                stored_messages[index][5] = " "
                stored_messages[index][3] = ""
                stored_messages[index][1] = ""
                send_message(warning_message, main_bubble_ID, media)
        if settings[0] == 1 and flagsetting > 1:
            totalcount = stored_messages[index][6] + stored_messages[index][4] + stored_messages[index][2]
            if totalcount >= flagsetting:
                warning_message = f"Warning: <@{sent_user_id}> has had {totalcount} flagged sections in the last 3 messages!"
                send_message(warning_message, main_bubble_ID, media)
                print(warning_message)
                increase_warning_count(sent_user_id)
                stored_messages[index][6] = 0
                stored_messages[index][4] = 0
                stored_messages[index][2] = 0
        if settings[4] == 1:
            
            if (stored_messages[index][9] - stored_messages[index][7]).total_seconds() < ratelimitseconds:
                stored_messages[index][7] = datetime.min 
                stored_messages[index][8] = datetime.min 
                stored_messages[index][9] = datetime.min 
                warning_message = f"Warning: <@{sent_user_id}> has exceded the rate limits!"
                increase_warning_count(sent_user_id)
                send_message(warning_message, main_bubble_ID, media)
                print(warning_message)
                
def increase_warning_count(sent_user_id):
    """Increase the warning count for the bot."""
    matches = list(filter(lambda row: row[0] == sent_user_id, warning_count))
    if matches.__len__() == 0:
        warning_count.append([sent_user_id, 1])
    else:
        index = warning_count.index(matches[0])
        warning_count[index][1] += 1
    if (warning_count[index][1] == warning_threshold):
        warning_message = f"Warning: <@{sent_user_id}> has reached the warning threshold of {warning_threshold} and has been removed!"
        send_message(warning_message, main_bubble_ID, media)
        kickUserFromBubble(accesstoken, main_bubble_ID, [sent_user_id])
        print(warning_message)
def decrease_warning_count(sent_user_id):
    """Increase the warning count for the bot."""
    matches = list(filter(lambda row: row[0] == sent_user_id, warning_count))
    if matches.__len__() == 0:
        send_message(f"Warning: <@{sent_user_id}> has no warnings to decrease.", main_bubble_ID, media)
    else:
        index = warning_count.index(matches[0])
        if (warning_count[index][1] == 0):
            send_message(f"Warning: <@{sent_user_id}> has no warnings to decrease.", main_bubble_ID, media)
            return
        warning_count[index][1] -= 1
    send_message(f"Warning: <@{sent_user_id}> has decreased their warning count to {warning_count[index][1]}.", main_bubble_ID, media)
def send_message(message, bubble, send_media):
    """Send a message to the API."""
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
main_bubble_ID = input("Ender bubble id: ")
log_channel_ID = input("Enter log channel id: ")
# Start WebSocket Listening

bubble_id = main_bubble_ID
bubble_info = get_bubble_info(accesstoken, bubble_id)
bubble_owners = [row["user_id"] for row in bubble_info["bubble"]["memberships"] if row["role"] == "owner"]
bubbles = getUsersBubbles(accesstoken)

bubble_sid = bubble_info["bubble"]["channelcode"]
print(bubble_sid)
asyncio.run(main(bubble_id, bubble_sid))

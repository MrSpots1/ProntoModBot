import requests
import uuid
from datetime import datetime, timezone
import time
import json
import re

accesstoken = ""
api_base_url = "https://stanfordohs.pronto.io/"
user_id = "5301889"
int_user_id = 5301889
main_bubble_ID = "4066670"
log_channel_ID = "4249501"
global media 
media = []
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {accesstoken}",
}
settings = [1, 1, 1, 1]
flagsetting = 3
stored_messages = []
warning_message = ""
log_message = ""
last_message_id = ""

URL = "https://raw.githubusercontent.com/MrSpots1/MrSpots1.github.io/main/words%20%5BMConverter.eu%5D.txt"

def download_wordlist(url):
    """
    Downloads the bad words list from the given URL.
    
    Args:
    - url (str): The URL of the text file.

    Returns:
    - set: A set of bad words in lowercase.
    """
    response = requests.get(url)
    
    if response.status_code == 200:
        words = response.text.split("\n")  # Split by lines
        # Ensure all words are in lowercase and remove empty lines
        return set(word.strip().lower() for word in words if word.strip())
    else:
        print("Failed to download word list.")
        return set()

def fetch_latest_message():
    """Fetch only the most recent message."""
    url = f"{api_base_url}api/v1/bubble.history"
    data = {"bubble_id": main_bubble_ID}
    response = requests.post(url, headers=headers, json=data)
    
    if response.status_code == 200:
        messages = response.json().get("messages", [])
        return messages[0]  # Return the most recent message
    else:
        print(f"HTTP error occurred: {response.status_code} - {response.text}")
    return None

def monitor_messages():
    
    """Continuously fetch the latest message and check for flagged words."""
    global warning_message  
    global last_message_id
    
    while True:
        msg = fetch_latest_message()
        
        if msg and isinstance(msg, dict) and "message" in msg and "user_id" in msg and "id" in msg and "messagemedia" in msg:
            
            msg_id = msg["id"]
            msg_text = msg["message"].lower()
            msg_text_origional = msg["message"]
            msg_media = msg["messagemedia"]

            if msg_id != last_message_id:  # Only process if it's a new message
                
                last_message_id = msg_id  # Update last seen message

                # Check the message for flagged words using regex
                if settings[0] == 1:
                    count = check_bad_words(msg_text, msg['user_id'])
                if settings[1] == 1:
                    log(msg_text_origional, msg['user_id'], msg_media)
                if settings[2] == 1:
                    repeat_check(msg_text, msg['user_id'], count)
                if settings[3] == 1:
                    check_length(msg_text, msg['user_id'])
        time.sleep(1)  # Poll every 1 second
def check_bad_words(msg_text, sent_user_id):
    """Check if the message contains any flagged words."""
    if bool(BAD_WORDS_REGEX.search(msg_text)):
                    countflags = BAD_WORDS_REGEX.findall(msg_text)
                    
                    warning_message = f"Warning: <@{sent_user_id}> sent a flagged message with {countflags.__len__()} flagged section(s)!"
                    if flagsetting == 1:
                        send_message(warning_message, main_bubble_ID, media)  # Send alert
                    print(warning_message)
                    
                    
                    if (countflags != None):
                        return countflags.__len__()
    else:
        return 0
def log(msg_text_origional, sent_user_id, msg_media):
    if sent_user_id != int_user_id or (sent_user_id == int_user_id and msg_text_origional[:9] != "Warning: "):
                    log_message = f"Message sent by <@{sent_user_id}>: {msg_text_origional} "
                    send_message(log_message, log_channel_ID, msg_media)
                    print(log_message)
def check_length(msg_text, sent_user_id):
    if len(msg_text) > 750:
        warning_message = f"Warning: <@{sent_user_id}> sent a message that is {len(msg_text)} characters long, which is clasified as a text wall!"
        send_message(warning_message, main_bubble_ID, media)
        print(warning_message)
def repeat_check(msg_text, sent_user_id, flagcount):
    matches = list(filter(lambda row: row[0] == sent_user_id, stored_messages))
    if matches.__len__() == 0:
        stored_messages.append([sent_user_id, "", 0, "", 0, msg_text, flagcount])
    else:
        index = stored_messages.index(matches[0])
        
        
        stored_messages[index][1] = stored_messages[index][3]
        stored_messages[index][2] = stored_messages[index][4]
        stored_messages[index][3] = stored_messages[index][5]
        stored_messages[index][4] = stored_messages[index][6]
        stored_messages[index][5] = msg_text
        stored_messages[index][6] = flagcount
        print(stored_messages)
        if stored_messages[index][1] == stored_messages[index][3] and stored_messages[index][3] == stored_messages[index][5]:
            warning_message = f"Warning: <@{sent_user_id}> sent a repeated message!"
            send_message(warning_message, main_bubble_ID, media)
        if settings[0] == 1 and flagsetting > 1:
            totalcount = stored_messages[index][6] + stored_messages[index][4] + stored_messages[index][2]
            if totalcount >= flagsetting:
                warning_message = f"Warning: <@{sent_user_id}> has had {totalcount} flagged sections in the last 3 messages!"
                send_message(warning_message, main_bubble_ID, media)
                stored_messages[index][6] = 0
                stored_messages[index][4] = 0
                stored_messages[index][2] = 0
             
    
            
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
        "messagemedia": []
    }
    url = f"{api_base_url}api/v1/message.create"
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()

BAD_WORDS = download_wordlist(URL)

BAD_WORDS_REGEX = re.compile(r"\b(" + "|".join(re.escape(word) for word in BAD_WORDS) + r")\b", re.IGNORECASE)

# Start monitoring messages
monitor_messages()

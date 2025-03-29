import websockets
import asyncio
import json
import requests
import sys


api_base_url = "https://stanfordohs.pronto.io/"



accesstoken = "Bc7ohwbpkMcDqE90oCQG5wcdr2JzzuIXInOHsFz8.1354676856"
user_id = "5301889"
chat_link = "4066670"
bubble_id = chat_link[-7:]


if bubble_id.isdigit():
   print("Chat Registered")


else:
   print("Error: Not a valid link.")
   sys.exit()


headers = {
 "Content-Type": "application/json",
 "Authorization": f"Bearer {accesstoken}",
}


bubble_sid = "dRRIOchii2zlTboeIW12ARtDz6eANFO9Pux16dmX"




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
   print(f"Bubble Auth: {bubble_auth}")
   return bubble_auth


def start_push(bubble_id, bubble_sid):
   async def connect_and_listen():
       uri = "wss://ws-mt1.pusher.com/app/f44139496d9b75f37d27?protocol=7&client=js&version=8.3.0&flash=false"


       async with websockets.connect(uri) as websocket:
           # wait for the connection established message, which should *theoretically* contain the socket_id
           response = await websocket.recv()
           print(f"Received: {response}")


           # nevermind it always contains the socket_id we good to go
           data = json.loads(response)
           if "data" in data:
               inner_data = json.loads(data["data"])
               socket_id = inner_data.get("socket_id", None)


               data = {
                   "event": "pusher:subscribe",
                   "data": {
                       "channel": f"private-bubble.{bubble_id}.{bubble_sid}",
                       "auth": str(chat_auth(bubble_id, bubble_sid, socket_id))
                   }
               }


               await websocket.send(json.dumps(data))




               if socket_id:
                   print(f"Socket ID: {socket_id}")
               else:
                   print("Socket ID not found in response")


           # keep listening for the stuffies
           async for message in websocket:
               if message == "ping":
                   await websocket.send("pong") # saw this on urs so we keep it but i dont think nec




               else:
                   print(f"Received: {message}")


   async def main():
       await connect_and_listen()


   asyncio.run(main())



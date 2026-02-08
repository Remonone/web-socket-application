import time
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketState
from constants import LOBBY_ID_LENGTH
from data.lobby import Lobby
from typing import Dict
from components.challenge import *
from utils.util import *
from logging import *

import traceback

type Connection = tuple[WebSocket, str]

class ServerWrapper:
    app: FastAPI
    lobbies: Dict[str, Lobby[WebSocket]]
    connections: Dict[WebSocket, str]
    configs: Dict
    log: Logger
    def __init__(self, cfg):
        self.app = FastAPI()

        self.app.add_api_websocket_route("/ws", endpoint=self.connectToLobby)
        self.lobbies = set()
        self.configs = cfg
        self.log = getLogger("APP")

    def createLobby(self):
        lobbyId = generate_str(LOBBY_ID_LENGTH)
        lobby = Lobby(lobbyId)
        self.lobbies[lobbyId] = lobby
        return { lobbyId, lobby }

    async def connectToLobby(self, webSocket: WebSocket):
        await webSocket.accept()

        nonce = make_nonce()
        ts = int(time.time())
        
        challenge = {
            "type": "challenge",
            "nonce": nonce,
            "timestamp": ts
        }
        
        await webSocket.send_json(challenge)

        try:
            data = await webSocket.receive_json()

            if data.get("type") != "auth":
                await webSocket.close(code=1008)
                return

            device_id = data.get("device_id")
            signature = data.get("signature")
            if not device_id or signature:
                await webSocket.close(code=1008)
                return
            
            secret = self.configs["data"].get(device_id)
            if not secret:
                await webSocket.close(code=1008)
                return
            now = int(time.time())
            if abs(now - ts) > self.configs["maxConnectionDifference"]:
                await webSocket.close(code=1008)
                return
            msg=f"{device_id}|{nonce}|{ts}"
            auth = sign(secret, msg)
            if not compare_entries(auth, signature):
                await webSocket.close(code=1008)
                return
            while webSocket.client_state == WebSocketState.CONNECTED:
                request = await webSocket.receive_json()
                self.handle_request(webSocket, request)
        except WebSocketDisconnect:
            self.clear_user(webSocket)
            self.log.info(f"Client: {webSocket.client.host} have been disconnected")
            return
        except Exception:
            self.clear_user(webSocket)
            self.log.error(traceback.format_exc())
            await webSocket.close(code=1011)
            return
        
    def handle_request(self, user: WebSocket, request: Dict):
        type = request["type"]
        if type == "create_lobby":
            lobbyResponse = self.createLobby()
            lobby = lobbyResponse.lobby
            lobby_id = lobbyResponse.lobbyId
            user.send_json(convert_message("lobby", lobby_id))
            lobby.add_client(user)
            self.connections.add(tuple(user, lobby_id))
            return
        if type == "connect_lobby":
            id = request["id"]
            lobby = self.lobbies[id]
            if not lobby:
                user.send(convert_message("err", f"Lobby with id {id} not found!"))
                return
            lobby.add_client(user)
            self.connections.add(tuple(user, id))
            for lobbyUser in lobby.iterator():
                lobbyUser.send_json(convert_message("connection", user.client.host))
            return
        lobby_id = self.connections[user]
        if not lobby_id:
            user.send(convert_message("err", f"You are not connected to lobby!"))
            return
        lobby = self.lobbies[lobby_id]
        for mate in lobby.iterator():
            mate.send_json(request)
        return
            

    def clear_user(self, user: WebSocket):
        id = self.connections[user]
        lobby = self.lobbies[id]
        lobby.remove_client(user)
        for connection in lobby.iterator():
            connection.send_json("disconnect", user.client.host)
        self.connections.pop(user)
        return
            

            


        
        


        


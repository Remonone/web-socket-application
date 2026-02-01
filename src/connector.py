from fastapi import FastAPI, WebSocket, Query
from fastapi.websockets import WebSocketState
from constants import LOBBY_ID_LENGTH
from data.lobby import Lobby
from typing import Set
from utils.util import *

    


class ServerWrapper:
    app: FastAPI
    lobbies: Set[Lobby[WebSocket]]
    def __init__(self):
        self.app = FastAPI()
        self.app.add_api_route("/createLobby", endpoint=self.createLobby, methods=["GET"])
        self.app.add_api_websocket_route("/ws", endpoint=self.connectToLobby)
        self.lobbies = set()


    def createLobby(self):
        lobbyId = generate_str(LOBBY_ID_LENGTH)
        lobby = Lobby(lobbyId)
        self.lobbies.add(lobby)
        return { lobbyId }
    
    async def connectToLobby(self, webSocket: WebSocket, lobbyId: str = Query(...)):
        await webSocket.accept()
        filtered = [lobby for lobby in self.lobbies if lobby.get_lobby_id() == lobbyId]
        if len(filtered) != 1:
            webSocket.send(convert_message("err", f"Lobby with id {lobbyId} not found!"))
            webSocket.close()
            return
        lobby = filtered[0]
        lobby.add_client(webSocket)
        try:
            while webSocket.client_state == WebSocketState.CONNECTED:
                data = await webSocket.receive_text()
                for client in lobby.iterator():
                    await client.send(data)
        finally:
            lobby.remove_client(webSocket)
        


        


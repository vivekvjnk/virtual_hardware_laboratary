import asyncio
import os
import sys
import logging
from typing import Optional, Set, Tuple
from vhl_common.urp.data_types import MessageEnvelope
from .gate import Gate

logger = logging.getLogger(__name__)

class HILTerminal:
    """
    Human-in-the-Loop (HIL) TCP Socket Terminal Module.
    Connects to the GATE as "HIL".
    
    Listens on a TCP socket (configurable via VHL_HIL_HOST and VHL_HIL_PORT)
    and allows external connections (using tools like `nc` or `telnet`) to interact
    with the HIL module.
    """
    def __init__(self, gate: Gate, name: str = "HIL"):
        self.gate = gate
        self.name = name
        self.prompt = "HIL> "
        self.host = os.environ.get("VHL_HIL_HOST", "127.0.0.1")
        self.port = int(os.environ.get("VHL_HIL_PORT", "1085"))
        self._running = False
        self._server: Optional[asyncio.AbstractServer] = None
        self._server_task: Optional[asyncio.Task] = None
        self._clients: Set[Tuple[asyncio.StreamReader, asyncio.StreamWriter]] = set()
        
        # Register the HIL receiver function during initialization
        self.gate.register(self.name, self.send)

    def start(self) -> None:
        """Starts the TCP socket server in a background task."""
        if self._running:
            return
        
        self._running = True
        self._server_task = asyncio.create_task(self._run_server())
        logger.info(f"HIL Terminal starting TCP server on {self.host}:{self.port}...")

    async def _run_server(self) -> None:
        """Runs the asyncio TCP socket server loop."""
        try:
            self._server = await asyncio.start_server(
                self._handle_client, self.host, self.port
            )
            addr = self._server.sockets[0].getsockname()
            logger.info(f"HIL Terminal TCP server listening on {addr}")
            async with self._server:
                await self._server.serve_forever()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"HIL Terminal TCP server error: {e}", exc_info=True)

    async def stop(self) -> None:
        """Stops the TCP server and disconnects all clients."""
        if not self._running:
            return
        
        self._running = False
        
        # Disconnect all active clients
        for reader, writer in list(self._clients):
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass
        self._clients.clear()
        
        # Close server
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None
            
        if self._server_task:
            self._server_task.cancel()
            try:
                await self._server_task
            except asyncio.CancelledError:
                pass
            self._server_task = None
            
        self.gate.unregister(self.name)
        logger.info("HIL Terminal TCP server stopped and unregistered.")

    def _format_message(self, message: MessageEnvelope) -> str:
        """Formats a MessageEnvelope for terminal display."""
        sender = message.sender
        msg_type = message.type
        payload = message.payload
        correlation_id = message.correlation_id or "N/A"
        
        return (
            f"\n📥 [GATE -> HIL]\n"
            f"   Sender: {sender}\n"
            f"   Type:   {msg_type}\n"
            f"   CorrID: {correlation_id}\n"
            f"   Payload:\n{payload}\n"
            # f"   Message: \n{payload["result"]["content"][0].text}"
            f"──────────────────────────────────────────────────\n"
        )

    async def send(self, message: MessageEnvelope) -> None:
        """
        Ingress function called by the GATE to deliver messages to the HIL terminal.
        Sends the formatted message to all currently connected TCP clients.
        """
        formatted = self._format_message(message)
        
        if self._clients:
            for reader, writer in list(self._clients):
                try:
                    # Clear the prompt line, write the message, then restore the prompt
                    writer.write(f"\r\033[K{formatted}{self.prompt}".encode())
                    await writer.drain()
                except Exception as e:
                    logger.warning(f"Error sending message to HIL client: {e}")
                    self._clients.discard((reader, writer))
        else:
            # Fallback to local stdout logging if no external client is attached
            sys.stdout.write(formatted)
            sys.stdout.flush()

    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        """Handles communication with a single connected client."""
        addr = writer.get_extra_info('peername')
        logger.info(f"HIL Terminal: client connected from {addr}")
        client_key = (reader, writer)
        self._clients.add(client_key)
        
        try:
            # Welcome banner
            greeting = (
                f"\n=== Welcome to HIL Terminal ===\n"
                f"Connected to GATE as '{self.name}'\n"
                f"Use format '<receiver>: <message>' to route messages.\n"
                f"Type '/help' for options, '/exit' or '/quit' to disconnect.\n"
                f"================================\n"
                f"{self.prompt}"
            )
            writer.write(greeting.encode())
            await writer.drain()
            
            while self._running:
                line_bytes = await reader.readline()
                if not line_bytes:
                    # Connection closed by client
                    break
                
                user_input = line_bytes.decode().strip()
                if not user_input:
                    writer.write(self.prompt.encode())
                    await writer.drain()
                    continue
                
                if user_input.lower() == "/help":
                    help_text = (
                        "\n--- HIL Terminal Help ---\n"
                        "Supported formats:\n"
                        "  <receiver>: <message>\n"
                        "  Example: microcontroller-module.archy: Start synthesis\n"
                        "Other commands:\n"
                        "  /help - Show this help menu\n"
                        "  /exit, /quit - Disconnect\n"
                        "-------------------------\n"
                        f"{self.prompt}"
                    )
                    writer.write(help_text.encode())
                    await writer.drain()
                    continue
                
                if user_input.lower() in ("/exit", "/quit"):
                    break
                
                if ":" not in user_input:
                    writer.write(f"[!] Invalid format. Use '<receiver>: <message>'\n{self.prompt}".encode())
                    await writer.drain()
                    continue
                
                receiver, message_content = user_input.split(":", 1)
                receiver = receiver.strip()
                message_content = message_content.strip()
                
                if not receiver or not message_content:
                    writer.write(f"[!] Receiver and message content cannot be empty.\n{self.prompt}".encode())
                    await writer.drain()
                    continue
                
                # Wrap the message in MessageEnvelope and send via GATE
                message = MessageEnvelope(
                    type="HUMAN_RESPONSE",
                    payload=message_content,
                    sender=self.name,
                    receiver=receiver
                )
                
                try:
                    await self.gate.send(message)
                    writer.write(f"[+] Sent message to {receiver} via GATE.\n{self.prompt}".encode())
                except Exception as e:
                    writer.write(f"[-] Failed to send message via GATE: {e}\n{self.prompt}".encode())
                await writer.drain()
                
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error handling HIL client {addr}: {e}", exc_info=True)
        finally:
            self._clients.discard(client_key)
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass
            logger.info(f"HIL Terminal: client {addr} disconnected.")

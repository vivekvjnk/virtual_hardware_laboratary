import os

from pydantic import SecretStr

from openhands.sdk import (
    LLM,
    Agent,
    LLMSummarizingCondenser,
    Conversation,
    Event,
    LLMConvertibleEvent,
    get_logger,
)
from openhands.sdk.tool import Tool
from openhands.tools.gemini import GEMINI_FILE_TOOLS
from openhands.tools.terminal import TerminalTool

from .prompts import SYSTEM_PROMPT
from .object_store import MinioObjectStore

logger = get_logger(__name__)

class ANA_validation_agent:
    def __init__(self, mcp_url: str = "http://localhost:8081/vap", minio_url: str = "http://127.0.0.1:9000"):
        self.mcp_url = mcp_url
        self.minio_url = minio_url
        self.object_store = MinioObjectStore(endpoint_url=minio_url)
        self.tsx_mapping = {}
        self.llm = self._setup_llm()
        self.agent = self._setup_agent()
        self.llm_messages = []

    def _setup_llm(self,usage_id="ana_validation_agent") -> LLM:
        api_key = os.getenv("LLM_API_KEY")
        if not api_key:
            raise ValueError("LLM_API_KEY environment variable is not set.")
        
        model = os.getenv("LLM_MODEL", "anthropic/claude-3-5-sonnet-20241022")
        base_url = os.getenv("LLM_BASE_URL")
        
        return LLM(
            usage_id=usage_id,
            model=model,
            base_url=base_url,
            api_key=SecretStr(api_key),
        )

    def _setup_agent(self) -> Agent:
        tools = [
            Tool(name=TerminalTool.name), 
            # Terminal tool might be useful for debugging or file ops, but FileEditor is primary
            *GEMINI_FILE_TOOLS,
        ]

        mcp_config = {
            "mcpServers": {
                "vhl-library": {
                    "url": self.mcp_url,
                    # Assuming the SDK handles the transport details based on URL
                }
            }
        }
        
        llm_condenser = self._setup_llm(usage_id="librarian_condenser")
        condenser = LLMSummarizingCondenser(llm=llm_condenser, max_size=80, keep_first=8)

        return Agent(
            llm=self.llm,
            tools=tools,
            mcp_config=mcp_config,
            system_prompt=SYSTEM_PROMPT,
            condenser=condenser,
        )

    def _conversation_callback(self, event: Event):
        if isinstance(event, LLMConvertibleEvent):
            self.llm_messages.append(event.to_llm_message())

    def sync_workspace_to_minio(self, workspace_path: str):
        """
        Uploads all .tsx files from workspace to Minio and updates the mapping.
        """
        logger.info(f"Syncing .tsx files from {workspace_path} to Minio.")
        self.tsx_mapping = self.object_store.upload_tsx_files(workspace_path)
        logger.info(f"Sync complete. Mapping: {self.tsx_mapping}")

    def validate_circuit(self, circuit_path: str) -> None:
        """
        Process the SCUD file: read it, check components, and update it.
        """
        if not os.path.exists(circuit_path):
            raise FileNotFoundError(f"SCUD file not found at: {circuit_path}")

        # Sync workspace to Minio before starting
        # Assuming the workspace is the directory containing the circuit file or a specific path
        workspace_dir = os.path.dirname(os.path.abspath(circuit_path))
        self.sync_workspace_to_minio(workspace_dir)

        cwd = os.getcwd()
        
        conversation = Conversation(
            agent=self.agent,
            callbacks=[self._conversation_callback],
            workspace=cwd,
        )

        logger.info(f"Starting Librarian Agent for SCUD: {circuit_path}")
        
        # We send a message to kick off the process
        # The system prompt already tells the agent what to do, but we need to point it to the file.
        user_message = (
            f"Please validate the circuit file located at '{circuit_path}' using VHL-VAP process. "
        )
        
        conversation.send_message(user_message)
        conversation.run()
        
        logger.info("Librarian Agent finished processing.")

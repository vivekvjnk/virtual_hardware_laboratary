import pytest
import shutil
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock
from vhl_common.urp.data_types import AgentDescriptor, MessageEnvelope
from librarian_agent.urp_librarian import LibrarianURPAgent, LibrarianContext

@pytest.fixture
def temp_project_dir(tmp_path):
    # Setup a mock project structure in a temp directory
    project_root = tmp_path / "test_project"
    project_root.mkdir()
    
    # Create lib directory
    lib_dir = project_root / "lib"
    lib_dir.mkdir()
    
    # Create module directory
    module_dir = project_root / "my_module"
    module_dir.mkdir()
    
    return project_root, module_dir

@pytest.mark.asyncio
async def test_postconditions_success(temp_project_dir):
    project_root, module_dir = temp_project_dir
    
    # Create a mock file in lib/imports
    imports_dir = project_root / "lib" / "imports"
    imports_dir.mkdir(parents=True)
    (imports_dir / "some_component.json").write_text("{}")
    
    # Create a dummy scud file in the module dir
    scud_file = module_dir / "my_module.scud"
    scud_file.write_text("Dummy SCUD")
    
    # Mock workspace manager
    workspace_mock = MagicMock()
    workspace_mock.project_name = "test_project"
    workspace_mock.project_root = project_root
    workspace_mock.module_paths = {"my_module": module_dir}
    workspace_mock.get_file_changes.return_value = "Added a section:\n### Library Mapping:\n- compA -> libA"
    workspace_mock.record_operation = MagicMock(return_value=123)
    
    # Mock sync manager
    sync_mock = MagicMock()
    sync_mock.sync_library = AsyncMock()
    
    # Initialize the agent
    desc = AgentDescriptor(
        agent_id="my_module.librarian",
        name="Librarian Agent",
        version="1.0",
        capabilities=["LIBRARY_RESOLUTION"],
        accepted_message_types=["IMPORT_COMPONENTS"]
    )
    agent = LibrarianURPAgent(descriptor=desc)
    
    context = {
        "module_name": "my_module",
        "workspace": workspace_mock,
        "sqlite_manager": MagicMock(),
        "sync_manager": sync_mock,
        "config": MagicMock()
    }
    agent.initialize(context=context, emit_callback=MagicMock())
    
    message = MessageEnvelope(
        type="IMPORT_COMPONENTS",
        payload={"text": "import components"},
        sender="test_suite",
        receiver="my_module.librarian"
    )
    
    success, msg = await agent._check_postconditions(message, result=None)
    
    assert success is True
    assert "Postconditions check passed" in msg
    sync_mock.sync_library.assert_called_once_with("test_project")
    workspace_mock.get_file_changes.assert_called_once_with(scud_file)
    workspace_mock.record_operation.assert_called_once_with(
        module_name="my_module",
        op_name="LIBRARY_UPDATE",
        author="my_module.librarian",
        status="SUCCESS",
        payload={"library_updated": True, "scud_updated": True},
        commit_message="Library update by Librarian agent"
    )

@pytest.mark.asyncio
async def test_postconditions_fail_empty_lib(temp_project_dir):
    project_root, module_dir = temp_project_dir
    # lib/ directory exists but is empty (no files)
    
    # Create a dummy scud file in the module dir
    scud_file = module_dir / "my_module.scud"
    scud_file.write_text("Dummy SCUD")
    
    # Mock workspace manager
    workspace_mock = MagicMock()
    workspace_mock.project_name = "test_project"
    workspace_mock.project_root = project_root
    workspace_mock.module_paths = {"my_module": module_dir}
    workspace_mock.get_file_changes.return_value = "### Library Mapping:"
    workspace_mock.record_operation = MagicMock()
    
    # Mock sync manager
    sync_mock = MagicMock()
    sync_mock.sync_library = AsyncMock()
    
    # Initialize the agent
    desc = AgentDescriptor(
        agent_id="my_module.librarian",
        name="Librarian Agent",
        version="1.0",
        capabilities=["LIBRARY_RESOLUTION"],
        accepted_message_types=["IMPORT_COMPONENTS"]
    )
    agent = LibrarianURPAgent(descriptor=desc)
    
    context = {
        "module_name": "my_module",
        "workspace": workspace_mock,
        "sqlite_manager": MagicMock(),
        "sync_manager": sync_mock,
        "config": MagicMock()
    }
    agent.initialize(context=context, emit_callback=MagicMock())
    
    message = MessageEnvelope(
        type="IMPORT_COMPONENTS",
        payload={"text": "import components"},
        sender="test_suite",
        receiver="my_module.librarian"
    )
    
    success, msg = await agent._check_postconditions(message, result=None)
    
    assert success is False
    assert "No files created in lib directory" in msg
    workspace_mock.record_operation.assert_not_called()

@pytest.mark.asyncio
async def test_postconditions_fail_missing_scud_mapping(temp_project_dir):
    project_root, module_dir = temp_project_dir
    
    # Create a mock file in lib/imports
    imports_dir = project_root / "lib" / "imports"
    imports_dir.mkdir(parents=True)
    (imports_dir / "some_component.json").write_text("{}")
    
    # Create a dummy scud file in the module dir
    scud_file = module_dir / "my_module.scud"
    scud_file.write_text("Dummy SCUD")
    
    # Mock workspace manager (no Library Mapping in git diff)
    workspace_mock = MagicMock()
    workspace_mock.project_name = "test_project"
    workspace_mock.project_root = project_root
    workspace_mock.module_paths = {"my_module": module_dir}
    workspace_mock.get_file_changes.return_value = "Modified some other section"
    workspace_mock.record_operation = MagicMock()
    
    # Mock sync manager
    sync_mock = MagicMock()
    sync_mock.sync_library = AsyncMock()
    
    # Initialize the agent
    desc = AgentDescriptor(
        agent_id="my_module.librarian",
        name="Librarian Agent",
        version="1.0",
        capabilities=["LIBRARY_RESOLUTION"],
        accepted_message_types=["IMPORT_COMPONENTS"]
    )
    agent = LibrarianURPAgent(descriptor=desc)
    
    context = {
        "module_name": "my_module",
        "workspace": workspace_mock,
        "sqlite_manager": MagicMock(),
        "sync_manager": sync_mock,
        "config": MagicMock()
    }
    agent.initialize(context=context, emit_callback=MagicMock())
    
    message = MessageEnvelope(
        type="IMPORT_COMPONENTS",
        payload={"text": "import components"},
        sender="test_suite",
        receiver="my_module.librarian"
    )
    
    success, msg = await agent._check_postconditions(message, result=None)
    
    assert success is False
    assert "Library Mapping" in msg
    workspace_mock.record_operation.assert_not_called()

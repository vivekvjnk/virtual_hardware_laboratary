
import os
import asyncio
import tempfile
import subprocess
import jinja2
from typing import Optional
import yaml
from typing import Any
from fastapi import HTTPException
from virtual_hardware_lab.simulation_core.simulation_manager import SimulationManager # Needed for metadata parsing and ngspice path
import logging

logger = logging.getLogger("virtual_hardware_lab")

def jsonrpc_success(result: Any, id_val: Any):
    return {"jsonrpc": "2.0", "result": result, "id": id_val}

def jsonrpc_error(code: int, message: str, id_val: Any = None, data: Any = None):
    err = {"code": code, "message": message}
    if data is not None:
        err["data"] = data
    return {"jsonrpc": "2.0", "error": err, "id": id_val}


def _parse_metadata_from_content(content: str):
    """
    Parses YAML metadata from the top of a .j2 file's content.
    Metadata is expected to be between `* ---` and `* ---` lines.
    Returns a tuple of (metadata_dict, content_without_metadata).
    If no metadata is found, returns ({}, original_content).
    """
    metadata_start_tag = '* ---\n'
    metadata_end_tag = '* ---\n'

    start_index = content.find(metadata_start_tag)
    end_index = content.find(metadata_end_tag, start_index + len(metadata_start_tag))

    if start_index == -1 or end_index == -1:
        return {}, content # No metadata found

    metadata_block = content[start_index + len(metadata_start_tag):end_index].strip()

    # Remove the leading '* ' from each line in the metadata block
    cleaned_metadata_block = '\n'.join([line[2:] if line.startswith('* ') else line for line in metadata_block.splitlines()])

    try:
        metadata = yaml.safe_load(cleaned_metadata_block)
    except yaml.YAMLError as e:
        print(f"Error parsing YAML metadata from content: {e}")
        metadata = {}
    
    # Content after the metadata block
    content_without_metadata = content[end_index + len(metadata_end_tag):].strip()
    return metadata, content_without_metadata

async def _validate_spice_code(spice_code: str) -> Optional[str]:
    """
    Validates SPICE code using ngspice in batch mode.
    Returns an error message string if ngspice reports errors, otherwise returns None.
    """
    print(f"--- SPICE Code being validated by ngspice ---\n{spice_code}\n---------------------------------------------")
    if not spice_code.strip():
        return "SPICE code is empty."

    with tempfile.NamedTemporaryFile(mode='w+', suffix='.cir', delete=False) as temp_file:
        temp_file.write(spice_code)
        temp_file_path = temp_file.name
    try:
        command = ["ngspice", "-b", temp_file_path]
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        stdout_str = stdout.decode('utf-8')
        stderr_str = stderr.decode('utf-8')
        full_output = f"ngspice stdout:\n{stdout_str}\nngspice stderr:\n{stderr_str}"

        if process.returncode != 0:
            if "error:" in stdout_str.lower() or "error:" in stderr_str.lower():
                error_message = f"ngspice validation failed with exit code {process.returncode}.\n"
                error_message += full_output
                return f"SPICE code validation failed: {error_message}"
            else:
                logger.warning(f"ngspice finished with non-zero exit code {process.returncode}, but no explicit errors found. Output:\n{full_output}")
                return None # It's a warning, not a critical error
        return None # Success
    finally:
        os.remove(temp_file_path)

def safe_join(base_dir: str, *paths: str) -> str:
    candidate = os.path.abspath(os.path.join(base_dir, *paths))
    base_dir_abs = os.path.abspath(base_dir)
    if not candidate.startswith(base_dir_abs):
        raise ValueError("Invalid path (possible path traversal).")
    return candidate

async def save_and_validate_template_file(directory: str, filename: str, content: str):
    if not filename.endswith(".j2"):
        logger.warning(f"Filename {filename} does not end with .j2 extension. Changing extension to .j2.")
        filename = os.path.splitext(filename)[0] + ".j2"
        

    # 1. Parse metadata to get default parameters for rendering
    metadata, template_content = _parse_metadata_from_content(content)
    template_params = {}
    if 'parameters' in metadata:
        for param_name, param_info in metadata['parameters'].items():
            if 'default' in param_info:
                template_params[param_name] = param_info['default']
            elif 'type' in param_info:
                # Provide a dummy value based on type for validation if no default
                if param_info['type'] == 'float':
                    template_params[param_name] = 0.0
                elif param_info['type'] == 'int':
                    template_params[param_name] = 0
                elif param_info['type'] == 'str':
                    template_params[param_name] = "dummy_string"
                elif param_info['type'] == 'bool':
                    template_params[param_name] = False
    
    # 2. Render the template with dummy parameters for validation
    env = jinja2.Environment(loader=jinja2.BaseLoader)
    template = env.from_string(template_content)
    rendered_spice_code = template.render(template_params)

    # 3. Validate the rendered SPICE code using ngspice
    validation_error = await _validate_spice_code(rendered_spice_code)
    if validation_error:
        logger.error(f"SPICE validation failed for {filename}: {validation_error}")
        return {"error": validation_error}

    # 4. If validation passes, save the original .j2 file
    os.makedirs(directory, exist_ok=True)
    file_path = safe_join(directory, filename)

    def write_file():
        with open(file_path, "w") as f:
            f.write(content)
    await asyncio.to_thread(write_file)

    return {"filename": filename, "message": f"Successfully uploaded and validated {filename} to {directory}"}


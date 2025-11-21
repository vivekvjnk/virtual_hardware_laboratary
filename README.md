
# ngspice_simulator

This project provides a Python package for managing and running ngspice simulations. It leverages FastAPI for building a web interface or API, Jinja2 for templating (if a web interface is present), Matplotlib and NumPy for data processing and visualization, Pydantic for data validation, Uvicorn as an ASGI server, and PyYAML for configuration.

## Features

*   **ngspice Simulation Management**: Facilitates the setup, execution, and analysis of ngspice circuit simulations.
*   **Model and Control Upload**: Allows users to upload their own ngspice model and control template files (`.j2`) to the server.
*   **Web Interface/API**: Built with FastAPI, allowing for interaction with the simulator through a web interface or programmatic API calls.
*   **Data Validation**: Uses Pydantic for robust data validation, ensuring consistency and correctness of simulation parameters and results.
*   **Data Visualization**: Integrates Matplotlib and NumPy for processing and visualizing simulation outputs.

## Installation

To install the `ngspice_simulator` package, first clone the repository:

```bash
git clone https://github.com/vivekvjnk/ngspice_simulator.git
cd ngspice_simulator
```

Then, install the required dependencies:

```bash
pip install -r requirements.txt
```

Finally, install the package:

```bash
pip install .
```

## Usage

### Running the MCP Server
To start the MCP server, navigate to the project's root directory and run:

```bash
uvicorn ngspice_simulator_package.mcp_server:app --host 0.0.0.0 --port 55273
```

The server will be accessible at `http://localhost:55273`.

### Uploading Model and Control Files
You can upload your own ngspice model (`.j2`) and control (`.j2`) template files using the dedicated API endpoints.

**Upload a Model File:**
```bash
curl -X POST -F "file=@/path/to/your/model.j2" http://localhost:55273/upload_model
```

**Upload a Control File:**
```bash
curl -X POST -F "file=@/path/to/your/control.j2" http://localhost:55273/upload_control
```
Replace `/path/to/your/model.j2` and `/path/to/your/control.j2` with the actual paths to your files.

### Listing Available Models and Controls
(Further usage instructions will be added here once the project's specific functionalities are detailed.)

## Project Structure

*   `controls/`: Likely contains control scripts or configuration files for simulations.
*   `docs/`: Documentation files for the project.
*   `models/`: Could contain Pydantic models for data structures used in the simulations or API.
*   `ngspice_simulator_package/`: The core Python package containing:
    *   `__init__.py`: Initializes the package.
    *   `mcp_server.py`: Potentially a multi-client process server or a server-related component.
    *   `simulation_manager.py`: Manages the ngspice simulation process.
*   `runs/`: Directory for storing simulation run outputs or results.
*   `requirements.txt`: Lists all Python dependencies.
*   `setup.py`: Setup script for the Python package.

## Dependencies

The project relies on the following Python libraries:

*   `fastapi`: For building APIs.
*   `jinja2`: A modern and designer-friendly templating language for Python.
*   `matplotlib`: For creating static, animated, and interactive visualizations in Python.
*   `numpy`: The fundamental package for scientific computing with Python.
*   `pydantic`: Data validation and settings management using Python type hints.
*   `uvicorn`: An ASGI web server for Python.
*   `PyYAML`: A YAML parser and emitter for Python.

## Contributing

(Contribution guidelines will be added here.)

## License

This project is licensed under the MIT License - see the `LICENSE` file for details. (Note: A `LICENSE` file is not currently present in the repository, but it's good practice to include one.)


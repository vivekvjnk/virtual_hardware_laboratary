
# ngspice_simulator

This project provides a Python package for managing and running ngspice simulations. It leverages FastAPI for building a web interface or API, Jinja2 for templating (if a web interface is present), Matplotlib and NumPy for data processing and visualization, Pydantic for data validation, Uvicorn as an ASGI server, and PyYAML for configuration.

## Features

*   **ngspice Simulation Management**: Facilitates the setup, execution, and analysis of ngspice circuit simulations.
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


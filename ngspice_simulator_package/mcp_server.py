import os
import uvicorn
import yaml
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional

from .simulation_manager import SimulationManager # Assuming simulation_manager.py is in the same directory

# Initialize SimulationManager
manager = SimulationManager()

app = FastAPI(
    title="Virtual Hardware Lab MCP Server",
    description="API for managing and running SPICE simulations using the SimulationManager."
)

# Pydantic models for request bodies
class RunExperimentRequest(BaseModel):
    model_name: str = Field(..., description="Name of the model template (e.g., 'randles_cell.j2').")
    model_params: Dict[str, Any] = Field({}, description="Parameters to pass to the model template.")
    control_name: str = Field(..., description="Name of the control template (e.g., 'eis_control.j2').")
    control_params: Dict[str, Any] = Field({}, description="Parameters to pass to the control template.")
    sim_id: Optional[str] = Field(None, description="Optional simulation ID. If not provided, one will be generated.")

@app.get("/", summary="Root endpoint")
async def root():
    return {"message": "Virtual Hardware Lab MCP Server is running!"}

@app.get("/models", summary="List all available model templates")
async def list_models():
    """
    Retrieves a list of all available SPICE model templates along with their embedded metadata.
    """
    models = manager.list_models()
    return JSONResponse(content=models)

@app.get("/controls", summary="List all available control templates")
async def list_controls():
    """
    Retrieves a list of all available SPICE control templates along with their embedded metadata.
    """
    controls = manager.list_controls()
    return JSONResponse(content=controls)

@app.post("/run_experiment", summary="Run a new simulation experiment")
async def run_experiment(request: RunExperimentRequest):
    """
    Triggers a new SPICE simulation experiment using the specified model and control templates
    and their respective parameters. Returns the manifest of the completed simulation.
    """
    try:
        manifest = manager.start_sim(
            model_name=request.model_name,
            model_params=request.model_params,
            control_name=request.control_name,
            control_params=request.control_params,
            sim_id=request.sim_id
        )
        return JSONResponse(content=manifest)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/results/{sim_id}", summary="Get simulation results (manifest)")
async def get_results(sim_id: str):
    """
    Retrieves the manifest (detailed results and metadata) for a specific simulation ID.
    """
    manifest = manager.read_results(sim_id)
    if manifest:
        return JSONResponse(content=manifest)
    raise HTTPException(status_code=404, detail=f"Simulation with ID '{sim_id}' not found.")

@app.get("/results/{sim_id}/artifact/{artifact_filename}", summary="Get a specific simulation artifact")
async def get_artifact(sim_id: str, artifact_filename: str):
    """
    Retrieves a specific artifact (e.g., .png plot, .log file, .txt data)
    from a completed simulation run.
    """
    artifact_path = os.path.join(manager.runs_dir, sim_id, artifact_filename)
    if not os.path.exists(artifact_path):
        raise HTTPException(status_code=404, detail="Artifact not found.")

    # Security check: Ensure the requested file is within the sim_id's directory
    # and not trying to access files outside.
    abs_artifact_path = os.path.abspath(artifact_path)
    abs_run_dir = os.path.abspath(os.path.join(manager.runs_dir, sim_id))

    if not abs_artifact_path.startswith(abs_run_dir):
        raise HTTPException(status_code=400, detail="Invalid artifact path.")

    return FileResponse(artifact_path)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=53328)


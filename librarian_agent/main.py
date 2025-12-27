import argparse
import os
import sys
from dotenv import load_dotenv

# Add the current directory to sys.path to allow imports if running from root
sys.path.append(os.getcwd())

from librarian_agent.agent import LibrarianAgent

def main():
    load_dotenv() # Load env vars from .env if present

    parser = argparse.ArgumentParser(description="Librarian Agent for VHL")
    parser.add_argument(
        "--scud_path", 
        help="Path to the SCUD (Shared Circuit Understanding Document) file"
    )
    parser.add_argument(
        "--mcp-url", 
        default="http://localhost:8080/mcp",
        help="URL of the VHL Library MCP Server (default: http://localhost:8080/mcp)"
    )

    args = parser.parse_args()
    if not args.scud_path:
        args.scud_path = "./docs/bq79616_scud.md"
        
    scud_path = os.path.abspath(args.scud_path)
    
    try:
        agent = LibrarianAgent(mcp_url=args.mcp_url)
        agent.process_scud(scud_path)
        print(f"Successfully processed SCUD file: {scud_path}")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()

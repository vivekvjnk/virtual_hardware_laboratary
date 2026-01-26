from mcp_utils import list_mcp_tools, call_mcp_function
import json

def main():
    # 1. List tools from VAP server
    vap_url = "http://localhost:8081/mcp"
    print(f"--- Tools on VAP ({vap_url}) ---")
    try:
        vap_tools = list_mcp_tools(vap_url)
        for tool in vap_tools:
            print(f"Tool: {tool['name']}")
            print(f"  Description: {tool['description']}")
    except Exception as e:
        print(f"Error listing VAP tools: {e}")

    # 2. List tools from VHL Library server
    vhl_url = "http://localhost:8080/mcp"
    print(f"\n--- Tools on VHL Library ({vhl_url}) ---")
    try:
        vhl_tools = list_mcp_tools(vhl_url)
        for tool in vhl_tools:
            print(f"Tool: {tool['name']}")
    except Exception as e:
        print(f"Error listing VHL tools: {e}")

    # 3. Call a function (Example: list_local_components)
    print(f"\n--- Calling list_local_components on VHL ---")
    try:
        result = call_mcp_function(vhl_url, "list_local_components")
        # result is an MCPToolObservation
        # We can access the text content or the raw content blocks
        print("Result:")
        print(result.text)
    except Exception as e:
        print(f"Error calling function: {e}")

if __name__ == "__main__":
    main()

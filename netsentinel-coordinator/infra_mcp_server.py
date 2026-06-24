import json
from mcp.server.fastmcp import FastMCP

# Create the FastMCP server
mcp = FastMCP("NetSentinel-Infra-Gateway")

@mcp.tool()
def get_kubernetes_pod_logs(pod_name: str, namespace: str = "production") -> str:
    """Get the logs for a Kubernetes pod."""
    if "payment-processor" in pod_name:
        return "ERROR: java.lang.OutOfMemoryError: Java heap space\nProcess exited with code 137"
    return f"Pod {pod_name} in namespace {namespace} is running normally."

@mcp.tool()
def check_network_latency(source: str, target: str) -> str:
    """Check the network latency between a source and a target."""
    if target == "db-primary":
        result = {
            "source": source,
            "target": target,
            "status": "CRITICAL",
            "p99_latency_ms": 15400
        }
        return json.dumps(result, indent=2)
    
    result = {
        "source": source,
        "target": target,
        "status": "OK",
        "p99_latency_ms": 12
    }
    return json.dumps(result, indent=2)

if __name__ == "__main__":
    # Run the MCP server using the stdio transport
    mcp.run(transport="stdio")

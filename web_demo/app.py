"""
Serbian Data MCP — Live Web Demo

Bridge between Google Gemini (free tier) and the Serbian Data MCP server.
Provides a chat interface where users ask questions about Serbian open data
and the LLM calls MCP tools to search, fetch, and visualize data.

Usage (local dev):
    export GEMINI_API_KEY=your-key
    uv run python web_demo/app.py

Deployment (Render.com):
    gunicorn wsgi:app
"""

import asyncio
import os
import sys
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
from google import genai
from google.genai import types

# Add src/ to path for MCP server imports
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT / "src"))

from serbian_data_mcp import mcp  # noqa: E402

# Resolve paths relative to project root
_STATIC_DIR = Path(__file__).resolve().parent / "static"
_EXPORTS_DIR = _PROJECT_ROOT / "exports"

app = Flask(__name__, static_folder=str(_STATIC_DIR))

# ---------------------------------------------------------------------------
# MCP tool → Gemini function declaration adapter
# ---------------------------------------------------------------------------

EXPOSED_TOOLS = [
    "search_datasets",
    "list_organizations",
    "suggest_datasets",
    "get_dataset",
    "get_resource_data",
    "data_profile",
    "create_chart",
    "transform_data",
    "extract_data_insights",
    "generate_data_narrative",
    "create_serbia_map",
    "export_visualization",
    "health_check",
]

_tool_cache: list[dict] | None = None


async def get_mcp_tool_schemas() -> list[dict]:
    """Load MCP tool schemas and clean for Gemini compatibility."""
    global _tool_cache
    if _tool_cache is not None:
        return _tool_cache

    tools_raw = await mcp.list_tools()
    _tool_cache = []
    for tool in tools_raw:
        if tool.name not in EXPOSED_TOOLS:
            continue

        schema = tool.parameters
        props = schema.get("properties", {})
        required = schema.get("required", [])

        # Gemini doesn't like "anyOf" for optional fields — flatten to single type
        cleaned_props = {}
        for pname, pinfo in props.items():
            cleaned = dict(pinfo)
            if "anyOf" in cleaned:
                options = [t for t in cleaned["anyOf"] if t.get("type") != "null"]
                if options:
                    cleaned["type"] = options[0].get("type", "string")
                else:
                    cleaned["type"] = "string"
                del cleaned["anyOf"]
            cleaned_props[pname] = cleaned

        _tool_cache.append(
            {
                "name": tool.name,
                "description": str(tool.description) if tool.description else "",
                "parameters": {
                    "type": "object",
                    "properties": cleaned_props,
                    "required": required,
                },
            }
        )
    return _tool_cache


def to_gemini_declarations(tool_schemas: list[dict]) -> list[types.FunctionDeclaration]:
    """Convert JSON Schema tool defs to Gemini FunctionDeclarations."""
    declarations = []
    for ts in tool_schemas:
        params = ts["parameters"]
        properties = {}
        for pname, pinfo in params.get("properties", {}).items():
            ptype = pinfo.get("type", "string")
            schema_kwargs: dict = {"type": ptype, "description": pinfo.get("description", "")}
            if ptype == "array" and "items" in pinfo:
                item_type = pinfo["items"].get("type", "string") if isinstance(pinfo["items"], dict) else "string"
                schema_kwargs["items"] = types.Schema(type=item_type)
            if ptype == "object":
                schema_kwargs["additional_properties"] = types.Schema(type="string")
            properties[pname] = types.Schema(**schema_kwargs)

        declarations.append(
            types.FunctionDeclaration(
                name=ts["name"],
                description=ts["description"],
                parameters=types.Schema(
                    type="object",
                    properties=properties,
                    required=params.get("required", []),
                ),
            )
        )
    return declarations


# ---------------------------------------------------------------------------
# MCP tool caller
# ---------------------------------------------------------------------------


async def call_mcp_tool(name: str, args: dict) -> str:
    """Call an MCP tool and return JSON string of the result."""
    try:
        result = await mcp.call_tool(name, args)
        if hasattr(result, "content"):
            parts = []
            for item in result.content:
                if hasattr(item, "text"):
                    parts.append(item.text)
                elif isinstance(item, dict) and "text" in item:
                    parts.append(item["text"])
            text = "\n".join(parts)
        elif isinstance(result, str):
            text = result
        else:
            text = str(result)

        # Truncate to avoid Gemini token limits
        if len(text) > 8000:
            text = text[:8000] + "\n...[truncated]"
        return text
    except Exception as e:
        return f"Error calling {name}: {e}"


# ---------------------------------------------------------------------------
# Gemini chat loop with tool calling
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are an AI assistant for Serbian open data (data.gov.rs). You help users find,
explore, and visualize datasets about Serbia — demographics, budgets, health, education, etc.

Rules:
- ALWAYS search for datasets first using search_datasets(). Never guess dataset/resource IDs.
- After finding datasets, use get_dataset() to get details and resource IDs.
- Use get_resource_data() to download actual data, then data_profile() to understand columns.
- When creating charts, pass the actual data rows from get_resource_data().
- For maps, use create_serbia_map() with district-level data.
- Keep responses concise and useful.
- When showing data, format it clearly.
- If you create a visualization, mention the file path so the user can view it.
- Serbian and English search terms both work.
- You can respond in both English and Serbian depending on what the user speaks."""


async def chat_with_tools(message: str, history: list[dict]) -> str:
    """Run one turn of the Gemini chat loop with MCP tool calling."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return (
            "Error: GEMINI_API_KEY environment variable not set. Get a free key at https://aistudio.google.com/apikey"
        )

    client = genai.Client(api_key=api_key)
    tool_schemas = await get_mcp_tool_schemas()
    declarations = to_gemini_declarations(tool_schemas)
    gemini_tools = [types.Tool(function_declarations=declarations)]

    # Build conversation for Gemini
    contents = []
    for msg in history[-10:]:
        role = "user" if msg["role"] == "user" else "model"
        contents.append(types.Content(role=role, parts=[types.Part(text=msg["text"])]))
    contents.append(types.Content(role="user", parts=[types.Part(text=message)]))

    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        tools=gemini_tools,
        temperature=0.3,
        max_output_tokens=4096,
    )

    # Tool-calling loop (max 8 rounds)
    for _ in range(8):
        response = await asyncio.to_thread(
            client.models.generate_content,
            model="gemini-2.0-flash",
            contents=contents,
            config=config,
        )

        candidate = response.candidates[0] if response.candidates else None
        if not candidate:
            return "No response generated."

        parts = candidate.content.parts
        has_function_call = any(p.function_call for p in parts if hasattr(p, "function_call") and p.function_call)

        if not has_function_call:
            text_parts = [p.text for p in parts if hasattr(p, "text") and p.text]
            return "\n".join(text_parts) if text_parts else "No text response."

        # Execute tool calls
        function_responses = []
        for part in parts:
            if hasattr(part, "function_call") and part.function_call:
                fc = part.function_call
                args = dict(fc.args) if fc.args else {}
                result_text = await call_mcp_tool(fc.name, args)
                function_responses.append(
                    types.Part(
                        function_response=types.FunctionResponse(
                            name=fc.name,
                            response={"result": result_text},
                        ),
                    )
                )

        contents.append(types.Content(role="model", parts=parts))
        contents.append(types.Content(role="user", parts=function_responses))

        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            tools=gemini_tools,
            temperature=0.3,
            max_output_tokens=4096,
        )

    return "Reached maximum tool call rounds. Try a more specific query."


# ---------------------------------------------------------------------------
# Flask routes
# ---------------------------------------------------------------------------


@app.route("/")
def index():
    return send_from_directory(str(_STATIC_DIR), "index.html")


@app.route("/chat", methods=["POST"])
def chat():
    """Handle a chat message. Returns JSON with 'response'."""
    data = request.get_json()
    message = data.get("message", "")
    history = data.get("history", [])

    if not message.strip():
        return jsonify({"response": "Please type a question."})

    result = asyncio.run(chat_with_tools(message, history))
    return jsonify({"response": result})


@app.route("/health")
def health():
    """Health check endpoint."""
    api_key = os.environ.get("GEMINI_API_KEY", "")
    return jsonify(
        {
            "status": "ok",
            "gemini_configured": bool(api_key),
            "note": "Set GEMINI_API_KEY env var" if not api_key else "Ready",
        }
    )


@app.route("/export/<path:filename>")
def serve_export(filename):
    """Serve generated HTML/PNG exports."""
    _EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    if not (_EXPORTS_DIR / filename).exists():
        return jsonify({"error": "File not found"}), 404
    return send_from_directory(str(_EXPORTS_DIR), filename)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print("🚀 Serbian Data MCP Web Demo")
    print(f"   URL: http://localhost:{port}")
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("   ⚠️  GEMINI_API_KEY not set! Get one free at:")
        print("   https://aistudio.google.com/apikey")
    else:
        print(f"   ✅ Gemini API key configured ({api_key[:8]}...)")
    app.run(host="0.0.0.0", port=port, debug=True)

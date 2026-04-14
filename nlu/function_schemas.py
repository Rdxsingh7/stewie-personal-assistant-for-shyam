
"""
Stewie Function Schemas — OpenAI function-calling definitions.

Defines all available "tools" that the LLM can call, mapping 1:1
with execution module methods. This is the contract between NLU and execution.
"""

# All available function schemas for OpenAI function calling
STEWIE_FUNCTION_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "open_application",
            "description": "Open/launch a Windows application by its name.",
            "parameters": {
                "type": "object",
                "properties": {
                    "app_name": {
                        "type": "string",
                        "description": "Name of the application to open (e.g., 'Chrome', 'Word', 'Notepad', 'Calculator').",
                    }
                },
                "required": ["app_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "close_application",
            "description": "Close/terminate a running Windows application by its name.",
            "parameters": {
                "type": "object",
                "properties": {
                    "app_name": {
                        "type": "string",
                        "description": "Name of the application to close.",
                    }
                },
                "required": ["app_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_brightness",
            "description": "Set the screen brightness to a specific level.",
            "parameters": {
                "type": "object",
                "properties": {
                    "level": {
                        "type": "integer",
                        "description": "Brightness level from 0 to 100.",
                        "minimum": 0,
                        "maximum": 100,
                    }
                },
                "required": ["level"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "adjust_brightness",
            "description": "Increase or decrease screen brightness by a relative amount.",
            "parameters": {
                "type": "object",
                "properties": {
                    "delta": {
                        "type": "integer",
                        "description": "Amount to change brightness by. Positive to increase, negative to decrease.",
                    }
                },
                "required": ["delta"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_volume",
            "description": "Set the system volume to a specific level.",
            "parameters": {
                "type": "object",
                "properties": {
                    "level": {
                        "type": "number",
                        "description": "Volume level from 0.0 (mute) to 1.0 (maximum).",
                        "minimum": 0.0,
                        "maximum": 1.0,
                    }
                },
                "required": ["level"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "toggle_mute",
            "description": "Toggle the system audio mute on or off.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "shutdown_pc",
            "description": "Shut down the computer after a delay.",
            "parameters": {
                "type": "object",
                "properties": {
                    "delay_seconds": {
                        "type": "integer",
                        "description": "Seconds to wait before shutdown. Default is 30.",
                        "default": 30,
                    }
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "restart_pc",
            "description": "Restart the computer after a delay.",
            "parameters": {
                "type": "object",
                "properties": {
                    "delay_seconds": {
                        "type": "integer",
                        "description": "Seconds to wait before restart. Default is 10.",
                        "default": 10,
                    }
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "lock_screen",
            "description": "Lock the Windows workstation.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_battery_level",
            "description": "Get the current battery percentage and charging status of the computer.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "type_text",
            "description": "Type/dictate text into the currently focused window.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "The text to type.",
                    },
                    "press_enter": {
                        "type": "boolean",
                        "description": "Whether to press the Enter key after typing. Useful for submitting searches, sending messages, or executing a URL. Default is true.",
                        "default": True,
                    }
                },
                "required": ["text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_screen",
            "description": "Read and return the text content currently visible on the screen using OCR.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "summarize_screen",
            "description": "Read the screen content and provide a concise summary of what's being displayed.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for information on a specific topic.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query.",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results to return. Default is 5.",
                        "default": 5,
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "research_topic",
            "description": "Conduct in-depth research on a topic by searching the web, extracting content from multiple sources, and compiling findings.",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "The topic to research.",
                    },
                    "depth": {
                        "type": "string",
                        "enum": ["brief", "detailed", "comprehensive"],
                        "description": "How deep the research should go. Default is 'detailed'.",
                        "default": "detailed",
                    },
                },
                "required": ["topic"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_document",
            "description": "Create a new Microsoft Word document with specified content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Title of the document.",
                    },
                    "content": {
                        "type": "string",
                        "description": "The text content to include in the document. Can be plain text or structured.",
                    },
                    "filename": {
                        "type": "string",
                        "description": "Filename for the document (without extension). If not provided, derived from title.",
                    },
                },
                "required": ["title", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "place_order",
            "description": "Place an order based on user specifications. Records the order and optionally opens relevant apps/websites.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_details": {
                        "type": "string",
                        "description": "Full description of the order to place.",
                    }
                },
                "required": ["order_details"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "self_report",
            "description": "Generate a self-analysis report showing what Stewie has learned from past interactions, including usage patterns, favorite apps, success rates, and learned corrections. Triggered by questions like 'what have you learned?', 'show me your report', or 'how are you improving?'.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "learning_stats",
            "description": "Get quick statistics about Stewie's learning progress — total commands, success rate, and corrections learned. Triggered by 'how are you doing?', 'your stats', or 'learning progress'.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]

# Quick lookup: function name → schema
SCHEMA_MAP = {
    schema["function"]["name"]: schema for schema in STEWIE_FUNCTION_SCHEMAS
}

# All available action names
AVAILABLE_ACTIONS = list(SCHEMA_MAP.keys())

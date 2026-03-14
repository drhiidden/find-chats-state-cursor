"""Export transcripts to various formats (markdown, json, html, cjson)."""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

from .models import TranscriptMetadata


def export_to_markdown(metadata: TranscriptMetadata, messages: List[Dict[str, Any]], output_path: Path) -> None:
    """Export transcript to enhanced markdown format."""
    from .summary import generate_summary
    
    # Generate summary with all metadata
    summary = generate_summary(metadata, messages)
    
    # Add full conversation
    summary += "\n\n---\n\n## Full Conversation\n\n"
    
    for msg in messages:
        role = msg.get("role", "unknown")
        timestamp = msg.get("timestamp", "")
        
        # Extract text content
        content = msg.get("message", {}).get("content", [])
        text = ""
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text += item.get("text", "")
        elif isinstance(content, str):
            text = content
        
        if text:
            summary += f"### {role.title()}\n\n"
            if timestamp:
                summary += f"*{timestamp}*\n\n"
            summary += f"{text}\n\n"
            summary += "---\n\n"
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(summary, encoding="utf-8")


def export_to_json(metadata: TranscriptMetadata, messages: List[Dict[str, Any]], output_path: Path) -> None:
    """Export transcript to structured JSON format."""
    export_data = {
        "metadata": metadata.to_aits_dict(),
        "messages": messages,
        "exported_at": datetime.utcnow().isoformat() + "Z",
        "exporter": {
            "tool": "cursor-org",
            "version": "0.3.0",
            "format": "structured_json"
        }
    }
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False)


def export_to_cjson(metadata: TranscriptMetadata, messages: List[Dict[str, Any]], output_path: Path) -> None:
    """
    Export transcript to CJSON (Common JSON) format for interoperability.
    
    Spec: https://docs.cjson.dev/
    """
    cjson_data = {
        "version": "1.0",
        "standard": "CJSON",
        "exported_at": datetime.utcnow().isoformat() + "Z",
        "source": {
            "ide": "Cursor",
            "tool": "cursor-transcript-organizer",
            "version": "0.3.0"
        },
        "session": {
            "id": metadata.uuid,
            "title": metadata.title or metadata.topic_raw,
            "created_at": metadata.created_at.isoformat() if metadata.created_at else None,
            "updated_at": metadata.updated_at.isoformat() if metadata.updated_at else None,
            "message_count": metadata.message_count,
            "workspace": str(metadata.workspace) if metadata.workspace else None,
            "metadata": {
                "model": metadata.model,
                "tool_calls_count": len(metadata.tool_calls),
                "token_usage": metadata.tokens,
                "files_touched": metadata.files_touched,
                "git_branch": metadata.git_branch,
                "git_commit": metadata.git_commit,
                "languages": metadata.languages,
                "thinking_blocks": len(metadata.thinking_blocks),
                "subagents_spawned": metadata.subagents_spawned,
            }
        },
        "messages": []
    }
    
    # Convert messages to CJSON format
    for msg in messages:
        role = msg.get("role")
        timestamp = msg.get("timestamp")
        
        # Extract content
        content = msg.get("message", {}).get("content", [])
        text = ""
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text += item.get("text", "")
        elif isinstance(content, str):
            text = content
        
        cjson_msg = {
            "type": msg.get("type", "message"),
            "uuid": msg.get("uuid"),
            "timestamp": timestamp,
            "role": role,
            "content": text,
            "metadata": {}
        }
        
        # Add tool calls if present
        if msg.get("toolUses"):
            cjson_msg["tool_calls"] = msg.get("toolUses")
        
        # Add thinking if present
        if msg.get("thinking"):
            cjson_msg["metadata"]["thinking"] = msg.get("thinking")
        
        # Add token usage if present
        if msg.get("tokenUsage"):
            cjson_msg["metadata"]["token_usage"] = msg.get("tokenUsage")
        
        cjson_data["messages"].append(cjson_msg)
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(cjson_data, f, indent=2, ensure_ascii=False)


def export_to_html(metadata: TranscriptMetadata, messages: List[Dict[str, Any]], output_path: Path) -> None:
    """Export transcript to styled HTML format."""
    html_template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
            color: #333;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
        }}
        .header h1 {{
            margin: 0 0 15px 0;
            font-size: 28px;
        }}
        .metadata {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 10px;
            font-size: 14px;
            opacity: 0.9;
        }}
        .metadata-item {{
            display: flex;
            flex-direction: column;
        }}
        .metadata-label {{
            font-weight: bold;
            margin-bottom: 3px;
        }}
        .stats {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .stats h2 {{
            margin-top: 0;
            color: #667eea;
        }}
        .message {{
            background: white;
            padding: 20px;
            margin-bottom: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .message.user {{
            border-left: 4px solid #667eea;
        }}
        .message.assistant {{
            border-left: 4px solid #764ba2;
        }}
        .message-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
            padding-bottom: 10px;
            border-bottom: 1px solid #eee;
        }}
        .role {{
            font-weight: bold;
            text-transform: uppercase;
            font-size: 12px;
            letter-spacing: 1px;
        }}
        .role.user {{
            color: #667eea;
        }}
        .role.assistant {{
            color: #764ba2;
        }}
        .timestamp {{
            color: #999;
            font-size: 12px;
        }}
        .message-content {{
            line-height: 1.6;
            white-space: pre-wrap;
        }}
        code {{
            background: #f4f4f4;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
        }}
        .footer {{
            text-align: center;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 2px solid #eee;
            color: #999;
            font-size: 14px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{title}</h1>
        <div class="metadata">
            <div class="metadata-item">
                <span class="metadata-label">UUID</span>
                <span>{uuid}</span>
            </div>
            <div class="metadata-item">
                <span class="metadata-label">Date</span>
                <span>{date}</span>
            </div>
            <div class="metadata-item">
                <span class="metadata-label">Messages</span>
                <span>{message_count}</span>
            </div>
            {model_section}
            {tokens_section}
        </div>
    </div>
    
    {stats_section}
    
    <div class="conversation">
        {messages_html}
    </div>
    
    <div class="footer">
        Generated by cursor-org on {export_date}
    </div>
</body>
</html>
"""
    
    # Build metadata sections
    model_section = ""
    if metadata.model:
        model_section = f"""
            <div class="metadata-item">
                <span class="metadata-label">Model</span>
                <span>{metadata.model}</span>
            </div>
        """
    
    tokens_section = ""
    if metadata.tokens and metadata.tokens.get("total", 0) > 0:
        tokens = metadata.tokens
        tokens_section = f"""
            <div class="metadata-item">
                <span class="metadata-label">Tokens</span>
                <span>{tokens['total']:,} ({tokens['input']:,} in / {tokens['output']:,} out)</span>
            </div>
        """
    
    # Build stats section
    stats_items = []
    if metadata.tool_calls:
        from collections import Counter
        tool_counts = Counter([tc.tool for tc in metadata.tool_calls])
        top_tools = ", ".join([f"{tool} ({count})" for tool, count in tool_counts.most_common(5)])
        stats_items.append(f"<p><strong>Tool Calls:</strong> {len(metadata.tool_calls)} total - {top_tools}</p>")
    
    if metadata.files_touched:
        stats_items.append(f"<p><strong>Files Touched:</strong> {len(metadata.files_touched)} unique files</p>")
    
    if metadata.thinking_blocks:
        stats_items.append(f"<p><strong>Extended Thinking:</strong> {len(metadata.thinking_blocks)} block(s)</p>")
    
    if metadata.subagents_spawned > 0:
        stats_items.append(f"<p><strong>Subagents:</strong> {metadata.subagents_spawned} spawned</p>")
    
    stats_section = ""
    if stats_items:
        stats_section = f"""
    <div class="stats">
        <h2>Session Statistics</h2>
        {''.join(stats_items)}
    </div>
        """
    
    # Build messages HTML
    messages_html = ""
    for msg in messages:
        role = msg.get("role", "unknown")
        timestamp = msg.get("timestamp", "")
        
        # Extract text content
        content = msg.get("message", {}).get("content", [])
        text = ""
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text += item.get("text", "")
        elif isinstance(content, str):
            text = content
        
        if text:
            # Escape HTML
            import html as html_module
            text_escaped = html_module.escape(text)
            
            messages_html += f"""
        <div class="message {role}">
            <div class="message-header">
                <span class="role {role}">{role}</span>
                <span class="timestamp">{timestamp}</span>
            </div>
            <div class="message-content">{text_escaped}</div>
        </div>
            """
    
    # Format final HTML
    html_content = html_template.format(
        title=metadata.title or metadata.topic_raw,
        uuid=metadata.uuid,
        date=metadata.start_time.strftime("%Y-%m-%d %H:%M"),
        message_count=metadata.message_count,
        model_section=model_section,
        tokens_section=tokens_section,
        stats_section=stats_section,
        messages_html=messages_html,
        export_date=datetime.now().strftime("%Y-%m-%d %H:%M")
    )
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html_content, encoding="utf-8")

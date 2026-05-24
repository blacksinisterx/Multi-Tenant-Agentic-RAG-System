"""
AI-DOC:
Purpose: Memory management system for multi-turn conversations with buffer and summary modes
Constraints: Thread-safe, tenant-isolated, configurable buffer limits
Manual QA: see plan.md -> Phase 4 Manual QA section

INTEGRATION: LangChain integration (mandatory for assignment) while preserving exact API compatibility
"""

import json
import threading
import yaml
import os
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path

# LangChain integration (mandatory for assignment)
try:
    from retrieval.langchain_memory import LangChainMemoryManager
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False


class MemoryManager:
    """
    Manages conversation memory with buffer and summary modes.
    
    Features:
    - Thread-safe operations for concurrent users
    - Tenant-isolated memory storage
    - Configurable buffer limits
    - Automatic summarization when buffer exceeds limits
    - Persistent storage with JSON serialization
    - LangChain integration (mandatory for assignment) while preserving exact API
    """
    
    def __init__(self, 
                 memory_dir: str = ".state/memory", 
                 buffer_limit: int = 10,
                 summary_mode: bool = True,
                 base_dir: str = ".",
                 config_path: str = "config.yaml"):
        """
        Initialize memory manager.
        
        Args:
            memory_dir: Directory to store memory files
            buffer_limit: Maximum number of messages in buffer before summarization
            summary_mode: Whether to use summarization (True) or simple truncation (False)
            base_dir: Base directory for config
            config_path: Path to config file
        """
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(exist_ok=True)
        self.buffer_limit = buffer_limit
        self.summary_mode = summary_mode
        self._memory_cache: Dict[str, Dict] = {}
        self._lock = threading.RLock()
        
        # Determine backend from config (mandatory LangChain integration)
        self.backend = "default"
        config_file = os.path.join(base_dir, config_path)
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    config = yaml.safe_load(f)
                    memory_config = config.get('memory', {})
                    if memory_config.get('use_langchain', False) or config.get('retrieval', {}).get('backend') == 'langchain':
                        self.backend = "langchain"
            except:
                pass
        
        # Initialize LangChain memory manager if available and configured
        if self.backend == "langchain" and LANGCHAIN_AVAILABLE:
            self.langchain_manager = LangChainMemoryManager(base_dir)
        else:
            self.langchain_manager = None
        
    def _get_memory_file(self, tenant_id: str) -> Path:
        """Get memory file path for tenant."""
        return self.memory_dir / f"{tenant_id}_memory.json"
    
    def _load_memory(self, tenant_id: str) -> Dict[str, Any]:
        """
        Load memory from file or cache.
        
        Returns:
            Dict with keys: buffer (list), summary (str), metadata (dict)
        """
        with self._lock:
            if tenant_id in self._memory_cache:
                return self._memory_cache[tenant_id]
            
            memory_file = self._get_memory_file(tenant_id)
            if memory_file.exists():
                try:
                    with open(memory_file, 'r', encoding='utf-8') as f:
                        memory = json.load(f)
                except (json.JSONDecodeError, IOError):
                    memory = self._create_empty_memory()
            else:
                memory = self._create_empty_memory()
            
            self._memory_cache[tenant_id] = memory
            return memory
    
    def _create_empty_memory(self) -> Dict[str, Any]:
        """Create empty memory structure."""
        return {
            "buffer": [],
            "summary": "",
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat(),
                "total_messages": 0,
                "summary_count": 0
            }
        }
    
    def _save_memory(self, tenant_id: str, memory: Dict[str, Any]) -> None:
        """Save memory to file."""
        with self._lock:
            memory["metadata"]["last_updated"] = datetime.now().isoformat()
            memory_file = self._get_memory_file(tenant_id)
            
            try:
                with open(memory_file, 'w', encoding='utf-8') as f:
                    json.dump(memory, f, indent=2, ensure_ascii=False)
                self._memory_cache[tenant_id] = memory
            except IOError as e:
                print(f"Warning: Failed to save memory for {tenant_id}: {e}")
    
    def add_message(self, tenant_id: str, role: str, content: str, metadata: Optional[Dict] = None) -> None:
        """
        Add a message to conversation memory.
        
        Args:
            tenant_id: Tenant identifier
            role: Message role (user/assistant/system)
            content: Message content
            metadata: Optional metadata (timestamp, etc.)
        """
        memory = self._load_memory(tenant_id)
        
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        
        memory["buffer"].append(message)
        memory["metadata"]["total_messages"] += 1
        
        # Check if buffer needs management
        if len(memory["buffer"]) > self.buffer_limit:
            if self.summary_mode:
                self._summarize_buffer(memory)
            else:
                self._truncate_buffer(memory)
        
        self._save_memory(tenant_id, memory)
    
    def _truncate_buffer(self, memory: Dict[str, Any]) -> None:
        """Simple truncation: keep only recent messages."""
        keep_count = max(1, self.buffer_limit // 2)  # Keep half the limit
        memory["buffer"] = memory["buffer"][-keep_count:]
    
    def _summarize_buffer(self, memory: Dict[str, Any]) -> None:
        """
        Summarize older messages and keep recent ones.
        Note: This is a simple implementation. In production, use LLM for better summaries.
        """
        if len(memory["buffer"]) <= 2:
            return
        
        # Keep last 3 messages, summarize the rest
        keep_count = 3
        to_summarize = memory["buffer"][:-keep_count]
        memory["buffer"] = memory["buffer"][-keep_count:]
        
        if to_summarize:
            # Simple summarization (could be enhanced with LLM)
            user_messages = [msg for msg in to_summarize if msg["role"] == "user"]
            assistant_messages = [msg for msg in to_summarize if msg["role"] == "assistant"]
            
            summary_parts = []
            if memory["summary"]:
                summary_parts.append(memory["summary"])
            
            summary_parts.append(f"Previous conversation: {len(user_messages)} user queries, {len(assistant_messages)} responses")
            
            if user_messages:
                recent_topics = [msg["content"][:50] + "..." if len(msg["content"]) > 50 
                               else msg["content"] for msg in user_messages[-2:]]
                summary_parts.append(f"Recent topics: {'; '.join(recent_topics)}")
            
            memory["summary"] = " | ".join(summary_parts)
            memory["metadata"]["summary_count"] += 1
    
    def get_context(self, tenant_id: str, include_summary: bool = True) -> str:
        """
        Get conversation context for LLM.
        
        Args:
            tenant_id: Tenant identifier
            include_summary: Whether to include summary in context
            
        Returns:
            Formatted context string
        """
        memory = self._load_memory(tenant_id)
        
        context_parts = []
        
        # Add summary if available and requested
        if include_summary and memory["summary"]:
            context_parts.append(f"Previous Context: {memory['summary']}")
        
        # Add recent messages from buffer
        if memory["buffer"]:
            context_parts.append("Recent Conversation:")
            for msg in memory["buffer"][-5:]:  # Last 5 messages
                role = msg["role"].capitalize()
                content = msg["content"][:200] + "..." if len(msg["content"]) > 200 else msg["content"]
                context_parts.append(f"{role}: {content}")
        
        return "\n".join(context_parts) if context_parts else "No previous conversation."
    
    def get_recent_messages(self, tenant_id: str, count: int = 5) -> List[Dict[str, Any]]:
        """Get recent messages from buffer."""
        memory = self._load_memory(tenant_id)
        return memory["buffer"][-count:] if memory["buffer"] else []
    
    def get_memory(self, tenant_id: str, memory_type: str = "buffer") -> Dict[str, Any]:
        """
        Get memory for tenant - API compatibility method for testing
        
        Args:
            tenant_id: Tenant identifier
            memory_type: Type of memory (buffer or summary)
            
        Returns:
            Dict with memory data
        """
        # Use LangChain memory manager if configured
        if self.langchain_manager and self.backend == "langchain":
            return self.langchain_manager.get_memory(tenant_id, memory_type)
        
        # Fallback to standard memory
        memory = self._load_memory(tenant_id)
        if memory_type == "summary":
            return {"buffer": [], "summary": memory.get("summary", "")}
        else:
            return {"buffer": memory.get("buffer", []), "summary": memory.get("summary", "")}
    
    def add_to_memory(self, tenant_id: str, user_msg: str, assistant_msg: str, memory_type: str = "buffer"):
        """
        Add to memory - API compatibility method for testing
        
        Args:
            tenant_id: Tenant identifier
            user_msg: User message
            assistant_msg: Assistant message
            memory_type: Type of memory (buffer or summary)
        """
        # Use LangChain memory manager if configured
        if self.langchain_manager and self.backend == "langchain":
            return self.langchain_manager.add_to_memory(tenant_id, user_msg, assistant_msg, memory_type)
        
        # Fallback to standard memory
        self.add_message(tenant_id, "user", user_msg)
        self.add_message(tenant_id, "assistant", assistant_msg)

    def clear_memory(self, tenant_id: str) -> bool:
        """
        Clear all memory for a tenant.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Clear LangChain memory if configured
            if self.langchain_manager and self.backend == "langchain":
                self.langchain_manager.clear_memory(tenant_id)
            
            with self._lock:
                # Remove from cache
                if tenant_id in self._memory_cache:
                    del self._memory_cache[tenant_id]
                
                # Remove file
                memory_file = self._get_memory_file(tenant_id)
                if memory_file.exists():
                    memory_file.unlink()
                
                return True
        except Exception as e:
            print(f"Error clearing memory for {tenant_id}: {e}")
            return False
    
    def get_memory_stats(self, tenant_id: str) -> Dict[str, Any]:
        """Get memory statistics for a tenant."""
        memory = self._load_memory(tenant_id)
        return {
            "total_messages": memory["metadata"]["total_messages"],
            "buffer_size": len(memory["buffer"]),
            "has_summary": bool(memory["summary"]),
            "summary_count": memory["metadata"]["summary_count"],
            "created_at": memory["metadata"]["created_at"],
            "last_updated": memory["metadata"]["last_updated"]
        }
    
    def list_tenants(self) -> List[str]:
        """List all tenants with memory files."""
        tenants = []
        for memory_file in self.memory_dir.glob("*_memory.json"):
            tenant_id = memory_file.stem.replace("_memory", "")
            tenants.append(tenant_id)
        return sorted(tenants)


# Utility functions for integration

def create_memory_manager(config: Dict[str, Any]) -> MemoryManager:
    """Create memory manager from config."""
    memory_config = config.get("memory", {})
    return MemoryManager(
        memory_dir=memory_config.get("directory", ".state/memory"),
        buffer_limit=memory_config.get("buffer_limit", 10),
        summary_mode=memory_config.get("summary_mode", True)
    )


def format_conversation_context(memory_manager: MemoryManager, tenant_id: str) -> str:
    """Format conversation context for LLM prompts."""
    return memory_manager.get_context(tenant_id, include_summary=True)
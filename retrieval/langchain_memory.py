from __future__ import annotations
import os, json
from typing import Optional, Dict, Any

try:
    from langchain.memory import ConversationBufferMemory, ConversationSummaryMemory
    from langchain_community.chat_message_histories import FileChatMessageHistory
    from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False

class LangChainMemoryManager:
    """LangChain-based memory manager that maintains exact API compatibility"""
    
    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        self.memory_dir = os.path.join(base_dir, ".state", "memory")
        os.makedirs(self.memory_dir, exist_ok=True)
        self.memories: Dict[str, Any] = {}

    def _get_memory_file(self, tenant_id: str, memory_type: str) -> str:
        """Get memory file path for tenant and type"""
        if memory_type == "buffer":
            return os.path.join(self.memory_dir, f"{tenant_id}_buffer.json")
        else:  # summary
            return os.path.join(self.memory_dir, f"{tenant_id}_summary.json")

    def _get_langchain_memory_key(self, tenant_id: str, memory_type: str) -> str:
        return f"{tenant_id}_{memory_type}"

    def get_memory(self, tenant_id: str, memory_type: str = "buffer") -> Dict[str, Any]:
        """Get memory for tenant - preserves exact API"""
        memory_key = self._get_langchain_memory_key(tenant_id, memory_type)
        
        if memory_key not in self.memories and LANGCHAIN_AVAILABLE:
            # Initialize LangChain memory
            memory_file = self._get_memory_file(tenant_id, memory_type)
            
            if memory_type == "buffer":
                # Use LangChain ConversationBufferMemory
                chat_history = FileChatMessageHistory(memory_file)
                self.memories[memory_key] = ConversationBufferMemory(
                    chat_memory=chat_history,
                    return_messages=True,
                    memory_key="history"
                )
            else:  # summary
                # Use LangChain ConversationSummaryMemory
                from agents.llm import build_messages, call_llm
                # Create a simple LLM wrapper for LangChain
                class SimpleLLM:
                    def __call__(self, prompt: str) -> str:
                        messages = build_messages("You are a helpful assistant that summarizes conversations.", prompt)
                        return call_llm(messages, model="hermes3:8b", temperature=0.1, max_tokens=200)
                
                chat_history = FileChatMessageHistory(memory_file)
                self.memories[memory_key] = ConversationSummaryMemory(
                    llm=SimpleLLM(),
                    chat_memory=chat_history,
                    return_messages=True,
                    memory_key="history"
                )

        # Return compatible format
        if memory_key in self.memories:
            langchain_memory = self.memories[memory_key]
            # Convert LangChain memory to expected format
            try:
                if memory_type == "buffer":
                    messages = langchain_memory.chat_memory.messages
                    buffer = []
                    for msg in messages:
                        if isinstance(msg, HumanMessage):
                            buffer.append({"role": "user", "content": msg.content})
                        elif isinstance(msg, AIMessage):
                            buffer.append({"role": "assistant", "content": msg.content})
                    return {"buffer": buffer, "summary": ""}
                else:  # summary
                    summary = langchain_memory.predict_new_summary(langchain_memory.chat_memory.messages, "")
                    return {"buffer": [], "summary": summary}
            except Exception:
                pass

        # Fallback to original implementation
        memory_file = self._get_memory_file(tenant_id, memory_type)
        if os.path.exists(memory_file):
            try:
                with open(memory_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        
        return {"buffer": [], "summary": ""}

    def add_to_memory(self, tenant_id: str, user_msg: str, assistant_msg: str, memory_type: str = "buffer"):
        """Add to memory - preserves exact API"""
        memory_key = self._get_langchain_memory_key(tenant_id, memory_type)
        
        if memory_key in self.memories and LANGCHAIN_AVAILABLE:
            # Use LangChain memory
            langchain_memory = self.memories[memory_key]
            try:
                langchain_memory.chat_memory.add_user_message(user_msg)
                langchain_memory.chat_memory.add_ai_message(assistant_msg)
                return
            except Exception:
                pass

        # Fallback to original implementation
        memory = self.get_memory(tenant_id, memory_type)
        if memory_type == "buffer":
            memory["buffer"].append({"role": "user", "content": user_msg})
            memory["buffer"].append({"role": "assistant", "content": assistant_msg})
        else:  # summary
            # For summary mode, update the summary
            current_summary = memory.get("summary", "")
            new_entry = f"User: {user_msg}\nAssistant: {assistant_msg}"
            if current_summary:
                memory["summary"] = f"{current_summary}\n\n{new_entry}"
            else:
                memory["summary"] = new_entry

        self._save_memory(tenant_id, memory, memory_type)

    def _save_memory(self, tenant_id: str, memory: Dict[str, Any], memory_type: str):
        """Save memory to file"""
        memory_file = self._get_memory_file(tenant_id, memory_type)
        os.makedirs(os.path.dirname(memory_file), exist_ok=True)
        with open(memory_file, 'w', encoding='utf-8') as f:
            json.dump(memory, f, indent=2, ensure_ascii=False)

    def clear_memory(self, tenant_id: str):
        """Clear all memory for tenant - preserves exact API"""
        memory_key_buffer = self._get_langchain_memory_key(tenant_id, "buffer")
        memory_key_summary = self._get_langchain_memory_key(tenant_id, "summary")
        
        # Clear LangChain memories if they exist
        if memory_key_buffer in self.memories:
            try:
                self.memories[memory_key_buffer].clear()
            except Exception:
                pass
            del self.memories[memory_key_buffer]
        
        if memory_key_summary in self.memories:
            try:
                self.memories[memory_key_summary].clear()
            except Exception:
                pass
            del self.memories[memory_key_summary]

        # Clear memory files
        for memory_type in ["buffer", "summary"]:
            memory_file = self._get_memory_file(tenant_id, memory_type)
            if os.path.exists(memory_file):
                try:
                    os.remove(memory_file)
                except Exception:
                    pass

    def get_context_string(self, tenant_id: str, memory_type: str = "buffer") -> str:
        """Get memory as context string - preserves exact API"""
        memory = self.get_memory(tenant_id, memory_type)
        
        if memory_type == "buffer":
            context_parts = []
            for turn in memory["buffer"][-10:]:  # Last 10 turns
                role = turn["role"]
                content = turn["content"]
                context_parts.append(f"{role.capitalize()}: {content}")
            return "\n".join(context_parts)
        else:  # summary
            return memory.get("summary", "")
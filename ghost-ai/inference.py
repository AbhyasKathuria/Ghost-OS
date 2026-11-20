"""Ghost-AI Offline Inference Engine.

Wraps llama-cpp-python for local compact GGUF models (e.g., Qwen2.5-3B-Instruct
or Llama-3.2-3B-Instruct Q4_K_M) stored in GhostVault/models/.
Includes deterministic fallback intelligence when no GGUF model is loaded.
"""

import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple

from ghost_ai.tools import VaultInspectionTools
from ghost_vault.db import GhostVaultDB

try:
    from llama_cpp import Llama
    HAS_LLAMA_CPP = True
except ImportError:
    HAS_LLAMA_CPP = False


class GhostAiCopilot:
    """Offline intelligence copilot querying encrypted vault state via local inference or deterministic fallback."""

    def __init__(self, models_dir: Optional[str] = None):
        if not models_dir:
            if os.path.exists("models"):
                models_dir = "models"
            elif os.path.exists("GhostVault/models"):
                models_dir = "GhostVault/models"
            else:
                models_dir = "models"
        self.models_dir = os.path.abspath(models_dir)
        self.llm = None
        self.model_name = None
        self._init_local_llm()

    def _init_local_llm(self) -> None:
        """Attempts to load a GGUF model if llama-cpp-python and a .gguf file are available."""
        if not HAS_LLAMA_CPP or not os.path.exists(self.models_dir):
            return

        for fname in os.listdir(self.models_dir):
            if fname.endswith(".gguf"):
                model_path = os.path.join(self.models_dir, fname)
                try:
                    llm = Llama(
                        model_path=model_path,
                        n_ctx=4096,
                        n_threads=max(1, (os.cpu_count() or 4) - 1),
                        verbose=False,
                    )
                    # Sanity check: Ensure weights are valid and generate actual text, not uninitialized token noise
                    test_out = llm("Hello", max_tokens=4)
                    test_text = test_out["choices"][0]["text"]
                    if not re.search(r"[a-zA-Z]{2,}", test_text):
                        self.llm = None
                        self.model_name = None
                        continue

                    self.llm = llm
                    self.model_name = fname
                    break
                except Exception:
                    self.llm = None
                    self.model_name = None

    @property
    def is_gguf_active(self) -> bool:
        return self.llm is not None

    def query(
        self,
        user_prompt: str,
        vault: GhostVaultDB,
        machine_fingerprint: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Processes a natural language query against the vault with verified database facts."""
        tools = VaultInspectionTools(vault)

        # If GGUF LLM is loaded and healthy, we run prompt grounding
        if self.is_gguf_active and self.llm:
            try:
                res = self._run_gguf_inference(user_prompt, tools, machine_fingerprint)
                reply = res.get("reply", "")
                # Guard against corrupted outputs or hallucinated token streams
                if len(re.findall(r"[a-zA-Z]{2,}", reply)) >= 4:
                    return res
            except Exception:
                # Fall back gracefully on inference error
                pass

        # Authoritative Deterministic Intelligence Fallback Engine
        return self._run_deterministic_synthesis(user_prompt, tools, machine_fingerprint)

    def _run_deterministic_synthesis(
        self,
        prompt: str,
        tools: VaultInspectionTools,
        fingerprint: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Deterministic query synthesizer that routes questions to exact SQL/tool assertions."""
        p_lower = prompt.lower()
        sources: List[str] = []
        reply_lines: List[str] = []

        # 1. SMART Attribute explanation questions
        smart_mappings = [
            ("percentage_used", ["percentage used", "percentage_used", "wear", "endurance", "flash life"]),
            ("available_spare", ["available spare", "available_spare", "spare blocks", "spare"]),
            ("critical_warning", ["critical warning", "critical_warning"]),
            ("media_errors", ["media error", "media_errors", "integrity error", "ecc"]),
            ("reallocated_sector_count", ["reallocated", "bad sector"]),
            ("temperature", ["temperature", "thermal", "overheat"]),
        ]

        matched_smart = None
        for canonical, aliases in smart_mappings:
            if any(alias in p_lower for alias in aliases):
                matched_smart = canonical
                break

        if ("smart" in p_lower and ("explain" in p_lower or "what is" in p_lower or "how" in p_lower)) or matched_smart:
            attr_target = matched_smart or "percentage_used"
            attr_info = tools.explain_smart_attribute(attr_target)
            sources.append(f"SMART Knowledge Base: {attr_info['title']}")

            reply_lines.append(f"### {attr_info['title']}\n")
            reply_lines.append(f"{attr_info['description']}\n")
            reply_lines.append(f"- **Critical Threshold:** {attr_info['critical_threshold']}")
            reply_lines.append(f"- **Technician Guidance:** {attr_info['recommended_action']}\n")

        # 2. Warning / Issue / Failure queries
        if any(w in p_lower for w in ["warning", "issue", "fail", "problem", "attention", "alert", "health"]):
            warnings = tools.find_warnings(machine_fingerprint=fingerprint)
            sources.append(f"Vault DB: diagnostic_results ({len(warnings)} found)")

            if not warnings:
                reply_lines.append("✓ **No critical warnings or hardware failures** detected across the evaluated scan records. All diagnostic assertions are nominal.")
            else:
                reply_lines.append(f"**Identified {len(warnings)} diagnostic attention item(s) in Vault records:**\n")
                for w in warnings[:6]:
                    reply_lines.append(f"- **[{w['status']}] {w['test_name']}** (Machine `{w['machine_fingerprint'][:10]}...`)")
                    reply_lines.append(f"  *Evidence:* {w['evidence']}")
                    reply_lines.append(f"  *Recommendation:* {w['recommendation']}\n")

        # 3. Hardware Change / Diff queries
        if any(w in p_lower for w in ["change", "diff", "upgrade", "replace", "degrade", "swapped", "since last"]):
            # Resolve target machine
            target_fp = fingerprint
            if not target_fp:
                machines = tools.vault.list_machines()
                if machines:
                    target_fp = machines[0]["machine_fingerprint"]

            if target_fp:
                diff_data = tools.compare_scans(target_fp)
                sources.append(f"HardwareDiffEngine: {target_fp[:12]}...")

                if "error" in diff_data:
                    reply_lines.append(f"Note regarding hardware diff: {diff_data['error']}")
                else:
                    reply_lines.append(f"**Hardware Delta Summary for `{target_fp[:12]}...`:**\n")
                    reply_lines.append(f"{diff_data['summary']}\n")

                    if diff_data.get("degradations"):
                        reply_lines.append("**Degradation Alerts:**")
                        for d in diff_data["degradations"]:
                            reply_lines.append(f"- ⚠️ [{d['component']}] {d['description']}")

                    if diff_data.get("changes"):
                        reply_lines.append("\n**Component Alterations:**")
                        for c in diff_data["changes"]:
                            reply_lines.append(f"- 🔹 [{c['component']} - {c['change_type']}] {c['description']}")

        # 4. Machine Details / Fleet Summary
        if not reply_lines or any(w in p_lower for w in ["fleet", "machine", "specs", "cpu", "ram", "memory", "battery", "storage"]):
            target_fp = fingerprint
            if not target_fp:
                machines = tools.vault.list_machines()
                if machines:
                    target_fp = machines[0]["machine_fingerprint"]

            if target_fp:
                history = tools.get_machine_history(target_fp)
                sources.append(f"Vault DB: machines ({target_fp[:12]}...)")
                m_info = history.get("machine", {})
                hw_info = history.get("hardware_summary", {})

                reply_lines.append(f"### Machine Status: `{target_fp[:16]}...`")
                reply_lines.append(f"- **Asset Tag:** {m_info.get('asset_tag') or 'Unassigned'}")
                reply_lines.append(f"- **Latest Health Score:** {m_info.get('latest_health_score')}/100")
                reply_lines.append(f"- **Total Scans Recorded:** {history.get('total_scans')}")

                if hw_info:
                    cpu = hw_info.get("cpu", {})
                    mem = hw_info.get("memory", {})
                    reply_lines.append(f"- **Processor:** {cpu.get('model')} ({cpu.get('physical_cores')}C / {cpu.get('logical_threads')}T)")
                    reply_lines.append(f"- **Installed Memory:** {round((mem.get('total_bytes', 0))/(1024**3), 1)} GB RAM")

        reply_text = "\n".join(reply_lines)
        return {
            "reply": reply_text,
            "sources": sources,
            "engine_used": "deterministic_fallback",
            "model_name": None,
        }

    def _run_gguf_inference(
        self,
        prompt: str,
        tools: VaultInspectionTools,
        fingerprint: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Executes offline GGUF inference grounded with tool facts."""
        # Pre-fetch relevant context
        warnings = tools.find_warnings(machine_fingerprint=fingerprint)
        system_prompt = (
            "You are the Ghost-OS Hardware Intelligence Copilot running offline from a USB drive. "
            "You have strict access to the encrypted Ghost Vault database. You MUST cite verified hardware telemetry "
            "and NEVER hallucinate specs. Here is the verified vault context:\n"
            f"Active Warnings: {json.dumps(warnings[:5])}\n"
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]

        output = self.llm.create_chat_completion(
            messages=messages,
            max_tokens=512,
            temperature=0.2,
        )

        reply = output["choices"][0]["message"]["content"]
        return {
            "reply": reply,
            "sources": [f"GGUF: {self.model_name}", "Vault SQLite"],
            "engine_used": "llama_cpp",
            "model_name": self.model_name,
        }

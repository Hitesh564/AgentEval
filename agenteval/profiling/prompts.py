"""
Versioned Profiler Prompts for AgentEval Workflow Profiling.
"""

from typing import Dict, List
from agenteval.profiling.models import WorkflowContext, ExecutableMetricSpec

PROFILER_VERSION = "1.0"

SYSTEM_PROFILER_PROMPT = """You are an expert AI agent evaluation profiler.
Your task is to analyze the execution evidence and topology of an agentic workflow and build a semantic evaluation profile for each node.

CRITICAL GUIDELINES:
1. DO NOT classify nodes based primarily on their names. A node named "node_a" or "interview_agent" must be analyzed by what it DOES (its inputs, outputs, tools, state, and graph position).
2. DO NOT restrict roles to primitive taxonomies like "planner", "retriever", "generator", "critic". Infer application-specific descriptive roles (e.g., "adaptive_interview_agent", "sql_execution_agent", "compliance_validator", "interview_planner").
3. DO NOT invent arbitrary executable metrics that do not exist. Select executable metrics ONLY from the provided Executable Metric Catalog.
4. If a conceptual dimension matters (e.g. adaptiveness), include it in evaluation_dimensions and map it to an applicable executable metric if available.
5. Provide a confidence score (0.0 to 1.0) for each inferred profile.
6. Return strict JSON matching the specified JSON schema format. Do not include markdown code blocks or extra conversational commentary outside the JSON object.
"""

def build_workflow_profiler_prompt(
    context: WorkflowContext,
    catalog: Dict[str, ExecutableMetricSpec]
) -> str:
    """Builds the structured prompt sent to the profiling LLM."""
    
    catalog_str_lines = []
    for metric_name, spec in catalog.items():
        catalog_str_lines.append(
            f"  - {spec.name}: {spec.description} (Required Inputs: {', '.join(spec.required_inputs)})"
        )
    catalog_summary = "\n".join(catalog_str_lines)

    nodes_summary_lines = []
    for nctx in context.node_contexts:
        nodes_summary_lines.append(
            f"""--- NODE: {nctx.node_id} ---
  - Node Name: {nctx.node_name}
  - Parent Nodes: {nctx.parents}
  - Child Nodes: {nctx.children}
  - Execution Order: {nctx.execution_order}
  - Tools Invoked: {nctx.tools_invoked}
  - Retrieved Docs Count: {nctx.retrieved_docs_count}
  - Inputs Excerpt: {nctx.inputs_excerpt}
  - Outputs Excerpt: {nctx.outputs_excerpt}
  - Tool Calls Excerpt: {nctx.tool_calls_excerpt}
  - Metadata: {nctx.metadata_excerpt}
"""
        )
    nodes_summary = "\n".join(nodes_summary_lines)

    prompt = f"""
WORKFLOW TO ANALYZE:
Session ID: {context.session_id}
Workflow ID: {context.workflow_id}
Total Nodes: {context.total_nodes}
Execution Graph (Parent -> Children): {context.execution_graph}
Global Workflow Inputs Excerpt: {context.global_inputs_excerpt}

NODE EXECUTION EVIDENCE:
{nodes_summary}

AVAILABLE EXECUTABLE METRIC CATALOG IN AGENTEVAL:
{catalog_summary}

INSTRUCTIONS:
Generate a JSON object with the following schema:
{{
  "workflow_id": "{context.workflow_id}",
  "purpose": "<Overall purpose of this agent workflow>",
  "node_profiles": [
    {{
      "node_id": "<node_id>",
      "inferred_role": "<descriptive_role>",
      "purpose": "<summary of node purpose>",
      "responsibilities": ["<responsibility 1>", "<responsibility 2>"],
      "inputs_summary": ["<input 1>"],
      "outputs_summary": ["<output 1>"],
      "tools_used": ["<tool 1>"],
      "evaluation_dimensions": [
        {{
          "dimension_name": "<dimension_name>",
          "description": "<why dimension matters>",
          "mapped_executable_metrics": ["<metric_name_from_catalog>"],
          "is_executable": true
        }}
      ],
      "executable_metrics": ["<metric_name_from_catalog>"],
      "metric_weights": {{
        "<metric_name_from_catalog>": 0.35
      }},
      "confidence": 0.95
    }}
  ]
}}

Ensure all metric names in executable_metrics match names in the EXECUTABLE METRIC CATALOG.
Respond ONLY with the raw JSON string.
"""
    return prompt

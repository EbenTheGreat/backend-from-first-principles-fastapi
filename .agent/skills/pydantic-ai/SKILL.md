---
name: Pydantic AI Quick Reference
description: A practical quick reference guide for building production-grade GenAI agents with Pydantic AI, covering agents, tools, output types, dependencies, multi-agent patterns, MCP, streaming, graphs, and supported models.
---

# Pydantic AI Quick Reference Guide

> **Source**: https://ai.pydantic.dev/llms-full.txt · **Fetched**: April 2026
> **Requires**: Python 3.10+ · `pip install pydantic-ai`

---

## 🚀 Installation

```bash
pip install pydantic-ai
# or with extras
pip install "pydantic-ai-slim[openai,google,logfire]"
uv add pydantic-ai
```

Optional extras: `logfire`, `evals`, `openai`, `vertexai`, `google`, `anthropic`, `groq`, `mistral`, `cohere`, `bedrock`, `huggingface`, `duckduckgo`, `tavily`, `exa`, `cli`, `mcp`, `fastmcp`, `a2a`, `ui`, `ag-ui`, `dbos`, `prefect`

---

## 🤖 Agents — Core Concept

An `Agent` is the primary interface for interacting with LLMs.

### Hello World

```python
from pydantic_ai import Agent

agent = Agent(
    'anthropic:claude-sonnet-4-6',
    instructions='Be concise, reply with one sentence.',
)

result = agent.run_sync('Where does "hello world" come from?')
print(result.output)
```

### Running an Agent (5 Ways)

```python
# 1. Async — returns RunResult
result = await agent.run('What is 2+2?')

# 2. Sync wrapper
result = agent.run_sync('What is 2+2?')

# 3. Async streaming context manager → StreamedRunResult
async with agent.run_stream('Tell me a story') as result:
    async for chunk in result.stream_text():
        print(chunk)

# 4. Async iterable of AgentStreamEvents
async for event in agent.run_stream_events('Hello'):
    print(event)

# 5. Context manager → AgentRun (async iterable over graph nodes)
async with agent.iter('Hello') as run:
    async for node in run:
        print('Node:', node)
```

### Instructions vs System Prompts

| | `instructions` | `system_prompt` |
|---|---|---|
| Scope | Current agent only | Retained across all message history |
| Recommended | ✅ Yes | For specific cross-agent use cases |

---

## 🧩 Dependencies (Dependency Injection)

```python
from dataclasses import dataclass
import httpx
from pydantic_ai import Agent, RunContext

@dataclass
class MyDeps:
    api_key: str
    http_client: httpx.AsyncClient

agent = Agent('openai:gpt-5.2', deps_type=MyDeps)

@agent.system_prompt
async def get_system_prompt(ctx: RunContext[MyDeps]) -> str:
    response = await ctx.deps.http_client.get('https://example.com')
    return f'Prompt: {response.text}'

# Override deps in tests
with agent.override(deps=test_deps):
    result = await application_code('Tell me a joke.')
```

---

## 🛠️ Function Tools

```python
import random
from pydantic_ai import Agent, RunContext

agent = Agent('google-gla:gemini-3-flash-preview', deps_type=str)

# Tool WITH context (access to deps, usage, etc.)
@agent.tool
def get_player_name(ctx: RunContext[str]) -> str:
    """Get the player's name."""
    return ctx.deps

# Tool WITHOUT context (pure function)
@agent.tool_plain
def roll_dice() -> str:
    """Roll a six-sided die and return the result."""
    return str(random.randint(1, 6))
```

> **Tool Schema**: Function signatures + docstrings (google, numpy, sphinx styles) are auto-extracted.

### Dynamic Tools (Conditional Availability)

```python
async def only_if_42(ctx: RunContext[int], tool_def: ToolDefinition) -> ToolDefinition | None:
    if ctx.deps == 42:
        return tool_def  # None = tool hidden from model

@agent.tool(prepare=only_if_42)
def hitchhiker(ctx: RunContext[int], answer: str) -> str:
    return f'{ctx.deps} {answer}'
```

### Tool Timeout

```python
agent = Agent('test', tool_timeout=30)      # default for all tools

@agent.tool_plain(timeout=5)                # override per tool
async def fast_tool() -> str:
    return 'Done'
```

---

## 📦 Structured Output

```python
from pydantic import BaseModel
from pydantic_ai import Agent

class CityLocation(BaseModel):
    city: str
    country: str

agent = Agent('google-gla:gemini-3-flash-preview', output_type=CityLocation)
result = agent.run_sync('Where were the 2012 Olympics held?')
print(result.output)  # city='London' country='United Kingdom'
```

### Output Modes

| Mode | How | Compatibility |
|---|---|---|
| Tool Output (default) | Tool calls | Most compatible |
| Native Output | Model's native JSON schema | Not all models |
| Prompted Output | Schema injected into instructions | Least reliable, most universal |

### Output Functions (Callable Output)

```python
def run_sql_query(query: str) -> list[Row]:
    """Run a SQL query on the database."""
    ...

sql_agent = Agent(
    'openai:gpt-5.2',
    output_type=[run_sql_query, SQLFailure],
    instructions='You are a SQL agent...',
)
```

### Streamed Structured Output

```python
async with agent.run_stream('Where does "hello world" come from?') as result:
    async for message in result.stream_text():
        print(message)
```

---

## 💬 Message History & Chat

```python
from pydantic_ai import Agent

agent = Agent('openai:gpt-5.2', instructions='Be a helpful assistant.')

result1 = agent.run_sync('Tell me a joke.')
result2 = agent.run_sync('Explain?', message_history=result1.new_messages())
```

### Storing / Restoring History (JSON)

```python
from pydantic_core import to_jsonable_python
from pydantic_ai import ModelMessagesTypeAdapter

history = result1.all_messages()
as_json = to_jsonable_python(history)
restored = ModelMessagesTypeAdapter.validate_python(as_json)
```

### History Processors (Filter Messages)

```python
from pydantic_ai.models import ModelMessage, ModelRequest

def filter_responses(messages: list[ModelMessage]) -> list[ModelMessage]:
    return [msg for msg in messages if isinstance(msg, ModelRequest)]

agent = Agent('openai:gpt-5.2', history_processors=[filter_responses])
```

---

## 🔁 Self-Correction / Retries

```python
from pydantic_ai import ModelRetry

@agent.tool
def my_tool(ctx, value: str) -> str:
    if value == "bad":
        raise ModelRetry("That value is invalid, try again.")
    return f"Got: {value}"
```

> Default retry count: **1**. Configurable per agent, tool, or output type.

---

## 🚦 Usage Limits

```python
from pydantic_ai import Agent, UsageLimits

result = agent.run_sync(
    'What is the capital of Italy?',
    usage_limits=UsageLimits(response_tokens_limit=10),
)
```

---

## ⚙️ Model Settings

```python
from pydantic_ai import Agent, ModelSettings

agent = Agent(model, model_settings=ModelSettings(temperature=0.5))
# Override per-run:
result = agent.run_sync('...', model_settings=ModelSettings(temperature=0.0))
```

---

## 🔌 Capabilities

Bundle tools, hooks, instructions, and model settings into a reusable unit.

```python
from pydantic_ai import Agent
from pydantic_ai.capabilities import Thinking, WebSearch

agent = Agent(
    'anthropic:claude-opus-4-6',
    capabilities=[Thinking(effort='high'), WebSearch()],
)
```

### Built-in Capabilities

| Capability | What it provides |
|---|---|
| `Thinking` | Model thinking/reasoning |
| `Hooks` | Decorator-based lifecycle hooks |
| `WebSearch` | Web search |
| `WebFetch` | URL fetching |
| `ImageGeneration` | Image generation |
| `MCP` | MCP server integration |
| `PrepareTools` | Filter/modify tool definitions per step |
| `PrefixTools` | Prefix tool names |
| `BuiltinTool` | Register a builtin tool |
| `Toolset` | Wraps an `AbstractToolset` |
| `HistoryProcessor` | Wraps a history processor |

### Custom Capability

```python
from dataclasses import dataclass
from typing import Any
from pydantic_ai.capabilities import AbstractCapability

@dataclass
class MathTools(AbstractCapability[Any]):
    """Provides basic math operations."""

    def get_toolset(self):
        return math_toolset

agent = Agent('openai:gpt-5.2', capabilities=[MathTools()])
```

---

## 🪝 Lifecycle Hooks

```python
from pydantic_ai import Agent, ModelRequestContext, RunContext
from pydantic_ai.capabilities import Hooks

hooks = Hooks()

@hooks.on.before_model_request
async def log_request(ctx: RunContext[None], request_context: ModelRequestContext):
    print(f'Sending {len(request_context.messages)} messages to the model')
    return request_context

agent = Agent('test', capabilities=[hooks])
```

**Hook firing points:**
- Run: `before_run`, `after_run`, `wrap_run`, `on_run_error`
- Node: `before_node_run`, `after_node_run`, `wrap_node_run`, `on_node_run_error`
- Model Request: `before_model_request`, `after_model_request`, `wrap_model_request`, `on_model_request_error`
- Tool Validate: `before_tool_validate`, `after_tool_validate`, `wrap_tool_validate`, `on_tool_validate_error`
- Tool Execute: `before_tool_execute`, `after_tool_execute`, `wrap_tool_execute`, `on_tool_execute_error`

---

## 🔗 MCP (Model Context Protocol)

### Client (consume MCP server)

```python
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStdio

server = MCPServerStdio('python', args=['-m', 'mcp_server'])
agent = Agent('openai:gpt-5.2', toolsets=[server])
```

### Server (expose agent as A2A/MCP)

```python
agent = Agent('openai:gpt-5.2', instructions='Be fun!')
app = agent.to_a2a()
# uvicorn agent_to_a2a:app --host 0.0.0.0 --port 8000
```

---

## 🧱 Toolsets

```python
from pydantic_ai import Agent, FunctionToolset

def my_tool():
    return "I'm a tool"

toolset = FunctionToolset(tools=[my_tool])
agent = Agent('openai:gpt-5.2', toolsets=[toolset])
```

### Toolset Composition

```python
from pydantic_ai import CombinedToolset

combined = CombinedToolset([ts1, ts2])
filtered = toolset.filtered(lambda ctx, td: td.name != 'danger')
prefixed = toolset.prefixed('v1_')
renamed = toolset.renamed({'new_name': 'old_name'})
prepared = toolset.prepared(fn)
approval_required = toolset.approval_required(fn)
```

---

## 🙋 Human-in-the-Loop (Deferred Tools)

```python
from pydantic_ai import Agent, DeferredToolRequests, DeferredToolResults, ToolDenied

agent = Agent('openai:gpt-5.2', output_type=[str, DeferredToolRequests])

@agent.tool_plain(requires_approval=True)
def delete_file(path: str) -> str:
    return f'File {path!r} deleted'

result = agent.run_sync('Delete __init__.py')
messages = result.all_messages()

results = DeferredToolResults()
for call in result.output.approvals:
    results.approvals[call.tool_call_id] = ToolDenied('Deletion not allowed')

final = agent.run_sync(message_history=messages, deferred_tool_results=results)
```

---

## 🧠 Thinking / Reasoning

```python
# Via model settings
agent = Agent('anthropic:claude-opus-4-6', model_settings={'thinking': 'high'})

# Via capability
from pydantic_ai.capabilities import Thinking
agent = Agent('anthropic:claude-opus-4-6', capabilities=[Thinking(effort='high')])
```

`thinking` accepts: `True`, `False`, `'minimal'`, `'low'`, `'medium'`, `'high'`, `'xhigh'`

---

## 🤝 Multi-Agent Patterns

### Agent Delegation (Tool-based)

```python
from pydantic_ai import Agent, RunContext

parent = Agent('openai:gpt-5.2')
child = Agent('google-gla:gemini-3-flash-preview', output_type=list[str])

@parent.tool
async def child_factory(ctx: RunContext[None], count: int) -> list[str]:
    r = await child.run(f'Generate {count} items.', usage=ctx.usage)
    return r.output
```

### Programmatic Hand-off
Run agents in sequence; application code decides which agent runs next.

---

## 📋 Agent Specs (YAML / JSON — No Code Required)

```yaml
model: anthropic:claude-opus-4-6
instructions: You are a helpful research assistant.
model_settings:
  max_tokens: 8192
capabilities:
  - WebSearch
  - Thinking:
      effort: high
```

```python
from pydantic_ai import Agent
agent = Agent.from_file('agent.yaml')
```

---

## 🏗️ Built-in Tools

```python
from pydantic_ai import Agent, WebSearchTool

agent = Agent('anthropic:claude-sonnet-4-6', builtin_tools=[WebSearchTool()])
result = agent.run_sync('What is the biggest news in AI this week?')
```

| Tool | Description |
|---|---|
| `WebSearchTool` | Web search |
| `CodeExecutionTool` | Secure code execution |
| `ImageGenerationTool` | Image generation |
| `WebFetchTool` | Fetch web pages |
| `MemoryTool` | Use model memory |
| `MCPServerTool` | Remote MCP servers |
| `FileSearchTool` | RAG over uploaded files |

---

## 🔍 Common Search Tools

```python
# DuckDuckGo
from pydantic_ai.common_tools.duckduckgo import duckduckgo_search_tool
agent = Agent('openai:gpt-5.2', tools=[duckduckgo_search_tool()])

# Tavily
from pydantic_ai.common_tools.tavily import tavily_search_tool
agent = Agent('openai:gpt-5.2', tools=[tavily_search_tool(api_key)])

# Exa
from pydantic_ai.common_tools.exa import ExaToolset
toolset = ExaToolset(api_key, num_results=5)
agent = Agent('openai:gpt-5.2', toolsets=[toolset])
```

---

## 🖼️ Multi-Modal Input (Images, Audio, Video, Docs)

```python
from pydantic_ai import Agent, ImageUrl, BinaryContent

agent = Agent(model='openai:gpt-5.2')

# URL-based
result = agent.run_sync(['What company is this?', ImageUrl(url='https://...')])

# Binary
result = agent.run_sync(['Describe this', BinaryContent(data=bytes_data, media_type='image/png')])
```

Also: `AudioUrl`, `VideoUrl`, `DocumentUrl`, `UploadedFile`

---

## 🌊 Embeddings

```python
from pydantic_ai import Embedder

embedder = Embedder('openai:text-embedding-3-small')

async def main():
    result = await embedder.embed_query('What is machine learning?')
    print(f'Embedding dimensions: {len(result.embeddings[0])}')  # 1536
```

**Supported**: OpenAI, Google, Cohere, VoyageAI, Bedrock, Sentence Transformers (local)

---

## 🧪 Testing

```python
from pydantic_ai.models.test import TestModel

test_model = TestModel()
agent = Agent(test_model)
result = agent.run_sync('hello')
print(test_model.last_model_request_parameters.function_tools)
```

---

## 📊 Pydantic Evals

```python
from pydantic_evals import Case, Dataset

dataset = Dataset(
    cases=[
        Case(name='capital_question', inputs='What is the capital of France?', expected_output='Paris'),
    ]
)
report = dataset.evaluate_sync(my_agent_function)
```

---

## 🕸️ Pydantic Graph

```python
from pydantic_graph import BaseNode, End, Graph, GraphRunContext
from dataclasses import dataclass

@dataclass
class DivisibleBy5(BaseNode[None, None, int]):
    foo: int

    async def run(self, ctx: GraphRunContext) -> 'Increment | End[int]':
        if self.foo % 5 == 0:
            return End(self.foo)
        return Increment(self.foo)

@dataclass
class Increment(BaseNode):
    foo: int

    async def run(self, ctx: GraphRunContext) -> DivisibleBy5:
        return DivisibleBy5(self.foo + 1)

fives_graph = Graph(nodes=[DivisibleBy5, Increment])
result = fives_graph.run_sync(DivisibleBy5(4))
print(result.output)  # 5
```

### Iterating Over a Graph

```python
async with my_graph.iter(StartNode(), state=state) as run:
    async for node in run:
        print('Node:', node)
print('Final output:', run.result.output)
```

### Generate Mermaid Diagram

```python
fives_graph.mermaid_code(start_node=DivisibleBy5)
```

---

## 🔄 HTTP Retries

```python
from httpx import AsyncClient, HTTPStatusError
from tenacity import retry_if_exception_type, stop_after_attempt, wait_exponential
from pydantic_ai.retries import AsyncTenacityTransport, RetryConfig, wait_retry_after

transport = AsyncTenacityTransport(
    config=RetryConfig(
        retry=retry_if_exception_type((HTTPStatusError, ConnectionError)),
        wait=wait_retry_after(fallback_strategy=wait_exponential(multiplier=1, max=60)),
        stop=stop_after_attempt(5),
        reraise=True
    ),
    validate_response=lambda r: r.raise_for_status()
)
client = AsyncClient(transport=transport)
```

Install: `pip install 'pydantic-ai-slim[retries]'`

---

## 🌐 Fallback & Concurrency Models

```python
from pydantic_ai.models.fallback import FallbackModel
from pydantic_ai import ConcurrencyLimitedModel

# Automatic fallback
fallback_model = FallbackModel('openai:gpt-5.2', 'anthropic:claude-sonnet-4-5')
agent = Agent(fallback_model)

# Concurrency limit
model = ConcurrencyLimitedModel('openai:gpt-4o', limiter=5)
agent = Agent(model)
```

---

## 🔑 Supported Models

| Provider | Example String |
|---|---|
| OpenAI | `openai:gpt-5.2` |
| Anthropic | `anthropic:claude-sonnet-4-6` |
| Google (GLA) | `google-gla:gemini-3-pro-preview` |
| Google (Vertex) | `google-vertex:gemini-3-pro-preview` |
| xAI | `xai:grok-4-1-fast-non-reasoning` |
| Bedrock | `bedrock:anthropic.claude-sonnet-4-5-20250929-v1:0` |
| Cerebras | `cerebras:llama-3.3-70b` |
| Cohere | `cohere:command-r7b-12-2024` |
| Groq | `groq:llama-3.3-70b-versatile` |
| Hugging Face | `huggingface:Qwen/Qwen3-235B-A22B` |
| Mistral | `mistral:mistral-large-latest` |
| OpenRouter | `openrouter:anthropic/claude-sonnet-4-5` |

**OpenAI-Compatible**: DeepSeek, Ollama, Azure AI Foundry, GitHub Models, Perplexity, Fireworks AI, Together AI, LiteLLM, and more.

```python
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

model = OpenAIChatModel(
    'model_name',
    provider=OpenAIProvider(base_url='https://...', api_key='your-key'),
)
```

---

## 🔭 Observability (Logfire)

```python
import logfire

logfire.configure()
logfire.instrument_pydantic_ai()
```

Or use the Pydantic AI Gateway (single key, multiple providers):

```python
agent = Agent('gateway/openai:gpt-5.2')
# Set PYDANTIC_AI_GATEWAY_API_KEY env var
```

---

## 🗃️ Prompt Caching (Anthropic)

```python
from pydantic_ai import Agent, CachePoint
from pydantic_ai.models.anthropic import AnthropicModelSettings

agent = Agent(
    'anthropic:claude-sonnet-4-6',
    model_settings=AnthropicModelSettings(
        anthropic_cache_instructions=True,
        anthropic_cache_tool_definitions='1h',
        anthropic_cache_messages=True,
    ),
)

# Manual cache points (max 4 per request — auto-managed)
result = agent.run_sync(['Long context...', CachePoint(), 'Question'])
```

---

## 🖥️ Web Chat UI

```python
agent = Agent('openai:gpt-5.2', instructions='You are a helpful assistant.')
app = agent.to_web()
# uvicorn my_module:app --host 127.0.0.1 --port 7932
```

Install: `pip install 'pydantic-ai-slim[web]'`

---

## 📚 Official Resources

- **Docs**: https://ai.pydantic.dev
- **GitHub**: https://github.com/pydantic/pydantic-ai
- **Full LLM Docs**: https://ai.pydantic.dev/llms-full.txt
- **Changelog**: https://ai.pydantic.dev/changelog/
- **Slack**: https://logfire.pydantic.dev/docs/join-slack/

---

**Pro Tip**: Reference this skill whenever building AI agents. Start with `Agent` + `deps_type` + `output_type` + `@agent.tool` — that covers 90% of use cases.

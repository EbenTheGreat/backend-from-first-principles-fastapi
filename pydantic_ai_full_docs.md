# Pydantic AI — Full Documentation

> Source: https://ai.pydantic.dev/llms-full.txt  
> Fetched: April 2026

---

## GenAI Agent Framework, the Pydantic way

Pydantic AI is a Python agent framework designed to make it less painful to build production grade
applications with Generative AI.

# Introduction

# Pydantic AI

*GenAI Agent Framework, the Pydantic way*

Pydantic AI is a Python agent framework designed to help you quickly, confidently, and painlessly build production grade applications and workflows with Generative AI.

FastAPI revolutionized web development by offering an innovative and ergonomic design, built on the foundation of [Pydantic Validation](https://docs.pydantic.dev) and modern Python features like type hints.

Yet despite virtually every Python agent framework and LLM library using Pydantic Validation, when we began to use LLMs in [Pydantic Logfire](https://pydantic.dev/logfire), we couldn't find anything that gave us the same feeling.

We built Pydantic AI with one simple aim: to bring that FastAPI feeling to GenAI app and agent development.

## Why use Pydantic AI

1. **Built by the Pydantic Team**: [Pydantic Validation](https://docs.pydantic.dev/latest/) is the validation layer of the OpenAI SDK, the Google ADK, the Anthropic SDK, LangChain, LlamaIndex, AutoGPT, Transformers, CrewAI, Instructor and many more. *Why use the derivative when you can go straight to the source?*
1. **Model-agnostic**: Supports virtually every [model](https://ai.pydantic.dev/models/overview/index.md) and provider: OpenAI, Anthropic, Gemini, DeepSeek, Grok, Cohere, Mistral, and Perplexity; Azure AI Foundry, Amazon Bedrock, Google Vertex AI, Ollama, LiteLLM, Groq, OpenRouter, Together AI, Fireworks AI, Cerebras, Hugging Face, GitHub, Heroku, Vercel, Nebius, OVHcloud, Alibaba Cloud, SambaNova, and Outlines. If your favorite model or provider is not listed, you can easily implement a [custom model](https://ai.pydantic.dev/models/overview/#custom-models).
1. **Seamless Observability**: Tightly [integrates](https://ai.pydantic.dev/logfire/index.md) with [Pydantic Logfire](https://pydantic.dev/logfire), our general-purpose OpenTelemetry observability platform, for real-time debugging, evals-based performance monitoring, and behavior, tracing, and cost tracking. If you already have an observability platform that supports OTel, you can [use that too](https://ai.pydantic.dev/logfire/#alternative-observability-backends).
1. **Fully Type-safe**: Designed to give your IDE or AI coding agent as much context as possible for auto-completion and [type checking](https://ai.pydantic.dev/agent/#static-type-checking), moving entire classes of errors from runtime to write-time for a bit of that Rust "if it compiles, it works" feel.
1. **Powerful Evals**: Enables you to systematically test and [evaluate](https://ai.pydantic.dev/evals/index.md) the performance and accuracy of the agentic systems you build, and monitor the performance over time in Pydantic Logfire.
1. **Extensible by Design**: Build agents from composable [capabilities](https://ai.pydantic.dev/capabilities/index.md) that bundle tools, hooks, instructions, and model settings into reusable units. Use built-in capabilities for [web search](https://ai.pydantic.dev/capabilities/#provider-adaptive-tools), [thinking](https://ai.pydantic.dev/capabilities/#thinking), and [MCP](https://ai.pydantic.dev/capabilities/#provider-adaptive-tools), build your own, or install [third-party capability packages](https://ai.pydantic.dev/extensibility/index.md). Define agents entirely in [YAML/JSON](https://ai.pydantic.dev/agent-spec/index.md) — no code required.
1. **MCP, A2A, and UI**: Integrates the [Model Context Protocol](https://ai.pydantic.dev/mcp/overview/index.md), [Agent2Agent](https://ai.pydantic.dev/a2a/index.md), and various [UI event stream](https://ai.pydantic.dev/ui/overview/index.md) standards to give your agent access to external tools and data, let it interoperate with other agents, and build interactive applications with streaming event-based communication.
1. **Human-in-the-Loop Tool Approval**: Easily lets you flag that certain tool calls [require approval](https://ai.pydantic.dev/deferred-tools/#human-in-the-loop-tool-approval) before they can proceed, possibly depending on tool call arguments, conversation history, or user preferences.
1. **Durable Execution**: Enables you to build [durable agents](https://ai.pydantic.dev/durable_execution/overview/index.md) that can preserve their progress across transient API failures and application errors or restarts, and handle long-running, asynchronous, and human-in-the-loop workflows with production-grade reliability.
1. **Streamed Outputs**: Provides the ability to [stream](https://ai.pydantic.dev/output/#streamed-results) structured output continuously, with immediate validation, ensuring real time access to generated data.
1. **Graph Support**: Provides a powerful way to define [graphs](https://ai.pydantic.dev/graph/index.md) using type hints, for use in complex applications where standard control flow can degrade to spaghetti code.

## Hello World Example

```python
from pydantic_ai import Agent

agent = Agent(
    'anthropic:claude-sonnet-4-6',
    instructions='Be concise, reply with one sentence.',
)

result = agent.run_sync('Where does "hello world" come from?')
print(result.output)
"""
The first known use of "hello, world" was in a 1974 textbook about the C programming language.
"""
```

## Tools & Dependency Injection Example

```python
from dataclasses import dataclass
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from bank_database import DatabaseConn

@dataclass
class SupportDependencies:
    customer_id: int
    db: DatabaseConn

class SupportOutput(BaseModel):
    support_advice: str = Field(description='Advice returned to the customer')
    block_card: bool = Field(description="Whether to block the customer's card")
    risk: int = Field(description='Risk level of query', ge=0, le=10)

support_agent = Agent(
    'openai:gpt-5.2',
    deps_type=SupportDependencies,
    output_type=SupportOutput,
    instructions=(
        'You are a support agent in our bank, give the '
        'customer support and judge the risk level of their query.'
    ),
)

@support_agent.instructions
async def add_customer_name(ctx: RunContext[SupportDependencies]) -> str:
    customer_name = await ctx.deps.db.customer_name(id=ctx.deps.customer_id)
    return f"The customer's name is {customer_name!r}"

@support_agent.tool
async def customer_balance(
    ctx: RunContext[SupportDependencies], include_pending: bool
) -> float:
    """Returns the customer's current account balance."""
    return await ctx.deps.db.customer_balance(
        id=ctx.deps.customer_id,
        include_pending=include_pending,
    )
```

## `llms.txt`

The Pydantic AI documentation is available in the [llms.txt](https://llmstxt.org/) format.

- [`llms.txt`](https://ai.pydantic.dev/llms.txt): brief description + links
- [`llms-full.txt`](https://ai.pydantic.dev/llms-full.txt): every link's content included

---

# Installation

```bash
pip install pydantic-ai
# or
uv add pydantic-ai
```

Requires Python 3.10+.

## Slim Install

```bash
pip install "pydantic-ai-slim[openai,google,logfire]"
uv add "pydantic-ai-slim[openai,google,logfire]"
```

Optional groups: `logfire`, `evals`, `openai`, `vertexai`, `google`, `anthropic`, `groq`, `mistral`, `cohere`, `bedrock`, `huggingface`, `duckduckgo`, `tavily`, `exa`, `cli`, `mcp`, `fastmcp`, `a2a`, `ui`, `ag-ui`, `dbos`, `prefect`

---

# Core Concepts

## Agents

Agents are Pydantic AI's primary interface for interacting with LLMs.

```python
from pydantic_ai import Agent, RunContext

roulette_agent = Agent(
    'openai:gpt-5.2',
    deps_type=int,
    output_type=bool,
    system_prompt=(
        'Use the `roulette_wheel` function to see if the '
        'customer has won based on the number they provide.'
    ),
)

@roulette_agent.tool
async def roulette_wheel(ctx: RunContext[int], square: int) -> str:
    """check if the square is a winner"""
    return 'winner' if square == ctx.deps else 'loser'

success_number = 18
result = roulette_agent.run_sync('Put my money on square eighteen', deps=success_number)
print(result.output)  # True
```

### Running Agents

Five ways to run an agent:
1. `agent.run()` — async, returns `RunResult`
2. `agent.run_sync()` — sync wrapper
3. `agent.run_stream()` — async context manager, returns `StreamedRunResult`
4. `agent.run_stream_events()` — async iterable of `AgentStreamEvent`s
5. `agent.iter()` — context manager returning `AgentRun` (async iterable over graph nodes)

### Instructions vs System Prompts

- **`instructions`**: Only the *current* agent's instructions are included per request (recommended)
- **`system_prompt`**: Retained across message history from all agents

### Reflection and Self-Correction

- Raise `ModelRetry` from tools/validators to ask the model to retry
- Default retry count: 1 (configurable per agent, tool, or output)

### Usage Limits

```python
from pydantic_ai import Agent, UsageLimitExceeded, UsageLimits

agent = Agent('anthropic:claude-sonnet-4-6')
result = agent.run_sync(
    'What is the capital of Italy?',
    usage_limits=UsageLimits(response_tokens_limit=10),
)
```

### Model Settings

```python
from pydantic_ai import Agent, ModelSettings

agent = Agent(model, model_settings=ModelSettings(temperature=0.5))
result = agent.run_sync('...', model_settings=ModelSettings(temperature=0.0))
```

---

## Dependencies

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
```

### Overriding Dependencies (Testing)

```python
with joke_agent.override(deps=test_deps):
    joke = await application_code('Tell me a joke.')
```

---

## Function Tools

```python
import random
from pydantic_ai import Agent, RunContext

agent = Agent(
    'google-gla:gemini-3-flash-preview',
    deps_type=str,
    instructions="You're a dice game...",
)

@agent.tool_plain
def roll_dice() -> str:
    """Roll a six-sided die and return the result."""
    return str(random.randint(1, 6))

@agent.tool
def get_player_name(ctx: RunContext[str]) -> str:
    """Get the player's name."""
    return ctx.deps
```

### Tool Schema

Function parameters are extracted from the function signature. Docstrings provide descriptions. Supports google, numpy, sphinx style docstrings.

---

## Output

### Structured Output

```python
from pydantic import BaseModel
from pydantic_ai import Agent

class CityLocation(BaseModel):
    city: str
    country: str

agent = Agent('google-gla:gemini-3-flash-preview', output_type=CityLocation)
result = agent.run_sync('Where were the olympics held in 2012?')
print(result.output)  # city='London' country='United Kingdom'
```

### Output Modes

- **Tool Output** (default): Uses tool calls — most compatible
- **Native Output**: Uses model's native JSON schema (not all models)
- **Prompted Output**: Injects schema into instructions — least reliable but most universal

### Output Functions

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

### Streamed Results

```python
async with agent.run_stream('Where does "hello world" come from?') as result:
    async for message in result.stream_text():
        print(message)
```

---

## Messages and Chat History

```python
from pydantic_ai import Agent

agent = Agent('openai:gpt-5.2', instructions='Be a helpful assistant.')

result1 = agent.run_sync('Tell me a joke.')
result2 = agent.run_sync('Explain?', message_history=result1.new_messages())
```

### Storing Messages (JSON)

```python
from pydantic_core import to_jsonable_python
from pydantic_ai import Agent, ModelMessagesTypeAdapter

agent = Agent('openai:gpt-5.2')
result1 = agent.run_sync('Tell me a joke.')
history_step_1 = result1.all_messages()
as_python_objects = to_jsonable_python(history_step_1)
same_history = ModelMessagesTypeAdapter.validate_python(as_python_objects)
```

### History Processors

```python
def filter_responses(messages: list[ModelMessage]) -> list[ModelMessage]:
    return [msg for msg in messages if isinstance(msg, ModelRequest)]

agent = Agent('openai:gpt-5.2', history_processors=[filter_responses])
```

---

## Capabilities

A capability bundles tools, lifecycle hooks, instructions, and model settings into a reusable unit.

```python
from pydantic_ai import Agent
from pydantic_ai.capabilities import Thinking, WebSearch

agent = Agent(
    'anthropic:claude-opus-4-6',
    capabilities=[Thinking(effort='high'), WebSearch()],
)
```

### Built-in Capabilities

| Capability       | What it provides                          |
|------------------|-------------------------------------------|
| Thinking         | Model thinking/reasoning                  |
| Hooks            | Decorator-based lifecycle hook registration |
| WebSearch        | Web search (builtin or local fallback)    |
| WebFetch         | URL fetching                              |
| ImageGeneration  | Image generation                          |
| MCP              | MCP server integration                    |
| PrepareTools     | Filter/modify tool definitions per step   |
| PrefixTools      | Prefix tool names                         |
| BuiltinTool      | Register a builtin tool                   |
| Toolset          | Wraps an AbstractToolset                  |
| HistoryProcessor | Wraps a history processor                 |

### Building Custom Capabilities

```python
from dataclasses import dataclass
from typing import Any
from pydantic_ai import Agent
from pydantic_ai.capabilities import AbstractCapability

@dataclass
class MathTools(AbstractCapability[Any]):
    """Provides basic math operations."""

    def get_toolset(self) -> AgentToolset[Any] | None:
        return math_toolset

agent = Agent('openai:gpt-5.2', capabilities=[MathTools()])
```

### Lifecycle Hooks

Hooks fire at five lifecycle points:
- **Run hooks**: `before_run`, `after_run`, `wrap_run`, `on_run_error`
- **Node hooks**: `before_node_run`, `after_node_run`, `wrap_node_run`, `on_node_run_error`
- **Model request hooks**: `before_model_request`, `after_model_request`, `wrap_model_request`, `on_model_request_error`
- **Tool validation hooks**: `before_tool_validate`, `after_tool_validate`, `wrap_tool_validate`, `on_tool_validate_error`
- **Tool execution hooks**: `before_tool_execute`, `after_tool_execute`, `wrap_tool_execute`, `on_tool_execute_error`

---

## Hooks

```python
from pydantic_ai import Agent, ModelRequestContext, RunContext
from pydantic_ai.capabilities import Hooks

hooks = Hooks()

@hooks.on.before_model_request
async def log_request(ctx: RunContext[None], request_context: ModelRequestContext) -> ModelRequestContext:
    print(f'Sending {len(request_context.messages)} messages to the model')
    return request_context

agent = Agent('test', capabilities=[hooks])
```

---

## MCP (Model Context Protocol)

### Client

```python
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStdio

server = MCPServerStdio('python', args=['-m', 'mcp_server'])
agent = Agent('openai:gpt-5.2', toolsets=[server])
```

### Server

```python
from pydantic_ai import Agent
agent = Agent('openai:gpt-5.2', instructions='Be fun!')
app = agent.to_a2a()
```

---

## Built-in Tools

Native tools provided by LLM providers:

- **WebSearchTool**: Web search
- **CodeExecutionTool**: Execute code securely
- **ImageGenerationTool**: Generate images
- **WebFetchTool**: Fetch web pages
- **MemoryTool**: Use memory
- **MCPServerTool**: Remote MCP servers via provider
- **FileSearchTool**: RAG over uploaded files

```python
from pydantic_ai import Agent, WebSearchTool

agent = Agent('anthropic:claude-sonnet-4-6', builtin_tools=[WebSearchTool()])
result = agent.run_sync('Give me a sentence with the biggest news in AI this week.')
```

---

## Toolsets

```python
from pydantic_ai import Agent, FunctionToolset
from pydantic_ai.models.test import TestModel

def my_tool():
    return "I'm a tool"

toolset = FunctionToolset(tools=[my_tool])
agent = Agent(TestModel(), toolsets=[toolset])
```

### Toolset Composition

- `CombinedToolset([ts1, ts2])` — combine multiple toolsets
- `toolset.filtered(lambda ctx, td: ...)` — filter tools
- `toolset.prefixed('prefix')` — prefix tool names
- `toolset.renamed({'new': 'old'})` — rename tools
- `toolset.prepared(fn)` — modify tool definitions per step
- `toolset.approval_required(fn)` — require human approval
- `WrapperToolset` — subclass to intercept tool execution

---

## Deferred Tools

### Human-in-the-Loop Approval

```python
from pydantic_ai import Agent, ApprovalRequired, DeferredToolRequests, DeferredToolResults, RunContext, ToolDenied

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

## Thinking / Reasoning

```python
from pydantic_ai import Agent

agent = Agent('anthropic:claude-opus-4-6', model_settings={'thinking': 'high'})
```

Or via capability:

```python
from pydantic_ai.capabilities import Thinking
agent = Agent('anthropic:claude-opus-4-6', capabilities=[Thinking(effort='high')])
```

`thinking` accepts: `True`, `False`, `'minimal'`, `'low'`, `'medium'`, `'high'`, `'xhigh'`

---

## Agent Specs (YAML/JSON)

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

## Multi-Agent Applications

### Agent Delegation

```python
from pydantic_ai import Agent, RunContext

parent_agent = Agent('openai:gpt-5.2', instructions='...')
child_agent = Agent('google-gla:gemini-3-flash-preview', output_type=list[str])

@parent_agent.tool
async def child_factory(ctx: RunContext[None], count: int) -> list[str]:
    r = await child_agent.run(f'Generate {count} items.', usage=ctx.usage)
    return r.output
```

### Programmatic Hand-off

Run agents in succession, application code decides which agent runs next.

---

## Embeddings

```python
from pydantic_ai import Embedder

embedder = Embedder('openai:text-embedding-3-small')

async def main():
    result = await embedder.embed_query('What is machine learning?')
    print(f'Embedding dimensions: {len(result.embeddings[0])}')  # 1536
```

Supported providers: OpenAI, Google, Cohere, VoyageAI, Bedrock, Sentence Transformers (local)

---

## Testing

```python
from pydantic_ai.models.test import TestModel

test_model = TestModel()
agent = Agent(test_model)
result = agent.run_sync('hello')
print(test_model.last_model_request_parameters.function_tools)
```

---

# Models & Providers

## Supported Models

| Provider | Example |
|----------|---------|
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

## OpenAI-Compatible Providers

DeepSeek, Alibaba (DashScope), Ollama, Azure AI Foundry, Vercel AI Gateway, MoonshotAI, GitHub Models, Perplexity, Fireworks AI, Together AI, Heroku AI, LiteLLM, Nebius AI Studio, OVHcloud, SambaNova

```python
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

model = OpenAIChatModel(
    'model_name',
    provider=OpenAIProvider(base_url='https://...', api_key='your-key'),
)
agent = Agent(model)
```

## Fallback Model

```python
from pydantic_ai.models.fallback import FallbackModel

fallback_model = FallbackModel(
    'openai:gpt-5.2',
    'anthropic:claude-sonnet-4-5',
)
agent = Agent(fallback_model)
```

## Concurrency Limiting

```python
from pydantic_ai import Agent, ConcurrencyLimitedModel

model = ConcurrencyLimitedModel('openai:gpt-4o', limiter=5)
agent = Agent(model)
```

---

# Pydantic AI Gateway

Unified interface for accessing multiple AI providers with a single key via Pydantic Logfire.

```python
from pydantic_ai import Agent

agent = Agent('gateway/openai:gpt-5.2')
result = agent.run_sync('Where does "hello world" come from?')
```

Set `PYDANTIC_AI_GATEWAY_API_KEY` env var. Sign up at [logfire.pydantic.dev](https://logfire.pydantic.dev/).

---

# Integrations

## Pydantic Logfire

```python
import logfire

logfire.configure()
logfire.instrument_pydantic_ai()
```

## Durable Execution

- Temporal
- DBOS
- Prefect

## UI Event Streams

- AG-UI
- Vercel AI

## Agent2Agent (A2A) Protocol

```python
from pydantic_ai import Agent

agent = Agent('openai:gpt-5.2', instructions='Be fun!')
app = agent.to_a2a()
# uvicorn agent_to_a2a:app --host 0.0.0.0 --port 8000
```

---

# Pydantic Evals

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

# Pydantic Graph

```python
from pydantic_graph import BaseNode, End, Graph, GraphRunContext
from dataclasses import dataclass

@dataclass
class DivisibleBy5(BaseNode[None, None, int]):
    foo: int

    async def run(self, ctx: GraphRunContext) -> 'Increment | End[int]':
        if self.foo % 5 == 0:
            return End(self.foo)
        else:
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

### Graph Components

- **`GraphRunContext`**: Context for the run, holds state and deps
- **`End`**: Return to indicate the graph run should end
- **`BaseNode`**: Base class for nodes (usually dataclasses)
- **`Graph`**: The execution graph itself

### Stateful Graphs

State is a dataclass/Pydantic model passed through nodes.

### Iterating Over a Graph

```python
async with my_graph.iter(StartNode(), state=state) as run:
    async for node in run:
        print('Node:', node)
print('Final output:', run.result.output)
```

### Mermaid Diagrams

```python
fives_graph.mermaid_code(start_node=DivisibleBy5)
```

---

# HTTP Request Retries

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

# Common Tools

## DuckDuckGo Search

```python
from pydantic_ai.common_tools.duckduckgo import duckduckgo_search_tool
agent = Agent('openai:gpt-5.2', tools=[duckduckgo_search_tool()])
```

## Tavily Search

```python
from pydantic_ai.common_tools.tavily import tavily_search_tool
agent = Agent('openai:gpt-5.2', tools=[tavily_search_tool(api_key)])
```

## Exa Search

```python
from pydantic_ai.common_tools.exa import ExaToolset
toolset = ExaToolset(api_key, num_results=5)
agent = Agent('openai:gpt-5.2', toolsets=[toolset])
```

---

# Image, Audio, Video & Document Input

```python
from pydantic_ai import Agent, ImageUrl, BinaryContent

agent = Agent(model='openai:gpt-5.2')

# URL-based image
result = agent.run_sync(['What company is this logo from?', ImageUrl(url='https://...')])

# Binary image
result = agent.run_sync(['Describe this image', BinaryContent(data=bytes_data, media_type='image/png')])
```

Also supported: `AudioUrl`, `VideoUrl`, `DocumentUrl`, `UploadedFile`

---

# Prompt Caching (Anthropic)

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

# Or with manual CachePoint markers
result = agent.run_sync([
    'Long context...',
    CachePoint(),
    'Question'
])
```

Max 4 cache points per request. Pydantic AI manages this limit automatically.

---

# Web Chat UI

```python
from pydantic_ai import Agent

agent = Agent('openai:gpt-5.2', instructions='You are a helpful assistant.')
app = agent.to_web()
# uvicorn my_module:app --host 127.0.0.1 --port 7932
```

Install: `pip install 'pydantic-ai-slim[web]'`

---

# Advanced Tool Features

## Dynamic Tools (prepare)

```python
async def only_if_42(ctx: RunContext[int], tool_def: ToolDefinition) -> ToolDefinition | None:
    if ctx.deps == 42:
        return tool_def

@agent.tool(prepare=only_if_42)
def hitchhiker(ctx: RunContext[int], answer: str) -> str:
    return f'{ctx.deps} {answer}'
```

## Tool Timeout

```python
agent = Agent('test', tool_timeout=30)

@agent.tool_plain(timeout=5)
async def fast_tool() -> str:
    return 'Done'
```

## Custom Tool Schema

```python
tool = Tool.from_schema(
    function=foobar,
    name='sum',
    description='Sum two numbers.',
    json_schema={...},
    takes_ctx=False,
)
```

## Parallel Tool Calls

Pydantic AI schedules parallel tool calls concurrently using `asyncio.create_task`. Use `sequential=True` for serial execution.

---

# Extensibility

## Custom Capabilities

```python
from pydantic_ai.capabilities import AbstractCapability

@dataclass
class RateLimit(AbstractCapability[Any]):
    rpm: int = 60

agent = Agent.from_spec(
    AgentSpec(model='test', capabilities=[{'RateLimit': {'rpm': 30}}]),
    custom_capability_types=[RateLimit],
)
```

## Custom Models

Subclass `Model` (and `StreamedResponse` for streaming) from `pydantic_ai.models.base`.

## Third-party Tools

- **LangChain**: `tool_from_langchain(search)`, `LangChainToolset(toolkit.get_tools())`
- **ACI.dev**: `tool_from_aci('TAVILY__SEARCH', ...)`, `ACIToolset([...], ...)`

---

# Contributing

See [contributing guidelines](https://ai.pydantic.dev/contributing/) on GitHub.

## Project

- [Upgrade Guide / Changelog](https://ai.pydantic.dev/changelog/)
- [Version Policy](https://ai.pydantic.dev/version-policy/)
- [GitHub](https://github.com/pydantic/pydantic-ai)
- [Slack](https://logfire.pydantic.dev/docs/join-slack/)

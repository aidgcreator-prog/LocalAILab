# Graph Report - F:\LocalAiLab\smolagent_rag\old_files\smolagent\smolagents  (2026-07-24)

## Corpus Check
- 177 files · ~178,791 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2337 nodes · 6407 edges · 159 communities (93 shown, 66 thin omitted)
- Extraction: 63% EXTRACTED · 37% INFERRED · 0% AMBIGUOUS · INFERRED: 2365 edges (avg confidence: 0.54)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Community 0
- Community 1
- Community 2
- Community 3
- Community 4
- Community 5
- Community 6
- Community 7
- Community 8
- Community 9
- Community 10
- Community 11
- Community 12
- Community 13
- Community 14
- Community 15
- Community 16
- Community 17
- Community 18
- Community 19
- Community 20
- Community 21
- Community 22
- Community 23
- Community 24
- Community 25
- Community 26
- Community 27
- Community 28
- Community 29
- Community 30
- Community 31
- Community 32
- Community 33
- Community 34
- Community 35
- Community 36
- Community 37
- Community 38
- Community 39
- Community 40
- Community 41
- Community 42
- Community 43
- Community 44
- Community 45
- Community 46
- Community 47
- Community 48
- Community 49
- Community 50
- Community 51
- Community 52
- Community 53
- Community 54
- Community 55
- Community 56
- Community 57
- Community 58
- Community 59
- Community 60
- Community 61
- Community 62
- Community 63
- Community 64
- Community 65
- Community 67
- Community 68
- Community 69
- Community 70
- Community 71
- Community 72
- Community 73
- Community 74
- Community 75
- Community 76
- Community 77
- Community 78
- Community 79
- Community 80
- Community 81
- Community 82
- Community 83
- Community 84
- Community 85
- Community 86
- Community 87
- Community 88
- Community 89
- Community 90
- Community 91
- Community 92
- Community 93
- Community 94
- Community 95
- Community 96
- Community 97
- Community 98
- Community 99
- Community 100
- Community 101
- Community 102
- Community 103
- Community 104
- Community 105
- Community 106
- Community 107
- Community 108
- Community 109
- Community 110
- Community 111
- Community 112
- Community 114
- Community 115
- Community 116
- Community 117
- Community 118
- Community 119
- Community 120
- Community 125
- Community 127
- Community 128
- Community 129
- Community 130
- Community 131
- Community 132
- Community 133
- Community 134
- Community 135
- Community 136
- Community 137
- Community 138
- Community 139
- Community 140
- Community 141
- Community 142
- Community 143
- Community 144
- Community 145
- Community 146
- Community 147
- Community 148
- Community 149
- Community 150
- Community 151
- Community 152
- Community 153
- Community 154
- Community 155
- Community 156
- Community 157

## God Nodes (most connected - your core abstractions)
1. `Tool` - 180 edges
2. `ChatMessage` - 154 edges
3. `CodeAgent` - 128 edges
4. `TokenUsage` - 118 edges
5. `evaluate_python_code()` - 116 edges
6. `TestEvaluatePythonCode` - 109 edges
7. `MultiStepAgent` - 100 edges
8. `ToolCallingAgent` - 99 edges
9. `ActionStep` - 96 edges
10. `FinalAnswerTool` - 88 edges

## Surprising Connections (you probably didn't know these)
- `serialize_agent_error()` --indirect_call--> `AgentError`  [INFERRED]
  examples/open_deep_research/scripts/run_agents.py → src/smolagents/utils.py
- `serialize_agent_error()` --indirect_call--> `AgentError`  [INFERRED]
  examples/smolagents_benchmark/run.py → src/smolagents/utils.py
- `get_agent()` --calls--> `CodeAgent`  [INFERRED]
  examples/async_agent/main.py → src/smolagents/agents.py
- `get_agent()` --calls--> `InferenceClientModel`  [INFERRED]
  examples/async_agent/main.py → src/smolagents/models.py
- `create_agent()` --calls--> `CodeAgent`  [INFERRED]
  examples/open_deep_research/run.py → src/smolagents/agents.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **CodeAgent Architecture** — readme_codeagent, docs_source_en_conceptual_guides_react_react_framework, docs_source_en_conceptual_guides_react_multistepagent, docs_source_en_guided_tour_final_answer, docs_source_en_guided_tour_tool [INFERRED 0.85]
- **Project Governance** — license_apache_2_0, code_of_conduct_contributor_covenant, contributing_contribution_guide, security_security_policy [EXTRACTED 1.00]
- **LLM Model Ecosystem** — readme_smolagents, readme_inferenceclientmodel, readme_litellmmodel, readme_model_agnostic [INFERRED 0.85]
- **Agent Execution Cycle (Plan-Act-Observe)** — old_files_smolagent_smolagents_docs_source_en_examples_plan_customization_plan_interruption, old_files_smolagent_smolagents_docs_source_en_examples_plan_customization_step_callback, old_files_smolagent_smolagents_docs_source_en_tutorials_memory_agent_memory [INFERRED 0.85]
- **Sandboxed Code Execution Ecosystem** — old_files_smolagent_smolagents_docs_source_en_tutorials_secure_code_execution_local_python_executor, old_files_smolagent_smolagents_docs_source_en_tutorials_secure_code_execution_sandbox_approach_1, old_files_smolagent_smolagents_docs_source_en_tutorials_secure_code_execution_sandbox_approach_2, old_files_smolagent_smolagents_docs_source_en_tutorials_secure_code_execution_code_vs_json_rationale [INFERRED 0.85]
- **Model Integration Hierarchy** — old_files_smolagent_smolagents_docs_source_en_reference_models_model_base, old_files_smolagent_smolagents_docs_source_en_reference_models_api_model, old_files_smolagent_smolagents_docs_source_en_reference_models_inference_client_model, old_files_smolagent_smolagents_docs_source_en_reference_models_litellm_model, old_files_smolagent_smolagents_docs_source_en_reference_models_openai_model, old_files_smolagent_smolagents_docs_source_en_reference_models_transformers_model [INFERRED 0.85]
- **Multi-step agent loop** — old_files_smolagent_smolagents_docs_source_hi_conceptual_guides_intro_agents_multi_step_agent, old_files_smolagent_smolagents_docs_source_hi_conceptual_guides_intro_agents_tool_calling, old_files_smolagent_smolagents_docs_source_hi_conceptual_guides_intro_agents_memory, old_files_smolagent_smolagents_docs_source_hi_conceptual_guides_intro_agents_parser, old_files_smolagent_smolagents_docs_source_hi_conceptual_guides_intro_agents_system_prompt [EXTRACTED 1.00]
- **Agent tool system** — old_files_smolagent_smolagents_docs_source_hi_reference_tools_tool, old_files_smolagent_smolagents_docs_source_hi_reference_tools_tool_decorator, old_files_smolagent_smolagents_docs_source_hi_reference_tools_load_tool, old_files_smolagent_smolagents_docs_source_hi_reference_tools_tool_collection, old_files_smolagent_smolagents_docs_source_hi_tutorials_tools_tool_as_class, old_files_smolagent_smolagents_docs_source_hi_tutorials_tools_tool_from_langchain, old_files_smolagent_smolagents_docs_source_hi_tutorials_tools_tool_from_space, old_files_smolagent_smolagents_docs_source_hi_tutorials_tools_mcp_servers [EXTRACTED 1.00]
- **Model integration ecosystem** — old_files_smolagent_smolagents_docs_source_hi_guided_tour_transformers_model, old_files_smolagent_smolagents_docs_source_hi_guided_tour_inference_client_model, old_files_smolagent_smolagents_docs_source_hi_guided_tour_lite_llm_model, old_files_smolagent_smolagents_docs_source_hi_reference_agents_open_ai_model, old_files_smolagent_smolagents_docs_source_ko_examples_using_different_models_vllm_model, old_files_smolagent_smolagents_docs_source_ko_examples_using_different_models_mlx_model, old_files_smolagent_smolagents_docs_source_ko_examples_using_different_models_lite_llm_router_model, old_files_smolagent_smolagents_docs_source_ko_examples_using_different_models_azure_open_ai_model, old_files_smolagent_smolagents_docs_source_ko_examples_using_different_models_amazon_bedrock_model [EXTRACTED 1.00]
- **Agent Class Hierarchy** — docs_source_ko_reference_agents_multistepagent, docs_source_ko_guided_tour_codeagent, docs_source_ko_guided_tour_toolcallingagent [EXTRACTED 1.00]
- **Model Class Hierarchy** — docs_source_ko_reference_models_model, docs_source_ko_reference_models_apimodel, docs_source_ko_guided_tour_inferenceclientmodel, docs_source_ko_reference_models_transformersmodel, docs_source_ko_reference_models_litellmmodel, docs_source_ko_reference_models_azureopenaimodel, docs_source_ko_reference_models_amazonbedrockmodel, docs_source_ko_reference_models_mlxmodel, docs_source_ko_reference_models_vllmmodel [EXTRACTED 1.00]
- **Observability Stack** — docs_source_ko_tutorials_inspect_runs_opentelemetry, docs_source_ko_tutorials_inspect_runs_smolagentsinstrumentor, docs_source_ko_tutorials_inspect_runs_arizephoenix, docs_source_ko_tutorials_inspect_runs_langfuse [EXTRACTED 1.00]
- **Agent class hierarchy (Agent -> MultiStepAgent -> CodeAgent/ToolCallingAgent)** — old_files_smolagent_smolagents_docs_source_zh_reference_agents_agent, old_files_smolagent_smolagents_docs_source_zh_reference_agents_multistepagent, old_files_smolagent_smolagents_docs_source_zh_guided_tour_codeagent, old_files_smolagent_smolagents_docs_source_zh_guided_tour_toolcallingagent [EXTRACTED 1.00]
- **Model provider ecosystem (TransformersModel, InferenceClientModel, LiteLLMModel, OpenAIModel, AzureOpenAIModel, MLXModel)** — old_files_smolagent_smolagents_docs_source_zh_guided_tour_transformersmodel, old_files_smolagent_smolagents_docs_source_zh_guided_tour_inferenceclientmodel, old_files_smolagent_smolagents_docs_source_zh_guided_tour_litellmmodel, old_files_smolagent_smolagents_docs_source_zh_reference_models_openaimodel, old_files_smolagent_smolagents_docs_source_zh_guided_tour_azureopenaimodel, old_files_smolagent_smolagents_docs_source_zh_guided_tour_mlxmodel [EXTRACTED 1.00]
- **Telemetry/observability ecosystem (OpenTelemetry + SmolagentsInstrumentor + Phoenix/Langfuse)** — old_files_smolagent_smolagents_docs_source_zh_tutorials_inspect_runs_opentelemetry, old_files_smolagent_smolagents_docs_source_zh_tutorials_inspect_runs_smolagentsinstrumentor, old_files_smolagent_smolagents_docs_source_zh_tutorials_inspect_runs_arize_ai_phoenix, old_files_smolagent_smolagents_docs_source_zh_tutorials_inspect_runs_langfuse [EXTRACTED 1.00]

## Communities (159 total, 66 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.04
Nodes (17): evaluate_python_code(), Evaluate a python expression using the content of the variables stored in a stat, add_two(), Test that __exit__ is called on the context manager, not the __enter__ return va, Test that __exit__ is called on context managers used without 'as' clause., Test that __exit__ returning True suppresses the exception., Test that __exit__ returning False re-raises the original exception., Test that when the inner CM suppresses, the outer CM's __exit__ gets (None, None (+9 more)

### Community 1 - "Community 1"
Cohesion: 0.05
Nodes (48): Console, FinalAnswerTool, Any, Search Wikipedia and return the summary or full text of the requested article, a, WikipediaSearchTool, CodeOutput, DockerExecutor, E2BExecutor (+40 more)

### Community 2 - "Community 2"
Cohesion: 0.09
Nodes (51): AgentImage, AgentText, Text type returned by the agent. Behaves as a string., Image type returned by the agent. Behaves as a PIL.Image.Image., PlanningPromptTemplate, This agent uses JSON-like tool calls, using method `model.get_tool_call` to leve, Prompt templates for the planning step.      Args:         plan (`str`): Init, Perform one step in the ReAct framework: the agent thinks, acts, and observes th (+43 more)

### Community 3 - "Community 3"
Cohesion: 0.04
Nodes (48): Any, Convert JSON-safe format back to Python objects.          Args:             o, Serialize object to string.          Args:             obj: Object to seriali, Deserialize string with format detection.          Args:             data: Se, Test datetime module types., Test Decimal and Path., Test deeply nested structures., Test edge cases and boundary conditions. (+40 more)

### Community 4 - "Community 4"
Cohesion: 0.06
Nodes (40): ActionOutput, populate_template(), Process tool calls from the model output and update agent memory.          Arg, Perform one step in the ReAct framework: the agent thinks, acts, and observes th, Run the agent for the given task.          Args:             task (`str`): Ta, Reads past llm_outputs, actions, and observations or errors from the memory into, Perform one step in the ReAct framework: the agent thinks, acts, and observes th, Perform one step in the ReAct framework: the agent thinks, acts, and observes th (+32 more)

### Community 5 - "Community 5"
Cohesion: 0.05
Nodes (32): Create agent from a dictionary representation.          Args:             age, The SmolAgents tools available from the MCP server.          Note: for now, th, Apply rate limiting before making API calls., Overrides the base method to handle Bedrock-specific configurations., Process the input messages and return the model's response.          Parameter, Model to use [vLLM](https://docs.vllm.ai/) for fast LLM inference and serving., Remove content after any stop sequence is encountered.      Some providers may, remove_content_after_stop_sequences() (+24 more)

### Community 6 - "Community 6"
Cohesion: 0.06
Nodes (66): AnnAssign, Assert, Assign, Attribute, AugAssign, BinOp, Call, ClassDef (+58 more)

### Community 7 - "Community 7"
Cohesion: 0.08
Nodes (33): AmazonBedrockModel, ApiModel, AzureOpenAIModel, ChatMessageToolCallStreamDelta, LiteLLMModel, LiteLLMRouterModel, MLXModel, OpenAIModel (+25 more)

### Community 8 - "Community 8"
Cohesion: 0.06
Nodes (42): interactive_mode(), load_model(), main(), parse_arguments(), Run the CLI in interactive mode, run_smolagent(), Creates a [`Tool`] from a Space given its id on the Hub.          Args:, close_popups() (+34 more)

### Community 9 - "Community 9"
Cohesion: 0.06
Nodes (36): _clean_model_output(), _format_code_content(), get_step_footnote_content(), GradioUI, _process_action_step(), _process_final_answer_step(), _process_planning_step(), pull_messages_from_step() (+28 more)

### Community 10 - "Community 10"
Cohesion: 0.07
Nodes (31): DocumentConverter, DocumentConverterResult, DocxConverter, HtmlConverter, ImageConverter, MediaConverter, Mp3Converter, PdfConverter (+23 more)

### Community 11 - "Community 11"
Cohesion: 0.06
Nodes (34): AST, add_description(), load_tool(), ABC, Main function to quickly load a tool from the Hub.      <Tip warning={true}>, A decorator that adds a description to a function., validate_after_init(), create_agent_gradio_app_template() (+26 more)

### Community 12 - "Community 12"
Cohesion: 0.08
Nodes (28): IntEnum, FinalAnswerPromptTemplate, ManagedAgentPromptTemplate, MultiStepAgent, PromptTemplates, ABC, # TODO: tool_call_result naming could allow for different names of same type, Prompt templates for the managed agent.      Args:         task (`str`): Task (+20 more)

### Community 13 - "Community 13"
Cohesion: 0.12
Nodes (11): CodeAgent, In this agent, the tool calls will be formulated by the LLM in code format, then, PythonInterpreterTool, FakeCodeModel, FakeCodeModelFunctionDef, FakeCodeModelImport, FakeCodeModelNoReturn, Test that final answer checks can access agent properties. (+3 more)

### Community 14 - "Community 14"
Cohesion: 0.09
Nodes (18): Enum, ChatMessageToolCall, ChatMessageToolCallFunction, MessageRole, str, AgentLogger, agent_logger(), FakeToolCallModelVL (+10 more)

### Community 15 - "Community 15"
Cohesion: 0.13
Nodes (26): Dataset, create_agent(), answer_single_question(), append_answer(), create_agent_team(), get_examples_to_answer(), load_gaia_dataset(), main() (+18 more)

### Community 16 - "Community 16"
Cohesion: 0.07
Nodes (12): launch_gradio_demo(), Launches a gradio demo for a tool. The corresponding tool class needs to properl, DefaultToolTests, test_wikipedia_search(), TestFinalAnswerTool, TestDuckDuckGoSearchTool, # TODO: Fix this test case: property is marked as nullable because it has a defa, # TODO: Fix this test case: property is marked as nullable because it can be Non (+4 more)

### Community 17 - "Community 17"
Cohesion: 0.06
Nodes (24): Extract method body without the def line and dedent it., Returns the SafeSerializer class definition as string for injection into sandbox, Generate deserializer function for remote execution with setting baked in., JSON-based serializer with type markers for safe serialization.      Supports:, Get optional type class with caching to avoid repeated imports., Convert Python objects to JSON-serializable format with type markers., SafeSerializer, Test that legacy pickle data can still be read when explicitly allowed. (+16 more)

### Community 18 - "Community 18"
Cohesion: 0.08
Nodes (20): AgentAudio, handle_agent_input_types(), handle_agent_output_types(), Any, str, Audio type returned by the agent., Returns the "raw" version of that object. It is a `torch.Tensor` object., PreTool (+12 more)

### Community 19 - "Community 19"
Cohesion: 0.08
Nodes (18): PythonExecutor, BlaxelExecutor, _create_kernel_http(), Delete sandbox using Blaxel's sync API and wait for completion., Sync wrapper to clean up sandbox and resources., Ensure cleanup on deletion., Ensure cleanup on deletion., Create kernel using http. (+10 more)

### Community 20 - "Community 20"
Cohesion: 0.09
Nodes (5): LocalPythonExecutor, Executor of Python code in a local environment.      This executor evaluates P, Check that all authorized imports are installed on the system.          Handle, TestLocalPythonExecutor, TestLocalPythonExecutorSecurity

### Community 21 - "Community 21"
Cohesion: 0.08
Nodes (12): Any, Searches for the query from the current viewport forward, looping back to the st, Scroll to the next viewport that matches the query, Search for matches between the starting viewport looping when reaching the end., Update the address, visit the page, and return the content of the viewport., (In preview) An extremely simple text-based web browser comparable to Lynx. Suit, Return the address of the current page., Return the content of the current viewport. (+4 more)

### Community 22 - "Community 22"
Cohesion: 0.08
Nodes (18): GoogleSearchTool, Validates that a Tool class follows the proper patterns:     0. Any argument of, validate_tool_attributes(), InvalidToolComplexAttrs, InvalidToolName, InvalidToolNonLiteralDefaultParam, InvalidToolRequiredParams, InvalidToolUndefinedNames (+10 more)

### Community 23 - "Community 23"
Cohesion: 0.07
Nodes (34): CodeAgent, GradioUI, InferenceClientModel, ManagedAgent, ToolCallingAgent, WebSearchTool, DockerExecutor, E2BExecutor (+26 more)

### Community 24 - "Community 24"
Cohesion: 0.07
Nodes (21): Deserialize final answer with format detection.          Accepts explicit pref, Exception, Raised when a type cannot be safely serialized., SerializationError, Test that defaults are secure., Verify dumps defaults to safe mode., Verify loads defaults to safe mode., Test error handling and malformed data. (+13 more)

### Community 25 - "Community 25"
Cohesion: 0.08
Nodes (12): MethodChecker, Track variables in list comprehensions, Track variables in dictionary comprehensions, Track variables in set comprehensions, Checks that a method     - only uses defined names     - contains no local imp, Track class definitions, Collect function arguments, Track aliases in 'with' statements (the 'y' in 'with X as y') (+4 more)

### Community 26 - "Community 26"
Cohesion: 0.08
Nodes (15): Any, Path, Loads an agent defined on the Hub.          <Tip warning={true}>          Lo, Loads an agent from a local folder.          Args:             folder (`str`, Upload the agent to the Hub.          Parameters:             repo_id (`str`), Replace string values in arguments with their corresponding state values if they, Execute a tool or managed agent with the provided arguments.          The argu, Convert the agent to a dictionary representation.          Returns: (+7 more)

### Community 27 - "Community 27"
Cohesion: 0.11
Nodes (14): get_json_schema(), This function generates a JSON schema for a given function, based on its docstri, Test that property types are correctly mapped., Test that basic schema structure is correct., Test schema generation for complex types., Test schema generation for optional arguments., Test schema generation for enum choices in docstring., Test schema generation for union types. (+6 more)

### Community 28 - "Community 28"
Cohesion: 0.08
Nodes (10): evaluate_subscript(), get_iterable(), InterpreterError, nodunder_getattr(), An error raised when the interpreter cannot evaluate a Python expression, due to, Subscript, Test that when no CM suppresses, the original exception propagates., Test that an exception raised inside __exit__ replaces the original. (+2 more)

### Community 29 - "Community 29"
Cohesion: 0.10
Nodes (18): _coerce_tool_call(), get_clean_message_list(), get_tool_json_schema(), _ParameterRemove, Creates a list of messages to give as input to the LLM. These messages are dicti, Check if the model supports the `stop` parameter.      Not supported with reas, Sentinel value to indicate a parameter should be removed., Prepare parameters required for model invocation.          Parameter priority (+10 more)

### Community 30 - "Community 30"
Cohesion: 0.10
Nodes (26): Ruff, Contributor Guidelines, Contributor Covenant Code of Conduct, Contribution Guide, Agency Spectrum, Code Actions Paradigm, Multi-step Agent Pattern, MultiStepAgent (+18 more)

### Community 31 - "Community 31"
Cohesion: 0.09
Nodes (16): ExecutionTimeoutError, Exception raised when code execution exceeds the maximum allowed time., Decorator to limit the execution time of a function using threading.      This, timeout(), Test the timeout mechanism for code execution., Test that code completing within the timeout limit works correctly., Test that code exceeding the timeout limit raises ExecutionTimeoutError., Test that evaluate_python_code completes within timeout for quick code. (+8 more)

### Community 32 - "Community 32"
Cohesion: 0.12
Nodes (8): MemoryStep, Register a callback for a step class.          Args:             step_cls (Ty, TaskStep, DummyMultiStepAgent, Test that _setup_step_callbacks correctly sets up the callback registry., Test that to_dict() and from_dict() work correctly for agents with managed agent, TestMultiStepAgent, TestMemoryStep

### Community 33 - "Community 33"
Cohesion: 0.10
Nodes (15): BoolOp, Compare, Delete, evaluate_boolop(), evaluate_condition(), evaluate_delete(), get_safe_module(), Creates a safe copy of a module or returns the original if it's a function (+7 more)

### Community 34 - "Community 34"
Cohesion: 0.10
Nodes (22): Agency, Agency spectrum, Code actions, JSON actions, CodeAgent, MultiStepAgent, ReAct framework, ToolCallingAgent (+14 more)

### Community 35 - "Community 35"
Cohesion: 0.13
Nodes (16): MCPClient, BaseException, Disconnect from the MCP server, Disconnect from the MCP server., Manages the connection to an MCP server and make its tools available to SmolAgen, Test the MCPClient with the try ... finally syntax., Test the MCPClient with multiple servers., Test the MCPClient with the context manager syntax. (+8 more)

### Community 36 - "Community 36"
Cohesion: 0.13
Nodes (15): DocCodeExtractor, Exception, Path, pytest_generate_tests(), Test a single documentation file., Fixture to ensure temporary directory exists for each test., Generate test cases for each markdown file., Runs command with subprocess.check_output and returns stdout if requested. (+7 more)

### Community 37 - "Community 37"
Cohesion: 0.13
Nodes (20): CodeAgent, Modality-Agnostic Design, Model-Agnostic Design, smolagents Library, Tool-Agnostic Design, ToolCallingAgent, Remote Execution Extras, Toolkit Extras (+12 more)

### Community 38 - "Community 38"
Cohesion: 0.11
Nodes (20): CodeAgent, Hub integration, Multi-step agent paradigm, PythonInterpreterTool, ToolCallingAgent, smolagents framework, MultiStepAgent, GoogleSearchTool (+12 more)

### Community 40 - "Community 40"
Cohesion: 0.11
Nodes (5): get_weather(), Get weather in the next days at given location.     Secretly this tool does not, RetrieverTool, Allows you to perform SQL queries on the table. Returns a string representation, sql_engine()

### Community 41 - "Community 41"
Cohesion: 0.17
Nodes (9): _CustomMarkdownify, Any, Helper function that converts and HTML string., Handle YouTube specially, focusing on the video title, description, and transcri, A custom version of markdownify's MarkdownConverter. Changes include:      - A, Same as usual, but be sure to start with a new line, Same as usual converter, but removes Javascript links and escapes URIs., Same as usual converter, but removes data URIs (+1 more)

### Community 42 - "Community 42"
Cohesion: 0.20
Nodes (7): MarkdownConverter, (In preview) An extremely simple text-based document reader, suitable for LLM us, Args:             - source: can be a string representing a path or url, or a re, Append a unique non-None, non-empty extension to a list of extensions., Use puremagic (a Python implementation of libmagic) to guess a file's extension, TextInspectorTool, Response

### Community 43 - "Community 43"
Cohesion: 0.11
Nodes (8): bad_return_func(), missing_arg_doc_func(), no_docstring_func(), A well-formed function with docstring, type hints, and return block., Function with no docstring., Function with docstring but missing an argument description., Function docstring with missing return description (allowed)., valid_func()

### Community 44 - "Community 44"
Cohesion: 0.12
Nodes (17): Human-in-the-Loop (HITL), Agent Memory Preservation, Plan Interruption Pattern, Step Callback, Agentic RAG, BM25 Retriever, Hypothetical Document Embedding (HyDE), RetrieverTool (+9 more)

### Community 45 - "Community 45"
Cohesion: 0.13
Nodes (17): Google Gemini Integration, xAI Grok Integration, OpenRouter Integration, REMOVE_PARAMETER Sentinel, Model Integration Extras, AmazonBedrockModel, ApiModel, AzureOpenAIModel (+9 more)

### Community 46 - "Community 46"
Cohesion: 0.16
Nodes (6): PrintContainer, Implements the += operator, String representation, Representation for debugging, Implements len() function support, TestPrintContainer

### Community 47 - "Community 47"
Cohesion: 0.12
Nodes (9): GradioUITester, Test scenario with special characters in filename, Test custom allowed file types, Clean up test environment, Test default allowed file types, Test default disallowed file types, Test successful file upload scenario, Test scenario when no file is selected (+1 more)

### Community 48 - "Community 48"
Cohesion: 0.22
Nodes (4): Search using the Exa API. Requires an EXA_API_KEY environment variable., WebSearchTool, Tests for the Exa engine in WebSearchTool., TestWebSearchToolExa

### Community 49 - "Community 49"
Cohesion: 0.13
Nodes (14): convert_currency(), get_joke(), get_news_headlines(), get_random_fact(), get_time_in_timezone(), get_weather(), Fetches a random joke from the JokeAPI.     This function sends a GET request t, Fetches the current time for a given location using the World Time API.     Arg (+6 more)

### Community 50 - "Community 50"
Cohesion: 0.23
Nodes (4): is_rate_limit_error(), Any, BaseException, Check if the exception is a rate limit error.

### Community 51 - "Community 51"
Cohesion: 0.22
Nodes (4): get_tool_call_from_text(), parse_json_if_needed(), Sometimes APIs do not return the tool call as a specific object, so we need to p, TestGetToolCallFromText

### Community 52 - "Community 52"
Cohesion: 0.18
Nodes (13): Default toolbox, DuckDuckGoSearchTool, load_tool, PythonInterpreterTool, Tool, ToolCollection, tool decorator, VisitWebpageTool (+5 more)

### Community 53 - "Community 53"
Cohesion: 0.15
Nodes (5): AgentType, Displays correctly this type in an ipython notebook (ipython, colab, jupyter, .., Displays correctly this type in an ipython notebook (ipython, colab, jupyter, .., Returns the stringified version of that object. In the case of an AgentAudio, it, Abstract class to be reimplemented to define types that can be returned by agent

### Community 55 - "Community 55"
Cohesion: 0.15
Nodes (8): PicklableCustomClass, A simple class that can be pickled., Verify pickle fallback works but warns in legacy mode., Test handling of different prefix formats., Test detection of safe: prefix., Test pickle: prefix when pickle is allowed., Test detection and handling of legacy format (no prefix)., TestPrefixHandling

### Community 56 - "Community 56"
Cohesion: 0.23
Nodes (11): display_plan(), get_modified_plan(), get_user_choice(), interrupt_after_plan(), main(), Plan Customization Example  This example demonstrates how to use step callback, Run the complete plan customization example, Display the plan in a formatted way (+3 more)

### Community 57 - "Community 57"
Cohesion: 0.27
Nodes (4): InferenceClientModel, A class to interact with Hugging Face's Inference Providers for language model i, Create the Hugging Face client., TestInferenceClientModel

### Community 58 - "Community 58"
Cohesion: 0.17
Nodes (6): Any, Send variables to the kernel namespace using SafeSerializer.          Uses pre, Run the code and determine if it is the final answer., Patch the FinalAnswerTool to raise an exception.          This is necessary be, Execute Python code in the Blaxel sandbox and return the result.          Args, get_tools_definition_code()

### Community 59 - "Community 59"
Cohesion: 0.24
Nodes (5): Tool collections enable loading a collection of tools in the agent's toolbox., Loads a tool collection from the Hub.          it adds a collection of tools f, Automatically load a tool collection from an MCP server.          This method, ToolCollection, TestToolCollection

### Community 60 - "Community 60"
Cohesion: 0.17
Nodes (3): Test that PythonInterpreterTool can disable timeout., Test that PythonInterpreterTool respects custom timeout., TestPythonInterpreterTool

### Community 61 - "Community 61"
Cohesion: 0.20
Nodes (4): Update the metrics of the monitor.          Args:             step_log ([`Mem, Logs a message to the console.          Args:             level (LogLevel, op, Convert arbitrary values (including bytes / control characters) into a safe stri, sanitize_for_rich()

### Community 62 - "Community 62"
Cohesion: 0.33
Nodes (9): check_close_call(), check_prediction_contains_answer_letters_in_order(), is_float(), normalize_number_str(), normalize_str(), any, question_scorer(), Normalize a string by:     - Removing all white spaces     - Optionally removi (+1 more)

### Community 63 - "Community 63"
Cohesion: 0.31
Nodes (9): _convert_type_hints_to_json_schema(), _get_json_schema_type(), _parse_google_format_docstring(), _parse_type_hint(), _parse_union_type(), Any, Parses a Google-style docstring to extract the function description,     argume, Exception raised for errors in parsing type hints to generate JSON schemas (+1 more)

### Community 64 - "Community 64"
Cohesion: 0.20
Nodes (8): DocstringParsingException, get_imports(), get_package_name(), Exception, Return the package name for a given import name.      Args:         import_na, Extracts all the libraries (not relative imports) that are imported in a code., Exception raised for errors in parsing docstrings to generate JSON schemas, TestGetCode

### Community 65 - "Community 65"
Cohesion: 0.22
Nodes (4): get_dict_from_nested_dataclasses(), make_json_serializable(), Any, Recursive function to make objects JSON serializable

### Community 67 - "Community 67"
Cohesion: 0.28
Nodes (9): MCPClient, Tool (base class), ToolCollection, LangChain Tool Adapter, MCP Server Integration, Hub Space as Tool, MCP Structured Output, @tool Decorator (+1 more)

### Community 68 - "Community 68"
Cohesion: 0.36
Nodes (7): get_document_description(), get_image_description(), get_single_file_description(), get_tasks_to_run(), get_zip_description(), Path, serialize_agent_error()

### Community 69 - "Community 69"
Cohesion: 0.39
Nodes (6): InMemorySpanExporter, in_memory_span_exporter(), instrument(), TestOpenTelemetry, tracer_provider(), TracerProvider

### Community 70 - "Community 70"
Cohesion: 0.38
Nodes (4): answer_questions(), answer_single_question(), append_answer(), serialize_agent_error()

### Community 71 - "Community 71"
Cohesion: 0.33
Nodes (7): Agentic RAG, BM25Retriever, HyDE, RAG, RetrieverTool, Self-Query, Agentic RAG

### Community 72 - "Community 72"
Cohesion: 0.29
Nodes (7): AzureOpenAIModel, InferenceClientModel, LiteLLMModel, MLXModel, TransformersModel, Custom model pattern, OpenAIModel

### Community 73 - "Community 73"
Cohesion: 0.33
Nodes (5): extract_code_from_text(), parse_code_blobs(), Extract code from the LLM's output., Extract code blocs from the LLM's output.      If a valid code block is passed, AgentTextTests

### Community 74 - "Community 74"
Cohesion: 0.29
Nodes (4): Test that @tool correctly extracts source code with multiple decorators., Test that @tool correctly extracts source code with multiline function signature, Test that @tool works with both multiple decorators and multiline signatures., TestToolDecorator

### Community 75 - "Community 75"
Cohesion: 0.47
Nodes (5): get_agent(), Async CodeAgent Example with Starlette  This example demonstrates how to use a, run_agent_endpoint(), run_agent_in_thread(), Request

### Community 76 - "Community 76"
Cohesion: 0.47
Nodes (4): encode_image(), process_images_and_text(), resize_image(), VisualQATool

### Community 77 - "Community 77"
Cohesion: 0.33
Nodes (3): Any, Connect to the MCP server and initialize the tools., Connect to the MCP server and return the tools directly.          Note that be

### Community 79 - "Community 79"
Cohesion: 0.40
Nodes (5): Arize AI Phoenix, Langfuse, MLflow, OpenTelemetry Instrumentation, SmolagentsInstrumentor

### Community 80 - "Community 80"
Cohesion: 0.40
Nodes (5): Tool, tool decorator, ToolCollection, Tool.from_langchain, Tool.from_space

### Community 81 - "Community 81"
Cohesion: 0.67
Nodes (4): Arize AI Phoenix, Langfuse, OpenTelemetry, SmolagentsInstrumentor

### Community 83 - "Community 83"
Cohesion: 0.67
Nodes (3): main(), Return an inline MCP server script that exposes a weather tool., weather_server_script()

### Community 85 - "Community 85"
Cohesion: 0.50
Nodes (4): Agent memory, Multi-agent, Multi-step agent, Tool calling

### Community 86 - "Community 86"
Cohesion: 0.50
Nodes (4): Arize AI Phoenix, Langfuse, OpenTelemetry integration, SmolagentsInstrumentor

### Community 88 - "Community 88"
Cohesion: 0.50
Nodes (3): FinalAnswerException, BaseException, Exception raised when final_answer is called.      Inherits from BaseException

### Community 89 - "Community 89"
Cohesion: 0.50
Nodes (4): test_tool(), Test validation of tool arguments with focus on nullable properties: optional (w, test_validate_tool_arguments(), test_validate_tool_arguments_nullable()

### Community 90 - "Community 90"
Cohesion: 0.67
Nodes (3): AgentMemory, PromptTemplates, ActionStep

### Community 91 - "Community 91"
Cohesion: 0.67
Nodes (3): AgentAudio, AgentImage, AgentText

## Knowledge Gaps
- **148 isolated node(s):** `smolagents`, `Yao et al. 2022`, `InferenceClientModel`, `LiteLLMModel`, `final_answer` (+143 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **66 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Tool` connect `Community 5` to `Community 1`, `Community 2`, `Community 4`, `Community 6`, `Community 7`, `Community 8`, `Community 9`, `Community 11`, `Community 12`, `Community 13`, `Community 14`, `Community 15`, `Community 16`, `Community 18`, `Community 19`, `Community 20`, `Community 21`, `Community 22`, `Community 25`, `Community 27`, `Community 28`, `Community 29`, `Community 31`, `Community 32`, `Community 35`, `Community 39`, `Community 40`, `Community 42`, `Community 46`, `Community 48`, `Community 54`, `Community 57`, `Community 58`, `Community 59`, `Community 63`, `Community 74`, `Community 76`, `Community 77`, `Community 78`, `Community 82`, `Community 88`, `Community 114`?**
  _High betweenness centrality (0.252) - this node is a cross-community bridge._
- **Why does `SerializationError` connect `Community 24` to `Community 1`, `Community 3`, `Community 17`, `Community 19`, `Community 55`?**
  _High betweenness centrality (0.074) - this node is a cross-community bridge._
- **Why does `FinalAnswerTool` connect `Community 1` to `Community 0`, `Community 2`, `Community 4`, `Community 5`, `Community 7`, `Community 12`, `Community 13`, `Community 14`, `Community 16`, `Community 18`, `Community 19`, `Community 20`, `Community 28`, `Community 31`, `Community 32`, `Community 33`, `Community 46`, `Community 51`, `Community 57`, `Community 58`?**
  _High betweenness centrality (0.068) - this node is a cross-community bridge._
- **Are the 106 inferred relationships involving `Tool` (e.g. with `ActionOutput` and `CodeAgent`) actually correct?**
  _`Tool` has 106 INFERRED edges - model-reasoned connections that need verification._
- **Are the 70 inferred relationships involving `ChatMessage` (e.g. with `ActionOutput` and `CodeAgent`) actually correct?**
  _`ChatMessage` has 70 INFERRED edges - model-reasoned connections that need verification._
- **Are the 76 inferred relationships involving `CodeAgent` (e.g. with `get_agent()` and `create_agent()`) actually correct?**
  _`CodeAgent` has 76 INFERRED edges - model-reasoned connections that need verification._
- **Are the 82 inferred relationships involving `TokenUsage` (e.g. with `ActionOutput` and `CodeAgent`) actually correct?**
  _`TokenUsage` has 82 INFERRED edges - model-reasoned connections that need verification._
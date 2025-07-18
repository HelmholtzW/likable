#!/usr/bin/env python
# Copyright 2024 The HuggingFace Inc. team. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import re
import time
from collections.abc import Generator

from smolagents.agent_types import AgentAudio, AgentImage, AgentText
from smolagents.agents import PlanningStep
from smolagents.memory import ActionStep, FinalAnswerStep
from smolagents.models import ChatMessageStreamDelta
from smolagents.utils import _is_package_available


def get_step_footnote_content(
    step_log: ActionStep | PlanningStep, step_name: str
) -> str:
    """Get a footnote string for a step log with duration and token information"""
    step_footnote = f"**{step_name}**"
    if step_log.token_usage is not None:
        step_footnote += (
            f" | Input tokens: {step_log.token_usage.input_tokens:,} | "
            f"Output tokens: {step_log.token_usage.output_tokens:,}"
        )
    step_footnote += (
        f" | Duration: {round(float(step_log.timing.duration), 2)}s"
        if step_log.timing.duration
        else ""
    )
    step_footnote_content = (
        f"""<span style="color: #bbbbc2; font-size: 12px;">{step_footnote}</span> """
    )
    return step_footnote_content


def _clean_model_output(model_output: str) -> str:
    """
    Clean up model output by removing trailing tags and extra backticks.

    Args:
        model_output (`str`): Raw model output.

    Returns:
        `str`: Cleaned model output.
    """
    if not model_output:
        return ""
    model_output = model_output.strip()
    # Remove any trailing <end_code> and extra backticks,
    # handling multiple possible formats
    model_output = re.sub(
        r"```\s*<end_code>", "```", model_output
    )  # handles ```<end_code>
    model_output = re.sub(
        r"<end_code>\s*```", "```", model_output
    )  # handles <end_code>```
    model_output = re.sub(
        r"```\s*\n\s*<end_code>", "```", model_output
    )  # handles ```\n<end_code>
    return model_output.strip()


def _format_code_content(content: str) -> str:
    """
    Format code content as Python code block if it's not already formatted.

    Args:
        content (`str`): Code content to format.

    Returns:
        `str`: Code content formatted as a Python code block.
    """
    content = content.strip()
    # Remove existing code blocks and end_code tags
    content = re.sub(r"```.*?\n", "", content)
    content = re.sub(r"\s*<end_code>\s*", "", content)
    content = content.strip()
    # Add Python code block formatting if not already present
    if not content.startswith("```python"):
        content = f"```python\n{content}\n```"
    return content


def _process_action_step(
    step_log: ActionStep, skip_model_outputs: bool = False, parent_id: str | None = None
) -> Generator:
    """
    Process an [`ActionStep`] and yield appropriate Gradio ChatMessage objects.

    Args:
        step_log ([`ActionStep`]): ActionStep to process.
        skip_model_outputs (`bool`): Whether to skip model outputs.

    Yields:
        `gradio.ChatMessage`: Gradio ChatMessages representing the action step.
    """
    import gradio as gr

    # First yield the thought/reasoning from the LLM
    if not skip_model_outputs and getattr(step_log, "model_output", ""):
        model_output = _clean_model_output(step_log.model_output)
        yield gr.ChatMessage(
            role="assistant",
            content=model_output,
            metadata={
                "title": "💭 Thought",
                "status": "done",
                "id": int(time.time() * 1000),
                "parent_id": parent_id,
            },
        )

    # For tool calls, create a parent message
    if getattr(step_log, "tool_calls", []):
        first_tool_call = step_log.tool_calls[0]
        used_code = first_tool_call.name == "python_interpreter"

        # Process arguments based on type
        args = first_tool_call.arguments
        if isinstance(args, dict):
            content = str(args.get("answer", str(args)))
        else:
            content = str(args).strip()

        # Format code content if needed
        if used_code:
            content = _format_code_content(content)

        # Create the tool call message
        parent_message_tool = gr.ChatMessage(
            role="assistant",
            content=content,
            metadata={
                "title": f"🛠️ Used tool {first_tool_call.name}",
                "status": "done",
                "parent_id": parent_id,
                "id": int(time.time() * 1000),
            },
        )
        yield parent_message_tool

    # Display execution logs if they exist
    if getattr(step_log, "observations", "") and step_log.observations.strip():
        log_content = step_log.observations.strip()
        if log_content:
            log_content = re.sub(r"^Execution logs:\s*", "", log_content)
            yield gr.ChatMessage(
                role="assistant",
                content=f"```bash\n{log_content}\n",
                metadata={
                    "title": "📝 Execution Logs",
                    "status": "done",
                    "parent_id": parent_id,
                    "id": int(time.time() * 1000),
                },
            )

    # Display any images in observations
    if getattr(step_log, "observations_images", []):
        for image in step_log.observations_images:
            path_image = AgentImage(image).to_string()
            yield gr.ChatMessage(
                role="assistant",
                content={
                    "path": path_image,
                    "mime_type": f"image/{path_image.split('.')[-1]}",
                },
                metadata={
                    "title": "🖼️ Output Image",
                    "status": "done",
                    "parent_id": parent_id,
                    "id": int(time.time() * 1000),
                },
            )

    # Handle errors
    if getattr(step_log, "error", None):
        yield gr.ChatMessage(
            role="assistant",
            content=str(step_log.error),
            metadata={
                "title": "💥 Error",
                "status": "done",
                "parent_id": parent_id,
                "id": int(time.time() * 1000),
            },
        )

    # Add step footnote and separator
    # yield gr.ChatMessage(
    #     role="assistant",
    #     content=get_step_footnote_content(step_log, step_number),
    #     metadata={
    #         "status": "done",
    #         "parent_id": parent_id,
    #         "id": int(time.time() * 1000),
    #     },
    # )
    # yield gr.ChatMessage(
    #     role="assistant",
    #     content="-----",
    #     metadata={
    #         "status": "done",
    #         "parent_id": parent_id,
    #         "id": int(time.time() * 1000),
    #     },
    # )


def _process_planning_step(
    step_log: PlanningStep, skip_model_outputs: bool = False
) -> Generator:
    """
    Process a [`PlanningStep`] and yield appropriate gradio.ChatMessage objects.

    Args:
        step_log ([`PlanningStep`]): PlanningStep to process.

    Yields:
        `gradio.ChatMessage`: Gradio ChatMessages representing the planning step.
    """
    import gradio as gr

    if not skip_model_outputs:
        yield gr.ChatMessage(
            role="assistant", content="**Planning step**", metadata={"status": "done"}
        )
        yield gr.ChatMessage(
            role="assistant", content=step_log.plan, metadata={"status": "done"}
        )
    yield gr.ChatMessage(
        role="assistant",
        content=get_step_footnote_content(step_log, "Planning step"),
        metadata={"status": "done"},
    )
    yield gr.ChatMessage(role="assistant", content="-----", metadata={"status": "done"})


def _process_final_answer_step(step_log: FinalAnswerStep) -> Generator:
    """
    Process a [`FinalAnswerStep`] and yield appropriate gradio.ChatMessage objects.

    Args:
        step_log ([`FinalAnswerStep`]): FinalAnswerStep to process.

    Yields:
        `gradio.ChatMessage`: Gradio ChatMessages representing the final answer.
    """
    import gradio as gr

    final_answer = step_log.output
    if isinstance(final_answer, AgentText):
        yield gr.ChatMessage(
            role="assistant",
            content=f"**Final answer:**\n{final_answer.to_string()}\n",
            metadata={"status": "done"},
        )
    elif isinstance(final_answer, AgentImage):
        yield gr.ChatMessage(
            role="assistant",
            content={"path": final_answer.to_string(), "mime_type": "image/png"},
            metadata={"status": "done"},
        )
    elif isinstance(final_answer, AgentAudio):
        yield gr.ChatMessage(
            role="assistant",
            content={"path": final_answer.to_string(), "mime_type": "audio/wav"},
            metadata={"status": "done"},
        )
    else:
        yield gr.ChatMessage(
            role="assistant",
            content=f"**Final answer:** {str(final_answer)}",
            metadata={"status": "done"},
        )


def pull_messages_from_step(
    step_log: ActionStep | PlanningStep | FinalAnswerStep,
    skip_model_outputs: bool = False,
    parent_id: str | None = None,
):
    """Extract Gradio ChatMessage objects from agent steps with proper nesting.

    Args:
        step_log: The step log to display as gr.ChatMessage objects.
        skip_model_outputs: If True, skip the model outputs when creating
            the gr.ChatMessage objects:
            This is used for instance when streaming model outputs have
            already been displayed.
        parent_id: The ID of the parent message. Only used for nested thoughts.
            Nested thoughts can be nested by setting the parent_id to the id
            of the parent thought.
    """
    if not _is_package_available("gradio"):
        raise ModuleNotFoundError(
            "Please install 'gradio' extra to use the GradioUI: "
            "`pip install 'smolagents[gradio]'`"
        )
    if isinstance(step_log, ActionStep):
        yield from _process_action_step(step_log, skip_model_outputs, parent_id)
    elif isinstance(step_log, PlanningStep):
        yield from _process_planning_step(step_log, skip_model_outputs)
    elif isinstance(step_log, FinalAnswerStep):
        yield from _process_final_answer_step(step_log)
    else:
        raise ValueError(f"Unsupported step type: {type(step_log)}")


def stream_to_gradio(
    agent,
    task: str,
    task_images: list | None = None,
    reset_agent_memory: bool = False,
    additional_args: dict | None = None,
    parent_id: int | None = None,
) -> Generator:
    """Runs an agent with the given task and streams the messages from the agent
    as gradio ChatMessages."""
    if not _is_package_available("gradio"):
        raise ModuleNotFoundError(
            "Please install 'gradio' extra to use the GradioUI: "
            "`pip install 'smolagents[gradio]'`"
        )
    intermediate_text = ""

    for event in agent.run(
        task,
        images=task_images,
        stream=True,
        reset=reset_agent_memory,
        additional_args=additional_args,
    ):
        if isinstance(event, ActionStep | PlanningStep | FinalAnswerStep):
            intermediate_text = ""
            yield from pull_messages_from_step(
                event,
                # If we're streaming model outputs, no need to display them twice
                skip_model_outputs=getattr(agent, "stream_outputs", False),
                parent_id=parent_id,
            )
        elif isinstance(event, ChatMessageStreamDelta):
            intermediate_text += event.content or ""
            yield intermediate_text

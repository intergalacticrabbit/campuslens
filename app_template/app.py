"""A one-screen app you can copy and change. Run it from the repo folder:  python app_template/app.py

Two tabs: ask Gemma 4 about a picture, and an agent that can use small tools.
Look for the lines marked CHANGE THIS.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # so we can import gemma_client

import gradio as gr

import gemma_client
from harness import Agent

# CHANGE THIS: the rule that tells Gemma how to behave in your app.
SYSTEM_RULE = "You are a helpful assistant. Keep your answers short and clear."

# CHANGE THIS: the title shown at the top of the page.
TITLE = "My Gemma 4 App"


def ask_about_picture(image_path, question):
    """Tab 1: works with a picture, or with text only."""
    if not question.strip():
        return "Please type a question first."
    try:
        if image_path:
            return gemma_client.ask_with_image(image_path, question, system=SYSTEM_RULE)
        return gemma_client.ask(question, system=SYSTEM_RULE)
    except Exception as error:
        return gemma_client.describe_error(error)


def ask_agent(question):
    """Tab 2: the agent may use tools. We show each step, then the answer."""
    if not question.strip():
        return "", "Please type a question first."
    agent = Agent(system=SYSTEM_RULE)
    try:
        answer = agent.run(question)
    except Exception as error:
        return "", gemma_client.describe_error(error)
    steps = "\n".join(f"{i}. {s['text']}" for i, s in enumerate(agent.steps[:-1], 1))
    return steps or "(No tools were used.)", answer


# CHANGE THIS: the layout. Add boxes, move things, rename the tabs.
with gr.Blocks(title=TITLE) as demo:
    gr.Markdown(f"# {TITLE}")

    with gr.Tab("Ask about a picture"):
        picture = gr.Image(type="filepath", label="Picture (optional)")
        question = gr.Textbox(label="Your question", value="What can you tell me about this?")
        submit = gr.Button("Submit")
        answer = gr.Textbox(label="Answer", lines=6)
        submit.click(ask_about_picture, [picture, question], answer)

    with gr.Tab("Agent with tools"):
        agent_question = gr.Textbox(label="Your question", value="What is 17 * 23, and what time is it?")
        agent_submit = gr.Button("Ask the agent")
        agent_steps = gr.Textbox(label="Tool steps", lines=6)
        agent_answer = gr.Textbox(label="Final answer", lines=4)
        agent_submit.click(ask_agent, agent_question, [agent_steps, agent_answer])

if __name__ == "__main__":
    print("Starting... open this address in your browser: http://127.0.0.1:7860")
    demo.launch(share=False)  # share=True would put your app on the public internet. Do not.

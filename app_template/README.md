# App template

A one-screen app with two tabs, built with Gradio (a Python tool that makes web pages).

- **Ask about a picture:** upload an image (optional), type a question, get an answer. Works with text only too.
- **Agent with tools:** ask a question. The agent may use tools (calculator, time, notes) and the tool steps are shown.

## Run it

From the repo folder, with your virtual environment on:

```
python app_template/app.py
```

Open http://127.0.0.1:7860 in your browser. Stop it with Ctrl+C.

## Make it yours

Open `app_template/app.py` and look for **CHANGE THIS**:

1. `SYSTEM_RULE`: tells Gemma how to behave in your app. This is the biggest change you can make.
2. `TITLE`: the name at the top.
3. The layout near the bottom: boxes, tabs, buttons.

Keep one Gemma call per click. It keeps the app fast and your free allowance safe.

## About sharing

The app starts with `share=False`, so only your computer can open it. Do **not** change it to `share=True` for anything with private data. `share=True` puts your app on the public internet, and anyone with the link can use it (and spend your free allowance).

To demo, show it on your own screen. For a screenshot, press Win+Shift+S on Windows or Cmd+Shift+4 on Mac.

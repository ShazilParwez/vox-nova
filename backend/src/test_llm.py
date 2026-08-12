import asyncio
import os
from dotenv import load_dotenv
from livekit.plugins import google
from livekit.agents.llm import ChatContext, ChatMessage

async def main():
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env.local"))
    
    print("Testing gemini-2.0-flash-exp...")
    try:
        llm = google.LLM(model="gemini-2.0-flash-exp")
        ctx = ChatContext()
        ctx.messages.append(ChatMessage(role="user", content="Say hello!"))
        stream = llm.chat(chat_ctx=ctx)
        async for chunk in stream:
            print(chunk.choices[0].delta.content, end="")
        print("\nSuccess with gemini-2.0-flash-exp!")
    except Exception as e:
        print(f"Error with gemini-2.0-flash-exp: {e}")

    print("\nTesting gemini-1.5-flash...")
    try:
        llm = google.LLM(model="gemini-1.5-flash")
        ctx = ChatContext()
        ctx.messages.append(ChatMessage(role="user", content="Say hello!"))
        stream = llm.chat(chat_ctx=ctx)
        async for chunk in stream:
            print(chunk.choices[0].delta.content, end="")
        print("\nSuccess with gemini-1.5-flash!")
    except Exception as e:
        print(f"Error with gemini-1.5-flash: {e}")

if __name__ == "__main__":
    asyncio.run(main())

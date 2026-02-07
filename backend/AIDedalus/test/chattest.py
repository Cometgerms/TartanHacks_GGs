import asyncio
import os
import inspect

from dotenv import load_dotenv

# Load env from backend/.env (this file is: backend/AIDedalus/test/chattest.py)
ENV_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
load_dotenv(ENV_PATH)

try:
    from dedalus_labs import AsyncDedalus, DedalusRunner  # type: ignore
except ModuleNotFoundError as e:
    raise SystemExit(
        "dedalus_labs is not installed in this environment.\n"
        "Install it first, then rerun this test.\n\n"
        "Suggested commands (Windows):\n"
        "  py -m pip install dedalus-labs\n"
    ) from e


async def main():
    api_key = (os.getenv("API_KEY") or "").strip()
    if not api_key:
        raise SystemExit(
            "API_KEY is missing. Add it to backend/.env as:\n"
            "  API_KEY=...\n"
        )

    # Prefer clean resource handling to avoid 'Event loop is closed' warnings on Windows.
    client = AsyncDedalus(api_key=api_key)
    try:
        runner = DedalusRunner(client)

        result = runner.run(
            input="What are the key factors that influence weather patterns?",
            model=os.getenv("DEDALUS_MODEL", "anthropic/claude-opus-4-6"),
        )
        response = await result if inspect.isawaitable(result) else result

        print(response.final_output)
    finally:
        # Try best-effort cleanup. Some SDK versions may keep an internal httpx AsyncClient.
        aclose = getattr(client, "aclose", None)
        if callable(aclose):
            maybe_awaitable = aclose()
            if inspect.isawaitable(maybe_awaitable):
                await maybe_awaitable

        # Extra cleanup for SDKs that expose the underlying httpx client.
        inner = getattr(client, "client", None) or getattr(client, "_client", None)
        inner_aclose = getattr(inner, "aclose", None)
        if callable(inner_aclose):
            maybe_awaitable = inner_aclose()
            if inspect.isawaitable(maybe_awaitable):
                await maybe_awaitable


if __name__ == "__main__":
    asyncio.run(main())
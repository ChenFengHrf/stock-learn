from __future__ import annotations

import argparse
import os

from dotenv import load_dotenv
from openai import AuthenticationError, OpenAI


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(prog="mimo-chat")
    parser.add_argument("prompt", help="Prompt to send to the OpenAI-compatible chat endpoint.")
    parser.add_argument("--model", default=os.getenv("STOCK_LEARN_MODEL", "openai:mimo-v2.5-pro"))
    parser.add_argument("--max-tokens", type=int, default=512)
    args = parser.parse_args()

    model = args.model.removeprefix("openai:")
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL") or os.getenv("OPENAI_API_BASE")
    if not api_key or not base_url:
        raise SystemExit("请先在 .env 中配置 OPENAI_API_KEY 和 OPENAI_BASE_URL。")

    client = OpenAI(api_key=api_key, base_url=base_url)
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": args.prompt}],
            max_tokens=args.max_tokens,
        )
    except AuthenticationError as exc:
        raise SystemExit(
            "认证失败：当前 OPENAI_API_KEY 被网关返回为 invalid_key，请更换有效 key 后重试。"
        ) from exc
    print(response.choices[0].message.content)


if __name__ == "__main__":
    main()

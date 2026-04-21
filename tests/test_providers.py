import asyncio
import unittest
from logging import error

import config
from providers import (
    LLMProvider,
    ChatMessage,
    OpenAIProvider,
    AnthropicProvider,
    OllamaProvider,
)

import providers

PAYLOAD_MESSAGE = "Tell me a short sentence about yourself."


def build_payload():
    return ChatMessage(
        role='user',
        content=PAYLOAD_MESSAGE)


async def run_test(provider: LLMProvider, message: ChatMessage):
    """
    Infer a response from a given provider instance.

    :param provider: take a wild guess
    :param message: The message object
    :return: A boolean indicating success or failure
    """
    name = provider.name
    header = f"[{name}]"
    print(f"{header} Generating response...")

    response = await provider.send_message(message) #await provider.chat(messages=[message])

    print(f"{header} ✓ (Model: {response.model})")
    print(f"{' ' * len(header)} Preview: {response.content[:100]}...")
    print()

    return response.content is not None

class MyTestCase(unittest.TestCase):
    def test_provider(self,
                      name: str,
                      assertion: bool = True):
        provider = config.load_provider(name)
        payload = build_payload()

        task = run_test(provider, payload)
        try:
            success = asyncio.run(task)
        except:
            success = False

        if assertion:
            self.assertEqual(
                success,
                True,
                f"Provider \"{name}\" failed test.")
        else:
            if success: pass
            error("Provider %s failed.", name)

    def test_openai(self):
        self.test_provider('openai')

    def test_anthropic(self):
        self.test_provider('anthropic')

    def test_ollama(self):
        self.test_provider('ollama')

    def test_all(self):
        all_providers = providers.PROVIDERS.keys()
        for provider in all_providers:
            self.test_provider(provider, False)


if __name__ == '__main__':
    unittest.main()

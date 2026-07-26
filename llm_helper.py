"""LLM configuration for Azure OpenAI and local OpenAI development."""

import os
from functools import lru_cache

from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI, ChatOpenAI

load_dotenv()


@lru_cache(maxsize=1)
def get_llm():
    '''Return a model authenticated by Azure CLI or Managed Identity.'''
    azure_endpoint = os.getenv('AZURE_OPENAI_ENDPOINT')
    azure_deployment = os.getenv('AZURE_OPENAI_DEPLOYMENT')

    if azure_endpoint and azure_deployment:
        from azure.identity import DefaultAzureCredential, get_bearer_token_provider

        token_provider = get_bearer_token_provider(
            DefaultAzureCredential(),
            'https://cognitiveservices.azure.com/.default',
        )
        return AzureChatOpenAI(
            azure_endpoint=azure_endpoint,
            azure_deployment=azure_deployment,
            api_version=os.getenv('AZURE_OPENAI_API_VERSION', '2024-10-21'),
            azure_ad_token_provider=token_provider,
            temperature=0.2,
        )

    openai_api_key = os.getenv('OPENAI_API_KEY')
    if openai_api_key:
        return ChatOpenAI(
            api_key=openai_api_key,
            model=os.getenv('OPENAI_MODEL', 'gpt-4.1-mini'),
            temperature=0.2,
        )

    raise RuntimeError(
        'AI is not configured. Set AZURE_OPENAI_ENDPOINT and '
        'AZURE_OPENAI_DEPLOYMENT after az login, or set OPENAI_API_KEY.'
    )

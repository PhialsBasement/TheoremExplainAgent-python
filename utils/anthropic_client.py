import anthropic
import logging
import time
import httpx

logger = logging.getLogger(__name__)

class AnthropicClient:
    def __init__(self, api_key, model_name, timeout=5400):
        # Anthropic client uses httpx underneath
        transport = httpx.HTTPTransport(retries=0)
        http_client = httpx.Client(
            timeout=timeout,
            transport=transport
        )

        self.client = anthropic.Anthropic(
            api_key=api_key,
            http_client=http_client  # Pass the configured httpx client
        )
        self.model = model_name
        logger.info(f"Initialized Anthropic client with model: {self.model} and timeout: {timeout}")

    def generate_response(self, prompt, max_tokens=32000, temperature=0.0, retries=3, retry_delay=5):
        """Generate a response from the Anthropic Claude model."""
        for attempt in range(retries):
            try:
                logger.debug(f"Sending prompt to Anthropic API (prompt length: {len(prompt)})")
                logger.info(f"Requesting response with max_tokens={max_tokens}")

                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )

                logger.debug(f"Received response from Anthropic API")
                return response.content[0].text

            except Exception as e:
                logger.error(f"Error generating response from Anthropic API (attempt {attempt+1}/{retries}): {str(e)}")
                if attempt < retries - 1:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    raise

"""Cost estimation for HPP (cost of goods) per article.

Prices are USD. Text prices are per 1,000,000 tokens (input / output); image
prices are per generated image. Defaults use current OpenAI list prices as the
cost basis. Replace with real SumoPod rates once confirmed — these are the only
numbers to touch, no business logic depends on the values.
"""

# model -> (input_usd_per_1m, output_usd_per_1m). SumoPod rates (per their Models page).
TEXT_PRICES = {
    # OpenAI
    'gpt-4o-mini': (0.15, 0.60),
    'gpt-4o': (2.50, 10.00),
    'gpt-4.1': (2.00, 8.00),
    'gpt-4.1-mini': (0.40, 1.60),
    'gpt-4.1-nano': (0.10, 0.40),
    'gpt-5-mini': (0.25, 2.00),
    'gpt-5-nano': (0.05, 0.40),
    'o4-mini': (1.10, 4.40),
    # Anthropic
    'claude-sonnet-4-6': (3.00, 15.00),
    'claude-haiku-4-5': (1.00, 5.00),
    # Google
    'gemini/gemini-2.5-flash': (0.30, 2.50),
    'gemini-2.5-flash': (0.30, 2.50),
    'gemini/gemini-2.5-flash-lite': (0.10, 0.40),
    'gemini-2.5-flash-lite': (0.10, 0.40),
    # Cheap test models
    'deepseek-v4-flash': (0.14, 0.28),
    'mimo-v2.5': (0.14, 0.28),
    'qwen3.7-plus': (0.32, 1.28),
    'MiniMax-M2.7-highspeed': (0.03, 0.12),
}

# image model -> {size: usd_per_image}
IMAGE_PRICES = {
    'dall-e-3': {
        '1024x1024': 0.040,
        '1024x1792': 0.080,
        '1792x1024': 0.080,
    },
    'dall-e-2': {
        '1024x1024': 0.020,
        '512x512': 0.018,
        '256x256': 0.016,
    },
}

_DEFAULT_IMAGE_PRICE = 0.040


def estimate_text_cost(model, tokens_in, tokens_out):
    """USD cost for a text generation. Unknown model -> 0.0."""
    rates = TEXT_PRICES.get(model)
    if not rates:
        return 0.0
    in_rate, out_rate = rates
    return (tokens_in / 1_000_000) * in_rate + (tokens_out / 1_000_000) * out_rate


def estimate_image_cost(model, size="1024x1024"):
    """USD cost for one generated image. Unknown -> default flat price."""
    if not model:
        return 0.0
    sizes = IMAGE_PRICES.get(model)
    if not sizes:
        return _DEFAULT_IMAGE_PRICE
    return sizes.get(size, _DEFAULT_IMAGE_PRICE)

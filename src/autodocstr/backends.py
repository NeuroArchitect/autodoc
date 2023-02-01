# The type of document generator to use
import abc
import ast
import hashlib
import json
import logging
import os
import pickle
import time
import urllib.parse
import urllib.request
from functools import wraps
from typing import Dict, Union

# Set up logging
logger = logging.getLogger(__name__)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
ch = logging.StreamHandler()
ch.setFormatter(formatter)
logger.addHandler(ch)
logger.setLevel(logging.DEBUG)


def rate_limited(max_per_minute):
    """
    Decorator that make functions not be called faster than
    """
    min_interval = 60 / max_per_minute

    def decorate(func):
        last_time_called = [0.0]

        @wraps(func)
        def rate_limited_function(*args, **kwargs):
            elapsed = time.perf_counter() - last_time_called[0]
            left_to_wait = min_interval - elapsed
            if left_to_wait > 0:
                time.sleep(left_to_wait)
            ret = func(*args, **kwargs)
            last_time_called[0] = time.perf_counter()
            return ret

        return rate_limited_function

    return decorate


# https://platform.openai.com/docs/guides/rate-limits/overview
@rate_limited(20)
def make_request(url: str, headers, data: Dict):
    """
    Creates a POST request to the specified URL with the given data.
    Returns the response object.
    """
    import io

    fd = io.StringIO()
    json.dump(data, fd)
    fd.flush()
    fd.seek(0)
    req = urllib.request.Request(url, headers=headers, data=fd, method="POST")
    try:
        response = urllib.request.urlopen(req)
    except urllib.error.HTTPError as e:
        logger.error(e.read(), exc_info=True)
        raise e
    body = response.read().decode("utf-8")
    return json.loads(body)


class Backend(abc.ABC):
    @abc.abstractmethod
    def generate_function_doc_string(self, func_signature, func_body):
        """
        Generate a docstring for a function.
        Args:
            func_signature (str): The function signature.
            func_body (str): The function body.
        Returns:
            str: The docstring.
        """
        raise NotImplementedError


def _load_cache():
    """Loads the cache from disk.
    Args:
        None
    Returns:
        The cache as a dictionary.
    Raises:
        None
    """
    if not os.path.exists("cache.pickle"):
        return None
    with open("cache.pickle", "rb") as f:
        return pickle.load(f)


def _write_cache(cache):
    """Write the cache to disk.
    Args:
        cache: The cache to write to disk.
    """
    with open("cache.pickle", "wb") as f:
        return pickle.dump(cache, f, protocol=pickle.HIGHEST_PROTOCOL)


def compute_sha256(data):
    """
    Compute the SHA256 hash of a given string.
    Args:
        data (str): The string to hash.
    Returns:
        str: The SHA256 hash of the given string.
    """
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


class CodexBackend(Backend):
    def __init__(self, api_key):
        """
        Initialize the OpenAI API client.
        Args:
            api_key: The OpenAI API key.
        """
        self.api_key = api_key
        self.cache = _load_cache() or {}
        if not api_key or api_key.strip() == "":
            raise ValueError("OPENAI_API_KEY is not set.")

    def __del__(self):
        """Write the cache to disk and then destroy the object."""
        _write_cache(self.cache)

    def generate_function_doc_string(self, func_signature, func_body):
        """
        Generate a docstring for a function.
        :param func_signature: The function signature.
        :param func_body: The function body.
        :return: The docstring.
        """
        functions_prompts = [
            "# Write a python docstring for the following function.",
            "# A python docstring MUST give enough information to write \
                a call to the function without reading the function's code.",
            '# The python docstring MUST be imperative-style \
            ("""Fetch rows from a Bigtable.""").',
            "# The python docstring MUST describe the function's calling syntax"
            "and its semantics, but not its implementation details.",
            "# The python docstring MUST contain at least ONE short descriptive statement.",
            "# Use Google's documentation style.",
            "#  Args: List each parameter by name.",
            "#  Returns or Yields: The return value."
            "If the function only returns None, this section is not required."
            "It may also be omitted if the docstring starts with Returns or Yields"
            "#  Raises: List the exceptions that are relevant to the interface.",
            "# write only the docstring, nothing else."
            '# terminate the docstring with: <|docstr|>. i.e: """This is a docstring."""\n\t<|docstr|>""',
            "# The docstring MUST be a valid python docstring.",
            "# Add the docstring to the following function:",
        ]
        prompt = "\n".join([*functions_prompts, func_signature])
        result = self.get_response(prompt, "\n\t# start of function: " + func_body)
        if result is None:
            raise ValueError("Codex response is empty.")
        for completion_candidate in result["choices"]:
            if completion_candidate["finish_reason"] == "stop":
                return completion_candidate["text"]

        return completion_candidate["text"]

    def get_response(self, prompt, suffix) -> Union[Dict, None]:
        """
        Call the Codex API with the constructed prompt using the user's OPENAI_API_KEY.
        API calls look like:
        """
        # https://platform.openai.com/docs/guides/code/best-practices
        data = {
            "model": "code-davinci-002",
            "prompt": prompt,
            "suffix": suffix,
            "max_tokens": 512 * 3,
            "temperature": 0.0,
            "top_p": 0.0,
            "best_of": 1,
            "stop": ["<|docstr|>", "<|endoftext|>"],
            "frequency_penalty": 0.01,
            "presence_penalty": 0.0,
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        hash = compute_sha256(json.dumps(data))

        if hash in self.cache:
            logger.info("Using cached response")
            response = self.cache[hash]
            return response

        try:
            result = make_request(
                "https://api.openai.com/v1/completions",
                headers=headers,
                data=data,
            )
            # cache result
            self.cache[hash] = result
            return result
        except KeyError:
            logger.error("Error: Codex API call failed.", exc_info=True)
            return None

    def quick_extract_doc(self, data):
        """
        Extracts the docstring from a python file.
        Args:
            data: The python file.
        Returns:
            The docstring.
        """
        # Iterate over all nodes in the AST
        try:
            tree = ast.parse(data)
            for node in ast.walk(tree):
                # If the node is a function or method definition, add its name to the list
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    return ast.get_docstring(node)
        except SyntaxError:
            return f'"""{data}"""'

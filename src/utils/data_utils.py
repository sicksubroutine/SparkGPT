from datetime import datetime as dt
import datetime
import random
import string
from pathlib import Path
import requests
from logging import Logger
import logging
from constants import MARKDOWN_DIR
from utils.chat_utils import openai_response
from db_manage import g
from typing import Tuple
import qrcode

logger: Logger = logging.getLogger(__name__)


def time_get() -> str:
    return dt.now().strftime("%m-%d-%Y %I:%M:%S %p")


def time_get_unix() -> int:
    return int(dt.now().timestamp() * 1000)


def unix_to_string(unix: int) -> str:
    return dt.fromtimestamp(unix / 1000).strftime("%m-%d-%Y %I:%M:%S %p")


def api_request(method: str, url: str, **kwargs: dict) -> tuple:
    """
    Sends an API request to the given URL using the given HTTP method
    and keyword arguments.

    Parameters:
      method (str): The HTTP method to be used for the request.
      url (str): The URL for the request.
      **kwargs (dict): The keyword arguments to be passed to the request.

    Raises:
      Exception: If the API request fails.

    Returns:
      tuple: A tuple containing the response and the response JSON.
      The tuple has the following structure: (response, response_json)
    """
    try:
        response = requests.request(method, url, **kwargs)
        if not response.ok:
            raise Exception(
                f"API request failed with status code {response.status_code}."
            )
        response_json = response.json()
        return response, response_json
    except Exception as e:
        logger.error(f"API request failed: {e}")
        return None, None


def tokenGet30() -> str:
    """
    Generate a random token consisting of uppercase letters and digits.
    The token is 30 characters long.

    Returns:
    str: A random token.
    """
    return "".join(
        random.choice(string.ascii_letters + string.digits) for _ in range(30)
    )


def tokenGet16() -> str:
    """
    Generate a random token consisting of uppercase letters and digits.
    The token is 16 characters long.

    Returns:
    str: A random token.
    """
    return "".join(
        random.choice(string.ascii_uppercase + string.digits) for _ in range(16)
    )


def clean_up_files(path: Path, extension: str) -> None:
    """
    Cleans up files with a specific extension from a directory.

    Parameters:
        path (Path): The path to the directory to clean up.
        extension (str): The extension of the files to clean up.
    """
    for filename in path.iterdir():
        if filename.suffix == extension:
            filename.unlink()


def check_old_markdown() -> None:
    """
    Checks and removes outdated Markdown files from the 'static/markdown/' directory.

    This method checks if the 'static/markdown/' directory exists.
    If it doesn't, the directory is created.
    Then, it iterates through each file in the directory
    and removes any file with the '.md' extension.
    """
    markdown_path: Path = MARKDOWN_DIR
    if not markdown_path.exists():
        markdown_path.mkdir(parents=True, exist_ok=True)
    clean_up_files(markdown_path, ".md")


def clean_up_invoices() -> None:
    """
    Cleans up old invoice QR code files from the 'static/qr/' directory.

    This method iterates through each file in the 'static/qr/' directory and
    removes any file with the '.png' extension.
    """
    path = Path("static/qr/")
    clean_up_files(path, ".png")


def summary_of_messages(message: str) -> Tuple[str, str]:
    """
    Generates a summary of the user's messages in a conversation
    and obtains a concise response.

    Parameters:
        message (str): The message to be summarized.

    Returns:
        tuple[str, str]: A tuple containing the longer response and the concise response.
        The tuple has the following structure: (longer_response, concise_response)
    """

    prompt = """
        The following message should be summarized as your output.
        Output should have no explanation or elaboration. Just a summary.
        Output is required to be seven words or less with no punctuation.
        """
    summary = [
        {"role": "system", "content": f"{prompt}"},
        {"role": "user", "content": message},
    ]
    response, _ = openai_response(summary, "gpt-3.5-turbo")
    longer_response = response
    response = response.split()
    response = "_".join(response)
    response = filter_out_symbols(response)
    return longer_response, response


def filter_out_symbols(text: str) -> str:
    """
    Filters out symbols from the given text.

    Args:
        text (str): The text to filter.

    Returns:
        str: The text with symbols removed.
    """
    return "".join(char for char in text if char.isalnum() or char == "_")


def export_as_markdown(convo: str, title: str, model: str) -> str:
    """
    Exports a conversation as a Markdown file.

    Parameters:
        convo (str): The conversation identifier or key.
        title (str): The title of the session.
        model (str): The model used for the session.

    Returns:
        str: The path to the Markdown file.

    Notes:
        - The method retrieves the messages from a database
        based on the given conversation identifier.
        - It iterates through the messages and
        creates a Markdown file with the following format:
        - The title of the session.
        - The model used for the session.
        - The user's messages.
        - The assistant's messages.
        - The Markdown file is saved in the 'static/markdown/' directory.
    """
    base = g.base
    messages = base.get_conversation_history(convo)
    summary = base.get_conversation_summaries(convo)["short_summary"]
    markdown = ""
    for message in messages:
        if message["role"] == "system":
            markdown += title + "\n\n"
            markdown += model + "\n\n"
        elif message["role"] == "user":
            markdown += f"**User:** {message['content']}\n\n"
        elif message["role"] == "assistant":
            markdown += f"**Assistant:** {message['content']}\n\n"
    filename = f"{summary}.md"
    path = "static/markdown/"
    path_filename = path + filename
    with open(path_filename, "w") as f:
        f.write(markdown)
    return path_filename


def random_filename(ext: str, start_str: str = "") -> str:
    """
    Generate a random filename with the given extension.

    Parameters:
        ext (str): The extension of the filename.
        start_str (str): The starting string of the filename.

    Returns:
        str: A random filename with the given extension.
    """
    return (
        start_str
        + "".join(random.choices(string.ascii_letters + string.digits, k=16))
        + ext
    )


def qr_code_generator(text: str, filename: str) -> Path:
    """
    Generate a QR code with the given text.

    Parameters:
        text (str): The text to encode in the QR code.

    Returns:
        str: The filename of the generated QR code.
    """

    qr_img = qrcode.make(text)
    if not Path("static/qr/").exists():
        Path("static/qr/").mkdir(parents=True, exist_ok=True)
    qr_img.save(f"static/qr/{filename}")
    return Path(f"static/qr/{filename}")

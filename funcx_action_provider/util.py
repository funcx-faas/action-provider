from boto3.session import Session
from botocore.exceptions import ClientError, NoCredentialsError
from datetime import timezone, datetime
import logging
import os
import re

from .config import FXConfig

logger = logging.getLogger(__name__)


class FXUtil(object):
    @staticmethod
    def iso_tz_now(local: bool = False) -> str:
        """
        :param local: Whether the timezone should be localtime.  UTC if False

        Returns an iso8601 compliant, timezone aware timestamp str.
        """
        if local:
            return datetime.now().astimezone().isoformat()
        else:
            return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def get_start(s: str, max_length: int = 8, replace_line_breaks: bool = False):
        """
        :param s: The source str
        :param max_length: How many characters to return, if length exceeds
        :param replace_line_breaks: Whether to replace line breaks with <br>

        Returns the start of a string, with '...' replacing the rest if
         it is longer than max_length.  Can also replace line breaks for
         more single line clarity.  Note a line break counts as one char
        """
        if not s:
            return s
        elif not isinstance(s, str):
            raise ValueError("Input to get_start must be a string")
        elif len(s) <= max_length:
            result = s
        else:
            result = s[:max_length] + '...'

        line_break_replacement = ' <br> '
        if replace_line_breaks:
            return result.replace('\n', line_break_replacement)
        else:
            return result

    @staticmethod
    def sanitize(s: str, show_max_chars: int = 7):
        """
        Obfuscate the input string and only show the last few chars.

        :param s:               Input string
        :param show_max_chars:  Maximum chars to show, rest replaced with '*'
        :return:  The obfuscated string
        """
        if show_max_chars < 0:
            raise ValueError("show_max_chars must be non-negative")
        if len(s) <= show_max_chars:
            return s

        show = '' if show_max_chars == 0 else s[-show_max_chars:]
        hidden_length = len(s) - show_max_chars

        # Show at most 3 *s
        star_chars = '***'
        if hidden_length == 2:
            star_chars = '**'
        elif hidden_length == 1:
            star_chars = '*'
        return star_chars + show

    @staticmethod
    def verify_uuid(uuid):
        """
        Verifies whether the input is valid uuid4 format.
        See https://stackoverflow.com/questions/11384589/what-is-the-correct-regex-for-matching-values-generated-by-uuid-uuid4-hex
        for longer discussion

        :param uuid: Input to be checked
        :return: True if valid
        """

        regex = re.compile(
            '^[a-f\\d]{8}-?[a-f\\d]{4}-?4[a-f\\d]{3}-?[89ab][a-f\\d]{3}-?[a-f\\d]{12}$',
            re.I
        )
        match = regex.match(uuid)
        return bool(match)

    @staticmethod
    def get_client_secret() -> str:
        """Gets the client secret in this order:
            1) Env variable CLIENT_SECRET_ENV
            2) AWS secrets key funcx-action-provider-client

        :return: The client secret, raises exception if not found
        """
        env_client_secret = os.getenv(FXConfig.CLIENT_SECRET_ENV)

        if env_client_secret:
            return env_client_secret

        try:
            client = Session().client(
                service_name='secretsmanager',
                region_name=FXConfig.AWS_REGION,
            )
            secret_value_response = client.get_secret_value(
                SecretId=FXConfig.AWS_SECRET_ID
            )
            return eval(secret_value_response.get('SecretString'))['secret']
        except NoCredentialsError as e:
            raise EnvironmentError(f"AWS credentials error: {e}")
        except ClientError as e:
            raise ValueError(f"Could not locate AWS secret: {e}")
        except Exception as e:
            raise ValueError(f"Unknown error locating client secret: {e}")

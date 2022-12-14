from datetime import timezone, datetime
import logging
import re

from globus_action_provider_tools.data_types import ActionProviderJsonEncoder

logger = logging.getLogger(__name__)


class FXUtil(object):
    @staticmethod
    def iso_tz_now(local: bool = False) -> str:
        """
        :param local: Whether the timezone should be localtime.  UTC if False

        Returns an iso8601 compliant, timezone aware timestamp str.
        """
        if local:
            return datetime.now(timezone.utc).isoformat()
        else:
            return datetime.now().astimezone().isoformat()

    @staticmethod
    def get_start(s, max_length=8, replace_line_breaks=False):
        """
        :param s: The source str
        :param max_length: How many characters to return, if length exceeds
        :param replace_line_breaks: Whether to replace line breaks with <br>

        Returns the start of a string, with '...' replacing the rest if
         it is longer than max_length.  Can also replace line breaks for
         more single line clarity
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
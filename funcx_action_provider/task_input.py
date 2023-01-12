import json
from json.decoder import JSONDecodeError

from .util import FXUtil


class TaskInput:
    def __init__(self, endpoint, function, args, kwargs, check_uuid=True):
        endpoint = endpoint.strip()
        function = function.strip()

        if not endpoint and not function:
            raise ValueError("Endpoint UUID and function UUID must be provided")

        if check_uuid:
            FXUtil.check_uuid(endpoint)
            FXUtil.check_uuid(function)

        self.endpoint_id = endpoint
        self.function_id = function
        self.args = []
        self.kwargs = {}

        if args:
            self.args = FXUtil.parse_item_to_list(args)

        if kwargs:
            # kwargs is much simpler because it must be a dictionary
            if isinstance(kwargs, str):
                kwargs = kwargs.strip()
                if kwargs[0] != '{':
                    raise ValueError("kwargs must be a dict starting with '{'")
                self.kwargs = json.loads(kwargs)
            else:
                assert isinstance(kwargs, dict)
                self.kwargs = kwargs

    def __repr__(self):
        return f"{self.endpoint_id}, {self.function_id}, {self.args}, {self.kwargs}"

    @staticmethod
    def from_request(request_body: dict, check_uuid=True) -> list:
        json_input = request_body.get("tasks")
        endpoint_id = request_body.get("endpoint")
        function_id = request_body.get("function")
        f_args = request_body.get("args")
        f_kwargs = request_body.get("kwargs")
        results = []
        if json_input:
            if isinstance(json_input, str):
                # Input could be a string from UI or elsewhere
                json_input = json.loads(json_input.strip())
            if endpoint_id or function_id:
                raise ValueError("tasks and endpoint/function are exclusive")
            if "endpoint" in json_input and "function" in json_input:
                json_input = [json_input]
            for task_input in json_input:
                results.append(TaskInput(
                    task_input.get("endpoint"),
                    task_input.get("function"),
                    task_input.get("args"),
                    task_input.get("payload") or task_input.get("kwargs"),
                    check_uuid=check_uuid
                ))
        else:
            results.append(TaskInput(
                endpoint_id,
                function_id,
                f_args,
                f_kwargs,
                check_uuid=check_uuid
            ))
            endpoint_2_id = request_body.get("endpoint_2")
            function_2_id = request_body.get("function_2")
            if endpoint_2_id and function_2_id:
                results.append(TaskInput(
                    endpoint_2_id,
                    function_2_id,
                    request_body.get("args_2"),
                    request_body.get("kwargs_2"),
                    check_uuid=check_uuid
                ))

        return results

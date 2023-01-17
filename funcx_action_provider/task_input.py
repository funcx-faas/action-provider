import json
import time

from .config import FXConfig
# from funcx_common.tasks.constants import TaskState, ActorName
from .config import TaskState, ActorName
from .util import FXUtil


class TaskInput:
    def __init__(
        self,
        tg_id,
        endpoint,
        function,
        args,
        kwargs,
        creator_id: str = FXConfig.NOT_AVAILABLE,
        check_uuid: bool = True,
        task_id: str = FXConfig.NOT_AVAILABLE
    ):
        endpoint = endpoint.strip()
        function = function.strip()

        if not endpoint and not function:
            raise ValueError("Endpoint UUID and function UUID must be provided")

        if check_uuid:
            FXUtil.check_uuid(endpoint)
            FXUtil.check_uuid(function)

        self.task_group_id = tg_id
        self.endpoint_id = endpoint
        self.function_id = function
        self.args = []
        self.kwargs = {}

        # For logging
        self.creator_id = creator_id
        self.task_id = task_id

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

    def logging_info(self):
        return {
            "user_id": self.creator_id,
            "task_id": self.task_id,
            "task_group_id": self.task_group_id,
            "function_id": self.function_id,
            "endpoint_id": self.endpoint_id,
            "container_id": FXConfig.NOT_AVAILABLE,
            "actor": ActorName.ACTION_PROVIDER,
            "state_time": time.time_ns(),
            "log_type": "task_transition",
        }

    @staticmethod
    def from_request(request_body: dict, tg_id, user_id, check_uuid=True) -> list:
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
                    tg_id,
                    task_input.get("endpoint"),
                    task_input.get("function"),
                    task_input.get("args"),
                    task_input.get("payload") or task_input.get("kwargs"),
                    creator_id=user_id,
                    check_uuid=check_uuid
                ))
        else:
            results.append(TaskInput(
                tg_id,
                endpoint_id,
                function_id,
                f_args,
                f_kwargs,
                creator_id=user_id,
                check_uuid=check_uuid
            ))
            endpoint_2_id = request_body.get("endpoint_2")
            function_2_id = request_body.get("function_2")
            if endpoint_2_id and function_2_id:
                results.append(TaskInput(
                    tg_id,
                    endpoint_2_id,
                    function_2_id,
                    request_body.get("args_2"),
                    request_body.get("kwargs_2"),
                    creator_id=user_id,
                    check_uuid=check_uuid
                ))

        return results

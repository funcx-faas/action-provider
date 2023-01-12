import pytest

from funcx_action_provider.task_input import TaskInput


class TestTaskInput:
    @pytest.mark.parametrize(
        "input_values",
        [
            [
                {"tasks":
                    [
                         {
                             "endpoint": "e1",
                             "function": "f1",
                             "payload": {"abc": 1, 2: 5, 3: 4}
                         }
                    ],
                 }, 1, [["e1", "f1", 0, 3, 0]]
            ],
            [
                {"tasks":
                    [
                        {
                            "endpoint": "e1",
                            "function": "f1",
                            "args": [1, 2, 3],
                        },
                        {
                            "endpoint": "e2",
                            "function": "f2",
                            "args": [99, 2, 3],
                            "kwargs": {"abc": 1, 2: 3, 4: 5}
                        }
                    ],
                 },
                2,
                [
                    ["e1", "f1", 3, 0, 1],
                    ["e2", "f2", 3, 3, 99],
                ]
            ],
            [
                {
                    "endpoint": "e1",
                    "function": "f1",
                    "args": [1, 2, 3],
                    "kwargs": {"abc": 1, 2: 3, 4: 5}
                },
                1,
                [
                    ["e1", "f1", 3, 3, 1],
                ]
            ],
            [
                {
                    "endpoint": "e1",
                    "function": "f1",
                    "args": [1, 2, 3],
                    "kwargs": {"abc": 1, 2: 3, 4: 5},
                    "endpoint_2": "e2",
                    "function_2": "f2",
                    "args_2": [4, 2, 3],
                    "kwargs_2": {"abc": 1, 2: 3, 4: 5}
                },
                2,
                [
                    ["e1", "f1", 3, 3, 1],
                    ["e2", "f2", 3, 3, 4],
                ]
            ],
            [
                {
                    "endpoint": "e1",
                    "function": "f1",
                    "args": "31x",
                    "kwargs": None
                },
                1,
                [
                    ["e1", "f1", 1, 0, "31x"],
                ]
            ],
            [
                {
                    "endpoint": "e1",
                    "function": "f1",
                    "args": 31.1,
                    "kwargs": None
                },
                1,
                [
                    ["e1", "f1", 1, 0, 31.1],
                ]
            ],
        ]
    )
    def test_from_request(self, input_values):
        body, num_inputs, inputs = input_values

        processed = TaskInput.from_request(body, check_uuid=False)

        assert num_inputs == len(processed)
        for i in range(num_inputs):
            e_id, f_id, num_args, num_kwargs, first_arg = inputs[i]
            assert processed[i].endpoint_id == e_id
            assert processed[i].function_id == f_id
            if num_args == 0:
                assert not processed[i].args
            else:
                assert num_args == len(processed[i].args)
                assert first_arg == processed[i].args[0]
            if num_kwargs == 0:
                assert not processed[i].kwargs
            else:
                if num_kwargs != len(processed[i].kwargs):
                    assert str(num_kwargs) + str(body) == str(processed[i])




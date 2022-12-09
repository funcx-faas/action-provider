class FuncXDirectorySchema:
    endpoint: str
    function: str
    payload: object

    class Config:
        title = "FuncX Action Provider Schema"
        schema_extra = {
            "example": {
                "endpoint": "12345678-abcd-1234-4567-abcdeabcdeab",
                "function": "12345678-abcd-1234-1234-abcdeabcdeab",
                "payload": "{'first_number': 1, 'second_number': 2}",
            },
        }

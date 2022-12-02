class FuncXDirectorySchema:
    endpoint_uuid: str
    function_uuid: str
    function_arguments: str

    class Config:
        title = "FuncX Action Provider Schema"
        schema_extra = {
            "example": {
                "endpoint_uuid": "12345678-abcd-1234-4567-abcdeabcdeab",
                "function_uuid": "12345678-abcd-1234-1234-abcdeabcdeab",
                "function_arguments": "{'first_number': 1, 'second_number': 2}",
            }
        }
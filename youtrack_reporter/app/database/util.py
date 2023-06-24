# import functools

# from pydantic import BaseModel, root_validator, ValidationError
# from typing import Dict, Any, Optional
# from datetime import datetime

# def check_empty_strings(data: Dict[str, Any]):

#     names = []
#     for name, value in data.items():
#         if isinstance(value, str):
#             if len(value) == 0:
#                 names.append(name)

#     return names


# class PydanticBaseModel(BaseModel):
#     @root_validator
#     def check_empty_strings(cls, data: Dict[str, Any]):

#         names = check_empty_strings(data)
#         if not names:
#             return data

#         raise ValidationError(
#             [
#                 {
#                     "loc": names,
#                     "msg": "Empty strings not allowed",
#                     "type": "value_error.string_empty",
#                 }
#             ],
#         )
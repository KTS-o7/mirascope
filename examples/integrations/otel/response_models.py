from pydantic import BaseModel

from mirascope.core import openai
from mirascope.integrations.otel import configure, with_otel

configure()


class Book(BaseModel):
    title: str
    author: str


@with_otel()
@openai.call(model="gpt-4o-mini", response_model=Book)
def recommend_book(genre: str) -> str:
    return f"Recommend a {genre} book."


print(recommend_book("fantasy"))

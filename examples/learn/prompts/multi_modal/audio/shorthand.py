from pydub import AudioSegment

from mirascope.core import prompt_template, Messages, openai


@prompt_template()
def identify_book_prompt(audio_mp3: AudioSegment) -> Messages.Type:
    return ["Here's an audio book snippet:", audio_mp3, "What book is this?"]


with open("....", "rb") as audio:
    print(identify_book_prompt(AudioSegment.from_mp3(audio)))
# Output: [
#     BaseMessageParam(
#         role="user",
#         content=[
#             TextPart(type="text", text="Here's an audio book snippet:"),
#             AudioPart(type='audio', media_type='audio/wav', audio=b'...'),
#             TextPart(type="text", text="What book is this?"),
#         ],
#     )
# ]

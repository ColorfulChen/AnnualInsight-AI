from google import genai
from google.genai import types
from dotenv import load_dotenv
import os
import io

load_dotenv()
apikey = os.getenv("GOOGLE_API_KEY")
model_name_base = os.getenv("MODEL_NAME")

def chat(prompt):
    client = genai.Client(
        api_key=apikey,
    )
    response = client.models.generate_content(
        model="gemini-2.0-flash", contents=prompt
    )
    print(response.text)
    return response.text

def upload_pdf(file_path):
    client = genai.Client()
    with open(file_path, 'rb') as f:
        doc_io = io.BytesIO(f.read())

    document = client.files.upload(
    file=doc_io,
    config=dict(mime_type='application/pdf')
    )

    model_name = model_name_base
    system_instruction = "You are an expert analyzing transcripts."

    # Create a cached content object
    cache = client.caches.create(
        model=model_name,
        config=types.CreateCachedContentConfig(
        system_instruction=system_instruction,
        contents=[document],
        )
    )

    # Display the cache details
    print(f'{cache=}')

    # Generate content using the cached prompt and document
    response = client.models.generate_content(
    model=model_name,
    contents="Please summarize this transcript",
    config=types.GenerateContentConfig(
        cached_content=cache.name
    ))

    # (Optional) Print usage metadata for insights into the API call
    print(f'{response.usage_metadata=}')

    # Print the generated text
    print('\n\n', response.text)

if __name__ == "__main__":
    upload_pdf('_annualReport\铂力特_西安铂力特增材技术股份有限公司2024年年度报告(修订版).pdf')
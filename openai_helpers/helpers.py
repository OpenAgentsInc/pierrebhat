from openai.embeddings_utils import get_embedding, cosine_similarity
import openai
import numpy as np
import os

MAX_CONTENT_LENGTH = 8191
EMBED_DIMS = 1536
MODEL_EMBED = 'text-embedding-ada-002'
MODEL_COMPLETION = 'code-davinci-002'

openai.api_key = os.getenv("OPENAI_API_KEY")

# Helpers
def embed(text):
    if isinstance(text, list):
        for i, t in enumerate(text):
            text[i] = t.replace("\n", " ")
            if len(text[i]) > MAX_CONTENT_LENGTH:
                text[i] = text[i][0:MAX_CONTENT_LENGTH]
        embeddings = openai.Embedding.create(input=text, model=MODEL_EMBED)["data"]
        return np.array([np.array(embedding['embedding'], dtype=np.float32) for embedding in embeddings])
    else:
        text = text.replace("\n", " ")
        if len(text) > MAX_CONTENT_LENGTH:
            text = text[0:MAX_CONTENT_LENGTH]
        return np.array(openai.Embedding.create(input=[text], model=MODEL_EMBED)["data"][0]["embedding"], dtype=np.float32)

def compare_embeddings(embed1, embed2):
    return cosine_similarity(embed1, embed2)

def compare_text(text1, text2):
    return compare_embeddings(embed(text1), embed(text2))

def complete(prompts):
    results = openai.Completion.create(
        engine=MODEL_COMPLETION,
        prompt=prompts,
        max_tokens=100,
        temperature=0.2,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0.6,
        stop=[])

    return results['choices'][0]['text']
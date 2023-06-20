import os
import openai
import streamlit as st
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import QueryType

# Replace these with your own values, either in environment variables or directly here
AZURE_STORAGE_ACCOUNT = os.environ.get("AZURE_STORAGE_ACCOUNT") or "mystorageaccount"
AZURE_STORAGE_CONTAINER = os.environ.get("AZURE_STORAGE_CONTAINER") or "content"
AZURE_SEARCH_SERVICE = "aicogsearch"
AZURE_SEARCH_INDEX = "azuresql-index"
AZURE_OPENAI_SERVICE = "ava-oai"
AZURE_OPENAI_GPT_DEPLOYMENT =  "chat-model1"
AZURE_OPENAI_CHATGPT_DEPLOYMENT = "chat-model1"

KB_FIELDS_CONTENT =  "content"
KB_FIELDS_CATEGORY = "category"
KB_FIELDS_SOURCEPAGE = "sourcepage"

# Use the current user identity to authenticate with Azure OpenAI, Cognitive Search and Blob Storage (no secrets needed, 
# just use 'az login' locally, and managed identity when deployed on Azure). If you need to use keys, use separate AzureKeyCredential instances with the 
# keys for each service
azure_credential = AzureKeyCredential("eBmGqM94MA30rEbz0BsfH6tWNak5bI4mfDBLGDOZFWAzSeDhJVgn")

# Used by the OpenAI SDK
openai.api_type = "azure"
openai.api_base = f"https://api.openai.com"
openai.api_base = f"https://{AZURE_OPENAI_SERVICE}.openai.azure.com"
openai.api_version = "2022-12-01"

# Comment these two lines out if using keys, set your API key in the OPENAI_API_KEY environment variable instead
#openai.api_type = "azure_ad"
openai.api_key ="a2867b0cec2e47bc9f991d2abe375cc7"
st.title("Prathap GPT with Cog Search Demo on Azure SQL")
selectedIndex = st.selectbox("Data source: ",
                     ['myindex1', 'myindex1'])

def loadSqlIndex():
    search_client = SearchClient(
        endpoint=f"https://{AZURE_SEARCH_SERVICE}.search.windows.net",
        index_name="azuresql-index",
        credential=azure_credential)
    r = search_client.search("", top=5)
    results = [doc for doc in r]
    return results


def loadDocumentIndex():
    search_client = SearchClient(
        endpoint=f"https://{AZURE_SEARCH_SERVICE}.search.windows.net",
        index_name="myindex1",
        credential=azure_credential)
    r = search_client.search("", top=5)
    results = [doc[KB_FIELDS_SOURCEPAGE] + ": " + doc[KB_FIELDS_CONTENT].replace("\n", "").replace("\r", "") for doc in r]
    return results

user_input = st.text_input("enter your Query here")

# Set up clients for Cognitive Search and Storage
# search_client = SearchClient(
#     endpoint=f"https://{AZURE_SEARCH_SERVICE}.search.windows.net",
#     index_name=selectedIndex,
#     credential=azure_credential)

prompt_prefix = """<|im_start|>system
How may i help you 
Sources:
{sources}

<|im_end|>"""

turn_prefix = """
<|im_start|>user
"""

turn_suffix = """
<|im_end|>
<|im_start|>assistant
"""

prompt_history = turn_prefix

history = []

summary_prompt_template = """Below is a summary of the conversation so far, and a new question asked by the user that needs to be answered by searching in a knowledge base. Generate a search query based on the conversation and the new question. Source names are not good search terms to include in the search query.

Summary:
{summary}

Question:
{question}

Search query:
"""
# Execute this cell multiple times updating user_input to accumulate chat history


# Exclude category, to simulate scenarios where there's a set of docs you can't see
exclude_category = None

if len(history) > 0:
    completion = openai.Completion.create(
        engine=AZURE_OPENAI_GPT_DEPLOYMENT,
        prompt=summary_prompt_template.format(summary="\n".join(history), question=user_input),
        temperature=0.7,
        max_tokens=32,
        stop=["\n"])
    search = completion.choices[0].text
else:
    search = user_input

# Alternatively simply use search_client.search(q, top=3) if not using semantic search
print("Searching:", search)
print("-------------------")
filter = "category ne '{}'".format(exclude_category.replace("'", "''")) if exclude_category else None
# r = search_client.search(search, 
#                          filter=filter,
#                          query_type=QueryType.FULL, 
#                          query_language="en-us", 
#                          query_speller="lexicon", 
#                          semantic_configuration_name="default", 
#                          top=3)
# r = search_client.search("", top=10)
# results = [doc for doc in r]
# results = [doc[KB_FIELDS_SOURCEPAGE] + ": " + doc[KB_FIELDS_CONTENT].replace("\n", "").replace("\r", "") for doc in r]
results = "Consider Below Data for Payments Summary \n {} End of Payments Summary Data\n  Start of employee hand Book Data \n {} End of Employee hand book data \n"
# results = "Consider Below Data for Payments Summary \n"+ loadSqlIndex() + "End of Payments Summary Data\n  Start of employee hand Book Data \n"+loadDocumentIndex()+" End of Employee hand book data \n"
content = results.format(loadSqlIndex(),loadDocumentIndex()) #"\n".join(results)

prompt = prompt_prefix.format(sources=content) + prompt_history + user_input + turn_suffix

completion = openai.Completion.create(
    engine=AZURE_OPENAI_CHATGPT_DEPLOYMENT, 
    prompt=prompt, 
    temperature=0.7, 
    max_tokens=1024,
    stop=["<|im_end|>", "<|im_start|>"])

prompt_history += user_input + turn_suffix + completion.choices[0].text + "\n<|im_end|>" + turn_prefix
history.append("user: " + user_input)
history.append("assistant: " + completion.choices[0].text)
st.write(completion.choices[0].text)
# print("\n-------------------\n".join(history))
# print("\n-------------------\nPrompt:\n" + prompt)


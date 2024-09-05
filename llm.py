from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.schema import StrOutputParser
from langchain.schema.runnable import RunnablePassthrough
from dotenv import load_dotenv

load_dotenv()

# Initialize the GPT models
gpt3 = ChatOpenAI(
    temperature=0.2,
    streaming=True,
    verbose=True
)

gpt4 = ChatOpenAI(
    model='gpt-4',
    temperature=0.2,
    streaming=True,
    verbose=True
)

# Define the prompt templates
cds_helper_ddx_prompt = PromptTemplate.from_template(
    """##DDX model
Based on the provided transcript snippets from a doctor-patient consultation, parse the information to generate a differential diagnosis. The results should be organized as follows:
Differential Diagnosis: List each possible diagnosis with a model confidence score from 0-100 (example: [30]), 100 being most confident.
Please consider the patient's stated symptoms, their medical history, and any other relevant information presented in the transcript. The consultation snippets are as follows:

{transcript}
Differential Diagnosis:
"""
)

clinical_note_writer_template = PromptTemplate.from_template(
    """Based on the conversation transcript and doctor's hints provided below, generate a clinical note in the following format:
Diagnosis:
History of Presenting Illness:
Medications (Prescribed): List current medications and note if they are being continued, or if any new ones have been added.
Lab Tests (Ordered):
Please consider any information in the transcript that might be relevant to each of these sections, and use the doctor's hint as a guide.

### Example
Conversation Transcript:
Patient: "I've been taking the Glycomet-GP 1 as you prescribed, doctor, but I'm still feeling quite unwell. My blood pressure readings are all over the place and my sugar levels are high."
Doctor: "I see, we may need to adjust your medications. Let's add Jalra-OD and Telmis to your regimen and see how you respond."
Doctor's Hint: The patient has uncontrolled diabetes and hypertension despite adherence to the Glycomet-GP 1.
Clinical Note:
Diagnosis: Uncontrolled Diabetes and Hypertension
History of Presenting Illness: The patient has been adhering to their current medication regimen but the diabetes and hypertension seem uncontrolled.
Medications (Prescribed):
[Continue] Glycomet-GP 1 (tablet) | Glimepiride and Metformin
[Added] Jalra-OD 100mg (tablet) | Vildagliptin
[Added] Telmis 20 (Tablet)
Lab Tests (Ordered): None
Now, based on the following conversation and hints, please generate a clinical note:

### Conversation Transcript
{transcript}

### Doctor's Hint
{input}
"""
)

# Define the chains using Runnable sequence
cds_helper_ddx = (
    RunnablePassthrough.assign(transcript=lambda x: x["transcript"])
    | cds_helper_ddx_prompt
    | gpt4
    | StrOutputParser()
)

clinical_note_writer = (
    RunnablePassthrough.assign(transcript=lambda x: x["transcript"])
    | RunnablePassthrough.assign(input=lambda x: x["input"])
    | clinical_note_writer_template
    | gpt4
    | StrOutputParser()
)
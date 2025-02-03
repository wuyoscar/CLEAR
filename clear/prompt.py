
from pdf2image import convert_from_path
import io
import base64

def generate_image_uris_from_pdfs(pdf_paths):
    """
    Convert a list of PDF paths into a list of image URIs.

    Args:
        pdf_paths (list of str): List of PDF file paths.

    Returns:
        list of str: List of image URIs in base64 format.
    """
    def convert_doc_to_images(path):
        return convert_from_path(path)

    def get_img_uri(img):
        png_buffer = io.BytesIO()
        img.save(png_buffer, format="PNG")
        png_buffer.seek(0)
        base64_png = base64.b64encode(png_buffer.read()).decode('utf-8')
        return f"data:image/png;base64,{base64_png}"

    all_image_uris = []
    for pdf_path in pdf_paths:
        try:
            images = convert_doc_to_images(pdf_path)
            all_image_uris.extend(get_img_uri(img) for img in images)
        except Exception as e:
            print(f"Error processing {pdf_path}: {e}")

    return all_image_uris


def generate_query_prompt(query):
    alpaca_prompt = """Below is an instruction that describes a task, paired with an input that provides further context. Your response must be a valid JSON object, strictly following the requested format.

### Instruction:
{}

### Input:
{}

### Response (valid JSON only):
{}
"""
    instruction = (
        "Extract location, topics, and search queries from Australian climate policy questions. "
        "Your response must be a valid JSON object with the following structure:\n\n"
        "{\n"
        '  "rag_queries": ["query1", "query2", "query3"],  // 1-3 policy search queries\n'
        '  "topics": ["topic1", "topic2", "topic3"],       // 1-3 climate/environment topics\n'
        '  "location": {                                   // Location details\n'
        '    "query_suburb": "suburb_name or null",\n'
        '    "query_state": "state_code or null",\n'
        '    "query_lga": "lga_name or null"\n'
        '  }\n'
        "}\n\n"
        "Notes:\n"
        "- RAG queries should target policy documents\n"
        "- Topics should focus on climate and environmental concerns\n"
        "- Location fields should be null if not specified in input\n"
        "- Response must be valid JSON only, no additional text or formatting"
    )
    return alpaca_prompt.format(instruction,query,"")







def extract_title_and_link(data):
    return {
        "title": data.get("title"),
        "link": data.get("link")
    }
def section_community_analysis_prompt(data_obj, text_obj):
    censue_lga_reference = f"The 2021 Census data for {data_obj['suburb_info']['suburb']}, {data_obj['suburb_info']['state']}, can be accessed via the Australian Bureau of Statistics (ABS) website: {data_obj['suburb_info']['censusURL_2021']}"
    censue_sub_reference = f"The 2021 Census data for {data_obj['lga_info']['lga']}, {data_obj['lga_info']['state']}, can be accessed via the Australian Bureau of Statistics (ABS) website: {data_obj['lga_info']['censusURL_2021']}"
    lga_wiki_var_reference = extract_title_and_link(text_obj['page_var']['lga_wiki_var_reference'])
    suburb_wiki_var_reference = extract_title_and_link(text_obj['page_var']['suburb_wiki_var_reference'])
    
    community_context_prompt = f"""
From the user query {data_obj['user_query']} and provided data, create a comprehensive community analysis for residents in suburb of {data_obj['suburb_info'].get('suburb_name', None)} supervised by local government {data_obj['lga_info'].get('lga', None)}.

##Community Level Info 

### 1. Geographic and Demographic Overview
#### Input Data:
- **Suburb Wikipedia Data**: {text_obj['page_var'].get('suburb_wiki_var', 'No Wikipedia information available')}
- **Local Government Wikipedia Data**: {text_obj['page_var'].get('lga_wiki_var', 'No Wikipedia information available')}

#### Required Insights:
- **Location and Significance**: Describe the geographic importance of the suburb and its relevance to the region.
- **Demographic Snapshot**: Provide a concise demographic summary (e.g., population, age distribution, economic activity).
- **Environmental Characteristics**: Highlight key environmental features (e.g., coastal areas, bushfire zones, biodiversity).

---
   
### 2. Local Government Area ({data_obj['lga_info'].get('lga', None)}) Analysis
#### Input Data:
- **Census Information**: {text_obj['page_var'].get('lga_census_var', 'No Census information available')}

#### Required Insights:
- **Population and Infrastructure**:
  - Assess vulnerabilities (e.g., socio-economic, disaster-prone areas).
  - Analyze infrastructure capacity (e.g., housing, transport, utilities).
  - Evaluate emergency preparedness measures.
  
- **Sustainability and Resilience**:
  - Review current sustainability programs and policies.
  - Identify resilience factors (e.g., community engagement, adaptive capacity).
  - Assess the capacity for future climate adaptation.

---

### 3. Data Presentation
#### Requirements:
- Present insights using **markdown tables** with captions for each table.
- Include **state/regional comparisons** to contextualize local data.
- Highlight trends and climate-relevant impacts (e.g., flood risks, emissions).
- Format statistics consistently (e.g., numbers with percentages).
- Provide **clear labels** for all indicators and values.
- You can generate more tables as many as you need 

#### Example Table Format:
| Indicator                | Local Value | Regional Average | Impact Level  |
|--------------------------|-------------|------------------|---------------|
| Population Density       | X people/km² | Y people/km²    | Moderate      |
| Households with Solar PV | X%           | Y%              | High          |

**[Table X: Description of the Table]**

---
Please create references based on the following data in the correct format. List them in order, starting with 1, 2, 3:

{suburb_wiki_var_reference}
{lga_wiki_var_reference}
{censue_lga_reference}

---
Remember:
- Keep analysis relevant to climate change impacts
- Maintain clear connection between data and community needs 

"""

    prompt_messages = [
        {
            "role": "system",
            "content": "You are an expert data analyst specializing in Australian community demographics and climate policy. Your task is to analyze and present community-level information in a clear, structured format. Your analysis should provide actionable, data-driven insights relevant to climate resilience and community development."
        },
        {
            "role": "user",
            "content": community_context_prompt
        }
    ]

    return prompt_messages



def section_topic_question_prompt(data_obj, text_obj, image_uris):
    document_analysis_prompt = [
        {
            "role": "system",
            "content": """You are an expert Australian policy and community analyst to summary policy iamge docuement and answer user question according to those government image document"""
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": f"""Analyze the provided policy documents for {data_obj['lga_info'].get('lga', None)} focusing on both specific topics and user questions.

    BACKGROUND:
    Resident Location: {data_obj['suburb_info'].get('suburb_name', None)}, {data_obj['lga_info'].get('lga', None)}
    Key Topics: {' '.join(data_obj['query_extraction']['topics'])}
    Questions: {' '.join(data_obj['query_extraction']['rag_queries'])}


    Required Analysis Structure:
    ## LGA Policy Document Analysis
    
    ### 1.Topic-Specific Analysis
    For each identified topic:
    #### [Topic Name]
    - Current Status and Programs
    - Local Implementation Details
    - Future Plans and Timeline

    ### 2.Document QA Analysis
    For each question:
    #### [Question Number]: [Question]
    - Evidence Found (with exact quotes and page numbers)
    - OR No Evidence Found (with explanation)

    ### 3.Information Gaps
    - Assess whether the provided policy documents sufficiently address the resident's concerns, as outlined in their query: "{data_obj['user_query']}". Identify missing information, unclear areas, or additional clarifications required to fully resolve their questions from their perspective.

    Requirements:
    1. Use exact document references
    2. Connect findings to local context
    3. Focus on practical implications
    4. Discuss how the resident's needs align with the government's focus, highlighting any gaps or misalignments in the Information Gaps section.

    Present all findings in clear markdown format."""
                }
            ] + [
                {
                    "type": "image_url",
                    "image_url": {"url": image_uri}}
                for image_uri in image_uris
            ],
        }
    ]
    return document_analysis_prompt

def email_report_prompt(data_obj, text_obj, document_analysis_text):
    email_report_template = f"""
    ## Background
    A resident has requested information from the Australian local government regarding climate change risks in their area.

    ### Key Details:
    - **Resident Query**: {data_obj['user_query']}
    - **Key Topics of Interest**: {', '.join(data_obj['query_extraction']['topics'])}
    - **Location**: Suburb of {data_obj['suburb_info']['suburb']}, {data_obj['lga_info']['lga']}

    ### Current Analysis Summary:
    - **Available Analyses**: {document_analysis_text}
    - **Identified Information Gaps**:
    - Explain why gaps exist between the government and resident information.
    - Highlight areas where documentation or clarity is missing.

    ---

    ## Email to Council

    **To**: {data_obj['lga_info']['govEmail']}  
    **Subject**: Information Request: Climate Policy Query for {data_obj['suburb_info']['suburb']} Resident  

    Dear {data_obj['lga_info']['lga']} Council,

    I am a resident of {data_obj['suburb_info']['suburb']} seeking further information about climate policies and initiatives relevant to our community.

    After reviewing available resources, I have identified the following gaps:
    [List specific gaps from the analysis]

    My primary areas of interest include:
    [Reference key user query and missing information from your analysis]

    **Original Query**: {data_obj['user_query']}

    I kindly request the following:
    1. [Specific request based on the identified gaps]
    2. [Additional information or data related to resident concerns]
    3. [Any relevant documentation or reports not publicly available]

    Your support in addressing these questions will help enhance community awareness and resilience.

    Thank you for your attention and assistance. I look forward to your response.

    Best regards,  
    [Resident Name]  

    ---

    ### Requirements:
    1. Maintain a professional yet personal tone in the email.
    2. Reference specific gaps from the analysis clearly and concisely.
    3. Ensure alignment between the user’s original query and the requests in the email.
    4. Focus on actionable and relevant information requests.
    """


    email_report_prompt = [
        {
            "role": "system",
            "content": """You are an expert climate policy analyst specializing in Australian local government reporting. Your task is to integrate analyses into clear, actionable, and data-driven reports for residents. These reports should bridge the information gap between residents and the government by:
    1. Highlighting identified gaps in existing government information.
    2. Clearly addressing the resident’s original query and concerns.
    3. Formulating a cohesive and professional email template for the resident to send to their local government, ensuring actionable requests are included."""
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": email_report_template,
                }
            ] 
        }
    ]
    return email_report_prompt



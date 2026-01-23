PROMPTS = {
    1: "More and more people use computers, but not everyone agrees that this benefits society. Write a letter to your local newspaper stating your opinion on the effects computers have on people. Persuade the readers to agree with you.",
    2: "Censorship in the Libraries: Some people believe that certain materials, such as books, music, movies, magazines, etc., should be removed from the shelves if they are found offensive. Write a persuasive essay to a newspaper reflecting your views on censorship in libraries.",
    3: "Write a response that explains how the features of the setting affect the cyclist. In your response, include examples from the essay that support your conclusion.",
    4: "Read the article 'Winter Hibiscus' by Minfong Ho. Based on the article, describe the challenges the mother faces in the new country.",
    5: "Describe the mood created by the author in the memoir. Support your answer with relevant and specific information from the memoir.",
    6: "Based on the excerpt, describe the obstacles the builders of the Empire State Building faced in attempting to allow dirigibles to dock there. Support your answer with relevant and specific information from the excerpt.",
}

RUBRIC_PROMPTS_1_2 = [
    {
        "name": "Content",
        "levels": [
            {
                "score": 1,
                "definition": "The writing lacks a central idea or purpose. Ideas are extremely limited or unclear, with attempts at development that are minimal or nonexistent.",
            },
            {
                "score": 2,
                "definition": "Main ideas and purpose are somewhat unclear or development is attempted but minimal. Details are irrelevant, repetitive, or insufficient.",
            },
            {
                "score": 3,
                "definition": "The reader can understand the main ideas, although they may be overly broad or simplistic. Supporting detail is often limited, insubstantial, or occasionally off-topic.",
            },
            {
                "score": 4,
                "definition": "The writing is clear and focused. The reader can easily understand the main ideas. Support is present, though may be overly general or limited in places.",
            },
            {
                "score": 5,
                "definition": "The writing is clear, focused, and interesting. Main ideas stand out and are developed by supporting details suitable to audience and purpose.",
            },
            {
                "score": 6,
                "definition": "The writing is exceptionally clear, focused, and interesting. It holds the reader's attention throughout with strong support and rich details.",
            },
        ],
    },
    {
        "name": "Organization",
        "levels": [
            {
                "score": 1,
                "definition": "The essay is awkward and fragmented. Ideas are not self-contained and there is no clear structure.",
            },
            {
                "score": 2,
                "definition": "Shows little or no evidence of organization. The writing lacks coherent structure.",
            },
            {
                "score": 3,
                "definition": "The essay shows some organization. Ideas may not be fully self-contained. Form may not match the expected format.",
            },
            {
                "score": 4,
                "definition": "The essay shows satisfactory organization. Contains a basic introduction, body, and conclusion.",
            },
            {
                "score": 5,
                "definition": "The essay shows good organization. There is a flow of ideas, though they may not be completely self-contained.",
            },
            {
                "score": 6,
                "definition": "The essay is well-organized. There is a clear flow of ideas with each idea self-contained. Has appropriate form for the task.",
            },
        ],
    },
    {
        "name": "Word Choice",
        "levels": [
            {
                "score": 1,
                "definition": "The writing shows extremely limited vocabulary or words are misused so meaning is obscured. Words do not fit the text and seem imprecise or inadequate.",
            },
            {
                "score": 2,
                "definition": "Language is monotonous and/or misused, detracting from meaning and impact. Words are flat, colorless, or imprecise with repetitive patterns.",
            },
            {
                "score": 3,
                "definition": "Language lacks precision and variety, or may be inappropriate in places. Writing uses familiar but generic words that rarely capture reader interest.",
            },
            {
                "score": 4,
                "definition": "Words effectively convey the intended message. Writer employs functional words appropriate to audience and purpose, though not particularly energizing.",
            },
            {
                "score": 5,
                "definition": "Words convey the intended message in an interesting, precise, and natural way. Writer employs a broad range of carefully chosen words.",
            },
            {
                "score": 6,
                "definition": "Words convey the intended message in an exceptionally interesting, precise, and natural way. Rich, broad vocabulary with words carefully placed for impact.",
            },
        ],
    },
    {
        "name": "Sentence Fluency",
        "levels": [
            {
                "score": 1,
                "definition": "The writing is difficult to follow or read aloud. Sentences are incomplete, rambling, or irregular with confusing word order.",
            },
            {
                "score": 2,
                "definition": "The writing tends to be choppy or rambling. Awkward constructions force rereading. Sentence patterns are monotonous.",
            },
            {
                "score": 3,
                "definition": "The writing tends to be mechanical rather than fluid. Some passages invite reading while others are awkward. Some variety in structure exists.",
            },
            {
                "score": 4,
                "definition": "The writing flows, though connections between phrases may be less than fluid. Sentence patterns are somewhat varied, contributing to ease in reading.",
            },
            {
                "score": 5,
                "definition": "The writing has an easy flow and rhythm. Sentences are carefully crafted with strong and varied structure that makes reading enjoyable.",
            },
            {
                "score": 6,
                "definition": "The writing has an effective flow and rhythm. Sentences show a high degree of craftsmanship with consistently strong and varied structure.",
            },
        ],
    },
    {
        "name": "Conventions",
        "levels": [
            {
                "score": 1,
                "definition": "Numerous errors in usage, spelling, capitalization, and punctuation repeatedly distract the reader. The severity and frequency of errors make the text difficult to read.",
            },
            {
                "score": 2,
                "definition": "The writing demonstrates little control of standard conventions. Frequent, significant errors impede readability.",
            },
            {
                "score": 3,
                "definition": "The writing demonstrates limited control of standard conventions. Errors begin to impede readability with frequent spelling or grammar mistakes.",
            },
            {
                "score": 4,
                "definition": "The writing demonstrates control of standard conventions. Significant errors do not occur frequently. Minor errors do not impede readability.",
            },
            {
                "score": 5,
                "definition": "The writing demonstrates strong control of standard conventions. Errors are few and minor. Conventions support readability.",
            },
            {
                "score": 6,
                "definition": "The writing demonstrates exceptionally strong control of standard conventions and uses them effectively to enhance communication.",
            },
        ],
    },
]

RUBRIC_PROMPTS_3_6 = [
    {
        "name": "Content",
        "levels": [
            {
                "score": 0,
                "definition": "The response is irrelevant, incorrect, or incomplete.",
            },
            {
                "score": 1,
                "definition": "The response may lack information or evidence showing a lack of understanding of the text.",
            },
            {
                "score": 2,
                "definition": "The response addresses some of the points. Evidence from the story supporting those points is present.",
            },
            {
                "score": 3,
                "definition": "The response answers the question asked. Sufficient evidence from the story is used to support points the writer makes.",
            },
        ],
    },
    {
        "name": "Prompt Adherence",
        "levels": [
            {
                "score": 0,
                "definition": "The response does not address the prompt at all.",
            },
            {
                "score": 1,
                "definition": "The response shows a misreading of the text or question, or consistently wanders off topic.",
            },
            {
                "score": 2,
                "definition": "The response shows a good understanding of the meaning of the text and question, though occasionally wanders off topic.",
            },
            {
                "score": 3,
                "definition": "The response shows an excellent understanding of the meaning of the text and question, and stays on topic.",
            },
        ],
    },
    {
        "name": "Language",
        "levels": [
            {
                "score": 0,
                "definition": "The response has severe language issues that make it incomprehensible.",
            },
            {
                "score": 1,
                "definition": "The response has significant language errors that interfere with understanding.",
            },
            {
                "score": 2,
                "definition": "The response has some language errors but they do not significantly interfere with understanding.",
            },
            {
                "score": 3,
                "definition": "The response demonstrates strong command of language with few or no errors.",
            },
        ],
    },
    {
        "name": "Narrativity",
        "levels": [
            {
                "score": 0,
                "definition": "The response lacks any narrative structure or coherence.",
            },
            {
                "score": 1,
                "definition": "The response has minimal narrative structure with poor coherence.",
            },
            {
                "score": 2,
                "definition": "The response has adequate narrative structure with reasonable coherence.",
            },
            {
                "score": 3,
                "definition": "The response has strong narrative structure with excellent coherence and flow.",
            },
        ],
    },
]


def get_rubric(essay_set: int) -> list:
    if essay_set in (1, 2):
        return RUBRIC_PROMPTS_1_2
    elif essay_set in (3, 4, 5, 6):
        return RUBRIC_PROMPTS_3_6


def get_prompt(essay_set: int) -> str:
    return PROMPTS[essay_set]


def get_trait_names(essay_set: int) -> list[str]:
    rubric = get_rubric(essay_set)
    return [trait["name"] for trait in rubric]

from collections.abc import Sequence

TemplateLevel = dict[str, int | str]
TemplateCriterion = dict[str, str | list[TemplateLevel]]
TemplateDefinition = dict[str, str | list[TemplateCriterion]]


RUBRIC_TEMPLATES: list[TemplateDefinition] = [
    {
        "key": "smarter-balanced-elementary-opinion",
        "name": "Elementary Opinion Writing (Grades 3-5)",
        "description": (
            "Smarter Balanced Assessment Consortium opinion writing rubric aligned "
            "with Common Core standards for grades 3-5."
        ),
        "criteria": [
            {
                "name": "Organization/Purpose",
                "levels": [
                    {
                        "score": 1,
                        "descriptor": (
                            "The response has little or no discernible organizational "
                            "structure. The response may be related to the opinion but "
                            "may provide little or no focus: opinion may be confusing "
                            "or ambiguous; response may be too brief or the focus may "
                            "drift from the purpose and/or audience; few or no "
                            "transitional strategies are evident; introduction and/or "
                            "conclusion may be missing; frequent extraneous ideas may "
                            "be evident; ideas may be randomly ordered or have an "
                            "unclear progression."
                        ),
                    },
                    {
                        "score": 2,
                        "descriptor": (
                            "The response has an inconsistent organizational "
                            "structure. Some flaws are evident, and some ideas may be "
                            "loosely connected. The organization is somewhat sustained "
                            "between and within paragraphs. The response may have a "
                            "minor drift in focus: opinion may be somewhat unclear, or "
                            "the focus may be insufficiently sustained for the purpose "
                            "and/or audience; inconsistent use of transitional "
                            "strategies and/or little variety; introduction or "
                            "conclusion, if present, may be weak; uneven progression "
                            "of ideas from beginning to end; inconsistent or unclear "
                            "connections between and among ideas."
                        ),
                    },
                    {
                        "score": 3,
                        "descriptor": (
                            "The response has an evident organizational structure and "
                            "a sense of completeness. Though there may be minor flaws, "
                            "they do not interfere with the overall coherence. The "
                            "organization is adequately sustained between and within "
                            "paragraphs. The response is generally focused: opinion is "
                            "clear, and the focus is mostly maintained for the purpose "
                            "and audience; adequate use of transitional strategies "
                            "with some variety to clarify relationships between and "
                            "among ideas; adequate introduction and conclusion; "
                            "adequate progression of ideas from beginning to end."
                        ),
                    },
                    {
                        "score": 4,
                        "descriptor": (
                            "The response has a clear and effective organizational "
                            "structure, creating a sense of unity and completeness. "
                            "The organization is sustained between and within "
                            "paragraphs. The response is consistently and purposefully "
                            "focused: opinion is introduced, clearly communicated, and "
                            "the focus is strongly maintained for the purpose and "
                            "audience; consistent use of a variety of transitional "
                            "strategies to clarify the relationships between and among "
                            "ideas; effective introduction and conclusion; logical "
                            "progression of ideas from beginning to end; strong "
                            "connections between and among ideas with some syntactic "
                            "variety."
                        ),
                    },
                ],
            },
            {
                "name": "Evidence/Elaboration",
                "levels": [
                    {
                        "score": 1,
                        "descriptor": (
                            "The response provides minimal elaboration of the "
                            "support/evidence for the opinion and supporting idea(s) "
                            "that includes little or no use of source material. The "
                            "response is vague, lacks clarity, or is confusing: "
                            "evidence (facts and details) from the source material is "
                            "minimal, irrelevant, absent, incorrectly used, or "
                            "predominantly copied; insufficient use of citations or "
                            "attribution to source material; minimal, if any, use of "
                            "elaborative techniques; vocabulary is limited or "
                            "ineffective for the audience and purpose; little or no "
                            "evidence of appropriate style."
                        ),
                    },
                    {
                        "score": 2,
                        "descriptor": (
                            "The response provides uneven, cursory elaboration of the "
                            "support/evidence for the opinion and supporting idea(s) "
                            "that includes partial or uneven use of source material. "
                            "The response develops ideas unevenly, using simplistic "
                            "language: some evidence (facts and details) from the "
                            "source material may be weakly integrated, imprecise, "
                            "repetitive, vague, and/or copied; weak use of citations "
                            "or attribution to source material; weak or uneven use of "
                            "elaborative techniques; development may consist primarily "
                            "of source summary; vocabulary use is uneven or somewhat "
                            "ineffective for the audience and purpose; inconsistent or "
                            "weak attempt to create appropriate style."
                        ),
                    },
                    {
                        "score": 3,
                        "descriptor": (
                            "The response provides adequate elaboration of the "
                            "support/evidence for the opinion and supporting idea(s) "
                            "that includes the use of source material. The response "
                            "adequately develops ideas, employing a mix of precise "
                            "with more general language: adequate evidence (facts and "
                            "details) from the source material is integrated and "
                            "relevant, yet may be general; adequate use of citations "
                            "or attribution to source material; adequate use of some "
                            "elaborative techniques; vocabulary is generally "
                            "appropriate for the audience and purpose; generally "
                            "appropriate style is evident."
                        ),
                    },
                    {
                        "score": 4,
                        "descriptor": (
                            "The response provides thorough and convincing elaboration "
                            "of the support/evidence for the opinion and supporting "
                            "idea(s) that includes the effective use of source "
                            "material. The response clearly and effectively develops "
                            "ideas, using precise language: comprehensive evidence "
                            "(facts and details) from the source material is "
                            "integrated, relevant, and specific; clear citations or "
                            "attribution of source material; effective use of a "
                            "variety of elaborative techniques; vocabulary is clearly "
                            "appropriate for the audience and purpose; effective, "
                            "appropriate style enhances content."
                        ),
                    },
                ],
            },
            {
                "name": "Conventions",
                "levels": [
                    {
                        "score": 0,
                        "descriptor": (
                            "The response demonstrates little or no command of "
                            "conventions: infrequent use of correct sentence "
                            "formation, punctuation, capitalization, grammar usage, "
                            "and spelling."
                        ),
                    },
                    {
                        "score": 1,
                        "descriptor": (
                            "The response demonstrates a partial command of "
                            "conventions: limited use of correct sentence formation, "
                            "punctuation, capitalization, grammar usage, and spelling."
                        ),
                    },
                    {
                        "score": 2,
                        "descriptor": (
                            "The response demonstrates an adequate command of "
                            "conventions: adequate use of correct sentence formation, "
                            "punctuation, capitalization, grammar usage, and spelling."
                        ),
                    },
                ],
            },
        ],
    },
    {
        "key": "smarter-balanced-middle-argumentative",
        "name": "Middle School Argumentative Writing (Grades 6-8)",
        "description": (
            "Smarter Balanced Assessment Consortium argumentative writing rubric "
            "aligned with Common Core standards for grades 6-8."
        ),
        "criteria": [
            {
                "name": "Organization/Purpose",
                "levels": [
                    {
                        "score": 1,
                        "descriptor": (
                            "The response has little or no discernible organizational "
                            "structure. The response may be related to the claim but "
                            "may provide little or no focus: claim may be confusing or "
                            "ambiguous; response may be too brief or the focus may "
                            "drift from the purpose and/or audience; few or no "
                            "transitional strategies are evident; introduction and/or "
                            "conclusion may be missing; frequent extraneous ideas may "
                            "be evident; ideas may be randomly ordered or have unclear "
                            "progression; alternate and opposing argument(s) may not "
                            "be acknowledged."
                        ),
                    },
                    {
                        "score": 2,
                        "descriptor": (
                            "The response has an inconsistent organizational "
                            "structure. Some flaws are evident, and some ideas may be "
                            "loosely connected. The organization is somewhat sustained "
                            "between and within paragraphs. The response may have a "
                            "minor drift in focus: claim may be somewhat unclear, or "
                            "the focus may be insufficiently sustained for the purpose "
                            "and/or audience; inconsistent use of transitional "
                            "strategies and/or little variety; introduction or "
                            "conclusion, if present, may be weak; uneven progression "
                            "of ideas from beginning to end; inconsistent or unclear "
                            "connections among ideas; alternate and opposing "
                            "argument(s) may be confusing or not acknowledged."
                        ),
                    },
                    {
                        "score": 3,
                        "descriptor": (
                            "The response has an evident organizational structure and "
                            "a sense of completeness. Though there may be minor flaws, "
                            "they do not interfere with the overall coherence. The "
                            "organization is adequately sustained between and within "
                            "paragraphs. The response is generally focused: claim is "
                            "clear, and the focus is mostly maintained for the purpose "
                            "and audience; adequate use of transitional strategies "
                            "with some variety to clarify relationships between and "
                            "among ideas; adequate introduction and conclusion; "
                            "adequate progression of ideas from beginning to end; "
                            "adequate connections between and among ideas; alternate "
                            "and opposing argument(s) are adequately acknowledged or "
                            "addressed."
                        ),
                    },
                    {
                        "score": 4,
                        "descriptor": (
                            "The response has a clear and effective organizational "
                            "structure, creating a sense of unity and completeness. "
                            "The organization is fully sustained between and within "
                            "paragraphs. The response is consistently and purposefully "
                            "focused: claim is introduced, clearly communicated, and "
                            "the focus is strongly maintained for the purpose and "
                            "audience; consistent use of a variety of transitional "
                            "strategies to clarify the relationships between and among "
                            "ideas; effective introduction and conclusion; logical "
                            "progression of ideas from beginning to end; strong "
                            "connections between and among ideas with some syntactic "
                            "variety; alternate and opposing argument(s) are clearly "
                            "acknowledged or addressed."
                        ),
                    },
                ],
            },
            {
                "name": "Evidence/Elaboration",
                "levels": [
                    {
                        "score": 1,
                        "descriptor": (
                            "The response provides minimal elaboration of the "
                            "support/evidence for the claim and argument(s) that "
                            "includes little or no use of source material. The "
                            "response is vague, lacks clarity, or is confusing: "
                            "evidence (facts and details) from the source material is "
                            "minimal, irrelevant, absent, incorrectly used, or "
                            "predominantly copied; insufficient use of citations or "
                            "attribution to source material; minimal, if any, use of "
                            "elaborative techniques; emotional appeal may dominate; "
                            "vocabulary is limited or ineffective for the audience and "
                            "purpose."
                        ),
                    },
                    {
                        "score": 2,
                        "descriptor": (
                            "The response provides uneven, cursory elaboration of the "
                            "support/evidence for the claim and argument(s) that "
                            "includes some reasoned analysis and partial or uneven use "
                            "of source material. The response develops ideas unevenly, "
                            "using simplistic language: some evidence (facts and "
                            "details) from the source material may be weakly "
                            "integrated, imprecise, repetitive, vague, and/or copied; "
                            "weak use of citations or attribution to source material; "
                            "weak or uneven use of elaborative techniques; development "
                            "may consist primarily of source summary or may rely on "
                            "emotional appeal; vocabulary use is uneven or somewhat "
                            "ineffective for the audience and purpose; inconsistent or "
                            "weak attempt to create appropriate style."
                        ),
                    },
                    {
                        "score": 3,
                        "descriptor": (
                            "The response provides adequate elaboration of the "
                            "support/evidence for the claim and argument(s) that "
                            "includes reasoned analysis and the use of source "
                            "material. The response adequately develops ideas, "
                            "employing a mix of precise with more general language: "
                            "adequate evidence (facts and details) from the source "
                            "material is integrated and relevant, yet may be general; "
                            "adequate use of citations or attribution to source "
                            "material; adequate use of some elaborative techniques; "
                            "vocabulary is generally appropriate for the audience and "
                            "purpose; generally appropriate style is evident."
                        ),
                    },
                    {
                        "score": 4,
                        "descriptor": (
                            "The response provides thorough and convincing elaboration "
                            "of the support/evidence for the claim and argument(s) "
                            "including reasoned, in-depth analysis and the effective "
                            "use of source material. The response clearly and "
                            "effectively develops ideas, using precise language: "
                            "comprehensive evidence (facts and details) from the "
                            "source material is integrated, relevant, and specific; "
                            "clear citations or attribution to source material; "
                            "effective use of a variety of elaborative techniques; "
                            "vocabulary is clearly appropriate for the audience and "
                            "purpose; effective, appropriate style enhances content."
                        ),
                    },
                ],
            },
            {
                "name": "Conventions",
                "levels": [
                    {
                        "score": 0,
                        "descriptor": (
                            "The response demonstrates little or no command of "
                            "conventions: infrequent use of correct sentence "
                            "formation, punctuation, capitalization, grammar usage, "
                            "and spelling."
                        ),
                    },
                    {
                        "score": 1,
                        "descriptor": (
                            "The response demonstrates a partial command of "
                            "conventions: limited use of correct sentence formation, "
                            "punctuation, capitalization, grammar usage, and spelling."
                        ),
                    },
                    {
                        "score": 2,
                        "descriptor": (
                            "The response demonstrates an adequate command of "
                            "conventions: adequate use of correct sentence formation, "
                            "punctuation, capitalization, grammar usage, and spelling."
                        ),
                    },
                ],
            },
        ],
    },
    {
        "key": "ccss-high-school-argument",
        "name": "High School Argument Writing (Grades 9-12)",
        "description": (
            "Common Core State Standards-aligned argument writing rubric for grades "
            "9-12, developed by the English Professional Learning Council (EPLC)."
        ),
        "criteria": [
            {
                "name": "Claim",
                "levels": [
                    {
                        "score": 1,
                        "descriptor": (
                            "The text contains an unidentifiable claim or vague "
                            "position. The text has limited structure and "
                            "organization."
                        ),
                    },
                    {
                        "score": 2,
                        "descriptor": (
                            "The text contains an unclear or emerging claim that "
                            "suggests a vague position. The text attempts a structure "
                            "and organization to support the position."
                        ),
                    },
                    {
                        "score": 3,
                        "descriptor": (
                            "The text introduces a claim that is arguable and takes a "
                            "position. The text has a structure and organization "
                            "aligned with the claim."
                        ),
                    },
                    {
                        "score": 4,
                        "descriptor": (
                            "The text introduces a precise claim that is clearly "
                            "arguable and takes an identifiable position on an issue. "
                            "The text has an effective structure and organization "
                            "aligned with the claim."
                        ),
                    },
                    {
                        "score": 5,
                        "descriptor": (
                            "The text introduces a compelling claim that is clearly "
                            "arguable and takes a purposeful position on an issue. The "
                            "text has a structure and organization carefully crafted "
                            "to support the claim."
                        ),
                    },
                ],
            },
            {
                "name": "Development",
                "levels": [
                    {
                        "score": 1,
                        "descriptor": (
                            "The text contains limited data and evidence related to "
                            "the claim and lacks counterclaims. The text may fail to "
                            "conclude the argument or position."
                        ),
                    },
                    {
                        "score": 2,
                        "descriptor": (
                            "The text provides data and evidence that attempt to back "
                            "up the claim and unclearly addresses counterclaims or "
                            "lacks counterclaims. The conclusion merely restates the "
                            "position."
                        ),
                    },
                    {
                        "score": 3,
                        "descriptor": (
                            "The text provides data and evidence to back up the claim "
                            "and addresses counterclaims. The conclusion ties to the "
                            "claim and evidence."
                        ),
                    },
                    {
                        "score": 4,
                        "descriptor": (
                            "The text provides sufficient and relevant data and "
                            "evidence to back up the claim and fairly addresses "
                            "counterclaims. The conclusion effectively reinforces the "
                            "claim and evidence."
                        ),
                    },
                    {
                        "score": 5,
                        "descriptor": (
                            "The text provides convincing and relevant data and "
                            "evidence to back up the claim and skillfully addresses "
                            "counterclaims. The conclusion effectively strengthens the "
                            "claim and evidence."
                        ),
                    },
                ],
            },
            {
                "name": "Audience",
                "levels": [
                    {
                        "score": 1,
                        "descriptor": (
                            "The text lacks an awareness of the audience's knowledge "
                            "level and needs."
                        ),
                    },
                    {
                        "score": 2,
                        "descriptor": (
                            "The text illustrates an inconsistent awareness of the "
                            "audience's knowledge level and needs."
                        ),
                    },
                    {
                        "score": 3,
                        "descriptor": (
                            "The text considers the audience's knowledge level, "
                            "concerns, values, and possible biases about the claim. "
                            "The text addresses the needs of the audience."
                        ),
                    },
                    {
                        "score": 4,
                        "descriptor": (
                            "The text anticipates the audience's knowledge level, "
                            "concerns, values, and possible biases about the claim. "
                            "The text addresses the specific needs of the audience."
                        ),
                    },
                    {
                        "score": 5,
                        "descriptor": (
                            "The text consistently addresses the audience's knowledge "
                            "level, concerns, values, and possible biases about the "
                            "claim. The text addresses the specific needs of the "
                            "audience."
                        ),
                    },
                ],
            },
            {
                "name": "Cohesion",
                "levels": [
                    {
                        "score": 1,
                        "descriptor": (
                            "The text contains few, if any, words, phrases, and "
                            "clauses to link the major sections of the text. The text "
                            "does not connect the claims and reasons."
                        ),
                    },
                    {
                        "score": 2,
                        "descriptor": (
                            "The text contains limited words, phrases, and clauses to "
                            "link the major sections of the text. The text attempts to "
                            "connect the claim and reasons."
                        ),
                    },
                    {
                        "score": 3,
                        "descriptor": (
                            "The text uses words, phrases, and clauses as well as "
                            "varied syntax to link the major sections of the text. The "
                            "text connects the claim and reasons. The text links the "
                            "counterclaims to the claim."
                        ),
                    },
                    {
                        "score": 4,
                        "descriptor": (
                            "The text skillfully uses words, phrases, and clauses as "
                            "well as varied syntax to link the major sections of the "
                            "text. The text identifies the relationship between the "
                            "claim and reasons as well as the evidence. The text "
                            "effectively links the counterclaims to the claim."
                        ),
                    },
                    {
                        "score": 5,
                        "descriptor": (
                            "The text strategically uses words, phrases, and clauses "
                            "as well as varied syntax to link the major sections of "
                            "the text. The text explains the relationships between the "
                            "claim and reasons as well as the evidence. The text "
                            "strategically links the counterclaims to the claim."
                        ),
                    },
                ],
            },
            {
                "name": "Style and Conventions",
                "levels": [
                    {
                        "score": 1,
                        "descriptor": (
                            "The text illustrates a limited awareness of or "
                            "inconsistent tone. The text demonstrates inaccuracy in "
                            "standard English conventions of usage and mechanics."
                        ),
                    },
                    {
                        "score": 2,
                        "descriptor": (
                            "The text illustrates a limited awareness of formal tone. "
                            "The text demonstrates some accuracy in standard English "
                            "conventions of usage and mechanics."
                        ),
                    },
                    {
                        "score": 3,
                        "descriptor": (
                            "The text presents a formal tone. The text demonstrates "
                            "standard English conventions of usage and mechanics while "
                            "attending to the norms of the discipline (e.g., MLA, "
                            "APA)."
                        ),
                    },
                    {
                        "score": 4,
                        "descriptor": (
                            "The text presents a formal, objective tone. The text "
                            "demonstrates standard English conventions of usage and "
                            "mechanics while attending to the norms of the discipline "
                            "(e.g., MLA, APA)."
                        ),
                    },
                    {
                        "score": 5,
                        "descriptor": (
                            "The text presents an engaging, formal, and objective "
                            "tone. The text intentionally uses standard English "
                            "conventions of usage and mechanics while attending to the "
                            "norms of the discipline (e.g., MLA, APA)."
                        ),
                    },
                ],
            },
        ],
    },
]


def get_template_by_key(key: str) -> TemplateDefinition | None:
    for template in RUBRIC_TEMPLATES:
        if template["key"] == key:
            return template
    return None


def build_template_summary(template: TemplateDefinition) -> dict[str, object]:
    criteria = template["criteria"]
    assert isinstance(criteria, Sequence)
    level_pattern: list[int] = []
    for criterion in criteria:
        levels = criterion["levels"]
        assert isinstance(levels, Sequence)
        level_pattern.append(len(levels))

    return {
        "key": template["key"],
        "name": template["name"],
        "description": template["description"],
        "criteria_count": len(criteria),
        "level_pattern": level_pattern,
    }

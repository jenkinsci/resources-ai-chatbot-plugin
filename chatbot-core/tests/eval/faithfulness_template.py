"""Jenkins-specific adaptation of DeepEval's FaithfulnessTemplate."""

# pylint: disable=unused-argument

import textwrap
from typing import List, Optional

from deepeval.metrics.faithfulness.template import FaithfulnessTemplate


class JenkinsFaithfulnessTemplate(FaithfulnessTemplate):
    """Prompt FaithfulnessMetric with Jenkins RAG-specific judging rules."""

    @staticmethod
    def generate_claims(actual_output: str, multimodal: bool = False):
        """
        Extract atomic factual claims from the Jenkins chatbot answer.

        Args:
            actual_output (str): Chatbot answer being evaluated.
            multimodal (bool): Kept for DeepEval template compatibility.

        Returns:
            str: Prompt that must produce JSON with a ``claims`` list.
        """
        return textwrap.dedent(
            f"""Based on the given Jenkins chatbot answer, please extract a comprehensive
            list of atomic FACTUAL claims that can be inferred from the answer.
            These claims MUST BE COHERENT and CANNOT be taken out of context.

            Example:
            Example Answer:
            "The provided context does not mention this."

            Example JSON:
            {{
                "claims": []
            }}
            ===== END OF EXAMPLE ======

            Example:
            Example Answer:
            "Install the Google Kubernetes Engine Plugin from Manage Jenkins >
            Manage Plugins > Available, then click Install without restart."

            Example JSON:
            {{
                "claims": [
                    "The Google Kubernetes Engine Plugin is listed under Available plugins.",
                    "Click Install without restart to install the Google Kubernetes Engine Plugin."
                ]
            }}
            ===== END OF EXAMPLE ======

            **
            IMPORTANT: Please make sure to only return in JSON format, with the "claims"
            key as a list of strings. No words or explanation is needed.
            Split compound claims into atomic factual claims. Do not extract claims from
            uncertainty or lack-of-context statements like "the provided context does not
            mention this".
            Preserve Jenkins plugin names, UI labels, file paths, URLs, commands, class
            names, annotations, and configuration keys exactly.
            Do not include prior knowledge. Extract only what the answer says.
            **

            Jenkins Chatbot Answer:
            {actual_output}

            JSON:
            """
        )

    @staticmethod
    def generate_truths(
        retrieval_context: str,
        extraction_limit: Optional[int] = None,
        multimodal: bool = False,
    ):
        """
        Extract relevant truths from noisy Jenkins retrieval context.

        Args:
            retrieval_context (str): Retrieved context supplied to the chatbot.
            extraction_limit (Optional[int]): Optional DeepEval truth limit.
            multimodal (bool): Kept for DeepEval template compatibility.

        Returns:
            str: Prompt that must produce JSON with a ``truths`` list.
        """
        if extraction_limit is None:
            limit = "all directly relevant factual truths"
        elif extraction_limit == 1:
            limit = "the single most important directly relevant factual truth"
        else:
            limit = f"up to {extraction_limit} directly relevant factual truths"

        return textwrap.dedent(
            f"""Based on the given Jenkins retrieval context, please generate a
            comprehensive list of {limit} that can be inferred from the context.
            These truths MUST BE COHERENT. They must NOT be taken out of context.
            The context is noisy and may contain multiple search-tool blocks, unrelated
            plugin index entries, quoted user problem statements, community replies,
            Stack Overflow placeholders, and partial docs.

            Example:
            Example Context:
            "[Result of the search tool search_plugin_docs]:
            The Google Kubernetes Engine (GKE) Plugin allows you to deploy build artifacts
            to Kubernetes clusters running in GKE with Jenkins.
            Installation: Go to Manage Jenkins then Manage Plugins. In the Plugin Manager,
            click the Available tab and look for the Google Kubernetes Engine Plugin. Check
            the box under the Install column and click the Install without restart button.
            [Result of the search tool search_stackoverflow_threads]:
            Nothing relevant"

            Example JSON:
            {{
                "truths": [
                    "The Google Kubernetes Engine Plugin deploys build artifacts to GKE clusters.",
                    "Install the Google Kubernetes Engine Plugin from Manage Plugins.",
                    "Click the Available tab and look for the Google Kubernetes Engine Plugin.",
                    "Check the Install column and click Install without restart."
                ]
            }}
            ===== END OF EXAMPLE ======

            **
            IMPORTANT: Please make sure to only return in JSON format, with the "truths"
            key as a list of strings. No words or explanation is needed.
            Prefer the context block that directly discusses the topic, plugin name,
            command, UI label, class, annotation, or error.
            Ignore blocks that say "Nothing relevant".
            Do not extract random plugin index entries unless they are directly relevant
            to the answer being judged.
            Preserve plugin names, UI labels, Jenkins terms, file paths, URLs, commands,
            annotations, and configuration keys exactly.
            For community/discourse-style context, distinguish quoted user problem
            statements from corrective answers or maintainer replies.
            Do not include prior knowledge. Extract only from the context.
            **

            Jenkins Retrieval Context:
            {retrieval_context}

            JSON:
            """
        )

    @staticmethod
    def generate_verdicts(
        claims: List[str], retrieval_context: str, multimodal: bool = False
    ):
        """
        Judge each claim against extracted Jenkins truths.

        Args:
            claims (List[str]): Atomic claims extracted from the answer.
            retrieval_context (str): Extracted truths joined by DeepEval.
            multimodal (bool): Kept for DeepEval template compatibility.

        Returns:
            str: Prompt that must produce JSON with a ``verdicts`` list.
        """
        return textwrap.dedent(
            f"""Based on the given claims, which is a list of strings, generate a list of
            JSON objects to indicate whether EACH claim is supported by the extracted
            retrieval truths. The JSON will have 2 fields: "verdict" and "reason".
            The "verdict" key should STRICTLY be either "yes", "no", or "idk".
            Provide a "reason" ONLY if the answer is "no" or "idk".

            Expected JSON format:
            {{
                "verdicts": [
                    {{
                        "verdict": "yes"
                    }},
                    {{
                        "reason": "explain why the truths contradict the claim",
                        "verdict": "no"
                    }},
                    {{
                        "reason": "explain what required support is missing",
                        "verdict": "idk"
                    }}
                ]
            }}

            Example:
            Example Extracted Truths:
            "The Git plugin accepts username/password credentials for HTTP/HTTPS repository
            access and SSH private key credentials for SSH repository access but not GitLab
            API tokens.
            The Pipeline stage can contain both retry and timeout steps. When a stage times
            out, the pipeline is marked as failed in that stage.
            To install the Google Kubernetes Engine Plugin, click Install without restart.
            The Build Log Compress Plugin can be enabled by checking Compress Build Log in
            job configuration or by adding compressBuildLog() to Pipeline properties.
            A community reply says Jenkins creates separate workspaces with suffixes such
            as @2 for concurrent runs."

            Example Claims:
            [
                "The Git plugin does not accept GitLab API token credentials.",
                "You can combine retry and timeout steps in a Jenkins Pipeline stage.",
                "The Google Kubernetes Engine Plugin must be installed after restarting Jenkins.",
                "The Google Kubernetes Engine Plugin supports AWS Lambda deployment mode.",
                "The Build Log Compress Plugin change applies immediately.",
                "Jenkins creates separate workspaces like @2 for concurrent runs.",
                "The plugin might require extra setup, but the context is incomplete."
            ]

            Example JSON:
            {{
                "verdicts": [
                    {{
                        "verdict": "yes"
                    }},
                    {{
                        "verdict": "yes"
                    }},
                    {{
                        "reason": "The truths say to click Install without restart.",
                        "verdict": "no"
                    }},
                    {{
                        "reason": "The truths do not support AWS Lambda deployment mode.",
                        "verdict": "no"
                    }},
                    {{
                        "reason": "The truths support enabling the plugin, but not immediacy.",
                        "verdict": "no"
                    }},
                    {{
                        "verdict": "yes"
                    }},
                    {{
                        "reason": "The claim is cautious and the truths are incomplete.",
                        "verdict": "idk"
                    }}
                ]
            }}
            ===== END OF EXAMPLE ======

            **
            IMPORTANT: Please make sure to only return in JSON format, with the "verdicts"
            key as a list of JSON objects.
            Generate exactly one verdict per claim, in the same order.
            Use "yes" when the claim is directly supported, semantically supported, or a
            reasonable inference from the truths that does not add a new unsupported tool,
            URL, version, command, plugin name, or recommendation.
            Use "no" when a confident factual claim is not supported by the truths, uses
            outside Jenkins knowledge, contradicts the truths, adds an unsupported detail
            that changes the meaning, or is too broad or vague to fully verify.
            Use "no" when only part of a claim is supported and another critical part is
            unsupported.
            Use "idk" only when the claim itself is cautious or uncertain, such as "may",
            "might", "likely", "appears", or "not enough context", or when the extracted
            truths are too noisy, malformed, empty, or incomplete to fairly judge the claim.
            Do not use "idk" as a safe fallback for confidently unsupported answer claims.
            Non-factual statements should not have been extracted as claims.
            Preserve Jenkins terminology: job, item, project, Pipeline, stage, agent,
            controller, workspace, plugin, credential, CLI, JCasC.
            Treat plugin names, UI labels, file paths, URLs, commands, and annotations as
            exact identifiers.
            If your reason says the truths support the claim, the verdict must be "yes".
            If your reason says a confident factual claim lacks support, the verdict must
            be "no".
            **

            Extracted Retrieval Truths:
            {retrieval_context}

            Claims:
            {claims}

            JSON:
            """
        )

    @staticmethod
    def generate_reason(
        score: float, contradictions: List[str], multimodal: bool = False
    ):
        """
        Summarize Faithfulness contradictions when reasons are enabled.

        Args:
            score (float): Faithfulness score calculated by DeepEval.
            contradictions (List[str]): Contradiction reasons from verdicts.
            multimodal (bool): Kept for DeepEval template compatibility.

        Returns:
            str: Prompt that must produce JSON with a ``reason`` string.
        """
        return textwrap.dedent(
            f"""Below is a list of Contradictions. It is a list of strings explaining why
            the Jenkins chatbot answer does not align with the information presented in
            the retrieval context.
            Given the faithfulness score, which is a 0-1 score indicating how faithful
            the actual output is to the retrieval context, CONCISELY summarize the
            contradictions to justify the score.

            Expected JSON format:
            {{
                "reason": "The score is <faithfulness_score> because <your_reason>."
            }}

            **
            IMPORTANT: Please make sure to only return in JSON format, with the "reason"
            key providing the reason.
            Your reason MUST use information in `contradictions` in your reason.
            **

            Faithfulness Score:
            {score}

            Contradictions:
            {contradictions}

            JSON:
            """
        )

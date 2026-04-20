# AgentLens™️ Core: System Architecture Design

**Status:** Draft 1.0  
**Phase:** 2 (Architectural Design)

## 1. System Overview

AgentLens™️ is a distributed, agentic intelligence platform designed to monitor, test, and optimize brand visibility within LLM-driven environments. The system follows a **Modular Agentic Loop** architecture, separating data ingestion (Observation) from strategic reasoning (Analysis).

## 2. High-Level Component Architecture

The system is composed of four primary functional modules, orchestrated via a central API Gateway.

### A. The Observation Engine (The "Eyes")
*   **Function:** Scrapes and snapshots the digital footprint of target brands.
*   **Core Components:**
    *   `WebCrawler`: Uses Firecrawl/Agent Browser to capture HTML/Markdown.
    *   `SERP_Snapshotter`: Captets the current state of AI search results (Perplexity, Gemini, etc.).
*   **Data Output:** Raw HTML/Markdown, Metadata (Timestamps, URLs), and Search Result Snapshots.

### B. The Intent Engine (The "Context")
*   **Function:** Generates high-fidelity, persona-driven query sets.
*   **Core Components:**
    *   `PersonaGenerator`: Uses LLMs to define demographic and psychographic profiles.
    **`QuerySynthesizer`**: Uses personas to generate natural language queries targeting specific brand attributes.
*   **Data Output:** A structured `IntentProfile` (Persona + Query + Targeted Attribute).

### C. The Agentic Tester (The "Execution")
*   **Function:** Spawns isolated sub-agents to execute queries and capture reasoning.
*   **Core Components:**
    *   `AgentOrchestrator`: Manages the lifecycle of sub-agent sessions (using `sessions_spawn`).
    *   `ReasoningExtractor`: Uses an LLM to parse raw agent responses into structured semantic data.
*   **Data Output:** `AgentResponse` (Presence Score, Reasoning Attributes, Sentiment).

### D. The Optimization Loop (The "Brain")
*   **Function:** Correlates data to generate actionable AEO recommendations.
*   **Core Components:**
    *   `CorrelationEngine`: Maps reasoning attributes to content clusters.
    *   `RecommendationGenerator`: Generates the final "Action Plan" for brand owners.
*   **Data Output:** `AEO_Action_Plan` (Content updates, keyword adjustments, etc.).

---

## 3. Communication & Orchestration Flow

1.  **API Gateway (FastAPI)** receives a request to start a new "Audit Cycle."
2.  **Observer** fetches the baseline data.
3.  **Intent Engine** generates the query set.
4.  **Orchestrator** spawns $N$ sub-agents (one per persona).
5.  **Tester** captures the reasoning and returns it to the API.
6.  **Analysis Engine** processes the batch and updates the database.
7.  **Optimization Loop** triggers a notification when a new strategic insight is found.

---

## 4. Security & Governance Model

*   **Isolation:** All agentic testing is performed in isolated, ephemeral sessions.
*   **Identity:** All tool calls are mediated through an Enterprise AI Gateway.
*   **Auditability:** Every reasoning extraction is linked to a unique `SessionID` and a raw `SourceSnippet`.

---
**Next Step:** Detailed Database Schema Design.

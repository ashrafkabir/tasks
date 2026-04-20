# Product Requirements Document (PRD): AgentLens™️ Core

**Version:** 0.1 (Draft)  
**Status:** In Progress  
**Owner:** Ash (Strategic Research Assistant)

---

## 1. Product Vision & Problem Statement

### 🎯 Vision
To transform digital marketing from "keyword-centric" to "reasoning-centric" by providing brands with an attribution engine that quantifies their visibility within the emerging agentic web (LLM-driven search and conversational commerce).

### ❌ The Problem
Traditional SEO tools track **rankings** (where you appear). However, in an agentic world, being "ranked" is secondary to being "reasoned into." Current tools cannot tell a brand **why** an AI agent recommended a competitor over them, or **which specific content attributes** (e.g., technical specs, price, or ethical stance) are driving the agent's decision-making process.

---

## 2. Target Personas & Intent Profiles

The Agentic Tester must simulate diverse, high-fidelity personas to capture a representative sample of the "Reasoning Landscape."

### 👤 Persona Archetypes

| Persona Name | Profile | Core Intent | Query Style |
| :--- | :--- | :--- | :--- |
| **The Technical Specialist** | Expert, detail-oriented, skeptical of marketing fluff. | Technical validation & specification matching. | "What is the exact thermal resistance of [Product] vs [Competitor]?" |
| **The Budget-Conscious Parent** | Value-driven, family-oriented, looking for reliability/safety. | Price-to-value ratio and long-term durability. | "Which [Category] offers the best longevity for under $500?" |
| **The Luxury Trend-Seeker** | Brand-conscious, status-driven, follows influencers/hype. | Brand prestige and aesthetic alignment. | "Which [Brand] is trending in high-fashion circles right now?" |
| **The Ethical Consumer** | Values-driven, sustainability-focused, research-heavy. | Environmental/ethical footprint and corporate stance. | "Which [Category] brands have the most transparent supply chains?" |

### 🎯 Intent-Based Query Generation
Queries will be generated using a template-based approach powered by LLMs to ensure variety:
`[Persona Context] + [Category/Product] + [Specific Attribute/Pain Point] + [Comparison/Recommendation Request]`

---

## 3. The Scoring Rubric: Quantifying "Agentic Visibility"

To turn qualitative agent responses into quantitative data, AgentLens™️ will utilize a multi-dimensional scoring system.

### 📊 Metric 1: Presence Score (PS)
*   **Definition:** A binary/ordinal score of whether the brand is mentioned in the agent's response.
*   **Calculation:** 
    *   `0`: Not mentioned.
    *   `1`: Mentioned as a secondary/alternative option.
    *   `2`: Mentioned as a primary/top recommendation.

### 📊 Metric 2: Reasoning Strength Score (RSS)
*   **Definition:** The degree of "attribution weight" the agent assigns to the brand.
*   **Calculation:** Based on the density and sentiment of "Reasoning Attributes" (e.g., "highly recommended due to [Attribute]").
*   **Formula:** `RSS = (Attribute_Count * Sentiment_Weight) / Total_Response_Length`

### 📊 Metric 3: Competitive Delta (CD)
*   **Definition:** The relative positioning of the brand compared to the top-ranked competitor in a specific intent category.
*   **Calculation:** `CD = (Brand_RSS - Competitor_RSS) / Competitor_RSS`

---

## 4. Functional Requirements

### 🛠️ Core Modules
1.  **Observer Module:** Automated web-scraping of target pages and AI search results (SERPs).
2.  **Intent Engine:** Generates persona-driven query sets using LLM-based templating.
3.  **Agentic Tester:** Spawns sub-agents to perform queries and captures raw text/reasoning outputs.
4.  **Analysis Engine:** Performs semantic parsing to map text to the RSS and PS scores.
5.  **AEO Optimizer:** Generates actionable content recommendations based on the scoring gaps.

---

## 5. Non-Functional Requirements
*   **Scalability:** Must support running 50+ concurrent sub-agent sessions.
*   **Auditability:** Every reasoning extraction must be linked to a raw source snippet for verification.
*   **Extensibility:** Must allow for the addition of new "Personas" and "Attribute Sets" via configuration.

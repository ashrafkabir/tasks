# AgentLens™️ Core: Database Schema Design

**Status:** Draft 1.0  
**Phase:** 2 (Architectural Design)

## 1. Conceptual Data Model

The database is designed to track the journey from a **Brand** being monitored to a specific **Actionable Recommendation** being generated. The core of the model is the **Reasoning Linkage**: connecting a specific agent's reasoning back to the query and the persona that drove it.

## 2. Entity-Relationship Diagram (ERD) Logic

### A. Core Entities

#### 1. `brands`
Stores the target brands being monitored.
*   `id` (PK)
*   `name` (String, Unique)
*   `category` (String)
*   `created_at` (Timestamp)

#### 2. `personas`
Stores the profiles of the simulated agents.
*   `id` (PK)
*   `name` (String)
*   `demographic_profile` (JSON: age, location, etc.)
*   `psychographic_profile` (JSON: values, interests, pain points)
*   `query_style` (String: e.g., "Technical", "Casual", "Aggressive")

#### 3. `intents`
Stores the specific queries generated for a persona.
*   `id` (PK)
*   `persona_id` (FK $\rightarrow$ `personas.id`)
*   `brand_id` (FK $\rightarrow$ `brands.id`)
*   `query_text` (String)
*   `target_attribute` (String: e.g., "Durability", "Price")
*   `status` (Enum: `pending`, `completed`, `failed`)

#### 4. `agent_responses`
Stores the raw and processed output from the testing phase.
*   `id` (PK)
*   `intent_id` (FK $\rightarrow$ `intents.id`)
*   `raw_text` (Text: The full agent response)
*   `presence_score` (Integer: 0-2)
*   `sentiment_score` (Float: -1.0 to 1.0)
*   `created_at` (Timestamp)

#### 5. `reasoning_attributes`
The "Intelligence Layer." Stores the granular reasons why an agent made a recommendation.
*   `id` (PK)
*   `response_id` (FK $\rightarrow$ `agent_responses.id`)
*   `attribute_name` (String: e.g., "Technical Accuracy", "Price Advantage")
*   `attribute_weight` (Float: 0.0 to 1.0)
*   `supporting_evidence` (Text: The specific snippet from the raw text)

### B. Supporting Entities

#### 6. `audit_logs`
Tracks all system actions for compliance.
*   `id` (PK)
*   `action_type` (String)
*   `actor` (String)
*   `timestamp` (Timestamp)

---

## 3. Relational Mapping (Summary)

`Brands` $\rightarrow$ `Intents` $\leftarrow$ `Personas`  
`Intents` $\rightarrow$ `Agent_Responses` $\rightarrow$ `Reasoning_Attributes`

---

## 4. Technical Implementation Notes

*   **Database Engine:** PostgreSQL (Production) / SQLite (Development).
*   **ORM:** SQLAlchemy / SQLModel.
*   **Indexing Strategy:** 
    *   Index on `intents.brand_id` and `intents.persona_id` for fast query reconstruction.
    *   Index on `reasoning_attributes.attribute_name` to enable fast correlation analysis.
*   **Scalability:** The `reasoning_attributes` table is expected to be the largest. It should be partitioned by `brand_id` if scaling to hundreds of brands.

---
**Next Step:** Transition to Phase 3 (Agentic Core) - Implementation of the Observer and Intent Engine.

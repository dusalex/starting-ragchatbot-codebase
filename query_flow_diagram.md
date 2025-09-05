# RAG System Query Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                   FRONTEND                                          │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐ │
│  │                            User Interface (script.js)                          │ │
│  │                                                                                 │ │
│  │  1. User types query + presses Enter                                           │ │
│  │  2. sendMessage() triggered                                                    │ │
│  │  3. Show loading animation                                                     │ │
│  │  4. POST /api/query                                                           │ │
│  │     ┌─────────────────────────────────┐                                       │ │
│  │     │ {                               │                                       │ │
│  │     │   "query": "user's question",   │                                       │ │
│  │     │   "session_id": "optional_id"   │                                       │ │
│  │     │ }                               │                                       │ │
│  │     └─────────────────────────────────┘                                       │ │
│  └─────────────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                   BACKEND                                           │
│                                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐ │
│  │                          FastAPI Endpoint (app.py)                             │ │
│  │                                                                                 │ │
│  │  1. Receive QueryRequest at /api/query                                         │ │
│  │  2. Create session_id if missing                                               │ │
│  │  3. Call rag_system.query(query, session_id)                                  │ │
│  │  4. Return QueryResponse                                                       │ │
│  └─────────────────────────────────────────────────────────────────────────────────┘ │
│                                         │                                           │
│                                         ▼                                           │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐ │
│  │                        RAG System Orchestrator (rag_system.py)                 │ │
│  │                                                                                 │ │
│  │  1. Get conversation history from SessionManager                               │ │
│  │  2. Prepare prompt: "Answer this question about course materials: {query}"    │ │
│  │  3. Call ai_generator.generate() with tools                                   │ │
│  └─────────────────────────────────────────────────────────────────────────────────┘ │
│                                         │                                           │
│                                         ▼                                           │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐ │
│  │                        AI Generator (ai_generator.py)                          │ │
│  │                                                                                 │ │
│  │  1. Claude AI receives system prompt + user query                             │ │
│  │  2. AI decides: General knowledge OR Course-specific search needed?           │ │
│  │                                                                                 │ │
│  │     General Knowledge          │          Course-Specific Query               │ │
│  │           │                    │                    │                         │ │
│  │           ▼                    │                    ▼                         │ │
│  │  ┌─────────────────┐          │          ┌─────────────────────────┐         │ │
│  │  │ Direct Answer   │          │          │ Use CourseSearchTool    │         │ │
│  │  │ from Claude's   │          │          │                         │         │ │
│  │  │ Training Data   │          │          │ 1. Convert query to     │         │ │
│  │  └─────────────────┘          │          │    embeddings           │         │ │
│  │                               │          │ 2. Search ChromaDB      │         │ │
│  │                               │          │ 3. Return top chunks    │         │ │
│  │                               │          └─────────────────────────┘         │ │
│  │                               │                    │                         │ │
│  │                               │                    ▼                         │ │
│  │                               │          ┌─────────────────────────┐         │ │
│  │                               │          │ Vector Store Search     │         │ │
│  │                               │          │ (vector_store.py)       │         │ │
│  │                               │          │                         │         │ │
│  │                               │          │ ┌─────────────────────┐ │         │ │
│  │                               │          │ │    ChromaDB         │ │         │ │
│  │                               │          │ │                     │ │         │ │
│  │                               │          │ │ • Course chunks     │ │         │ │
│  │                               │          │ │ • Vector embeddings │ │         │ │
│  │                               │          │ │ • Metadata          │ │         │ │
│  │                               │          │ └─────────────────────┘ │         │ │
│  │                               │          └─────────────────────────┘         │ │
│  │                               │                    │                         │ │
│  │           ┌───────────────────┼────────────────────┘                         │ │
│  │           │                   │                                               │ │
│  │           ▼                   │                                               │ │
│  │  ┌─────────────────────────────┐                                             │ │
│  │  │ Claude synthesizes final    │                                             │ │
│  │  │ response using:             │                                             │ │
│  │  │ • System prompt guidelines  │                                             │ │
│  │  │ • Conversation history      │                                             │ │
│  │  │ • Search results (if any)   │                                             │ │
│  │  └─────────────────────────────┘                                             │ │
│  └─────────────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                               RESPONSE FLOW                                         │
│                                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐ │
│  │                          Backend Response                                       │ │
│  │                                                                                 │ │
│  │     ┌─────────────────────────────────┐                                       │ │
│  │     │ {                               │                                       │ │
│  │     │   "answer": "AI response",      │                                       │ │
│  │     │   "sources": [],                │                                       │ │
│  │     │   "session_id": "session123"    │                                       │ │
│  │     │ }                               │                                       │ │
│  │     └─────────────────────────────────┘                                       │ │
│  └─────────────────────────────────────────────────────────────────────────────────┘ │
│                                         │                                           │
│                                         ▼                                           │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐ │
│  │                          Frontend Display                                      │ │
│  │                                                                                 │ │
│  │  1. Remove loading animation                                                   │ │
│  │  2. Display AI response with markdown formatting                               │ │
│  │  3. Update session_id if new                                                  │ │
│  │  4. Re-enable input for next query                                            │ │
│  │  5. Scroll to show new message                                                │ │
│  └─────────────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              SESSION MANAGEMENT                                     │
│                                                                                     │
│  Throughout the entire process, SessionManager maintains:                          │
│  • Conversation history for context-aware responses                                │
│  • Session state across multiple queries                                          │
│  • Memory of previous interactions                                                 │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

## Key Flow Points:

1. **Frontend**: User input → API call → Loading state
2. **API Layer**: Request validation → RAG system delegation  
3. **RAG Orchestration**: Session management → AI generation with tools
4. **AI Decision**: General knowledge OR course-specific search
5. **Vector Search**: Embedding similarity → ChromaDB retrieval (if needed)
6. **Response Synthesis**: Claude combines context + search results
7. **Display**: Remove loading → Show formatted response → Re-enable input

The system intelligently routes queries through appropriate paths while maintaining conversational context.
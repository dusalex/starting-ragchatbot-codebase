# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Running the Application
```bash
# Quick start with shell script
chmod +x run.sh
./run.sh

# Manual start
cd backend && uv run uvicorn app:app --reload --port 8000
```

### Environment Setup
```bash
# Install dependencies
uv sync

# Set up environment variables
cp .env.example .env
# Edit .env to add your ANTHROPIC_API_KEY
```

### Application Access
- Web Interface: http://localhost:8000
- API Documentation: http://localhost:8000/docs

## Architecture Overview

This is a **Retrieval-Augmented Generation (RAG) system** for querying course materials using Anthropic Claude AI with ChromaDB vector storage.

### Core Components Architecture

**RAGSystem** (`rag_system.py`) - Central orchestrator that coordinates all components:
- Manages document processing pipeline
- Handles user queries through AI generation with tool access
- Coordinates between vector search and AI response generation

**Query Processing Flow:**
1. User query → FastAPI endpoint (`/api/query`)
2. RAGSystem processes query and manages session
3. AI Generator (Claude) decides: general knowledge OR course-specific search
4. If course-specific: CourseSearchTool queries ChromaDB vector store
5. Claude synthesizes final response using search results + conversation history

**Key Integration Points:**

- **DocumentProcessor** (`document_processor.py`): Parses structured course files with metadata extraction, lesson segmentation, and sentence-based chunking with configurable overlap
- **VectorStore** (`vector_store.py`): ChromaDB wrapper managing course metadata and content chunks with embedding-based semantic search
- **AIGenerator** (`ai_generator.py`): Claude API integration with system prompt defining tool usage patterns and response guidelines
- **SessionManager** (`session_manager.py`): Maintains conversation history for context-aware responses across chat sessions
- **ToolManager/CourseSearchTool** (`search_tools.py`): Provides Claude with structured access to vector database through tool calling

### Data Models (`models.py`)
- **Course**: Contains title, instructor, lessons list, and course link
- **Lesson**: Lesson number, title, and optional lesson link
- **CourseChunk**: Text content with course/lesson metadata for vector storage

### Document Processing Pipeline
Course documents follow this structure:
```
Course Title: [title]
Course Link: [url]
Course Instructor: [instructor]

Lesson 0: Introduction
Lesson Link: [lesson_url]
[content...]
```

Text is chunked using sentence-based splitting with configurable size (800 chars) and overlap (100 chars). Chunks are enhanced with contextual metadata like "Course {title} Lesson {N} content: {chunk}".

### Configuration (`config.py`)
Centralized settings via environment variables and dataclass:
- Anthropic API key and model selection
- Chunk size/overlap parameters  
- ChromaDB path and embedding model
- Search result limits and conversation history depth

### Frontend Integration
Simple HTML/JS interface (`frontend/`) communicates via REST API with session management, loading states, and markdown rendering for responses.

## File Organization

- `backend/` - Python FastAPI application
- `frontend/` - Static HTML/CSS/JS files  
- `docs/` - Course script files for processing
- `run.sh` - Application startup script
- `pyproject.toml` - uv dependency management

The system automatically processes course documents from `/docs` folder on startup and maintains persistent vector storage in `./chroma_db`.
- Always use uv to run the server, do not use pip directly
- Make sure to use uv to manage all dependencies
- Use uv to run Python files
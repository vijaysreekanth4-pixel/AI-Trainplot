"""
InterviewAI — LangGraph Agentic Backend v3.0
Architecture:
  - LangGraph StateGraph with human-in-the-loop interrupt pattern
  - FAISS RAG for resume-grounded question generation
  - ConversationBufferMemory via LangGraph MemorySaver
  - AI decides dynamically when to end (min 10 questions, based on resume depth)
"""

import os
import re
import uuid
import tempfile
import operator
import hashlib
import json
import io
import contextlib
from typing import TypedDict, List, Optional, Annotated

from fastapi import FastAPI, UploadFile, File, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn
from dotenv import load_dotenv

# LangGraph
from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt, Command

# LangChain Core
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool

# Agentic Tools
try:
    from duckduckgo_search import DDGS
    DDGS_AVAILABLE = True
except ImportError:
    DDGS_AVAILABLE = False
    print("duckduckgo_search not installed — web search tool disabled.")


load_dotenv()

# Always import LangChain OpenAI components (they will be used dynamically if key is provided)
try:
    from langchain_openai import OpenAIEmbeddings, ChatOpenAI
    from langchain_community.vectorstores import FAISS
    from langchain_community.document_loaders import PyPDFLoader, TextLoader
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except Exception as e:
    print("Warning: Missing some langchain packages. Demo mode will be active.", e)

# ── In-memory stores ──────────────────────────────────────────────────
vector_stores: dict = {}   # resume_session_id → FAISS
resume_texts: dict = {}    # resume_session_id → raw text (demo mode)

# ── Cross-Session Memory ───────────────────────────────────────────────
HISTORY_FILE = "resume_history.json"
def load_resume_history() -> dict:
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_resume_history(history: dict):
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=4)

global_resume_history = load_resume_history()

# ── Demo question banks (used when OpenAI key not set) ────────────────
DEMO_QUESTIONS = {
    "Software Engineering": [
        "Tell me about yourself and your software engineering background.",
        "Explain the most complex project you’ve built — what was your role and what challenges did you solve?",
        "Walk me through your experience with REST APIs. How have you designed or consumed them?",
        "Describe your approach to debugging a production issue you’ve never seen before.",
        "What is Docker and how have you used containerization in your projects?",
        "Explain SOLID principles. Can you give an example from your codebase?",
        "How do you handle database design and optimization in your applications?",
        "Tell me about a time you improved the performance of an existing system.",
        "How do you approach writing unit tests and what coverage do you aim for?",
        "What CI/CD tools have you used and how did you set up the pipeline?",
        "Describe your experience with cloud platforms (AWS/GCP/Azure).",
        "How do you handle authentication and authorization in your apps?",
        "Tell me about your experience with microservices vs monolith architectures.",
        "How do you handle version control and code reviews in your team?",
        "What design patterns have you used and when did you choose them?",
        "Describe a time you had to refactor legacy code. How did you approach it?",
        "How do you handle concurrency and thread safety in your applications?",
        "Explain the difference between SQL and NoSQL databases and when you’d choose each.",
        "What is your approach to API versioning and backward compatibility?",
        "Describe how you would architect a system to handle 1 million users.",
        "How have you implemented caching in your applications? What strategy did you use?",
        "Explain the CAP theorem and how it affects distributed system design.",
        "What is your experience with message queues like RabbitMQ or Kafka?",
        "How do you approach system monitoring and alerting in production?",
        "Describe a security vulnerability you identified and fixed in your code.",
        "CODING CHALLENGE: Write pseudo-code to reverse a linked list.",
        "CODING CHALLENGE: How would you find the first non-repeating character in a string?",
        "CODING CHALLENGE: Explain the logic to detect a cycle in a directed graph.",
        "ALGORITHM: What is the difference between BFS and DFS, and when would you use each?",
        "ALGORITHM: Explain Big O notation and analyze the complexity of binary search.",
        "SYSTEM DESIGN: How would you design a URL shortener like bit.ly?",
        "SYSTEM DESIGN: Design a real-time chat application. What components would you use?",
    ],
    "Data Science": [
        "Tell me about yourself and your data science background.",
        "Describe the most impactful ML model you’ve built. What was the business impact?",
        "Walk me through your end-to-end process for a machine learning project.",
        "How have you handled class imbalance in classification problems?",
        "Explain feature engineering techniques you’ve applied in real projects.",
        "What is the bias-variance tradeoff and how did you manage it in a past project?",
        "Describe your experience with FAISS or vector databases for similarity search.",
        "How do you evaluate and choose between different ML models?",
        "Explain how you’ve deployed an ML model into production.",
        "What tools do you use for data visualization and storytelling?",
        "How do you handle missing or corrupted data in datasets?",
        "Describe your experience with time-series forecasting.",
        "What is gradient boosting and when would you use XGBoost vs LightGBM?",
        "How do you monitor model drift in production?",
        "Tell me about a failed model — what went wrong and what did you learn?",
        "Explain the difference between precision, recall, and F1-score with real examples.",
        "What is cross-validation and why is it important?",
        "Describe your experience with NLP techniques and transformers.",
        "How have you used dimensionality reduction techniques like PCA or t-SNE?",
        "What is regularization and when would you use L1 vs L2?",
        "Explain how a Random Forest works and its advantages over a single Decision Tree.",
        "Describe a data pipeline you built and the tools you used.",
        "How do you approach A/B testing and statistical significance?",
        "What is the difference between supervised, unsupervised, and reinforcement learning?",
        "Describe your experience with deep learning frameworks like TensorFlow or PyTorch.",
        "How do you explain a complex ML model to a non-technical stakeholder?",
        "What is attention mechanism and how does it work in transformers?",
        "Describe a recommendation system you built or would design.",
        "How do you handle data leakage in machine learning?",
        "CODING: Write the logic to calculate cosine similarity between two vectors.",
        "SYSTEM DESIGN: How would you design a real-time fraud detection system?",
    ],
    "Product Management": [
        "Tell me about yourself and your product management journey.",
        "Describe a product you built from 0 to 1. How did you validate the idea?",
        "How do you prioritize features when you have limited engineering bandwidth?",
        "Walk me through how you write a Product Requirements Document.",
        "Tell me about a time you had to say no to a stakeholder request.",
        "How do you measure the success of a product feature post-launch?",
        "Describe your process for conducting user research.",
        "How do you collaborate with engineering teams to ship on time?",
        "Tell me about a product decision you made with incomplete data.",
        "How do you handle conflicting priorities between sales and engineering?",
        "Describe your approach to competitive analysis.",
        "What OKRs have you set and how did you track them?",
        "How do you build a product roadmap for the next 6 months?",
        "Tell me about a product failure. What would you do differently?",
        "How do you stay updated on industry trends and incorporate them into your product?",
        "Describe a time you used data to change a product direction.",
        "How do you handle a situation where user feedback contradicts analytics data?",
        "What frameworks do you use for product discovery?",
        "How do you define and measure North Star metrics?",
        "Describe your experience with go-to-market strategy for a new feature.",
        "How do you manage technical debt from a PM perspective?",
        "Tell me about a time you had to pivot a product mid-development.",
        "How do you handle a low NPS score for your product?",
        "Describe how you would design an onboarding flow for a new mobile app.",
        "How do you balance short-term user needs vs long-term product vision?",
        "What tools do you use for product analytics (Mixpanel, Amplitude, etc.)?",
        "How do you coordinate across multiple engineering squads simultaneously?",
        "Describe a time you shipped a feature that didn’t perform as expected.",
        "How do you communicate product strategy to executives vs engineering teams?",
        "Tell me about a time you successfully launched a product in a new market.",
        "How do you approach pricing strategy for a SaaS product?",
    ],
}

def get_demo_question(domain: str, q_num: int, resume_text: str = "", history: list = None) -> str:
    if history is None:
        history = []

    bank = list(DEMO_QUESTIONS.get(domain, DEMO_QUESTIONS["Software Engineering"]))
    extras = [
        "Can you elaborate more on the project you mentioned? What was the biggest technical challenge?",
        "How did you measure the success of that project?",
        "What would you do differently if you were to redo that project today?",
        "How did you collaborate with your team on that initiative?",
        "What new skills did you gain from that experience?",
        "Describe a situation where you had to learn a new technology quickly under pressure.",
        "How do you approach debugging a production issue with limited information?",
        "Describe your experience with CI/CD pipelines and DevOps practices.",
        "How do you ensure code quality in a team setting?",
        "Tell me about a time you disagreed with a technical decision. How did you handle it?",
        "CODING CHALLENGE: Write a pseudo-code or explain the logic to reverse a linked list.",
        "CODING CHALLENGE: How would you find the first non-repeating character in a string? Explain the algorithm.",
        "CODING CHALLENGE: Explain the concept of recursion with a real-world example or code snippet.",
        "ALGORITHM QUESTION: What is the difference between BFS and DFS, and when would you use each?",
        "SYSTEM DESIGN: How would you design a scalable notification service?",
        "SYSTEM DESIGN: Design a rate limiter for a public API. What approach would you take?",
        "What is the most impactful optimization you’ve made to a system, and how did you measure success?",
        "Describe a time you mentored a junior developer or helped a teammate grow technically.",
        "Walk me through a scalability challenge you solved in a past project.",
        "How do you approach technical debt and give a real example of addressing it?",
    ]
    all_questions = bank + extras

    # Normalize a question for comparison (strip punctuation, lowercase, first 60 chars)
    def normalize(q):
        return re.sub(r'[^a-z0-9 ]', '', q.lower().strip())[:60]

    # Build set of already-asked normalized texts (current session only)
    asked_normalized = set(normalize(q) for q in history)

    # Filter strictly: remove any question whose normalized form is already asked
    available = [q for q in all_questions if normalize(q) not in asked_normalized]

    if not available:
        # All exhausted — generate a unique fallback
        fallback = [
            f"Question #{q_num}: Walk me through a scalability challenge you solved.",
            f"Question #{q_num}: How do you approach technical debt with a real example?",
            f"Question #{q_num}: What excites you most about the future of {domain}?",
            f"Question #{q_num}: Describe a time you mentored someone on your team.",
            f"Question #{q_num}: What is the most impactful system improvement you’ve made?",
        ]
        return fallback[q_num % len(fallback)]

    # Pick sequentially based on q_num to guarantee no repeats within session
    index = (q_num - 1) % len(available)
    return available[index]




# ─── Agentic Tools ────────────────────────────────────────────────────
def web_search_tool(query: str, max_results: int = 3) -> str:
    """Search the web for factual information to fact-check a candidate's answer."""
    if not DDGS_AVAILABLE:
        return "Web search unavailable."
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        if not results:
            return "No results found."
        summary = ""
        for r in results:
            summary += f"- {r.get('title', '')}: {r.get('body', '')[:200]}\n"
        return summary.strip()
    except Exception as e:
        return f"Search error: {e}"


def python_repl_tool(code: str) -> str:
    """Execute Python code and return stdout/stderr — used to evaluate code answers."""
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()
    result = {"output": "", "error": ""}
    try:
        with contextlib.redirect_stdout(stdout_capture), contextlib.redirect_stderr(stderr_capture):
            exec(compile(code, "<candidate_code>", "exec"), {})
        result["output"] = stdout_capture.getvalue()
        result["error"] = stderr_capture.getvalue()
    except Exception as e:
        result["error"] = str(e)
    output = result["output"] or "(no stdout)"
    error = result["error"]
    return f"Output: {output}" + (f"\nError: {error}" if error else "")


# ── Question-aware knowledge base for correct answers ──────────────────
CORRECT_ANSWERS_KB = {
    # System Design / Scalability
    "scalab": "Scalability can be achieved through horizontal scaling (adding more servers), load balancing, caching (Redis/Memcached), CDNs for static assets, database sharding or read replicas, and async message queues (Kafka/RabbitMQ). For fault tolerance, implement circuit breakers, retries with exponential backoff, health checks, and multi-region deployments with failover.",
    "fault toleran": "Fault tolerance means designing systems that continue operating despite partial failures. Strategies include: redundancy (active-active or active-passive), circuit breakers (Hystrix/Resilience4j), bulkhead pattern to isolate failures, retry logic with exponential backoff, graceful degradation, and chaos engineering (Netflix's Chaos Monkey) to proactively find weaknesses.",
    "microservic": "Microservices architecture decomposes an application into small, independently deployable services. Each service owns its data, communicates via REST/gRPC/events, and can be scaled independently. Key patterns: API Gateway, service discovery (Consul/Eureka), distributed tracing (Jaeger), saga pattern for distributed transactions, and event-driven communication (Kafka).",
    "docker": "Docker is a containerization platform. Containers package app + dependencies into isolated units. Key commands: docker build (create image), docker run (start container), docker-compose (multi-container). Best practices: use multi-stage builds to reduce image size, run as non-root user, pin base image versions, and use .dockerignore.",
    "kubernetes": "Kubernetes (K8s) orchestrates container deployments. Key concepts: Pod (smallest unit), Deployment (manages replicas), Service (exposes pods), Ingress (routes HTTP), ConfigMap/Secret (configuration), HPA (horizontal pod autoscaler). Use namespaces for isolation, resource limits for stability, and readiness/liveness probes for health checks.",
    "database": "Database design best practices: normalize data (1NF, 2NF, 3NF) to reduce redundancy, use indexes on frequently queried columns, implement connection pooling, choose SQL for ACID transactions and NoSQL (MongoDB, Redis, Cassandra) for scale/flexibility. For optimization: query analysis with EXPLAIN, avoid N+1 queries, use caching for read-heavy workloads.",
    "sql": "SQL optimization involves: creating proper indexes (B-tree for range queries, hash for equality), avoiding SELECT *, using JOINs efficiently, analyzing query plans with EXPLAIN, using pagination (LIMIT/OFFSET or cursor-based), partitioning large tables, and using materialized views for complex aggregations.",
    "cache": "Caching strategies: Cache-aside (app checks cache first, then DB), Write-through (write to cache + DB), Write-back (write to cache, async to DB), Read-through. Use Redis for distributed cache. Key considerations: TTL (expiration), cache invalidation strategies, cache stampede prevention (mutex/jitter), and cache hit ratio monitoring.",
    "api": "REST API best practices: use meaningful HTTP verbs (GET/POST/PUT/DELETE/PATCH), proper status codes (200/201/400/401/403/404/500), versioning (/v1/), pagination, rate limiting, input validation, and authentication (JWT/OAuth2). Design with resource-oriented URLs, use HATEOAS for discoverability, and document with OpenAPI/Swagger.",
    "machine learning": "ML pipeline: Data collection → EDA → Feature Engineering → Model Selection → Training → Evaluation (metrics: accuracy, precision, recall, F1, AUC-ROC) → Hyperparameter tuning (Grid/Random/Bayesian search) → Deployment → Monitoring (data drift, concept drift). Use cross-validation to prevent overfitting, regularization (L1/L2), and ensemble methods.",
    "neural network": "Neural networks consist of layers of neurons (input, hidden, output). Key concepts: activation functions (ReLU, Sigmoid, Softmax), backpropagation for weight updates, gradient descent (SGD, Adam, RMSProp), batch normalization, dropout for regularization, and learning rate scheduling. Deep networks learn hierarchical feature representations.",
    "cicd": "CI/CD pipeline: developers push code → CI server (Jenkins/GitHub Actions/GitLab CI) runs automated tests → builds artifact → CD deploys to staging → smoke tests → deploy to production. Best practices: keep builds fast, fail fast on tests, use feature flags for gradual rollouts, blue-green or canary deployments for zero-downtime releases.",
    "git": "Git best practices: use feature branches, write meaningful commit messages (Conventional Commits), squash commits before merging, use pull requests for code review, tag releases (semantic versioning), never force-push to main/master, use .gitignore for build artifacts, and use git hooks for pre-commit checks.",
    "security": "Security best practices: OWASP Top 10 (injection, XSS, CSRF, broken auth), use parameterized queries to prevent SQL injection, implement JWT/OAuth2 for authentication, HTTPS everywhere, input validation and sanitization, proper password hashing (bcrypt/Argon2), least privilege principle, regular security audits, and dependency vulnerability scanning.",
    "cloud": "Cloud architecture best practices: use managed services where possible, implement IaC (Terraform/CloudFormation), design for multi-AZ redundancy, use auto-scaling groups, implement proper IAM with least privilege, enable CloudWatch/monitoring, use VPC for network isolation, implement cost tagging, and leverage CDN for global distribution.",
    "performance": "Performance optimization: profile first (identify bottlenecks), optimize database queries (indexes, N+1), implement caching (Redis), use async/non-blocking I/O, compress responses (gzip/brotli), lazy load resources, implement CDN, use connection pooling, minimize network round trips, and set up APM tools (Datadog/New Relic) for monitoring.",
    "agile": "Agile methodology: iterative development in sprints (1-4 weeks), daily standups, sprint planning, retrospectives, and demos. Key roles: Product Owner (prioritizes backlog), Scrum Master (facilitates), Development Team. Focus on working software, collaboration, responding to change. Use story points for estimation, burndown charts for progress tracking.",
    "design pattern": "Key design patterns: Singleton (one instance), Factory (object creation), Observer (event handling), Strategy (interchangeable algorithms), Decorator (add behavior dynamically), Repository (data access abstraction), CQRS (separate read/write), Event Sourcing (store state changes as events). Apply SOLID principles: Single Responsibility, Open/Closed, Liskov, Interface Segregation, Dependency Inversion.",
    "object orient": "OOP principles: Encapsulation (bundle data + behavior, hide internals), Inheritance (reuse parent class behavior), Polymorphism (same interface, different implementations), Abstraction (hide complexity). SOLID principles guide good OOP design. Prefer composition over inheritance, use interfaces for decoupling, and follow the Law of Demeter.",
    "testing": "Testing pyramid: Unit tests (fast, isolated, mock dependencies) → Integration tests (test component interactions) → E2E tests (test full user flows). Use TDD (Red-Green-Refactor), aim for 80%+ coverage on critical paths, use mocking frameworks, implement contract testing for microservices, and run tests in CI pipeline.",
    "devops": "DevOps practices: Infrastructure as Code (Terraform/Ansible), CI/CD pipelines, containerization (Docker/K8s), monitoring & observability (metrics, logs, traces), automated testing, blue-green deployments, feature flags, on-call rotations, and blameless post-mortems. Goal: reduce MTTR and deployment frequency while maintaining stability.",
    "data structure": "Key data structures: Array (O(1) access), LinkedList (O(1) insert/delete), Stack (LIFO, used in recursion/undo), Queue (FIFO, used in BFS/scheduling), HashMap (O(1) avg lookup), Binary Tree (hierarchical data), Graph (networks), Heap (priority queue). Choose based on access patterns — arrays for indexed access, hash maps for key-value lookups.",
    "algorithm": "Algorithm complexity (Big O): O(1) constant, O(log n) binary search, O(n) linear search, O(n log n) merge sort, O(n²) bubble sort. Key algorithms: sorting (QuickSort, MergeSort), searching (Binary Search, BFS/DFS), dynamic programming (memoization/tabulation), greedy algorithms, and graph algorithms (Dijkstra, A*).",
    "react": "React best practices: use functional components with hooks, lift state up, use Context or Redux for global state, memoize expensive calculations (useMemo/useCallback), avoid prop drilling, implement code splitting (React.lazy), optimize re-renders, use proper key props in lists, and follow React Query/SWR for server state management.",
    "python": "Python best practices: use virtual environments (venv/conda), follow PEP 8 style guide, use list comprehensions for conciseness, leverage generators for memory efficiency, use context managers (with statement), type hints for better code quality, use dataclasses for data containers, and profile with cProfile/line_profiler for optimization.",
    "introduce yourself": "A strong self-introduction covers: 1) Your name and current role, 2) Total years of experience, 3) Key technical skills relevant to the position, 4) Notable achievements or projects with impact metrics, 5) Why you're interested in this opportunity. Keep it concise (2-3 minutes), quantify achievements (e.g., 'reduced latency by 40%'), and tailor it to the job description.",
    "yourself": "A strong self-introduction covers: 1) Your name and current role, 2) Total years of experience, 3) Key technical skills relevant to the position, 4) Notable achievements or projects with impact metrics, 5) Why you're interested in this opportunity. Keep it concise (2-3 minutes), quantify achievements (e.g., 'reduced latency by 40%'), and tailor it to the job description.",
    "strength": "When discussing strengths, pick 2-3 relevant to the role with concrete examples: e.g., 'Problem-solving — I debugged a memory leak that reduced server crashes by 90%', 'Collaboration — I led cross-functional teams across 3 time zones', 'Continuous learning — I completed AWS certification while delivering project milestones on time'.",
    "weakness": "A good weakness answer: choose a real weakness you've actively improved (e.g., 'I used to struggle with delegating tasks — I've since used project management tools and regular 1:1s to better distribute work'). Avoid clichés like 'I work too hard'. Show self-awareness and a growth mindset.",
    "technical risk": "Technical risk identification: use risk matrices (probability × impact), architecture reviews, threat modeling (STRIDE), dependency analysis, and proof-of-concept spikes. Mitigation strategies: fallback implementations, feature flags, phased rollouts, vendor redundancy, and maintaining runbooks for known failure scenarios.",
    "debug": "Debugging production issues requires a systematic approach: 1) Verify the problem and scope, 2) Check recent deployments or changes, 3) Analyze logs (Kibana, Datadog) and metrics, 4) Reproduce the issue locally if possible, 5) Isolate the component causing the failure. Always write a post-mortem and add tests to prevent regression.",
    "solid": "SOLID principles are: Single Responsibility (one reason to change), Open/Closed (open for extension, closed for modification), Liskov Substitution (subtypes must be substitutable for base types), Interface Segregation (small, specific interfaces), and Dependency Inversion (depend on abstractions, not concretions). They ensure code is maintainable.",
    "architecture": "When comparing microservices vs monoliths, monoliths are easier to develop and deploy initially but harder to scale. Microservices offer independent scaling and deployment, but introduce network latency and distributed system complexity. Start monolithic and extract microservices as domains grow.",
    "version control": "Version control best practices: Commit often with clear, descriptive messages. Use feature branches (Git Flow or GitHub Flow). Always review code via Pull Requests. Rebase or squash before merging to keep history clean. Use tags for semantic versioning of releases.",
    "project": "For complex projects, explain the context, your specific role, the technical challenges faced (e.g., scale, latency, legacy code), and the exact solution you implemented. Always quantify the impact (e.g., 'reduced load time by 2 seconds', 'saved $5k/month').",
    "success": "Project success is measured using both technical and business metrics. Technical metrics include latency, uptime, error rates, and resource utilization. Business metrics include user adoption, retention, revenue impact, and customer satisfaction (NPS).",
    "learn": "When learning a new technology under pressure, the best approach is: 1) Read the official quickstart/docs, 2) Build a small proof-of-concept to understand core mechanics, 3) Understand the anti-patterns, and 4) Pair program with experienced team members while reviewing their code.",
    "code quality": "Code quality is ensured through a combination of: automated testing (unit, integration), static analysis tools (SonarQube, ESLint, Pylint), strict code reviews, CI/CD pipelines that block failing builds, and a strong engineering culture that values refactoring and clean code.",
    "disagree": "Handling technical disagreements requires empathy and data. Approach: 1) Understand their perspective fully, 2) Focus on the problem, not the person, 3) Evaluate trade-offs using objective metrics (performance, time-to-market), 4) Create a quick prototype if needed, and 5) Commit to the decision once made.",
    "excite": "What excites me about the future of software engineering is the integration of AI tools (like Copilot and Agentic AI) that augment developer productivity, allowing us to focus on higher-level architecture and solving complex business problems rather than writing boilerplate code."
}

def get_demo_correct_answer(question: str, answer: str) -> str:
    """Generate a question-specific correct answer based on question keywords."""
    question_lower = question.lower()
    answer_words = len(answer.split())

    # Find matching knowledge base entry
    for keyword, correct in CORRECT_ANSWERS_KB.items():
        if keyword in question_lower:
            return correct

    # If no keyword match, use DuckDuckGo search to dynamically find an answer
    words_in_q = question_lower.split()
    topic_words = [w for w in words_in_q if len(w) > 4 and w not in
                   {'about', 'would', 'could', 'should', 'describe', 'explain', 'discuss', 'approach', 'handle', 'improve', 'question', 'please', 'tell', 'your', 'have', 'with', 'that', 'this', 'from', 'what', 'when', 'where', 'which', 'while'}]
    topic = ' '.join(topic_words[:4]).title() if topic_words else question
    
    try:
        search_result = web_search_tool(f"What is {topic} software engineering interview answer", max_results=1)
        if search_result and "Search error" not in search_result and "No results" not in search_result:
            # Clean up the search result to look like an answer
            answer_text = search_result.split(":", 1)[-1].strip()
            return f"While in Demo Mode, here is a quick web reference for {topic}: {answer_text}"
    except:
        pass
        
    return (
        f"A strong answer for {topic} should include specific technical details, "
        f"trade-off analysis, and real-world examples from your past projects."
    )

def demo_evaluate(answer: str, question: str = "") -> tuple:
    """Evaluate answer and return (tech_score, comm_score, feedback, correct_answer)."""
    words = len(answer.split())
    answer_lower = answer.lower().strip()

    # Detect non-answers
    is_blank = answer_lower in {"", "i don't know", "i dont know", "don't know", "idk", "no idea", "not sure", "na", "n/a"} or words == 0
    is_too_short = words > 0 and words < 5

    correct = get_demo_correct_answer(question, answer)
    
    # If blank or non-answer, immediately 0
    if is_blank or is_too_short:
        return 0, 0, "You did not provide a meaningful answer. Please study this topic and attempt a detailed response.", correct

    # Stricter keyword matching for demo mode
    stop_words = {'about', 'would', 'could', 'should', 'describe', 'explain', 'discuss', 'approach', 'handle', 'improve', 'question', 'please', 'tell', 'your', 'have', 'with', 'that', 'this', 'from', 'what', 'when', 'where', 'which', 'while', 'there', 'their', 'project', 'system', 'using', 'based', 'experience', 'example', 'examples', 'time', 'years'}
    
    correct_words = set([w.lower() for w in correct.split() if len(w) > 4 and w.lower() not in stop_words])
    question_words = set([w.lower() for w in question.split() if len(w) > 4 and w.lower() not in stop_words])
    answer_words_set = set([w for w in answer_lower.split() if len(w) > 4 and w not in stop_words])
    
    target_keywords = correct_words.union(question_words)
    overlap = len(target_keywords.intersection(answer_words_set))
    
    if overlap == 0:
        if words < 15:
             return 0, 0, "Your answer seems incorrect or completely off-topic. You missed the core concepts entirely.", correct
        else:
             return 20, 40, "You spoke a lot, but your answer lacked the necessary technical keywords related to the question.", correct

    # Calculate dynamic score based on answer content
    # Overlap score: assume 4 solid matching keywords is a perfect 100
    overlap_score = min(100, int((overlap / 4.0) * 100))
    
    # Length score: assume 30 words is a good detailed length (100)
    length_score = min(100, int((words / 30.0) * 100))
    
    # Final technical score leans heavily on hitting the right keywords (75% weight)
    tech_score = int((overlap_score * 0.75) + (length_score * 0.25))
    
    # Communication score leans on length/fluency (60% weight)
    comm_score = int((overlap_score * 0.40) + (length_score * 0.60))
    
    # Generate dynamic feedback based on the exact calculated score
    if tech_score < 40:
        feedback = f"You scored {tech_score}/100. Your answer touched on a few right words, but lacked depth and clarity. Try to explain the concepts more clearly."
    elif tech_score < 70:
        feedback = f"Good attempt. You scored {tech_score}/100. You mentioned some correct concepts, but the answer could be more detailed and technically precise."
    elif tech_score < 90:
        feedback = f"Great answer! You scored {tech_score}/100. You covered the core concepts well, though adding a few more specific details would make it perfect."
    else:
        feedback = f"Excellent, detailed response! You scored {tech_score}/100 and captured the core concepts perfectly. Keep it up."
        
    return tech_score, comm_score, feedback, correct


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# LangGraph STATE + NODES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class InterviewState(TypedDict):
    # Session config (set once)
    domain: str
    difficulty: str
    candidate_name: str
    resume_session_id: Optional[str]
    openai_api_key: Optional[str]

    # Growing state (appended)
    messages: Annotated[List[BaseMessage], operator.add]
    feedbacks: Annotated[List[dict], operator.add]

    # Counters
    questions_asked: int
    total_score: int

    # Per-turn transients (overwritten each turn)
    resume_context: str
    current_question: str
    current_answer: str
    current_score: int
    current_feedback: str

    correct_answer: str
    language_feedback: str

    # Strict question deduplication — every asked question is stored here
    asked_questions: Annotated[List[str], operator.add]

    # Terminal flag
    is_complete: bool


class EvaluationResult(BaseModel):
    is_question: bool = Field(description="True if the candidate asked a question/clarification, False if they answered your interview question.")
    score: int = Field(description="Technical score (0-100). If is_question is True, return -1.")
    comm_score: int = Field(description="Communication score (0-100). If is_question is True, return -1.")
    feedback: str = Field(description="Feedback on their answer. If is_question is True, provide a smart, JARVIS-like answer to their question.")
    correct_answer: str = Field(description="ALWAYS provide the ideal/perfect correct answer to the interview question in 3-5 sentences, regardless of their score. If is_question is True, return an empty string.")
    language_feedback: str = Field(description="Evaluate their language fluency, grammar, and sentence structure. Point out specific mistakes if any. If their language is perfect, say 'Your language and fluency were excellent.' If is_question is True, return an empty string.")



# ── Node 1: Retrieve relevant resume context ──────────────────────────
def retrieve_context(state: InterviewState) -> dict:
    sid = state.get("resume_session_id")
    api_key = state.get("openai_api_key")
    context = ""
    
    if sid:
        if api_key and sid in vector_stores:
            vs = vector_stores[sid]
            llm = ChatOpenAI(model="gpt-4o", temperature=0, api_key=api_key)
            
            # Analyze history to formulate an intelligent search query
            hist_str = ""
            for m in state.get("messages", [])[-4:]:
                role = "Kerin" if isinstance(m, AIMessage) else "Candidate"
                hist_str += f"{role}: {m.content[:200]}\n"
                
            if not hist_str:
                query = state["domain"]
            else:
                prompt = ChatPromptTemplate.from_messages([
                    ("system", f"You are a retrieval agent for a {state['domain']} interview. Based on the recent conversation, generate a short, precise search query (max 6 words) to find NEW, unexplored topics in the candidate's resume that are relevant to what they just said. Do not search for the exact same thing they just answered."),
                    ("human", f"Recent Conversation:\n{hist_str}\n\nSearch Query:")
                ])
                query = (prompt | llm).invoke({}).content.strip().replace('"', '')
                
            print(f"DEBUG (Agentic RAG): LLM generated search query -> '{query}'")
            docs = vs.similarity_search(query, k=5)
            context = "\n\n---\n\n".join([d.page_content for d in docs])
        elif sid in resume_texts:
            context = resume_texts[sid][:3500]
            
    return {"resume_context": context}


# ── Node 2: Generate question + INTERRUPT for human answer ────────────
def generate_question(state: InterviewState) -> dict:
    q_num = state.get("questions_asked", 0) + 1
    context = state.get("resume_context", "")
    domain = state["domain"]
    difficulty = state.get("difficulty", "Medium")
    history = state.get("messages", [])
    api_key = state.get("openai_api_key")
    resume_sid = state.get("resume_session_id", "")
    
    # ── STRICT deduplication: use dedicated asked_questions list ──────────
    # This persists in LangGraph state for the ENTIRE session — never resets
    previously_asked = list(state.get("asked_questions", []))

    # Cross-session deduplication using global_resume_history
    # Include both the specific resume hash AND a global history of all questions asked
    global_past = []
    if resume_sid:
        global_past.extend(global_resume_history.get(resume_sid, []))
    global_past.extend(global_resume_history.get("GLOBAL_HISTORY", []))
    
    for q in global_past:
        if q not in previously_asked:
            previously_asked.append(q)

    # Q1 intro — User specifically requested 1st question MUST always be self-introduction
    INTRO_Q = "Hello! I'm your AI Interviewer. Please tell me about yourself and walk me through your background."

    if q_num == 1:
        question = INTRO_Q
    elif api_key:
        llm = ChatOpenAI(model="gpt-4o", temperature=0.85, api_key=api_key)
        
        prev_q_text = "\n".join([f"- {q}" for q in previously_asked]) if previously_asked else "None yet."

        # Build history string (last 6 messages = 3 Q&A pairs)
        hist_str = ""
        for m in history[-6:]:
            role = "Kerin" if isinstance(m, AIMessage) else "Candidate"
            hist_str += f"{role}: {m.content[:300]}\n"

        system_prompt = f"""You are Kerin, an advanced, hyper-intelligent AI assistant created by Tony Stark. You are conducting a {domain} ({difficulty} level) interview.
You have access to the candidate's resume below.

AGENTIC CONVERSATIONAL INTELLIGENCE RULES:
1. **Dynamic Follow-ups**: If the candidate's last answer was shallow or introduced an interesting concept, ask a piercing follow-up probing deeper.
2. **Resume & Coding Focus**: Ask questions based strictly on skills and projects in the resume. Include coding questions (algorithms, pseudo-code, logic problems).
3. **Pacing**: 
   - Q1: Warm up (intro)
   - Q2-Q4: Deep dive into resume projects
   - Q5-Q7: Coding questions, algorithms, and logic
   - Q8-Q10: System design and technical depth
4. **Tone**: Sophisticated, analytical, slightly witty (like JARVIS).
5. **ABSOLUTELY NO REPETITION**: The PREVIOUSLY ASKED QUESTIONS list is law. NEVER ask anything similar. Each question must cover a completely new angle.
6. Return ONLY the exact question text — no preamble, no numbering."""

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", f"Resume Context:\n{context}\n\nPREVIOUSLY ASKED QUESTIONS (DO NOT REPEAT ANY OF THESE):\n{prev_q_text}\n\nRecent Conversation:\n{hist_str}\n\nGenerate question #{q_num}:")
        ])
        
        # AGENTIC VALIDATION LOOP: regenerate if too similar to past questions
        max_attempts = 3
        question = ""
        for attempt in range(max_attempts):
            result = (prompt | llm).invoke({})
            temp_q = result.content.strip()
            
            is_similar = False
            temp_words = set([w.lower() for w in temp_q.split() if len(w) > 4])
            for past_q in previously_asked:
                past_words = set([w.lower() for w in past_q.split() if len(w) > 4])
                if temp_words and past_words:
                    overlap = len(temp_words.intersection(past_words)) / max(len(temp_words), len(past_words))
                    if overlap > 0.35:
                        is_similar = True
                        break
            
            if not is_similar or attempt == max_attempts - 1:
                question = temp_q
                break
            else:
                print(f"DEBUG: Question rejected (too similar). Attempt {attempt+1}/{max_attempts}")
                prompt = ChatPromptTemplate.from_messages([
                    ("system", system_prompt),
                    ("human", f"Resume Context:\n{context}\n\nPREVIOUSLY ASKED QUESTIONS:\n{prev_q_text}\n\nREJECTED (too similar to past): {temp_q}\n\nYou MUST pick a COMPLETELY DIFFERENT topic. Generate question #{q_num}:")
                ])
    else:
        # Demo mode — pass the exact list of already-asked questions
        question = get_demo_question(domain, q_num, context, history=previously_asked)

    # Save to per-resume history (for future cross-session reference if needed)
    if resume_sid:
        if resume_sid not in global_resume_history:
            global_resume_history[resume_sid] = []
        if question not in global_resume_history[resume_sid]:
            global_resume_history[resume_sid].append(question)
    save_resume_history(global_resume_history)

    answer = interrupt({"question": question, "question_number": q_num})

    return {
        "messages": [AIMessage(content=question)],
        "asked_questions": [question],   # appended to state — never lost
        "current_question": question,
        "current_answer": answer,
        "questions_asked": q_num,
    }


# ── Node 3: Evaluate the candidate's answer ───────────────────────────
def evaluate_answer(state: InterviewState) -> dict:
    answer = state.get("current_answer", "")
    question = state.get("current_question", "")
    context = state.get("resume_context", "")
    domain = state["domain"]
    api_key = state.get("openai_api_key")

    if api_key:
        llm = ChatOpenAI(model="gpt-4o", temperature=0.2, api_key=api_key)

        # ── AGENTIC: Detect code blocks and fact-check claims ────────
        agent_context = ""

        # 1. If answer contains code, run it and capture result
        code_match = re.search(r'```(?:python)?\n?(.*?)```', answer, re.DOTALL)
        if code_match:
            code_snippet = code_match.group(1).strip()
            exec_result = python_repl_tool(code_snippet)
            agent_context += f"\n\n[CODE EXECUTION RESULT]\n{exec_result}"
            print(f"DEBUG Agentic: Executed candidate code → {exec_result[:100]}")

        # 2. If answer mentions specific technologies/libraries, fact-check the first one
        tech_mentions = re.findall(r'\b([A-Z][a-zA-Z0-9]+(?:JS|AI|ML|DB|QL)?(?:\.[a-zA-Z]+)?)\b', answer)
        if tech_mentions and DDGS_AVAILABLE:
            query_term = tech_mentions[0]
            # Only search if it looks like a niche tech term (not common words)
            if len(query_term) > 3 and query_term not in {"The", "This", "That", "For", "With", "When", "What", "How", "And", "But"}:
                search_result = web_search_tool(f"{query_term} technology overview 2024", max_results=2)
                agent_context += f"\n\n[WEB SEARCH: '{query_term}']\n{search_result}"
                print(f"DEBUG Agentic: Web searched '{query_term}'")

        prompt = ChatPromptTemplate.from_messages([
            ("system", f"""You are Kerin, an advanced agentic AI evaluating a {domain} interview.
You have access to AGENTIC TOOLS — you can search the web and run code. Any tool results are provided below in the candidate's context.

Analyze the user's input:
- If they are ANSWERING your interview question:
  * Evaluate their technical accuracy (use CODE EXECUTION RESULT and WEB SEARCH data if available) and assign a technical score (0-100).
  * CRITICAL RULE: If the user's answer is completely wrong, technically incorrect, or irrelevant, you MUST assign a score of 0. Do not give partial points for wrong answers. Give a score > 0 ONLY if the answer is genuinely correct.
  * Evaluate their communication, grammar, sentence structure, and fluency, and assign a comm_score (0-100).
  * Provide comprehensive, intelligent feedback on their technical answer. Reference code execution results or search facts if available.
  * ALWAYS provide the ideal, perfect correct answer to the interview question in the correct_answer field, regardless of their score.
  * In the language_feedback field, list any grammatical errors, fluency issues, or sentence structure mistakes.
- If they are ASKING YOU a question:
  * Provide a highly intelligent, polite, JARVIS-style answer using your knowledge and the web search results.
  * Set is_question=True, score=-1, comm_score=-1, correct_answer="", language_feedback=""."""),
            ("human", f"Interview Question: {question}\nCandidate Input: {answer}\nResume Context: {context[:600]}{agent_context}")
        ])
        eval_llm = llm.with_structured_output(EvaluationResult)
        try:
            result = eval_llm.invoke(prompt.format_messages())
            score = result.score
            comm_score = result.comm_score
            feedback = result.feedback
            is_question = result.is_question
            correct_answer = result.correct_answer
            if not correct_answer or len(correct_answer.strip()) < 5:
                correct_answer = f"The ideal answer to this question should include specific technical details, trade-off analysis, and real-world examples from your past projects."
            language_feedback = result.language_feedback or ""
        except Exception as e:
            print("Evaluation Error:", e)
            score, comm_score, feedback, correct_answer = demo_evaluate(answer, question)
            is_question = False
            language_feedback = ""
    else:
        score, comm_score, feedback, correct_answer = demo_evaluate(answer, question)
        is_question = False
        language_feedback = ""

    if is_question:
        return {
            "messages": [HumanMessage(content=answer), AIMessage(content=feedback)],
            "feedbacks": [],
            "current_score": -1,
            "current_feedback": feedback,
            "total_score": state.get("total_score", 0),
            "questions_asked": max(1, state.get("questions_asked", 1) - 1)
        }
    else:
        fb_record = {
            "question_number": state["questions_asked"],
            "question": question,
            "answer": answer,
            "score": score,
            "comm_score": comm_score,
            "feedback": feedback,
            "correct_answer": correct_answer,
            "language_feedback": language_feedback,
        }
        return {
            "messages": [HumanMessage(content=answer)],
            "feedbacks": [fb_record],
            "current_score": score,
            "current_feedback": feedback,
            "correct_answer": correct_answer,
            "language_feedback": language_feedback,
            "total_score": state.get("total_score", 0) + score,
        }


# ── Edge: decide whether to continue or end ───────────────────────────
def should_continue(state: InterviewState) -> str:
    q_asked = state.get("questions_asked", 0)
    context = state.get("resume_context", "")

    # Always ask at least 10
    if q_asked < 10:
        return "continue"

    # Hard cap at 20 to prevent infinite loops
    if q_asked >= 20:
        return "end"

    api_key = state.get("openai_api_key")
    if api_key:
        llm = ChatOpenAI(model="gpt-4o", temperature=0, api_key=api_key)
        feedbacks = state.get("feedbacks", [])
        topics = [f["question"][:80] for f in feedbacks[-5:]]
        decision = llm.invoke(
            f"Interview context: {context[:400]}\n"
            f"Questions asked: {q_asked}\n"
            f"Recent topics: {topics}\n"
            f"Should we ask more questions? Answer ONLY 'continue' or 'end'."
        ).content.strip().lower()
        return "continue" if "continue" in decision else "end"
    else:
        # Demo: continue until 15 if resume has good content
        if q_asked < 15 and len(context) > 800:
            return "continue"
        return "end"


# ── Node 4: Mark session complete ─────────────────────────────────────
def end_session(state: InterviewState) -> dict:
    return {"is_complete": True}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# BUILD LangGraph
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def build_graph():
    builder = StateGraph(InterviewState)

    builder.add_node("retrieve_context", retrieve_context)
    builder.add_node("generate_question", generate_question)
    builder.add_node("evaluate_answer", evaluate_answer)
    builder.add_node("end_session", end_session)

    builder.add_edge(START, "retrieve_context")
    builder.add_edge("retrieve_context", "generate_question")
    builder.add_edge("generate_question", "evaluate_answer")
    builder.add_conditional_edges(
        "evaluate_answer",
        should_continue,
        {"continue": "retrieve_context", "end": "end_session"},
    )
    builder.add_edge("end_session", END)

    checkpointer = MemorySaver()
    return builder.compile(checkpointer=checkpointer)

interview_graph = build_graph()
print("LangGraph interview agent compiled successfully.")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# FastAPI App
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

app = FastAPI(title="InterviewAI LangGraph Engine v3.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Pydantic models ───────────────────────────────────────────────────
class InterviewSetup(BaseModel):
    name: str
    experience: str
    domain: str
    difficulty: str = "Medium"
    resume_session_id: Optional[str] = None
    openai_api_key: Optional[str] = None


class AnswerPayload(BaseModel):
    session_id: str
    answer: str


class OTPRequest(BaseModel):
    email: str

class OTPVerify(BaseModel):
    email: str
    otp: str

# ── OTP Email Configuration ──────────────────────────────────────────
import smtplib
from email.message import EmailMessage

EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD") # e.g. Gmail App Password
otp_store = {} # Temporary in-memory store: email -> otp

def send_otp_email(to_email: str, otp: str) -> bool:
    if not EMAIL_ADDRESS or not EMAIL_PASSWORD:
        print(f"\n[MOCK EMAIL SENT TO {to_email}]: Your OTP is {otp}\n")
        # In real life, return False or throw error if credentials aren't set
        # But for development without .env, we'll return True so frontend works
        return True
    
    try:
        msg = EmailMessage()
        msg['Subject'] = 'Your AI Interview Coach Password Reset OTP'
        msg['From'] = f"AI Interview Coach <{EMAIL_ADDRESS}>"
        msg['To'] = to_email
        msg.set_content(f"Hello,\n\nYour OTP for password reset is: {otp}\n\nIf you did not request this, please ignore this email.")
        
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            smtp.send_message(msg)
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False


# ── Helpers ───────────────────────────────────────────────────────────
def _get_interrupted_question(config: dict) -> Optional[dict]:
    """Extract the interrupted question from the graph state."""
    try:
        state = interview_graph.get_state(config)
        if state.tasks:
            for task in state.tasks:
                for intr in task.interrupts:
                    return intr.value  # {"question": ..., "question_number": ...}
    except Exception as e:
        print(f"[get_interrupted_question] {e}")
    return None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ENDPOINTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.get("/api/health")
def health():
    return {"status": "ok", "engine": "LangGraph v3.0"}

@app.post("/api/send-otp")
def send_otp_route(req: OTPRequest):
    import random
    email = req.email.lower()
    otp = str(random.randint(100000, 999999))
    otp_store[email] = otp
    
    success = send_otp_email(email, otp)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to send email. Check SMTP configuration.")
    return {"message": f"OTP sent to {email}"}

@app.post("/api/verify-otp")
def verify_otp_route(req: OTPVerify):
    email = req.email.lower()
    if email not in otp_store:
        raise HTTPException(status_code=400, detail="No OTP requested for this email.")
    if otp_store[email] != req.otp:
        raise HTTPException(status_code=400, detail="Invalid OTP.")
    
    # Valid
    del otp_store[email]
    return {"message": "OTP verified successfully."}


@app.post("/api/upload_resume")
def upload_resume(file: UploadFile = File(...), x_openai_key: Optional[str] = Header(None)):
    print(f"DEBUG: Started upload_resume for {file.filename}")
    suffix = ".pdf" if file.filename.lower().endswith(".pdf") else ".txt"

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        print("DEBUG: Reading file...")
        content = file.file.read()
        resume_sid = hashlib.md5(content).hexdigest()
        print(f"DEBUG: Read {len(content)} bytes, hash: {resume_sid}")
        tmp.write(content)
        tmp_path = tmp.name

    raw_text = ""
    indexed = False
    try:
        print(f"DEBUG: Loading document with suffix {suffix}")
        if suffix == ".pdf":
            from langchain_community.document_loaders import PyPDFLoader
            loader = PyPDFLoader(tmp_path)
        else:
            from langchain_community.document_loaders import TextLoader
            loader = TextLoader(tmp_path, encoding="utf-8")

        print("DEBUG: Calling loader.load()")
        docs = loader.load()
        print(f"DEBUG: Loaded {len(docs)} documents")
        raw_text = "\n".join([d.page_content for d in docs])
        resume_texts[resume_sid] = raw_text[:5000]

        if x_openai_key:
            print("DEBUG: API key provided, splitting docs...")
            from langchain_text_splitters import RecursiveCharacterTextSplitter
            from langchain_openai import OpenAIEmbeddings
            from langchain_community.vectorstores import FAISS
            splitter = RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=100)
            chunks = splitter.split_documents(docs)
            print(f"DEBUG: Created {len(chunks)} chunks, generating embeddings...")
            embeddings = OpenAIEmbeddings(model="text-embedding-3-small", api_key=x_openai_key)
            vs = FAISS.from_documents(chunks, embeddings)
            vector_stores[resume_sid] = vs
            indexed = True
            print("DEBUG: FAISS indexing complete with text-embedding-3-small")
        else:
            print("DEBUG: No API Key provided, skipping FAISS")

    except Exception as e:
        print(f"[upload_resume] Error: {e}")
    finally:
        try:
            os.unlink(tmp_path)
            print("DEBUG: Deleted temp file")
        except Exception:
            pass

    print("DEBUG: Returning response")
    return {
        "resume_session_id": resume_sid,
        "filename": file.filename,
        "openai_enabled": bool(x_openai_key),
        "faiss_indexed": indexed,
        "text_length": len(raw_text),
        "message": "Resume indexed into FAISS vector store." if indexed else "Resume parsed in demo mode."
    }


@app.post("/api/setup_interview")
async def setup_interview(setup: InterviewSetup):
    """
    Initialize a new interview session.
    Starts the LangGraph agent, which runs until the first interrupt (first question ready).
    """
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    initial_state: InterviewState = {
        "domain": setup.domain,
        "difficulty": setup.difficulty,
        "candidate_name": setup.name,
        "resume_session_id": setup.resume_session_id,
        "openai_api_key": setup.openai_api_key,
        "messages": [],
        "feedbacks": [],
        "questions_asked": 0,
        "total_score": 0,
        "resume_context": "",
        "current_question": "",
        "current_answer": "",
        "current_score": 0,
        "current_feedback": "",
        "correct_answer": "",
        "language_feedback": "",
        "asked_questions": [],  # strict per-session deduplication list
        "is_complete": False,
    }

    try:
        # Run graph until it hits the first interrupt (question generated, waiting for answer)
        for _ in interview_graph.stream(initial_state, config, stream_mode="updates"):
            pass
    except Exception as e:
        print(f"[setup_interview] Graph stream error: {e}")

    # Extract first question from interrupt
    intr = _get_interrupted_question(config)
    first_question = intr.get("question", "Tell me about yourself.") if intr else "Tell me about yourself."

    return {
        "session_id": thread_id,
        "status": "Ready",
        "first_question": first_question,
        "question_number": 1,
        "minimum_questions": 10,
    }


@app.post("/api/submit_answer")
async def submit_answer(payload: AnswerPayload):
    """
    Submit candidate answer → resume LangGraph → get score, feedback, next question.
    """
    config = {"configurable": {"thread_id": payload.session_id}}

    # Validate session exists
    try:
        state_snapshot = interview_graph.get_state(config)
    except Exception:
        raise HTTPException(status_code=404, detail="Session not found. Please restart the interview.")

    current_state_values = state_snapshot.values
    q_asked_before = current_state_values.get("questions_asked", 0)

    try:
        # Resume graph with the candidate's answer
        for _ in interview_graph.stream(
            Command(resume=payload.answer),
            config,
            stream_mode="updates"
        ):
            pass
    except Exception as e:
        print(f"[submit_answer] Graph stream error: {e}")

    # Get updated state
    new_snapshot = interview_graph.get_state(config)
    new_values = new_snapshot.values

    score = new_values.get("current_score", 0)
    feedback = new_values.get("current_feedback", "")
    correct_answer = new_values.get("correct_answer", "")
    language_feedback = new_values.get("language_feedback", "")
    is_complete = new_values.get("is_complete", False)
    q_asked = new_values.get("questions_asked", q_asked_before)
    feedbacks = new_values.get("feedbacks", [])

    # Latest comm_score from last feedback record
    comm_score = feedbacks[-1].get("comm_score", score) if feedbacks else score

    # Check if graph is still interrupted (more questions remain)
    intr = _get_interrupted_question(config)
    next_question = None
    if intr and not is_complete:
        next_question = intr.get("question")

    # Graph ended naturally
    if not intr and not is_complete:
        is_complete = True

    return {
        "score": score,
        "comm_score": comm_score,
        "feedback": feedback,
        "correct_answer": correct_answer,
        "language_feedback": language_feedback,
        "next_question": next_question,
        "is_complete": is_complete,
        "question_number": q_asked,
        "questions_so_far": len(feedbacks),
    }


@app.get("/api/session_result/{session_id}")
def session_result(session_id: str):
    """Get the final results for a completed interview."""
    config = {"configurable": {"thread_id": session_id}}
    try:
        snapshot = interview_graph.get_state(config)
        values = snapshot.values
    except Exception:
        raise HTTPException(status_code=404, detail="Session not found.")

    feedbacks = values.get("feedbacks", [])
    scores = [f["score"] for f in feedbacks]
    comm_scores = [f.get("comm_score", f["score"]) for f in feedbacks]
    avg = round(sum(scores) / len(scores), 1) if scores else 0
    avg_comm = round(sum(comm_scores) / len(comm_scores), 1) if comm_scores else 0

    return {
        "session_id": session_id,
        "candidate_name": values.get("candidate_name", "Candidate"),
        "domain": values.get("domain", ""),
        "difficulty": values.get("difficulty", ""),
        "average_score": avg,
        "avg_comm_score": avg_comm,
        "total_questions": len(feedbacks),
        "feedbacks": feedbacks,
    }


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8001)

# AI Developer System Instructions for SuperMean Project

**Instructions for AI Models continuing SuperMean development**

## 🎯 Project Context

SuperMean is an AI agent orchestration platform with e-commerce integration capabilities. You are contributing to a structured development process with specific phases, commit requirements, and quality standards.

### Current System Status
- **Backend**: 95% complete (solid foundation)
- **Frontend**: 60% complete (active development focus)
- **E-Commerce**: 0% complete (future phases)
- **Production Ops**: 30% complete (upcoming phases)

## 🔧 Development Environment Setup

### Prerequisites
```bash
# Always work within the specified directory
cd /home/user/webapp

# Verify project structure
ls -la SuperMean/

# Check current git status
git status
git branch
```

### Required Tools
- **Backend**: Python 3.8+, FastAPI, PostgreSQL
- **Frontend**: Node.js 18+, React/Next.js, TypeScript
- **Testing**: Jest, Cypress, pytest
- **DevOps**: Docker, GitHub Actions

## 📋 MANDATORY Development Workflow

### 1. Phase Understanding
**BEFORE starting any work:**
```bash
# Read current phase documentation
cat DEVELOPMENT_MASTER_PLAN.md
cat SYSTEM_STATUS_SUMMARY.md

# Check active tasks
cat ToDo.md
```

### 2. Branch Management
```bash
# Always use the genspark_ai_developer branch
git checkout genspark_ai_developer
git pull origin genspark_ai_developer

# Verify you're on the correct branch
git branch
```

### 3. Development Process

#### A. Task Selection
- **PRIORITY ORDER**: Complete tasks in order of priority (CRITICAL → HIGH → MEDIUM → LOW)
- **PHASE FOCUS**: Stay within the current development phase
- **ATOMIC WORK**: Complete one specific task at a time

#### B. Implementation Standards

**Frontend Development (TypeScript/React):**
```typescript
// ✅ REQUIRED: Strict TypeScript
interface ComponentProps {
  data: DataType;
  onAction: (id: string) => void;
}

// ✅ REQUIRED: Error handling
const Component: React.FC<ComponentProps> = ({ data, onAction }) => {
  const [error, setError] = useState<string | null>(null);
  
  try {
    // Component logic
  } catch (err) {
    setError(err.message);
  }
};

// ✅ REQUIRED: Loading states
const [loading, setLoading] = useState(false);

// ✅ REQUIRED: Accessibility
<button 
  aria-label="Action description"
  role="button"
  tabIndex={0}
>
```

**Backend Development (Python/FastAPI):**
```python
# ✅ REQUIRED: Type hints
from typing import List, Optional
from pydantic import BaseModel, Field

# ✅ REQUIRED: Input validation
class RequestModel(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., regex=r'^[\w\.-]+@[\w\.-]+\.\w+$')

# ✅ REQUIRED: Error handling
@app.post("/api/endpoint")
async def endpoint(request: RequestModel):
    try:
        # Implementation
        return {"success": True}
    except Exception as e:
        logger.error(f"Endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Internal error")
```

#### C. Testing Requirements
**MANDATORY for all new code:**

```bash
# Frontend testing
cd SuperMean/frontend
npm test                    # Unit tests
npm run test:e2e           # E2E tests

# Backend testing  
cd SuperMean/backend
pytest                     # Unit tests
pytest integration_tests.py # Integration tests
```

**Test Coverage Standards:**
- **Unit Tests**: 90%+ for new components/functions
- **Integration Tests**: All API endpoints
- **E2E Tests**: Critical user workflows

### 4. MANDATORY Commit Process

#### A. Commit Requirements
**EVERY code change MUST be committed immediately after completion**

```bash
# Add changes
git add .

# Commit with conventional format
git commit -m "feat(frontend): implement error boundary system

- Add React error boundary component
- Create centralized error store with Zustand  
- Implement toast notifications for user feedback
- Add error retry mechanisms for API calls
- Include comprehensive error logging

Resolves: Phase 1A Day 1-2 tasks"

# Push immediately
git push origin genspark_ai_developer
```

#### B. Commit Message Format
```
type(scope): brief description

- Detailed bullet point 1
- Detailed bullet point 2
- Detailed bullet point 3

Additional context if needed
Resolves: [Phase/Task reference]
```

**Types**: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`  
**Scopes**: `frontend`, `backend`, `api`, `ui`, `auth`, `tests`, `docs`

### 5. Documentation Updates

**REQUIRED after each major task completion:**

```bash
# Update progress tracking
# Edit ToDo.md to mark tasks complete

# Update implementation notes
# Add to DEVELOPMENT_MASTER_PLAN.md if needed

# Document any issues
# Add to docs/ErrorLog.md if problems encountered
```

## 🎨 Phase-Specific Instructions

### Phase 1A: Frontend UI Foundation (CURRENT)

**Focus Areas:**
1. **Error Handling** (Days 1-2) - CRITICAL
2. **Loading States** (Days 3-4) - CRITICAL  
3. **Responsive Design** (Days 5-7) - HIGH
4. **Advanced Components** (Week 2) - MEDIUM

**Key Files to Work With:**
```
SuperMean/frontend/
├── components/           # UI components
├── store/               # Zustand stores  
├── services/            # API and WebSocket services
├── hooks/               # Custom React hooks
├── pages/               # Next.js pages
└── styles/              # CSS and styling
```

**Implementation Priority:**
1. **Error Boundary System**: Global error catching and user feedback
2. **Loading Infrastructure**: Consistent loading states across all components
3. **Responsive Polish**: Mobile-first design improvements
4. **Accessibility**: WCAG 2.1 AA compliance
5. **Testing Coverage**: Comprehensive test suite

### Phase 1B: Backend Security & Performance (NEXT)

**Focus Areas:**
1. **Security Hardening** - CRITICAL
2. **Performance Optimization** - HIGH
3. **API Enhancements** - HIGH

**Key Files to Work With:**
```
SuperMean/backend/
├── api/                 # FastAPI endpoints
├── middleware/          # Security and auth middleware
├── utils/               # Utility functions
└── tests/               # Backend tests
```

### Phase 2: Production Operations (FUTURE)

**Focus Areas:**
1. **Monitoring Setup** - CRITICAL
2. **Deployment Pipeline** - HIGH
3. **Infrastructure** - HIGH

### Phase 3: E-Commerce Integration (FUTURE)

**Focus Areas:**
1. **Shopping Agents** - HIGH
2. **Platform APIs** - HIGH  
3. **Shopping UI** - MEDIUM

## 🚨 Critical Guidelines

### DO's ✅
- **READ** existing code before modifying
- **TEST** all changes thoroughly
- **DOCUMENT** significant changes
- **COMMIT** every completed task
- **FOLLOW** TypeScript/Python best practices
- **MAINTAIN** consistent code style
- **CHECK** existing tests pass before committing
- **UPDATE** ToDo.md with progress

### DON'Ts ❌
- **DON'T** skip testing requirements
- **DON'T** commit broken code
- **DON'T** make changes outside current phase scope
- **DON'T** introduce new dependencies without justification
- **DON'T** modify core architecture without discussion
- **DON'T** leave TODO comments in production code
- **DON'T** commit without updating documentation

### Emergency Protocols 🚨
If you encounter **critical issues**:

1. **Document** the issue in `docs/ErrorLog.md`
2. **Create** a detailed issue description
3. **Revert** changes if they break existing functionality
4. **Commit** the revert with explanation
5. **Escalate** by updating ToDo.md with BLOCKED status

## 🔍 Quality Checkpoints

### Before Each Commit
```bash
# Frontend quality check
cd SuperMean/frontend
npm run lint              # ESLint check
npm run type-check        # TypeScript check
npm test                  # Unit tests
npm run build             # Build verification

# Backend quality check  
cd SuperMean/backend
flake8 .                  # Python linting
mypy .                    # Type checking
pytest                    # Tests
```

### Code Review Checklist
- [ ] TypeScript strict mode compliance
- [ ] Error handling implemented
- [ ] Loading states added
- [ ] Accessibility features included
- [ ] Tests written and passing
- [ ] Documentation updated
- [ ] Performance considerations addressed
- [ ] Security best practices followed

## 📊 Progress Tracking

### Daily Tasks
1. **Morning**: Review current phase tasks and priority
2. **Development**: Implement features following standards
3. **Testing**: Verify all changes work correctly
4. **Evening**: Commit progress and update documentation

### Weekly Goals
- Complete scheduled phase tasks
- Maintain test coverage above 90%
- Update project documentation
- Review and refine code quality

### Phase Completion Criteria
Each phase must meet specific success criteria before moving to the next phase. See DEVELOPMENT_MASTER_PLAN.md for detailed criteria.

## 🤖 AI-Specific Guidelines

### Context Management
- **ALWAYS** read existing files before making changes
- **UNDERSTAND** the current system state before implementing
- **VERIFY** your changes integrate properly with existing code
- **MAINTAIN** consistency with established patterns

### Code Generation Best Practices
- **REFERENCE** existing code patterns in the project
- **FOLLOW** established naming conventions
- **INCLUDE** proper error handling and type safety
- **ADD** comprehensive comments for complex logic

### Problem Solving Approach
1. **ANALYZE** the existing codebase structure
2. **IDENTIFY** the specific task requirements  
3. **PLAN** the implementation approach
4. **IMPLEMENT** following project standards
5. **TEST** thoroughly before committing
6. **DOCUMENT** the changes made

## 🎯 Success Metrics

### Individual Task Success
- [ ] Feature implemented correctly
- [ ] Tests passing
- [ ] Documentation updated
- [ ] Code review standards met
- [ ] Committed with proper message

### Phase Success
- [ ] All phase tasks completed
- [ ] Quality gates passed
- [ ] Performance benchmarks met
- [ ] User acceptance criteria satisfied
- [ ] Ready for next phase

Remember: **Quality over speed**. It's better to complete fewer tasks correctly than to rush through many tasks with poor quality.

---

## Quick Reference Commands

```bash
# Start development session
cd /home/user/webapp && git checkout genspark_ai_developer && git pull

# Check current status
git status && cat DEVELOPMENT_MASTER_PLAN.md | head -50

# Run tests
cd SuperMean/frontend && npm test
cd SuperMean/backend && pytest

# Commit changes
git add . && git commit -m "type(scope): description" && git push

# Check phase progress
grep -n "Phase 1A" DEVELOPMENT_MASTER_PLAN.md
```

Follow these instructions carefully to ensure consistent, high-quality development across all AI contributors to the SuperMean project.
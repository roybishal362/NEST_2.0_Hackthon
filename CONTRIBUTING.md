# Contributing to C-TRUST

Thank you for your interest in contributing to C-TRUST! This document provides guidelines for contributing to the project.

## Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Help maintain a positive environment

## Getting Started

1. Fork the repository
2. Clone your fork
3. Create a new branch for your feature
4. Make your changes
5. Test thoroughly
6. Submit a pull request

## Development Setup

See [SETUP.md](SETUP.md) for detailed installation instructions.

## Code Style

### Python

- Follow PEP 8 style guide
- Use type hints
- Write docstrings for all functions
- Maximum line length: 100 characters

```python
def calculate_dqi(agent_scores: List[float]) -> float:
    """
    Calculate Data Quality Index from agent scores.
    
    Args:
        agent_scores: List of scores from individual agents
        
    Returns:
        Normalized DQI score between 0 and 100
    """
    return sum(agent_scores) / len(agent_scores)
```

### TypeScript/React

- Use TypeScript for all new code
- Follow React best practices
- Use functional components with hooks
- Use meaningful variable names

```typescript
interface AgentScore {
  agentName: string;
  score: number;
  confidence: number;
}

const calculateAverageScore = (scores: AgentScore[]): number => {
  return scores.reduce((sum, s) => sum + s.score, 0) / scores.length;
};
```

## Testing

### Writing Tests

- Write tests for all new features
- Maintain test coverage above 80%
- Use descriptive test names
- Test edge cases

### Running Tests

```bash
# Backend tests
cd c_trust
pytest

# Frontend tests
cd c_trust/frontend
npm test
```

## Commit Messages

Use clear, descriptive commit messages:

```
feat: Add new agent for protocol deviation detection
fix: Resolve DQI calculation error for edge cases
docs: Update API documentation
test: Add property-based tests for feature extraction
refactor: Simplify consensus calculation logic
```

## Pull Request Process

1. **Update Documentation**: Ensure all documentation is updated
2. **Add Tests**: Include tests for new features
3. **Run Tests**: Ensure all tests pass
4. **Update CHANGELOG**: Add entry for your changes
5. **Request Review**: Tag relevant reviewers

### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] Tests pass locally
```

## Project Structure

```
c_trust/
├── src/
│   ├── agents/          # AI agents
│   ├── data/            # Data processing
│   ├── intelligence/    # LLM and DQI engine
│   └── api/             # FastAPI endpoints
├── tests/
│   ├── unit/            # Unit tests
│   ├── integration/     # Integration tests
│   └── property/        # Property-based tests
├── frontend/
│   ├── src/
│   │   ├── components/  # React components
│   │   ├── pages/       # Page components
│   │   ├── hooks/       # Custom hooks
│   │   └── api/         # API client
│   └── tests/           # Frontend tests
└── scripts/             # Utility scripts
```

## Adding New Features

### Adding a New Agent

1. Create agent class in `src/agents/signal_agents/`
2. Inherit from `BaseAgent`
3. Implement `analyze()` method
4. Add tests in `tests/unit/`
5. Update agent registry
6. Update documentation

Example:

```python
from src.intelligence.base_agent import BaseAgent

class NewAgent(BaseAgent):
    def __init__(self, llm_client):
        super().__init__(
            name="New Agent",
            description="Analyzes new aspect",
            llm_client=llm_client
        )
    
    async def analyze(self, features: Dict) -> Dict:
        # Implementation
        pass
```

### Adding a New API Endpoint

1. Add endpoint in `src/api/main.py`
2. Add tests in `tests/api/`
3. Update API documentation
4. Add frontend integration

Example:

```python
@app.get("/api/new-endpoint")
async def new_endpoint():
    """
    New endpoint description.
    
    Returns:
        Response data
    """
    return {"status": "success"}
```

### Adding a New Frontend Component

1. Create component in `src/components/`
2. Add TypeScript types
3. Add tests
4. Update parent components
5. Update documentation

Example:

```typescript
interface NewComponentProps {
  data: DataType;
  onAction: () => void;
}

export const NewComponent: React.FC<NewComponentProps> = ({ data, onAction }) => {
  return (
    <div>
      {/* Component implementation */}
    </div>
  );
};
```

## Documentation

- Update README.md for major changes
- Update TECHNICAL_DOCUMENTATION.md for architecture changes
- Add inline comments for complex logic
- Update API documentation
- Add examples for new features

## Performance Guidelines

- Optimize database queries
- Use caching where appropriate
- Minimize API calls
- Lazy load components
- Profile before optimizing

## Security Guidelines

- Never commit API keys or secrets
- Validate all user inputs
- Use parameterized queries
- Sanitize data before display
- Follow OWASP guidelines

## Questions?

- Check existing documentation
- Review similar implementations
- Ask in pull request comments
- Consult technical documentation

## License

By contributing, you agree that your contributions will be licensed under the same license as the project.

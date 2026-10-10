# REALITY.EXE BACKEND ENGINEERING RULES

You are modifying a hackathon project that already has documented architecture.

## BEFORE ANY CHANGE:
1. Inspect the repository.
2. Read the relevant documentation.
3. Understand existing code.
4. Reuse existing abstractions.
5. Do not replace working systems without reason.

## NEVER:
- delete working functionality without approval
- rewrite the entire backend unnecessarily
- hardcode secrets
- hardcode AI model names
- bypass validation
- bypass authentication
- trust LLM output blindly
- award XP directly from controllers
- expose filesystem paths
- store plaintext passwords
- create duplicate state transitions
- create duplicate XP transactions
- use mock data in production
- add random dependencies
- create giant files
- put business logic inside route handlers

## ALWAYS:
- use services for business logic
- use repositories/data-access boundaries where appropriate
- use Pydantic schemas
- validate inputs
- validate AI outputs
- enforce authorization
- write tests
- update documentation when contracts change
- preserve backward compatibility
- run tests after changes
- report what changed

## REALITY.EXE PRINCIPLE:

The AI creates the game.
The backend enforces the rules.
The safety system protects the player.
The database remembers the adventure.
The frontend gets the player outside.

# ClickUp Clone — Backend

A workspace-based project and task management backend built with **FastAPI, Strawberry GraphQL, PostgreSQL, and SQLAlchemy's async ORM**. Amazon Cognito handles user authentication, while PostgreSQL stores application users, workspaces, memberships, roles, permissions, tasks, tags, comments, invitations, and activity history.

> **Project scope:** This repository contains the backend API. The current repository does not include a frontend, Docker Compose configuration, automated test suite, or deployment manifests.

## Contents

- [Overview](#overview)
- [Features](#features)
- [Technology stack](#technology-stack)
- [Architecture](#architecture)
- [Project structure](#project-structure)
- [Authentication and authorization](#authentication-and-authorization)
- [Domain model](#domain-model)
- [Getting started](#getting-started)
- [Database migrations](#database-migrations)
- [GraphQL API](#graphql-api)
- [Configuration](#configuration)
- [Operational notes](#operational-notes)
- [License](#license)

## Overview

The application organizes collaboration around workspaces. A workspace has members and workspace-scoped roles; members collaborate on tasks, assign work, add tags and comments, and review task activity.

The codebase is structured as a **modular monolith**. Business capabilities are grouped under `app/modules`, while shared application infrastructure—configuration, database sessions, logging, middleware, and GraphQL schema composition—is kept in dedicated packages.

## Features

### Authentication and user profiles

- Sign up, confirm registration, and resend Cognito confirmation codes.
- Authenticate through Amazon Cognito and handle token refresh and sign-out flows.
- Verify Cognito access-token signatures using the User Pool JWKS endpoint.
- Validate token issuer, expiry, token use, and app-client ID.
- Map the Cognito subject (`sub`) to a local application user.
- Reject tokens issued before a user's `tokens_valid_after` timestamp.
- Read the authenticated user's information and update profile data.

### Workspaces and membership

- Create workspaces with globally unique slugs.
- Provision the `OWNER`, `ADMIN`, and `MEMBER` roles when a workspace is created.
- Assign the workspace creator the `OWNER` role.
- Read and update workspace information.
- Invite users by email with a selected role.
- Accept, decline, revoke, and resend invitations.
- Read workspace members, update member roles, and remove members.
- Protect owner membership from ordinary member role-change and removal operations.
- Soft-delete workspaces.

Invitation records store a hash of the invitation token and an expiry timestamp rather than storing the raw token. The invitation service currently sets a seven-day expiry.

### Role-based access control (RBAC)

- Maintain a permission catalogue using keys such as `workspace.read`, `members.invite`, and `tasks.assign`.
- Map permissions to roles through the `role_permissions` table.
- Seed permission records and provision role policies during workspace creation.
- Check workspace membership and the required permission before protected service operations.

The permission catalogue and default role policies are defined in:

- `app/modules/authorization/permissions.py`
- `app/modules/authorization/role_policies.py`

### Tasks, tags, and collaboration

- Create, read, update, and soft-delete tasks.
- Restore soft-deleted tasks.
- Track task status: `TODO`, `IN_PROGRESS`, and `COMPLETED`.
- Track task priority: `LOW`, `MEDIUM`, `HIGH`, and `URGENT`.
- Store task descriptions and optional due dates.
- Support a single level of subtasks and validate parent-task workspace boundaries.
- Assign multiple workspace members to a task.
- Retrieve tasks assigned to the current user.
- Create workspace-scoped tags and associate reusable tags with tasks.
- Create, update, and soft-delete task comments; comment ownership is checked by the service.
- Record task activity for supported task, assignment, tag, and comment operations.
- Store activity change data using PostgreSQL JSONB.

## Technology stack

| Area | Technology |
|---|---|
| Language | Python |
| Web framework | FastAPI |
| ASGI server | Uvicorn |
| API style | GraphQL |
| GraphQL library | Strawberry GraphQL |
| Database | PostgreSQL |
| ORM | SQLAlchemy async ORM |
| PostgreSQL driver | Psycopg 3 |
| Migrations | Alembic |
| Settings | Pydantic Settings |
| Authentication | Amazon Cognito |
| AWS SDK | Boto3 |
| JWT verification | PyJWT and Cognito JWKS |
| Async execution | Python asyncio |

Pinned dependencies are listed in [requirements.txt](requirements.txt).

## Architecture

The application uses a layered, modular-monolith approach:

| Layer | Responsibility |
|---|---|
| GraphQL queries and mutations | Expose client operations and pass validated inputs to services |
| Types | Define GraphQL input and output types |
| Services | Apply business rules, validation, and authorization |
| Repositories | Encapsulate SQLAlchemy queries and persistence operations |
| Models | Define database tables and ORM mappings |
| Core and database | Provide configuration, logging, middleware, engine, and session management |

### Request lifecycle

1. A client sends a request to `POST /graphql`, optionally including an access token in the `Authorization: Bearer <token>` header.
2. FastAPI middleware handles request logging and assigns a request ID. CORS middleware applies the configured cross-origin policy.
3. Strawberry's context dependency obtains an asynchronous SQLAlchemy session.
4. If a bearer token is present, the application verifies the Cognito access token and resolves the local user using the token's `sub` claim.
5. The GraphQL context exposes the database session, authenticated claims (when valid), and access token to resolvers.
6. Resolvers delegate business operations to the relevant service.
7. Services enforce domain rules and call authorization checks for protected workspace operations.
8. Repositories read or modify PostgreSQL through SQLAlchemy.
9. The custom GraphQL router formats expected GraphQL errors and logs unexpected exceptions with the request ID.

### Error handling and request logging

- `RequestLoggingMiddleware` provides request-level logging and the `X-Request-ID` response header.
- Centralized logging is configured in `app/core/logging`.
- `CentralizedGraphQLRouter` returns a generic internal-server-error message for unexpected resolver exceptions while logging the underlying exception.
- Expected GraphQL errors retain their formatted error information and receive the request ID in their extensions.

## Project structure

The following tree reflects the current repository layout (with repetitive package initializer files omitted):

```text
ClickUp-Clone/
├── app/
│   ├── core/
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── logging/
│   │   └── middleware/
│   ├── db/
│   │   ├── base.py
│   │   └── session.py
│   ├── graphql/
│   │   ├── error_handler.py
│   │   └── schema.py
│   └── modules/
│       ├── auth/
│       ├── authorization/
│       ├── users/
│       ├── workspaces/
│       │   ├── models/
│       │   ├── mutations/
│       │   ├── queries/
│       │   ├── repositories/
│       │   ├── security/
│       │   └── services/
│       ├── tasks/
│       │   ├── enums/
│       │   ├── models/
│       │   ├── mutations/
│       │   ├── queries/
│       │   ├── repository/
│       │   ├── services/
│       │   └── types/
│       └── tags/
│           ├── models/
│           ├── mutations/
│           ├── queries/
│           ├── repository/
│           ├── services/
│           └── types/
├── migrations/
│   └── versions/
├── alembic.ini
├── main.py
├── requirements.txt
├── LICENSE
└── .gitignore
```

### Important entry points

| File | Purpose |
|---|---|
| `main.py` | Creates the FastAPI application, configures middleware, mounts GraphQL, and exposes the health endpoint |
| `app/core/config.py` | Loads application settings from environment variables and `.env` |
| `app/db/session.py` | Creates the async SQLAlchemy engine, session factory, and database dependency |
| `app/graphql/schema.py` | Composes module query and mutation classes into the Strawberry schema |
| `app/graphql/error_handler.py` | Implements centralized GraphQL error formatting |
| `migrations/env.py` | Connects Alembic to application settings and model metadata |

## Authentication and authorization

### Authentication with Cognito

Amazon Cognito is the identity provider. The backend verifies access tokens using the User Pool's JWKS public keys. Token verification checks the signature, issuer, expiry, required claims, `token_use=access`, and configured Cognito app-client ID.

For authenticated GraphQL operations, send the Cognito **access token**:

```http
Authorization: Bearer <COGNITO_ACCESS_TOKEN>
Content-Type: application/json
```

The application resolves the local user from the verified Cognito `sub` claim. Resolvers can use the authentication helper in `app/modules/auth/authorization.py` to require an authenticated user.

### Workspace RBAC

Authorization is scoped to a workspace:

1. Resolve the user's role in the requested workspace.
2. Reject the request if the user is not a workspace member.
3. Check whether the role is mapped to the requested permission.
4. Reject the operation when the permission is not granted.

Default role policies are defined in code and provisioned for each new workspace.

| Role | Intended access |
|---|---|
| OWNER | Full workspace, member, role/permission, task, comment, and tag access |
| ADMIN | Workspace read, member read/invite, and task, comment, and tag operations |
| MEMBER | Workspace read, task create/read/update, and comment create/read |

The exact permission mapping is defined in `ROLE_POLICIES`; refer to that file for the source of truth.

## Domain model

The principal persisted entities include:

| Entity | Purpose |
|---|---|
| Users | Local application identities linked to Cognito subjects |
| User profiles | User display and profile information |
| Workspaces | Collaboration boundaries with unique slugs |
| Workspace members | Associates users with workspaces and roles |
| Roles | Workspace-specific role definitions |
| Permissions | Catalogue of permission keys |
| Role permissions | Maps roles to permissions within a workspace |
| Workspace invitations | Tracks invitees, assigned roles, token hashes, status, and expiry |
| Tasks | Workspace tasks with status, priority, due date, and optional parent task |
| Task assignees | Associates multiple users with tasks |
| Tags and task tags | Reusable workspace tags and task-tag associations |
| Task comments | User-authored task discussion |
| Task history | Task activity records with structured change details |

Invitation status, task status, and task priority use enumerated values. Task activity details are stored as JSONB.

## Getting started

### Prerequisites

- Python version compatible with the pinned packages in `requirements.txt`.
- PostgreSQL.
- An Amazon Cognito User Pool and app client configured for the authentication flows used by the application.
- AWS credentials/configuration for the Cognito operations used by the backend.

### 1. Clone the repository

```bash
git clone https://github.com/Hariprasaath-meyc/ClickUp-Clone.git
cd ClickUp-Clone
```

### 2. Create and activate a virtual environment

**Windows PowerShell**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**macOS / Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install pydantic-settings
```

The application imports `pydantic-settings` in its settings module; install it explicitly because it is not currently listed in `requirements.txt`.

### 4. Configure environment variables

Create a `.env` file in the repository root:

```dotenv
DATABASE_URL=postgresql+psycopg://<db_user>:<db_password>@localhost:5432/<database_name>

AWS_REGION=ap-south-1
COGNITO_CLIENT_ID=<your_cognito_app_client_id>
COGNITO_CLIENT_SECRET=<your_cognito_app_client_secret>
COGNITO_USER_POOL_ID=<your_cognito_user_pool_id>
```

Notes:

- `DATABASE_URL` is required by the application settings.
- `COGNITO_USER_POOL_ID` is required by the token verification module.
- `AWS_REGION` defaults to `ap-south-1` when omitted.
- `COGNITO_CLIENT_SECRET` is needed when the Cognito app client is configured with a secret.
- Keep `.env` out of version control. Never commit real credentials or secrets.

The database URL must be compatible with SQLAlchemy's async engine and the Psycopg driver.

### 5. Create the PostgreSQL database

Create an empty database matching the name in `DATABASE_URL`. For example:

```sql
CREATE DATABASE clickup_clone;
```

### 6. Apply migrations

```bash
alembic upgrade head
```

### 7. Start the application

```bash
uvicorn main:app --reload
```

The development server uses the default Uvicorn address unless configured otherwise:

- GraphQL API: http://127.0.0.1:8000/graphql
- Health check: http://127.0.0.1:8000/health

The current CORS configuration in `main.py` allows the Vite development origin `http://localhost:5173`, with POST and OPTIONS methods and the Content-Type and Authorization headers.

## Database migrations

Alembic is configured in `alembic.ini` and `migrations/env.py`. The migration environment imports the ORM models and uses the application's configured database URL and SQLAlchemy metadata.

Common commands:

```bash
# Apply all pending migrations
alembic upgrade head

# Show the current database revision
alembic current

# Show migration history
alembic history

# Generate a migration from model changes
alembic revision --autogenerate -m "describe the schema change"

# Roll back one revision
alembic downgrade -1
```

Review autogenerated migration scripts before applying them, especially when changing enums, foreign keys, constraints, or columns that may contain existing data.

## GraphQL API

The Strawberry schema is composed in `app/graphql/schema.py`. It combines query and mutation classes from the authentication, user, workspace, membership, invitation, task, task-comment, task-history, and tag modules.

The endpoint is:

```text
POST /graphql
```

A simple query available in the schema:

```graphql
query {
  hello
}
```

For authenticated operations, include the Cognito access token in the Authorization header. Consult the relevant module's mutation, query, and type definitions for the exact operation names and input/output fields.

## Configuration

| Variable | Required | Description |
|---|---:|---|
| `DATABASE_URL` | Yes | Async SQLAlchemy PostgreSQL connection URL using Psycopg |
| `AWS_REGION` | No | Cognito region; defaults to `ap-south-1` |
| `COGNITO_CLIENT_ID` | For token verification | Cognito app-client ID checked against the access token |
| `COGNITO_CLIENT_SECRET` | If app client has a secret | Used by Cognito authentication flows that require a secret hash |
| `COGNITO_USER_POOL_ID` | Yes for token verification | Used to construct the Cognito issuer and JWKS URL |

## Operational notes

- This repository currently contains backend code only; no frontend is included.
- The FastAPI application mounts the GraphQL router at `/graphql` and exposes `/health`.
- The async SQLAlchemy session is provided through the GraphQL context dependency.
- Task and comment deletion use soft-delete behavior in the service/repository layer.
- Task restoration is implemented for soft-deleted tasks.
- Workspace creation provisions the default roles, permission mappings, and creator's OWNER membership.
- No Docker Compose configuration, automated test suite, or deployment workflow is present in the current repository tree.
- The current `requirements.txt` does not include `pydantic-settings`, although `app/core/config.py` imports it. It is installed explicitly in the setup instructions above; consider adding it to the dependency file.

## License

This project is licensed under the **MIT License**. See [LICENSE](LICENSE) for the complete license text.

# ClickUp Clone

A backend implementation of a workspace-based project and task management platform, built with **FastAPI, Strawberry GraphQL, PostgreSQL, and SQLAlchemy's async ORM**. Authentication is delegated to **Amazon Cognito**, while application users, workspaces, memberships, roles, permissions, tasks, and activity records are persisted in PostgreSQL.

> This repository currently contains the backend only. A frontend, Docker Compose setup, and deployment manifests are not present in the inspected repository tree.

## Contents

- [Overview](#overview)
- [Features](#features)
- [Technology stack](#technology-stack)
- [Architecture](#architecture)
- [Project structure](#project-structure)
- [Authentication and request lifecycle](#authentication-and-request-lifecycle)
- [Authorization model](#authorization-model)
- [Domain model](#domain-model)
- [Getting started](#getting-started)
- [Database migrations](#database-migrations)
- [Running the application](#running-the-application)
- [GraphQL API](#graphql-api)
- [Configuration reference](#configuration-reference)
- [Implementation notes](#implementation-notes)

## Overview

ClickUp Clone organizes work around workspaces. A workspace contains members, workspace-scoped roles and permissions, tasks, tags, comments, and task activity history. Users authenticate through Cognito; the backend verifies Cognito access tokens and maps the authenticated Cognito identity to a local user record.

The codebase follows a **modular monolith** structure: domain capabilities are grouped into modules inside one FastAPI application, while shared infrastructure such as configuration, database sessions, middleware, and GraphQL schema composition lives under `app/core`, `app/db`, and `app/graphql`.

## Features

### Authentication and user profiles

- Sign up with email and password through Amazon Cognito.
- Confirm an account with the Cognito confirmation code and request a replacement code.
- Log in and receive Cognito access, ID, and refresh tokens.
- Refresh a session and log out through Cognito global sign-out.
- Verify access-token signature and claims using Cognito's JWKS endpoint.
- Require a verified Cognito email before the local user is created during login.
- Create or retrieve the local user using the Cognito subject (`sub`).
- Retrieve the authenticated user's profile and update profile details.

### Workspaces and membership

- Create workspaces with a unique slug.
- Create the predefined `OWNER`, `ADMIN`, and `MEMBER` roles when a workspace is created.
- Assign the creator the `OWNER` role.
- Read and update workspace information.
- Invite users to a workspace with a selected non-owner role.
- Accept, decline, revoke, and resend workspace invitations.
- View workspace membership, change a member's role, and remove a member.
- Prevent changing or removing the workspace owner through the member-role operations.

Invitations use a generated token; the stored invitation record contains a token hash and an expiry timestamp. The invitation service sets a seven-day expiry when creating an invitation.

### Role-based access control (RBAC)

- Define permissions using stable keys such as `tasks.create`, `tasks.assign`, and `members.invite`.
- Associate permissions with workspace roles through role-permission mappings.
- Seed permission records and apply the role policies when a workspace is created.
- Check workspace membership and the requested permission before protected service operations.

The predefined role policies are maintained in `app/modules/authorization/role_policies.py`. The permission catalogue is in `app/modules/authorization/permissions.py`.

### Tasks

- Create, read, update, and soft-delete workspace tasks.
- Track task status: `TODO`, `IN_PROGRESS`, and `COMPLETED`.
- Track task priority: `LOW`, `MEDIUM`, `HIGH`, and `URGENT`.
- Store optional descriptions and due dates.
- Support one level of subtasks; a subtask cannot itself have another subtask.
- Validate that a parent task belongs to the same workspace.
- Assign multiple workspace members to a task and remove assignments.
- Retrieve tasks assigned to the current user.

### Tags, comments, and activity history

- Create workspace-scoped tags as they are assigned to tasks.
- Reuse tags across tasks within the same workspace.
- Add and remove task-tag associations.
- Create, update, and soft-delete task comments; the service restricts comment edits and deletion to the comment author.
- Record task activity such as task creation, updates, deletion, assignment changes, tag changes, and comment changes.
- Store activity change details as PostgreSQL JSONB data.

## Technology stack

| Area | Technology |
|---|---|
| Web framework | FastAPI |
| ASGI server | Uvicorn |
| API | GraphQL |
| GraphQL implementation | Strawberry GraphQL |
| Database | PostgreSQL |
| ORM | SQLAlchemy async ORM |
| Database driver | Psycopg 3 |
| Schema migrations | Alembic |
| Configuration and validation | Pydantic / Pydantic Settings |
| Authentication provider | Amazon Cognito |
| AWS SDK | Boto3 |
| Token verification | PyJWT and Cognito JWKS |
| Async runtime | Python asyncio |

The exact pinned dependencies are maintained in [requirements.txt](requirements.txt).

## Architecture

The application is a modular monolith. Each business module owns its domain-specific GraphQL operations, services, repositories, types, and ORM models where applicable.

### Request flow

1. A client sends a GraphQL request to `/graphql`, usually with an `Authorization: Bearer <access-token>` header.
2. FastAPI middleware handles request logging; CORS middleware handles configured cross-origin requests.
3. The GraphQL context dependency obtains an asynchronous SQLAlchemy session and verifies the Cognito access token when one is supplied.
4. The context exposes the database session, verified user claims, and access token to GraphQL resolvers.
5. Resolvers validate authentication where required and call the relevant service.
6. Services enforce business rules and, for protected workspace operations, check membership and permissions.
7. Repositories perform database access through SQLAlchemy.
8. Strawberry returns the GraphQL response; centralized GraphQL error handling is configured through the custom router.

### Module responsibilities

| Layer | Responsibility |
|---|---|
| GraphQL queries and mutations | Define the client-facing API and translate inputs into service calls |
| Types | Define GraphQL input and output types |
| Services | Enforce business rules, validation, and authorization |
| Repositories | Encapsulate database queries and persistence |
| Models | Define SQLAlchemy ORM tables and relationships |
| Core / DB | Shared configuration, middleware, engine, and session management |

## Project structure

The following is a high-level map of the current repository. Some modules intentionally use slightly different internal layouts as they have evolved.

```text
ClickUp-Clone/
├── app/
│   ├── core/
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── logging/
│   │   └── middleware/
│   │       └── request_logging.py
│   ├── db/
│   │   ├── base.py
│   │   └── session.py
│   ├── graphql/
│   │   ├── error_handler.py
│   │   └── schema.py
│   └── modules/
│       ├── auth/
│       │   ├── authorization.py
│       │   ├── cognito.py
│       │   ├── mutation.py
│       │   ├── service.py
│       │   └── token_service.py
│       ├── authorization/
│       │   ├── permission_seeder.py
│       │   ├── permissions.py
│       │   ├── role_policies.py
│       │   └── service.py
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
└── .gitignore
```

## Authentication and request lifecycle

Amazon Cognito is the identity provider. The application does not treat an arbitrary JWT as authenticated: `app/modules/auth/token_service.py` verifies the signature using the Cognito JWKS keys, checks the issuer and expiry, requires the `token_use` claim to be `access`, and checks the Cognito app-client ID.

For authenticated GraphQL requests:

- Send the Cognito **access token** in the Authorization header.
- The GraphQL context places verified claims in `current_user`.
- Resolvers use `require_authenticated_user` to reject unauthenticated access.
- The local user is looked up by Cognito `sub`, rather than trusting a client-supplied user ID.

The login mutation also checks the Cognito identity's verified email before creating or retrieving the local application user.

## Authorization model

Authorization is workspace-scoped. A user must first be a member of the target workspace. The role assigned to that membership determines the permissions available to the user.

The default role policies currently defined in the code are:

| Role | General access |
|---|---|
| OWNER | Full workspace, membership, role/permission, task, comment, and tag permissions |
| ADMIN | Workspace read, member read/invite, and task, comment, and tag operations |
| MEMBER | Workspace read, task create/read/update, and comment create/read |

The exact permission keys for each role are defined in `app/modules/authorization/role_policies.py`; that file is the source of truth if this summary and implementation ever differ.

Protected service operations call `AuthorizationService.require_permission(...)`. This checks that the user has a role in the workspace and that the role is mapped to the requested permission.

## Domain model

The current ORM models and migration history cover these principal entities:

| Entity | Purpose |
|---|---|
| Users | Local application identity linked to a Cognito subject |
| User profiles | Display name and profile information |
| Workspaces | Top-level collaboration boundary with a unique slug |
| Workspace members | Associates users with a workspace and role |
| Roles | Workspace-specific role definitions |
| Permissions | Catalogue of permission keys |
| Role permissions | Maps workspace roles to permission records |
| Workspace invitations | Tracks invitation recipient, role, token hash, status, and expiry |
| Tasks | Workspace tasks, including status, priority, due date, and optional parent task |
| Task assignees | Associates multiple workspace members with a task |
| Tags / task tags | Workspace-scoped tags and task-tag associations |
| Task comments | User-authored task discussion |
| Task history | Activity/audit records with JSONB change details |

Task status, priority, and invitation status are represented by enumerated values in the code and database migrations.

## Getting started

### Prerequisites

Install or prepare:

- Python compatible with the pinned dependencies in `requirements.txt`.
- PostgreSQL.
- An Amazon Cognito User Pool and app client configured for the authentication flows used by the application.
- AWS credentials/configuration with access to the Cognito User Pool operations used by the backend.

### 1. Clone the repository

```bash
git clone https://github.com/Hariprasaath-meyc/ClickUp-Clone.git
cd ClickUp-Clone
```

### 2. Create and activate a virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

macOS / Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

The current configuration module imports `pydantic-settings`; if it is not installed in your environment, install it with:

```bash
pip install pydantic-settings
```

### 4. Configure environment variables

Create a `.env` file in the repository root:

```dotenv
DATABASE_URL=postgresql+psycopg://<db_user>:<db_password>@localhost:5432/<database_name>

AWS_REGION=ap-south-1
COGNITO_CLIENT_ID=<your_cognito_app_client_id>
COGNITO_CLIENT_SECRET=<your_cognito_app_client_secret>
COGNITO_USER_POOL_ID=<your_cognito_user_pool_id>
```

Use the actual database credentials and Cognito values from your environment. Do not commit `.env` or expose Cognito client secrets.

The application settings are defined in `app/core/config.py`. The database URL must use a SQLAlchemy-compatible PostgreSQL URL with the Psycopg driver for the async engine configured in `app/db/session.py`.

### 5. Create the PostgreSQL database

Create an empty database matching the database name in `DATABASE_URL`. For example, from a PostgreSQL administrative session:

```sql
CREATE DATABASE clickup_clone;
```

If you use a different database name, update `DATABASE_URL` accordingly.

### 6. Apply database migrations

```bash
alembic upgrade head
```

This applies the migration revisions under `migrations/versions` to the configured database.

### 7. Start the API

```bash
uvicorn main:app --reload
```

The development server is normally available at:

- GraphQL endpoint: [http://127.0.0.1:8000/graphql](http://127.0.0.1:8000/graphql)
- Health check: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

The health check returns a simple application status response. The current CORS configuration in `main.py` allows the Vite development origin `http://localhost:5173`, with POST and OPTIONS methods and the Content-Type and Authorization headers.

## Database migrations

Alembic is configured to use the application's database URL and SQLAlchemy model metadata.

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

Always review autogenerated migration files before applying them, especially for enum changes, foreign keys, constraints, and destructive schema operations.

## GraphQL API

The Strawberry schema is composed in `app/graphql/schema.py` from module-level query and mutation classes.

The active API endpoint is:

```text
POST /graphql
```

For authenticated operations, include the Cognito access token:

```http
Authorization: Bearer <COGNITO_ACCESS_TOKEN>
Content-Type: application/json
```

A basic query:

```graphql
query {
  hello
}
```

A basic signup mutation:

```graphql
mutation {
  signup(
    email: "user@example.com"
    password: "YourStrongPassword123!"
    displayName: "Example User"
  ) {
    confirmationRequired
    message
  }
}
```

The GraphQL schema uses Strawberry's Python-to-GraphQL naming conversion. Check the declared input and output types in the relevant module for the exact fields of each operation.

### Main operation areas

| Module | GraphQL responsibilities |
|---|---|
| Auth | Signup, confirmation, resend confirmation code, login, refresh session, logout |
| Users | Current-user query and profile update |
| Workspaces | Create/update workspace and workspace queries |
| Membership | Member queries, role changes, and member removal |
| Invitations | Create, accept, decline, revoke, resend, and query invitations |
| Tasks | Task queries and task mutations |
| Task comments | Create, update, and delete comments |
| Task history | Query task activity history |
| Tags | Tag queries and tag mutations |

## Configuration reference

| Variable | Required | Description |
|---|---:|---|
| `DATABASE_URL` | Yes | PostgreSQL SQLAlchemy connection URL |
| `AWS_REGION` | No | Cognito AWS region; defaults to `ap-south-1` |
| `COGNITO_CLIENT_ID` | Yes for Cognito auth | Cognito app client ID |
| `COGNITO_CLIENT_SECRET` | Required for a secret-enabled app client | Cognito app client secret used to calculate the secret hash |
| `COGNITO_USER_POOL_ID` | Yes for token verification | Cognito User Pool ID used to construct the token issuer and JWKS URL |

## Implementation notes

- The repository is a backend project; no frontend application is included in the current tree.
- The FastAPI application registers the Strawberry GraphQL router at `/graphql` and a `/health` endpoint.
- A separate authentication HTTP router exists under `app/modules/auth/router.py`, but it is not included in `main.py`; the documented active authentication flow is through the GraphQL mutations.
- The application uses an async SQLAlchemy engine and session dependency for GraphQL database work.
- Task deletion and comment deletion are implemented as soft-delete operations in their services/repositories; task activity is recorded separately.
- Workspace creation provisions the default roles, role-permission mappings, and the creator's OWNER membership.
- No Docker Compose file, automated test suite, or deployment workflow was present in the inspected repository tree. Add these as the project evolves rather than assuming they are already available.

## License

No license file was present in the inspected repository. All rights are reserved by default unless a license is added to the project.

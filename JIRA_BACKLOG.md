# JIRA Backlog Structure - AI-Driven Recruitment Backend

## Table of Contents
1. [INVEST Criteria Guidelines](#invest-criteria-guidelines)
2. [Story Templates](#story-templates)
3. [Epic Structure](#epic-structure)
4. [Sprint Planning Guide](#sprint-planning-guide)
5. [Definition of Done](#definition-of-done)
6. [Priority Framework](#priority-framework)
7. [Ready-to-Work Criteria](#ready-to-work-criteria)

## INVEST Criteria Guidelines

### Independent
- Stories should be self-contained
- Minimal dependencies on other stories
- Can be developed in any order

### Negotiable
- Details can be discussed and refined
- Implementation approach is flexible
- Acceptance criteria can be adjusted

### Valuable
- Delivers business value to end users
- Contributes to product goals
- Has measurable impact

### Estimable
- Team can estimate effort required
- Requirements are clear enough
- Technical approach is understood

### Small
- Can be completed within one sprint
- Typically 1-8 story points
- Can be broken down if too large

### Testable
- Clear acceptance criteria
- Testable outcomes defined
- Success/failure is measurable

## Story Templates

### User Story Template
```
Title: [Action] - [Outcome]

As a [user type]
I want [functionality]
So that [business value]

Acceptance Criteria:
- [ ] Given [context], when [action], then [outcome]
- [ ] Given [context], when [action], then [outcome]
- [ ] Given [context], when [action], then [outcome]

Definition of Done:
- [ ] Code implemented and reviewed
- [ ] Unit tests written and passing
- [ ] Integration tests passing
- [ ] Documentation updated
- [ ] Security review completed
- [ ] Performance requirements met

Technical Notes:
- Implementation approach
- Dependencies
- Risks and assumptions

Story Points: [1, 2, 3, 5, 8, 13]
Priority: [Critical, High, Medium, Low]
Labels: [backend, api, database, security, performance]
```

### Bug Template
```
Title: [Component] - [Issue Description]

Environment: [Development/Staging/Production]
Browser/Client: [If applicable]

Steps to Reproduce:
1. Step one
2. Step two
3. Step three

Expected Result:
[What should happen]

Actual Result:
[What actually happens]

Acceptance Criteria:
- [ ] Bug is fixed
- [ ] Root cause identified
- [ ] Regression tests added
- [ ] No new bugs introduced

Severity: [Critical, High, Medium, Low]
Priority: [Critical, High, Medium, Low]
Labels: [bug, hotfix, regression]
```

### Technical Task Template
```
Title: [Technical Task Description]

Description:
[Detailed description of technical work needed]

Acceptance Criteria:
- [ ] Technical requirement 1
- [ ] Technical requirement 2
- [ ] Technical requirement 3

Definition of Done:
- [ ] Implementation complete
- [ ] Code reviewed
- [ ] Documentation updated
- [ ] Tests added if applicable

Story Points: [1, 2, 3, 5, 8]
Priority: [High, Medium, Low]
Labels: [technical-debt, refactor, infrastructure]
```

## Epic Structure

### Epic 1: Multi-Tenant Foundation
**Goal**: Establish secure multi-tenant architecture
**Business Value**: Enable multiple consulting companies to use the platform
**Timeline**: Sprints 1-2
**Success Metrics**: 
- 100% data isolation between tenants
- Sub-200ms response time for tenant queries
- Zero security vulnerabilities

#### Stories in Epic:
- RECRUIT-001: Multi-Tenant Database Models
- RECRUIT-002: Tenant-Aware Authentication
- RECRUIT-003: Tenant Data Isolation
- RECRUIT-004: Tenant Management APIs

---

### Epic 2: Role-Based Access Control
**Goal**: Implement comprehensive RBAC system
**Business Value**: Ensure users have appropriate access levels
**Timeline**: Sprints 2-3
**Success Metrics**:
- 5 distinct user roles implemented
- 100% permission coverage
- Zero unauthorized access incidents

#### Stories in Epic:
- RECRUIT-005: Enhanced User Role System
- RECRUIT-006: Permission Management
- RECRUIT-007: Role Assignment APIs
- RECRUIT-008: Access Control Middleware

---

### Epic 3: Candidate Bench Management
**Goal**: Enable comprehensive candidate profile management
**Business Value**: Streamline consultant tracking and placement
**Timeline**: Sprints 3-4
**Success Metrics**:
- 100% candidate profile completeness
- 50% reduction in placement time
- 90% user satisfaction score

#### Stories in Epic:
- RECRUIT-009: Candidate Bench Management API
- RECRUIT-010: Skill and Certification Tracking
- RECRUIT-011: Availability Status Management
- RECRUIT-012: Candidate Search and Filtering

---

### Epic 4: Client Relationship Management
**Goal**: Comprehensive client and opportunity management
**Business Value**: Improve sales efficiency and client satisfaction
**Timeline**: Sprints 4-5
**Success Metrics**:
- 25% increase in client retention
- 40% improvement in opportunity conversion
- 100% client data accuracy

#### Stories in Epic:
- RECRUIT-013: Client Management System
- RECRUIT-014: Client Contact Management
- RECRUIT-015: Job Opportunity Tracking
- RECRUIT-016: Client Performance Analytics

---

## Sprint Planning Guide

### Sprint Structure (2-week sprints)

#### Sprint Capacity Planning
- **Team Size**: 4-6 developers
- **Sprint Capacity**: 40-60 story points
- **Buffer**: 20% for bugs and unexpected work
- **Focus**: 1-2 epics per sprint maximum

#### Sprint Goals Template
```
Sprint [Number]: [Sprint Name]
Duration: [Start Date] - [End Date]

Sprint Goal:
[Clear, measurable objective for the sprint]

Commitment:
- Epic: [Epic Name] - [X story points]
- Bug fixes: [X story points]
- Technical debt: [X story points]

Risks:
- [Risk 1 and mitigation]
- [Risk 2 and mitigation]

Success Criteria:
- [Measurable outcome 1]
- [Measurable outcome 2]
```

### Story Point Distribution
- **1 Point**: Configuration changes, minor fixes
- **2 Points**: Simple CRUD endpoints
- **3 Points**: Complex business logic
- **5 Points**: Feature with multiple components
- **8 Points**: Complex integration work
- **13 Points**: Major architectural changes (break down)

## Definition of Done

### Story Level DoD
- [ ] **Code Quality**
  - Code follows style guidelines (Black, isort)
  - No linting errors (flake8, mypy)
  - Code review completed and approved
  - No TODO comments in production code

- [ ] **Testing**
  - Unit tests written and passing (90%+ coverage)
  - Integration tests passing
  - Manual testing completed
  - No regression in existing functionality

- [ ] **Documentation**
  - API documentation updated (OpenAPI)
  - Code comments for complex logic
  - README updated if needed
  - Migration scripts documented

- [ ] **Security**
  - Security review completed
  - No sensitive data in logs
  - Input validation implemented
  - Authentication/authorization working

- [ ] **Performance**
  - Performance requirements met
  - No memory leaks
  - Database queries optimized
  - Response times within SLA

### Sprint Level DoD
- [ ] All committed stories completed
- [ ] Sprint goal achieved
- [ ] Demo prepared and delivered
- [ ] Retrospective conducted
- [ ] Next sprint planned

### Release Level DoD
- [ ] All features tested in staging
- [ ] Performance testing completed
- [ ] Security audit passed
- [ ] Documentation complete
- [ ] Deployment runbook ready
- [ ] Rollback plan prepared

## Priority Framework

### Priority Levels

#### Critical (P0)
- Production outages
- Security vulnerabilities
- Data corruption issues
- **SLA**: Fix within 4 hours

#### High (P1)
- Core functionality broken
- Significant user impact
- Business-critical features
- **SLA**: Fix within 24 hours

#### Medium (P2)
- Feature enhancements
- Minor bugs
- Performance improvements
- **SLA**: Fix within 1 week

#### Low (P3)
- Nice-to-have features
- Technical debt
- Documentation updates
- **SLA**: Fix when capacity allows

### Priority Matrix
```
           High Impact    Low Impact
High Effort    P2            P3
Low Effort     P1            P2
```

## Ready-to-Work Criteria

Before a story can be moved to "In Progress":

- [ ] **Requirements Clear**
  - Acceptance criteria defined
  - Business value understood
  - User personas identified

- [ ] **Technical Design**
  - Implementation approach agreed
  - Dependencies identified
  - Technical risks assessed

- [ ] **Estimation Complete**
  - Story points assigned
  - Team consensus on estimate
  - Effort breakdown available

- [ ] **Resources Available**
  - Developer assigned
  - Required tools/access available
  - Dependencies resolved

## Sample JIRA Stories

### RECRUIT-001: Multi-Tenant Database Models
```
Epic: Multi-Tenant Foundation
Story Type: Story
Priority: Critical
Story Points: 13
Labels: backend, database, architecture, multi-tenant

As a system architect
I want tenant-aware database models
So that data is properly isolated between different consulting companies

Acceptance Criteria:
- [ ] Given a new tenant registration, when creating database records, then all records include tenant_id
- [ ] Given a user query, when accessing data, then only tenant-specific data is returned
- [ ] Given multiple tenants, when one tenant's data is modified, then other tenants' data remains unchanged
- [ ] Given database queries, when filtering by tenant, then performance is under 200ms

Technical Notes:
- Implement TenantAwareBase model class
- Add tenant_id foreign key to all relevant models
- Create database indexes for tenant-based queries
- Update all existing queries to include tenant filtering

Definition of Done:
- [ ] All models inherit from TenantAwareBase
- [ ] Migration scripts created and tested
- [ ] Unit tests achieve 95%+ coverage
- [ ] Integration tests verify data isolation
- [ ] Performance tests confirm query speed
- [ ] Code review completed
- [ ] Documentation updated

Risks:
- Large migration may cause downtime
- Existing data needs tenant assignment
- Query performance impact

Dependencies:
- Database backup completed
- Tenant model defined
```

### RECRUIT-009: Candidate Bench Management API
```
Epic: Candidate Bench Management
Story Type: Story
Priority: High
Story Points: 8
Labels: backend, api, candidate-management

As a profile manager
I want to manage candidate bench profiles
So that I can track available consultants and their skills

Acceptance Criteria:
- [ ] Given valid candidate data, when creating a profile, then profile is saved with all required fields
- [ ] Given an existing profile, when updating information, then changes are persisted correctly
- [ ] Given a profile manager role, when viewing candidates, then only accessible candidates are shown
- [ ] Given search criteria, when filtering candidates, then relevant results are returned
- [ ] Given candidate status change, when updating availability, then status is reflected immediately

API Endpoints:
- POST /api/v1/candidates - Create candidate profile
- GET /api/v1/candidates - List candidates with filtering
- GET /api/v1/candidates/{id} - Get candidate details
- PUT /api/v1/candidates/{id} - Update candidate profile
- PATCH /api/v1/candidates/{id}/status - Update availability status

Definition of Done:
- [ ] All CRUD endpoints implemented
- [ ] Input validation using Pydantic schemas
- [ ] Role-based access control enforced
- [ ] OpenAPI documentation complete
- [ ] Unit tests for all endpoints (90%+ coverage)
- [ ] Integration tests with database
- [ ] Error handling for edge cases
- [ ] Performance tests for list endpoint

Technical Notes:
- Use existing CandidateBench model
- Implement pagination for list endpoint
- Add search functionality using database indexes
- Include audit trail for profile changes

Dependencies:
- RECRUIT-001: Multi-Tenant Database Models
- RECRUIT-005: Enhanced User Role System
```

### RECRUIT-BUG-001: Authentication Token Expiry
```
Bug Type: Bug
Severity: High
Priority: High
Labels: bug, authentication, security

Environment: Production
Affected Users: All authenticated users

Steps to Reproduce:
1. Login to the application
2. Wait for token to expire (24 hours)
3. Make any API request
4. Observe 401 Unauthorized error

Expected Result:
Token should be automatically refreshed or user redirected to login

Actual Result:
User receives 401 error with no clear indication of what to do

Acceptance Criteria:
- [ ] Given an expired token, when making API request, then user is redirected to login
- [ ] Given token near expiry, when user is active, then token is automatically refreshed
- [ ] Given token refresh failure, when attempting refresh, then user sees clear error message

Root Cause Analysis:
- Token refresh mechanism not implemented
- Frontend not handling 401 responses properly
- No token expiry warning system

Fix Approach:
- Implement automatic token refresh
- Add token expiry middleware
- Update frontend error handling

Definition of Done:
- [ ] Token refresh mechanism implemented
- [ ] Frontend handles 401 responses
- [ ] User experience improved
- [ ] Regression tests added
- [ ] No similar issues in other auth flows
```

## Backlog Grooming Guidelines

### Weekly Grooming Sessions
- **Duration**: 1-2 hours
- **Participants**: Product Owner, Scrum Master, Development Team
- **Agenda**:
  1. Review upcoming stories
  2. Refine acceptance criteria
  3. Estimate story points
  4. Identify dependencies
  5. Update priorities

### Grooming Checklist
- [ ] Story follows INVEST criteria
- [ ] Acceptance criteria are testable
- [ ] Story points estimated by team
- [ ] Dependencies identified
- [ ] Priority assigned
- [ ] Labels added
- [ ] Ready-to-work criteria met

---

**Next Steps**: Review the [Testing Framework](TESTING_FRAMEWORK.md) for comprehensive testing guidelines and implementation details.
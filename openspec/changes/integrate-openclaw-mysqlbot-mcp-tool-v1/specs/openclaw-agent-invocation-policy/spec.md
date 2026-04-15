## ADDED Requirements

### Requirement: OpenClaw SHALL invoke mysqlbot through registered tools
The integration SHALL register one or more OpenClaw tools that call the mysqlbot OpenClaw-facing contract. Production invocation MUST flow through those tool definitions rather than ad hoc shell or raw HTTP calls embedded in the skill.

#### Scenario: Agent needs mysqlbot-backed data analysis
- **WHEN** an OpenClaw agent determines that a user request requires mysqlbot-backed data querying or analysis
- **THEN** the agent SHALL invoke the registered mysqlbot tool for execution

### Requirement: OpenClaw skill policy SHALL govern invocation timing and input collection
The integration SHALL provide a skill or equivalent policy document that tells OpenClaw when mysqlbot should be called, the minimum parameters or clarifications that must be collected before invocation, and when the agent MUST answer without invoking mysqlbot.

#### Scenario: User asks a database-backed question
- **WHEN** the user request falls within the mysqlbot-backed data-query or analysis scope defined by the policy
- **THEN** the skill SHALL direct the agent to invoke the mysqlbot tool with the required context

#### Scenario: User asks a non-database question
- **WHEN** the user request falls outside the mysqlbot-backed scope defined by the policy
- **THEN** the skill SHALL direct the agent not to invoke mysqlbot

### Requirement: Tool results SHALL be returned in agent-consumable form
The OpenClaw integration SHALL map mysqlbot tool responses into a stable agent-consumable form so downstream reasoning can summarize results without depending on undocumented backend fields.

#### Scenario: Tool call returns a successful mysqlbot response
- **WHEN** the mysqlbot-backed tool call completes successfully
- **THEN** the OpenClaw integration SHALL return the structured result in the documented agent-consumable form for that tool

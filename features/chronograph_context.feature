Feature: Chronograph full local work-continuity engine
  Chronograph ingests fragmented work signals, builds a source-grounded context graph, persists state locally, and exposes curated work state.

  Scenario: Merge fragmented signals into one active work item
    Given an empty Chronograph workspace
    When I ingest a meeting source "m1" saying "Finance should follow up with the customer"
    And I ingest a slack source "s1" saying "Need this by Friday"
    And I ingest an email source "e1" saying "Alex owns the finance follow-up now"
    Then Chronograph should have 1 active work item
    And the work item should be titled "Finance follow-up"
    And the work item owner should be "Alex"
    And the work item deadline should be "Friday"
    And the work item sources should be "m1,s1,e1"

  Scenario: Curate real commitments instead of dumping conversational noise
    Given an empty Chronograph workspace
    When I ingest a meeting source "m2" saying "Great chat everyone. Sarah will send the board memo by Tuesday. Maybe someday we should redesign the logo."
    Then Chronograph should have 1 active work item
    And the work item should be titled "Board memo"
    And the work item owner should be "Sarah"
    And the work item deadline should be "Tuesday"

  Scenario: Keep source grounding for extracted work
    Given an empty Chronograph workspace
    When I ingest a doc source "d1" saying "Liam will review the data center report by Monday"
    Then the work item should include source quote "Liam will review the data center report by Monday"
    And the work item should explain provenance with source "d1"

  Scenario: Track continuity as signals change over time
    Given an empty Chronograph workspace
    When I ingest a meeting source "m3" saying "Priya owns the investor response by Thursday"
    And I ingest a slack source "s3" saying "Investor response is blocked on finance numbers"
    Then the work item state should be "blocked"
    And the work item blocker should be "finance numbers"
    And Chronograph should report change "blocked"

  Scenario: Surface proactive review items without notification spam
    Given an empty Chronograph workspace
    When I ingest a meeting source "m4" saying "Sam will send customer follow-up by Friday"
    And I ingest a slack source "s4" saying "Customer follow-up is risky and needs review today"
    Then Chronograph should surface 1 review item
    And the review item reason should be "risky and needs review today"

  Scenario: Persist and reload a local workspace
    Given an empty Chronograph workspace
    When I ingest a meeting source "m5" saying "Nina will send launch plan by Wednesday for Project Atlas"
    And I reopen the Chronograph workspace
    Then Chronograph should have 1 active work item
    And the work item owner should be "Nina"
    And the graph should include relationship "Nina owns Launch plan"

  Scenario: Export and import complete state without losing provenance
    Given an empty Chronograph workspace
    When I ingest a doc source "d2" saying "Omar will review security checklist by Friday"
    And I export and import the Chronograph workspace
    Then Chronograph should have 1 active work item
    And the work item should include source quote "Omar will review security checklist by Friday"

  Scenario: Mark completed work done while retaining source history
    Given an empty Chronograph workspace
    When I ingest a task source "t1" saying "Maya will send renewal quote by Thursday"
    And I ingest a task source "t2" saying "Renewal quote is done"
    Then the work item state should be "done"
    And the work item sources should be "t1,t2"

  Scenario: Search across sources and active work
    Given an empty Chronograph workspace
    When I ingest an email source "e2" saying "Ravi will send customer escalation response by Friday"
    Then searching for "escalation" should return source "e2"

  Scenario: Retain source author and metadata for provenance
    Given an empty Chronograph workspace
    When I ingest a slack source "s10" from "Ada" with metadata "channel=eng" saying "Ada will send infra update by Monday"
    Then Chronograph should have 1 active work item
    And the source "s10" author should be "Ada"
    And the source "s10" metadata "channel" should be "eng"

  Scenario: The Chronograph CLI exposes the documented commands
    Given the Chronograph CLI
    Then the CLI should expose command "ingest"
    And the CLI should expose command "list"
    And the CLI should expose command "active"
    And the CLI should expose command "review"
    And the CLI should expose command "show"
    And the CLI should expose command "search"
    And the CLI should expose command "export"
    And the CLI should expose command "import"
    And the CLI should expose command "serve"

  Scenario: The Chronograph HTTP API responds to the documented endpoints
    Given an empty Chronograph workspace
    When I request GET "/health"
    Then the HTTP response status should be "200 OK"
    When I request GET "/active"
    Then the HTTP response status should be "200 OK"
    When I request GET "/work-items"
    Then the HTTP response status should be "200 OK"
    When I request GET "/review"
    Then the HTTP response status should be "200 OK"
    When I request GET "/export"
    Then the HTTP response status should be "200 OK"

  Scenario: Workspace state stays local in the SQLite file
    Given an empty Chronograph workspace
    When I ingest a meeting source "m20" saying "Priya owns the compliance review by Friday"
    Then the workspace file should exist locally
    And the workspace file should contain source "m20"

Feature: Chronograph context graph and proactive work state
  Chronograph turns fragmented work signals into structured, source-grounded active work state.

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

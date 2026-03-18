## 1. Baseline and Policy Definition

- [x] 1.1 Inventory current `Spell Check with Typos` failures and separate historical debt from intentional project-specific vocabulary
- [x] 1.2 Decide which file classes the blocking PR spelling gate will check in the first rollout
- [x] 1.3 Define the review policy for adding approved words or ignored patterns

## 2. CI Gate Implementation

- [x] 2.1 Add repository spelling configuration for approved terms and reviewed exceptions
- [x] 2.2 Update the typo-check workflow so blocking PR checks run against changed files only
- [x] 2.3 Add or document a non-blocking maintenance path for broader historical typo scans

## 3. Verification and Documentation

- [x] 3.1 Verify a PR with no new typos passes even when historical typo debt remains elsewhere in the repository
- [x] 3.2 Verify a PR that introduces a new typo fails with an actionable file-and-token report
- [x] 3.3 Document how maintainers approve new vocabulary and how contributors interpret typo-check failures

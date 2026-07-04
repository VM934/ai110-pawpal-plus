# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

My initial design separated the project into domain objects and one scheduler. I used `Owner` for availability and daily care limits, `Pet` for the animal being planned for, `CareTask` for care items, `ScheduledTask` and `SkippedTask` for results, and `DailyPlan` for the final output. `PawPalScheduler` owns the algorithm instead of putting scheduling logic inside the Streamlit UI.

**b. Design changes**

The main design change was adding explicit result objects instead of returning raw dictionaries. A raw dictionary was faster at first, but `ScheduledTask` and `SkippedTask` made the code easier to test and made explanations cleaner in both the CLI demo and Streamlit app.

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

The scheduler considers owner availability, fixed-time tasks, preferred task times, recurrence rules, task priority, duration, and an optional daily care-minute limit. I made fixed-time tasks the strongest constraint because medication, appointments, and feeding windows are less flexible than enrichment or grooming. After fixed tasks, flexible tasks are sorted by priority so urgent/high care happens before lower-priority items.

**b. Tradeoffs**

The scheduler uses a greedy algorithm instead of trying every possible arrangement. That means it is predictable and easy to explain, but it may not always find a mathematically perfect schedule. I think that is reasonable for this scenario because a pet owner needs a clear daily plan and understandable reasons more than an invisible optimization process.

## 3. AI Collaboration

**a. How you used AI**

I used AI to scaffold the class design, identify edge cases, and keep the work aligned with prior feedback. The most helpful prompts were specific ones that asked for project completion while preserving grader requirements, such as checking prior feedback and carrying it forward into tests, documentation, and commit history.

**b. Judgment and verification**

One place I did not accept an assumption as-is was conflict fallback behavior. My first test expected a flexible task to jump earlier when its preferred time was occupied. After running the test, I reviewed the actual policy and decided the clearer behavior was to schedule it immediately after the occupied preferred slot when possible. I changed the test to verify the real scheduling requirement: no overlap and a clear explanation.

## 4. Testing and Verification

**a. What you tested**

I tested priority selection under a daily time limit, fixed-time conflicts, preferred-time placement, exact boundary fitting, availability-window overflow, recurrence rules, generator input support, invalid task fields, and invalid owner availability. These tests matter because they cover the algorithmic parts that are easiest to break while changing the UI.

**b. Confidence**

I am confident that the scheduler handles the required behaviors for a single owner, one pet, and one day. If I had another iteration, I would add multi-pet scheduling, travel buffers between tasks, and stronger optimization for cases where a lower-priority short task could fit after higher-priority tasks are skipped.

## 5. Reflection

**a. What went well**

The clean separation between `pawpal_system.py` and `app.py` went well. It made the CLI demo, Streamlit UI, and tests all use the same backend instead of duplicating scheduling rules.

**b. What you would improve**

I would improve the scheduling algorithm so it can compare multiple candidate schedules instead of using only greedy placement. I would also make the Streamlit UI support editing or deleting individual tasks instead of only clearing the full task list.

**c. Key takeaway**

The biggest takeaway is that good system design makes AI assistance safer. When logic is isolated into small classes and tested directly, I can use AI suggestions without blindly trusting them because every important behavior has a verification path.

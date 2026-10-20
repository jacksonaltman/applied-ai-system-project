# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

User needs to be able to enter owner and pet info
User needs to be able to add and edit tasks
User needs to be able to generate a daily schedule/plan based on constraints and priorities

- Briefly describe your initial UML design.
The initial UML design uses four classes. It structures the relationships between the user, their pet, the tasks, and the scheduling that processes time and priority constraints to output a daily schedule.
- What classes did you include, and what responsibilities did you assign to each?
Pet: Holds basic pet information required by the app, such as the pet's name and breed.
Owner: Stores the user's basic information alongside their specific scheduling constraints, such as the total time they have available for pet care.
Task: Stores details for individual care activities, such as the amount of time it will take and how high of a priority it is. It can also identify the type of task, such as walks, feeding, meds, playing, or grooming.
Plan: Manages the core scheduling logic to generate a daily schedule. It evaluates the list of tasks against the owner's constraints and priorities to produce a finalized plan, and it is responsible for displaying the plan clearly along with an explanation of its reasoning.

**b. Design changes**

- Did your design change during implementation?
Yes, a little bit.
- If yes, describe at least one change and why you made it.
The model needed to add some fields (such as "owner" to Plan class) to implement the relationships between classes.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?
The scheduler looks at the owner's available time for the day, each task's priority (low, medium, high), each task's duration, and its start time. It also skips tasks that are already completed. It doesn't handle owner preferences yet.
- How did you decide which constraints mattered most?
Available time is the hard limit, because the owner can't do more than they have time for. Inside that limit, priority matters most, since a missed medication is more important than a missed play session. Start time and duration only break ties: earlier tasks go first, then shorter ones.

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.
The scheduler is greedy. It goes through tasks from highest priority down and adds each one if it still fits in the time left. This means it can miss a better combination. For example, one 45 minute high priority task could use up time that would have fit two medium priority tasks. Also, if two scheduled tasks overlap on the clock, it only warns about the overlap and doesn't move anything around.
- Why is that tradeoff reasonable for this scenario?
For a daily pet care plan with only a handful of tasks, a simple rule that always puts the most important things first is easy to understand and explain, which is part of what the app is supposed to do. Finding the perfect combination would be a lot more complicated and the plan would be harder to explain. Warning about overlaps also leaves the final call to the owner.

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
I used AI to turn my UML into Python class skeletons, then to review that skeleton, and then to fill in the real logic, a terminal demo (`main.py`), tests, docstrings, and the README summary.
- What kinds of prompts or questions were most helpful?
The most helpful one was asking it to look for missing relationships and logic bottlenecks in the skeleton before I wrote any logic, because it had a lot of suggestions to make which I was not expecting.

It pointed out that a Task wasn't connected to a Pet, that priority stored as a string would sort in the wrong order ("high", "low", "medium"), and that there was no validation for things like a duration of 0. It also suggested the greedy scheduling approach (highest priority first, then earliest time, then shortest) and a list of reasons for each skipped task so the plan can be explained.

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
When the AI wrote a 12-test suite, I said I didn't need all of that yet and asked for just two simple tests: one for `mark_complete()` and one for adding a task to a pet. I also redirected the design so it matched the assignment. The AI's version had a Plan class with its own task lists, and I asked for Task, Pet, Owner and Scheduler, where Pet holds its tasks and the Scheduler reads everything through `Owner.get_all_tasks()`. That removed the Plan and ScheduledTask classes the AI had added.
- How did you evaluate or verify what the AI suggested?
I ran `main.py` and checked that the schedule made sense , and I ran pytest to confirm the two tests pass. I also checked that the Scheduler really pulls from every pet and not just one, since that was a requirement.

**c. AI strategy**

- Which AI coding assistant features were most effective for building your scheduler?
Reviewing the skeleton before writing any logic was the most useful. Asking the AI to look for missing relationships and bottlenecks caught the Task-to-Pet link, the string-priority sorting bug, and missing validation while they were still cheap to fix. After that, having it work from the real files (`pawpal_system.py`, the tests, `main.py`) instead of describing the code to it meant its suggestions matched what I had actually built. It was also good at the tedious parts: drafting the test cases, docstrings, and the README, and keeping the UML in sync with the code at the end. Running the tests and `main.py` right after each change gave me a fast way to check its work.

- Give one example of an AI suggestion you rejected or modified to keep your system design clean.
The AI's first design had a `Plan` class that held its own task lists, plus a `ScheduledTask` class. I rejected both and asked for the four classes in the assignment (Task, Pet, Owner, Scheduler). Pets own their tasks, and the Scheduler reads everything through `Owner.get_all_tasks()`. That kept a single source of truth for tasks, so a task can't be out of sync between a pet and a plan. I did the same with testing: it offered a 12-test suite early on, and I asked for just two tests until the logic existed, then expanded the suite once the behavior was stable.

- How did using separate chat sessions for different phases help you stay organized?
Giving each phase its own session (design and UML, implementation, then testing) kept each conversation focused on one question. The testing session only had to think about edge cases like a pet with no tasks or two tasks at the same time, and not about how the scheduler should be designed. It also meant the AI had to read the current code instead of relying on earlier assumptions, which helped me notice when the UML had drifted from the implementation.

- Summarize what you learned about being the "lead architect" when collaborating with powerful AI tools.
The AI is fast and has plenty of ideas, but it doesn't know what the project is supposed to be. It tends to add classes, tests, and features because it can, not because they're needed. My job was to decide the boundaries: which classes exist, who owns the data, what the scheduler should and shouldn't do (it warns about conflicts and doesn't silently rearrange tasks), and what counts as done. I learned to treat its output as a draft to review, to keep the design simple enough that I could explain every piece, and to verify with tests and by running the app instead of trusting a confident answer.

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
I wrote 22 tests in `tests/test_pawpal.py`. They cover sorting (chronological order across pets, priority tie-breaks, tasks on different days, no tasks), recurrence (daily and weekly tasks create the next one, one-off tasks don't, completing twice makes no duplicate, late completion recurs from today), conflict detection (same start time, partial overlap, back-to-back tasks not counting as conflicts, completed tasks ignored), and edge cases like a pet with no tasks, filtering, an invalid duration, and tasks skipped when time runs out.
- Why were these tests important?
Sorting, recurrence, and conflicts are the parts that make the scheduler "smart", and they are the easiest to get subtly wrong, especially around boundaries like a task that ends exactly when the next one starts.

**b. Confidence**

- How confident are you that your scheduler works correctly?
Fairly confident, about 4 out of 5. All 22 tests pass and cover the main behaviors and edge cases.
- What edge cases would you test next if you had more time?
Tasks that run past midnight, the Streamlit UI itself, and `Scheduler.complete_task`, which uses the real current date and so is harder to test. I would also test what happens with a very large number of tasks.

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?
That the Scheduler reads every pet's tasks through the Owner, so the sorting, filtering, and conflict warnings all work from one list, and that the UI shows those warnings clearly with a suggestion for fixing them.

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?
I would let the owner resolve a conflict from the UI (for example, by picking a new time), and replace the greedy scheduler with something that can find a better combination of tasks when time is tight. I would also add owner preferences, which aren't handled yet.

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
The AI system tends to overcomplicate.
It is also easy to be impressed by how much code it writes in one go. The useful habit was slowing down: deciding the design first, asking for small pieces, and checking each one.

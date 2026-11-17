from datetime import date, datetime

import streamlit as st

import ai_agent
from pawpal_system import Frequency, Owner, Pet, Priority, Scheduler, Task

SPECIES = ["dog", "cat", "rabbit", "small mammal", "bird", "fish", "reptile", "other"]

ai_agent.setup_logging()
st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

# Streamlit reruns this whole script on every click, so the Owner has to live in
# session_state. Only create it if it isn't already in the "vault".
if "owner" not in st.session_state:
    st.session_state.owner = Owner(name="Jordan", available_time=90)
owner: Owner = st.session_state.owner

st.title("🐾 PawPal+")
st.caption("A pet care planner: add your pets, add their tasks, and generate today's schedule.")

# --- Owner ---
st.subheader("Owner")
with st.form("owner_form"):
    owner_name = st.text_input("Owner name", value=owner.name)
    available = st.number_input(
        "Time available today (minutes)", min_value=0, max_value=1440, value=owner.available_time
    )
    if st.form_submit_button("Save owner"):
        owner.name = owner_name.strip() or owner.name
        owner.available_time = int(available)
        st.success(f"Saved {owner.name} ({owner.available_time} min available).")

# --- Pets ---
st.subheader("Pets")
with st.form("pet_form", clear_on_submit=True):
    pet_name = st.text_input("Pet name")
    breed = st.text_input("Breed")
    sp1, sp2 = st.columns(2)
    with sp1:
        species = st.selectbox("Species", SPECIES)
    with sp2:
        age = st.number_input("Age (years)", min_value=0.0, max_value=40.0, value=3.0, step=0.5)
    if st.form_submit_button("Add pet"):
        if not pet_name.strip():
            st.error("Please enter a pet name.")
        else:
            owner.add_pet(
                Pet(name=pet_name.strip(), breed=breed.strip() or "unknown", species=species, age_years=float(age))
            )
            st.success(f"Added {pet_name.strip()}!")

if owner.pets:
    st.table(
        [
            {"Name": p.name, "Species": p.species, "Breed": p.breed, "Age": p.age_years, "Tasks": len(p.tasks)}
            for p in owner.pets
        ]
    )
else:
    st.info("No pets yet. Add one above.")

# --- Tasks ---
st.subheader("Tasks")
if not owner.pets:
    st.info("Add a pet before adding tasks.")
else:
    with st.form("task_form", clear_on_submit=True):
        pet_choice = st.selectbox("Pet", [p.name for p in owner.pets])
        description = st.text_input("Task", placeholder="Morning walk")
        col1, col2 = st.columns(2)
        with col1:
            start = st.time_input("Start time", value=datetime.now().replace(second=0, microsecond=0).time())
            duration = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=20)
        with col2:
            frequency = st.selectbox("Repeats", [f.value for f in Frequency])
            priority = st.selectbox("Priority", [p.name.lower() for p in Priority], index=2)
        if st.form_submit_button("Add task"):
            if not description.strip():
                st.error("Please enter a task description.")
            else:
                owner.get_pet(pet_choice).add_task(
                    Task(
                        description=description.strip(),
                        time=datetime.combine(date.today(), start),
                        duration=int(duration),
                        frequency=Frequency(frequency),
                        priority=Priority[priority.upper()],
                    )
                )
                st.success(f"Added '{description.strip()}' for {pet_choice}.")

# --- AI suggestions: retrieve care docs -> Gemini drafts tasks -> the human approves ---
if owner.pets and ai_agent.is_configured():
    st.markdown("#### ✨ AI task suggestions")
    st.caption(
        "Drafts a routine from our pet-care guides. Nothing is added until you approve it. "
        "This is general guidance, not veterinary advice."
    )
    ai_pet = st.selectbox("Suggest tasks for", [p.name for p in owner.pets], key="ai_pet")
    if st.button("Suggest tasks"):
        with st.spinner("Looking up care guidance and drafting tasks..."):
            st.session_state.ai_result = (ai_pet, ai_agent.suggest_tasks(owner.get_pet(ai_pet)))

    if "ai_result" in st.session_state:
        result_pet, result = st.session_state.ai_result
        pet_obj = owner.get_pet(result_pet)
        if pet_obj is None:  # pet was removed since the suggestions were made
            del st.session_state.ai_result
        else:
            if result.docs:
                with st.expander("Guides used (retrieved)"):
                    for d in result.docs:
                        st.markdown(f"**{d.title}** (`{d.id}`)")
            if result.error:
                st.error(result.error)
            else:
                if result.rejected:
                    st.caption(f"{result.rejected} invalid suggestion(s) were filtered out automatically.")
                st.write(f"Review suggestions for **{result_pet}** and tick the ones you want:")
                picks = []
                for i, s in enumerate(result.suggestions):
                    label = f"{s.start} · {s.description} ({s.duration} min, {s.frequency.value}, {s.priority.name.lower()})"
                    if st.checkbox(label, value=True, key=f"ai_pick_{i}"):
                        picks.append(s)
                    st.caption(f"Why: {s.reason} (source: {s.source})")
                if st.button("Add selected tasks"):
                    for s in picks:
                        pet_obj.add_task(s.to_task())
                    st.session_state.flash = f"Added {len(picks)} AI-suggested task(s) to {result_pet}."
                    del st.session_state.ai_result
                    st.rerun()
elif owner.pets:
    st.info("✨ AI task suggestions are off. Set the GEMINI_API_KEY environment variable and restart to enable them.")

scheduler = Scheduler(owner)


def task_rows(tasks):
    return [
        {
            "Time": f"{t.time:%H:%M}-{t.end_time:%H:%M}",
            "Pet": t.pet_name,
            "Task": t.description,
            "Repeats": t.frequency.value,
            "Priority": t.priority.name.lower(),
            "Status": "✅ done" if t.completed else "⏳ pending",
        }
        for t in tasks
    ]


# --- Conflicts: surfaced as soon as they exist, before the user generates a plan ---
conflicts = scheduler.find_conflicts()
if conflicts:
    st.warning(f"⚠️ {len(conflicts)} scheduling conflict(s) found. You can't be in two places at once!")
    for a, b in conflicts:
        who = (
            f"both for {a.pet_name}"
            if a.pet_name == b.pet_name
            else f"{a.pet_name} and {b.pet_name} at the same time"
        )
        st.warning(
            f"**{a.description}** ({a.pet_name}, {a.time:%H:%M}-{a.end_time:%H:%M}) overlaps "
            f"**{b.description}** ({b.pet_name}, {b.time:%H:%M}-{b.end_time:%H:%M}), {who}. "
            f"Tip: move {b.description} to {a.end_time:%H:%M} or later, or shorten {a.description}."
        )
elif scheduler.pending_tasks():
    st.success("No conflicts: your pending tasks don't overlap.")

# --- Task list: sorted by time, with filters ---
if scheduler.get_all_tasks():
    st.markdown("#### All tasks")
    f1, f2 = st.columns(2)
    with f1:
        pet_filter = st.selectbox("Filter by pet", ["All pets"] + [p.name for p in owner.pets])
    with f2:
        status_filter = st.selectbox("Filter by status", ["All", "Pending", "Completed"])
    filtered = scheduler.filter_tasks(
        pet_name=None if pet_filter == "All pets" else pet_filter,
        completed={"All": None, "Pending": False, "Completed": True}[status_filter],
    )
    filtered = scheduler.sort_by_time(filtered)
    if filtered:
        st.table(task_rows(filtered))
    else:
        st.info("No tasks match these filters.")

    pending = scheduler.sort_by_time(scheduler.pending_tasks())
    if pending:
        st.markdown("#### Mark a task complete")
        chosen = st.selectbox(
            "Task",
            range(len(pending)),
            format_func=lambda i: f"{pending[i].time:%H:%M} {pending[i].description} ({pending[i].pet_name})",
        )
        if st.button("Mark complete"):
            task = pending[chosen]
            nxt = scheduler.complete_task(task)
            if nxt:
                st.session_state.flash = (
                    f"Completed '{task.description}'. Next {nxt.frequency.value} task scheduled for "
                    f"{nxt.time:%a %b %d at %H:%M}."
                )
            else:
                st.session_state.flash = f"Completed '{task.description}'."
            st.rerun()
elif owner.pets:
    st.info("No tasks yet. Add one above.")

if "flash" in st.session_state:
    st.success(st.session_state.pop("flash"))

st.divider()

# --- Schedule ---
st.subheader("Today's Schedule")
if st.button("Generate schedule"):
    if not scheduler.pending_tasks():
        st.warning("Add at least one pending task first.")
    else:
        plan = scheduler.generate_schedule(day=date.today())
        if plan:
            used = sum(t.duration for t in plan)
            st.success(f"Scheduled {len(plan)} task(s) using {used} of {owner.available_time} minutes.")
            st.table(task_rows(plan))
        else:
            st.info("Nothing to schedule for today.")
        if scheduler.skipped:
            st.warning(
                "Skipped (not enough time): "
                + ", ".join(f"{t.description} ({t.pet_name})" for t in scheduler.skipped)
            )
        for w in scheduler.conflict_warnings(plan):
            st.warning(w)
        with st.expander("Why this plan?", expanded=True):
            st.text(scheduler.explain_reasoning())

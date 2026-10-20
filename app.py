from datetime import date, datetime

import streamlit as st

from pawpal_system import Frequency, Owner, Pet, Priority, Scheduler, Task

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
    breed = st.text_input("Breed / species")
    if st.form_submit_button("Add pet"):
        if not pet_name.strip():
            st.error("Please enter a pet name.")
        else:
            owner.add_pet(Pet(name=pet_name.strip(), breed=breed.strip() or "unknown"))
            st.success(f"Added {pet_name.strip()}!")

if owner.pets:
    st.table([{"Name": p.name, "Breed": p.breed, "Tasks": len(p.tasks)} for p in owner.pets])
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

scheduler = Scheduler(owner)
all_tasks = scheduler.sort_by_time()  # tasks from every pet, via Owner.get_all_tasks()
if all_tasks:
    st.table(
        [
            {
                "Time": t.time.strftime("%H:%M"),
                "Pet": t.pet_name,
                "Task": t.description,
                "Duration": f"{t.duration} min",
                "Repeats": t.frequency.value,
                "Priority": t.priority.name.lower(),
            }
            for t in all_tasks
        ]
    )
elif owner.pets:
    st.info("No tasks yet. Add one above.")

st.divider()

# --- Schedule ---
st.subheader("Today's Schedule")
if st.button("Generate schedule"):
    if not all_tasks:
        st.warning("Add at least one task first.")
    else:
        scheduler.generate_schedule(day=date.today())
        st.text(scheduler.display_plan())
        if scheduler.skipped:
            st.warning(
                "Skipped (not enough time): "
                + ", ".join(f"{t.description} ({t.pet_name})" for t in scheduler.skipped)
            )
        with st.expander("Why this plan?", expanded=True):
            st.text(scheduler.explain_reasoning())

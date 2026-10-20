from datetime import datetime

from pawpal_system import Pet, Task


def test_mark_complete_changes_status():
    task = Task("Walk", datetime(2026, 1, 1, 8))
    assert task.completed is False

    task.mark_complete()

    assert task.completed is True


def test_adding_task_increases_pet_task_count():
    pet = Pet("Rex", "Lab")
    assert len(pet.tasks) == 0

    pet.add_task(Task("Walk", datetime(2026, 1, 1, 8)))

    assert len(pet.tasks) == 1

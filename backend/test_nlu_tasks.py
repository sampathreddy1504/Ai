from app.services.nlu import get_structured_intent

examples = [
    "Add me a task to attend party tomorrow at 8pm",
    "Can you add a task to brush my teeth at 7:30am",
    "Remind me to call mom in 2 hours",
    "Please add a task to submit assignment",
    "Remind me to take meds at 9pm",
    "Add a task to buy groceries",
]

for ex in examples:
    print("INPUT:", ex)
    print("PARSED:", get_structured_intent(ex))
    print()

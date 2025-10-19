import runpy
import os

# Run the nlu.py as a standalone module to avoid package-top imports
nlu_path = os.path.join(os.path.dirname(__file__), 'app', 'services', 'nlu.py')
# Execute as a module and extract get_structured_intent from its globals
ns = runpy.run_path(nlu_path)
get_structured_intent = ns['get_structured_intent']

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

import runpy
import os

nlu_path = os.path.join(os.path.dirname(__file__), 'app', 'services', 'nlu.py')
ns = runpy.run_path(nlu_path)
get_structured_intent = ns['get_structured_intent']

examples = [
    # YouTube positive
    'play some music on youtube',
    'open youtube and search for lo-fi beats',
    'search youtube for python tutorial',
    'youtube: funny cat videos',

    # YouTube negative (informational)
    'tell me about youtube',
    'what is youtube used for?',

    # Spotify positive
    'play blinding lights on spotify',
    'open spotify and search for jazz playlist',

    # Maps positive
    'open maps for coffee shops near me',
    'navigate to the nearest gas station',

    # Instagram positive
    'open instagram and search for nasa',
    'instagram: nasa',

    # Generic negative
    'tell me about spotify',
    'what is instagram?',
]

for ex in examples:
    print('INPUT:', ex)
    print('PARSED:', get_structured_intent(ex))
    print()

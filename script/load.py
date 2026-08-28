import os 

print(os.path.abspath(__file__))

script_dir = os.path.dirname(os.path.abspath(__file__))

print(os.path.abspath(os.path.join(script_dir, "..", "data", "raw_data")))
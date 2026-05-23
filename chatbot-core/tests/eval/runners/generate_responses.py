import json

#Config: existing file, new file
input_file="chatbot-core/tests/eval/datasets/golden_dataset.json"
output_file="chatbot-core/tests/eval/datasets/responses.json"

# Read existing json
with open(input_file, "r") as f:
    data = json.load(f)
    
new_data = []

#Loop through each object
for item in data:
    input_text = item.get("input")
    question_id = item.get("additional_metadata", {}).get("id")
    
    #New schema
    new_obj= {
        "id": question_id,
        "input": input_text,
        "actual_output": "",
        "retrieval_context": []
    }
    
    new_data.append(new_obj)
    
#Write json file
with open(output_file, "w") as f:
    json.dump(new_data,f,indent=4)

print(f"Created {output_file}")
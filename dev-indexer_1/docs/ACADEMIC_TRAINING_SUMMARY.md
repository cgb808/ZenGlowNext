# Academic Training Pipeline Summary

{
"pipeline_overview": {
"tiny_tool_controller": {
"model": "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
"purpose": "Fast tool classification",
"target_latency": "< 100ms",
"training_data": "consolidated_tool_control.jsonl"
},
"phi3_specialists": {
"mathematics": {
"model": "microsoft/Phi-3-mini-4k-instruct",
"specialization": "mathematics_education",
"output_name": "phi3_mathematics_tutor"
},
"science": {
"model": "microsoft/Phi-3-mini-4k-instruct",
"specialization": "science_education",
"output_name": "phi3_science_tutor"
},
"english": {
"model": "microsoft/Phi-3-mini-4k-instruct",
"specialization": "english_education",
"output_name": "phi3_english_tutor"
},
"history": {
"model": "microsoft/Phi-3-mini-4k-instruct",
"specialization": "history_education",
"output_name": "phi3_history_tutor"
},
"art": {
"model": "microsoft/Phi-3-mini-4k-instruct",
"specialization": "art_education",
"output_name": "phi3_art_tutor"
},
"foreign_language": {
"model": "microsoft/Phi-3-mini-4k-instruct",
"specialization": "language_education",
"output_name": "phi3_language_tutor"
}
}
},
"training_sequence": [
"1. Train tiny tool controller for fast classification",
"2. Train domain-specific Phi-3 specialists",
"3. Create deployment configuration",
"4. Test integrated pipeline"
],
"data_distribution": {
"mathematics": 3350,
"english": 250,
"science": 14139,
"history": 250,
"art": 438,
"foreign_language": 250
},
"expected_outcomes": {
"tiny_controller": "Sub-100ms tool classification",
"phi3_specialists": "Domain-aware educational responses",
"integration": "Seamless audio → tool → specialist pipeline"
}
}

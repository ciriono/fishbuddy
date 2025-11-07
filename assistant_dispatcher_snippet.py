import json
from tools import (
    geocode_place, canton_from_place, get_weather_by_place,
    get_water_data, list_species_by_place, check_rules
)

def handle_tool_calls(client, thread_id: str, run):
    ra = getattr(run, "required_action", None)
    if not ra or getattr(ra, "type", None) != "submit_tool_outputs":
        return run

    outs = []
    for call in ra.submit_tool_outputs.tool_calls:
        name = call.function.name
        args = json.loads(call.function.arguments or "{}")
        if name == "geocode_place":
            out = geocode_place(**args)
        elif name == "canton_from_place":
            out = canton_from_place(**args)
        elif name == "get_weather_by_place":
            out = get_weather_by_place(**args)
        elif name == "get_water_data":
            out = get_water_data(**args)
        elif name == "list_species_by_place":
            out = list_species_by_place(**args)
        elif name == "check_rules":
            out = check_rules(**args)
        else:
            out = json.dumps({"error": f"unknown tool {name}"})
        outs.append({"tool_call_id": call.id, "output": out})

    return client.beta.threads.runs.submit_tool_outputs(
        thread_id=thread_id,
        run_id=run.id,
        tool_outputs=outs
    )

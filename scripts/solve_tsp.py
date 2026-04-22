import json
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
from pathlib import Path

OUT_PATH = Path("data") / "route_solution.json"
OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

def load_data():
    with open("data/time_matrix.json", "r", encoding="utf-8") as f:
        matrix = json.load(f)

    data = {}
    # OR-Tools expects integers
    data["time_matrix"] = [
        [int(x) for x in row] for row in matrix["durations"]
    ]
    data["num_vehicles"] = 1
    data["depot"] = 0
    return data


def main():
    data = load_data()

    manager = pywrapcp.RoutingIndexManager(
        len(data["time_matrix"]),
        data["num_vehicles"],
        data["depot"]
    )

    routing = pywrapcp.RoutingModel(manager)

    def time_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return data["time_matrix"][from_node][to_node]

    transit_callback_index = routing.RegisterTransitCallback(time_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (
    routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    )
    search_parameters.local_search_metaheuristic = (
    routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    )
    search_parameters.time_limit.seconds = 30

    solution = routing.SolveWithParameters(search_parameters)

    if not solution:
        raise RuntimeError("No solution found")

    print("Route:")
    index = routing.Start(0)
    route = []
    total_time = 0

    while not routing.IsEnd(index):
        node = manager.IndexToNode(index)
        route.append(node)
        next_index = solution.Value(routing.NextVar(index))
        total_time += routing.GetArcCostForVehicle(index, next_index, 0)
        index = next_index

    route.append(manager.IndexToNode(index))

    print(" → ".join(map(str, route)))
    print(f"Total travel time: {total_time / 3600:.2f} hours")

    with open(OUT_PATH, "w", encoding="utf-8") as f:
    json.dump(out, f, indent=2)

print(f"Wrote {OUT_PATH.resolve()}")

if __name__ == "__main__":
    main()

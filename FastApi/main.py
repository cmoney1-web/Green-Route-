import math
import json
import copy
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse


app = FastAPI()

# Find the JSON files beside this Python file.
data_folder = Path(__file__).resolve().parent / "data"

with open(data_folder / "emission-factors.json", "r", ) as file:
    data = json.load(file)

with open(data_folder / "sample-response.json", "r",) as file:
    data1 = json.load(file)
    

# Calculate car emissions per person using the selected vehicle type.
def calculatecar(route, vehicle):
    factor = data["vehicles"][vehicle["type"]]["value"]
    return (route["distanceKm"] * factor) / vehicle["occupancy"]


# Add emissions from bus legs. Walking legs add zero.
def calculatebus(route):
    factor = data["vehicles"]["bus"]["value"]
    total = 0

    for leg in route["legs"]:
        if leg["mode"] == "bus":
            emissions = leg["distanceKm"] * factor
            total += emissions

    return total
    
    
#  #test cases for both car and bus mi amor
# test_car_route = {"distanceKm": 11}
# test_vehicle = {"type": "petrol", "occupancy": 2}

# car_result = calculatecar(test_car_route, test_vehicle)
# print("Car emissions:", car_result)

# test_bus_route = {
#     "legs": [
#         {"mode": "walk", "distanceKm": 0.5},
#         {"mode": "bus", "distanceKm": 9},
#         {"mode": "walk", "distanceKm": 0.5}
#     ]
# }

# bus_result = calculatebus(test_bus_route)
# print("Bus emissions:", bus_result)
    

@app.get("/")
def home():
    return {"chesney": "yes"}


@app.get("/api/health/status")
def health():
    return {
        "success": True,
        "status": "ok"
    }


@app.post("/api/journeys/plan")
def journey(body: dict):
    # FastAPI checks that the request body is a dictionary.
    # Start a new error list for every request.
    errors = []

    # Check the origin and destination coordinates.
    for field in ["origin", "destination"]:
        location = body.get(field)

        if not isinstance(location, dict):
            errors.append(f"{field} must contain latitude and longitude.")
            continue

        latitude = location.get("latitude")

        if type(latitude) not in (int, float) or not (-90 <= latitude <= 90):
            errors.append(f"{field}.latitude must be a number between -90 and 90.")

        longitude = location.get("longitude")

        if type(longitude) not in (int, float) or not (-180 <= longitude <= 180):
            errors.append(f"{field}.longitude must be a number between -180 and 180.")

    supported_modes = ["car", "bus", "bicycle", "walk"]
    allowed_modes = body.get("allowedModes")

    # Check that allowed modes is a list with at least one item.
    if not isinstance(allowed_modes, list) or len(allowed_modes) == 0:
        errors.append("allowedModes must be a list containing at least one mode.")
    else:
        for mode in allowed_modes:
            if mode not in supported_modes:
                errors.append("allowedModes supports car, bus, bicycle and walk.")
                break

    # Check that the time limit is a positive, finite number.
    max_duration = body.get("maxDurationMinutes")

    if type(max_duration) not in (int, float):
        errors.append("maxDurationMinutes must be a number greater than zero.")
    elif max_duration <= 0 or max_duration == math.inf or max_duration != max_duration:
        errors.append("maxDurationMinutes must be a number greater than zero.")

    # Check whether the user requested car travel.
    car_requested = False

    if isinstance(allowed_modes, list):
        car_requested = "car" in allowed_modes

    # Check car details when supplied or when car travel is requested.
    if car_requested or "vehicle" in body:
        supported_vehicles = ["petrol", "diesel", "hybrid", "electric"]
        vehicle = body.get("vehicle")

        if not isinstance(vehicle, dict):
            errors.append("vehicle must contain a type and occupancy.")
        else:
            vehicle_type = vehicle.get("type")
            occupancy = vehicle.get("occupancy")

            if vehicle_type not in supported_vehicles:
                errors.append("vehicle.type must be petrol, diesel, hybrid or electric.")

            if type(occupancy) is not int or occupancy < 1:
                errors.append("vehicle.occupancy must be a whole number of at least 1.")

    # Send all validation errors back to the user.
    if len(errors) > 0:
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "errors": errors
            }
        )
        
    

    #the code below : # Check the journey details, calculate emissions for the requested travel modes, and return the results.
    
    response = copy.deepcopy(data1) # Copy the sample data so changes for this request do not affect future requests.
    calculated_routes = []

    response["factorSource"] = data["source"]
    response["factorVersion"] = data["version"]

    for route in response["routes"]:
        # Skip transport modes the user did not request.
        if route["mode"] not in body["allowedModes"]:
            continue

        if route["mode"] == "car":
            vehicle = body["vehicle"]
            route["estimatedEmissionsKgCO2e"] = calculatecar(route, vehicle)
            route["emissionFactor"] = data["vehicles"][vehicle["type"]]
            route["vehicleType"] = vehicle["type"]

        if route["mode"] == "bus":
            route["estimatedEmissionsKgCO2e"] = calculatebus(route)
            route["emissionFactor"] = data["vehicles"]["bus"]

        calculated_routes.append(route)

    response["routes"] = calculated_routes
  
    
    # Find the fastest route.
    fastest_route = None
    for route in response["routes"]:
        if fastest_route is None:
            fastest_route = route
        elif route["durationMinutes"] < fastest_route["durationMinutes"]:
            fastest_route = route
            
    # Find the route with the lowest emissions.
    lowest_emission_route = None
    for route in response["routes"]:
        if lowest_emission_route is None:
            lowest_emission_route = route
        elif route["estimatedEmissionsKgCO2e"] < lowest_emission_route["estimatedEmissionsKgCO2e"]:
            lowest_emission_route = route

    # Choose the lowest-emission route within the user's time limit.
    recommended_route = None

    for route in response["routes"]:
        if route["durationMinutes"] <= body["maxDurationMinutes"]:
            if recommended_route is None:
                recommended_route = route
            elif (
                route["estimatedEmissionsKgCO2e"]
                < recommended_route["estimatedEmissionsKgCO2e"]
            ):
                recommended_route = route
            elif (
                route["estimatedEmissionsKgCO2e"]
                == recommended_route["estimatedEmissionsKgCO2e"]
                and route["durationMinutes"] < recommended_route["durationMinutes"]
            ):
                # When emissions match, choose the faster route.
                recommended_route = route

    # Explain the choice in the API response so Postman can display it.
    response["meetsTimeLimit"] = False

    if fastest_route is None:
        response["recommendationReason"] = "No routes are available for the requested modes."
    elif recommended_route is None:
        recommended_route = fastest_route
        response["recommendationReason"] = "The time limit is too short. Showing the fastest route."
    else:
        response["meetsTimeLimit"] = True
        response["recommendationReason"] = "Lowest estimated emissions within your time limit, choosing the faster route when emissions match."

    # Use empty IDs when there are no routes to choose from.
    response["fastestRouteId"] = None
    response["lowestEmissionRouteId"] = None
    response["recommendedRouteId"] = None

    if fastest_route is not None:
        response["fastestRouteId"] = fastest_route["id"]

    if lowest_emission_route is not None:
        response["lowestEmissionRouteId"] = lowest_emission_route["id"]

    if recommended_route is not None:
        response["recommendedRouteId"] = recommended_route["id"]

    return response
 
            

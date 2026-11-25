import math
import json
import os
import httpx
from pathlib import Path
from dotenv import load_dotenv

from fastapi import FastAPI
from fastapi.responses import JSONResponse


app = FastAPI()

# Find the JSON files beside this Python file.
data_folder = Path(__file__).resolve().parent / "data"

with open(data_folder / "emission-factors.json", "r", ) as file:
    data = json.load(file)

    
    
# Load the environment file beside main.py.
env_file = Path(__file__).resolve().parent / "chesney.env"
load_dotenv(env_file)

#reads the key
geoapify_api_key = os.getenv("GEOAPIFY_API_KEY")

if not geoapify_api_key:
    raise RuntimeError("Add GEOAPIFY_API_KEY to chesney.env.")
    

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
    
#function for fetching a car route

#this loads the car route using the api 

def get_car_route(origin, destination):
    # Geoapify expects latitude,longitude for each location.
    start = f'{origin["latitude"]},{origin["longitude"]}'
    end = f'{destination["latitude"]},{destination["longitude"]}'

    parameters = {
        "waypoints": f"{start}|{end}",
        "mode": "drive",
        "format": "geojson",
        "units": "metric",
        "apiKey": geoapify_api_key
    }

    #if the request takes to long it stops waiting
    with httpx.Client(timeout=15) as client:
        response = client.get(
            "https://api.geoapify.com/v1/routing",
            params=parameters
        )

        response.raise_for_status()

        return response.json()



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
        
    

    # This first real-route connection supports driving.
    if "car" not in body["allowedModes"]:
        return JSONResponse(
            status_code=400,
            content={
                "message": "Only driving is connected so far. Include car in allowedModes."
            }
        )

    #real route request now
    try:
        route_data = get_car_route(body["origin"], body["destination"])
    except httpx.TimeoutException:
        return JSONResponse(
            status_code=504,
            content={"message": "The routing service took too long. Try again."}
        )
    except httpx.HTTPStatusError:
        # Keep the provider's request URL private because it contains the key.
        return JSONResponse(
            status_code=502,
            content={"message": "The routing service rejected the request. Check the API key and quota."}
        )
    except httpx.RequestError:
        return JSONResponse(
            status_code=502,
            content={"message": "Could not connect to the routing service."}
        )
    except ValueError:
        return JSONResponse(
            status_code=502,
            content={"message": "The routing service returned invalid JSON."}
        )

    # Check the returned data before trying to read its first route.
    if not isinstance(route_data, dict) or not isinstance(route_data.get("features"), list):
        return JSONResponse(
            status_code=502,
            content={"message": "The routing service returned an unexpected response."}
        )

    if len(route_data["features"]) == 0:
        return JSONResponse(
            status_code=404,
            content={"message": "No driving route was found."}
        )

    try:
        first_route = route_data["features"][0]
        properties = first_route["properties"]
        distance_metres = properties["distance"]
        duration_seconds = properties["time"]
        geometry = first_route["geometry"]
    except (KeyError, TypeError):
        return JSONResponse(
            status_code=502,
            content={"message": "The routing response is missing route details."}
        )

    #the number must be zero or greater in order for it to work
    for value in [distance_metres, duration_seconds]:
        if type(value) not in (int, float) or not (0 <= value < math.inf):
            return JSONResponse(
                status_code=502,
                content={"message": "The routing response contains an invalid distance or time."}
            )

    distance_km = distance_metres / 1000
    duration_minutes = duration_seconds / 60

    # Keep the field names your calculator and recommendation loops already use.
    route_dictionary = {
        "id": "geoapify-car",
        "name": "Driving Route",
        "mode": "car",
        "distanceKm": distance_km,
        "durationMinutes": duration_minutes,
        "geometry": geometry,
        "legs": [
            {
                "mode": "car",
                "distanceKm": distance_km,
                "durationMinutes": duration_minutes
            }
        ]
    }

    # Calculate estimated emissions using the user's vehicle and occupancy.
    vehicle = body["vehicle"]
    route_dictionary["estimatedEmissionsKgCO2e"] = calculatecar(route_dictionary, vehicle)
    route_dictionary["vehicleType"] = vehicle["type"]
    route_dictionary["emissionFactor"] = data["vehicles"][vehicle["type"]]

    # Return the real driving route to the existing recommendation loops.
    response = {
        "dataSource": "geoapify",
        "routes": [route_dictionary]
    }

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
        response["recommendationReason"] = "cant find any thing for this specific route"
    elif recommended_route is None:
        recommended_route = fastest_route
        response["recommendationReason"] = "The time limit is too short. Showing the fastest route."
    else:
        response["meetsTimeLimit"] = True
        response["recommendationReason"] = "Lowest estimated emissions within your time limit, choosing the faster route when emissions match."

    #when no routes are avalaible all these values will appear as none
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


# TODO: Connect real cycling, walking and scheduled public transport routes.

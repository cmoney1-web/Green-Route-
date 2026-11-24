import express from "express";
import fs from "fs";
// Read the sample routes and testing factors from JSON files.
// Using the file's location lets the server start from any folder.
const data = fs.readFileSync(
  new URL("./data/sample-response.json", import.meta.url),
  "utf8",
);
const data1 = JSON.parse(data);
const factorData = fs.readFileSync(
  new URL("./data/emission-factors.json", import.meta.url),
  "utf8",
);
const emissionFactors = JSON.parse(factorData);
const app = express();
const port = process.env.PORT || 3000;

// Read JSON sent in a request and store it in req.body.
app.use(express.json());

// A car factor is for the whole vehicle, so divide by the people in it.
function calculateCarboncar(route, vehicle) {
  const factor = emissionFactors.vehicles[vehicle.type].value;
  return (route.distanceKm * factor) / vehicle.occupancy;
}

// Add the emissions for every bus leg. Walking legs add zero.
function calculateCarbonbus(route) {
  const factor = emissionFactors.vehicles.bus.value;
  let total = 0;

  for (const leg of route.legs) {
    if (leg.mode === "bus") {
      const emissions = leg.distanceKm * factor;
      total = total + emissions;
    }
  }

  return total;
}

app.get("/", (req, res) => {
  res.send("hello from simple server :)");
});
app.get("/api/health/status", (req, res) => {
  // returns the health status
  res.status(200).json({
    success: true,
    status: "ok",
  });
});

app.post("/api/journeys/plan", (req, res) => {
  const body = req.body;

  if (!body || typeof body !== "object" || Array.isArray(body)) {
    return res.status(400).json({
      success: false,
      errors: ["Send a JSON object containing your journey details."],
    });
  }

  const errors = [];

  // Check the origin and destination coordinates.
  for (const field of ["origin", "destination"]) {
    const location = body[field];

    if (!location || typeof location !== "object" || Array.isArray(location)) {
      errors.push(`${field} must contain latitude and longitude.`);
      continue;
    }

    if (
      !Number.isFinite(location.latitude) ||
      location.latitude < -90 ||
      location.latitude > 90
    ) {
      errors.push(`${field}.latitude must be a number between -90 and 90.`);
    }

    if (
      !Number.isFinite(location.longitude) ||
      location.longitude < -180 ||
      location.longitude > 180
    ) {
      errors.push(`${field}.longitude must be a number between -180 and 180.`);
    }
  }

  const supportedModes = ["car", "bus", "bicycle", "walk"];

  if (!Array.isArray(body.allowedModes) || body.allowedModes.length === 0) {
    errors.push("allowedModes must be a list containing at least one mode.");
  } else if (body.allowedModes.some((mode) => !supportedModes.includes(mode))) {
    errors.push("allowedModes supports car, bus, bicycle and walk.");
  }

  if (
    !Number.isFinite(body.maxDurationMinutes) ||
    body.maxDurationMinutes <= 0
  ) {
    errors.push("maxDurationMinutes must be a number greater than zero.");
  }

  // Validate car details when supplied or when car travel is requested.
  const carRequested =
    Array.isArray(body.allowedModes) && body.allowedModes.includes("car");

  if (carRequested || body.vehicle !== undefined) {
    const supportedVehicles = ["petrol", "diesel", "hybrid", "electric"];

    if (
      !body.vehicle ||
      typeof body.vehicle !== "object" ||
      Array.isArray(body.vehicle)
    ) {
      errors.push("vehicle must contain a type and occupancy.");
    } else {
      if (!supportedVehicles.includes(body.vehicle.type)) {
        errors.push("vehicle.type must be petrol, diesel, hybrid or electric.");
      }

      if (
        !Number.isInteger(body.vehicle.occupancy) ||
        body.vehicle.occupancy < 1
      ) {
        errors.push("vehicle.occupancy must be a whole number of at least 1.");
      }
    }
  }

  if (errors.length > 0) {
    return res.status(400).json({
      success: false,
      errors,
    });
  }

  // Make a fresh copy so one request cannot change the next request's data.
  const response = structuredClone(data1);
  const calculatedRoutes = [];
  response.factorSource = emissionFactors.source;
  response.factorVersion = emissionFactors.version;

  for (const route of response.routes) {
    // Return only modes the user asked for. Car details are only needed for cars.
    if (!body.allowedModes.includes(route.mode)) {
      continue;
    }

    if (route.mode === "car") {
      route.estimatedEmissionsKgCO2e = calculateCarboncar(route, body.vehicle);
      route.emissionFactor = emissionFactors.vehicles[body.vehicle.type];
      route.vehicleType = body.vehicle.type;
    }

    if (route.mode === "bus") {
      route.estimatedEmissionsKgCO2e = calculateCarbonbus(route);
      route.emissionFactor = emissionFactors.vehicles.bus;
    }

    calculatedRoutes.push(route);
  }

  response.routes = calculatedRoutes;
  // return res.status(200).json(response);


  //fastest route logic
  let fastestRoute=null;
  for(const route of response.routes)
  {
   if(fastestRoute==null)
   {
      fastestRoute=route // remeber the first route
   }
   else if(route.durationMinutes<fastestRoute.durationMinutes) // if it is less than this is the current fastest route
   {
      fastestRoute=route
   }
   
  }
   // lowest emmision route
   let lowestEmissionRoute=null
   for(const route of response.routes)
   {
      if(lowestEmissionRoute===null)
      {
         lowestEmissionRoute=route
      }
      else if(route.estimatedEmissionsKgCO2e<lowestEmissionRoute.estimatedEmissionsKgCO2e)
      {
         lowestEmissionRoute=route
      }
   }
   
   //recomnmended route logic now
   let recommended_route=null

   for(const route of response.routes)
   {
      // only consider the routes that the user picks
      if(route.durationMinutes<=body.maxDurationMinutes)
      {
         if(recommended_route===null)
         {
            recommended_route=route
         }
         else if(route.estimatedEmissionsKgCO2e<recommended_route.estimatedEmissionsKgCO2e)
         {
            recommended_route=route
         }
         else if(route.estimatedEmissionsKgCO2e=== recommended_route.estimatedEmissionsKgCO2e && route.durationMinutes < recommended_route.durationMinutes)
         {
            recommended_route=route
         }
      }
   }
   if (recommended_route===null)
   {
      recommended_route=fastestRoute
      console.log("the time limit is too short");
      
   }
   if(fastestRoute===null)
   {
      console.log("there is not routes available try again please");
      
   }
 console.log("if you know what this means and if you do not then you have to do better if ");
 

 



});

app.listen(port, () =>
  console.log("> Server is up and running on port : " + port),
);


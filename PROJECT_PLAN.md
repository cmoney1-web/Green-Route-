# GreenRoute implementation plan

Build a responsive web app for a campus commuter. A commuter enters two places, compares feasible routes by time and estimated emissions, chooses a trip, and records it after travelling. My Impact then shows the estimated difference against a comparable car trip.

Use one campus and its surrounding area for the first release. This plan uses an Irish campus as a working assumption so it can name a transit feed. Pick your actual campus and swap the local data sources if needed. Use GreenRoute in the interface to match the repository. The design PDFs use the name EcoPath.

## 1. Set up the project and build a fixture demo

- Create a React app with Vite's JavaScript template. Use `.jsx` for React components and `.js` for logic such as the carbon calculator. When you connect routing services, add a small Node.js and Express server in JavaScript. Use Leaflet for the map and SQLite for trip history. Add setup instructions and an `.env.example` as you introduce configuration.
- Build two pages, Route Planner and My Impact. In the planner, put the origin, destination, mode controls and route cards beside the map on desktop. Stack them on mobile. Use the planner mockup's map layer toggle and potential savings panel.
- Add one saved test scenario with the four routes from the brief. Use small sample GeoJSON lines for the map. Label the scenario **Demo data** and use it as an offline fallback through development.
- Make each route card select its matching map line. Give the user a way to enter a maximum journey time and choose which modes to consider. Use the same labels for origin and destination in the form, map markers and route results.

**Done when** you can select all four test routes, see the matching line, and use the planner on a narrow screen with a keyboard.

## 2. Implement the carbon calculator and eco-routing rules

- Use the class diagram as a guide for plain JavaScript objects. Start with `Journey` (request and options), `RouteOption` (mode, distance, duration and geometry), `TransportMode` (mode and factor reference) and `User` (preferences and trip ownership). Give a journey an optional selected route. Add `RouteLeg` so a transit option can contain walking and transit segments. Use `CarbonCalculator` and `EcoRoutingEngine` as independent JavaScript modules with functions that take inputs and return results. Implement `BehaviouralNudge` as a rule that returns a message and `SustainabilityDashboard` as a view over trip summaries.
- Display **estimated kg CO₂e per traveller**. For cars, multiply vehicle distance by a `kg CO₂e / vehicle-km` factor and divide by the number of people in the car, including the driver. For transit, multiply each transit leg's distance by its `kg CO₂e / passenger-km` factor. A passenger-km factor already reflects an occupancy assumption. Sum all leg estimates. Use zero for walking and conventional cycling under the chosen operational boundary.
- Keep factors in a versioned data file with units, geography, year, source and emissions scope. Use consistent operational boundaries across modes and document what the estimates cover. Use local factors if available. The [UK government 2026 conversion factors](https://www.gov.uk/government/publications/greenhouse-gas-reporting-conversion-factors-2026) are a possible labelled UK proxy for an Irish prototype. Use the brief's values as fixtures. For the first release, use distance, vehicle type and occupancy. Add elevation and traffic adjustments after you have suitable data and a documented calculation model.
- Show **Fastest** and **Lowest emissions** for the returned options allowed by the user's mode choices. For **Recommended**, choose the lowest estimated emissions among options that meet the user's time limit, then break ties by time, distance and stable ID. Show routes with unknown emissions as **Estimate unavailable** and exclude them from emissions ranking. If every option that fits has unknown emissions, show the fastest fitting option and explain why an emissions-based recommendation is unavailable. Show the fastest allowed option with a clear time-limit warning if none fit. Use this time limit as the first implementation of the time preference shown in the class diagram.
- Use the fastest same-journey car option as the explicit savings baseline, using the traveller's selected vehicle type and occupancy. Compute `car baseline − chosen route`. Show a signed difference when the chosen route emits more. If the baseline is unavailable, show the route estimate and leave savings unavailable.

**Done when** the brief's fixed fixture yields car A as fastest at 18 minutes, cycling as lowest emissions, and the bus as recommended under a 30-minute limit. The bus card shows a saving of 1.8 kg and a 10-minute trade-off using fixture values. The calculator also passes a separate unit test where `10 km × 0.20 kg CO₂e/vehicle-km ÷ 2` gives `1.00 kg CO₂e per traveller`. The factor in that test is illustrative.

## 3. Connect real routes

- Add `GET /api/locations?q=...` for place search and `POST /api/journeys/plan` for selected coordinates, departure time, allowed modes, maximum duration, vehicle type and occupancy. Keep provider credentials on the server. Normalize provider responses into the same route structure used by the fixture. Include route geometry, duration, per-mode availability and factor version in the response.
- Start with driving, cycling and walking from openrouteservice. Test one known campus pair first, then request driving alternatives where supported. Draw the returned geometry and retain the tile provider's attribution. Candidate reranking operates over returned routes. [openrouteservice endpoints](https://giscience.github.io/openrouteservice/v9.10.0/api-reference/endpoints/) · [Hosted API limits](https://giscience.github.io/openrouteservice/hosted-api-restrictions) · [Leaflet quick start](https://leafletjs.com/examples/quick-start/)
- Add scheduled transit for the pilot area. For Ireland, load the relevant National Transport Authority GTFS feed and a matching OpenStreetMap extract into OpenTripPlanner. Check a single itinerary in its own interface before wiring your backend to it. Convert the response into walking and transit legs. Include access walking, waiting, transfers and final walking in total journey time. Show a scheduled label and handle departures with no service. [NTA GTFS dataset](https://data.gov.ie/dataset/nta-gtfs) · [OpenTripPlanner tutorial](https://docs.opentripplanner.org/en/latest/Basic-Tutorial/)
- Surface missing routes, service timeouts and rate limits in the affected mode while preserving results from the other providers. Keep fixture mode explicitly selectable so the demo still works offline.

**Done when** a commuter can look up two real places and compare returned options around the pilot campus. Test a departure with a bus itinerary and one without service.

## 4. Add trip logging, My Impact and nudges

- Turn the mockup's **Start Journey** into a simple trip lifecycle. Selecting or starting a route creates a planned trip. The user presses **Mark trip complete** after travelling. Save the trip owner, completion time, route mode and distance, emissions estimate, baseline estimate and factor version. Complete each trip once, even on repeated clicks or retries. A demo profile is enough for development. Use per-user access before sharing a multi-user deployment.
- Build My Impact from completed trips. Start with completed trip count, distance travelled on lower-emissions trips, estimated difference versus the car baseline, a weekly trend and savings by mode. Use local dates for weekly and monthly groupings. Include a table or text summary of chart data. Show a clear empty state and report how many trips had a comparable baseline. Use positive savings for the donut chart and label that scope, since a donut cannot represent negative values.
- Add a route-card nudge when a feasible lower-emission option has a known saving. For the demo fixture, use “The bus saves an estimated 1.8 kg compared with the fastest car route and takes 10 minutes longer.” Add the mockup's weekly bus challenge once trip logging can count completions. Drive the target from completed bus trips and the savings from their actual comparison values.
- Treat rewards redemption, communities, campus rank, turn-by-turn guidance and emissions equivalencies as extensions. Prioritise the complete route comparison and trip feedback flow before adding them.

**Done when** completing a bus trip updates the weekly total, breakdown and challenge exactly once. A planned or cancelled trip adds nothing to completed impact. A refresh preserves completed data.

## 5. Build the Carbon Heatmap

- Start with **Estimated route emissions** in the mockup's map layer control. Apply it to the currently selected route. Show an intensity legend in `g CO₂e per traveller-km` so longer segments do not automatically appear more intense. Where you only have one factor for a route leg, display uniform intensity for that leg and explain the source in the legend. Use a distinct style for missing data.
- Add a corridor heatmap for the pilot campus using a documented set of representative car routes. Split those routes into mapped segments, compute intensity from each segment's estimated emissions and length, and combine repeated segments consistently, such as by averaging their intensity. Label the result as modelled for sampled routes and state the vehicle, occupancy, coverage and dataset date. Add local traffic and gradient variation only when the model has validated inputs for them.

**Done when** the layer toggle and legend explain the metric, the visible colours match known input values, and uncovered streets are clearly distinguishable from streets with low estimated emissions.

## 6. Test, deploy and prepare the project demonstration

| Area | Acceptance checks |
| --- | --- |
| Search and routing | Ambiguous place, invalid coordinates, no route, missed transit service and partial provider failure |
| Calculator | Metres-to-kilometres conversion, car occupancy of 1 and 2, invalid occupancy, active travel, mixed-mode leg sum and unavailable factor |
| Recommendation | Fastest and greenest differ, time limit changes the recommendation, ties are deterministic and no option fits the limit |
| Impact | Missing car baseline, negative trip difference, repeated completion, empty history and crossing a local week boundary |
| UI and map | Phone and desktop layouts, keyboard navigation, selectable lines, map legend, provider attribution and meaningful error states |

- Document setup, credentials, supported area, data and factor sources, estimation boundary and how to reproduce the demo. Keep API secrets in environment variables and use persistent storage for SQLite on the deployment. Deployment must also be able to reach the transit backend.
- Demonstrate the fixture first so assessors can verify the calculation. Then enter a real campus journey, compare the modes, change the time limit, inspect the map layer, complete a trip, and check that My Impact changes once.
- For the report, capture the updated class diagram with `RouteLeg` and trip completion. Update the flowchart's “Best option is sustainable?” decision to “Does a route meet the selected modes and time limit?” Show the fallback path and add selection, completion and the dashboard update. Record how you evaluated correctness. If you test with commuters, check whether they can explain the estimate and make an informed choice, and describe any observed change as part of your test rather than assuming long-term behaviour change.

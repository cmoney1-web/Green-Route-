const emissionFactors = {
   source: "Illustrative development values",
   year: null,
   version: "demo-1",

   vehicles: {
      petrol: {
         value: 0.20,
         unit: "kg CO2e per vehicle-km"
      },

      diesel: {
         value: 0.18,
         unit: "kg CO2e per vehicle-km"
      },

      hybrid: {
         value: 0.12,
         unit: "kg CO2e per vehicle-km"
      },

      electric: {
         value: 0.05,
         unit: "kg CO2e per vehicle-km"
      },

      bus: {
         value: 0.06,
         unit: "kg CO2e per passenger-km"
      },

      bicycle: {
         value: 0,
         unit: "kg CO2e per passenger-km"
      },

      walk: {
         value: 0,
         unit: "kg CO2e per passenger-km"
      }
   }
}

function calculateCarboncar(distance,occupancy){
return (distance*emissionFactors.vehicles.petrol.value)/occupancy
}
function calculateCarbonbus(distance){ // per passenger
    return distance*emissionFactors.vehicles.bus.value
}




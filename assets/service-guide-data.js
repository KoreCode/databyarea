window.DBA_SERVICE_GUIDES = {
  plumber: {
    label: "Plumber Rates",
    service: "plumber",
    unit: "hour",
    range: "$85-$165/hr",
    low: 85,
    high: 165,
    projectExamples: [
      "Leak repair or drain clearing",
      "Fixture and faucet replacement",
      "Water heater installation",
      "Pipe replacement or rerouting"
    ],
    drivers: [
      "Emergency versus scheduled service",
      "Pipe material and accessibility",
      "Local plumbing codes",
      "Fixture quality and replacement scope"
    ],
    related: ["water-heater", "electrician", "hvac"]
  },
  electrician: {
    label: "Electrician Rates",
    service: "electrician",
    unit: "hour",
    range: "$90-$175/hr",
    low: 90,
    high: 175,
    projectExamples: [
      "Panel inspection or repair",
      "Outlet and switch installation",
      "EV charger installation",
      "Rewiring and dedicated circuits"
    ],
    drivers: [
      "Panel capacity and existing wiring condition",
      "Permit and inspection requirements",
      "Circuit complexity",
      "Material and device quality"
    ],
    related: ["hvac", "plumber", "water-heater"]
  },
  hvac: {
    label: "HVAC Installation",
    service: "HVAC contractor",
    unit: "project",
    range: "$5,500-$14,500",
    low: 5500,
    high: 14500,
    projectExamples: [
      "Central AC replacement",
      "Furnace replacement",
      "Heat pump installation",
      "Ductwork repair or replacement"
    ],
    drivers: [
      "System size and efficiency rating",
      "Duct condition",
      "Local climate",
      "Electrical or permit work"
    ],
    related: ["electrician", "plumber", "water-heater"]
  },
  roofing: {
    label: "Roof Replacement",
    service: "roofer",
    unit: "project",
    range: "$8,000-$24,000",
    low: 8000,
    high: 24000,
    projectExamples: [
      "Asphalt shingle replacement",
      "Roof deck repair",
      "Flashing and ventilation work",
      "Tear-off and disposal"
    ],
    drivers: [
      "Roof size and pitch",
      "Material choice",
      "Decking condition",
      "Storm exposure and local labor demand"
    ],
    related: ["garage-door", "foundation", "concrete-driveway"]
  },
  "water-heater": {
    label: "Water Heater Installation",
    service: "water heater installer",
    unit: "project",
    range: "$1,200-$4,500",
    low: 1200,
    high: 4500,
    projectExamples: [
      "Tank water heater replacement",
      "Tankless water heater installation",
      "Expansion tank or valve work",
      "Vent and gas line adjustments"
    ],
    drivers: [
      "Tank versus tankless system",
      "Fuel type",
      "Code upgrades",
      "Access and disposal"
    ],
    related: ["plumber", "electrician", "hvac"]
  },
  "garage-door": {
    label: "Garage Door Repair",
    service: "garage door contractor",
    unit: "project",
    range: "$180-$1,800",
    low: 180,
    high: 1800,
    projectExamples: [
      "Spring replacement",
      "Opener installation",
      "Panel replacement",
      "Full door replacement"
    ],
    drivers: [
      "Door size and material",
      "Spring and opener type",
      "Emergency timing",
      "Track or panel damage"
    ],
    related: ["roofing", "foundation", "concrete-driveway"]
  },
  foundation: {
    label: "Foundation Repair",
    service: "foundation repair contractor",
    unit: "project",
    range: "$2,500-$18,000",
    low: 2500,
    high: 18000,
    projectExamples: [
      "Crack repair",
      "Pier installation",
      "Basement waterproofing",
      "Structural stabilization"
    ],
    drivers: [
      "Soil movement",
      "Structural severity",
      "Water intrusion",
      "Engineering and permit needs"
    ],
    related: ["concrete-driveway", "roofing", "garage-door"]
  },
  "concrete-driveway": {
    label: "Concrete Driveway Cost",
    service: "concrete contractor",
    unit: "project",
    range: "$4,000-$12,000",
    low: 4000,
    high: 12000,
    projectExamples: [
      "Driveway replacement",
      "Concrete removal",
      "Base preparation",
      "Stamped or reinforced concrete"
    ],
    drivers: [
      "Square footage",
      "Concrete thickness",
      "Site preparation",
      "Finish and reinforcement"
    ],
    related: ["foundation", "garage-door", "roofing"]
  }
};

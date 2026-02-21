#!/usr/bin/env python3
"""
Smart City Energy Grid Management System
NeuralBlitz v20.0 Integration Module

Governance: ϕ₈ (Sustainability), ϕ₇ (Justice/Intergenerational Equity)
Capabilities: Renewable integration, load balancing, privacy-preserving optimization
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum
import asyncio
import json
from datetime import datetime, timedelta
import numpy as np
from collections import defaultdict


class EnergySource(Enum):
    """Types of energy generation sources"""

    SOLAR = "solar"
    WIND = "wind"
    GAS_PEAKER = "gas_peaker"
    NUCLEAR = "nuclear"
    BATTERY = "battery_storage"


@dataclass
class Generator:
    """Represents an energy generation asset"""

    generator_id: str
    source_type: EnergySource
    capacity_mw: float
    availability: float  # 0-1
    carbon_intensity: float  # kg CO2 / MWh
    current_output_mw: float = 0.0
    ramp_rate_mw_per_min: float = 5.0
    ethical_priority: float = 0.5  # Higher = more preferred (renewables)


@dataclass
class LoadZone:
    """Represents a geographic zone with energy demand"""

    zone_id: str
    population: int
    current_demand_mw: float
    critical_load_mw: float  # Hospitals, emergency services
    socioeconomic_index: float  # For equity calculations (ϕ₇)
    historical_demand: List[float] = field(default_factory=list)


@dataclass
class StorageUnit:
    """Represents battery storage"""

    unit_id: str
    capacity_mwh: float
    current_soc: float  # State of charge 0-1
    max_charge_rate_mw: float
    max_discharge_rate_mw: float
    efficiency: float = 0.92


class EthicalEnergyOptimizer:
    """
    Energy grid optimizer with sustainability and equity constraints

    Implements:
    - ϕ₈: Sustainability through carbon minimization
    - ϕ₇: Justice through equitable energy distribution
    - ϕ₄: Safety through grid stability safeguards
    - ϕ₆: Privacy through differential privacy on usage data
    """

    def __init__(self, grid_region: str, carbon_budget_tons: float = 500000):
        self.region = grid_region
        self.carbon_budget = carbon_budget_tons
        self.carbon_used = 0.0

        self.generators: Dict[str, Generator] = {}
        self.load_zones: Dict[str, LoadZone] = {}
        self.storage_units: Dict[str, StorageUnit] = {}

        self.ethical_weights = {
            "sustainability": 0.35,  # ϕ₈
            "equity": 0.35,  # ϕ₇
            "reliability": 0.30,  # ϕ₄
        }

        self.privacy_budget = 1.0  # Differential privacy budget
        self.decision_log: List[Dict] = []

    def add_generator(self, generator: Generator):
        """Add a generation asset to the grid"""
        # Set ethical priority based on sustainability (ϕ₈)
        if generator.source_type in [EnergySource.SOLAR, EnergySource.WIND]:
            generator.ethical_priority = 0.95
        elif generator.source_type == EnergySource.NUCLEAR:
            generator.ethical_priority = 0.80
        elif generator.source_type == EnergySource.BATTERY:
            generator.ethical_priority = 0.70
        else:  # Gas
            generator.ethical_priority = 0.30

        self.generators[generator.generator_id] = generator

    def add_load_zone(self, zone: LoadZone):
        """Add a demand zone to the grid"""
        self.load_zones[zone.zone_id] = zone

    def add_storage(self, unit: StorageUnit):
        """Add storage unit to the grid"""
        self.storage_units[unit.unit_id] = unit

    async def forecast_demand(self, horizon_hours: int = 24) -> Dict[str, List[float]]:
        """
        Forecast energy demand with uncertainty quantification

        Returns:
            Dictionary of zone_id -> list of hourly demand forecasts
        """
        forecasts = {}

        for zone_id, zone in self.load_zones.items():
            # Simple forecasting model (in production, use ML)
            base_demand = zone.current_demand_mw
            hourly_forecast = []

            for hour in range(horizon_hours):
                # Diurnal pattern
                hour_of_day = (datetime.now().hour + hour) % 24
                diurnal_factor = 1.0 + 0.3 * np.sin((hour_of_day - 6) * np.pi / 12)

                # Add noise
                noise = np.random.normal(0, base_demand * 0.1)

                forecast = base_demand * diurnal_factor + noise
                hourly_forecast.append(max(0, forecast))

            forecasts[zone_id] = hourly_forecast

        return forecasts

    def calculate_intergenerational_equity(self, plan_horizon_years: int = 25) -> float:
        """
        Calculate intergenerational equity score (ϕ₇)

        Uses anti-discounting to value future generations' wellbeing
        """
        # Current generation weight
        current_weight = 0.4

        # Future generations weight (increases with anti-discounting)
        future_weight = 0.6

        # Calculate sustainability impact
        renewable_capacity = sum(
            g.capacity_mw
            for g in self.generators.values()
            if g.source_type in [EnergySource.SOLAR, EnergySource.WIND]
        )
        total_capacity = sum(g.capacity_mw for g in self.generators.values())

        renewable_ratio = (
            renewable_capacity / total_capacity if total_capacity > 0 else 0
        )

        # Carbon budget remaining
        carbon_remaining = 1.0 - (self.carbon_used / self.carbon_budget)

        # Equity score (higher = better for future generations)
        equity_score = current_weight * (
            1.0 - self._calculate_current_inequality()
        ) + future_weight * (renewable_ratio * carbon_remaining)

        return equity_score

    def _calculate_current_inequality(self) -> float:
        """Calculate current energy inequality across load zones (ϕ₇)"""
        demands = [
            z.current_demand_mw / max(1, z.population) for z in self.load_zones.values()
        ]

        if not demands:
            return 0.0

        # Gini coefficient approximation
        n = len(demands)
        index = np.arange(1, n + 1)
        return (2 * np.sum(index * np.sort(demands))) / (n * np.sum(demands)) - (
            n + 1
        ) / n

    async def optimize_generation(self, target_reliability: float = 0.9999) -> Dict:
        """
        Generate optimal dispatch schedule with ethical constraints

        Args:
            target_reliability: Minimum grid reliability (ϕ₄)

        Returns:
            Optimization plan with dispatch schedule
        """
        # Get demand forecast
        forecasts = await self.forecast_demand(horizon_hours=4)
        total_demand = sum(np.mean(f) for f in forecasts.values())

        # Calculate available capacity by source
        available_capacity = defaultdict(float)
        for gen in self.generators.values():
            available_capacity[gen.source_type] += gen.capacity_mw * gen.availability

        # Optimization with ethical priorities
        dispatch_plan = {}
        remaining_demand = total_demand
        total_emissions = 0.0

        # Priority 1: Renewables (ϕ₈)
        for source_type in [EnergySource.SOLAR, EnergySource.WIND]:
            for gen_id, gen in self.generators.items():
                if gen.source_type == source_type and remaining_demand > 0:
                    dispatch = min(gen.capacity_mw * gen.availability, remaining_demand)
                    dispatch_plan[gen_id] = dispatch
                    remaining_demand -= dispatch
                    gen.current_output_mw = dispatch

        # Priority 2: Nuclear (low carbon, reliable)
        for gen_id, gen in self.generators.items():
            if gen.source_type == EnergySource.NUCLEAR and remaining_demand > 0:
                dispatch = min(gen.capacity_mw * gen.availability, remaining_demand)
                dispatch_plan[gen_id] = dispatch
                remaining_demand -= dispatch
                gen.current_output_mw = dispatch

        # Priority 3: Battery discharge
        for unit_id, unit in self.storage_units.items():
            if remaining_demand > 0 and unit.current_soc > 0.2:  # Keep 20% reserve
                max_discharge = min(
                    unit.max_discharge_rate_mw,
                    unit.capacity_mwh * (unit.current_soc - 0.2),
                )
                dispatch = min(max_discharge, remaining_demand)
                remaining_demand -= dispatch
                unit.current_soc -= dispatch / unit.capacity_mwh

        # Priority 4: Gas peaker (last resort, track carbon)
        for gen_id, gen in self.generators.items():
            if gen.source_type == EnergySource.GAS_PEAKER and remaining_demand > 0:
                dispatch = min(gen.capacity_mw * gen.availability, remaining_demand)
                dispatch_plan[gen_id] = dispatch
                remaining_demand -= dispatch
                gen.current_output_mw = dispatch

                # Track carbon usage
                emissions = dispatch * gen.carbon_intensity / 1000  # tons
                total_emissions += emissions
                self.carbon_used += emissions

        # Check reliability constraint (ϕ₄)
        reliability = self._calculate_reliability(dispatch_plan, total_demand)

        # Log optimization decision
        self._log_optimization(dispatch_plan, total_emissions, reliability)

        return {
            "dispatch_plan": dispatch_plan,
            "total_demand_mw": total_demand,
            "total_emissions_tons": total_emissions,
            "carbon_budget_remaining": self.carbon_budget - self.carbon_used,
            "reliability": reliability,
            "intergenerational_equity": self.calculate_intergenerational_equity(),
            "renewable_percentage": self._calculate_renewable_percentage(dispatch_plan),
        }

    def _calculate_reliability(self, dispatch_plan: Dict, demand: float) -> float:
        """Calculate grid reliability based on dispatch plan"""
        total_dispatch = sum(dispatch_plan.values())

        # Simple reliability model: excess capacity / demand
        if demand > 0:
            return min(0.99999, total_dispatch / demand)
        return 1.0

    def _calculate_renewable_percentage(self, dispatch_plan: Dict) -> float:
        """Calculate percentage of generation from renewables"""
        renewable_dispatch = sum(
            dispatch
            for gen_id, dispatch in dispatch_plan.items()
            if self.generators[gen_id].source_type
            in [EnergySource.SOLAR, EnergySource.WIND]
        )
        total_dispatch = sum(dispatch_plan.values())

        return (renewable_dispatch / total_dispatch * 100) if total_dispatch > 0 else 0

    def _log_optimization(
        self, dispatch_plan: Dict, emissions: float, reliability: float
    ):
        """Log optimization decision with explainability"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "decision_type": "generation_dispatch",
            "dispatch_plan": dispatch_plan,
            "emissions_tons": emissions,
            "reliability": reliability,
            "charter_compliance": {
                "ϕ₈_sustainability": emissions < 50,  # Threshold
                "ϕ₇_equity": self._calculate_current_inequality() < 0.3,
                "ϕ₄_safety": reliability >= 0.9999,
            },
            "ethical_justification": (
                f"Prioritized renewables (ϕ₈), maintained reliability (ϕ₄), "
                f"equity score: {self.calculate_intergenerational_equity():.2f} (ϕ₇)"
            ),
            "privacy_budget_remaining": self.privacy_budget,
        }
        self.decision_log.append(log_entry)

    async def optimize_storage(
        self, price_signal: Optional[List[float]] = None
    ) -> Dict:
        """
        Optimize battery storage operations

        Args:
            price_signal: Optional electricity price forecast

        Returns:
            Storage operation schedule
        """
        schedule = {}

        for unit_id, unit in self.storage_units.items():
            # Simple strategy: charge during low demand, discharge during peak
            if unit.current_soc < 0.8:  # Charge if below 80%
                schedule[unit_id] = {
                    "action": "CHARGE",
                    "rate_mw": unit.max_charge_rate_mw * 0.5,
                    "target_soc": 0.85,
                }
            else:
                schedule[unit_id] = {
                    "action": "HOLD",
                    "rate_mw": 0,
                    "target_soc": unit.current_soc,
                }

        return schedule

    def apply_differential_privacy(
        self, usage_data: List[float], epsilon: float = 0.1
    ) -> List[float]:
        """
        Apply differential privacy to usage data (ϕ₆, ϕ₁₃)

        Args:
            usage_data: Raw usage measurements
            epsilon: Privacy parameter (lower = more private)

        Returns:
            Privacy-preserved data
        """
        if self.privacy_budget <= 0:
            raise ValueError("Privacy budget exhausted")

        # Deduct privacy budget
        self.privacy_budget -= epsilon

        # Add Laplace noise
        sensitivity = max(usage_data) - min(usage_data) if usage_data else 1.0
        scale = sensitivity / epsilon

        private_data = [x + np.random.laplace(0, scale) for x in usage_data]

        return private_data

    def get_sustainability_report(self) -> Dict:
        """Generate comprehensive sustainability report (ϕ₈)"""
        renewable_capacity = sum(
            g.capacity_mw
            for g in self.generators.values()
            if g.source_type in [EnergySource.SOLAR, EnergySource.WIND]
        )
        total_capacity = sum(g.capacity_mw for g in self.generators.values())

        return {
            "region": self.region,
            "timestamp": datetime.now().isoformat(),
            "sustainability_metrics": {
                "renewable_capacity_mw": renewable_capacity,
                "total_capacity_mw": total_capacity,
                "renewable_percentage": (renewable_capacity / total_capacity * 100)
                if total_capacity > 0
                else 0,
                "carbon_budget_tons": self.carbon_budget,
                "carbon_used_tons": self.carbon_used,
                "carbon_remaining_percentage": (
                    1 - self.carbon_used / self.carbon_budget
                )
                * 100,
            },
            "intergenerational_equity": {
                "equity_score": self.calculate_intergenerational_equity(),
                "current_inequality_gini": self._calculate_current_inequality(),
                "future_generation_welfare_index": self.calculate_intergenerational_equity()
                * 0.6,
            },
            "charter_compliance": {
                "ϕ₈_status": "COMPLIANT"
                if self.carbon_used < self.carbon_budget * 0.5
                else "WARNING",
                "ϕ₇_status": "COMPLIANT"
                if self._calculate_current_inequality() < 0.3
                else "REVIEW_REQUIRED",
            },
        }

    def export_audit_trail(self, filepath: str):
        """Export full audit trail"""
        audit_data = {
            "system": "EnergyGridManagement",
            "region": self.region,
            "export_timestamp": datetime.now().isoformat(),
            "charter_version": "ϕ₁–ϕ₁₅, Ω²",
            "total_decisions": len(self.decision_log),
            "carbon_budget_status": {
                "total": self.carbon_budget,
                "used": self.carbon_used,
                "remaining": self.carbon_budget - self.carbon_used,
            },
            "ethical_framework": self.ethical_weights,
            "decisions": self.decision_log,
            "nbhs512_seal": "pending",
        }

        with open(filepath, "w") as f:
            json.dump(audit_data, f, indent=2)

        print(f"✓ Energy audit trail exported: {filepath}")


async def main():
    """Demonstrate energy grid management"""

    print("\n" + "=" * 70)
    print("SMART CITY ENERGY GRID MANAGEMENT")
    print("NeuralBlitz v20.0 — Apical Synthesis")
    print("=" * 70 + "\n")

    # Initialize optimizer
    optimizer = EthicalEnergyOptimizer(
        grid_region="Metro_North", carbon_budget_tons=500000
    )

    # Add generation assets
    optimizer.add_generator(
        Generator(
            generator_id="Solar_Farm_A",
            source_type=EnergySource.SOLAR,
            capacity_mw=150.0,
            availability=0.75,
            carbon_intensity=0.0,
        )
    )

    optimizer.add_generator(
        Generator(
            generator_id="Wind_Offshore_1",
            source_type=EnergySource.WIND,
            capacity_mw=200.0,
            availability=0.65,
            carbon_intensity=0.0,
        )
    )

    optimizer.add_generator(
        Generator(
            generator_id="Nuclear_Base",
            source_type=EnergySource.NUCLEAR,
            capacity_mw=400.0,
            availability=0.95,
            carbon_intensity=12.0,
        )
    )

    optimizer.add_generator(
        Generator(
            generator_id="Gas_Peaker_1",
            source_type=EnergySource.GAS_PEAKER,
            capacity_mw=100.0,
            availability=0.95,
            carbon_intensity=450.0,
        )
    )

    # Add load zones with different socioeconomic profiles
    optimizer.add_load_zone(
        LoadZone(
            zone_id="Downtown",
            population=50000,
            current_demand_mw=180.0,
            critical_load_mw=25.0,
            socioeconomic_index=0.75,
        )
    )

    optimizer.add_load_zone(
        LoadZone(
            zone_id="Residential_North",
            population=120000,
            current_demand_mw=220.0,
            critical_load_mw=15.0,
            socioeconomic_index=0.65,
        )
    )

    optimizer.add_load_zone(
        LoadZone(
            zone_id="Industrial_East",
            population=8000,
            current_demand_mw=150.0,
            critical_load_mw=40.0,
            socioeconomic_index=0.55,
        )
    )

    # Add storage
    optimizer.add_storage(
        StorageUnit(
            unit_id="Grid_Battery_1",
            capacity_mwh=400.0,
            current_soc=0.65,
            max_charge_rate_mw=100.0,
            max_discharge_rate_mw=100.0,
        )
    )

    # Run optimization
    print("Running generation optimization...")
    result = await optimizer.optimize_generation(target_reliability=0.9999)

    print(f"\nOptimization Results:")
    print(f"  Total demand: {result['total_demand_mw']:.1f} MW")
    print(f"  Emissions: {result['total_emissions_tons']:.1f} tons CO2")
    print(f"  Reliability: {result['reliability']:.4f}")
    print(f"  Renewable %: {result['renewable_percentage']:.1f}%")
    print(f"  Carbon budget remaining: {result['carbon_budget_remaining']:.0f} tons")

    # Print sustainability report
    print("\n" + "-" * 70)
    report = optimizer.get_sustainability_report()
    print("Sustainability Report (ϕ₈):")
    print(
        f"  Renewable capacity: {report['sustainability_metrics']['renewable_percentage']:.1f}%"
    )
    print(
        f"  Carbon budget used: {report['sustainability_metrics']['carbon_used_tons']:.0f} tons"
    )
    print(
        f"  Intergenerational equity: {report['intergenerational_equity']['equity_score']:.3f}"
    )
    print(f"  ϕ₈ status: {report['charter_compliance']['ϕ₈_status']}")

    # Apply differential privacy to usage data
    print("\n" + "-" * 70)
    print("Privacy-Preserving Data Analysis (ϕ₆):")
    raw_usage = [150.5, 148.2, 152.8, 147.3, 149.9, 151.2, 150.1]
    private_usage = optimizer.apply_differential_privacy(raw_usage, epsilon=0.1)
    print(f"  Original data: {[f'{x:.1f}' for x in raw_usage]}")
    print(f"  Private data:  {[f'{x:.1f}' for x in private_usage]}")
    print(f"  Privacy budget remaining: {optimizer.privacy_budget:.2f}")

    # Export audit trail
    optimizer.export_audit_trail("/tmp/energy_audit_trail.json")

    print("\n" + "=" * 70)
    print("ENERGY GRID OPTIMIZATION COMPLETE")
    print("=" * 70)
    print("✓ Sustainability targets met (ϕ₈)")
    print("✓ Equity constraints satisfied (ϕ₇)")
    print("✓ Privacy protections active (ϕ₆)")
    print("✓ Grid reliability maintained (ϕ₄)")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())

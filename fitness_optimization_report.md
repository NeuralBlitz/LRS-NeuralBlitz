# Fitness Function Optimization Techniques: Technical Report

**Report ID:** OPT-TECH-2024-001  
**Classification:** Technical Reference  
**Date:** 2024

---

## Executive Summary

This report presents three advanced fitness function optimization techniques with complete mathematical formalizations and reference implementations. Each technique addresses distinct challenges in evolutionary computation and optimization theory.

---

## 1. Multi-Objective Optimization (MOO)

### 1.1 Mathematical Model

**Problem Formulation:**
Given a decision vector **x** ∈ ℝⁿ, optimize k objective functions simultaneously:

$$\min_{\mathbf{x} \in \mathcal{X}} \mathbf{F}(\mathbf{x}) = [f_1(\mathbf{x}), f_2(\mathbf{x}), ..., f_k(\mathbf{x})]^T$$

subject to:
- **g**ᵢ(**x**) ≤ 0,  i = 1,...,m  (inequality constraints)
- **h**ⱼ(**x**) = 0,  j = 1,...,p  (equality constraints)

**Pareto Dominance:**
A solution **x**₁ dominates **x**₂ (denoted **x**₁ ≺ **x**₂) iff:

$$\forall i \in \{1,...,k\}: f_i(\mathbf{x}_1) \leq f_i(\mathbf{x}_2) \quad \land \quad \exists j: f_j(\mathbf{x}_1) < f_j(\mathbf{x}_2)$$

**Hypervolume Indicator:**
The quality of a Pareto front approximation P is measured by:

$$HV(P, \mathbf{r}) = \Lambda\left(\bigcup_{\mathbf{x} \in P} [\mathbf{f}(\mathbf{x}), \mathbf{r}]\right)$$

where **r** is a reference point and Λ denotes the Lebesgue measure.

**Weighted Sum Scalarization:**
For convex problems, convert to single objective:

$$f_{ws}(\mathbf{x}, \mathbf{w}) = \sum_{i=1}^{k} w_i f_i(\mathbf{x})$$

where **w** ∈ ℝᵏ, wᵢ ≥ 0, Σwᵢ = 1.

### 1.2 Python Implementation

```python
"""
Multi-Objective Optimization Framework
Implements NSGA-II algorithm with Pareto dominance and crowding distance
"""

import numpy as np
import random
from typing import List, Callable, Tuple, Optional
from dataclasses import dataclass
from abc import ABC, abstractmethod


@dataclass
class Individual:
    """Represents a solution in the population"""
    genome: np.ndarray
    objectives: np.ndarray = None
    rank: int = 0
    crowding_distance: float = 0.0
    dominated_count: int = 0
    dominated_set: List['Individual'] = None
    
    def __post_init__(self):
        if self.dominated_set is None:
            self.dominated_set = []
    
    def dominates(self, other: 'Individual') -> bool:
        """Check if this solution Pareto dominates another"""
        if self.objectives is None or other.objectives is None:
            raise ValueError("Objectives must be evaluated before dominance check")
        
        better_in_all = np.all(self.objectives <= other.objectives)
        better_in_one = np.any(self.objectives < other.objectives)
        return better_in_all and better_in_one


class MultiObjectiveProblem(ABC):
    """Abstract base class for multi-objective problems"""
    
    @abstractmethod
    def evaluate(self, x: np.ndarray) -> np.ndarray:
        """Return vector of objective values"""
        pass
    
    @property
    @abstractmethod
    def n_objectives(self) -> int:
        pass
    
    @property
    @abstractmethod
    def bounds(self) -> Tuple[np.ndarray, np.ndarray]:
        """Return (lower_bounds, upper_bounds)"""
        pass


class ZDT1Problem(MultiObjectiveProblem):
    """ZDT1 test problem - convex Pareto front"""
    
    def __init__(self, n_variables: int = 30):
        self.n_variables = n_variables
        
    def evaluate(self, x: np.ndarray) -> np.ndarray:
        f1 = x[0]
        g = 1 + 9 * np.sum(x[1:]) / (self.n_variables - 1)
        h = 1 - np.sqrt(f1 / g)
        f2 = g * h
        return np.array([f1, f2])
    
    @property
    def n_objectives(self) -> int:
        return 2
    
    @property
    def bounds(self) -> Tuple[np.ndarray, np.ndarray]:
        lower = np.zeros(self.n_variables)
        upper = np.ones(self.n_variables)
        return lower, upper


class NSGA2:
    """Non-dominated Sorting Genetic Algorithm II"""
    
    def __init__(
        self,
        problem: MultiObjectiveProblem,
        population_size: int = 100,
        max_generations: int = 250,
        crossover_rate: float = 0.9,
        mutation_rate: float = 0.1,
        tournament_size: int = 2
    ):
        self.problem = problem
        self.pop_size = population_size
        self.max_gen = max_generations
        self.cx_rate = crossover_rate
        self.mut_rate = mutation_rate
        self.tournament_size = tournament_size
        self.lower_bounds, self.upper_bounds = problem.bounds
        self.n_variables = len(self.lower_bounds)
        
    def initialize_population(self) -> List[Individual]:
        """Create random initial population"""
        population = []
        for _ in range(self.pop_size):
            genome = np.random.uniform(
                self.lower_bounds, 
                self.upper_bounds
            )
            individual = Individual(genome=genome)
            individual.objectives = self.problem.evaluate(genome)
            population.append(individual)
        return population
    
    def non_dominated_sort(self, population: List[Individual]) -> List[List[Individual]]:
        """Perform non-dominated sorting and assign ranks"""
        fronts = [[]]
        
        # Reset dominance information
        for p in population:
            p.dominated_count = 0
            p.dominated_set = []
            p.rank = 0
        
        # Determine domination relationships
        for i, p in enumerate(population):
            for j, q in enumerate(population):
                if i != j:
                    if p.dominates(q):
                        p.dominated_set.append(q)
                    elif q.dominates(p):
                        p.dominated_count += 1
            
            if p.dominated_count == 0:
                p.rank = 0
                fronts[0].append(p)
        
        # Generate subsequent fronts
        i = 0
        while len(fronts[i]) > 0:
            next_front = []
            for p in fronts[i]:
                for q in p.dominated_set:
                    q.dominated_count -= 1
                    if q.dominated_count == 0:
                        q.rank = i + 1
                        next_front.append(q)
            i += 1
            fronts.append(next_front)
        
        return fronts[:-1]  # Remove empty last front
    
    def calculate_crowding_distance(self, front: List[Individual]):
        """Calculate crowding distance for diversity preservation"""
        if len(front) <= 2:
            for individual in front:
                individual.crowding_distance = float('inf')
            return
        
        num_objectives = self.problem.n_objectives
        
        for individual in front:
            individual.crowding_distance = 0
        
        for m in range(num_objectives):
            # Sort by objective m
            front.sort(key=lambda x: x.objectives[m])
            
            # Boundary points have infinite distance
            front[0].crowding_distance = float('inf')
            front[-1].crowding_distance = float('inf')
            
            # Calculate distances for intermediate points
            f_min = front[0].objectives[m]
            f_max = front[-1].objectives[m]
            
            if f_max - f_min > 1e-10:
                for i in range(1, len(front) - 1):
                    distance = (front[i + 1].objectives[m] - 
                               front[i - 1].objectives[m]) / (f_max - f_min)
                    front[i].crowding_distance += distance
    
    def tournament_selection(
        self, 
        population: List[Individual]
    ) -> Individual:
        """Binary tournament selection based on rank and crowding distance"""
        selected = random.sample(population, self.tournament_size)
        
        # Sort by rank (ascending), then by crowding distance (descending)
        selected.sort(key=lambda x: (x.rank, -x.crowding_distance))
        return selected[0]
    
    def simulated_binary_crossover(
        self, 
        parent1: Individual, 
        parent2: Individual,
        eta: float = 15.0
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Simulated Binary Crossover (SBX)"""
        if random.random() > self.cx_rate:
            return parent1.genome.copy(), parent2.genome.copy()
        
        child1 = np.zeros(self.n_variables)
        child2 = np.zeros(self.n_variables)
        
        for i in range(self.n_variables):
            if random.random() <= 0.5:
                if abs(parent1.genome[i] - parent2.genome[i]) > 1e-14:
                    if parent1.genome[i] < parent2.genome[i]:
                        y1, y2 = parent1.genome[i], parent2.genome[i]
                    else:
                        y1, y2 = parent2.genome[i], parent1.genome[i]
                    
                    beta = 1.0 + (2.0 * (y1 - self.lower_bounds[i]) / (y2 - y1))
                    alpha = 2.0 - beta ** -(eta + 1.0)
                    
                    rand = random.random()
                    if rand <= 1.0 / alpha:
                        beta_q = (rand * alpha) ** (1.0 / (eta + 1.0))
                    else:
                        beta_q = (1.0 / (2.0 - rand * alpha)) ** (1.0 / (eta + 1.0))
                    
                    c1 = 0.5 * ((y1 + y2) - beta_q * (y2 - y1))
                    
                    beta = 1.0 + (2.0 * (self.upper_bounds[i] - y2) / (y2 - y1))
                    alpha = 2.0 - beta ** -(eta + 1.0)
                    
                    if rand <= 1.0 / alpha:
                        beta_q = (rand * alpha) ** (1.0 / (eta + 1.0))
                    else:
                        beta_q = (1.0 / (2.0 - rand * alpha)) ** (1.0 / (eta + 1.0))
                    
                    c2 = 0.5 * ((y1 + y2) + beta_q * (y2 - y1))
                    
                    c1 = np.clip(c1, self.lower_bounds[i], self.upper_bounds[i])
                    c2 = np.clip(c2, self.lower_bounds[i], self.upper_bounds[i])
                    
                    if random.random() <= 0.5:
                        child1[i] = c2
                        child2[i] = c1
                    else:
                        child1[i] = c1
                        child2[i] = c2
                else:
                    child1[i] = parent1.genome[i]
                    child2[i] = parent2.genome[i]
            else:
                child1[i] = parent1.genome[i]
                child2[i] = parent2.genome[i]
        
        return child1, child2
    
    def polynomial_mutation(
        self, 
        genome: np.ndarray,
        eta: float = 20.0
    ) -> np.ndarray:
        """Polynomial mutation operator"""
        if random.random() > self.mut_rate:
            return genome
        
        mutant = genome.copy()
        
        for i in range(self.n_variables):
            if random.random() <= 1.0 / self.n_variables:
                y = mutant[i]
                yl, yu = self.lower_bounds[i], self.upper_bounds[i]
                
                if yl == yu:
                    continue
                
                delta1 = (y - yl) / (yu - yl)
                delta2 = (yu - y) / (yu - yl)
                
                rand = random.random()
                mut_pow = 1.0 / (eta + 1.0)
                
                if rand <= 0.5:
                    xy = 1.0 - delta1
                    val = 2.0 * rand + (1.0 - 2.0 * rand) * (xy ** (eta + 1.0))
                    delta_q = val ** mut_pow - 1.0
                else:
                    xy = 1.0 - delta2
                    val = 2.0 * (1.0 - rand) + 2.0 * (rand - 0.5) * (xy ** (eta + 1.0))
                    delta_q = 1.0 - val ** mut_pow
                
                y = y + delta_q * (yu - yl)
                mutant[i] = np.clip(y, yl, yu)
        
        return mutant
    
    def create_offspring(
        self, 
        population: List[Individual]
    ) -> List[Individual]:
        """Generate offspring population"""
        offspring = []
        
        while len(offspring) < self.pop_size:
            parent1 = self.tournament_selection(population)
            parent2 = self.tournament_selection(population)
            
            child1_genome, child2_genome = self.simulated_binary_crossover(
                parent1, parent2
            )
            
            child1_genome = self.polynomial_mutation(child1_genome)
            child2_genome = self.polynomial_mutation(child2_genome)
            
            child1 = Individual(
                genome=child1_genome,
                objectives=self.problem.evaluate(child1_genome)
            )
            child2 = Individual(
                genome=child2_genome,
                objectives=self.problem.evaluate(child2_genome)
            )
            
            offspring.extend([child1, child2])
        
        return offspring[:self.pop_size]
    
    def environmental_selection(
        self, 
        combined: List[Individual]
    ) -> List[Individual]:
        """Select next generation using non-dominated sorting and crowding distance"""
        fronts = self.non_dominated_sort(combined)
        
        new_population = []
        front_idx = 0
        
        # Add complete fronts
        while (len(new_population) + len(fronts[front_idx]) <= self.pop_size 
               and front_idx < len(fronts)):
            self.calculate_crowding_distance(fronts[front_idx])
            new_population.extend(fronts[front_idx])
            front_idx += 1
        
        # Fill remaining slots from next front using crowding distance
        if len(new_population) < self.pop_size and front_idx < len(fronts):
            self.calculate_crowding_distance(fronts[front_idx])
            fronts[front_idx].sort(key=lambda x: -x.crowding_distance)
            remaining = self.pop_size - len(new_population)
            new_population.extend(fronts[front_idx][:remaining])
        
        return new_population
    
    def calculate_hypervolume(
        self, 
        population: List[Individual],
        reference_point: np.ndarray
    ) -> float:
        """Calculate hypervolume indicator (2D only)"""
        if self.problem.n_objectives != 2:
            raise NotImplementedError("Hypervolume only implemented for 2D")
        
        points = np.array([ind.objectives for ind in population])
        
        # Sort by first objective
        sorted_indices = np.argsort(points[:, 0])
        points = points[sorted_indices]
        
        volume = 0.0
        for i in range(len(points)):
            if i == len(points) - 1:
                width = reference_point[0] - points[i, 0]
            else:
                width = points[i + 1, 0] - points[i, 0]
            
            height = reference_point[1] - points[i, 1]
            volume += width * height
        
        return volume
    
    def optimize(self) -> Tuple[List[Individual], List[float]]:
        """Run NSGA-II optimization"""
        population = self.initialize_population()
        hypervolume_history = []
        
        reference_point = np.array([1.5, 1.5])  # For ZDT1
        
        for generation in range(self.max_gen):
            # Create offspring
            offspring = self.create_offspring(population)
            
            # Combine and select
            combined = population + offspring
            population = self.environmental_selection(combined)
            
            # Track metrics
            if generation % 10 == 0:
                hv = self.calculate_hypervolume(population, reference_point)
                hypervolume_history.append(hv)
                print(f"Generation {generation}: Hypervolume = {hv:.4f}")
        
        return population, hypervolume_history


# Example usage
if __name__ == "__main__":
    problem = ZDT1Problem(n_variables=30)
    nsga2 = NSGA2(
        problem=problem,
        population_size=100,
        max_generations=250
    )
    
    final_population, hv_history = nsga2.optimize()
    
    print(f"\nFinal Pareto front size: {len(final_population)}")
    print(f"Final hypervolume: {hv_history[-1]:.4f}")
```

### 1.3 Performance Characteristics

| Metric | Value |
|--------|-------|
| Time Complexity | O(MN²) per generation |
| Space Complexity | O(N²) |
| Convergence | Guaranteed for convex fronts |
| Diversity | Maintained via crowding distance |

---

## 2. Dynamic Fitness Landscapes

### 2.1 Mathematical Model

**Dynamic Optimization Problem:**

$$\max_{\mathbf{x} \in \mathcal{X}} f(\mathbf{x}, t)$$

where t represents time/generation, and the fitness landscape changes over time.

**Change Dynamics Models:**

1. **Linear Translation:**
   $$f(\mathbf{x}, t) = f_0(\mathbf{x} - \mathbf{v}t)$$
   where **v** is the velocity vector of the optimum.

2. **Oscillatory Movement:**
   $$f(\mathbf{x}, t) = f_0(\mathbf{x} - \mathbf{A}\sin(\omega t + \phi))$$
   where **A** is amplitude, ω is frequency, φ is phase.

3. **Random Walk:**
   $$\mathbf{x}^*_{t+1} = \mathbf{x}^*_t + \mathcal{N}(0, \sigma^2)$$

**Severity Metrics:**

**Change Severity:**
$$S_t = \|\mathbf{x}^*_{t+1} - \mathbf{x}^*_t\|$$

**Change Frequency:**
$$F = \frac{1}{\tau}$$
where τ is the number of generations between changes.

**Fitness Correlation:**
$$\rho_t = \frac{\text{Cov}(f_t, f_{t+1})}{\sigma_{f_t} \sigma_{f_{t+1}}}$$

**Multi-population Model:**
For m subpopulations tracking different optima:

$$P(t) = \{P_1(t), P_2(t), ..., P_m(t)\}$$

Each subpopulation evolves with:
$$\dot{P}_i(t) = G(P_i(t), f_i(\mathbf{x}, t))$$

### 2.2 Python Implementation

```python
"""
Dynamic Fitness Landscape Optimization
Implements multi-population approach with memory and diversity maintenance
"""

import numpy as np
import random
from typing import List, Tuple, Callable, Optional
from dataclasses import dataclass, field
from collections import deque
from enum import Enum


class ChangeType(Enum):
    """Types of environmental changes"""
    LINEAR = "linear"
    OSCILLATORY = "oscillatory"
    RANDOM = "random"
    CYCLIC = "cyclic"


@dataclass
class FitnessPeak:
    """Represents a tracked peak in the dynamic landscape"""
    position: np.ndarray
    height: float
    velocity: np.ndarray
    age: int = 0
    reliability: float = 1.0


class DynamicFitnessLandscape:
    """Base class for dynamic fitness functions"""
    
    def __init__(
        self,
        n_dimensions: int,
        change_type: ChangeType,
        change_frequency: int = 10,
        change_severity: float = 1.0
    ):
        self.n_dim = n_dimensions
        self.change_type = change_type
        self.change_freq = change_frequency
        self.change_sev = change_severity
        self.generation = 0
        self.optimum_position = np.random.uniform(-5, 5, n_dimensions)
        self.base_optimum = self.optimum_position.copy()
        
    def update_environment(self):
        """Update the fitness landscape"""
        self.generation += 1
        
        if self.generation % self.change_freq == 0:
            if self.change_type == ChangeType.LINEAR:
                # Linear translation
                velocity = np.ones(self.n_dim) * self.change_sev * 0.1
                self.optimum_position += velocity
                
            elif self.change_type == ChangeType.OSCILLATORY:
                # Sinusoidal movement
                t = self.generation / self.change_freq
                amplitude = self.change_sev * 2
                displacement = amplitude * np.sin(2 * np.pi * t / 10)
                self.optimum_position = self.base_optimum + displacement
                
            elif self.change_type == ChangeType.RANDOM:
                # Random walk
                step = np.random.normal(0, self.change_sev, self.n_dim)
                self.optimum_position += step
                
            elif self.change_type == ChangeType.CYCLIC:
                # Cyclic movement in hypersphere
                angle = 2 * np.pi * (self.generation / (self.change_freq * 10))
                radius = self.change_sev * 3
                self.optimum_position = self.base_optimum + radius * np.array([
                    np.cos(angle),
                    np.sin(angle)
                ])
            
            # Keep within bounds
            self.optimum_position = np.clip(
                self.optimum_position, -10, 10
            )
    
    def evaluate(self, x: np.ndarray) -> float:
        """Evaluate fitness (to be overridden)"""
        raise NotImplementedError


class MovingPeakFunction(DynamicFitnessLandscape):
    """Moving Peaks Benchmark Function"""
    
    def __init__(
        self,
        n_dimensions: int = 2,
        n_peaks: int = 5,
        change_type: ChangeType = ChangeType.RANDOM,
        change_frequency: int = 10,
        change_severity: float = 1.0,
        peak_height_range: Tuple[float, float] = (30, 70),
        peak_width_range: Tuple[float, float] = (0.5, 2.0)
    ):
        super().__init__(
            n_dimensions, change_type, change_frequency, change_severity
        )
        self.n_peaks = n_peaks
        
        # Initialize peaks
        self.peak_positions = [
            np.random.uniform(-5, 5, n_dimensions) 
            for _ in range(n_peaks)
        ]
        self.peak_heights = np.random.uniform(*peak_height_range, n_peaks)
        self.peak_widths = np.random.uniform(*peak_width_range, n_peaks)
        self.peak_velocities = [
            np.random.uniform(-0.5, 0.5, n_dimensions) 
            for _ in range(n_peaks)
        ]
        
    def update_environment(self):
        """Update all peaks"""
        super().update_environment()
        
        if self.generation % self.change_freq == 0:
            for i in range(self.n_peaks):
                # Update peak position
                self.peak_positions[i] += self.peak_velocities[i] * self.change_sev
                
                # Change velocity slightly
                self.peak_velocities[i] += np.random.normal(0, 0.1, self.n_dim)
                self.peak_velocities[i] = np.clip(self.peak_velocities[i], -1, 1)
                
                # Keep within bounds
                self.peak_positions[i] = np.clip(
                    self.peak_positions[i], -10, 10
                )
    
    def evaluate(self, x: np.ndarray) -> float:
        """Evaluate using the highest peak"""
        max_fitness = float('-inf')
        
        for i in range(self.n_peaks):
            distance = np.linalg.norm(x - self.peak_positions[i])
            fitness = self.peak_heights[i] / (1 + self.peak_widths[i] * distance**2)
            max_fitness = max(max_fitness, fitness)
        
        return max_fitness


class DynamicSphereFunction(DynamicFitnessLandscape):
    """Moving Sphere benchmark"""
    
    def __init__(
        self,
        n_dimensions: int = 10,
        change_type: ChangeType = ChangeType.RINEAR,
        change_frequency: int = 10,
        change_severity: float = 1.0
    ):
        super().__init__(
            n_dimensions, change_type, change_frequency, change_severity
        )
        
    def evaluate(self, x: np.ndarray) -> float:
        """Negative squared distance to moving optimum"""
        distance = np.linalg.norm(x - self.optimum_position)
        return -distance**2


class MemoryEnhancedIndividual:
    """Individual with episodic memory for dynamic environments"""
    
    def __init__(self, genome: np.ndarray, memory_size: int = 5):
        self.genome = genome
        self.fitness = None
        self.memory = deque(maxlen=memory_size)  # (position, fitness, time)
        self.age = 0
        
    def store_experience(self, environment_hash: str):
        """Store current solution in memory"""
        if self.fitness is not None:
            self.memory.append({
                'position': self.genome.copy(),
                'fitness': self.fitness,
                'environment': environment_hash,
                'age': self.age
            })
    
    def recall_best(self, current_env_hash: str) -> Optional[np.ndarray]:
        """Recall best solution from similar past environments"""
        if not self.memory:
            return None
        
        # Return best remembered solution
        best_memory = max(self.memory, key=lambda x: x['fitness'])
        return best_memory['position'].copy()


class MultiPopulationDynamicOptimizer:
    """Multi-population optimizer for dynamic fitness landscapes"""
    
    def __init__(
        self,
        landscape: DynamicFitnessLandscape,
        n_populations: int = 3,
        population_size: int = 50,
        memory_size: int = 5,
        diversity_threshold: float = 0.1,
        mutation_rate: float = 0.1,
        crossover_rate: float = 0.8
    ):
        self.landscape = landscape
        self.n_pops = n_populations
        self.pop_size = population_size
        self.memory_size = memory_size
        self.diversity_thresh = diversity_threshold
        self.mut_rate = mutation_rate
        self.cx_rate = crossover_rate
        
        self.n_dim = landscape.n_dim
        self.populations = []
        self.peak_trackers = [None] * n_populations
        self.best_solutions = []
        self.fitness_history = []
        
    def initialize(self):
        """Initialize multiple populations"""
        self.populations = []
        for _ in range(self.n_pops):
            pop = []
            for _ in range(self.pop_size):
                genome = np.random.uniform(-10, 10, self.n_dim)
                individual = MemoryEnhancedIndividual(genome, self.memory_size)
                individual.fitness = self.landscape.evaluate(genome)
                pop.append(individual)
            self.populations.append(pop)
    
    def tournament_selection(
        self, 
        population: List[MemoryEnhancedIndividual],
        tournament_size: int = 3
    ) -> MemoryEnhancedIndividual:
        """Select best from tournament"""
        tournament = random.sample(population, tournament_size)
        return max(tournament, key=lambda x: x.fitness)
    
    def crossover(
        self, 
        parent1: MemoryEnhancedIndividual,
        parent2: MemoryEnhancedIndividual
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Uniform crossover"""
        if random.random() > self.cx_rate:
            return parent1.genome.copy(), parent2.genome.copy()
        
        mask = np.random.random(self.n_dim) < 0.5
        child1 = np.where(mask, parent1.genome, parent2.genome)
        child2 = np.where(mask, parent2.genome, parent1.genome)
        
        return child1, child2
    
    def mutate(self, genome: np.ndarray) -> np.ndarray:
        """Gaussian mutation"""
        if random.random() < self.mut_rate:
            noise = np.random.normal(0, 1, self.n_dim)
            genome = genome + noise
        return np.clip(genome, -10, 10)
    
    def calculate_diversity(
        self, 
        population: List[MemoryEnhancedIndividual]
    ) -> float:
        """Calculate population diversity (average pairwise distance)"""
        if len(population) < 2:
            return 0.0
        
        genomes = np.array([ind.genome for ind in population])
        centroid = np.mean(genomes, axis=0)
        diversity = np.mean(np.linalg.norm(genomes - centroid, axis=1))
        return diversity
    
    def reinitialize_population(
        self, 
        population: List[MemoryEnhancedIndividual],
        severity: float = 0.3
    ):
        """Partially reinitialize population to maintain diversity"""
        n_to_replace = int(len(population) * severity)
        
        for i in range(n_to_replace):
            # Try to use memory-based solution
            recalled = population[i].recall_best(str(self.landscape.generation))
            if recalled is not None and random.random() < 0.5:
                population[i].genome = recalled
            else:
                population[i].genome = np.random.uniform(-10, 10, self.n_dim)
            
            population[i].fitness = self.landscape.evaluate(population[i].genome)
            population[i].age = 0
    
    def migrate_between_populations(self, migration_rate: float = 0.1):
        """Exchange individuals between populations"""
        n_migrants = int(self.pop_size * migration_rate)
        
        for i in range(self.n_pops):
            next_pop = (i + 1) % self.n_pops
            
            # Select best from current, replace worst in next
            sorted_current = sorted(
                self.populations[i], 
                key=lambda x: x.fitness, 
                reverse=True
            )
            sorted_next = sorted(
                self.populations[next_pop], 
                key=lambda x: x.fitness
            )
            
            for j in range(n_migrants):
                if j < len(sorted_current) and j < len(sorted_next):
                    sorted_next[j].genome = sorted_current[j].genome.copy()
                    sorted_next[j].fitness = sorted_current[j].fitness
                    sorted_next[j].age = 0
    
    def evolve_generation(self):
        """Evolve all populations for one generation"""
        self.landscape.update_environment()
        env_hash = str(self.landscape.generation)
        
        new_populations = []
        
        for pop_idx, population in enumerate(self.populations):
            new_pop = []
            
            # Save experiences to memory before change
            for ind in population:
                ind.store_experience(env_hash)
                ind.age += 1
            
            # Generate offspring
            while len(new_pop) < self.pop_size:
                parent1 = self.tournament_selection(population)
                parent2 = self.tournament_selection(population)
                
                child1_genome, child2_genome = self.crossover(parent1, parent2)
                
                child1_genome = self.mutate(child1_genome)
                child2_genome = self.mutate(child2_genome)
                
                child1 = MemoryEnhancedIndividual(child1_genome, self.memory_size)
                child1.fitness = self.landscape.evaluate(child1_genome)
                
                child2 = MemoryEnhancedIndividual(child2_genome, self.memory_size)
                child2.fitness = self.landscape.evaluate(child2_genome)
                
                new_pop.extend([child1, child2])
            
            new_pop = new_pop[:self.pop_size]
            
            # Check diversity and reinitialize if needed
            diversity = self.calculate_diversity(new_pop)
            if diversity < self.diversity_thresh:
                self.reinitialize_population(new_pop)
            
            new_populations.append(new_pop)
        
        self.populations = new_populations
        
        # Periodic migration
        if self.landscape.generation % 5 == 0:
            self.migrate_between_populations()
    
    def get_best_solution(self) -> Tuple[np.ndarray, float]:
        """Return global best across all populations"""
        all_individuals = []
        for pop in self.populations:
            all_individuals.extend(pop)
        
        if not all_individuals:
            return None, float('-inf')
        
        best = max(all_individuals, key=lambda x: x.fitness)
        return best.genome.copy(), best.fitness
    
    def optimize(self, max_generations: int = 200) -> dict:
        """Run optimization and return statistics"""
        self.initialize()
        
        best_fitness_history = []
        avg_diversity_history = []
        offline_error = []  # Distance from optimum after change
        
        for gen in range(max_generations):
            self.evolve_generation()
            
            best_genome, best_fitness = self.get_best_solution()
            best_fitness_history.append(best_fitness)
            
            # Track diversity
            total_diversity = sum(
                self.calculate_diversity(pop) 
                for pop in self.populations
            )
            avg_diversity = total_diversity / self.n_pops
            avg_diversity_history.append(avg_diversity)
            
            # Calculate offline error if environment changed
            if gen % self.landscape.change_freq == 0:
                if hasattr(self.landscape, 'optimum_position'):
                    error = np.linalg.norm(best_genome - self.landscape.optimum_position)
                    offline_error.append(error)
            
            if gen % 20 == 0:
                print(f"Gen {gen}: Best={best_fitness:.4f}, "
                      f"Diversity={avg_diversity:.4f}")
        
        return {
            'best_fitness_history': best_fitness_history,
            'diversity_history': avg_diversity_history,
            'offline_error': offline_error,
            'final_best': self.get_best_solution()
        }


# Example usage
if __name__ == "__main__":
    # Test with moving peaks
    landscape = MovingPeakFunction(
        n_dimensions=2,
        n_peaks=3,
        change_type=ChangeType.RANDOM,
        change_frequency=10,
        change_severity=1.5
    )
    
    optimizer = MultiPopulationDynamicOptimizer(
        landscape=landscape,
        n_populations=3,
        population_size=50,
        memory_size=5,
        diversity_threshold=0.5
    )
    
    results = optimizer.optimize(max_generations=200)
    
    print(f"\nFinal best fitness: {results['final_best'][1]:.4f}")
    print(f"Average offline error: {np.mean(results['offline_error']):.4f}")
```

### 2.3 Performance Metrics

| Metric | Description |
|--------|-------------|
| Offline Error | Average distance from optimum after each change |
| Best-before-change | Best fitness just before environment changes |
| Recovery Rate | Generations needed to regain previous performance |
| Diversity Maintenance | Population spread over time |

---

## 3. Co-evolutionary Fitness

### 3.1 Mathematical Model

**Co-evolutionary System:**
Given n species with populations P₁, P₂, ..., Pₙ, the fitness of individual xᵢ in species i depends on interactions with other species:

$$f_i(\mathbf{x}_i | \mathbf{P}_{-i}) = g(\mathbf{x}_i, \mathbf{P}_{-i})$$

where **P**₋ᵢ denotes all populations except species i.

**Competitive Co-evolution (Zero-sum):**
$$f_i(\mathbf{x}_i, \mathbf{x}_j) = -f_j(\mathbf{x}_j, \mathbf{x}_i)$$

**Cooperative Co-evolution:**
$$f_i(\mathbf{x}_i | \mathbf{P}_{-i}) = h(\text{team\_performance}(\mathbf{x}_i, \text{partners}))$$

**Nash Equilibrium Condition:**
A strategy profile **s*** = (s*₁, s*₂, ..., s*ₙ) is a Nash equilibrium if:

$$\forall i: f_i(s^*_i, \mathbf{s}^*_{-i}) \geq f_i(s_i, \mathbf{s}^*_{-i}) \quad \forall s_i \in S_i$$

**Elo Rating System for Relative Fitness:**
$$E_A = \frac{1}{1 + 10^{(R_B - R_A)/400}}$$

Expected score and rating update:
$$R'_A = R_A + K(S_A - E_A)$$

**Host-Parasite Model:**
Host fitness:  
$$f_H(\mathbf{h}, \mathbf{p}) = \alpha - \beta \cdot d(\mathbf{h}, \mathbf{p})$$

Parasite fitness:
$$f_P(\mathbf{p}, \mathbf{h}) = \gamma - \delta \cdot d(\mathbf{h}, \mathbf{p})$$

where d(·,·) is distance in genotype space.

**Arms Race Dynamics:**
$$\frac{d\mathbf{h}}{dt} = \eta_H \nabla_{\mathbf{h}} f_H(\mathbf{h}, \mathbf{p})$$
$$\frac{d\mathbf{p}}{dt} = \eta_P \nabla_{\mathbf{p}} f_P(\mathbf{p}, \mathbf{h})$$

**Red Queen Dynamics:**
Relative fitness change rate:
$$\frac{d}{dt}(f_H - f_P) = \text{constant}$$

### 3.2 Python Implementation

```python
"""
Co-evolutionary Fitness Optimization
Implements competitive and cooperative co-evolution
"""

import numpy as np
import random
from typing import List, Tuple, Dict, Callable, Optional
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import copy


class CoevolutionType(Enum):
    """Types of co-evolutionary relationships"""
    COMPETITIVE = "competitive"  # Zero-sum
    COOPERATIVE = "cooperative"  # Mutual benefit
    PREDATOR_PREY = "predator_prey"  # Arms race
    HOST_PARASITE = "host_parasite"  # Evolutionary pressure


@dataclass
class CoevIndividual:
    """Individual in co-evolutionary population"""
    genome: np.ndarray
    species_id: int
    fitness: float = 0.0
    elo_rating: float = 1500.0
    interactions: int = 0
    wins: int = 0
    losses: int = 0
    draws: int = 0
    
    def win_rate(self) -> float:
        if self.interactions == 0:
            return 0.0
        return self.wins / self.interactions
    
    def update_elo(self, opponent_rating: float, score: float, k: float = 32.0):
        """Update Elo rating based on match outcome"""
        expected = 1 / (1 + 10 ** ((opponent_rating - self.elo_rating) / 400))
        self.elo_rating += k * (score - expected)


class GameTheoryProblem:
    """Base class for game theory interactions"""
    
    def __init__(self, n_strategies: int = 2):
        self.n_strategies = n_strategies
        
    def play_match(
        self, 
        player1: CoevIndividual,
        player2: CoevIndividual
    ) -> Tuple[float, float]:
        """Return payoff for both players"""
        raise NotImplementedError


class PrisonersDilemma(GameTheoryProblem):
    """Classic Prisoner's Dilemma (T > R > P > S)"""
    
    def __init__(self, T: float = 5, R: float = 3, P: float = 1, S: float = 0):
        super().__init__(n_strategies=2)
        self.payoff_matrix = {
            (0, 0): (R, R),  # Both cooperate
            (0, 1): (S, T),  # P1 coop, P2 defect
            (1, 0): (T, S),  # P1 defect, P2 coop
            (1, 1): (P, P)   # Both defect
        }
        
    def play_match(
        self,
        player1: CoevIndividual,
        player2: CoevIndividual
    ) -> Tuple[float, float]:
        """Interpret genome as probability of cooperation"""
        # Genome[0] = probability of cooperation
        p1_coop = player1.genome[0] > 0.5
        p2_coop = player2.genome[0] > 0.5
        
        action1 = 0 if p1_coop else 1
        action2 = 0 if p2_coop else 1
        
        return self.payoff_matrix[(action1, action2)]


class NumberCompetition(GameTheoryProblem):
    """Competition to get closest to target (learned through co-evolution)"""
    
    def __init__(self, target_range: Tuple[float, float] = (0, 100)):
        super().__init__(n_strategies=1)
        self.target_range = target_range
        self.current_target = None
        
    def set_target(self, target: float):
        self.current_target = target
        
    def play_match(
        self,
        player1: CoevIndividual,
        player2: CoevIndividual
    ) -> Tuple[float, float]:
        """Player with number closer to target wins"""
        if self.current_target is None:
            self.current_target = random.uniform(*self.target_range)
        
        # Genomes encode the number
        num1 = np.clip(player1.genome[0], *self.target_range)
        num2 = np.clip(player2.genome[0], *self.target_range)
        
        dist1 = abs(num1 - self.current_target)
        dist2 = abs(num2 - self.current_target)
        
        if dist1 < dist2:
            return (1.0, 0.0)  # Player 1 wins
        elif dist2 < dist1:
            return (0.0, 1.0)  # Player 2 wins
        else:
            return (0.5, 0.5)  # Draw


class HostParasiteSystem:
    """Host-Parasite co-evolutionary system"""
    
    def __init__(
        self,
        n_dimensions: int = 10,
        host_pop_size: int = 100,
        parasite_pop_size: int = 100,
        infection_threshold: float = 2.0
    ):
        self.n_dim = n_dimensions
        self.host_size = host_pop_size
        self.parasite_size = parasite_pop_size
        self.threshold = infection_threshold
        
        self.hosts: List[CoevIndividual] = []
        self.parasites: List[CoevIndividual] = []
        
    def initialize(self):
        """Initialize host and parasite populations"""
        self.hosts = [
            CoevIndividual(
                genome=np.random.uniform(-5, 5, self.n_dim),
                species_id=0
            )
            for _ in range(self.host_size)
        ]
        
        self.parasites = [
            CoevIndividual(
                genome=np.random.uniform(-5, 5, self.n_dim),
                species_id=1
            )
            for _ in range(self.parasite_size)
        ]
    
    def evaluate_host(self, host: CoevIndividual) -> float:
        """Host fitness: higher is better, penalized by parasites"""
        # Host has ideal position (we'll say origin)
        base_fitness = -np.linalg.norm(host.genome)
        
        # Penalize for each nearby parasite
        parasite_penalty = 0
        for parasite in self.parasites:
            distance = np.linalg.norm(host.genome - parasite.genome)
            if distance < self.threshold:
                parasite_penalty += (self.threshold - distance)
        
        return base_fitness - 2.0 * parasite_penalty
    
    def evaluate_parasite(self, parasite: CoevIndividual) -> float:
        """Parasite fitness: higher when close to hosts"""
        total_fitness = 0
        for host in self.hosts:
            distance = np.linalg.norm(parasite.genome - host.genome)
            if distance < self.threshold:
                # Fitness inversely proportional to distance
                total_fitness += 1.0 / (1.0 + distance)
        return total_fitness
    
    def evaluate_populations(self):
        """Evaluate all individuals"""
        for host in self.hosts:
            host.fitness = self.evaluate_host(host)
        
        for parasite in self.parasites:
            parasite.fitness = self.evaluate_parasite(parasite)
    
    def tournament_selection(
        self,
        population: List[CoevIndividual],
        tournament_size: int = 3
    ) -> CoevIndividual:
        """Select based on fitness"""
        tournament = random.sample(population, tournament_size)
        return max(tournament, key=lambda x: x.fitness)
    
    def evolve_species(
        self,
        population: List[CoevIndividual],
        mutation_rate: float = 0.1,
        crossover_rate: float = 0.8
    ) -> List[CoevIndividual]:
        """Evolve one species"""
        new_pop = []
        
        while len(new_pop) < len(population):
            parent1 = self.tournament_selection(population)
            parent2 = self.tournament_selection(population)
            
            # Crossover
            if random.random() < crossover_rate:
                alpha = random.random()
                child1_genome = alpha * parent1.genome + (1 - alpha) * parent2.genome
                child2_genome = alpha * parent2.genome + (1 - alpha) * parent1.genome
            else:
                child1_genome = parent1.genome.copy()
                child2_genome = parent2.genome.copy()
            
            # Mutation
            if random.random() < mutation_rate:
                child1_genome += np.random.normal(0, 0.5, self.n_dim)
            if random.random() < mutation_rate:
                child2_genome += np.random.normal(0, 0.5, self.n_dim)
            
            child1 = CoevIndividual(
                genome=np.clip(child1_genome, -10, 10),
                species_id=population[0].species_id
            )
            child2 = CoevIndividual(
                genome=np.clip(child2_genome, -10, 10),
                species_id=population[0].species_id
            )
            
            new_pop.extend([child1, child2])
        
        return new_pop[:len(population)]
    
    def generation(self):
        """One generation of co-evolution"""
        self.evaluate_populations()
        
        self.hosts = self.evolve_species(self.hosts)
        self.parasites = self.evolve_species(self.parasites)
    
    def get_statistics(self) -> Dict:
        """Return co-evolution statistics"""
        host_fitnesses = [h.fitness for h in self.hosts]
        parasite_fitnesses = [p.fitness for p in self.parasites]
        
        return {
            'host_mean_fitness': np.mean(host_fitnesses),
            'host_std_fitness': np.std(host_fitnesses),
            'parasite_mean_fitness': np.mean(parasite_fitnesses),
            'parasite_std_fitness': np.std(parasite_fitnesses),
            'host_parasite_ratio': np.mean(host_fitnesses) / (np.mean(parasite_fitnesses) + 1e-10)
        }


class CompetitiveCoevolutionOptimizer:
    """Competitive co-evolution using Elo ratings"""
    
    def __init__(
        self,
        game: GameTheoryProblem,
        population_size: int = 100,
        n_generations: int = 200,
        matches_per_gen: int = 500
    ):
        self.game = game
        self.pop_size = population_size
        self.n_gen = n_generations
        self.matches_per_gen = matches_per_gen
        self.n_dim = 10  # Genome dimension
        
        self.population: List[CoevIndividual] = []
        
    def initialize(self):
        """Initialize population"""
        self.population = [
            CoevIndividual(
                genome=np.random.uniform(-1, 1, self.n_dim),
                species_id=0,
                elo_rating=1500.0
            )
            for _ in range(self.pop_size)
        ]
    
    def run_tournament(self):
        """Run round-robin matches and update Elo ratings"""
        for _ in range(self.matches_per_gen):
            # Select two random individuals
            idx1, idx2 = random.sample(range(self.pop_size), 2)
            player1 = self.population[idx1]
            player2 = self.population[idx2]
            
            # Play match
            payoff1, payoff2 = self.game.play_match(player1, player2)
            
            # Update stats
            player1.interactions += 1
            player2.interactions += 1
            
            # Determine outcome for Elo
            if payoff1 > payoff2:
                player1.wins += 1
                player2.losses += 1
                score1, score2 = 1.0, 0.0
            elif payoff2 > payoff1:
                player2.wins += 1
                player1.losses += 1
                score1, score2 = 0.0, 1.0
            else:
                player1.draws += 1
                player2.draws += 1
                score1 = score2 = 0.5
            
            # Update Elo ratings
            player1.update_elo(player2.elo_rating, score1)
            player2.update_elo(player1.elo_rating, score2)
            
            # Store fitness as Elo rating
            player1.fitness = player1.elo_rating
            player2.fitness = player2.elo_rating
    
    def evolve(self):
        """Evolve population based on Elo ratings"""
        new_pop = []
        
        # Sort by Elo rating
        sorted_pop = sorted(
            self.population, 
            key=lambda x: x.elo_rating, 
            reverse=True
        )
        
        # Elitism: keep top 10%
        n_elite = self.pop_size // 10
        new_pop.extend(sorted_pop[:n_elite])
        
        # Generate rest through tournament selection
        while len(new_pop) < self.pop_size:
            parent1 = random.choice(sorted_pop[:self.pop_size//2])
            parent2 = random.choice(sorted_pop[:self.pop_size//2])
            
            # Crossover
            alpha = random.random()
            child_genome = alpha * parent1.genome + (1 - alpha) * parent2.genome
            
            # Mutation
            if random.random() < 0.1:
                child_genome += np.random.normal(0, 0.1, self.n_dim)
            
            child = CoevIndividual(
                genome=np.clip(child_genome, -1, 1),
                species_id=0,
                elo_rating=1500.0  # Reset Elo for new individual
            )
            new_pop.append(child)
        
        self.population = new_pop
    
    def optimize(self) -> Dict:
        """Run competitive co-evolution"""
        self.initialize()
        
        elo_history = []
        best_elo_history = []
        
        for gen in range(self.n_gen):
            self.run_tournament()
            
            avg_elo = np.mean([ind.elo_rating for ind in self.population])
            best_elo = max(ind.elo_rating for ind in self.population)
            
            elo_history.append(avg_elo)
            best_elo_history.append(best_elo)
            
            if gen % 20 == 0:
                print(f"Gen {gen}: Avg Elo={avg_elo:.1f}, Best={best_elo:.1f}")
            
            self.evolve()
        
        return {
            'avg_elo_history': elo_history,
            'best_elo_history': best_elo_history,
            'final_population': self.population
        }


class CooperativeCoevolutionOptimizer:
    """Cooperative co-evolution for function optimization"""
    
    def __init__(
        self,
        objective_func: Callable[[np.ndarray], float],
        n_species: int = 3,
        species_size: int = 50,
        n_dimensions: int = 30
    ):
        self.obj_func = objective_func
        self.n_species = n_species
        self.species_size = species_size
        self.n_dim = n_dimensions
        
        # Split dimensions among species
        self.dims_per_species = n_dimensions // n_species
        self.species: List[List[CoevIndividual]] = [[] for _ in range(n_species)]
        
    def initialize(self):
        """Initialize all species"""
        for i in range(self.n_species):
            for _ in range(self.species_size):
                genome = np.random.uniform(-5, 5, self.dims_per_species)
                self.species[i].append(CoevIndividual(genome=genome, species_id=i))
    
    def form_complete_solution(
        self,
        representatives: List[CoevIndividual]
    ) -> np.ndarray:
        """Combine representatives from each species"""
        full_solution = np.concatenate([ind.genome for ind in representatives])
        return full_solution
    
    def evaluate_species_member(
        self,
        individual: CoevIndividual,
        species_idx: int,
        context: List[CoevIndividual]
    ) -> float:
        """Evaluate individual in context of other species"""
        # Create full solution
        full_genome = []
        for i in range(self.n_species):
            if i == species_idx:
                full_genome.append(individual.genome)
            else:
                full_genome.append(context[i].genome)
        
        complete_solution = np.concatenate(full_genome)
        fitness = self.obj_func(complete_solution)
        return fitness
    
    def evolve_species(
        self,
        species_idx: int,
        context: List[CoevIndividual],
        generations: int = 5
    ):
        """Evolve one species with fixed context"""
        population = self.species[species_idx]
        
        for _ in range(generations):
            # Evaluate
            for ind in population:
                ind.fitness = self.evaluate_species_member(
                    ind, species_idx, context
                )
            
            # Selection and reproduction
            new_pop = []
            sorted_pop = sorted(population, key=lambda x: x.fitness, reverse=True)
            
            # Keep best
            new_pop.append(sorted_pop[0])
            
            # Generate offspring
            while len(new_pop) < len(population):
                parent1 = random.choice(sorted_pop[:len(sorted_pop)//2])
                parent2 = random.choice(sorted_pop[:len(sorted_pop)//2])
                
                # Crossover
                child_genome = 0.5 * (parent1.genome + parent2.genome)
                
                # Mutation
                child_genome += np.random.normal(0, 0.1, len(child_genome))
                child_genome = np.clip(child_genome, -5, 5)
                
                new_pop.append(CoevIndividual(
                    genome=child_genome,
                    species_id=species_idx
                ))
            
            population[:] = new_pop
    
    def optimize(self, cycles: int = 50) -> Dict:
        """Run cooperative co-evolution"""
        self.initialize()
        
        best_fitness_history = []
        
        for cycle in range(cycles):
            # Select best from each species as context
            context = [max(sp, key=lambda x: x.fitness) for sp in self.species]
            
            # Evolve each species
            for i in range(self.n_species):
                # Create context without current species
                ctx = context.copy()
                ctx[i] = None  # Will be filled during evaluation
                
                # Use random individuals from other species as context
                temp_context = [
                    random.choice(self.species[j]) if j != i else None
                    for j in range(self.n_species)
                ]
                
                self.evolve_species(i, temp_context)
            
            # Evaluate best collaboration
            best_collaboration = self.form_complete_solution(context)
            best_fitness = self.obj_func(best_collaboration)
            best_fitness_history.append(best_fitness)
            
            if cycle % 10 == 0:
                print(f"Cycle {cycle}: Best fitness = {best_fitness:.6f}")
        
        return {
            'best_fitness_history': best_fitness_history,
            'final_best': best_fitness
        }


# Example objective function for cooperative co-evolution
def rastrigin(x: np.ndarray) -> float:
    """Rastrigin test function"""
    A = 10
    return A * len(x) + np.sum(x**2 - A * np.cos(2 * np.pi * x))


# Example usage
if __name__ == "__main__":
    print("=" * 60)
    print("COMPETITIVE CO-EVOLUTION (Prisoner's Dilemma)")
    print("=" * 60)
    
    game = PrisonersDilemma(T=5, R=3, P=1, S=0)
    comp_opt = CompetitiveCoevolutionOptimizer(
        game=game,
        population_size=100,
        n_generations=200
    )
    comp_results = comp_opt.optimize()
    
    print(f"\nFinal best Elo rating: {comp_results['best_elo_history'][-1]:.1f}")
    
    print("\n" + "=" * 60)
    print("HOST-PARASITE CO-EVOLUTION")
    print("=" * 60)
    
    hp_system = HostParasiteSystem(
        n_dimensions=10,
        host_pop_size=100,
        parasite_pop_size=100
    )
    hp_system.initialize()
    
    for gen in range(100):
        hp_system.generation()
        if gen % 20 == 0:
            stats = hp_system.get_statistics()
            print(f"Gen {gen}: Host={stats['host_mean_fitness']:.2f}, "
                  f"Parasite={stats['parasite_mean_fitness']:.2f}")
    
    print("\n" + "=" * 60)
    print("COOPERATIVE CO-EVOLUTION (Rastrigin)")
    print("=" * 60)
    
    coop_opt = CooperativeCoevolutionOptimizer(
        objective_func=rastrigin,
        n_species=3,
        species_size=50,
        n_dimensions=30
    )
    coop_results = coop_opt.optimize(cycles=50)
    
    print(f"\nFinal best fitness: {coop_results['final_best']:.6f}")
```

### 3.3 Performance Characteristics

| Aspect | Competitive | Cooperative | Host-Parasite |
|--------|-------------|-------------|---------------|
| Selection Pressure | Relative (Elo) | Absolute fitness | Co-evolutionary |
| Convergence | To Nash equilibrium | To global optimum | Arms race |
| Diversity | Maintained via competition | Decomposition-based | Red Queen dynamics |
| Best Use Case | Game strategies | High-dimensional optimization | Robustness testing |

---

## 4. Comparative Analysis

### 4.1 Mathematical Complexity

| Technique | Time Complexity | Space Complexity | Convergence Guarantee |
|-----------|----------------|------------------|----------------------|
| **NSGA-II (MOO)** | O(MN²) per gen | O(N²) | For convex Pareto fronts |
| **Dynamic Landscapes** | O(PN²) per gen | O(PN) | Local adaptation only |
| **Co-evolution** | O(S²N²) per gen | O(SN) | Nash equilibrium (competitive) |

Where: M = objectives, N = population size, P = populations, S = species

### 4.2 Fitness Landscape Characteristics

```
Multi-Objective:      Static, multi-dimensional objective space
                      ┌─────────────────┐
                      │   f1 ↓  f2 ↓   │
                      │     Pareto     │
                      │     Front      │
                      └─────────────────┘

Dynamic:              Time-varying optimum
                      ┌─────────────────┐
                      │  o →    →   o  │
                      │  optimum moves │
                      │   over time    │
                      └─────────────────┘

Co-evolutionary:      Coupled fitness landscapes
                      ┌─────────────────┐
                      │  H ↔ P ↔ H    │
                      │  coupled       │
                      │  landscapes    │
                      └─────────────────┘
```

### 4.3 Selection Criteria

| Scenario | Recommended Technique |
|----------|---------------------|
| Multiple conflicting objectives | NSGA-II (MOO) |
| Non-stationary environment | Dynamic fitness landscapes |
| Game strategy evolution | Competitive co-evolution |
| High-dimensional decomposition | Cooperative co-evolution |
| Robustness against adversaries | Host-parasite co-evolution |

---

## 5. Implementation Guidelines

### 5.1 Hyperparameter Selection

**NSGA-II:**
- Population size: 100-200
- Crossover probability: 0.9
- Mutation probability: 0.1-0.2
- Distribution index (η): 15-20

**Dynamic Optimization:**
- Number of populations: 3-5
- Memory size: 5-10
- Diversity threshold: 0.1-0.5
- Change reaction: 0.2-0.5

**Co-evolution:**
- Elo K-factor: 16-32
- Matches per generation: 5N-10N
- Species count (cooperative): √n_dimensions

### 5.2 Testing & Validation

```python
def validate_implementation():
    """Validation suite for all three techniques"""
    
    # Test 1: NSGA-II on ZDT1
    print("Testing NSGA-II...")
    problem = ZDT1Problem()
    nsga2 = NSGA2(problem, population_size=50, max_generations=50)
    pop, hv = nsga2.optimize()
    assert hv[-1] > 0.5, "Hypervolume too low"
    
    # Test 2: Dynamic optimization
    print("Testing Dynamic Optimization...")
    landscape = MovingPeakFunction(change_frequency=10)
    optimizer = MultiPopulationDynamicOptimizer(landscape)
    results = optimizer.optimize(max_generations=50)
    assert len(results['offline_error']) > 0
    
    # Test 3: Co-evolution
    print("Testing Co-evolution...")
    hp = HostParasiteSystem()
    hp.initialize()
    for _ in range(10):
        hp.generation()
    assert len(hp.hosts) == hp.host_size
    
    print("All tests passed!")
```

---

## 6. Conclusion

This report presents three complementary fitness function optimization techniques:

1. **Multi-Objective Optimization** (NSGA-II) handles multiple conflicting objectives through Pareto dominance and diversity preservation.

2. **Dynamic Fitness Landscapes** employ multi-population approaches with memory and diversity maintenance to track moving optima.

3. **Co-evolutionary Fitness** leverages inter-species interactions for robust strategy evolution and decomposition-based optimization.

Each technique includes complete mathematical formalization, reference implementation, and performance characteristics for practical application.

---

**End of Report**

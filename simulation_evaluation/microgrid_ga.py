import random
import math
import datetime
import time

# Based off of https://hackernoon.com/genetic-algorithms-explained-a-python-implementation-sd4w374i

from simulation_evaluation.microgrid_simulator import ControllEnvironment


class MicrogridGA:

    def __init__(self, generations, size, day_nr=18, precision=1, battery_power=21.1, pv_scale=1.0,
                 priorities=[1, 2, 3, 4, 5, 6, 7],
                 step_type="percentage", mutate_chance=0.2, elit_perc=0.05):
        self.battery_power = battery_power
        self.pv_scale = pv_scale
        self.priorities = priorities
        self.precision = precision
        self.test_env = ControllEnvironment(day_nr=day_nr, battery_power=battery_power, pv_scale=pv_scale,
                                            priorities=priorities)
        self.generations = generations
        self.size = size
        self.mutate_chance = mutate_chance
        self.step_type = step_type
        self.best = None
        self.best_score = None
        self.elit_perc = elit_perc
        self.history = {}
        self.population = None
        self.best_score = -99999999.999
        self.best = None

    def save_best(self):
        applied = self.test_env.step_24h(self.best, battery_power=self.battery_power, pv_scale=self.pv_scale,
                                         step_type=self.step_type)
        self.test_env.save_result(applied)

    def get_history(self):
        return self.history

    def get_deployed_best(self):
        applied = self.test_env.step_24h(self.best, battery_power=self.battery_power, pv_scale=self.pv_scale, step_type=self.step_type)
        return applied
    
    def get_original(self):
        return self.test_env.input_df.reset_index(drop=True)
    
    def generate_population(self):
        population = []
        for i in range(self.size):
            individual = {"Nursery1_Lights_Quota": [round(random.random(), self.precision) for x in range(0, 24)],
                          "Nursery1_Sockets_Quota": [round(random.random(), self.precision) for x in range(0, 24)],
                          "Nursery2_Lights_Quota": [round(random.random(), self.precision) for x in range(0, 24)],
                          "Nursery2_Sockets_Quota": [round(random.random(), self.precision) for x in range(0, 24)],
                          "Playground_Lights_Quota": [round(random.random(), self.precision) for x in range(0, 24)],
                          "Playground_Sockets_Quota": [round(random.random(), self.precision) for x in range(0, 24)],
                          "Streetlights_Quota": [round(random.random(), self.precision) for x in range(0, 24)]
                          }
            population.append(individual)
        self.population = population

    def evaluate_individual(self, individual):
        return sum(individual['Battery_SoC']) / 100.0 / 24.0

    def apply_function(self, individual):
        applied = self.test_env.step_24h(individual, battery_power=self.battery_power, pv_scale=self.pv_scale,
                                         step_type=self.step_type)
        return self.evaluate_individual(applied)
    
    def get_deployed(self,individual):
        applied = self.test_env.step_24h(individual, battery_power=self.battery_power, pv_scale=self.pv_scale,
                                         step_type=self.step_type)
        return applied
    
    def evaluate_population(self, population):
        ret = {}
        for pop in population:
            ret[self.apply_function(pop)] = pop
        return ret

    def choice_by_roulette(self, sorted_population, fitness_sum):
        offset = 0
        normalized_fitness_sum = fitness_sum

        lowest_fitness = min(sorted_population)
        if lowest_fitness < 0:
            offset = -lowest_fitness
            normalized_fitness_sum += offset * len(sorted_population)

        draw = random.uniform(0, 1)

        accumulated = 0
        for fitness_orig in sorted(sorted_population, reverse=True):
            fitness = offset + fitness_orig
            probability = fitness / normalized_fitness_sum
            accumulated += probability

            if draw <= accumulated:
                return sorted_population[fitness_orig]

    def crossover(self, individual_a, individual_b):
        new_individual = {}
        for dev in individual_a:
            new_individual[dev] = []
            for i, _ in enumerate(individual_a[dev]):
                # Select
                # new_individual[dev].append(random.choice([individual_a[dev][i], individual_b[dev][i]]))
                # Mean
                new_individual[dev].append(round((individual_a[dev][i] + individual_b[dev][i]) / 2.0, self.precision))
        return new_individual

    def mutate(self, individual):
        for dev in individual:
            for i, _ in enumerate(individual[dev]):
                # Random Full Mutation of value
                if random.random() > self.mutate_chance:
                    individual[dev][i] = round(random.random(), self.precision)
        return individual

    def make_next_generation(self, evaluated_population):
        next_generation = []
        population_size = len(evaluated_population)
        fitness_sum = sum(evaluated_population.keys())

        # Elitism
        elit_size = int(population_size * self.elit_perc)
        i = 0
        for score in sorted(evaluated_population, reverse=True):
            next_generation.append(evaluated_population[score])
            i += 1
            if i >= elit_size:
                break

        for i in range(population_size - elit_size):
            first_choice = None
            second_choice = None

            # Safe Wheel
            while first_choice is None:
                first_choice = self.choice_by_roulette(evaluated_population, fitness_sum)
            while second_choice is None:
                second_choice = self.choice_by_roulette(evaluated_population, fitness_sum)

            individual = self.crossover(first_choice, second_choice)
            individual = self.mutate(individual)

            next_generation.append(individual)

        return next_generation

    def do_step(self, step):
        evaluated_population = self.evaluate_population(self.population)
        if max(evaluated_population) > self.best_score:
            self.best = evaluated_population[max(evaluated_population)]
            self.best_score = max(evaluated_population)
        self.history[step] = [self.best_score, self.best]
        self.population = self.make_next_generation(evaluated_population)

    def run(self):
        start = time.time()
        self.generate_population()
        i = 0
        while True:
            print(f"🧬 GENERATION {i}")
            print("Started: ", datetime.datetime.now())
            self.do_step(i)
            print("Best Individual: ", self.best)
            print("Best Score: ", self.best_score)
            print("Elapsed Time:", time.time() - start)
            i += 1
            if i == self.generations:
                break

        print("\n🔬 FINAL RESULT")
        print("Best Individual: ", self.best)
        print("Best Score: ", self.best_score)
        print("Elapsed Time:", time.time() - start)
        #self.save_best()
        #print("Best Individual saved to output_data.csv")
        print("History: ", [self.history[x][0] for x in self.history])
